# SPDX-License-Identifier: GPL-3.0-or-later
"""The Plex library the Plexamp plugin lends (ADR-0184): held in memory,
asked for an album's cover and an artist's biography, picture, similar
artists and popular tracks; the pictures served through the core."""
from __future__ import annotations

import logging
from pathlib import Path

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gexis_core import plex as plex_mod
from gexis_core.enrichment import Answer, Cache, Enrichment, Outcome, TrackKey
from gexis_core.plex import (SWEPT_ALBUMS, SWEPT_ARTISTS, PlexArtist, PlexLibrary, PlexRelease,
                              swept)
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
ARTISTS = [
    {"ratingKey": "201", "title": "The Artist", "thumb": "/library/metadata/201/thumb/1700000001"},
    {"ratingKey": "202", "title": "Other", "thumb": "/library/metadata/202/thumb/7"},
    {"ratingKey": "203", "title": "No Face"},
]
RECORDS = {
    "201": {"ratingKey": "201", "title": "The Artist", "summary": "A biography.",
            "thumb": "/library/metadata/201/thumb/1700000002",
            "Similar": [{"tag": "Kin One"}, {"tag": "Kin Two"}, {"tag": "Kin One"}]},
    "202": {"ratingKey": "202", "title": "Other", "summary": "", "thumb": "/library/metadata/202/thumb/7"},
    "203": {"ratingKey": "203", "title": "No Face", "summary": "Only words."},
}
#: The artist's tracks as the server sorts them, most played first; one
#: recording twice, and one the wider world has no count for.
TRACKS = {"201": [{"title": "Big Hit", "ratingCount": 900000}, {"title": "Second Hit", "ratingCount": 5000},
                  {"title": "Big Hit", "ratingCount": 800}, {"title": "Unheard"}]}


class FakePlex:
    """A Plex Media Server: one music section, one of films, albums by page."""

    def __init__(self, albums=ALBUMS):
        self.albums = albums
        self.asked = []
        self.tokens = set()
        self.refuse_popular = False

    def app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/library/sections", self.sections)
        app.router.add_get("/library/sections/{key}/all", self.all)
        app.router.add_get("/photo/:/transcode", self.transcode)
        app.router.add_get("/library/metadata/{key}/thumb/{stamp}", self.thumb)
        app.router.add_get("/library/metadata/{key}", self.record)
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
        kind = request.query["type"]
        if kind == "10":
            # An artist's popular tracks, asked as Plexamp's DJ asks them.
            assert request.query["sort"] == "ratingCount:desc" and request.query["group"] == "guid"
            if self.refuse_popular:
                raise web.HTTPBadRequest()
            tracks = TRACKS.get(request.query["artist.id"], [])
            return web.json_response({"MediaContainer": {"size": len(tracks), "Metadata": tracks}})
        assert kind in ("8", "9") and request.query["excludeFields"] == "summary"
        items = self.albums if kind == "9" else ARTISTS
        start = int(request.query["X-Plex-Container-Start"])
        size = int(request.query["X-Plex-Container-Size"])
        page = items[start:start + size]
        return web.json_response({"MediaContainer": {
            "size": len(page), "totalSize": len(items), "Metadata": page}})

    async def record(self, request):
        self._seen(request)
        found = RECORDS.get(request.match_info["key"])
        if found is None:
            raise web.HTTPNotFound()
        return web.json_response({"MediaContainer": {"size": 1, "Metadata": [found]}})

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
    artist = TrackKey(artist="the artist").scoped("artist")
    cache.put(artist, "plex-artist", Answer(Outcome.FOUND, Enrichment(biography="b", sources=("plex",))))
    cache.remember(SWEPT_ARTISTS, "the artist", "201/1")
    cache.remember(SWEPT_ALBUMS, "the artist\x1falbum one", "101/1")
    assert swept(cache, SWEPT_ARTISTS, "the artist", 300) == "/plex/cover/201/1?size=300"
    _lend(PlexLibrary(store=cache), "http://10.0.0.6:32400", server="two")
    assert cache.get(key, "plex-release") is None
    assert cache.get(artist, "plex-artist") is None
    assert swept(cache, SWEPT_ARTISTS, "the artist", 300) is None
    assert swept(cache, SWEPT_ALBUMS, "the artist\x1falbum one", 300) is None
    cache.close()


def test_only_a_pictures_two_numbers_are_read_back_from_the_sweep(tmp_path):
    cache = Cache(tmp_path / "enrichment.db")
    for key, value in (("a", "../library/sections"), ("b", None), ("c", "1/2/3"), ("d", 5)):
        cache.remember(SWEPT_ALBUMS, key, value)
        assert swept(cache, SWEPT_ALBUMS, key, 300) is None, value
    assert swept(cache, SWEPT_ALBUMS, "never", 300) is None
    assert swept(None, SWEPT_ALBUMS, "a", 300) is None
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
    pages = [q for path, q in fake.asked if path.endswith("/all") and q["type"] == "9"]
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
        assert fake.asked[-1][1]["width"] == "1200", "brought into the range"
        await client.get("/plex/cover/101/1?size=50")
        assert fake.asked[-1][1]["width"] == "100"
        await client.get("/plex/cover/101/1")
        assert fake.asked[-1][1]["width"] == "600"
        # An artist's picture, by its two numbers, the same way.
        assert (await client.get("/plex/cover/201/1700000002")).status == 200
        assert fake.asked[-1][1]["url"] == "/library/metadata/201/thumb/1700000002"
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


# --- the artist (the second step, 2026-11-17) --------------------------------


async def test_an_artist_by_folded_name_or_lead_artist(served):
    _fake, url = served
    library = PlexLibrary()
    _lend(library, url)
    assert await library.artist("THE ARTIST") == (Outcome.FOUND, ("201", "1700000001", "3"))
    assert await library.artist("Other & Friend") == (Outcome.FOUND, ("202", "7", "3"))
    assert await library.artist("No Face") == (Outcome.FOUND, ("203", None, "3"))
    assert await library.artist("Nobody") == (Outcome.MISSING, None)
    await library.close()


async def test_the_artist_provider_answers_what_the_library_knows(served):
    fake, url = served
    library = PlexLibrary()
    allowed = [True]
    provider = PlexArtist(library, allowed=lambda: allowed[0])
    assert not provider.ready(), "nothing lent"
    _lend(library, url)
    assert provider.ready() and provider.serves("radio")
    allowed[0] = False
    assert not provider.ready(), "the row is off"

    answer = await provider.fetch(TrackKey(artist="the artist", raw_artist="The Artist"))
    assert answer.outcome is Outcome.FOUND
    found = answer.enrichment
    assert found.biography == "A biography." and found.biography_source == "Plex"
    assert found.artist_image == "/plex/cover/201/1700000002", "the record's picture, the newest"
    assert found.similar == ("Kin One", "Kin Two")
    assert found.popular == ("Big Hit", "Second Hit"), "most played first, once each, counted only"
    assert TOKEN not in str(found.to_json())
    popular = [q for path, q in fake.asked if q.get("type") == "10"]
    assert popular[-1]["artist.id"] == "201" and popular[-1]["limit"] == "10"

    words = (await provider.fetch(TrackKey(artist="no face"))).enrichment
    assert words.biography == "Only words." and words.artist_image is None
    picture = (await provider.fetch(TrackKey(artist="other"))).enrichment
    assert picture.biography is None and picture.biography_source is None
    assert picture.artist_image == "/plex/cover/202/7"
    assert (await provider.fetch(TrackKey(artist="nobody"))).outcome is Outcome.MISSING
    assert (await provider.fetch(TrackKey(title="x"))).outcome is Outcome.MISSING
    await library.close()


async def test_popular_tracks_that_cannot_be_read_are_none_not_a_failed_answer(served):
    fake, url = served
    fake.refuse_popular = True
    library = PlexLibrary()
    _lend(library, url)
    answer = await PlexArtist(library).fetch(TrackKey(artist="the artist"))
    assert answer.outcome is Outcome.FOUND
    assert answer.enrichment.biography == "A biography." and answer.enrichment.popular == ()
    await library.close()


async def test_an_artist_on_a_server_that_cannot_be_asked_is_unavailable(served):
    _fake, url = served
    library = PlexLibrary()
    _lend(library, url, token="stale")
    assert (await PlexArtist(library).fetch(TrackKey(artist="the artist"))).outcome is Outcome.UNAVAILABLE
    await library.close()


async def test_nothing_from_plex_while_the_row_is_off(served):
    _fake, url = served
    on = [True]
    library = PlexLibrary(allowed=lambda: on[0])
    _lend(library, url)
    server = StateServer(StateStore({}), plex=library)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.get("/plex/cover/101/1700000000")).status == 200
        on[0] = False
        assert not library.ready()
        assert (await client.get("/plex/cover/101/1700000000")).status == 404
    await library.close()


def test_the_grid_and_the_portraits_read_the_sweeps_plex_pictures_first(tmp_path):
    from gexis_core.artwork_sweep import ALBUM_NAMESPACE, ARTIST_NAMESPACE
    from gexis_core.library import LmsLibrary

    cache = Cache(tmp_path / "enrichment.db")
    cache.remember(SWEPT_ALBUMS, "the artist\x1falbum one", "101/1700000000")
    cache.remember(ALBUM_NAMESPACE, "the artist\x1falbum one", "https://fan/one.jpg")
    cache.remember(SWEPT_ARTISTS, "the artist", "201/1700000001")
    cache.remember(ARTIST_NAMESPACE, "the artist", "https://fan/a.jpg")
    on = [True]
    plex = PlexLibrary(allowed=lambda: on[0])
    lms = LmsLibrary("lms", 9000, store=cache)
    lms.plex = plex
    album = {"artist": "The Artist", "album": "Album One", "artwork_track_id": 5}

    class Library:
        base = "http://lms:9000"

    server = StateServer(StateStore({}), library=Library(), notes=cache, plex=plex)
    fanart_cover = "http://lms:9000/imageproxy/https://fan/one.jpg/image_300x300_o.jpg"
    fanart_portrait = "http://lms:9000/imageproxy/https://fan/a.jpg/image_600x600_o.jpg"
    assert lms._cover(album, 300) == fanart_cover, "nothing lent"
    assert server.swept_portrait_of("The Artist", 600) == fanart_portrait
    _lend(plex, "http://10.0.0.5:32400")
    assert lms._cover(album, 300) == "/plex/cover/101/1700000000?size=300"
    assert server.swept_portrait_of("The Artist", 600) == "/plex/cover/201/1700000001?size=600"
    on[0] = False
    assert lms._cover(album, 300) == fanart_cover, "the row is off"
    assert server.swept_portrait_of("The Artist", 600) == fanart_portrait
    cache.close()


class _Info:
    """LMS's own plugin, on the artist page."""

    async def photos(self, ids, size=200):
        return {ids[0]: "http://lms/photo.jpg"}

    async def biography(self, artist_id):
        return "From the plugin."


class _Library:
    base = "http://lms"

    def __init__(self, tracks):
        self.tracks = tracks

    async def artist_tracks(self, artist_id):
        return self.tracks

    async def artist_name(self, artist_id):
        return "The Artist"


class _ListenBrainzPopular:
    name = "popular"

    def serves(self, renderer):
        return True

    async def fetch(self, key):
        return Answer(Outcome.FOUND, Enrichment(popular=("Deep Cut",), sources=("popular",)))


async def _artist_page(url, tracks, *, lent=True):
    from gexis_core.enrichment import EnrichmentService

    library = PlexLibrary()
    if lent:
        _lend(library, url)
    service = EnrichmentService([PlexArtist(library), _ListenBrainzPopular()], Cache(Path(":memory:")))
    server = StateServer(StateStore({}), artistinfo=_Info(), enrichment=service,
                         library=_Library(tracks), plex=library)
    async with TestClient(TestServer(server.make_app())) as client:
        body = await (await client.get("/library/artist-info?id=7&name=The%20Artist")).json()
    await library.close()
    return body


async def test_the_artist_page_asks_plex_first_for_every_field(served):
    _fake, url = served
    tracks = [{"id": 11, "title": "Second Hit", "duration": 200}, {"id": 12, "title": "Big Hit"},
              {"id": 13, "title": "Deep Cut"}]
    body = await _artist_page(url, tracks)
    found = body["enrichment"]
    assert found["biography"] == "A biography." and found["biography_source"] == "Plex"
    assert found["artist_image"] == "/plex/cover/201/1700000002"
    assert found["similar"] == ["Kin One", "Kin Two"]
    assert [row["id"] for row in body["popular"]] == [12, 11], "Plex's order, what LMS can play"

    # Without a library lent, the page is what it was: LMS's words and picture.
    body = await _artist_page(url, tracks, lent=False)
    assert body["enrichment"]["biography"] == "From the plugin."
    assert body["enrichment"]["artist_image"] == "http://lms/photo.jpg"
    assert [row["id"] for row in body["popular"]] == [13]


async def test_popular_falls_back_to_listenbrainz_when_none_of_plexs_is_here(served):
    _fake, url = served
    body = await _artist_page(url, [{"id": 13, "title": "Deep Cut"}])
    assert [row["id"] for row in body["popular"]] == [13]


async def test_what_is_playing_shows_plexs_picture_over_the_sweeps_fanart(served):
    from gexis_core.artwork_sweep import ARTIST_NAMESPACE
    from gexis_core.enrichment import EnrichmentService
    from gexis_core.model import TrackMetadata

    _fake, url = served
    library = PlexLibrary()
    _lend(library, url)
    cache = Cache(Path(":memory:"))
    cache.remember(ARTIST_NAMESPACE, "the artist", "https://fan/a.jpg")
    store = StateStore({"spotify": True})
    store.set_active("spotify")
    store.set_metadata("spotify", TrackMetadata(artist="The Artist", title="Big Hit"))
    server = StateServer(store, enrichment=EnrichmentService([PlexArtist(library)], cache),
                         library=_Library([]), notes=cache, plex=library)
    async with TestClient(TestServer(server.make_app())) as client:
        body = await (await client.get("/enrichment")).json()
    assert body["enrichment"]["artist_image"] == "/plex/cover/201/1700000002"
    assert body["enrichment"]["biography_source"] == "Plex"
    await library.close()
