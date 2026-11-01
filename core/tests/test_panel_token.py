"""ADR-0170: the panel proves itself with this boot's token; a plugin calling
the core from loopback does not pass for it."""
from __future__ import annotations

import asyncio
import json
import os
import stat

from aiohttp.test_utils import TestClient, TestServer

from gexis_core import panel_token
from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer

TOKEN = "this-boot"
SENT = {"X-Gexis-Panel": TOKEN}


def test_the_token_is_made_once_and_kept_for_the_boot(tmp_path):
    path = tmp_path / "gexis" / "panel-token"
    first = panel_token.ensure(path, group="no-such-group")
    assert first and len(first) >= 40
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o640
    # A core restart reads the same one: the kiosk keeps the page it opened.
    assert panel_token.ensure(path) == first


def test_none_when_it_cannot_be_made(tmp_path):
    (tmp_path / "taken").write_text("")
    assert panel_token.ensure(tmp_path / "taken" / "panel-token") is None


async def test_loopback_without_the_token_is_not_the_panel():
    server = StateServer(StateStore({}), panel_token=TOKEN)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await (await client.get("/surface")).json())["surface"] == "remote"
        assert (await client.post("/touch")).status == 403
        assert (await client.post("/touch", headers={"X-Gexis-Panel": "guessed"})).status == 403
        assert (await client.post("/renderers/park")).status == 403
        assert (await client.post("/panel/shown", json={"idle": True})).status == 403
        assert (await (await client.get("/surface", headers=SENT)).json())["surface"] == "panel"
        assert (await client.post("/touch", headers=SENT)).status == 200


async def test_a_server_without_a_token_goes_by_loopback_as_before():
    server = StateServer(StateStore({}))
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await (await client.get("/surface")).json())["surface"] == "panel"


async def test_the_phone_s_typing_reaches_only_the_panel_that_proves_itself():
    server = StateServer(StateStore({}), panel_token=TOKEN)
    client = TestClient(TestServer(server.make_app()))
    await client.start_server()
    try:
        panel = await client.ws_connect(f"/touchpad?panel={TOKEN}")
        plugin = await client.ws_connect("/touchpad")   # loopback, no token: a phone
        phone = await client.ws_connect("/touchpad")
        await asyncio.sleep(0.05)
        await phone.send_str(json.dumps({"t": "text", "text": "a password"}))
        got = await panel.receive(timeout=0.5)
        assert json.loads(got.data) == {"t": "text", "text": "a password"}
        try:
            heard = await plugin.receive(timeout=0.3)
        except asyncio.TimeoutError:
            heard = None
        assert heard is None
    finally:
        await client.close()
