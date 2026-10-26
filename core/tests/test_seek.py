"""ADR-0164 C2: seeking, for the phone's remote on a player without a screen.
A renderer declares `seek`; the route takes a position in seconds and sends
it to whoever holds the device, while the track has a known duration."""
from __future__ import annotations

import pytest
from aiohttp.test_utils import TestClient, TestServer

from gexis_core.adapters.base import Capabilities, VolumeMechanism
from gexis_core.adapters.lms import LmsAdapter
from gexis_core.adapters.plugin import PluginAdapter
from gexis_core.adapters.spotify import SpotifyAdapter
from gexis_core.model import TrackMetadata
from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer

from test_lms_adapter import _adapter as _lms
from test_plugin_adapter import FakeSession


def _caps(controls=("play", "pause", "seek")) -> dict[str, Capabilities]:
    return {"lms": Capabilities(
        audio_connection="output",
        acquisition_events=frozenset({"acquired"}),
        supports_artwork=True,
        supports_sample_rate=True,
        volume_managed=True,
        volume_mechanism=VolumeMechanism.SOFTWARE_API,
        controls=frozenset(controls),
    )}


def _store(duration):
    store = StateStore(_caps())
    store.set_active("lms")
    store.set_metadata("lms", TrackMetadata(title="Song", position=10.0, duration=duration))
    return store


def test_a_seek_needs_a_known_duration():
    assert "seek" in _store(200.0).state.controls["available"]
    assert "seek" not in _store(None).state.controls["available"], "a live stream has nowhere to go"
    assert "seek" not in _store(0.0).state.controls["available"]


@pytest.mark.asyncio
async def test_the_route_sends_the_position_in_seconds_and_stops_at_the_end():
    sent = []

    async def transport(renderer_id, command, argument=None):
        sent.append((renderer_id, command, argument))
        return True

    server = StateServer(_store(200.0), transport=transport)
    async with TestClient(TestServer(server.make_app())) as client:
        ok = await client.post("/transport/seek", json={"position": 83})
        end = await client.post("/transport/seek", json={"position": 250.5})
        bad = [await client.post("/transport/seek", json=body)
               for body in ({"position": -1}, {"position": True}, {"position": "1:23"}, {})]
        none = await client.post("/transport/seek")

    assert (ok.status, end.status) == (200, 200)
    assert [r.status for r in bad] == [400] * 4 and none.status == 400
    assert sent == [("lms", "seek", 83.0), ("lms", "seek", 200.0)]


@pytest.mark.asyncio
async def test_without_a_duration_the_route_refuses():
    async def transport(renderer_id, command, argument=None):
        raise AssertionError("must not be called")

    server = StateServer(_store(None), transport=transport)
    async with TestClient(TestServer(server.make_app())) as client:
        resp = await client.post("/transport/seek", json={"position": 5})
    assert resp.status == 409


@pytest.mark.asyncio
async def test_lyrion_seeks_with_time(monkeypatch):
    adapter, rpc = _lms(monkeypatch, mode="play")
    assert "seek" in LmsAdapter.capabilities.controls
    await adapter.seek(83.456)
    assert [c for c in rpc.commands if c[0] != "status"] == [["time", "83.46"]]


@pytest.mark.asyncio
async def test_spotify_seeks_in_milliseconds(monkeypatch):
    adapter = SpotifyAdapter("127.0.0.1", 3678)
    posted = []

    async def post(action, body=None):
        posted.append((action, body))
        return True

    monkeypatch.setattr(adapter, "_post_player", post)
    assert "seek" in SpotifyAdapter.capabilities.controls
    assert await adapter.seek(83.456)
    assert posted == [("seek", {"position": 83456, "relative": False})]


@pytest.mark.asyncio
async def test_a_plugin_may_declare_seek_and_is_sent_the_position():
    session = FakeSession({"capabilities": {"controls": ["play", "pause", "seek"]}})
    adapter = PluginAdapter(session, signal_unit=lambda unit, force: None)
    assert "seek" in adapter.capabilities.controls
    assert await adapter.seek(12.5)
    assert session.sent[-1] == ("transport", {"command": "seek", "argument": 12.5})
