# SPDX-License-Identifier: GPL-3.0-or-later
"""The Plex library the Plexamp plugin lends (ADR-0184): held in memory,
asked for an album's cover, the cover served through the core."""
from __future__ import annotations

import logging

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gexis_core import plex as plex_mod
from gexis_core.enrichment import Answer, Cache, Enrichment, Outcome, TrackKey
from gexis_core.plex import PlexLibrary, PlexRelease
from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer

TOKEN = "server-token-xyz"
ALBUMS = [
    {"title": "Album One (Deluxe Edition)", "parentTitle": "The Artist",
     "thumb": "/library/metadata/101/thumb/1700000000"},
    {"title": "Second", "parentTitle": "Other & Friend", "thumb": "/library/metadata/102/thumb/5"},
    {"title": "No Picture", "parentTitle": "The Artist"},
    {"title": "Elsewhere", "parentTitle": "The Artist", "thumb": "http://example.org/a.jpg"},
]


class FakePlex:
    """A Plex Media Server: one music section, one of films, albums by page."""

    def __init__(self, albums=ALBUMS):
        self.albums = albums
        self.asked = []
        self.tokens = set()

    def app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/library/sections", self.sections)
        app.router.add_get("/library/sections/{key}/all", self.all)
        app.router.add_get("/photo/:/transcode", self.transcode)
        app.router.add_get("/library/metadata/{key}/thumb/{stamp}", self.thumb)
        return app

    def _seen(self, request):
        self.asked.append((request.path, dict(request.query)))
        self.tokens.add(request.headers.get("X-Plex-Token"))
        if request.headers.get("X-Plex-Token") != TOKEN:
            raise web.HTTPUnauthorized()

    async def sections(self, request):
        self._seen(request)
        return web.json_response({"MediaContainer": {"Directory": [
            {"key": "1", "type": "movie"}, {"key": "3", "type": "artist"}]}})

    async def all(self, request):
        self._seen(request)
        assert request.match_info["key"] == "3"
        assert request.query["type"] == "9" and request.query["excludeFields"] == "summary"
        start = int(request.query["X-Plex-Container-Start"])
        size = int(request.query["X-Plex-Container-Size"])
        page = self.albums[start:start + size]
        return web.json_response({"MediaContainer": {
            "size": len(page), "totalSize": len(self.albums), "Metadata": page}})

    async def transcode(self, request):
        self._seen(request)
        return web.Response(body=b"\xff\xd8scaled", content_type="image/jpeg")

    async def thumb(self, request):
        self._seen(request)
        return web.Response(body=b"\xff\xd8stored", content_type="image/jpeg")


@pytest.fixture
async def served():
    fake = FakePlex()
    server = TestServer(fake.app())
    await server.start_server()
    yield fake, f"http://127.0.0.1:{server.port}"
    await server.close()


def _lend(library, url, token=TOKEN, server="srv", plugin="plexamp"):
    return library.lend(plugin, {"t": "library", "kind": "plex", "server": server, "url": url,
                                 "token": token})


def test_only_plexamps_library_is_taken_and_only_on_this_network():
    library = PlexLibrary()
    assert not _lend(library, "http://10.0.0.5:32400", plugin="someone-else")
    assert not library.lent
    for url in ("http://1.1.1.1:32400", "http://plex.example.com:32400",
                "https://1-1-1-1.0123abcd.plex.direct:32400", "ftp://10.0.0.5", "http://10.0.0.5/x"):
        assert not _lend(library, url)
        assert not library.lent, url
    assert _lend(library, "https://10-0-0-5.0123abcd.plex.direct:32400")
    assert library.lent
    assert not _lend(library, "https://10-0-0-5.0123abcd.plex.direct:32400")
    assert library.lend("plexamp", {"kind": "plex", "server": None, "url": None, "token": None})
    assert not library.lent


def test_it_goes_with_the_plugin_and_the_token_is_never_said(caplog):
    caplog.set_level(logging.DEBUG, logger="gexis_core.plex")
    library = PlexLibrary()
    _lend(library, "http://10.0.0.5:32400")
    assert TOKEN not in repr(library._lent)
    assert not library.withdraw("someone-else")
    assert library.withdraw("plexamp")
    assert not library.lent
    said = " ".join(r.getMessage() for r in caplog.records)
    assert TOKEN not in said and "10.0.0.5" not in said


def test_another_servers_answers_are_forgotten_not_the_same_ones_after_a_restart(tmp_path):
    cache = Cache(tmp_path / "enrichment.db")
    key = TrackKey(artist="the artist", album="album one").scoped("album")
    found = Answer(Outcome.FOUND, Enrichment(album_art="/plex/cover/101/1", sources=("plex",)))
    _lend(PlexLibrary(store=cache), "http://10.0.0.5:32400", server="one")
    cache.put(key, "plex-release", found)
    _lend(PlexLibrary(store=cache), "http://10.0.0.5:32400", server="one")
    assert cache.get(key, "plex-release") is not None
    _lend(PlexLibrary(store=cache), "http://10.0.0.6:32400", server="two")
    assert cache.get(key, "plex-release") is None
    cache.close()


async def test_an_album_by_its_reduced_title_and_its_artist_or_lead_artist(served, monkeypatch):
    fake, url = served
    monkeypatch.setattr(plex_mod, "PAGE", 2)
    library = PlexLibrary()
    _lend(library, url)
    assert await library.album("The Artist", "Album One") == (Outcome.FOUND, ("101", "1700000000"))
    assert await library.album("Other", "Second") == (Outcome.FOUND, ("102", "5"))
    assert await library.album("Somebody Else", "Album One") == (Outcome.MISSING, None)
    # No picture, or one that is not the server's own: not a cover it can serve.
    assert await library.album("The Artist", "No Picture") == (Outcome.MISSING, None)
    assert await library.album("The Artist", "Elsewhere") == (Outcome.MISSING, None)
    pages = [q for path, q in fake.asked if path.endswith("/all")]
    assert [q["X-Plex-Container-Start"] for q in pages] == ["0", "2"], "two pages, once"
    assert fake.tokens == {TOKEN}
    await library.close()


async def test_the_index_is_made_again_when_old_or_lent_again(served):
    fake, url = served
    now = [1000.0]
    library = PlexLibrary(clock=lambda: now[0])
    _lend(library, url)
    await library.album("The Artist", "Album One")
    await library.album("The Artist", "Album One")
    assert sum(p == "/library/sections" for p, _ in fake.asked) == 1
    now[0] += plex_mod.INDEX_TTL_S + 1
    await library.album("The Artist", "Album One")
    assert sum(p == "/library/sections" for p, _ in fake.asked) == 2
    await library.close()


async def test_a_server_that_cannot_be_asked_is_unavailable_not_missing():
    library = PlexLibrary()
    _lend(library, "http://127.0.0.1:9")
    assert await library.album("The Artist", "Album One") == (Outcome.UNAVAILABLE, None)
    await library.close()


async def test_a_wrong_token_is_unavailable(served):
    _fake, url = served
    library = PlexLibrary()
    _lend(library, url, token="stale")
    assert (await library.album("The Artist", "Album One"))[0] is Outcome.UNAVAILABLE
    await library.close()


async def test_the_provider_answers_a_path_on_the_player_never_the_servers(served):
    _fake, url = served
    library = PlexLibrary()
    allowed = [True]
    provider = PlexRelease(library, allowed=lambda: allowed[0])
    assert not provider.ready(), "nothing lent"
    _lend(library, url)
    assert provider.ready()
    allowed[0] = False
    assert not provider.ready(), "the row is off"
    assert not provider.serves("radio") and provider.serves("spotify")
    key = TrackKey.of(type("M", (), {"artist": "The Artist", "album": "Album One (Deluxe Edition)",
                                     "title": "A Song", "duration": 200})()).scoped("album")
    answer = await provider.fetch(key)
    assert answer.outcome is Outcome.FOUND
    assert answer.enrichment.album_art == "/plex/cover/101/1700000000"
    assert TOKEN not in str(answer.enrichment.to_json())
    assert (await provider.fetch(TrackKey(artist="x"))).outcome is Outcome.MISSING
    await library.close()


async def test_the_cover_through_the_core(served):
    fake, url = served
    library = PlexLibrary()
    server = StateServer(StateStore({}), plex=library)
    async with TestClient(TestServer(server.make_app())) as client:
        answer = await client.get("/plex/cover/101/1700000000")
        assert answer.status == 404, "nothing lent"
        _lend(library, url)
        answer = await client.get("/plex/cover/101/1700000000?size=300")
        assert answer.status == 200
        assert await answer.read() == b"\xff\xd8scaled"
        assert answer.headers["Content-Type"] == "image/jpeg"
        path, query = fake.asked[-1]
        assert path == "/photo/:/transcode"
        assert query["url"] == "/library/metadata/101/thumb/1700000000"
        assert query["width"] == "300" and "X-Plex-Token" not in query
        await client.get("/plex/cover/101/1?size=5000")
        assert fake.asked[-1][1]["width"] == "600"
        assert (await client.get("/plex/cover/101/abc")).status == 404
        assert (await client.get("/plex/cover/..%2Fsections/1")).status == 404
    await library.close()


async def test_the_stored_picture_when_the_scaler_will_not():
    fake = FakePlex()
    server = TestServer(_refusing(fake))
    await server.start_server()
    library = PlexLibrary()
    _lend(library, f"http://127.0.0.1:{server.port}")
    assert await library.cover("101", "1700000000") == ("image/jpeg", b"\xff\xd8stored")
    assert await library.cover("101", "../x") is None
    await server.close()
    await library.close()


def _refusing(fake):
    app = web.Application()

    async def refuse(request):
        fake._seen(request)
        return web.Response(status=500)
    app.router.add_get("/photo/:/transcode", refuse)
    app.router.add_get("/library/metadata/{key}/thumb/{stamp}", fake.thumb)
    return app
