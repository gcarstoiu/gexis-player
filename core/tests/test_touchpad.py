"""ADR-0121: the touchpad's socket relays between the phones and the panel."""
from __future__ import annotations

import asyncio
import json

from aiohttp.test_utils import TestClient, TestServer

from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer


class Settings:
    def __init__(self, on=True):
        self.on = on

    def value(self, key):
        return self.on if key == "phone_touchpad" else None


async def _pair(server):
    """A panel and a phone on the touchpad socket, told apart in order."""
    sides = iter([True, False])
    server._from_panel = lambda request: next(sides)
    client = TestClient(TestServer(server.make_app()))
    await client.start_server()
    panel = await client.ws_connect("/touchpad")
    phone = await client.ws_connect("/touchpad")
    await asyncio.sleep(0.05)
    return client, panel, phone


async def _next(ws, timeout=0.3):
    try:
        msg = await ws.receive(timeout=timeout)
    except asyncio.TimeoutError:
        return None
    return json.loads(msg.data) if msg.data else None


async def test_a_phone_s_moves_reach_the_panel_and_the_panel_s_field_reaches_the_phone():
    server = StateServer(StateStore({}), settings=Settings())
    client, panel, phone = await _pair(server)
    try:
        await phone.send_str(json.dumps({"t": "move", "dx": 12, "dy": -3}))
        assert await _next(panel) == {"t": "move", "dx": 12, "dy": -3}
        await panel.send_str(json.dumps({"t": "over", "field": True}))
        assert await _next(phone) == {"t": "over", "field": True}
        # Each side may say only its own messages; the rest are dropped.
        await phone.send_str(json.dumps({"t": "over", "field": True}))
        await phone.send_str(json.dumps({"t": "volume", "percent": 100}))
        assert await _next(panel) is None
    finally:
        await client.close()


async def test_nothing_is_relayed_while_the_touchpad_is_off():
    server = StateServer(StateStore({}), settings=Settings(on=False))
    client, panel, phone = await _pair(server)
    try:
        await phone.send_str(json.dumps({"t": "tap"}))
        assert await _next(panel) is None
    finally:
        await client.close()
