"""**ADR-0178 decision 2: over its setup network, a player already set up
only joins a Wi-Fi network.** Two minutes off its Wi-Fi opened the setup
network with the printed password, and everything answered there: Settings
and their tokens, backups, a plugin upload, a factory reset. A new player is
set up there whole, as before."""
from __future__ import annotations

import pytest
from aiohttp.test_utils import TestClient, TestServer

from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer

from test_setup_network import NOTHING, FakeNM
from test_setup_screen import FakeSetup
from test_setup_flow import make


def _server(tmp_path, needed, over_setup_network=True):
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    (tmp_path / "ui" / "assets").mkdir(parents=True)
    (tmp_path / "ui" / "index.html").write_text("<html></html>")
    (tmp_path / "ui" / "assets" / "index-abc.js").write_text("//")
    server = StateServer(StateStore({}), setup=FakeSetup(needed=needed), setup_flow=flow, ui_dir=tmp_path / "ui")
    server._over_setup_network = lambda request: over_setup_network
    return server


@pytest.mark.asyncio
async def test_a_set_up_player_answers_only_setup_over_its_setup_network(tmp_path):
    server = _server(tmp_path, needed=False)
    async with TestClient(TestServer(server.make_app())) as client:
        for path in ("/", "/assets/index-abc.js", "/setup/status", "/setup/answers"):
            assert (await client.get(path)).status == 200, path
        assert (await client.get("/setup/networks")).status != 403
        assert (await client.post("/setup/answers", json={"ssid": "NewRouter"})).status != 403
        refused = [("GET", "/settings"), ("GET", "/backups/gexis-x-20261110-120000.tgz"), ("GET", "/setup/plugins"),
                   ("GET", "/setup/outputs"), ("GET", "/setup/screen"), ("POST", "/setup/backup"),
                   ("POST", "/settings/factory_reset"), ("POST", "/plugins/upload"), ("POST", "/volume"),
                   ("POST", "/backups"), ("GET", "/api")]
        for method, path in refused:
            r = await client.request(method, path)
            assert r.status == 403, (method, path, r.status)
        assert "Wi-Fi" in (await r.json())["error"]


@pytest.mark.asyncio
async def test_a_new_player_is_set_up_whole_over_its_setup_network(tmp_path):
    server = _server(tmp_path, needed=True)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.get("/setup/outputs")).status != 403
        assert (await client.get("/settings")).status != 403


@pytest.mark.asyncio
async def test_the_home_network_is_not_limited(tmp_path):
    server = _server(tmp_path, needed=False, over_setup_network=False)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.get("/settings")).status != 403
