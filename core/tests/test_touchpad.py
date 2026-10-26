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
        # ADR-0164 C5: the D-pad's ring on a text field; ADR-0157's untyped.
        for said in ({"t": "ring", "field": True}, {"t": "untyped"}):
            await panel.send_str(json.dumps(said))
            assert await _next(phone) == said
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


async def test_scrolling_and_zooming_reach_the_panel_and_a_phone_leaving_is_said():
    """ADR-0121 §2, amended: two fingers scroll and zoom; a phone gone is
    told to the panel, which zooms back out."""
    server = StateServer(StateStore({}), settings=Settings())
    client, panel, phone = await _pair(server)
    try:
        await phone.send_str(json.dumps({"t": "scroll", "dx": 0, "dy": -40}))
        assert await _next(panel) == {"t": "scroll", "dx": 0, "dy": -40}
        await phone.send_str(json.dumps({"t": "zoom", "by": 1.1}))
        assert await _next(panel) == {"t": "zoom", "by": 1.1}
        await phone.close()
        assert await _next(panel) == {"t": "gone", "phones": 0}
    finally:
        await client.close()


async def test_a_ping_is_answered_to_its_sender_alone_even_while_off():
    """George, 2026-10-14: the touchpad "loses connection when inactive". A
    socket that died without a close still reads open; only an answer that
    stops coming tells the phone to open a new one."""
    server = StateServer(StateStore({}), settings=Settings(on=False))
    client, panel, phone = await _pair(server)
    try:
        await phone.send_str('{"t":"ping"}')
        assert await _next(phone) == {"t": "pong"}
        assert await _next(panel) is None, "not relayed"
    finally:
        await client.close()


def test_wifi_power_saving_is_off_on_a_player():
    """George, 2026-10-14: the pointer "choppy sometimes". On sofapi, round
    trips from idle spiked to 85-98 ms with power saving on, 10-11 ms at most
    with it off."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    conf = (root / "image/stage-gexis/03-core/files/gexis-wifi-powersave.conf").read_text()
    assert "[connection]" in conf and "wifi.powersave = 2" in conf
    build = (root / "packaging/system/build.sh").read_text()
    assert "/etc/NetworkManager/conf.d/gexis-wifi-powersave.conf" in build
    assert "set power_save off" in build
