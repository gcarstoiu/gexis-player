"""ADR-0170: the panel proves itself with this boot's token; a plugin calling
the core from loopback does not pass for it."""
from __future__ import annotations

import asyncio
import json
import os
import re
import stat
from pathlib import Path

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


REPO = Path(__file__).resolve().parents[2]


def _panel_routes() -> set[str]:
    """Every route whose handler asks `_from_panel`, to the first `{`."""
    source = (REPO / "core/src/gexis_core/wsserver.py").read_text()
    asks = {name for name, body in re.findall(
        r"\n    async def (_handle_\w+)\(self[^\n]*\n(.*?)(?=\n    (?:async )?def |\Z)", source, re.S)
        if "self._from_panel(request)" in body}
    return {path.split("{")[0] for path, name in re.findall(r'add_\w+\("([^"]+)", self\.(\w+)\)', source)
            if name in asks}


def test_every_script_on_the_device_that_calls_the_panel_s_routes_sends_the_token():
    """The visualiser's touch report and the update's stop were missed when
    the token came in (found on sofapi, 2026-11-02): each was refused."""
    routes = _panel_routes()
    assert {"/touch", "/renderers/park", "/touchpad"} <= routes
    missing = []
    for path in [*(REPO / "image").rglob("*"), *(REPO / "core/updater").rglob("*")]:
        # Scripts and units only: `image/` may hold a built card.
        if not path.is_file() or path.stat().st_size > 1 << 20:
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        if "127.0.0.1:8090" not in text:
            continue
        calls = [r for r in routes if re.search(re.escape(r) + r"(?![\w-])", text)]
        if calls and "/run/gexis/panel-token" not in text:
            missing.append((str(path.relative_to(REPO)), sorted(calls)))
    assert missing == []
