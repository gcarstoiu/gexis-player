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
