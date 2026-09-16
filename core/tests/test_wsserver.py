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
        resp = await client.post("/renderer/qobuz/activate")

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

    async def transport(renderer_id, command):
        sent.append((renderer_id, command))
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

    async def transport(renderer_id, command):
        raise AssertionError("must not be called")

    server = StateServer(store, transport=transport)
    async with TestClient(TestServer(server.make_app())) as client:
        resp = await client.post(path)

    assert resp.status == status


@pytest.mark.asyncio
async def test_transport_reports_a_renderer_refusal():
    store = StateStore(_transport_caps("bluetooth"))
    store.set_active("bluetooth")

    async def transport(renderer_id, command):
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

    assert msg["controls"] == {"available": ["pause", "play"]}  # activate is not transport
    assert "unavailable" not in msg["metadata"]


@pytest.mark.asyncio
async def test_a_command_that_cannot_work_now_is_refused():
    store = StateStore(_transport_caps("lms", ("play", "pause", "next", "previous")))
    store.set_active("lms")
    store.set_metadata("lms", TrackMetadata(title="Radio", unavailable=frozenset({"next"})))

    async def transport(renderer_id, command):
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
