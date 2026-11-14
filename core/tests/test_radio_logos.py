# SPDX-License-Identifier: GPL-3.0-or-later
"""Station logos through the player (ADR-0180; George, 2026-11-14)."""
from __future__ import annotations

import asyncio

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from gexis_core import radio_logos as rl

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\0" * 64
WEBP = b"RIFF\0\0\0\0WEBPVP8 " + b"\0" * 64
SVG = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"


class Site:
    def __init__(self) -> None:
        self.asked: list[str] = []

    def app(self) -> web.Application:
        app = web.Application()

        async def handle(request):
            self.asked.append(request.path)
            name = request.match_info["name"]
            if name == "moved":
                raise web.HTTPFound("/logo.png")
            if name == "huge":
                return web.Response(body=PNG + b"\0" * (rl.MOST_BYTES + 10), content_type="image/png")
            bodies = {"logo.png": PNG, "logo.jpg": JPEG, "logo.webp": WEBP, "logo.svg": SVG,
                      "lies.png": b"<html>not a picture</html>"}
            if name not in bodies:
                return web.Response(status=404)
            # What the site says the type is does not matter: the bytes do.
            return web.Response(body=bodies[name], content_type="image/png")
        app.router.add_get("/{name}", handle)
        return app


@pytest.fixture
async def site(monkeypatch):
    s = Site()
    server = TestServer(s.app())
    await server.start_server()

    async def anywhere(url):
        return True
    # The fake site is on this machine; the address check is tested below.
    monkeypatch.setattr(rl.Logos, "_public", staticmethod(anywhere))
    yield s, f"http://{server.host}:{server.port}"
    await server.close()


class Clock:
    now = 1_800_000_000.0

    def __call__(self):
        return self.now


async def test_a_logo_the_player_handed_out_is_fetched_kept_and_served(tmp_path, site):
    s, base = site
    logos = rl.Logos(user_agent="t", cache_dir=tmp_path)
    try:
        path = logos.path(f"{base}/logo.jpg")
        assert path.startswith(rl.PREFIX) and len(path) == len(rl.PREFIX) + 16
        key = path[len(rl.PREFIX):]
        assert await logos.get(key) == ("image/jpeg", JPEG)
        assert await logos.get(key) == ("image/jpeg", JPEG)
        assert s.asked == ["/logo.jpg"], "kept, not fetched again"
        # A restart forgets the addresses but keeps the pictures.
        again = rl.Logos(user_agent="t", cache_dir=tmp_path)
        assert await again.get(key) == ("image/jpeg", JPEG)
        await again.close()
    finally:
        await logos.close()


async def test_a_key_the_player_never_gave_fetches_nothing(tmp_path, site):
    s, base = site
    logos = rl.Logos(user_agent="t", cache_dir=tmp_path)
    try:
        assert await logos.get(rl.key_of(f"{base}/logo.png")) is None
        assert await logos.get("../../etc/passwd") is None
        assert await logos.get("ZZZZZZZZZZZZZZZZ") is None
    finally:
        await logos.close()
    assert s.asked == []


@pytest.mark.parametrize("name", ["logo.svg", "lies.png", "huge", "missing.png"])
async def test_only_pictures_taken_and_a_failure_is_remembered(tmp_path, site, name):
    s, base = site
    clock = Clock()
    logos = rl.Logos(user_agent="t", cache_dir=tmp_path, clock=clock)
    try:
        key = logos.path(f"{base}/{name}")[len(rl.PREFIX):]
        assert await logos.get(key) is None
        assert await logos.get(key) is None
        assert len(s.asked) == 1, "not asked again within a day"
        clock.now += rl.FAILED_S + 1
        await logos.get(key)
        assert len(s.asked) == 2
    finally:
        await logos.close()


async def test_webp_and_a_redirect(tmp_path, site):
    s, base = site
    logos = rl.Logos(user_agent="t", cache_dir=tmp_path)
    try:
        assert await logos.get(logos.path(f"{base}/logo.webp")[len(rl.PREFIX):]) == ("image/webp", WEBP)
        assert await logos.get(logos.path(f"{base}/moved")[len(rl.PREFIX):]) == ("image/png", PNG)
    finally:
        await logos.close()


async def test_the_source_of_a_path_and_none():
    logos = rl.Logos(user_agent="t")
    path = logos.path("https://example.org/a.png")
    assert logos.source(path) == "https://example.org/a.png"
    assert logos.source(rl.PREFIX + "0" * 16) is None
    assert logos.source("https://example.org/b.png") == "https://example.org/b.png"
    assert logos.path(None) is None and logos.source(None) is None


@pytest.mark.parametrize("address, public", [
    ("93.184.215.14", True), ("192.168.1.1", False), ("10.0.0.5", False), ("127.0.0.1", False),
    ("169.254.1.1", False), ("::1", False), ("fd00::1", False), ("2001:4860:4860::8888", True),
])
async def test_never_an_address_on_the_home_network(monkeypatch, address, public):
    async def getaddrinfo(host, port, proto=0):
        return [(2, 1, 6, "", (address, port))]
    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", getaddrinfo)
    assert await rl.Logos._public("https://logo.example.org/x.png") is public
    assert await rl.Logos._public("ftp://logo.example.org/x.png") is False


async def test_a_redirect_to_the_home_network_is_refused(tmp_path, monkeypatch):
    calls = []

    async def public(url):
        calls.append(url)
        return "evil" not in url
    monkeypatch.setattr(rl.Logos, "_public", staticmethod(public))

    async def handle(request):
        raise web.HTTPFound("http://evil.example/admin")
    app = web.Application()
    app.router.add_get("/x.png", handle)
    server = TestServer(app)
    await server.start_server()
    logos = rl.Logos(user_agent="t", cache_dir=tmp_path)
    try:
        key = logos.path(f"http://{server.host}:{server.port}/x.png")[len(rl.PREFIX):]
        assert await logos.get(key) is None
        assert calls[-1] == "http://evil.example/admin"
    finally:
        await logos.close()
        await server.close()


def test_sniff():
    assert rl.sniff(PNG) == "image/png" and rl.sniff(JPEG) == "image/jpeg"
    assert rl.sniff(b"GIF89a....") == "image/gif" and rl.sniff(WEBP) == "image/webp"
    assert rl.sniff(SVG) is None and rl.sniff(b"") is None
