"""Phase 8 step 2: the enrichment service (ADR-0012, ADR-0040).

No network. The behaviour under test is who gets asked, how often, what is
believed and what is remembered - and in particular the distinction
[Finding 036](../../docs/findings/036-key-free-providers-against-real-tracks.md)
forced: a provider that **could not be asked** has not said there is nothing.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gexis_core.enrichment import (
    MISSING_TTL_S,
    RETRY_AFTER_S,
    Answer,
    Cache,
    Enrichment,
    EnrichmentService,
    Limiter,
    Outcome,
    TrackKey,
)
from gexis_core.model import TrackMetadata


class FakeClock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


class FakeProvider:
    """Answers whatever the test tells it to, and counts being asked."""

    def __init__(self, name, answers, serves=None):
        self.name = name
        self._answers = list(answers)
        self._serves = serves
        self.calls = 0

    def serves(self, renderer):
        return self._serves is None or renderer in self._serves

    async def fetch(self, key):
        self.calls += 1
        if not self._answers:
            return Answer(Outcome.MISSING)
        answer = self._answers[0]
        if len(self._answers) > 1:
            self._answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def _cache():
    return Cache(Path(":memory:"), clock=FakeClock())


def _found(**fields):
    return Answer(Outcome.FOUND, Enrichment(**fields))


KEY = TrackKey.of(TrackMetadata(title="Let There Be Rock", artist="AC/DC",
                               album="Let There Be Rock", duration=362.0))


# --- the key ---------------------------------------------------------------


def test_the_key_is_what_a_track_is_not_what_lms_calls_it():
    """A full rescan renumbers every LMS id (Finding 029), and the same track
    over Bluetooth has no id at all."""
    key = TrackKey.of(TrackMetadata(title="Ghetto Gospel", artist="2Pac",
                                    album="Loyal to the Game", duration=239.7))

    assert key == TrackKey("2pac", "loyal to the game", "ghetto gospel", 239)


def test_punctuation_and_case_do_not_split_the_cache():
    """"School's Out" against "School’s Out" - the curly apostrophe
    MusicBrainz returned in Finding 036."""
    ours = TrackKey.of(TrackMetadata(title="School's Out", artist="Alice Cooper"))
    theirs = TrackKey.of(TrackMetadata(title="School’s Out", artist="ALICE COOPER"))

    assert ours == theirs


def test_a_renderer_with_no_duration_still_has_a_key():
    """Bluetooth often reports none; the track is still worth looking up."""
    key = TrackKey.of(TrackMetadata(title="Almost Done", artist="Morcheeba"))

    assert key.duration is None and not key.is_empty()


def test_a_track_with_no_artist_and_no_title_is_not_looked_up():
    """A stopped renderer, or a stream whose text is a single space."""
    assert TrackKey.of(TrackMetadata(title=None, artist=None)).is_empty()
    assert TrackKey.of(TrackMetadata(title=" ", artist=" ")).is_empty()


# --- the three outcomes ----------------------------------------------------


@pytest.mark.asyncio
async def test_a_miss_is_cached_so_it_is_not_asked_twice():
    """ADR-0012: otherwise every play of an unmatched track re-queries."""
    provider = FakeProvider("mb", [Answer(Outcome.MISSING)])
    service = EnrichmentService([provider], _cache())

    await service.for_track(KEY)
    await service.for_track(KEY)

    assert provider.calls == 1


@pytest.mark.asyncio
async def test_a_server_that_could_not_answer_is_not_cached_as_nothing():
    """**The rule Finding 036 exists for.** MusicBrainz answered 503 "the web
    server is currently busy" for 4 of 9 searches. Caching that as "nothing
    found" would deny a track its enrichment permanently because a server was
    busy once."""
    clock = FakeClock()
    provider = FakeProvider("mb", [Answer(Outcome.UNAVAILABLE), _found(label="Atlantic")])
    service = EnrichmentService([provider], _cache(), clock=clock)

    first = await service.for_track(KEY)
    clock.advance(RETRY_AFTER_S + 1)
    second = await service.for_track(KEY)

    assert first.is_empty()
    assert second.label == "Atlantic"
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_a_provider_that_is_down_is_not_hammered_while_it_is_down():
    """Retried, but not on every track that plays in the meantime."""
    clock = FakeClock()
    provider = FakeProvider("mb", [Answer(Outcome.UNAVAILABLE)])
    service = EnrichmentService([provider], _cache(), clock=clock)

    await service.for_track(KEY)
    clock.advance(RETRY_AFTER_S / 2)
    await service.for_track(TrackKey.of(TrackMetadata(title="Other", artist="Someone")))

    assert provider.calls == 1


@pytest.mark.asyncio
async def test_a_miss_is_re_asked_once_it_is_stale():
    """A provider that had nothing a week ago may have something now."""
    clock = FakeClock()
    cache = Cache(Path(":memory:"), clock=clock)
    provider = FakeProvider("mb", [Answer(Outcome.MISSING), _found(label="Atlantic")])
    service = EnrichmentService([provider], cache)

    await service.for_track(KEY)
    clock.advance(MISSING_TTL_S + 1)
    again = await service.for_track(KEY)

    assert again.label == "Atlantic"
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_a_provider_that_raises_does_not_take_the_service_down():
    """One bad provider must not cost the panel every other field."""
    broken = FakeProvider("broken", [RuntimeError("boom")])
    working = FakeProvider("lrclib", [_found(lyrics="La la la")])
    service = EnrichmentService([broken, working], _cache())

    result = await service.for_track(KEY)

    assert result.lyrics == "La la la"


# --- what is believed ------------------------------------------------------


@pytest.mark.asyncio
async def test_a_low_scoring_match_shows_nothing():
    """ADR-0012: a confidently wrong artist biography is worse than a blank
    panel. MusicBrainz scored every correct match 100 in Finding 036."""
    provider = FakeProvider("mb", [Answer(Outcome.FOUND, Enrichment(biography="Wrong band"), confidence=45)])
    service = EnrichmentService([provider], _cache())

    assert (await service.for_track(KEY)).is_empty()


@pytest.mark.asyncio
async def test_the_first_provider_to_answer_a_field_keeps_it():
    """ADR-0040 §1's "LMS first" only means something if the ones behind it
    cannot overwrite what it said."""
    lms = FakeProvider("lms", [_found(biography="From the plugin", artist_image="http://lms/photo.jpg")])
    wiki = FakeProvider("wikipedia", [_found(biography="From Wikipedia", similar=("Queen",))])
    service = EnrichmentService([lms, wiki], _cache())

    result = await service.for_track(KEY)

    assert result.biography == "From the plugin"
    assert result.similar == ("Queen",)
    assert result.sources == ()


@pytest.mark.asyncio
async def test_a_provider_is_only_asked_for_the_renderers_it_serves():
    """LMS's plugin has nothing to say about a Spotify track: there is no LMS
    id for it (ADR-0040 §1)."""
    lms = FakeProvider("lms", [_found(biography="From the plugin")], serves={"lms"})
    service = EnrichmentService([lms], _cache())

    result = await service.for_track(KEY, renderer="spotify")

    assert lms.calls == 0 and result.is_empty()


# --- the limiter -----------------------------------------------------------


@pytest.mark.asyncio
async def test_the_limiter_spaces_requests_for_one_provider():
    """MusicBrainz answers 503 to *everything* above one request a second,
    so the interval is a floor, not an average (ADR-0012)."""
    clock = FakeClock()
    slept = []

    async def sleep(seconds):
        slept.append(seconds)
        clock.advance(seconds)

    limiter = Limiter(1.1, clock=clock, sleep=sleep)

    await limiter.wait()
    await limiter.wait()
    await limiter.wait()

    assert slept == [pytest.approx(1.1), pytest.approx(1.1)]


@pytest.mark.asyncio
async def test_concurrent_callers_do_not_all_go_at_once():
    """Without the lock, every waiting coroutine reads the same "next
    allowed" time, decides it may go, and the provider sees a burst."""
    clock = FakeClock()

    async def sleep(seconds):
        clock.advance(seconds)
        await asyncio.sleep(0)

    limiter = Limiter(1.0, clock=clock, sleep=sleep)
    starts = []

    async def one():
        await limiter.wait()
        starts.append(clock())

    await asyncio.gather(*(one() for _ in range(4)))

    assert starts == sorted(starts)
    assert starts[-1] - starts[0] >= 3.0


# --- the cache itself ------------------------------------------------------


def test_the_cache_keeps_what_was_found_across_a_restart(tmp_path):
    path = tmp_path / "enrichment.db"
    cache = Cache(path)
    cache.put(KEY, "lrclib", _found(lyrics="La la la", similar=("Queen", "Kiss")))
    cache.close()

    reopened = Cache(path)
    answer = reopened.get(KEY, "lrclib")

    assert answer.outcome is Outcome.FOUND
    assert answer.enrichment.lyrics == "La la la"
    # JSON has no tuples; the dataclass does.
    assert answer.enrichment.similar == ("Queen", "Kiss")


def test_the_cache_answers_nothing_for_a_provider_it_has_not_been_asked_about():
    cache = _cache()
    cache.put(KEY, "lrclib", _found(lyrics="La la la"))

    assert cache.get(KEY, "musicbrainz") is None


# --- warming the tab before it is opened -----------------------------------


@pytest.mark.asyncio
async def test_prefetch_asks_only_the_providers_on_this_network():
    """George, 2026-09-18: why not load it as soon as the artist is playing?
    Because one biography from the key-free set is four requests, MusicBrainz
    allows one a second and answered 503 to 4 of 9 searches, and its own
    guidance discourages speculative polling (Finding 036). LMS's plugin is
    on the LAN and costs nobody else anything, so that half is warmed and the
    rest waits until somebody opens the tab."""
    lms = FakeProvider("lms", [_found(biography="From the plugin")], serves={"lms"})
    wiki = FakeProvider("wikipedia", [_found(biography="From Wikipedia")])
    service = EnrichmentService([lms, wiki], _cache())

    await service.prefetch(KEY, renderer="lms")

    assert lms.calls == 1
    assert wiki.calls == 0


@pytest.mark.asyncio
async def test_what_prefetch_warmed_is_there_when_the_tab_opens():
    lms = FakeProvider("lms", [_found(biography="From the plugin")], serves={"lms"})
    service = EnrichmentService([lms], _cache())

    await service.prefetch(KEY, renderer="lms")
    result = await service.for_track(KEY, renderer="lms")

    assert result.biography == "From the plugin"
    assert lms.calls == 1


@pytest.mark.asyncio
async def test_a_prefetch_that_fails_is_not_an_error_anyone_sees():
    """A warm cache is a convenience, never a duty."""
    service = EnrichmentService([FakeProvider("lms", [RuntimeError("boom")], serves={"lms"})], _cache())

    await service.prefetch(KEY, renderer="lms")
