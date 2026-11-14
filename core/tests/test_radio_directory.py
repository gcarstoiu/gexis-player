# SPDX-License-Identifier: GPL-3.0-or-later
"""The radio directory (ADR-0180 item 1): radio-browser.info, asked through
servers found rather than written in, every list kept a day.

The fake servers fail as the real one has (Lesson 83): 503 to everything
(2026-10-23), a refused connection (down, 2025-03-30), and one that accepts
and says nothing. The shapes they answer with are the real directory's, read
from it once on 2026-11-14 (Lesson 40).
"""
from __future__ import annotations

import asyncio
import json
import socket

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from gexis_core import radio_directory as rd

UA = "GexisPlayer/test"

#: The real directory's station, trimmed (2026-11-14).
STATION = {
    "changeuuid": "299658a8-bfb8-4ff8-b197-ca70478bf80a",
    "stationuuid": "78012206-1aa1-11e9-a80b-52543be04c81",
    "name": "Example FM ",
    "url": "https://stream.example.org/playlist.pls",
    "url_resolved": "https://stream.example.org/live",
    "favicon": "https://example.org/logo-192x192.webp",
    "tags": "music,variety",
    "country": "Germany",
    "countrycode": "DE",
    "language": "english,german",
    "codec": "MP3",
    "bitrate": 128,
    "hls": 0,
    "lastcheckok": 1,
    "clickcount": 1200,
}


def station(n: int, **changes) -> dict:
    return {**STATION, "stationuuid": f"00000000-0000-0000-0000-{n:012d}", "name": f"Station {n}",
            **changes}


class Fake:
    """One directory server. `mode` is how it behaves now."""

    def __init__(self) -> None:
        self.mode = "ok"
        self.asked: list[str] = []
        self.stations = [station(1), station(2)]

    def app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/json/{rest:.*}", self.handle)
        return app

    async def handle(self, request: web.Request) -> web.StreamResponse:
        self.asked.append(request.path_qs)
        if self.mode == "503":
            return web.Response(status=503, text="Service Unavailable")
        if self.mode == "silent":
            await asyncio.sleep(30)
        path = request.path
        if path == "/json/stations/search":
            if request.query.get("hidebroken") != "true":
                return web.json_response([station(99, lastcheckok=0)])
            return web.json_response(self.stations)
        if path == "/json/countries":
            return web.json_response([{"name": "Germany", "iso_3166_1": "DE", "stationcount": 5592},
                                      {"name": "", "iso_3166_1": "XX", "stationcount": 3},
                                      {"name": "Nowhere", "iso_3166_1": "", "stationcount": 3}])
        if path == "/json/tags":
            return web.json_response([{"name": "pop", "stationcount": 5105},
                                      {"name": "empty", "stationcount": 0}])
        if path == "/json/languages":
            return web.json_response([{"name": "english", "iso_639": "en", "stationcount": 11267},
                                      {"name": "klingon", "iso_639": None, "stationcount": 2}])
        if path.startswith("/json/url/"):
            uuid = path.rsplit("/", 1)[1]
            return web.json_response({"ok": True, "message": "retrieved station url",
                                      "stationuuid": uuid, "name": "Example FM",
                                      "url": "http://moved.example.org/live"})
        return web.Response(status=404)


@pytest.fixture
async def servers():
    """Two fake servers; the list `discover` would give, in order."""
    fakes = [Fake(), Fake()]
    running = [TestServer(f.app()) for f in fakes]
    for server in running:
        await server.start_server()
    bases = [f"http://{s.host}:{s.port}" for s in running]
    yield fakes, bases
    for server in running:
        await server.close()


class Clock:
    def __init__(self) -> None:
        self.now = 1_800_000_000.0

    def __call__(self) -> float:
        return self.now


def make(tmp_path, bases, clock=None, discovered=None):
    calls = discovered if discovered is not None else []

    async def found():
        calls.append(1)
        return list(bases)
    return rd.Directory(user_agent=UA, cache_dir=tmp_path, servers=found, clock=clock or Clock())


async def test_popular_lists_playable_stations_with_logo_rules(tmp_path, servers):
    fakes, bases = servers
    fakes[0].stations = [
        station(1),
        station(2, favicon="https://example.org/favicon.ico?v=2"),   # .ico: none
        station(3, favicon=""),                                       # missing
        station(4, url_resolved="", url="ftp://nope"),               # not playable
        station(5, name="   "),                                       # no name
        station(1),                                                   # listed twice
        station(6, codec="UNKNOWN", bitrate=0, hls=1),
    ]
    directory = make(tmp_path, bases)
    try:
        stations = await directory.popular("de")
    finally:
        await directory.close()
    assert [s.name for s in stations] == ["Station 1", "Station 2", "Station 3", "Station 6"]
    assert stations[0].url == "https://stream.example.org/live"   # resolved, not the .pls
    assert stations[0].logo == "https://example.org/logo-192x192.webp"
    assert stations[1].logo is None and stations[2].logo is None
    assert stations[3].codec is None and stations[3].bitrate is None and stations[3].hls
    asked = fakes[0].asked[0]
    assert "countrycode=DE" in asked and "hidebroken=true" in asked and "order=clickcount" in asked
    assert directory.reachable is True


async def test_a_list_is_kept_a_day_and_asked_again_after(tmp_path, servers):
    fakes, bases = servers
    clock = Clock()
    directory = make(tmp_path, bases, clock)
    try:
        first = await directory.by_tag("jazz")
        clock.now += rd.FRESH_S - 60
        again = await directory.by_tag("jazz")
        assert again == first
        assert len(fakes[0].asked) == 1, "a list under a day old is not asked for again"
        clock.now += 120
        await directory.by_tag("jazz")
        assert len(fakes[0].asked) == 2, "older than a day, it is asked again"
    finally:
        await directory.close()


async def test_a_failing_server_is_passed_over_for_the_next(tmp_path, servers):
    fakes, bases = servers
    fakes[0].mode = "503"
    directory = make(tmp_path, bases)
    try:
        stations = await directory.search("example")
    finally:
        await directory.close()
    assert [s.name for s in stations] == ["Station 1", "Station 2"]
    assert len(fakes[0].asked) == 1 and len(fakes[1].asked) == 1
    assert directory.reachable is True


async def test_every_server_failing_is_unreachable_not_empty(tmp_path, servers, monkeypatch):
    fakes, bases = servers
    fakes[0].mode = "503"
    fakes[1].mode = "silent"
    monkeypatch.setattr(rd, "TIMEOUT_S", 0.3)
    refused = _refused_base()
    discovered = []
    directory = make(tmp_path, [refused, *bases], discovered=discovered)
    try:
        with pytest.raises(rd.Unreachable):
            await directory.countries()
        assert directory.reachable is False
        # Looked up afresh after all failed.
        fakes[0].mode = fakes[1].mode = "ok"
        countries = await directory.countries()
    finally:
        await directory.close()
    assert countries == [{"code": "DE", "name": "Germany", "stations": 5592}]
    assert len(discovered) == 2
    assert directory.reachable is True


async def test_the_days_list_is_shown_while_the_directory_is_down(tmp_path, servers):
    fakes, bases = servers
    clock = Clock()
    directory = make(tmp_path, bases, clock)
    try:
        tags = await directory.tags()
        for fake in fakes:
            fake.mode = "503"
        clock.now += 3600
        assert await directory.tags() == tags == [{"name": "pop", "stations": 5105}]
        # A list never seen is unreachable.
        with pytest.raises(rd.Unreachable):
            await directory.languages()
        # Past the day, the kept list is not shown stale.
        clock.now += rd.FRESH_S
        with pytest.raises(rd.Unreachable):
            await directory.tags()
    finally:
        await directory.close()


async def test_lists_survive_a_restart_through_the_cache(tmp_path, servers):
    fakes, bases = servers
    clock = Clock()
    first = make(tmp_path, bases, clock)
    try:
        await first.languages()
    finally:
        await first.close()
    for fake in fakes:
        fake.mode = "503"
    second = make(tmp_path, bases, clock)
    try:
        assert await second.languages() == [{"name": "english", "code": "en", "stations": 11267},
                                            {"name": "klingon", "code": None, "stations": 2}]
    finally:
        await second.close()


async def test_a_corrupt_cache_file_is_asked_again(tmp_path, servers):
    fakes, bases = servers
    directory = make(tmp_path, bases)
    try:
        await directory.tags()
        for path in tmp_path.glob("*.json"):
            path.write_text("{not json")
        await directory.tags()
    finally:
        await directory.close()
    assert len(fakes[0].asked) == 2


async def test_the_play_count_answers_the_address_now(tmp_path, servers):
    fakes, bases = servers
    directory = make(tmp_path, bases)
    try:
        url = await directory.count_play(STATION["stationuuid"])
        assert url == "http://moved.example.org/live"
        assert fakes[0].asked == [f"/json/url/{STATION['stationuuid']}"]
        # Never kept: each play is counted.
        await directory.count_play(STATION["stationuuid"])
        assert len(fakes[0].asked) == 2
    finally:
        await directory.close()


async def test_the_play_count_gives_up_quickly_and_plays_the_kept_address(tmp_path, servers, monkeypatch):
    fakes, bases = servers
    for fake in fakes:
        fake.mode = "silent"
    monkeypatch.setattr(rd, "PLAY_TIMEOUT_S", 0.3)
    directory = make(tmp_path, bases)
    loop = asyncio.get_running_loop()
    try:
        started = loop.time()
        assert await directory.count_play(STATION["stationuuid"]) is None
        assert loop.time() - started < 2.0
    finally:
        await directory.close()


async def test_the_user_agent_is_ours(tmp_path):
    seen = []

    async def handle(request):
        seen.append(request.headers.get("User-Agent"))
        return web.json_response([])
    app = web.Application()
    app.router.add_get("/json/tags", handle)
    server = TestServer(app)
    await server.start_server()
    directory = make(tmp_path, [f"http://{server.host}:{server.port}"])
    try:
        assert await directory.tags() == []
    finally:
        await directory.close()
        await server.close()
    assert seen == [UA]


def test_a_kept_station_round_trips_and_bad_ones_are_refused():
    s = rd.Station.from_directory(STATION)
    assert rd.Station.from_json(json.loads(json.dumps(s.to_json()))) == s
    assert rd.Station.from_json({"id": "x", "name": "N", "url": "file:///etc/passwd"}) is None
    assert rd.Station.from_json({"id": "", "name": "N", "url": "http://a/b"}) is None
    assert rd.Station.from_json("nope") is None
    kept = rd.Station.from_json({"id": "a1", "name": " N ", "url": "http://a/b", "listed": False,
                                 "bitrate": True, "logo": "http://a/x.ICO"})
    assert kept.name == "N" and kept.listed is False and kept.bitrate is None and kept.logo is None


async def test_discovery_names_each_address_back_and_keeps_only_the_directorys(monkeypatch):
    async def getaddrinfo(host, port, proto=0):
        assert host == rd.DISCOVERY_HOST
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.1", 443)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.2", 443)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.3", 443))]
    names = {"192.0.2.1": "de1.api.radio-browser.info.", "192.0.2.2": "elsewhere.example.org"}

    def gethostbyaddr(address):
        if address not in names:
            raise socket.herror("no name")
        return names[address], [], [address]
    loop = asyncio.get_running_loop()
    monkeypatch.setattr(loop, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(rd.socket, "gethostbyaddr", gethostbyaddr)
    assert await rd.discover() == ["https://de1.api.radio-browser.info"]
    names.clear()
    assert await rd.discover() == [f"https://{rd.DISCOVERY_HOST}"]


async def test_discovery_that_cannot_resolve_finds_nothing(monkeypatch):
    async def getaddrinfo(host, port, proto=0):
        raise socket.gaierror("no network")
    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", getaddrinfo)
    assert await rd.discover() == []


def _refused_base() -> str:
    """An address on this machine where nothing listens."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return f"http://127.0.0.1:{port}"
