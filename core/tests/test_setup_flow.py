"""ADR-0104 §4: the answers the core keeps, and applying them."""
from __future__ import annotations

import asyncio
import json
import stat

import pytest

from gexis_core import setup_network as sn
from gexis_core.setup_flow import SetupFlow

from test_setup_network import NOTHING, FakeNM, setup


class FakeSettings:
    def __init__(self, **values):
        self.values = {"device_name": "gexis", **values}
        self.sets = []

    def value(self, key):
        return self.values.get(key)

    def set(self, key, value):
        if key == "output_device" and value == "Nowhere":
            raise ValueError("not an option")
        self.sets.append((key, value))
        self.values[key] = value


def make(tmp_path, nm, settings=None, **kw):
    kw_servers = {"servers": kw.pop("servers", [])}
    offered = kw.pop("plugins", [])
    net, clock = setup(tmp_path, nm, **kw)
    countries, reboots = [], []

    async def country(c):
        countries.append(c)

    async def reboot():
        reboots.append(True)

    servers = kw_servers.pop("servers", [])

    async def find():
        return list(servers)

    flow = SetupFlow(
        net, settings or FakeSettings(), reboot=reboot,
        answers=tmp_path / "answers.json", marker=tmp_path / "setup-done",
        set_country=country, find_servers=find, sleep=clock.sleep,
        plugins=lambda: offered, settling_path=tmp_path / "settling.json",
    )
    return flow, net, clock, countries, reboots


def test_the_password_is_kept_but_never_handed_back(tmp_path):
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    out = flow.save({"ssid": "Home", "password": "hunter22", "name": "Den"})
    assert "password" not in out and out["has_password"] and out["ssid"] == "Home"
    assert stat.S_IMODE((tmp_path / "answers.json").stat().st_mode) == 0o600


def test_unknown_or_mistyped_answers_are_refused(tmp_path):
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    with pytest.raises(ValueError):
        flow.save({"favourite": "x"})
    with pytest.raises(ValueError):
        flow.save({"spotify": "yes"})


def test_a_new_password_clears_the_last_error(tmp_path):
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    flow._write({"ssid": "Home", "error": {"ssid": "Home", "reason": "The password was not accepted."}})
    assert flow.save({"password": "again123"}).get("error") is None


def test_country_from_the_time_zone(tmp_path):
    tab = tmp_path / "zone.tab"
    tab.write_text("# comment\nDE\t+5230+01322\tEurope/Berlin\tmost of Germany\nRO\t+4426+02606\tEurope/Bucharest\n")
    assert sn.country_for("Europe/Berlin", tab) == "DE"
    assert sn.country_for("Europe/Bucharest", tab) == "RO"
    assert sn.country_for("Mars/Olympus", tab) is None
    assert sn.country_for(None, tab) is None


def finish(flow, net):
    async def go():
        net._state = "open"
        net._needed = True
        flow.finish()
        await flow._task
    asyncio.run(go())


def test_finishing_writes_the_settings_then_joins_and_marks_the_device_set_up(tmp_path):
    nm = FakeNM(devices=NOTHING)
    settings = FakeSettings()
    flow, net, _, countries, reboots = make(tmp_path, nm, settings)
    flow.save({"ssid": "Home", "password": "hunter22", "name": "gexis", "timezone": "Europe/Berlin",
               "spotify": False, "bluetooth": True, "headless": False, "output": "HiFiBerry DAC+ HD",
               "clock": "12 h"})
    finish(flow, net)
    keys = [k for k, _ in settings.sets]
    assert "timezone" in keys and "spotify_enabled" in keys and "output_device" in keys
    assert ("clock_format", "12 h") in settings.sets
    assert "device_name" not in keys, "an unchanged value is not written again"
    assert countries == ["DE"]
    add = nm.did("connection", "add")[0]
    assert add[add.index("con-name") + 1] == "Home" and "hunter22" in add
    assert (tmp_path / "setup-done").exists() and not (tmp_path / "answers.json").exists()
    assert net.status()["network"] == "online" and not net.needed
    assert reboots == [], "no rename, no restart"


def test_a_rename_restarts_the_device_after_the_join(tmp_path):
    nm = FakeNM(devices=NOTHING)
    flow, net, _, _, reboots = make(tmp_path, nm)
    flow.save({"ssid": "Home", "password": "hunter22", "name": "Den"})
    finish(flow, net)
    assert reboots == [True]


def test_a_wrong_password_keeps_every_answer_but_the_password_and_reopens_setup(tmp_path):
    nm = FakeNM(devices=NOTHING, up_rc=4)
    flow, net, _, _, reboots = make(tmp_path, nm)
    flow.save({"ssid": "Home", "password": "wrongpass", "name": "Den", "timezone": "Europe/Berlin"})
    finish(flow, net)
    kept = flow.answers()
    assert kept["name"] == "Den" and kept["timezone"] == "Europe/Berlin" and kept["ssid"] == "Home"
    assert not kept["has_password"] and kept["step"] == "wifi"
    assert kept["error"] == {"ssid": "Home", "reason": "The password was not accepted."}
    assert nm.did("connection", "delete", "Home")[-1], "the wrong password is not kept by NetworkManager"
    assert net.status()["network"] == "open", "the setup network is back"
    assert net.status()["reason"] == "The password was not accepted." and net.status()["failed"] == "Home"
    assert not (tmp_path / "setup-done").exists() and reboots == []


def test_one_refused_setting_does_not_stop_setup(tmp_path):
    nm = FakeNM(devices=NOTHING)
    flow, net, *_ = make(tmp_path, nm)
    flow.save({"ssid": "Home", "password": "hunter22", "output": "Nowhere", "timezone": "Europe/Berlin"})
    finish(flow, net)
    assert (tmp_path / "setup-done").exists()


def test_without_a_network_there_is_nothing_to_finish(tmp_path):
    flow, net, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    net._state = "open"
    with pytest.raises(ValueError):
        flow.finish()


def test_the_retry_keeps_running_after_a_failed_join_from_setup(tmp_path):
    """The loop once ended when the network went down, so a join from setup
    that failed and reopened it left the device with no retry at all."""
    nm = FakeNM(devices=NOTHING, saved={"Home": "preconfigured"}, in_range=set(), up_rc=4)
    net, clock = setup(tmp_path, nm, stations=0)

    async def go():
        task = asyncio.create_task(net.run())
        while net.status()["network"] != "open":
            await asyncio.sleep(0)
        await net.join_new("Other", "wrongpass")
        assert net.status()["network"] == "open"
        nm.in_range = {"Home"}
        nm.up_rc = 0
        for _ in range(10_000):
            await asyncio.sleep(0)
            if net.status()["network"] == "online":
                break
        task.cancel()

    asyncio.run(go())
    assert net.status()["network"] == "online"
    assert nm.did("connection", "up", "preconfigured")


def test_without_an_address_one_lyrion_server_found_after_joining_is_used(tmp_path):
    nm = FakeNM(devices=NOTHING)
    settings = FakeSettings()
    flow, net, clock, *_ = make(tmp_path, nm, settings,
                                servers=[{"address": "192.168.1.10:9000", "name": "den-lms"}])
    seen = []
    net._on_change = seen.append
    flow.save({"ssid": "Home", "password": "hunter22", "lms_mode": "find"})
    finish(flow, net)
    assert ("lms_server", "192.168.1.10:9000") in settings.sets
    done = [s for s in seen if s["network"] == "done"][0]
    assert done["finished"] == {"ssid": "Home", "restarting": False, "restart_for": None, "name": "gexis",
                                "library": {"state": "found", "name": "den-lms", "address": "192.168.1.10:9000"}}
    assert net.status()["network"] == "online" and not net.status()["finished"]


def test_several_servers_are_named_and_none_is_chosen(tmp_path):
    nm = FakeNM(devices=NOTHING)
    settings = FakeSettings()
    flow, net, *_ = make(tmp_path, nm, settings,
                         servers=[{"address": "a:9000", "name": "one"}, {"address": "b:9000", "name": "two"}])
    seen = []
    net._on_change = seen.append
    flow.save({"ssid": "Home", "password": "hunter22", "lms_mode": "find"})
    finish(flow, net)
    assert not [k for k, _ in settings.sets if k == "lms_server"]
    assert [s for s in seen if s["network"] == "done"][0]["finished"]["library"] == {"state": "several", "names": ["one", "two"]}


def test_an_address_given_in_setup_is_not_searched_over(tmp_path):
    nm = FakeNM(devices=NOTHING)
    flow, net, *_ = make(tmp_path, nm, servers=[{"address": "x:9000", "name": "x"}])
    seen = []
    net._on_change = seen.append
    flow.save({"ssid": "Home", "password": "hunter22", "lms": "192.168.1.5:9000", "lms_mode": "address"})
    finish(flow, net)
    assert [s for s in seen if s["network"] == "done"][0]["finished"]["library"] == {"state": "given", "address": "192.168.1.5:9000"}


def test_the_last_screen_says_a_rename_restarts(tmp_path):
    nm = FakeNM(devices=NOTHING)
    flow, net, _, _, reboots = make(tmp_path, nm)
    seen = []
    net._on_change = seen.append
    flow.save({"ssid": "Home", "password": "hunter22", "name": "Den"})
    finish(flow, net)
    assert [s for s in seen if s["network"] == "done"][0]["finished"]["restarting"] is True
    assert reboots == [True]
    assert seen[-1]["network"] == "done", "no ordinary screen between setup and the restart"


def test_nothing_is_searched_for_or_adopted_without_being_asked(tmp_path):
    """George, 2026-09-29: a server the user did not ask for, found behind
    his back, is the thing to avoid."""
    nm = FakeNM(devices=NOTHING)
    settings = FakeSettings()
    flow, net, *_ = make(tmp_path, nm, settings, servers=[{"address": "x:9000", "name": "x"}])
    seen = []
    net._on_change = seen.append
    flow.save({"ssid": "Home", "password": "hunter22"})
    finish(flow, net)
    assert not [k for k, _ in settings.sets if k.startswith("lms")]
    assert [s for s in seen if s["network"] == "done"][0]["finished"]["library"] == {"state": "unchanged"}


def test_i_dont_use_lyrion_switches_it_off_and_ignores_a_typed_address(tmp_path):
    nm = FakeNM(devices=NOTHING)
    settings = FakeSettings(lms_enabled=True)
    flow, net, *_ = make(tmp_path, nm, settings)
    flow.save({"ssid": "Home", "password": "hunter22", "lms": "1.2.3.4:9000", "lms_mode": "off"})
    finish(flow, net)
    assert ("lms_enabled", False) in settings.sets
    assert not [k for k, _ in settings.sets if k == "lms_server"], "the field is not the answer"


def test_an_unknown_lms_mode_is_refused(tmp_path):
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    with pytest.raises(ValueError):
        flow.save({"lms_mode": "maybe"})


def test_the_panel_never_leaves_setup_between_the_join_and_the_last_screen(tmp_path):
    """George, 2026-09-29: the home screen showed between the join and the
    last setup screen, for as long as the Lyrion search took."""
    nm = FakeNM(devices=NOTHING)
    flow, net, *_ = make(tmp_path, nm, servers=[{"address": "a:9000", "name": "one"}])
    seen = []
    net._on_change = seen.append
    flow.save({"ssid": "Home", "password": "hunter22", "lms_mode": "find"})
    finish(flow, net)
    states = [s["network"] for s in seen]
    assert states.index("done") == states.index("joining") + 1, states
    assert states[-1] == "online"


def test_a_screen_chosen_in_setup_restarts_at_the_end_where_keep_is_asked(tmp_path):
    """ADR-0109 decision 5: the screen is written during setup and the
    restart that ends it is where the panel asks Keep this screen?."""
    from gexis_core import setup_network as sn
    net = sn.SetupNetwork()
    net.finished("Home", {"state": "off"}, "screen", "gexis")
    assert net.status()["finished"]["restart_for"] == "screen" and net.status()["finished"]["restarting"]
    net.finished("Home", {"state": "off"}, True, "gexis")
    assert net.status()["finished"]["restart_for"] == "name"


def test_the_phone_is_told_in_words_not_the_core_s_text():
    """George, 2026-10-04: "Human readable errors." The core's own text is
    for the log."""
    from gexis_core import setup_flow as sf
    assert sf.said("no network chosen") == "Choose a Wi-Fi network first, or connect the player by cable."
    assert sf.said("setup is not running") == "Setup has already finished. Open the player at its address instead."
    assert sf.said("unknown screen Acme/Panel 9") == "That screen isn't on the list. Choose another, or Headless."
    assert sf.said("choose a screen or headless, not both") == "Choose a screen or Headless, not both."
    for raw in ("answers must be an object", "unknown answer colour", "step must be text", "setup is not wired up"):
        assert sf.said(raw) == "Something went wrong saving that. Try again."


PLUGINS = [
    {"id": "plexamp", "name": "Plexamp", "row": "plexamp.enabled", "component": "plexamp", "notice": "Plex terms."},
    {"id": "lyrion-server", "name": "Lyrion Server", "row": "lyrion-server.enabled", "component": "lyrion"},
    {"id": "beszel", "name": "Beszel", "row": "beszel.enabled", "component": None},
]


def test_only_offered_plugins_are_an_answer(tmp_path):
    """ADR-0128: the Plugins step's answer is a list of what was offered."""
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING), plugins=PLUGINS)
    assert flow.save({"plugins": ["plexamp", "beszel"]})["plugins"] == ["beszel", "plexamp"]
    with pytest.raises(ValueError):
        flow.save({"plugins": ["spotify"]})
    with pytest.raises(ValueError):
        flow.save({"plugins": "plexamp"})


def test_chosen_plugins_go_on_after_the_join_the_rest_off_and_the_first_start_waits_for_them(tmp_path):
    """ADR-0128: switched after the join (they download), every offered one
    set explicitly, and what downloads is what the first start waits for -
    with the visualiser's skins when they were chosen."""
    nm = FakeNM(devices=NOTHING)
    settings = FakeSettings()
    flow, net, *_ = make(tmp_path, nm, settings, plugins=PLUGINS)
    flow.save({"ssid": "Home", "password": "hunter22", "visualiser": True,
               "plugins": ["plexamp", "beszel"]})
    finish(flow, net)
    assert ("plexamp.enabled", True) in settings.sets and ("beszel.enabled", True) in settings.sets
    assert ("lyrion-server.enabled", False) in settings.sets, "not chosen is off, not left at its default"
    import json
    waits = json.loads((tmp_path / "settling.json").read_text())["items"]
    assert [w["id"] for w in waits] == ["skins", "plexamp"], "Beszel downloads nothing to wait for"


def test_nothing_chosen_to_download_writes_nothing_to_wait_for(tmp_path):
    settings = FakeSettings()
    flow, net, *_ = make(tmp_path, FakeNM(devices=NOTHING), settings, plugins=PLUGINS)
    flow.save({"ssid": "Home", "password": "hunter22", "plugins": ["beszel"]})
    finish(flow, net)
    assert not (tmp_path / "settling.json").exists()


# -- ADR-0131: restoring a backup in setup ----------------------------------

from gexis_core import backups as _backups
from test_backups import VALUES, _real_device


def _with_backup(tmp_path, nm, settings=None, values=VALUES, **kw):
    flow, net, clock, countries, reboots = make(tmp_path, nm, settings, **kw)
    flow._backup = tmp_path / "state" / "setup-backup.tgz"
    flow._restore_root = tmp_path / "card"
    (tmp_path / "card").mkdir()
    names = []
    flow._apply_name = lambda: names.append(True)
    old = _real_device(tmp_path / "old", values)
    made = _backups.create("Living Room", tmp_path / "share", old)
    upload = tmp_path / "upload.part"
    upload.write_bytes((tmp_path / "share" / made).read_bytes())
    return flow, net, countries, reboots, upload, names


def test_a_backup_is_checked_kept_and_said_in_the_answers(tmp_path):
    flow, net, _, _, upload, _ = _with_backup(tmp_path, FakeNM(devices=NOTHING))
    out = flow.take_backup(upload, "gexis-living-room-20261008-101500.tgz")
    assert out["start"] == "restore" and out["backup"]["name"] == "Living Room"
    assert out["backup"]["file"] == "gexis-living-room-20261008-101500.tgz"
    assert stat.S_IMODE(flow._backup.stat().st_mode) == 0o600 and not upload.exists()


def test_a_refused_file_is_deleted_and_the_kept_one_stays(tmp_path):
    flow, net, _, _, upload, _ = _with_backup(tmp_path, FakeNM(devices=NOTHING))
    flow.take_backup(upload)
    junk = tmp_path / "junk.part"
    junk.write_bytes(b"a photo")
    with pytest.raises(_backups.Refused):
        flow.take_backup(junk)
    assert not junk.exists() and flow._backup.exists()
    assert flow.answers()["backup"]["name"] == "Living Room"


def test_restoring_joins_applies_the_backup_s_answers_puts_the_files_back_and_restarts(tmp_path):
    """ADR-0131 §5: the country from the backup's time zone, the join, its
    main answers through Settings (Headless before the screen), the files,
    what the first start waits for, then the restart - and the file gone."""
    nm = FakeNM(devices=NOTHING)
    settings = FakeSettings()
    flow, net, countries, reboots, upload, names = _with_backup(tmp_path, nm, settings, plugins=PLUGINS)
    flow.take_backup(upload)
    flow.save({"ssid": "Home", "password": "hunter22"})
    told = asyncio.run(_finish_told(flow, net))
    assert countries == ["DE"]
    keys = [k for k, _ in settings.sets]
    assert keys.index("headless") < keys.index("screen")
    assert ("device_name", "Living Room") in settings.sets and ("timezone", "Europe/Berlin") in settings.sets
    assert "volume_max" not in keys, "everything else comes back with the files"
    assert (tmp_path / "card/var/lib/gexis-core/settings.db").exists()
    assert names == [True]
    waits = json.loads((tmp_path / "settling.json").read_text())["items"]
    # The backup stores Plexamp on and Beszel off, and nothing for the
    # Lyrion Server: its switch's default, on - so it is waited for too
    # (found 2026-10-10: a switch left at its default read as off).
    assert [w["id"] for w in waits] == ["skins", "plexamp", "lyrion"]
    assert net.status()["finished"]["restart_for"] == "restore"
    assert reboots == [True] and not flow._backup.exists()
    assert (tmp_path / "setup-done").exists()
    assert told == {"keep_question": True}


def test_a_screen_this_version_does_not_know_is_left_to_settings(tmp_path):
    settings = FakeSettings()
    flow, net, _, _, upload, _ = _with_backup(tmp_path, FakeNM(devices=NOTHING), settings,
                                              values={**VALUES, "screen": "Future/Panel 9000"})
    flow.take_backup(upload)
    flow.save({"ssid": "Home", "password": "hunter22"})
    assert asyncio.run(_finish_told(flow, net)) == {"keep_question": False}
    assert "screen" not in [k for k, _ in settings.sets]


async def _finish_told(flow, net):
    net._state, net._needed = "open", True
    told = flow.finish()
    await flow._task
    return told


def test_a_failed_join_keeps_the_backup_and_goes_back_to_network(tmp_path):
    nm = FakeNM(devices=NOTHING, up_rc=4)
    settings = FakeSettings()
    flow, net, _, reboots, upload, _ = _with_backup(tmp_path, nm, settings)
    flow.take_backup(upload)
    flow.save({"ssid": "Home", "password": "wrongpass"})
    finish(flow, net)
    assert flow._backup.exists() and flow.answers()["step"] == "wifi"
    assert settings.sets == [] and reboots == []
    assert not (tmp_path / "card/var/lib/gexis-core/settings.db").exists()


def test_restore_without_a_backup_is_refused_and_new_ignores_one(tmp_path):
    flow, net, _, _, upload, _ = _with_backup(tmp_path, FakeNM(devices=NOTHING))
    flow.save({"ssid": "Home", "password": "hunter22", "start": "restore"})
    with pytest.raises(ValueError, match="no backup"):
        asyncio.run(_finish_told(flow, net))
    flow.take_backup(upload)
    flow.save({"start": "new"})
    finish(flow, net)
    assert not (tmp_path / "card/var/lib/gexis-core/settings.db").exists(), "New player: the backup is not used"


def _restored(tmp_path, key):
    import sqlite3
    conn = sqlite3.connect(tmp_path / "card/var/lib/gexis-core/settings.db")
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return json.loads(row[0]) if row else None


def test_a_step_changed_in_the_review_is_written_over_the_backup(tmp_path):
    """ADR-0131 as amended (George, 2026-10-08): a backup set up as another
    player - the name changed in the review is what it starts with, in the
    settings put back and through Settings; the backup's name is not
    re-applied over it. What was left alone stays the backup's."""
    settings = FakeSettings()
    flow, net, _, reboots, upload, names = _with_backup(tmp_path, FakeNM(devices=NOTHING), settings, plugins=PLUGINS)
    flow.take_backup(upload)
    flow.save({"ssid": "Home", "password": "hunter22", "name": "Kitchen", "plugins": ["beszel"]})
    asyncio.run(_finish_told(flow, net))
    assert _restored(tmp_path, "device_name") == "Kitchen"
    assert ("device_name", "Kitchen") in settings.sets
    assert names == [], "the backup's own name is not put back over the new one"
    assert _restored(tmp_path, "timezone") == "Europe/Berlin", "left alone: the backup's"
    assert _restored(tmp_path, "plexamp.enabled") is False and _restored(tmp_path, "beszel.enabled") is True
    assert not (tmp_path / "settling.json").exists() or \
        [w["id"] for w in json.loads((tmp_path / "settling.json").read_text())["items"]] == ["skins"]
    assert net.status()["finished"]["name"] == "Kitchen" and reboots == [True]


def test_lyrion_found_after_the_join_is_written_into_the_restored_settings(tmp_path):
    settings = FakeSettings()
    flow, net, _, _, upload, _ = _with_backup(tmp_path, FakeNM(devices=NOTHING), settings,
                                              servers=[{"name": "Den", "address": "10.0.0.5:9000"}])
    flow.take_backup(upload)
    flow.save({"ssid": "Home", "password": "hunter22", "lms_mode": "find"})
    asyncio.run(_finish_told(flow, net))
    assert _restored(tmp_path, "lms_server") == "10.0.0.5:9000" and _restored(tmp_path, "lms_enabled") is True


def test_a_backup_given_another_name_leaves_the_first_player_s_identities_behind(tmp_path):
    """George, 2026-10-08: "Setup could offer to leave these behind when the
    name is changed" - "yes". The Beszel fingerprint, Plexamp's claim, the
    Spotify sign-in and the pairings stay with the first player; everything
    else comes back."""
    flow, net, _, _, upload, _ = _with_backup(tmp_path, FakeNM(devices=NOTHING))
    seen = flow.take_backup(upload)["backup"]
    assert set(seen["identities"]) == {"Beszel connection", "Plexamp's claim", "Spotify sign-in", "Bluetooth pairings"}
    flow.save({"ssid": "Home", "password": "hunter22", "name": "Kitchen"})
    asyncio.run(_finish_told(flow, net))
    card = tmp_path / "card"
    for gone in ("var/lib/beszel-agent", "home/pi/.local/share/Plexamp", "var/lib/go-librespot/state.json",
                 "var/lib/bluetooth"):
        assert not (card / gone).exists(), gone
    assert (card / "var/lib/gexis-music/Playlists/Evening.m3u").exists()
    assert (card / "var/lib/gexis-core/enrichment.db").exists()


def test_the_same_player_keeps_them_renamed_or_not(tmp_path):
    """Said to be the same player (the switch off), or the name left as the
    backup's even with its step opened: everything comes back."""
    for answers in ({"name": "Kitchen", "second_player": False}, {"name": "Living Room"}):
        root = tmp_path / str(len(answers))
        root.mkdir()
        flow, net, _, _, upload, _ = _with_backup(root, FakeNM(devices=NOTHING))
        flow.take_backup(upload)
        flow.save({"ssid": "Home", "password": "hunter22", **answers})
        asyncio.run(_finish_told(flow, net))
        assert (root / "card/var/lib/beszel-agent/fingerprint").exists(), answers
        assert (root / "card/home/pi/.local/share/Plexamp/Settings").exists(), answers


CONNECTED = {**VALUES, "beszel.enabled": True, "beszel.hub": "http://192.0.2.9:8090", "beszel.key": "ssh-ed25519 AAAA",
             "beszel.token": "t0ken", "plexamp.claim_token": "claim-abc"}


def test_a_second_player_leaves_the_first_one_s_hub_and_claim_in_the_settings_too(tmp_path):
    """George, 2026-10-08: a second player came up still showing the first
    one's Beszel hub - "everything goes, including IP". The connection is
    settings, not files: the whole Beszel plugin back to its defaults, and
    Plexamp's claim token gone with its switch kept. The same player keeps
    them all."""
    for answers, kept in (({"name": "Kitchen"}, False), ({"name": "Kitchen", "second_player": False}, True)):
        root = tmp_path / str(kept)
        root.mkdir()
        flow, net, _, _, upload, _ = _with_backup(root, FakeNM(devices=NOTHING), values=CONNECTED)
        flow.take_backup(upload)
        flow.save({"ssid": "Home", "password": "hunter22", **answers})
        asyncio.run(_finish_told(flow, net))
        for key in ("beszel.enabled", "beszel.hub", "beszel.key", "beszel.token", "plexamp.claim_token"):
            assert (_restored(root, key) is not None) is kept, (key, answers)
        assert _restored(root, "plexamp.enabled") is True
        assert _restored(root, "device_name") == "Kitchen"


def test_a_plugin_switched_on_in_the_review_stays_on_a_second_player(tmp_path):
    flow, net, _, _, upload, _ = _with_backup(tmp_path, FakeNM(devices=NOTHING), values=CONNECTED, plugins=PLUGINS)
    flow.take_backup(upload)
    flow.save({"ssid": "Home", "password": "hunter22", "name": "Kitchen", "plugins": ["beszel"]})
    asyncio.run(_finish_told(flow, net))
    assert _restored(tmp_path, "beszel.enabled") is True and _restored(tmp_path, "beszel.hub") is None


def test_a_restore_applies_its_answers_with_a_real_store(tmp_path):
    """0.9.5 on a new card, 2026-10-08: the answers were applied after the
    settings file was replaced, and the store the core held open refused
    every write - the name, the time zone, the screen never applied. With a
    real store: they are applied, and a name changed in setup goes over the
    backup's own name file after the files are back."""
    from gexis_core.settings import SettingsStore
    from gexis_core.settings_registry import Settings, load_registry

    calls = []
    card = tmp_path / "card"
    (card / "var/lib/gexis-core").mkdir(parents=True)
    store = SettingsStore(card / "var/lib/gexis-core/settings.db")
    settings = Settings(store, registry=load_registry(), seed_path=tmp_path / "none.json",
                        defaults={"device_name": lambda: "raspberrypi"},
                        wired={"device_name": lambda v: calls.append(("set", "device_name", v)),
                               "timezone": lambda v: calls.append(("set", "timezone", v))})
    base = tmp_path / "setup"
    base.mkdir()
    flow, net, _, _, upload, _ = _with_backup(base, FakeNM(devices=NOTHING), settings)
    flow._restore_root = card
    flow._rename = lambda name: calls.append(("rename", name, (card / "etc/gexis/device-name.env").read_text()))
    flow.take_backup(upload)
    flow.save({"ssid": "Home", "password": "hunter22", "name": "ShelvesPi"})
    asyncio.run(_finish_told(flow, net))
    assert ("set", "device_name", "ShelvesPi") in calls
    assert ("set", "timezone", "Europe/Berlin") in calls
    rename = [c for c in calls if c[0] == "rename"]
    assert rename and rename[0][1] == "ShelvesPi"
    assert "NAME=gexis" in rename[0][2], "renamed after the backup's own name file came back"
    assert calls.index(("set", "device_name", "ShelvesPi")) < calls.index(rename[0])
