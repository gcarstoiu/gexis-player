"""Phase 8 step 4: the providers (ADR-0040 §1, §2).

No network. The replies are the shapes Finding 036 recorded when these
providers were asked for real tracks from George's library - including the
503 that is the reason `UNAVAILABLE` exists at all.
"""
from __future__ import annotations

import pytest

from gexis_core.enrichment import Outcome, TrackKey
from gexis_core.model import TrackMetadata
from gexis_core.providers import (
    ArtistIdentity,
    ListenBrainzSimilar,
    LmsArtistProvider,
    WikipediaBiography,
)

KEY = TrackKey.of(TrackMetadata(title="Let There Be Rock", artist="AC/DC",
                                album="Let There Be Rock", duration=362.0))

MB_ARTIST = {"artists": [{"id": "66c662b6-6e2f-4930-8610-912e24c63ed1",
                          "name": "AC/DC", "score": 100}]}
MB_RELATIONS = {"relations": [
    {"type": "official homepage", "url": {"resource": "https://www.acdc.com/"}},
    {"type": "wikidata", "url": {"resource": "https://www.wikidata.org/wiki/Q27593"}},
]}
WIKIDATA = {"entities": {"Q27593": {"sitelinks": {"enwiki": {"title": "AC/DC"}}}}}
SUMMARY = {"extract": "AC/DC are an Australian rock band formed in Sydney in 1973.",
           "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/AC/DC"}}}
SIMILAR = [{"name": "Queen", "score": 8322}, {"name": "Led Zeppelin", "score": 8000}]


class FakeHttp:
    """Answers by a fragment of the URL. `None` is what `Http.json` returns
    when a provider could not be asked."""

    def __init__(self, replies):
        self._replies = replies
        self.asked = []

    async def json(self, url, params=None):
        self.asked.append(url)
        # Longest fragment first: a lookup URL contains the search URL.
        for fragment in sorted(self._replies, key=len, reverse=True):
            if fragment in url:
                return self._replies[fragment]
        raise AssertionError(f"nothing recorded for {url}")


class FakeArtistInfo:
    def __init__(self, photo=None, biography=None):
        self._photo = photo
        self._biography = biography

    async def photos(self, ids, size=200):
        return {ids[0]: self._photo}

    async def biography(self, artist_id):
        return self._biography


# --- LMS's own plugin ------------------------------------------------------


@pytest.mark.asyncio
async def test_the_lms_provider_serves_lms_only():
    """Its answers are keyed on an LMS artist id, and a Spotify track has
    none (ADR-0040 §1)."""
    provider = LmsArtistProvider(FakeArtistInfo(), lambda: 7452)

    assert provider.serves("lms")
    assert not provider.serves("spotify")
    assert not provider.serves(None)


@pytest.mark.asyncio
async def test_the_lms_provider_credits_the_server_not_wikipedia():
    provider = LmsArtistProvider(
        FakeArtistInfo(photo="http://lms/photo.jpg", biography="An Australian rock band."),
        lambda: 7452,
    )

    answer = await provider.fetch(KEY)

    assert answer.outcome is Outcome.FOUND
    assert answer.enrichment.biography == "An Australian rock band."
    assert answer.enrichment.biography_source == "LMS"
    assert answer.enrichment.artist_image == "http://lms/photo.jpg"


@pytest.mark.asyncio
async def test_the_lms_provider_is_missing_when_the_track_has_no_artist_id():
    """A radio stream, or a renderer that does not report one."""
    provider = LmsArtistProvider(FakeArtistInfo(biography="…"), lambda: None)

    assert (await provider.fetch(KEY)).outcome is Outcome.MISSING


# --- Wikipedia, the long way round -----------------------------------------


@pytest.mark.asyncio
async def test_a_biography_comes_back_with_the_credit_the_licence_requires():
    """CC BY-SA: the credit and the link are the terms, not decoration
    (ADR-0040 §4)."""
    http = FakeHttp({"ws/2/artist/": MB_ARTIST, "ws/2/artist/66c": MB_RELATIONS,
                     "wikidata.org/w/api.php": WIKIDATA, "page/summary": SUMMARY})

    answer = await WikipediaBiography(http, ArtistIdentity(http)).fetch(KEY)

    assert answer.outcome is Outcome.FOUND
    assert answer.enrichment.biography.startswith("AC/DC are an Australian rock band")
    assert answer.enrichment.biography_source == "Wikipedia, CC BY-SA"
    assert answer.enrichment.biography_url == "https://en.wikipedia.org/wiki/AC/DC"
    assert answer.confidence == 100


@pytest.mark.asyncio
async def test_a_busy_musicbrainz_is_unavailable_not_missing():
    """**The distinction Finding 036 forced.** 4 of 9 searches answered 503
    "the web server is currently busy"; caching that as "no biography" would
    be permanent."""
    http = FakeHttp({"ws/2/artist/": None})

    answer = await WikipediaBiography(http, ArtistIdentity(http)).fetch(KEY)

    assert answer.outcome is Outcome.UNAVAILABLE


@pytest.mark.asyncio
async def test_an_artist_musicbrainz_does_not_know_is_missing_not_unavailable():
    """It answered. It has nothing. That is worth remembering."""
    http = FakeHttp({"ws/2/artist/": {"artists": []}})

    assert (await WikipediaBiography(http, ArtistIdentity(http)).fetch(KEY)).outcome is Outcome.MISSING


@pytest.mark.asyncio
async def test_an_artist_with_no_wikipedia_article_is_missing():
    http = FakeHttp({"ws/2/artist/": MB_ARTIST,
                     "ws/2/artist/66c": {"relations": []}})

    assert (await WikipediaBiography(http, ArtistIdentity(http)).fetch(KEY)).outcome is Outcome.MISSING


@pytest.mark.asyncio
async def test_a_weak_name_match_carries_its_score_so_the_service_can_refuse_it():
    """MusicBrainz scores its own match 0-100; the threshold lives in the
    service, not here (ADR-0012)."""
    http = FakeHttp({"ws/2/artist/": {"artists": [{"id": "x", "name": "Someone", "score": 43}]},
                     "ws/2/artist/x": MB_RELATIONS,
                     "wikidata.org/w/api.php": WIKIDATA, "page/summary": SUMMARY})

    answer = await WikipediaBiography(http, ArtistIdentity(http)).fetch(KEY)

    assert answer.outcome is Outcome.FOUND and answer.confidence == 43


@pytest.mark.asyncio
async def test_wikipedia_is_asked_through_musicbrainz_not_by_name():
    """Artist names are ambiguous and Wikipedia's search does not know it is
    being asked about a musician."""
    http = FakeHttp({"ws/2/artist/": MB_ARTIST, "ws/2/artist/66c": MB_RELATIONS,
                     "wikidata.org/w/api.php": WIKIDATA, "page/summary": SUMMARY})

    await WikipediaBiography(http, ArtistIdentity(http)).fetch(KEY)

    assert any("musicbrainz.org" in url for url in http.asked)
    assert not any("wikipedia.org/w/index.php?search" in url for url in http.asked)


# --- similar artists -------------------------------------------------------


@pytest.mark.asyncio
async def test_similar_artists_come_back_in_order():
    http = FakeHttp({"ws/2/artist/": MB_ARTIST, "similar-artists": SIMILAR})

    answer = await ListenBrainzSimilar(http, ArtistIdentity(http)).fetch(KEY)

    assert answer.enrichment.similar == ("Queen", "Led Zeppelin")


@pytest.mark.asyncio
async def test_a_rejected_algorithm_is_a_missing_section_not_an_error():
    """The enum has already changed under us once (Finding 036), and the
    endpoint carries no stability promise."""
    http = FakeHttp({"ws/2/artist/": MB_ARTIST, "similar-artists": None})

    assert (await ListenBrainzSimilar(http, ArtistIdentity(http)).fetch(KEY)).outcome is Outcome.UNAVAILABLE


@pytest.mark.asyncio
async def test_similar_artists_are_capped():
    http = FakeHttp({"ws/2/artist/": MB_ARTIST,
                     "similar-artists": [{"name": f"Band {i}"} for i in range(50)]})

    answer = await ListenBrainzSimilar(http, ArtistIdentity(http)).fetch(KEY)

    assert len(answer.enrichment.similar) == ListenBrainzSimilar.LIMIT


# --- the release -----------------------------------------------------------


class FakeLibrary:
    def __init__(self, album=None, fails=False):
        self._album = album
        self._fails = fails
        self.asked = []

    async def album(self, album_id):
        self.asked.append(album_id)
        if self._fails:
            raise RuntimeError("LMS unreachable")
        return self._album


class FakeAlbumInfo(FakeArtistInfo):
    def __init__(self, note=None):
        super().__init__()
        self._note = note

    async def album_note(self, album_id):
        return self._note


ALBUM = {
    "id": 6044, "title": "Live at Montreux 2010", "artist": "Gary Moore",
    "year": 2011, "release_type": "ALBUM",
    "tracks": [{"title": "Over the Hills", "duration": 300.0},
               {"title": "Oh Pretty Woman", "duration": 420.5}],
}


@pytest.mark.asyncio
async def test_a_release_is_read_from_the_library_not_from_the_internet():
    """The year, the type, the track count and the length are all in the
    library the device is already reading (ADR-0038 §1); asking a provider
    on the internet for them would be slower and no more true."""
    from gexis_core.providers import LmsReleaseProvider

    library = FakeLibrary(ALBUM)
    provider = LmsReleaseProvider(library, FakeAlbumInfo(note="A live album."), lambda: 6044)

    answer = await provider.fetch(KEY)

    assert answer.outcome is Outcome.FOUND
    assert answer.enrichment.release_type == "ALBUM"
    assert answer.enrichment.track_count == 2
    assert answer.enrichment.released == "2011"
    assert answer.enrichment.length_s == pytest.approx(720.5)
    assert answer.enrichment.album_note == "A live album."
    assert answer.enrichment.album_note_source == "LMS"
    assert library.asked == [6044]


@pytest.mark.asyncio
async def test_a_release_with_no_review_is_still_worth_having():
    from gexis_core.providers import LmsReleaseProvider

    provider = LmsReleaseProvider(FakeLibrary(ALBUM), FakeAlbumInfo(), lambda: 6044)

    answer = await provider.fetch(KEY)

    assert answer.enrichment.album_note is None
    assert answer.enrichment.track_count == 2


@pytest.mark.asyncio
async def test_a_library_that_cannot_answer_is_unavailable_not_missing():
    """Same rule as everywhere else in this phase: "could not ask" is never
    cached as "nothing there"."""
    from gexis_core.providers import LmsReleaseProvider

    provider = LmsReleaseProvider(FakeLibrary(fails=True), FakeAlbumInfo(), lambda: 6044)

    assert (await provider.fetch(KEY)).outcome is Outcome.UNAVAILABLE


@pytest.mark.asyncio
async def test_a_track_with_no_album_id_asks_the_library_nothing():
    """A radio stream has none."""
    from gexis_core.providers import LmsReleaseProvider

    library = FakeLibrary(ALBUM)
    provider = LmsReleaseProvider(library, FakeAlbumInfo(), lambda: None)

    assert (await provider.fetch(KEY)).outcome is Outcome.MISSING
    assert library.asked == []


# --- lyrics ----------------------------------------------------------------


GET_HIT = {"trackName": "All Out", "artistName": "2Pac", "instrumental": False,
           "plainLyrics": "Line one\nLine two",
           "syncedLyrics": "[00:12.00] Line one\n[00:18.50] Line two"}


@pytest.mark.asyncio
async def test_lyrics_with_a_duration_are_taken_as_matched():
    """`/api/get` wants artist, track, album and a duration within ±2 s; when
    it answers, LRCLIB has matched the recording itself."""
    from gexis_core.providers import LrclibLyrics

    http = FakeHttp({"lrclib.net/api/get": GET_HIT})

    answer = await LrclibLyrics(http).fetch(KEY)

    assert answer.outcome is Outcome.FOUND and answer.confidence == 100
    assert answer.enrichment.lyrics_synced.startswith("[00:12.00]")
    assert answer.enrichment.lyrics_source == "LRCLIB"


@pytest.mark.asyncio
async def test_without_a_duration_only_an_exact_match_is_used():
    """**The rule Finding 036 forced.** The no-duration fallback returned
    16-20 hits per track, of which 0-19 carried synced lyrics: the top hit is
    not automatically the right one."""
    from gexis_core.enrichment import TrackKey
    from gexis_core.providers import LrclibLyrics

    no_duration = TrackKey.of(TrackMetadata(title="All Out", artist="2Pac"))
    http = FakeHttp({"lrclib.net/api/search": [
        {"trackName": "All Out (Live)", "artistName": "2Pac", "plainLyrics": "wrong"},
        {"trackName": "All Out", "artistName": "Somebody Else", "plainLyrics": "wrong"},
        {"trackName": "All Out", "artistName": "2Pac", "plainLyrics": "right",
         "syncedLyrics": "[00:10.00] right"},
    ]})

    answer = await LrclibLyrics(http).fetch(no_duration)

    assert answer.enrichment.lyrics == "right"
    assert answer.confidence == LrclibLyrics.SEARCH_CONFIDENCE


@pytest.mark.asyncio
async def test_no_exact_match_shows_nothing_rather_than_the_first_hit():
    from gexis_core.enrichment import TrackKey
    from gexis_core.providers import LrclibLyrics

    no_duration = TrackKey.of(TrackMetadata(title="All Out", artist="2Pac"))
    http = FakeHttp({"lrclib.net/api/search": [
        {"trackName": "All Out (Live)", "artistName": "2Pac", "plainLyrics": "wrong"},
    ]})

    assert (await LrclibLyrics(http).fetch(no_duration)).outcome is Outcome.MISSING


@pytest.mark.asyncio
async def test_a_synced_hit_wins_over_an_earlier_plain_one():
    from gexis_core.enrichment import TrackKey
    from gexis_core.providers import LrclibLyrics

    no_duration = TrackKey.of(TrackMetadata(title="All Out", artist="2Pac"))
    http = FakeHttp({"lrclib.net/api/search": [
        {"trackName": "All Out", "artistName": "2Pac", "plainLyrics": "plain only"},
        {"trackName": "All Out", "artistName": "2Pac", "plainLyrics": "both",
         "syncedLyrics": "[00:01.00] both"},
    ]})

    assert (await LrclibLyrics(http).fetch(no_duration)).enrichment.lyrics == "both"


@pytest.mark.asyncio
async def test_an_instrumental_is_an_answer_not_a_blank():
    """The tab says so rather than looking broken."""
    from gexis_core.providers import LrclibLyrics

    http = FakeHttp({"lrclib.net/api/get": {"instrumental": True, "plainLyrics": None,
                                            "syncedLyrics": None}})

    answer = await LrclibLyrics(http).fetch(KEY)

    assert answer.outcome is Outcome.FOUND and answer.enrichment.instrumental


@pytest.mark.asyncio
async def test_a_track_lrclib_does_not_have_falls_through_to_search():
    """404 means "no such recording", not "cannot ask" - so the search is
    still worth trying."""
    from gexis_core.providers import LrclibLyrics

    http = FakeHttp({"lrclib.net/api/get": {}, "lrclib.net/api/search": []})

    assert (await LrclibLyrics(http).fetch(KEY)).outcome is Outcome.MISSING
    assert any("search" in url for url in http.asked)


@pytest.mark.asyncio
async def test_lrclib_being_unreachable_is_unavailable():
    from gexis_core.providers import LrclibLyrics

    http = FakeHttp({"lrclib.net/api/get": None})

    assert (await LrclibLyrics(http).fetch(KEY)).outcome is Outcome.UNAVAILABLE


# --- cover art -------------------------------------------------------------


CAA = {"images": [
    {"front": False, "image": "http://caa/back.jpg", "thumbnails": {"500": "http://caa/back-500.jpg"}},
    {"front": True, "image": "http://caa/front.jpg", "thumbnails": {"500": "http://caa/front-500.jpg"}},
]}
MB_GROUP = {"release-groups": [{"id": "rg-1", "title": "After Hours", "score": 100}]}


@pytest.mark.asyncio
async def test_cover_art_is_the_front_one_at_the_size_the_panel_draws():
    """For a renderer that sends no artwork at all - Bluetooth often sends
    none (George, 2026-09-18)."""
    from gexis_core.providers import CoverArtProvider

    http = FakeHttp({"release-group/?": MB_GROUP, "ws/2/release-group/": MB_GROUP,
                     "coverartarchive.org": CAA})

    answer = await CoverArtProvider(http).fetch(KEY)

    assert answer.outcome is Outcome.FOUND
    assert answer.enrichment.album_art == "http://caa/front-500.jpg"


@pytest.mark.asyncio
async def test_a_release_the_archive_has_no_art_for_is_missing():
    """The archive answers 404, which is an answer: it has nothing."""
    from gexis_core.providers import CoverArtProvider

    http = FakeHttp({"ws/2/release-group/": MB_GROUP, "coverartarchive.org": {}})

    assert (await CoverArtProvider(http).fetch(KEY)).outcome is Outcome.MISSING


@pytest.mark.asyncio
async def test_an_archive_that_cannot_be_reached_is_unavailable():
    from gexis_core.providers import CoverArtProvider

    http = FakeHttp({"ws/2/release-group/": MB_GROUP, "coverartarchive.org": None})

    assert (await CoverArtProvider(http).fetch(KEY)).outcome is Outcome.UNAVAILABLE


@pytest.mark.asyncio
async def test_a_track_with_no_album_name_is_not_looked_up():
    """AVRCP sometimes sends a title and nothing else; a release group cannot
    be identified from that."""
    from gexis_core.enrichment import TrackKey
    from gexis_core.providers import CoverArtProvider

    http = FakeHttp({})
    key = TrackKey.of(TrackMetadata(title="Some Song", artist="Somebody"))

    assert (await CoverArtProvider(http).fetch(key)).outcome is Outcome.MISSING
    assert http.asked == []


# --- the artist page's own lookup ------------------------------------------


@pytest.mark.asyncio
async def test_the_artist_page_asks_lms_first_then_the_rest():
    """ADR-0038 §2 left About and Similar undrawn "until Phase 8"; this is
    Phase 8. The order is ADR-0040 §1's, from the id the library already has,
    with the key-free providers keyed on the name."""
    from aiohttp.test_utils import TestClient, TestServer

    from gexis_core.enrichment import Cache, EnrichmentService
    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer
    from pathlib import Path as _P

    class Info:
        async def photos(self, ids, size=200):
            return {ids[0]: "http://lms/photo.jpg"}

        async def biography(self, artist_id):
            return "From the plugin."

    http = FakeHttp({"ws/2/artist/": MB_ARTIST, "ws/2/artist/66c": MB_RELATIONS,
                     "wikidata.org/w/api.php": WIKIDATA, "page/summary": SUMMARY,
                     "similar-artists": SIMILAR})
    identity = ArtistIdentity(http)
    service = EnrichmentService(
        [WikipediaBiography(http, identity), ListenBrainzSimilar(http, identity)],
        Cache(_P(":memory:")),
    )
    server = StateServer(StateStore({}), artistinfo=Info(), enrichment=service)

    async with TestClient(TestServer(server.make_app())) as client:
        body = await (await client.get("/library/artist-info?id=7452&name=AC%2FDC")).json()

    found = body["enrichment"]
    # LMS wins the biography; ListenBrainz fills what it has nothing for.
    assert found["biography"] == "From the plugin."
    assert found["biography_source"] == "LMS"
    assert found["artist_image"] == "http://lms/photo.jpg"
    assert found["similar"] == ["Queen", "Led Zeppelin"]


@pytest.mark.asyncio
async def test_the_artist_page_falls_back_when_lms_has_nothing():
    from aiohttp.test_utils import TestClient, TestServer

    from gexis_core.enrichment import Cache, EnrichmentService
    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer
    from pathlib import Path as _P

    class Empty:
        async def photos(self, ids, size=200):
            return {ids[0]: None}

        async def biography(self, artist_id):
            return None

    http = FakeHttp({"ws/2/artist/": MB_ARTIST, "ws/2/artist/66c": MB_RELATIONS,
                     "wikidata.org/w/api.php": WIKIDATA, "page/summary": SUMMARY,
                     "similar-artists": SIMILAR})
    identity = ArtistIdentity(http)
    service = EnrichmentService(
        [WikipediaBiography(http, identity), ListenBrainzSimilar(http, identity)],
        Cache(_P(":memory:")),
    )
    server = StateServer(StateStore({}), artistinfo=Empty(), enrichment=service)

    async with TestClient(TestServer(server.make_app())) as client:
        body = await (await client.get("/library/artist-info?id=7452&name=AC%2FDC")).json()

    assert body["enrichment"]["biography_source"] == "Wikipedia, CC BY-SA"


@pytest.mark.asyncio
async def test_the_artist_page_needs_a_name():
    from aiohttp.test_utils import TestClient, TestServer

    from gexis_core.enrichment import Cache, EnrichmentService
    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer
    from pathlib import Path as _P

    server = StateServer(StateStore({}),
                         enrichment=EnrichmentService([], Cache(_P(":memory:"))))

    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.get("/library/artist-info?id=7452")).status == 400
