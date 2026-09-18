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
