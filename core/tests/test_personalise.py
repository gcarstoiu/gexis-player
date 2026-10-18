"""ADR-0149: first use's part 2 - owed, applied, put off."""
from __future__ import annotations

import pytest

from gexis_core import personalise, settling


class FakeSettings:
    def __init__(self, values=None, refuse=()):
        self.values = dict(values or {})
        self.refuse = set(refuse)
        self.order = []

    def value(self, key):
        return self.values.get(key)

    def set(self, key, value):
        if key in self.refuse:
            raise ValueError(f"{key} refused")
        self.order.append(key)
        self.values[key] = value


OFFERED = [
    {"id": "lyrion-server", "name": "Lyrion Server", "row": "lyrion-server.enabled", "component": "lyrion-server"},
    {"id": "plexamp", "name": "Plexamp", "row": "plexamp.enabled", "component": "plexamp"},
    {"id": "beszel", "name": "Beszel", "row": "beszel.enabled", "component": "beszel"},
]


def test_owed_after_part_one_and_ended_by_finishing_or_putting_off(tmp_path):
    path = tmp_path / "personalise.json"
    assert personalise.state(path) is None, "a player updated from before part 2 is not owed it"
    personalise.mark_pending(path)
    assert personalise.state(path) == personalise.PENDING and personalise.first(path)
    personalise.mark_pending(path, first=False)
    assert not personalise.first(path), "asked again from Settings starts from what the player has"
    personalise.end(personalise.LATER, path)
    assert personalise.state(path) == personalise.LATER
    path.write_text("not json")
    assert personalise.state(path) is None


def test_only_part_twos_settings_are_written_and_one_more_refuses_them_all():
    with pytest.raises(ValueError, match="device_name"):
        personalise.checked({"spotify_enabled": True, "device_name": "x"})
    with pytest.raises(ValueError):
        personalise.checked(["spotify_enabled"])
    # George, 2026-10-18: the touchpad is part 2's too.
    assert personalise.checked({"phone_touchpad": False}) == {"phone_touchpad": False}
    # A plugin part 2 does not offer is not part 2's to switch on.
    with pytest.raises(ValueError, match="beszel.enabled"):
        personalise.checked({"beszel.enabled": True})


def test_answers_are_written_then_the_plugins_switched_on_then_the_downloads_followed():
    settings = FakeSettings({"spotify_enabled": True})
    begun = []
    result = personalise.apply({"plexamp.enabled": True, "lms_library": False, "spotify_enabled": True,
                                "visualiser_skins": True, "skin_corpus": "Turntables",
                                "lyrion-server.enabled": True}, settings, OFFERED, begun.extend)
    # The sources and the screen first, the switches that download last; a
    # value already held is not written again.
    assert settings.order == ["lms_library", "visualiser_skins", "skin_corpus",
                              "lyrion-server.enabled", "plexamp.enabled"]
    assert [w["id"] for w in begun] == ["skins", "lyrion-server", "plexamp"]
    assert result == {"failed": [], "waiting": ["skins", "lyrion-server", "plexamp"],
                      "written": ["lms_library", "visualiser_skins", "skin_corpus", "lyrion-server.enabled", "plexamp.enabled"]}


def test_one_refusal_is_named_and_the_rest_still_written():
    settings = FakeSettings(refuse={"weather_location"})
    begun = []
    result = personalise.apply({"idle_enabled": True, "idle_weather": True, "weather_location": "Lisbon",
                                "plexamp.enabled": False}, settings, OFFERED, begun.extend)
    assert result["failed"] == ["weather_location"]
    assert settings.values["idle_enabled"] is True and settings.values["plexamp.enabled"] is False
    assert begun == [], "a plugin switched off downloads nothing"


@pytest.mark.asyncio
async def test_the_routes_finish_and_put_off_part_two(tmp_path, monkeypatch):
    from aiohttp.test_utils import TestClient, TestServer
    from gexis_core import discovery
    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer

    monkeypatch.setattr(personalise, "PATH", tmp_path / "personalise.json")
    for fn in (personalise.state, personalise.mark_pending, personalise.end, personalise.first):
        monkeypatch.setattr(fn, "__defaults__", tuple(tmp_path / "personalise.json" if isinstance(d, type(personalise.PATH)) else d
                                                      for d in fn.__defaults__))
    begun = []
    monkeypatch.setattr(settling, "begin", lambda items, *a, **k: begun.extend(items))

    async def one_server(*_a, **_k):
        return [{"address": "192.0.2.10:9000", "name": "Lyrion Music Server", "version": "9.1.1", "uuid": "", "host": "nas"}]

    monkeypatch.setattr(discovery, "find_servers", one_server)
    store = StateStore({})
    settings = FakeSettings({"lms_enabled": True})
    personalise.mark_pending()
    store.set_personalise(personalise.PENDING)
    async with TestClient(TestServer(StateServer(store, settings=settings).make_app())) as client:
        assert (await (await client.get("/personalise")).json())["state"] == "pending"
        bad = await client.post("/personalise/finish", json={"settings": {"device_name": "x"}})
        assert bad.status == 400 and "device_name" not in settings.values
        r = await client.post("/personalise/finish", json={"settings": {"spotify_enabled": False, "visualiser_skins": True}})
        assert (await r.json())["waiting"] == ["skins"]
        assert settings.values["spotify_enabled"] is False
        assert personalise.state() == personalise.DONE and store.state.personalise is None
        # Put off on a new player (George, 2026-10-18): the Lyrion client goes
        # off, so the panel waits with Spotify and Bluetooth.
        personalise.mark_pending()
        assert (await client.post("/personalise/later")).status == 200
        assert settings.values["lms_enabled"] is False and "lms_server" not in settings.values
        assert personalise.state() == personalise.LATER
    assert [b["id"] for b in begun] == ["skins"]


def test_owed_only_until_the_first_boot_after_setup(tmp_path):
    """George, 2026-10-18: the automatic part 2 only on the first boot after
    setup; unanswered by then, it is put off."""
    path = tmp_path / "personalise.json"
    personalise.mark_pending(path, boot="setup")
    assert personalise.at_start(path, boot="setup") is True, "a core restart in setup's own boot"
    assert personalise.at_start(path, boot="next") is True, "the first boot after setup"
    assert personalise.at_start(path, boot="next") is True, "a core restart in that boot"
    assert personalise.at_start(path, boot="later") is False, "any boot after it"
    # Opened from Settings: the boot it was opened in, no more.
    personalise.mark_pending(path, first=False, boot="b1")
    assert personalise.at_start(path, boot="b1") is True
    assert personalise.at_start(path, boot="b2") is False
    personalise.end(personalise.DONE, path)
    assert personalise.at_start(path, boot="b3") is None


def test_put_off_on_a_new_player_leaves_spotify_and_bluetooth(tmp_path, monkeypatch):
    """George, 2026-10-18: skipped on a fresh install, the panel showed the
    library's tiles with nothing behind them. Put off on a new player, the
    Lyrion client goes off; asked again from Settings, nothing changes."""
    monkeypatch.setattr(personalise.end, "__defaults__", (tmp_path / "personalise.json",))
    settings = FakeSettings({"lms_enabled": True, "spotify_enabled": True})
    personalise.put_off(settings, first=True)
    assert settings.values["lms_enabled"] is False and settings.values["spotify_enabled"] is True
    again = FakeSettings({"lms_enabled": True})
    personalise.put_off(again, first=False)
    assert again.order == [], "asked again and put off, nothing is written"
    assert personalise.state(tmp_path / "personalise.json") == personalise.LATER


@pytest.mark.asyncio
async def test_a_server_part_two_sets_restarts_the_core_once_settled(tmp_path, monkeypatch):
    """George, 2026-10-18: after part 2 chose a Lyrion server, the library's
    tiles had nothing behind them - a server is used from the core's next
    start. The core restarts, but not before the downloads are in."""
    import asyncio
    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer

    store = StateStore({})
    server = StateServer(store, settings=FakeSettings({"lms_enabled": True}))
    ran = []

    async def fake_exec(*args, **_k):
        ran.append(args)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    record = {"items": [{"id": "skins"}]}
    monkeypatch.setattr(settling, "read", lambda *a, **k: record)
    store.set_settling({"phase": "settling", "items": []})
    task = asyncio.ensure_future(server._restart_when_settled(every_s=0.01))
    await asyncio.sleep(0.1)
    assert ran == [], "not while the skins are still coming"
    store.set_settling({"phase": "ready", "items": []})
    monkeypatch.setattr(asyncio, "sleep", (lambda real: (lambda s: real(0)))(asyncio.sleep))
    await asyncio.wait_for(task, 2)
    assert ran == [("systemctl", "restart", "gexis-core")]
