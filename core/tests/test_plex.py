# SPDX-License-Identifier: GPL-3.0-or-later
"""The Plex library the Plexamp plugin lends (ADR-0184): held in memory,
asked for an album's cover and an artist's biography, picture, similar
artists and popular tracks; the pictures served through the core."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gexis_core import plex as plex_mod
from gexis_core.enrichment import Answer, Cache, Enrichment, Outcome, TrackKey
from gexis_core.plex import (SWEPT_ALBUMS, SWEPT_ARTISTS, PlexArtist, PlexLibrary, PlexLyrics,
                              PlexRelease, swept)
from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer

TOKEN = "server-token-xyz"
MBID_ARTIST = "0a1b2c3d-0000-4000-8000-000000000201"
MBID_KIN = "0a1b2c3d-0000-4000-8000-000000000204"
ALBUMS = [
    {"ratingKey": "101", "title": "Album One (Deluxe Edition)", "parentTitle": "The Artist",
     "parentRatingKey": "201", "thumb": "/library/metadata/101/thumb/1700000000"},
    {"ratingKey": "104", "title": "Kin Album", "parentTitle": "Les Kin", "parentRatingKey": "204",
     "thumb": "/library/metadata/104/thumb/11"},
    {"ratingKey": "102", "title": "Second", "parentTitle": "Other & Friend",
     "thumb": "/library/metadata/102/thumb/5"},
    {"ratingKey": "105", "title": "No Picture", "parentTitle": "The Artist", "parentRatingKey": "201"},
    {"ratingKey": "106", "title": "Elsewhere", "parentTitle": "The Artist", "thumb": "http://example.org/a.jpg"},
]
ARTISTS = [
    {"ratingKey": "201", "title": "The Artist", "thumb": "/library/metadata/201/thumb/1700000001",
     "Guid": [{"id": f"mbid://{MBID_ARTIST}"}]},
    # Another name here than LMS's, and Plex's MusicBrainz id beside a guid of
    # another kind.
    {"ratingKey": "204", "title": "Les Kin", "thumb": "/library/metadata/204/thumb/9",
     "Guid": [{"id": "plex://artist/5d07"}, {"id": f"mbid://{MBID_KIN.upper()}"}]},
    {"ratingKey": "202", "title": "Other", "thumb": "/library/metadata/202/thumb/7"},
    {"ratingKey": "203", "title": "No Face"},
]
RECORDS = {
    "201": {"ratingKey": "201", "title": "The Artist", "summary": "A biography.",
            "thumb": "/library/metadata/201/thumb/1700000002",
            "Similar": [{"tag": "Kin One"}, {"tag": "Kin Two"}, {"tag": "Kin One"}]},
    "202": {"ratingKey": "202", "title": "Other", "summary": "", "thumb": "/library/metadata/202/thumb/7"},
    "203": {"ratingKey": "203", "title": "No Face", "summary": "Only words."},
    "204": {"ratingKey": "204", "title": "Les Kin", "summary": "Kin's story.",
            "thumb": "/library/metadata/204/thumb/9"},
}
#: The artist's tracks as the server sorts them, most played first; one
#: recording twice, and one the wider world has no count for.
TRACKS = {"201": [{"title": "Big Hit", "ratingCount": 900000}, {"title": "Second Hit", "ratingCount": 5000},
                  {"title": "Big Hit", "ratingCount": 800}, {"title": "Unheard"}]}

# --- lyrics (the fourth step): an album's tracks, their records, their streams
LYRICFIND = "com.plexapp.agents.lyricfind"
CHILDREN = {
    "105": [{"ratingKey": "301", "title": "Words", "duration": 200000},
            {"ratingKey": "306", "title": "Words", "duration": 400000},
            {"ratingKey": "302", "title": "Timed Words", "duration": 180000},
            {"ratingKey": "303", "title": "Silent"}, {"ratingKey": "304", "title": "Refused"}],
    "104": [{"ratingKey": "305", "title": "Kin Song"}],
}


def _lyric(key, provider=LYRICFIND, timed=False):
    return {"streamType": 4, "key": f"/library/streams/{key}", "provider": provider,
            "codec": "lrc" if timed else "txt", **({"timed": "1"} if timed else {})}


def _track(key, *lyrics):
    return {"ratingKey": key, "Media": [{"Part": [{"Stream": [{"streamType": 2, "codec": "flac"}, *lyrics]}]}]}


RECORDS.update({
    "301": _track("301", _lyric(901), _lyric(902, provider="com.plexapp.agents.localmedia")),
    "306": _track("306", _lyric(907)),
    "302": _track("302", _lyric(904), _lyric(903, timed=True)),
    "303": _track("303"),
    "304": _track("304", _lyric(905)),
    "305": _track("305", _lyric(906, timed=True)),
})
TIMED = ('<MediaContainer size="1"><Lyrics provider="com.plexapp.agents.lyricfind" timed="1" author="a" by=""'
         ' minLines="3"><Line startOffset="23060" endOffset="25000"><Span startOffset="23060" endOffset="25000"'
         ' text="Sung one"/></Line><Line startOffset="65500"><Span text=" "/></Line>'
         '<Line startOffset="125990"><Span text="Sung two"/></Line><Line><Span text="Writers: Somebody"/></Line>'
         '</Lyrics></MediaContainer>')


def _plain(first, provider=LYRICFIND):
    return (f'<MediaContainer size="1"><Lyrics provider="{provider}" timed="0"><Line><Span text="{first}"/></Line>'
            '<Line/><Line><Span text="Second verse"/></Line></Lyrics></MediaContainer>')


STREAMS = {"901": _plain("Licensed words"), "902": _plain("Own file", "com.plexapp.agents.localmedia"),
           "903": TIMED, "904": _plain("Untimed"), "906": TIMED, "907": _plain("The longer take")}


class FakePlex:
    """A Plex Media Server: one music section, one of films, albums by page."""

    def __init__(self, albums=ALBUMS):
        self.albums = albums
        self.asked = []
        self.tokens = set()
        self.refuse_popular = False
        self.lyrics_asked = []

    def app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/library/sections", self.sections)
        app.router.add_get("/library/sections/{key}/all", self.all)
        app.router.add_get("/photo/:/transcode", self.transcode)
        app.router.add_get("/library/metadata/{key}/thumb/{stamp}", self.thumb)
        app.router.add_get("/library/metadata/{key}", self.record)
        app.router.add_get("/library/metadata/{key}/children", self.children)
        app.router.add_get("/library/streams/{key}", self.stream)
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

    async def children(self, request):
        self._seen(request)
        tracks = CHILDREN.get(request.match_info["key"], [])
        return web.json_response({"MediaContainer": {"size": len(tracks), "Metadata": tracks}})

    async def stream(self, request):
        """A lyric, and the 404 that ends the server's allowance (Finding 153)."""
        self._seen(request)
        self.lyrics_asked.append((request.match_info["key"], dict(request.query)))
        found = STREAMS.get(request.match_info["key"])
        if found is None:
            raise web.HTTPNotFound()
        return web.Response(text=found, content_type="text/xml")

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
    assert [q["X-Plex-Container-Start"] for q in pages] == ["0", "2", "4"], "three pages, once"
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


# --- the artist's MusicBrainz id behind the name (the third step) ------------


class _Identity:
    """`ArtistIdentity`, as the providers ask it: `(mbid, score)`, None for
    nobody, False when MusicBrainz could not be asked."""

    def __init__(self, answers):
        self.answers = answers
        self.asked = []

    async def resolve(self, artist, raw=None):
        self.asked.append((artist, raw))
        return self.answers.get(artist)


async def test_an_artist_by_its_musicbrainz_id_only_when_the_name_misses(served):
    fake, url = served
    library = PlexLibrary()
    _lend(library, url)
    assert await library.artist("Kin", MBID_KIN) == (Outcome.FOUND, ("204", "9", "3")), \
        "any case of the id, beside a guid of another kind"
    assert await library.artist("Kin") == (Outcome.MISSING, None)
    assert await library.artist("The Artist", MBID_KIN) == (Outcome.FOUND, ("201", "1700000001", "3")), \
        "the name first, as built"
    assert await library.artist("Nobody", "0a1b2c3d-0000-4000-8000-000000000999") == (Outcome.MISSING, None)
    pages = [(q["type"], q.get("includeGuids")) for path, q in fake.asked if path.endswith("/all")]
    assert ("8", "1") in pages and ("9", None) in pages, "guids asked for the artists only"
    await library.close()


async def test_an_album_by_its_artists_id_and_its_title_when_the_name_misses(served):
    _fake, url = served
    library = PlexLibrary()
    _lend(library, url)
    assert await library.album("Kin", "Kin Album (Remastered)", MBID_KIN) == (Outcome.FOUND, ("104", "11"))
    assert await library.album("Kin", "Kin Album") == (Outcome.MISSING, None)
    assert await library.album("Kin", "Not Theirs", MBID_KIN) == (Outcome.MISSING, None)
    assert await library.album("Kin", "Album One", MBID_KIN) == (Outcome.MISSING, None), \
        "another artist's album of the title is not theirs"
    assert await library.album("The Artist", "Album One", MBID_KIN) == (Outcome.FOUND, ("101", "1700000000")), \
        "the name's answer stands"
    await library.close()


async def test_the_providers_ask_the_artists_id_after_a_miss_and_carry_its_score(served):
    _fake, url = served
    library = PlexLibrary()
    _lend(library, url)
    identity = _Identity({"kin": (MBID_KIN, 93), "busy": False, "nobody": None})
    release = PlexRelease(library, identity=identity)
    artist = PlexArtist(library, identity=identity)

    album = await release.fetch(TrackKey(artist="kin", album="kin album", raw_artist="Kin", raw_album="Kin Album"))
    assert album.outcome is Outcome.FOUND and album.enrichment.album_art == "/plex/cover/104/11"
    assert album.confidence == 93, "the service holds it to its threshold, as the others' answers"
    about = await artist.fetch(TrackKey(artist="kin", raw_artist="Kin"))
    assert about.outcome is Outcome.FOUND and about.confidence == 93
    assert about.enrichment.biography == "Kin's story." and about.enrichment.artist_image == "/plex/cover/204/9"
    assert identity.asked == [("kin", "Kin"), ("kin", "Kin")]

    named = await release.fetch(TrackKey(artist="the artist", album="album one"))
    assert named.outcome is Outcome.FOUND and named.confidence == 100
    assert len(identity.asked) == 2, "a name that finds asks for no id"
    for who in ("busy", "nobody"):
        assert (await artist.fetch(TrackKey(artist=who))).outcome is Outcome.MISSING
    assert (await PlexArtist(library).fetch(TrackKey(artist="kin"))).outcome is Outcome.MISSING, \
        "no identity, the name only"
    await library.close()


def test_the_misses_from_before_the_ids_are_forgotten_once(tmp_path):
    cache = Cache(tmp_path / "enrichment.db")
    missed = TrackKey(artist="kin", album="kin album").scoped("album")
    found = TrackKey(artist="the artist", album="album one").scoped("album")
    cache.put(missed, "plex-release", Answer(Outcome.MISSING))
    cache.put(found, "plex-release", Answer(Outcome.FOUND, Enrichment(album_art="/plex/cover/101/1")))
    cache.put(missed, "coverart", Answer(Outcome.MISSING))
    _lend(PlexLibrary(store=cache), "http://10.0.0.5:32400", server="one")
    assert cache.get(missed, "plex-release") is None, "the id may find it now"
    assert cache.get(found, "plex-release") is not None and cache.get(missed, "coverart") is not None
    cache.put(missed, "plex-release", Answer(Outcome.MISSING))
    _lend(PlexLibrary(store=cache), "http://10.0.0.5:32400", server="one")
    assert cache.get(missed, "plex-release") is not None, "once, not at every lend"
    cache.close()


# --- a track's lyrics, behind LRCLIB's (the fourth step) -------------------


def _words(title="timed words", duration=None, album="No Picture", artist="The Artist"):
    from gexis_core.enrichment import fold
    return TrackKey(artist=fold(artist), album=fold(album), title=fold(title), duration=duration,
                    raw_artist=artist, raw_album=album, raw_title=title)


async def test_a_tracks_lyrics_as_plexamp_asks_them_through_an_album_without_a_cover(served):
    fake, url = served
    library = PlexLibrary()
    _lend(library, url)
    answer = await PlexLyrics(library).fetch(_words())
    assert answer.outcome is Outcome.FOUND and answer.confidence == 100
    found = answer.enrichment
    assert found.lyrics_synced == "[00:23.06]Sung one\n[01:05.50]\n[02:05.99]Sung two"
    assert found.lyrics == "Sung one\n\nSung two\nWriters: Somebody", "the credit, untimed, in the words only"
    assert found.lyrics_source == "Plex · LyricFind"
    assert fake.lyrics_asked == [("903", {"format": "xml", "includeInlineAttribution": "1"})], \
        "the timed one of two, asked as Plexamp asks it"
    await library.close()


async def test_the_librarys_own_file_first_and_of_two_takes_the_nearer_length(served):
    fake, url = served
    library = PlexLibrary()
    _lend(library, url)
    own = (await PlexLyrics(library).fetch(_words("Words", duration=205))).enrichment
    assert (own.lyrics, own.lyrics_synced, own.lyrics_source) == ("Own file\n\nSecond verse", None, "Plex")
    longer = (await PlexLyrics(library).fetch(_words("Words", duration=390))).enrichment
    assert longer.lyrics.startswith("The longer take") and longer.lyrics_source == "Plex · LyricFind"
    assert [key for key, _ in fake.lyrics_asked] == ["902", "907"]
    await library.close()


async def test_no_lyric_stream_is_a_miss_and_a_refused_one_could_not_be_asked(served):
    fake, url = served
    library = PlexLibrary()
    _lend(library, url)
    lyrics = PlexLyrics(library)
    assert (await lyrics.fetch(_words("Silent"))).outcome is Outcome.MISSING
    assert (await lyrics.fetch(_words("Nobody Sings"))).outcome is Outcome.MISSING, "no such track"
    assert (await lyrics.fetch(_words(album="Not Here"))).outcome is Outcome.MISSING, "no such album"
    assert (await lyrics.fetch(_words("Refused"))).outcome is Outcome.UNAVAILABLE, \
        "Finding 153: a listed lyric refused is the allowance spent, not 'none'"
    assert [key for key, _ in fake.lyrics_asked] == ["905"], "the streams' records first, a lyric only when listed"
    assert (await PlexLyrics(PlexLibrary()).fetch(_words())).outcome is Outcome.UNAVAILABLE, "nothing lent"
    await library.close()


async def test_lyrics_by_the_artists_id_when_the_name_misses(served):
    _fake, url = served
    library = PlexLibrary()
    _lend(library, url)
    identity = _Identity({"kin": (MBID_KIN, 93)})
    answer = await PlexLyrics(library, identity=identity).fetch(_words("Kin Song", album="Kin Album", artist="Kin"))
    assert answer.outcome is Outcome.FOUND and answer.confidence == 93
    assert answer.enrichment.lyrics_synced.startswith("[00:23.06]")
    await library.close()


def test_only_plexs_own_lyric_answer_is_read():
    from gexis_core.plex import _lyric_set
    assert _lyric_set(b"not xml") is None
    assert _lyric_set(b"<html><Lyrics/></html>") is None
    assert _lyric_set(b'<MediaContainer size="0"/>') == {"timed": False, "provider": "", "lines": []}
    assert _lyric_set(b"<MediaContainer>" + b" " * 600_000 + b"</MediaContainer>") is None
    assert PlexLyrics.wanted(Enrichment(lyrics="plain"))
    assert not PlexLyrics.wanted(Enrichment(lyrics_synced="[00:01.00]a"))
    assert not PlexLyrics.wanted(Enrichment(instrumental=True))


class _Lrclib:
    name = "lrclib"

    def __init__(self, answer):
        self.answer = answer

    def serves(self, renderer):
        return True

    async def fetch(self, key):
        return self.answer


async def test_the_route_asks_plex_for_lyrics_only_while_they_are_on_screen_and_not_for_a_track_just_begun(
        served, monkeypatch):
    from gexis_core import wsserver
    from gexis_core.enrichment import EnrichmentService
    from gexis_core.model import TrackMetadata

    fake, url = served
    library = PlexLibrary()
    _lend(library, url)
    plain = Answer(Outcome.FOUND, Enrichment(lyrics="Plain", lyrics_source="LRCLIB", sources=("lrclib",)))
    store = StateStore({"spotify": True})
    store.set_active("spotify")
    store.set_metadata("spotify", TrackMetadata(artist="The Artist", album="No Picture", title="Timed Words"))
    service = EnrichmentService([_Lrclib(plain), PlexLyrics(library)], Cache(Path(":memory:")))
    server = StateServer(store, enrichment=service, library=_Library([]), plex=library)
    async with TestClient(TestServer(server.make_app())) as client:
        async def ask():
            return await (await client.get("/enrichment")).json()

        body = await ask()
        assert (body["enrichment"]["lyrics_source"], body["pending"]) == ("LRCLIB", False), "lyrics not on screen"
        store.set_panel(lyrics=True)
        body = await ask()
        assert (body["enrichment"]["lyrics"], body["pending"], body["lyrics_pending"]) == (None, True, True), \
            "a track just begun: Plex not yet, the plain words held back (ADR-0184, 7), the panel looks back"
        assert fake.lyrics_asked == []
        monkeypatch.setattr(wsserver, "LYRICS_SETTLE_S", 0.0)
        body = await ask()
        assert body["enrichment"]["lyrics_source"] == "Plex · LyricFind" and not body["pending"]
        assert body["enrichment"]["lyrics_synced"].startswith("[00:23.06]Sung one")
        assert body["lyrics_pending"] is False
    assert [key for key, _ in fake.lyrics_asked] == ["903"]
    await library.close()


async def test_a_track_just_begun_is_not_held_back_where_plex_would_not_be_asked(served):
    from gexis_core.enrichment import EnrichmentService
    from gexis_core.model import TrackMetadata

    _fake, _url = served
    store = StateStore({"spotify": True})
    store.set_active("spotify")
    store.set_metadata("spotify", TrackMetadata(artist="The Artist", album="No Picture", title="Timed Words"))
    store.set_panel(lyrics=True)
    plain = Answer(Outcome.FOUND, Enrichment(lyrics="Plain", lyrics_source="LRCLIB", sources=("lrclib",)))
    library = PlexLibrary()  # nothing lent
    service = EnrichmentService([_Lrclib(plain), PlexLyrics(library)], Cache(Path(":memory:")))
    server = StateServer(store, enrichment=service, library=_Library([]), plex=library)
    async with TestClient(TestServer(server.make_app())) as client:
        body = await (await client.get("/enrichment")).json()
    assert body["pending"] is False
    await library.close()


class _SlowPlex:
    """Plex's lyrics, answering only when let: still going after the
    enrichment's wait."""
    name = "plex-lyrics"
    behind = "lrclib"
    wanted = staticmethod(PlexLyrics.wanted)

    def __init__(self, answer):
        self.answer, self.go = answer, asyncio.Event()

    def serves(self, renderer):
        return renderer != "radio"

    async def fetch(self, key):
        await self.go.wait()
        return self.answer


def _lyrics_route(provider, *, words=None):
    from gexis_core.enrichment import EnrichmentService
    from gexis_core.model import TrackMetadata

    plain = Answer(Outcome.FOUND, words or Enrichment(lyrics="Plain", lyrics_source="LRCLIB", sources=("lrclib",)))
    store = StateStore({"spotify": True})
    store.set_active("spotify")
    store.set_metadata("spotify", TrackMetadata(artist="The Artist", album="An Album", title="A Song"))
    store.set_panel(lyrics=True)
    service = EnrichmentService([_Lrclib(plain), provider], Cache(Path(":memory:")))
    return service, StateServer(store, enrichment=service, library=_Library([]))


async def test_plain_words_wait_while_plex_is_still_answering_and_timed_ones_replace_them(monkeypatch):
    """ADR-0184, 7 (George, 2026-11-21: timed lyrics first): no plain words
    and then a swap - the panel is told lyrics are coming."""
    from gexis_core import enrichment, wsserver
    monkeypatch.setattr(wsserver, "LYRICS_SETTLE_S", 0.0)
    monkeypatch.setattr(enrichment, "WAIT_S", 0.05)
    timed = Answer(Outcome.FOUND, Enrichment(lyrics="Sung", lyrics_synced="[00:01.00]Sung",
                                             lyrics_source="Plex", sources=("plex-lyrics",)))
    slow = _SlowPlex(timed)
    _service, server = _lyrics_route(slow)
    async with TestClient(TestServer(server.make_app())) as client:
        body = await (await client.get("/enrichment")).json()
        assert (body["enrichment"]["lyrics"], body["enrichment"]["lyrics_source"]) == (None, None)
        assert body["pending"] and body["lyrics_pending"]
        slow.go.set()
        await asyncio.sleep(0)
        body = await (await client.get("/enrichment")).json()
    assert body["enrichment"]["lyrics_synced"] == "[00:01.00]Sung" and body["enrichment"]["lyrics_source"] == "Plex"
    assert not body["lyrics_pending"]


async def test_the_plain_words_show_once_the_wait_is_over_and_timed_ones_still_replace_them(monkeypatch):
    """ADR-0184, 8: at most `LYRICS_WAIT_S`, counted from the first ask with
    the lyrics on screen; a timed answer after it still wins (item 3)."""
    from gexis_core import enrichment, wsserver
    monkeypatch.setattr(wsserver, "LYRICS_SETTLE_S", 0.0)
    monkeypatch.setattr(enrichment, "WAIT_S", 0.05)
    clock = [1000.0]
    monkeypatch.setattr(wsserver, "_now", lambda: clock[0])
    timed = Answer(Outcome.FOUND, Enrichment(lyrics="Sung", lyrics_synced="[00:01.00]Sung",
                                             lyrics_source="Plex", sources=("plex-lyrics",)))
    slow = _SlowPlex(timed)
    _service, server = _lyrics_route(slow)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await (await client.get("/enrichment")).json())["lyrics_pending"]
        clock[0] += wsserver.LYRICS_WAIT_S - 0.5
        assert (await (await client.get("/enrichment")).json())["lyrics_pending"], "still within the wait"
        clock[0] += 0.5
        body = await (await client.get("/enrichment")).json()
        assert body["enrichment"]["lyrics"] == "Plain" and body["enrichment"]["lyrics_source"] == "LRCLIB"
        assert body["pending"] and not body["lyrics_pending"], "Plex still going: the panel looks back"
        slow.go.set()
        await asyncio.sleep(0)
        body = await (await client.get("/enrichment")).json()
    assert body["enrichment"]["lyrics_synced"] == "[00:01.00]Sung"


async def test_no_wait_when_plex_is_backed_off_or_lrclib_already_has_timed_words(monkeypatch):
    """ADR-0184, 9: the allowance spent (item 5's back-off) or nothing left
    for Plex to add - the words show at once."""
    from gexis_core import enrichment
    monkeypatch.setattr(enrichment, "WAIT_S", 0.05)
    slow = _SlowPlex(Answer(Outcome.UNAVAILABLE))
    service, server = _lyrics_route(slow)
    service._unavailable_until["plex-lyrics"] = service._clock() + 900
    async with TestClient(TestServer(server.make_app())) as client:
        body = await (await client.get("/enrichment")).json()
    assert body["enrichment"]["lyrics"] == "Plain" and not body["lyrics_pending"] and not body["pending"]
    timed = Enrichment(lyrics="Sung", lyrics_synced="[00:01.00]Sung", lyrics_source="LRCLIB", sources=("lrclib",))
    _service, server = _lyrics_route(_SlowPlex(Answer(Outcome.UNAVAILABLE)), words=timed)
    async with TestClient(TestServer(server.make_app())) as client:
        body = await (await client.get("/enrichment")).json()
    assert body["enrichment"]["lyrics_synced"] == "[00:01.00]Sung" and not body["lyrics_pending"]
