"""Integration tests for the state WebSocket (Phase 3 criterion 1).

DEVELOPMENT.md: Phase 3 is "tested with a WebSocket client" - these use a
real `aiohttp` WebSocket client against a real (ephemeral-port) server via
`aiohttp.test_utils`, not a mock of the transport, while staying tier-1
(no hardware, no external network).
"""
from __future__ import annotations

import pytest
from aiohttp.test_utils import TestClient, TestServer

from gexis_core.adapters.base import Capabilities, VolumeMechanism
from gexis_core.model import TrackMetadata
from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer


def _caps(*renderer_ids: str) -> dict[str, Capabilities]:
    return {
        rid: Capabilities(
            audio_connection="output",
            acquisition_events=frozenset({"acquired"}),
            supports_artwork=True,
            supports_sample_rate=True,
            volume_managed=True,
            volume_mechanism=VolumeMechanism.SOFTWARE_API,
        )
        for rid in renderer_ids
    }


@pytest.mark.asyncio
async def test_new_client_receives_the_current_state_on_connect():
    store = StateStore(_caps("lms", "spotify", "bluetooth"))
    store.set_active("lms")
    store.set_available("lms", True)
    store.set_metadata("lms", TrackMetadata(title="Song", artist="Artist", source_type="lms"))
    server = StateServer(store)

    async with TestClient(TestServer(server.make_app())) as client:
        async with client.ws_connect("/state") as ws:
            msg = await ws.receive_json()

    assert msg["active"] == "lms"
    assert msg["available"]["lms"] is True
    assert msg["metadata"]["title"] == "Song"
    assert msg["metadata"]["artist"] == "Artist"
    assert msg["capabilities"]["lms"] == {
        "audio_connection": "output",
        "acquisition_events": ["acquired"],
        "supports_artwork": True,
        "supports_sample_rate": True,
        "sample_rate_is_source": False,
        "volume_managed": True,
        "volume_mechanism": "software_api",
        "dummy_mixer_card": None,
        "controls": [],
    }


@pytest.mark.asyncio
async def test_a_state_change_is_pushed_to_a_connected_client():
    store = StateStore(_caps("lms", "spotify", "bluetooth"))
    server = StateServer(store)

    async with TestClient(TestServer(server.make_app())) as client:
        async with client.ws_connect("/state") as ws:
            await ws.receive_json()  # the initial snapshot, nobody active

            store.set_active("spotify")

            msg = await ws.receive_json()

    assert msg["active"] == "spotify"


@pytest.mark.asyncio
async def test_multiple_clients_all_receive_a_broadcast():
    store = StateStore(_caps("lms"))
    server = StateServer(store)

    async with TestClient(TestServer(server.make_app())) as client:
        async with client.ws_connect("/state") as ws1, client.ws_connect("/state") as ws2:
            await ws1.receive_json()
            await ws2.receive_json()

            store.set_active("lms")

            msg1 = await ws1.receive_json()
            msg2 = await ws2.receive_json()

    assert msg1["active"] == "lms"
    assert msg2["active"] == "lms"


@pytest.mark.asyncio
async def test_a_change_before_any_client_connects_is_not_lost():
    """The broadcast-only path (`_broadcast`) would have nobody to send to
    for a change that happens before the first connection - `_handle`
    sending the *current* state on connect, not just future broadcasts, is
    what makes a late-connecting client see it anyway."""
    store = StateStore(_caps("lms"))
    server = StateServer(store)
    store.set_active("lms")  # changes before any client ever connects

    async with TestClient(TestServer(server.make_app())) as client:
        async with client.ws_connect("/state") as ws:
            msg = await ws.receive_json()

    assert msg["active"] == "lms"


# --- Phase 4 / ADR-0028: the REST command surface -------------------------


def _activatable_caps(renderer_id: str) -> dict[str, Capabilities]:
    caps = _caps(renderer_id)
    return {
        renderer_id: Capabilities(
            audio_connection="output",
            acquisition_events=frozenset({"power_on"}),
            supports_artwork=True,
            supports_sample_rate=True,
            volume_managed=True,
            volume_mechanism=VolumeMechanism.DUMMY_MIXER,
            controls=frozenset({"activate"}),
        )
    }


@pytest.mark.asyncio
async def test_activate_calls_through_and_reports_success():
    store = StateStore(_activatable_caps("lms"))
    called = []

    async def activate(renderer_id):
        called.append(renderer_id)
        return True

    server = StateServer(store, activate=activate)
    async with TestClient(TestServer(server.make_app())) as client:
        resp = await client.post("/renderer/lms/activate")

    assert resp.status == 200
    assert called == ["lms"]


@pytest.mark.asyncio
async def test_activate_reports_an_upstream_failure_rather_than_pretending():
    """ADR-0020's rule applied to a command: "LMS unreachable" has to reach
    the caller, which is the whole reason ADR-0028 chose REST over the
    socket."""
    store = StateStore(_activatable_caps("lms"))

    async def activate(renderer_id):
        return False

    server = StateServer(store, activate=activate)
    async with TestClient(TestServer(server.make_app())) as client:
        resp = await client.post("/renderer/lms/activate")
        # Read inside the context: the body is a stream, and the connection
        # is gone once the client closes.
        body = await resp.json()

    assert resp.status == 502
    assert "did not activate" in body["error"]


@pytest.mark.asyncio
async def test_activating_a_renderer_that_declares_no_such_control_is_refused():
    """Spotify and Bluetooth are taken over by a phone connecting, never by
    us asking - so the request is a category error, not a failure."""
    store = StateStore(_caps("spotify"))  # no controls declared

    async def activate(renderer_id):
        raise AssertionError("must not be called")

    server = StateServer(store, activate=activate)
    async with TestClient(TestServer(server.make_app())) as client:
        resp = await client.post("/renderer/spotify/activate")

    assert resp.status == 409


@pytest.mark.asyncio
async def test_activating_an_unknown_renderer_is_a_404():
    store = StateStore(_caps("lms"))

    async def activate(renderer_id):
        raise AssertionError("must not be called")

    server = StateServer(store, activate=activate)
    async with TestClient(TestServer(server.make_app())) as client:
        resp = await client.post("/renderer/example/activate")

    assert resp.status == 404


@pytest.mark.asyncio
async def test_volume_accepts_a_percent_and_passes_it_on():
    store = StateStore(_caps("lms"))
    got = []

    async def set_volume(percent):
        got.append(percent)
        return True

    server = StateServer(store, set_volume=set_volume)
    async with TestClient(TestServer(server.make_app())) as client:
        resp = await client.post("/volume", json={"percent": 42})

    assert resp.status == 200
    assert got == [42.0]


@pytest.mark.asyncio
async def test_volume_rejects_a_missing_or_out_of_range_percent():
    store = StateStore(_caps("lms"))

    async def set_volume(percent):
        raise AssertionError("must not be called")

    server = StateServer(store, set_volume=set_volume)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.post("/volume", json={})).status == 400
        assert (await client.post("/volume", json={"percent": 101})).status == 400
        assert (await client.post("/volume", json={"percent": -1})).status == 400
        assert (await client.post("/volume", json={"percent": "loud"})).status == 400


@pytest.mark.asyncio
async def test_commands_answer_503_when_nothing_is_wired_up():
    """A truer answer than 404 for a server that has the concept but no
    wiring behind it."""
    store = StateStore(_activatable_caps("lms"))
    server = StateServer(store)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.post("/renderer/lms/activate")).status == 503
        assert (await client.post("/volume", json={"percent": 50})).status == 503


@pytest.mark.asyncio
async def test_the_socket_is_still_publish_only():
    """ADR-0028: commands are POSTs by decision. A client sending on the
    socket must be ignored without desyncing the connection."""
    store = StateStore(_caps("lms"))
    server = StateServer(store)

    async with TestClient(TestServer(server.make_app())) as client:
        async with client.ws_connect("/state") as ws:
            await ws.receive_json()
            await ws.send_str('{"command": "activate"}')
            store.set_active("lms")
            msg = await ws.receive_json()

    assert msg["active"] == "lms"


# --- Phase 4b: serving the UI (ADR-0028) ----------------------------------


def _ui_build(tmp_path):
    """A minimal stand-in for vite's output: index.html plus assets/."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><div id=app></div>")
    (tmp_path / "assets" / "index-abc123.js").write_text("console.log('gexis')")
    return tmp_path


@pytest.mark.asyncio
async def test_index_and_assets_are_served(tmp_path):
    store = StateStore(_caps("lms"))
    server = StateServer(store, ui_dir=_ui_build(tmp_path))

    async with TestClient(TestServer(server.make_app())) as client:
        index = await client.get("/")
        index_body = await index.text()
        asset = await client.get("/assets/index-abc123.js")
        asset_body = await asset.text()

    assert index.status == 200
    assert "id=app" in index_body
    assert asset.status == 200
    assert "gexis" in asset_body


@pytest.mark.asyncio
async def test_serving_the_ui_does_not_shadow_the_api(tmp_path):
    """The reason the UI is registered last and on two narrow routes: a
    greedy static mount would swallow /state and the command routes."""
    store = StateStore(_caps("lms"))
    server = StateServer(store, ui_dir=_ui_build(tmp_path))

    async with TestClient(TestServer(server.make_app())) as client:
        async with client.ws_connect("/state") as ws:
            msg = await ws.receive_json()
        volume = await client.post("/volume", json={"percent": 50})

    assert msg["active"] is None          # the socket, not index.html
    assert volume.status == 503           # the command route, not a 404 from static


@pytest.mark.asyncio
async def test_no_ui_build_means_api_only():
    """Every deployment before Phase 4b, and any core-only development
    install: the daemon must serve the API perfectly well with no UI."""
    store = StateStore(_caps("lms"))
    server = StateServer(store)

    async with TestClient(TestServer(server.make_app())) as client:
        index = await client.get("/")
        async with client.ws_connect("/state") as ws:
            msg = await ws.receive_json()

    assert index.status == 404
    assert msg["active"] is None


# --- ADR-0037: transport ---------------------------------------------------


def _transport_caps(renderer_id: str, controls=("play", "pause")) -> dict[str, Capabilities]:
    return {
        renderer_id: Capabilities(
            audio_connection="output",
            acquisition_events=frozenset({"acquired"}),
            supports_artwork=True,
            supports_sample_rate=True,
            volume_managed=True,
            volume_mechanism=VolumeMechanism.SOFTWARE_API,
            controls=frozenset(controls),
        )
    }


@pytest.mark.asyncio
async def test_transport_goes_to_the_active_renderer():
    store = StateStore(_transport_caps("spotify"))
    store.set_active("spotify")
    sent = []

    async def transport(renderer_id, command, argument=None):
        sent.append((renderer_id, command, argument) if argument is not None else (renderer_id, command))
        return True

    server = StateServer(store, transport=transport)
    async with TestClient(TestServer(server.make_app())) as client:
        resp = await client.post("/transport/pause")
        body = await resp.json()

    assert resp.status == 200
    assert sent == [("spotify", "pause")]
    assert body == {"sent": "pause", "renderer": "spotify"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("active", "controls", "path", "status"),
    [
        (None, ("play", "pause"), "/transport/play", 409),       # nothing active
        ("spotify", ("play",), "/transport/pause", 409),        # not declared
        ("spotify", ("play", "pause"), "/transport/seek", 404), # not a command
    ],
)
async def test_transport_refuses_what_cannot_be_sent(active, controls, path, status):
    store = StateStore(_transport_caps("spotify", controls))
    if active:
        store.set_active(active)

    async def transport(renderer_id, command, argument=None):
        raise AssertionError("must not be called")

    server = StateServer(store, transport=transport)
    async with TestClient(TestServer(server.make_app())) as client:
        resp = await client.post(path)

    assert resp.status == status


@pytest.mark.asyncio
async def test_transport_reports_a_renderer_refusal():
    store = StateStore(_transport_caps("bluetooth"))
    store.set_active("bluetooth")

    async def transport(renderer_id, command, argument=None):
        return False

    server = StateServer(store, transport=transport)
    async with TestClient(TestServer(server.make_app())) as client:
        resp = await client.post("/transport/play")

    assert resp.status == 502


@pytest.mark.asyncio
async def test_transport_unwired_answers_503():
    store = StateStore(_transport_caps("lms"))
    store.set_active("lms")
    server = StateServer(store)
    async with TestClient(TestServer(server.make_app())) as client:
        resp = await client.post("/transport/play")

    assert resp.status == 503


@pytest.mark.asyncio
async def test_state_publishes_what_the_active_renderer_can_do_now():
    store = StateStore(_transport_caps("lms", ("activate", "play", "pause", "next", "previous")))
    store.set_active("lms")
    store.set_metadata("lms", TrackMetadata(title="Radio", source_type="lms",
                                            unavailable=frozenset({"next", "previous"})))
    server = StateServer(store)
    async with TestClient(TestServer(server.make_app())) as client:
        async with client.ws_connect("/state") as ws:
            msg = await ws.receive_json()

    # activate is not transport; shuffle and repeat are not declared here
    assert msg["controls"] == {"available": ["pause", "play"], "shuffle": None, "repeat": None}
    assert "unavailable" not in msg["metadata"]


@pytest.mark.asyncio
async def test_a_command_that_cannot_work_now_is_refused():
    store = StateStore(_transport_caps("lms", ("play", "pause", "next", "previous")))
    store.set_active("lms")
    store.set_metadata("lms", TrackMetadata(title="Radio", unavailable=frozenset({"next"})))

    async def transport(renderer_id, command, argument=None):
        raise AssertionError("must not be called")

    server = StateServer(store, transport=transport)
    async with TestClient(TestServer(server.make_app())) as client:
        resp = await client.post("/transport/next")

    assert resp.status == 409


@pytest.mark.asyncio
async def test_nobody_active_publishes_no_controls():
    store = StateStore(_transport_caps("lms"))
    server = StateServer(store)
    async with TestClient(TestServer(server.make_app())) as client:
        async with client.ws_connect("/state") as ws:
            msg = await ws.receive_json()

    assert msg["controls"] is None


@pytest.mark.asyncio
async def test_shuffle_and_repeat_are_published_for_a_renderer_that_declares_them():
    store = StateStore(_transport_caps("lms", ("play", "pause", "shuffle", "repeat")))
    store.set_active("lms")
    store.set_metadata("lms", TrackMetadata(title="Song", shuffle=True, repeat="one"))
    server = StateServer(store)
    async with TestClient(TestServer(server.make_app())) as client:
        async with client.ws_connect("/state") as ws:
            msg = await ws.receive_json()

    assert msg["controls"]["shuffle"] is True
    assert msg["controls"]["repeat"] == "one"


@pytest.mark.asyncio
async def test_shuffle_and_repeat_carry_their_setting_to_the_renderer():
    store = StateStore(_transport_caps("lms", ("shuffle", "repeat")))
    store.set_active("lms")
    sent = []

    async def transport(renderer_id, command, argument=None):
        sent.append((command, argument))
        return True

    server = StateServer(store, transport=transport)
    async with TestClient(TestServer(server.make_app())) as client:
        ok1 = await client.post("/transport/shuffle", json={"on": True})
        ok2 = await client.post("/transport/repeat", json={"mode": "all"})
        bad1 = await client.post("/transport/shuffle", json={"on": "yes"})
        bad2 = await client.post("/transport/repeat", json={"mode": "twice"})
        bad3 = await client.post("/transport/repeat")

    assert (ok1.status, ok2.status) == (200, 200)
    assert (bad1.status, bad2.status, bad3.status) == (400, 400, 400)
    assert sent == [("shuffle", True), ("repeat", "all")]


@pytest.mark.asyncio
async def test_the_index_is_never_cached(tmp_path):
    """A cached index.html pins the panel to a build whose hashed assets
    have been deleted: the kiosk came back on the previous bundle and 404'd
    (2026-09-18)."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>gexis</title>")
    server = StateServer(StateStore({}), ui_dir=tmp_path)

    async with TestClient(TestServer(server.make_app())) as client:
        resp = await client.get("/")

        assert resp.status == 200
        assert resp.headers["Cache-Control"] == "no-store"


@pytest.mark.asyncio
async def test_the_panel_reporting_a_first_frame_drops_the_splash():
    """ADR-0043. The route exists so the boot animation outlives
    multi-user.target and ends on a painted pixel instead."""

    class FakeSplash:
        def __init__(self):
            self.drops = 0

        def drop(self):
            self.drops += 1
            return self.drops == 1

    splash = FakeSplash()
    server = StateServer(StateStore(_caps("lms")), splash=splash)

    async with TestClient(TestServer(server.make_app())) as client:
        first = await client.post("/panel/painted")
        assert first.status == 200
        assert await first.json() == {"painted": True, "splash_dropped": True}

        # A panel that reloads reports again; the daemon says so honestly
        # rather than pretending it dropped a splash twice.
        second = await client.post("/panel/painted")
        assert (await second.json())["splash_dropped"] is False

    assert splash.drops == 2


@pytest.mark.asyncio
async def test_a_daemon_with_no_splash_still_answers_the_panel():
    """Every deployment before this phase, and every development run: the
    panel must not see an error for reporting something true."""
    server = StateServer(StateStore(_caps("lms")))

    async with TestClient(TestServer(server.make_app())) as client:
        response = await client.post("/panel/painted")

    assert response.status == 200


class _Peppy:
    def __init__(self):
        self.touches = 0

    def on_touch(self):
        self.touches += 1


@pytest.mark.asyncio
async def test_the_phones_idle_toggle_reaches_the_panel_and_restarts_the_timers():
    """ADR-0101 (George: "Idle screen should toggle the idle screen on or off.
    Timers would restart from that point")."""
    store = StateStore(_caps("lms"))
    peppy = _Peppy()
    server = StateServer(store, peppy=peppy)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.post("/panel/idle/show")).status == 200
        first = store.state.panel["idle_request"]
        assert first["show"] is True and peppy.touches == 1
        assert (await client.post("/panel/idle/show")).status == 200
        assert store.state.panel["idle_request"]["seq"] == first["seq"] + 1, "the same ask twice is two asks"
        assert (await client.post("/panel/idle/hide")).status == 200
        assert store.state.panel["idle_request"]["show"] is False and peppy.touches == 3
        assert (await client.post("/panel/idle/sideways")).status == 404


@pytest.mark.asyncio
async def test_the_panel_says_whether_its_idle_screen_is_up():
    store = StateStore(_caps("lms"))
    server = StateServer(store)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.post("/panel/shown", json={"idle": True})).status == 200
        assert store.state.panel["idle"] is True
        assert (await client.post("/panel/shown", json={})).status == 400
        async with client.ws_connect("/state") as ws:
            assert (await ws.receive_json())["panel"]["idle"] is True


@pytest.mark.asyncio
async def test_the_phones_home_now_playing_and_lyrics_reach_the_panel():
    """ADR-0101 as amended 2026-10-05: each ask numbered and counted as
    attention; Now playing, Lyrics and Track refused while nothing plays."""
    store = StateStore(_caps("lms"))
    peppy = _Peppy()
    server = StateServer(store, peppy=peppy)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.post("/panel/go/home")).status == 200
        first = store.state.panel["view_request"]
        assert first["to"] == "home" and peppy.touches == 1
        for to in ("now", "lyrics", "track", "minimise"):
            assert (await client.post(f"/panel/go/{to}")).status == 409, f"{to} with nothing playing"
        assert store.state.panel["view_request"] == first
        store.set_active("lms")
        assert (await client.post("/panel/go/lyrics")).status == 200
        ask = store.state.panel["view_request"]
        assert ask["to"] == "lyrics" and ask["seq"] == first["seq"] + 1
        assert (await client.post("/panel/go/sideways")).status == 404


@pytest.mark.asyncio
async def test_the_panel_says_whether_its_lyrics_are_shown():
    store = StateStore(_caps("lms"))
    server = StateServer(store)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.post("/panel/shown", json={"lyrics": True})).status == 200
        assert store.state.panel["lyrics"] is True and store.state.panel["idle"] is False
        assert (await client.post("/panel/shown", json={"idle": True, "lyrics": False})).status == 200
        assert store.state.panel["idle"] is True and store.state.panel["lyrics"] is False
        # ADR-0122: whether Now Playing is up, for the phone's toggle.
        assert (await client.post("/panel/shown", json={"now": True})).status == 200
        assert store.state.panel["now"] is True


@pytest.mark.asyncio
async def test_the_web_app_manifest_and_icons_are_served_at_the_root(tmp_path):
    """ADR-0102 (a test): a phone installs Settings from these."""
    from gexis_core.wsserver import APP_FILES
    ui = _ui_build(tmp_path)
    for name in APP_FILES:
        (ui / name).write_bytes(b"x")
    server = StateServer(StateStore({}), ui_dir=ui)
    async with TestClient(TestServer(server.make_app())) as client:
        response = await client.get("/manifest.webmanifest")
        assert response.status == 200
        assert response.headers["Content-Type"].startswith("application/manifest+json")
        assert (await client.get("/app-icon-192.png")).headers["Content-Type"] == "image/png"
        assert (await client.get("/anything-else.png")).status == 404, "named, not a catch-all"


@pytest.mark.asyncio
async def test_park_pauses_through_the_callable():
    """George, 2026-09-29: a fresh start after every restart. The shutdown's
    unit calls this over loopback."""
    called = []

    async def park():
        called.append(True)
        return True

    server = StateServer(StateStore({}), park=park)
    async with TestClient(TestServer(server.make_app())) as client:
        resp = await client.post("/renderers/park")
        body = await resp.json()
    assert resp.status == 200 and body == {"parked": True} and called == [True]


@pytest.mark.asyncio
async def test_a_plugin_upload_reaches_the_installer_and_a_refusal_says_why():
    """ADR-0106: the package is the request body; a refusal comes back as
    words a person can act on."""
    from gexis_core import uploads
    got = []

    async def upload(data):
        got.append(data)
        if data == b"bad":
            raise uploads.Refused("plugin.json is not at the top of the package")
        return {"installed": "radiofoo", "version": "1.0.0", "kind": "renderer", "restarting": True}

    server = StateServer(StateStore({}), upload_plugin=upload)
    async with TestClient(TestServer(server.make_app())) as client:
        ok = await client.post("/plugins/upload", data=b"tarball-bytes")
        ok_body = await ok.json()
        bad = await client.post("/plugins/upload", data=b"bad")
        bad_body = await bad.json()
    assert ok.status == 200 and ok_body["installed"] == "radiofoo" and got[0] == b"tarball-bytes"
    assert bad.status == 400 and "plugin.json is not at the top" in bad_body["error"]


@pytest.mark.asyncio
async def test_uninstall_is_only_for_uploaded_plugins():
    async def uninstall(plugin_id):
        return plugin_id == "radiofoo"

    server = StateServer(StateStore({}), uninstall_plugin=uninstall)
    async with TestClient(TestServer(server.make_app())) as client:
        ok = await client.post("/plugins/radiofoo/uninstall")
        ours = await client.post("/plugins/lms/uninstall")
    assert ok.status == 200 and ours.status == 404


@pytest.mark.asyncio
async def test_a_second_show_while_the_visualiser_is_starting_again_waits_for_it(monkeypatch):
    """Review, 2026-10-12: nothing marked a restart as under way, so a second
    tap during the ~9 s the skins take to load restarted the unit again and
    killed the half-loaded one. The second ask now waits for the first."""
    from gexis_core import wsserver

    restarts = []

    async def started(*args, **kw):
        restarts.append(args)

        class _Done:
            async def wait(self):
                return 0
        return _Done()

    class _Slow:
        """No window until three looks after the restart."""
        def __init__(self):
            self.looks = 0

        def _has_levels(self):
            return True

        def request(self, action):
            if restarts:
                self.looks += 1
            return self.looks >= 3

        async def request_async(self, action):
            return self.request(action)

    import asyncio
    real_sleep = asyncio.sleep

    async def quick(_s):
        await real_sleep(0.01)  # the 1.5 s between looks, shortened

    monkeypatch.setattr(wsserver.asyncio, "create_subprocess_exec", started)
    server = StateServer(StateStore(_caps("lms")), peppy=_Slow())
    monkeypatch.setattr(wsserver.asyncio, "sleep", quick)
    async with TestClient(TestServer(server.make_app())) as client:
        first, second = await asyncio.gather(client.post("/peppy/show"), client.post("/peppy/show"))
    assert (first.status, second.status) == (200, 200)
    assert len(restarts) == 1, "one restart, however many asked"


class _PeppyWithoutWindow:
    """No window at first; shown once it has been started again, and saying
    so the way the real one does - `on_change` into the state store."""

    def __init__(self, store):
        self._store = store
        self.asked = 0

    def _has_levels(self):
        return True

    def request(self, action):
        self.asked += 1
        if self.asked == 1:
            return False
        self._store.set_panel(visualiser=True)
        return True

    async def request_async(self, action):
        # As the real one: worked off the loop, published back on it.
        return self.request(action)


@pytest.mark.asyncio
async def test_a_visualiser_started_again_is_shown_and_answered(monkeypatch):
    """**The first visualiser of the evening answered 500** (sofapi,
    2026-10-11): the window was gone, the core started it again, and showing
    it was asked from a worker thread - whose state change reached the phones
    through `create_task`, which needs the event loop. The visualiser came
    up; the answer was an error."""
    from gexis_core import wsserver

    async def started(*args, **kw):
        class _Done:
            async def wait(self):
                return 0
        return _Done()

    monkeypatch.setattr(wsserver.asyncio, "create_subprocess_exec", started)
    store = StateStore(_caps("lms"))
    peppy = _PeppyWithoutWindow(store)
    server = StateServer(store, peppy=peppy)
    async with TestClient(TestServer(server.make_app())) as client:
        async with client.ws_connect("/state") as phone:
            await phone.receive_json()
            response = await client.post("/peppy/show")
            assert response.status == 200
            assert (await phone.receive_json())["panel"]["visualiser"] is True


# -- a body or a failure a route did not expect (review, 2026-10-12) --------


@pytest.mark.asyncio
async def test_a_body_of_the_wrong_shape_is_a_400_not_a_500(tmp_path, monkeypatch):
    """Each of these answered a generic 500 where the sheet could have said
    something: a JSON list where an object belongs, an id of Infinity."""
    from types import SimpleNamespace

    from gexis_core import problem_report
    from gexis_core.settings import SettingsStore
    from gexis_core.settings_registry import Settings

    class Port:
        pending, changing = None, False

        async def change(self, *args):
            return {"address": None, "until": 0}

    monkeypatch.setattr(problem_report, "build", lambda note, *a, **k: SimpleNamespace(
        name="report.zip", data=note.encode(), summary="nothing"))
    settings = Settings(SettingsStore(tmp_path / "s.db"), registry=[])
    server = StateServer(StateStore(_caps("lms")), cable=Port(), wifi_address=Port(),
                         library=object(), settings=settings)
    async with TestClient(TestServer(server.make_app())) as client:
        for path in ("/network/cable", "/network/wifi/address"):
            assert (await client.post(path, json=[1])).status == 400, path
        r = await client.post("/library/action", data='{"kind": "album", "id": Infinity}',
                              headers={"Content-Type": "application/json"})
        assert r.status == 400
        r = await client.post("/report", json=[1])
        assert r.status == 200 and await r.read() == b"", "a list carries no note"


@pytest.mark.asyncio
async def test_a_share_browse_that_fails_says_so(tmp_path, monkeypatch):
    """A NAS that takes longer than smbclient's 15 s, a `server` that is a
    string: each was a 500 on the sheet."""
    import subprocess

    from gexis_core import lyrion_scan, lyrion_shares
    from gexis_core.settings import SettingsStore
    from gexis_core.settings_registry import Settings

    registry = [{"id": "g", "label": "G", "rows": [
        {"key": "lyrion-server.shares", "type": "list", "kind": "share", "discover": True}]}]
    store = SettingsStore(tmp_path / "s.db")
    settings = Settings(store, registry=registry, wired={"lyrion-server.shares": None})
    shares = lyrion_shares.Shares(store, root=tmp_path / "mnt", credentials=tmp_path / "cred",
                                  is_mount=lambda p: False)
    asked = []

    def slow(server, user=None, password=None):
        asked.append(server)
        raise subprocess.TimeoutExpired(["smbclient"], 15)

    monkeypatch.setattr(lyrion_scan, "shares", slow)
    server = StateServer(StateStore({}), settings=settings, lyrion_shares=shares)
    url = "/settings/lyrion-server.shares/items"
    async with TestClient(TestServer(server.make_app())) as client:
        r = await client.post(url, json={"name": "Tower", "action": "browse", "server": "abc"})
        assert r.status == 200
        answer = await r.json()
        assert answer["ok"] is False and "Tower" in answer["error"]
        assert asked[0].host == "Tower", "a server that is not an object is the name's"
        monkeypatch.setattr(lyrion_scan, "shares", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("smbclient")))
        r = await client.post(url, json={"name": "Tower", "action": "browse"})
        assert r.status == 200 and (await r.json())["ok"] is False


@pytest.mark.asyncio
async def test_a_truncated_backup_is_refused_with_a_reason(tmp_path, monkeypatch):
    """A backup half-copied into the guest-writable share: tarfile raises
    EOFError reading it, which was a 500 instead of the reason."""
    from gexis_core import backups
    from gexis_core.settings import SettingsStore
    from gexis_core.settings_registry import Settings

    registry = [{"id": "g", "label": "G", "rows": [{"key": "restore", "type": "list"}]}]
    settings = Settings(SettingsStore(tmp_path / "s.db"), registry=registry, wired={"restore": None})

    def truncated(name):
        raise EOFError("Compressed file ended before the end-of-stream marker was reached")

    monkeypatch.setattr(backups, "restore", truncated)

    async def restarted():
        raise AssertionError("nothing restarts for a backup that did not go back")

    server = StateServer(StateStore({}), settings=settings, restore=restarted)
    async with TestClient(TestServer(server.make_app())) as client:
        r = await client.post("/settings/restore/items", json={"name": "gexis-backup.tgz", "action": "join"})
        assert r.status == 200 and (await r.json())["ok"] is False


@pytest.mark.asyncio
async def test_the_updaters_backup_is_named_as_its_own_and_pruned(tmp_path, monkeypatch):
    """George, 2026-10-12, answer 3: `POST /settings/backup?before=update`
    makes an update's backup and keeps the newest three of those."""
    import asyncio

    from gexis_core import backups
    from gexis_core.settings import SettingsStore
    from gexis_core.settings_registry import Settings

    registry = [{"id": "g", "label": "G", "rows": [{"key": "backup", "type": "action"},
                                                    {"key": "device_name", "type": "text"}]}]
    store = SettingsStore(tmp_path / "s.db")
    settings = Settings(store, registry=registry, wired={"backup": lambda _=None: hand.append(1), "device_name": None})
    settings.set("device_name", "Den")
    hand = []
    made, pruned = [], []
    monkeypatch.setattr(backups, "create", lambda name, directory=None, root=None, automatic=False:
                        made.append((name, automatic)) or "gexis-den.before-update-20261012-101500.tgz")
    monkeypatch.setattr(backups, "prune_automatic", lambda name, directory=None: pruned.append(name))
    state = StateStore({})
    server = StateServer(state, settings=settings)
    async with TestClient(TestServer(server.make_app())) as client:
        r = await client.post("/settings/backup?before=update")
        assert r.status == 200
        for _ in range(500):  # 5 s: the prune runs in the background, and a loaded suite was slower than 1 s
            # Both: the Restore list is told after the prune, and GitHub's
            # runner once read it between the two (2026-10-18).
            if pruned and state.state.settings_revision == 1:
                break
            await asyncio.sleep(0.01)
        assert made == [("Den", True)]
        assert pruned == ["gexis-den.before-update-20261012-101500.tgz"]
        assert hand == [], "the row's own backup, taken by hand, is not run"
        assert state.state.settings_revision == 1, "the Restore list is told"
        r = await client.post("/settings/backup")
        assert r.status == 200 and hand == [1]


@pytest.mark.asyncio
async def test_usb_folders_are_browsed_added_and_removed(tmp_path):
    """ADR-0115 decision 23: the sheet lists the drives plugged in; a drive
    opens at its top with *Add the whole drive* first, a folder opens one
    level down with *Back up*; a folder added shows on the row with its
    Remove, and a drive with nothing chosen shows as *Not added yet*."""
    from gexis_core import lyrion_usb
    from gexis_core.settings import SettingsStore
    from gexis_core.settings_registry import Settings

    registry = [{"id": "g", "label": "G", "rows": [
        {"key": "lyrion-server.usb_folders", "type": "list", "kind": "usb-folder"}]}]
    store = SettingsStore(tmp_path / "s.db")
    settings = Settings(store, registry=registry, wired={"lyrion-server.usb_folders": None})
    root = tmp_path / "usb"
    (root / "AAAA" / "Music" / "Jazz").mkdir(parents=True)
    usb = lyrion_usb.UsbFolders(store, root=root, is_mount=lambda p: p.endswith("AAAA"),
                                by_uuid=tmp_path / "none", by_label=tmp_path / "none")
    woken = []
    server = StateServer(StateStore({}), settings=settings, lyrion_usb=usb,
                         lyrion_shares_changed=lambda: woken.append(1))
    url = "/settings/lyrion-server.usb_folders/items"
    async with TestClient(TestServer(server.make_app())) as client:
        drives = (await (await client.get(url)).json())["items"]
        assert [d["drive"] for d in drives] == ["AAAA"] and drives[0]["meta"].startswith("Not added yet")

        top = await (await client.post(url, json={"name": "AAAA", "action": "browse", "folder": ""})).json()
        assert top["ok"] and top["items"][0]["name"] == "Add the whole drive"
        assert [i["name"] for i in top["items"][1:]] == ["Music"] and top["items"][1]["open"]

        music = await (await client.post(url, json={"name": "AAAA", "action": "browse", "folder": "Music"})).json()
        assert [i["name"] for i in music["items"]] == ["Add Music", "Back up", "Jazz"]
        assert music["items"][1]["folder"] == ""

        out = await (await client.post(url, json={"name": "AAAA", "action": "browse", "folder": "../.."})).json()
        assert out["ok"] is False

        added = await (await client.post(url, json={"name": "AAAA", "action": "add", "folder": "Music"})).json()
        assert added["ok"] and woken

        rows = (await (await client.get("/settings")).json())
        row = next(r for g in rows["groups"] for r in g["rows"] if r["key"] == "lyrion-server.usb_folders")
        assert [(i["name"], i["address"]) for i in row["items"]] == [("Music", "AAAA/Music")]

        again = await (await client.post(url, json={"name": "AAAA", "action": "add", "folder": "Music/Jazz"})).json()
        assert again["ok"] is False and "Music" in again["error"]

        gone = await (await client.post(url, json={"name": "AAAA/Music", "action": "forget"})).json()
        assert gone["ok"] and usb.all() == []


@pytest.mark.asyncio
async def test_a_share_opens_into_its_folders_and_the_scan_is_kept_a_minute(tmp_path, monkeypatch):
    """George, 2026-10-18: browsing a share "stops only at level 1", and every
    list of shares waited two seconds for a scan."""
    from gexis_core import lyrion_scan, lyrion_shares
    from gexis_core.settings import SettingsStore
    from gexis_core.settings_registry import Settings

    registry = [{"id": "g", "label": "G", "rows": [
        {"key": "lyrion-server.shares", "type": "list", "kind": "share", "discover": True}]}]
    store = SettingsStore(tmp_path / "s.db")
    settings = Settings(store, registry=registry, wired={"lyrion-server.shares": None})
    shares = lyrion_shares.Shares(store, root=tmp_path / "mnt", credentials=tmp_path / "cred",
                                  is_mount=lambda p: False)
    scans, listed = [], []
    monkeypatch.setattr(lyrion_scan, "servers", lambda own: scans.append(1) or [
        lyrion_scan.Server(name="Tower", host="Tower.local", kind="smb")])
    monkeypatch.setattr(lyrion_scan, "folders", lambda address, user=None, password=None:
                        listed.append((address, user)) or ["Jazz", "Rock"])
    server = StateServer(StateStore({}), settings=settings, lyrion_shares=shares)
    url = "/settings/lyrion-server.shares/items"
    async with TestClient(TestServer(server.make_app())) as client:
        await client.get(url)
        await client.get(url)
        assert len(scans) == 1, "a second list within the minute reuses the scan"
        await client.get(url + "?fresh=1")
        assert len(scans) == 2
        assert (await (await client.get(url + "?saved=1")).json())["items"] == [] and len(scans) == 2

        top = await (await client.post(url, json={"name": "//Tower.local/Music", "action": "folders",
                                                   "user": "george", "password": "pw"})).json()
        assert [i["name"] for i in top["items"]] == ["Add Music", "Jazz", "Rock"]
        assert top["items"][1]["address"] == "//Tower.local/Music/Jazz" and top["items"][1]["open"]
        assert listed[-1] == ("//Tower.local/Music", "george")

        jazz = await (await client.post(url, json={"name": "//Tower.local/Music/Jazz", "action": "folders"})).json()
        assert [i["name"] for i in jazz["items"]][:2] == ["Add Jazz", "Back up"]
        assert jazz["items"][1]["address"] == "//Tower.local/Music"

        nfs = await (await client.post(url, json={"name": "nas:/volume1/music", "action": "folders"})).json()
        assert [i["name"] for i in nfs["items"]] == ["Add music"]


@pytest.mark.asyncio
async def test_the_music_folders_space_is_on_its_row_and_its_route(tmp_path, monkeypatch):
    from gexis_core import lyrion_folders
    from gexis_core.settings import SettingsStore
    from gexis_core.settings_registry import Settings

    monkeypatch.setattr(lyrion_folders, "music_space",
                        lambda music=None: {"free": 1, "total": 2, "text": "51.2 GB free of 58.0 GB"})
    registry = [{"id": "g", "label": "G", "rows": [
        {"key": "lyrion-server.music_folder", "type": "toggle", "label": "Music folder", "note": "The player's own."}]}]
    settings = Settings(SettingsStore(tmp_path / "s.db"), registry=registry, wired={"lyrion-server.music_folder": None})
    server = StateServer(StateStore({}), settings=settings)
    async with TestClient(TestServer(server.make_app())) as client:
        rows = (await (await client.get("/settings")).json())["groups"][0]["rows"]
        assert rows[0]["note"] == "The player's own. 51.2 GB free of 58.0 GB."
        assert (await (await client.get("/storage/music")).json())["text"] == "51.2 GB free of 58.0 GB"
