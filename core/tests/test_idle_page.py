"""The idle page probe (Phase 4d): whether the configured page can be embedded."""
from __future__ import annotations

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from multidict import CIMultiDict

from gexis_core.idle_page import framing_allowed, probe
from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer


@pytest.mark.parametrize(
    ("headers", "allowed"),
    [
        ({}, True),
        ({"X-Frame-Options": "DENY"}, False),
        ({"X-Frame-Options": "SAMEORIGIN"}, False),
        ({"Content-Security-Policy": "default-src 'self'"}, True),
        ({"Content-Security-Policy": "frame-ancestors 'none'"}, False),
        ({"Content-Security-Policy": "default-src *; frame-ancestors 'self'"}, False),
        ({"Content-Security-Policy": "frame-ancestors *"}, True),
        ({"content-security-policy": "FRAME-ANCESTORS 'self'"}, False),
    ],
)
def test_framing_allowed(headers, allowed):
    assert framing_allowed(CIMultiDict(headers)) is allowed


def _page_server(status=200, headers=None):
    async def handler(request):
        return web.Response(text="idle", status=status, headers=headers or {})

    app = web.Application()
    app.router.add_get("/", handler)
    return TestServer(app)


async def test_unconfigured_needs_no_request():
    async with aiohttp.ClientSession() as session:
        assert await probe("", session) == {"url": None, "embeddable": False, "reason": "unconfigured"}


async def test_an_embeddable_page():
    async with _page_server() as server, aiohttp.ClientSession() as session:
        url = str(server.make_url("/"))
        assert await probe(url, session) == {"url": url, "embeddable": True, "reason": None}


async def test_an_error_status_is_not_embeddable():
    async with _page_server(status=503) as server, aiohttp.ClientSession() as session:
        result = await probe(str(server.make_url("/")), session)
    assert result["embeddable"] is False
    assert result["reason"] == "http 503"


async def test_a_page_refusing_framing_is_not_embeddable():
    async with _page_server(headers={"X-Frame-Options": "DENY"}) as server, aiohttp.ClientSession() as session:
        result = await probe(str(server.make_url("/")), session)
    assert result["reason"] == "refuses framing"


async def test_an_unreachable_page_is_not_embeddable(unused_tcp_port):
    async with aiohttp.ClientSession() as session:
        result = await probe(f"http://127.0.0.1:{unused_tcp_port}/", session)
    assert result["embeddable"] is False
    assert result["reason"] == "unreachable"


async def test_the_idle_route_returns_the_probe_result():
    async def idle_page():
        return {"url": "http://example.test/", "embeddable": True, "reason": None}

    server = StateServer(StateStore({}), idle_page=idle_page)
    async with TestClient(TestServer(server.make_app())) as client:
        response = await client.get("/idle")
        assert response.status == 200
        assert await response.json() == {"url": "http://example.test/", "embeddable": True, "reason": None}


async def test_the_idle_route_answers_503_when_not_wired():
    server = StateServer(StateStore({}))
    async with TestClient(TestServer(server.make_app())) as client:
        response = await client.get("/idle")
        assert response.status == 503
