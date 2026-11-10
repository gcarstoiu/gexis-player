"""**ADR-0178 decision 1: a browser drives the player only from the player's
own pages.** A web page on another site, open in a browser at home, could
post to the player - a factory reset, the volume, a plugin - and under a
public name pointed at the player's address read what it answers. Programs
that are not browsers (Home Assistant, curl, plugins) are not affected."""
from __future__ import annotations

import aiohttp
import pytest
from aiohttp.test_utils import TestClient, TestServer

from gexis_core import own_pages
from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer

from test_wsserver import _caps

BROWSER = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15"}


@pytest.mark.parametrize("host, own", [
    ("192.0.2.7:8090", True), ("127.0.0.1:8090", True), ("[fe80::1]:8090", True), ("[::1]", True),
    ("localhost:8090", True), ("gexis:8090", True), ("living-room.local:8090", True), ("gexis-2.local", True),
    ("Sofa-Pi.LOCAL.:8090", True),
    ("evil.example:8090", False), ("gexis.home", False), ("192.0.2.7.nip.io:8090", False),
    ("local.evil.example", False), ("", False), ("[", False),
])
def test_the_names_only_the_home_network_can_give(host, own):
    assert own_pages.own_name(host) is own


def _server():
    got = []

    async def set_volume(percent):
        got.append(percent)
        return True

    return StateServer(StateStore(_caps("lms")), set_volume=set_volume), got


def _headers(client, **extra):
    return {**BROWSER, "Host": f"{client.host}:{client.port}", **extra}


@pytest.mark.asyncio
async def test_a_page_on_another_site_cannot_change_anything():
    server, got = _server()
    async with TestClient(TestServer(server.make_app())) as client:
        own = f"http://{client.host}:{client.port}"
        # A form or a no-cors fetch from another site: refused.
        r = await client.post("/volume", data='{"percent": 100}',
                              headers=_headers(client, Origin="https://evil.example", **{"Content-Type": "text/plain"}))
        assert r.status == 403
        r = await client.post("/volume", json={"percent": 100}, headers=_headers(client, **{"Sec-Fetch-Site": "cross-site"}))
        assert r.status == 403
        r = await client.post("/volume", json={"percent": 100}, headers=_headers(client, Origin="null"))
        assert r.status == 403
        assert got == []
        # The player's own page: taken.
        r = await client.post("/volume", json={"percent": 40},
                              headers=_headers(client, Origin=own, **{"Sec-Fetch-Site": "same-origin"}))
        assert r.status == 200 and got == [40.0]


@pytest.mark.asyncio
async def test_a_public_name_pointed_at_the_player_gets_nothing():
    """The rebinding: the page's own name now resolves to the player, so its
    requests are same-origin to the browser - and name the page's site."""
    server, _ = _server()
    async with TestClient(TestServer(server.make_app())) as client:
        r = await client.get("/player/status", headers={**BROWSER, "Host": "rebind.evil.example:8090"})
        assert r.status == 403
        r = await client.get("/player/status", headers={**BROWSER, "Host": "gexis.local:8090"})
        assert r.status != 403, "past the guard (the route itself is not wired up here)"


@pytest.mark.asyncio
async def test_programs_that_are_not_browsers_are_not_affected():
    """Home Assistant set up with a router's name for the player still works."""
    server, got = _server()
    async with TestClient(TestServer(server.make_app())) as client:
        r = await client.post("/volume", json={"percent": 30}, headers={"Host": "gexis.home:8090"})
        assert r.status == 200 and got == [30.0]


@pytest.mark.asyncio
async def test_a_socket_opens_only_from_the_player_s_own_page():
    server, _ = _server()
    async with TestClient(TestServer(server.make_app())) as client:
        with pytest.raises(aiohttp.WSServerHandshakeError) as refused:
            await client.ws_connect("/state", headers=_headers(client, Origin="https://evil.example"))
        assert refused.value.status == 403
        ws = await client.ws_connect("/state", headers=_headers(client, Origin=f"http://{client.host}:{client.port}"))
        await ws.close()
