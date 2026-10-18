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
    key = TrackKey.of(TrackMetadata(title="Track B", artist="Artist B",
                                    album="Album B", duration=239.7))

    assert key == TrackKey("artist b", "album b", "track b", 239)


def test_punctuation_and_case_do_not_split_the_cache():
    """"Night's Out" against "Night’s Out" - the curly apostrophe
    MusicBrainz returned in Finding 036."""
    ours = TrackKey.of(TrackMetadata(title="Night's Out", artist="Artist D"))
    theirs = TrackKey.of(TrackMetadata(title="Night’s Out", artist="ARTIST D"))

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


@pytest.mark.asyncio
async def test_a_provider_that_is_not_configured_does_not_start_the_backoff():
    """**The defect this test exists for.** A missing token made the provider
    answer UNAVAILABLE, which put it in the fifteen-minute backoff meant for
    servers that are down - so a token typed into Settings did nothing for a
    quarter of an hour (George, 2026-09-18)."""
    class NeedsToken(FakeProvider):
        def __init__(self):
            super().__init__("popular", [_found(similar=("Queen",))])
            self.token = None

        def ready(self):
            return bool(self.token)

    provider = NeedsToken()
    service = EnrichmentService([provider], _cache())

    assert (await service.for_track(KEY)).is_empty()
    provider.token = "typed just now"

    assert (await service.for_track(KEY)).similar == ("Queen",)


@pytest.mark.asyncio
async def test_providers_are_asked_at_once_not_one_after_another():
    """**The defect this test exists for.** Asked in order, the lyrics
    waited behind three providers that each start with the same MusicBrainz
    search, so a busy MusicBrainz meant no words on screen at all (George,
    2026-09-18). The merge order is still the providers' own, which is what
    keeps "LMS first" true."""
    started = []
    release = asyncio.Event()

    class Slow(FakeProvider):
        async def fetch(self, key):
            started.append(self.name)
            await release.wait()
            return await super().fetch(key)

    slow = Slow("wikipedia", [_found(biography="Late")])
    quick = Slow("lrclib", [_found(lyrics="La la la")])
    service = EnrichmentService([slow, quick], _cache())

    task = asyncio.ensure_future(service.for_track(KEY))
    # Three turns: `_ask` hands each fetch to a shared task (one per track
    # and provider, 2026-10-06), one hop more before it starts.
    for _ in range(3):
        await asyncio.sleep(0)
    # Both are in flight before either has answered.
    assert set(started) == {"wikipedia", "lrclib"}
    release.set()
    result = await task

    assert result.biography == "Late" and result.lyrics == "La la la"


@pytest.mark.asyncio
async def test_a_slow_provider_does_not_hold_the_answer_back():
    """MusicBrainz retrying a 503 for ten seconds must not keep the lyrics
    off the screen when they arrived in one (George, 2026-09-18). The slow
    one keeps going and its answer is there next time."""
    from gexis_core.enrichment import WAIT_S

    never = asyncio.Event()

    class Slow(FakeProvider):
        async def fetch(self, key):
            await never.wait()
            return _found(biography="Eventually")

    quick = FakeProvider("lrclib", [_found(lyrics="La la la")])
    service = EnrichmentService([Slow("wikipedia", []), quick], _cache())

    async def finish_early():
        await asyncio.sleep(0)
        never.set()

    # The wait is real, so the test drives the clock by finishing the slow
    # provider just after the bounded wait would have expired.
    result = await asyncio.wait_for(service.for_track(KEY), timeout=WAIT_S + 2)

    assert result.lyrics == "La la la"
    never.set()


@pytest.mark.asyncio
async def test_an_answer_says_when_it_is_not_the_whole_answer():
    """The panel used to guess - "no biography yet, ask again" - which left
    the Release tab empty, because its fields were not among the ones being
    watched for (George, 2026-09-18)."""
    never = asyncio.Event()

    class Slow(FakeProvider):
        async def fetch(self, key):
            await never.wait()
            return _found(label="Atlantic")

    service = EnrichmentService(
        [Slow("mb-release", []), FakeProvider("lrclib", [_found(lyrics="La la la")])],
        _cache(),
    )
    pending = []

    result = await service.for_track(KEY, pending=pending)

    assert result.lyrics == "La la la"
    assert pending == ["mb-release"]
    never.set()


@pytest.mark.asyncio
async def test_nothing_pending_when_everyone_answered():
    service = EnrichmentService([FakeProvider("lrclib", [_found(lyrics="La la la")])], _cache())
    pending = []

    await service.for_track(KEY, pending=pending)

    assert pending == []


class TestEnrichmentsOwnRowsAreWired:
    """ADR-0059, 2026-09-24. George: *"wire the rest of the enrichment
    entries which are not wired as of now."* Four rows had no code behind
    them at all. Each is a reason not to *ask* somebody rather than a reason
    to throw their answer away."""

    async def test_a_gated_provider_is_never_asked(self):
        from gexis_core.enrichment import Cache, EnrichmentService, TrackKey

        asked = []

        class Provider:
            name = "lrclib"
            def serves(self, _renderer):
                return True
            async def fetch(self, key):
                asked.append(key)
                raise AssertionError("a gated provider must not be asked")

        service = EnrichmentService([Provider()], Cache(Path(":memory:")), gate=lambda name: False)
        found = await service.for_track(TrackKey(artist="a", title="t"))
        assert not asked
        assert found.to_json()["lyrics"] is None

    async def test_the_threshold_is_read_on_every_ask(self):
        """A service holding the number it was built with would answer to
        yesterday's setting for as long as the daemon ran."""
        from gexis_core.enrichment import Cache, EnrichmentService

        threshold = {"value": 10}
        service = EnrichmentService([], Cache(Path(":memory:")),
                                    confidence_min=lambda: threshold["value"])
        assert service.confidence_min == 10
        threshold["value"] = 90
        assert service.confidence_min == 90

    async def test_a_plain_int_still_works(self):
        from gexis_core.enrichment import Cache, EnrichmentService

        assert EnrichmentService([], Cache(Path(":memory:")),
                                 confidence_min=55).confidence_min == 55


# --- on the go: what reached the screen (2026-10-06) ------------------------

@pytest.mark.asyncio
async def test_asks_that_overlap_share_one_fetch():
    """The panel, a phone and the daemon's cover search each asked while a
    slow provider was still going, and each began the same fetch again -
    the same MusicBrainz searches queued on one limiter."""
    release = asyncio.Event()
    calls = []

    class Slow(FakeProvider):
        async def fetch(self, key):
            calls.append(key)
            await release.wait()
            return await super().fetch(key)

    service = EnrichmentService([Slow("coverart", [_found(album_art="https://cover")])], _cache())
    first = asyncio.ensure_future(service.for_track(KEY))
    second = asyncio.ensure_future(service.for_track(KEY))
    for _ in range(3):
        await asyncio.sleep(0)
    release.set()
    a, b = await first, await second
    assert len(calls) == 1
    assert a.album_art == b.album_art == "https://cover"


def test_a_stored_nobody_is_believed_for_a_week():
    clock = FakeClock()
    cache = Cache(Path(":memory:"), clock=clock)
    cache.remember("mb-artist", "pitbull afrojack", None)
    cache.remember("mb-artist", "ac dc", ["66c6", 100])
    assert cache.recall("mb-artist", "pitbull afrojack", missing_ttl=7 * 24 * 3600) is None
    clock.advance(7 * 24 * 3600 + 1)
    with pytest.raises(KeyError):
        cache.recall("mb-artist", "pitbull afrojack", missing_ttl=7 * 24 * 3600)
    # A found one is not aged out.
    assert cache.recall("mb-artist", "ac dc", missing_ttl=7 * 24 * 3600) == ["66c6", 100]
    assert cache.forget_missing("mb-artist") == 1


@pytest.mark.asyncio
async def test_an_albums_answer_is_one_whatever_the_tracks_length():
    """The same track came as 290 s from LMS and 293 s over Bluetooth, and
    its album was looked up twice."""
    cover = FakeProvider("coverart", [_found(album_art="https://cover")])
    lyrics = FakeProvider("lrclib", [_found(lyrics="la")])
    service = EnrichmentService([cover, lyrics], _cache())
    one = TrackKey.of(TrackMetadata(title="I Wanna Dance", artist="Whitney Houston", album="Whitney", duration=290))
    two = TrackKey.of(TrackMetadata(title="So Emotional", artist="Whitney Houston", album="Whitney", duration=293))
    await service.for_track(one)
    found = await service.for_track(two)
    assert found.album_art == "https://cover"
    assert cover.calls == 1
    # Lyrics are the track's own.
    assert lyrics.calls == 2


@pytest.mark.asyncio
async def test_a_match_below_the_threshold_stays_refused_from_the_cache():
    """A cached answer came back at the default 100: refused once, then
    believed."""
    weak = FakeProvider("coverart", [Answer(Outcome.FOUND, Enrichment(album_art="https://wrong"), confidence=40)])
    service = EnrichmentService([weak], _cache(), confidence_min=90)
    assert (await service.for_track(KEY)).album_art is None
    assert (await service.for_track(KEY)).album_art is None
    assert weak.calls == 1


@pytest.mark.asyncio
async def test_the_covers_are_started_first():
    started = []

    class Note(FakeProvider):
        async def fetch(self, key):
            started.append(self.name)
            return await super().fetch(key)

    service = EnrichmentService([Note("wikipedia", []), Note("mb-release", []), Note("coverart", []),
                                 Note("recording-art", [])], _cache())
    await service.for_track(KEY)
    assert started[:2] == ["coverart", "recording-art"]


@pytest.mark.asyncio
async def test_a_stored_picture_follows_the_lms_server_to_its_new_address():
    """Review, 2026-10-12: a FOUND answer is kept for good, with the LMS
    address it was written with - stale after a new DHCP lease, the player's
    own server instead of a NAS's, or a backup restored elsewhere."""
    key = TrackKey.of(TrackMetadata(title="Example Title", artist="Example Artist",
                                    album="Example Album", duration=200.0))
    cache = _cache()
    old = "http://old-host:9000"
    remote = "https://assets.example.invalid/a.jpg"
    first = EnrichmentService([FakeProvider("fanart", [_found(
        artist_image=f"{old}/imageproxy/{remote}/image_600x600_o.jpg",
        artist_images=(f"{old}/imageproxy/{remote}/image_600x600_o.jpg", remote),
        album_art=f"{old}/imageproxy/mai/album/1/image_300x300_o.jpg")])], cache)
    await first.for_track(key)

    now = {"base": "http://new-host:9000"}
    again = FakeProvider("fanart", [])
    service = EnrichmentService([again], cache, lms_base=lambda: now["base"])
    found = await service.for_track(key)
    assert again.calls == 0
    assert found.artist_image == f"http://new-host:9000/imageproxy/{remote}/image_600x600_o.jpg"
    assert found.artist_images == (found.artist_image, remote), "a picture elsewhere stays as it is"
    assert found.album_art == "http://new-host:9000/imageproxy/mai/album/1/image_300x300_o.jpg"


def test_a_nothing_past_believing_is_cleared_when_the_cache_opens(tmp_path):
    """Review, 2026-10-12: enrichment.db only grew - a stale "nothing" was
    deleted only if the same track was looked up again."""
    clock = FakeClock()
    cache = Cache(tmp_path / "e.db", clock=clock)
    tracks = [TrackKey.of(TrackMetadata(title=f"Title {n}", artist="Example Artist", duration=200.0))
              for n in range(3)]
    cache.put(tracks[0], "wikipedia", Answer(Outcome.MISSING))
    cache.put(tracks[1], "wikipedia", _found(biography="kept"))
    clock.advance(MISSING_TTL_S + 1)
    cache.put(tracks[2], "wikipedia", Answer(Outcome.MISSING))
    cache.close()
    reopened = Cache(tmp_path / "e.db", clock=clock)
    rows = reopened._conn.execute("SELECT outcome FROM enrichment ORDER BY outcome").fetchall()
    assert rows == [("found",), ("missing",)], "the old nothing gone, the fresh one and the answer kept"


def test_the_answers_of_named_providers_can_be_dropped():
    cache = _cache()
    for provider in ("lms", "lms-release", "wikipedia"):
        cache.put(KEY, provider, _found(biography=provider))
    cache.forget_providers("lms", "lms-release")
    assert cache.get(KEY, "lms") is None and cache.get(KEY, "lms-release") is None
    assert cache.get(KEY, "wikipedia") is not None


@pytest.mark.asyncio
async def test_lyrions_stored_answers_go_when_the_library_is_rescanned():
    """George, 2026-10-12 (answer 8): LMS's answers carry picture paths with
    its ids, and a rescan renumbers them. The check runs before a stored
    answer is believed, not only when the provider happens to be asked."""
    from gexis_core.artistinfo import SCOPE_CHECK_S, LmsArtistInfo
    from gexis_core.providers import LmsArtistProvider, LmsReleaseProvider

    clock = FakeClock()

    class Lms:
        lastscan = "1"
        asked = 0

        async def __call__(self, command, player="", timeout=None):
            if command[0] == "serverstatus":
                return {"lastscan": self.lastscan}
            self.asked += 1
            if command[1] == "artistphoto":
                return {"url": f"imageproxy/mai/artist/{self.lastscan}/image.png"}
            return {"biography": "Born somewhere."}

    lms = Lms()
    cache = _cache()
    info = LmsArtistInfo(lms, "http://lms:9000", store=cache, clock=clock)
    info.on_forget(lambda: cache.forget_providers(LmsArtistProvider.name, LmsReleaseProvider.name))
    service = EnrichmentService([LmsArtistProvider(info, lambda: 7)], cache, clock=clock)

    first = await service.for_track(KEY, renderer="lms")
    assert "/artist/1/" in first.artist_image
    asked = lms.asked
    assert (await service.for_track(KEY, renderer="lms")).artist_image == first.artist_image
    assert lms.asked == asked, "the same scan: the stored answer"

    lms.lastscan = "2"
    clock.advance(SCOPE_CHECK_S)
    again = await service.for_track(KEY, renderer="lms")
    assert "/artist/2/" in again.artist_image and lms.asked > asked


# --- how large it may grow (George, 2026-10-12, answer 6) --------------------


class FakeDisk:
    """`shutil.disk_usage` for a filesystem the test describes."""

    def __init__(self, total, free):
        self.total, self.free = total, free

    def __call__(self, _path):
        return self


def _track(n):
    return TrackKey(artist=f"artist {n}", album=f"album {n}", title=f"title {n}", duration=200)


def _filled(path, clock, disk, rows=600):
    cache = Cache(path, clock=clock, disk_usage=disk)
    for n in range(rows):
        cache.put(_track(n), "lrclib", _found(lyrics="la " * 1500))
        clock.advance(1)
    return cache


def _rows(cache):
    return {row[0] for row in cache._conn.execute("SELECT key FROM enrichment")}


def test_an_older_cache_gains_a_last_used_time_from_when_each_answer_was_stored(tmp_path):
    import sqlite3

    path = tmp_path / "enrichment.db"
    old = sqlite3.connect(path)
    old.execute("CREATE TABLE enrichment (key TEXT NOT NULL, provider TEXT NOT NULL, outcome TEXT NOT NULL,"
                " value TEXT NOT NULL, stored_at REAL NOT NULL, PRIMARY KEY (key, provider))")
    old.execute("INSERT INTO enrichment VALUES (?, 'lrclib', 'found', '{}', 1234.0)", (KEY.as_text(),))
    old.commit()
    old.close()
    cache = Cache(path)
    assert cache._conn.execute("SELECT used_at FROM enrichment").fetchone() == (1234.0,)
    assert cache.get(KEY, "lrclib") is not None


def test_a_cache_within_its_limits_is_left_alone(tmp_path):
    clock = FakeClock()
    cache = _filled(tmp_path / "enrichment.db", clock, FakeDisk(total=64 * 1024 ** 3, free=30 * 1024 ** 3))
    report = cache.tidy()
    assert report["deleted"] == 0 and len(_rows(cache)) == 600


def test_low_space_drops_the_answers_used_longest_ago_but_not_what_is_playing(tmp_path):
    from gexis_core import enrichment as en

    clock = FakeClock()
    path = tmp_path / "enrichment.db"
    disk = FakeDisk(total=64 * 1024 ** 3, free=30 * 1024 ** 3)
    cache = _filled(path, clock, disk)
    # Track 0 is the oldest stored, but was read just now; track 1 is
    # playing. Both stay; tracks 2 onwards go oldest first.
    assert cache.get(_track(0), "lrclib") is not None
    cache.flush_used()
    size = path.stat().st_size
    disk.free = en.FREE_FLOOR_BYTES - size // 2       # half the cache over the floor
    report = cache.tidy(playing=[_track(1)])

    kept = _rows(cache)
    assert report["deleted"] > 0 and len(kept) < 600
    assert _track(0).as_text() in kept and _track(1).as_text() in kept
    assert _track(2).as_text() not in kept and _track(599).as_text() in kept
    assert path.stat().st_size <= en.TIDY_TO * (size // 2) + 64 * 1024, "the space is handed back"
    assert cache.get(_track(599), "lrclib") is not None, "still usable afterwards"


def test_a_cache_over_its_share_of_the_card_is_trimmed(tmp_path):
    from gexis_core import enrichment as en

    clock = FakeClock()
    path = tmp_path / "enrichment.db"
    disk = FakeDisk(total=64 * 1024 ** 3, free=30 * 1024 ** 3)
    cache = _filled(path, clock, disk)
    size = path.stat().st_size
    disk.total = int(size / en.CACHE_SHARE) // 2      # the cache is 20% of this card
    cache.tidy()
    assert path.stat().st_size <= en.TIDY_TO * size / 2 + 64 * 1024
    assert _track(599).as_text() in _rows(cache)


def test_a_card_made_before_the_limit_is_compacted_once_then_in_steps(tmp_path):
    import sqlite3

    from gexis_core import enrichment as en

    path = tmp_path / "enrichment.db"
    old = sqlite3.connect(path)                     # as every card's is today
    old.execute(Cache._SCHEMA)
    old.commit()
    old.close()
    clock = FakeClock()
    disk = FakeDisk(total=64 * 1024 ** 3, free=30 * 1024 ** 3)
    cache = _filled(path, clock, disk)
    assert cache._conn.execute("PRAGMA auto_vacuum").fetchone() == (0,)
    disk.free = en.FREE_FLOOR_BYTES - path.stat().st_size // 2
    cache.tidy()
    assert sqlite3.connect(path).execute("PRAGMA auto_vacuum").fetchone() == (2,)
    assert not cache._compacting.is_set()
    cache.put(KEY, "lms", _found(biography="b"))      # the daemon's own connection goes on
    assert cache.get(KEY, "lms") is not None
    assert cache._conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    # And next time, a few pages at a time rather than the whole file again.
    for n in range(1000, 1600):
        cache.put(_track(n), "lrclib", _found(lyrics="la " * 1500))
    size = path.stat().st_size
    disk.free = en.FREE_FLOOR_BYTES - size // 2
    cache.tidy()
    assert path.stat().st_size < size


@pytest.mark.asyncio
async def test_the_cache_is_looked_at_on_opening_then_hourly_off_the_loop(tmp_path):
    import threading

    from gexis_core import enrichment as en

    cache = Cache(tmp_path / "enrichment.db", disk_usage=FakeDisk(64 * 1024 ** 3, 30 * 1024 ** 3))
    seen, slept = [], []
    tidy = cache.tidy

    def watched(playing=()):
        seen.append((threading.current_thread() is threading.main_thread(), tuple(playing)))
        return tidy(playing)
    cache.tidy = watched

    async def sleep(seconds):
        slept.append(seconds)
        raise asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        await cache.keep_tidy(lambda: KEY, sleep=sleep)
    assert seen == [(False, (KEY,))] and slept == [en.TIDY_EVERY_S]


def test_a_read_while_the_file_is_compacted_is_a_miss_not_a_wait():
    cache = _cache()
    cache.put(KEY, "lrclib", _found(lyrics="la"))
    cache._compacting.set()
    assert cache.get(KEY, "lrclib") is None
    cache.put(KEY, "lms", _found(biography="b"))
    cache._compacting.clear()
    assert cache.get(KEY, "lms") is None and cache.get(KEY, "lrclib") is not None
