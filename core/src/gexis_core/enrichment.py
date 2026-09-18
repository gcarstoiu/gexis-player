# SPDX-License-Identifier: GPL-3.0-or-later
"""The enrichment service (ADR-0012, ADR-0040): what a track is, beyond what
the renderer said.

**Additive only.** Nothing here ever replaces renderer-supplied text. A fuzzy
match on messy AVRCP strings will sometimes be wrong, and a screen that lies
about what is playing is worse than one that says less (ADR-0012).

**Keyed on (artist, album, title, duration)**, never on LMS ids: a full
rescan renumbers every album and artist id (Finding 029), and the same track
played over Bluetooth has no LMS id at all.

**Three outcomes, not two.** Measured in Finding 036: MusicBrainz's search
answered `503 "the web server is currently busy"` for 4 of 9 searches while
lookups by id answered 4 of 4. ADR-0012 says to cache negative results so an
unmatched track is not re-queried on every play - but if a busy server's 503
lands in that cache, an album loses its enrichment permanently because the
server was busy once. So:

- `FOUND` - cached until the cache is cleared.
- `MISSING` - the provider answered, and has nothing. Cached, for
  `MISSING_TTL_S`, because the answer may change when a provider gains data.
- `UNAVAILABLE` - the provider could not be asked, or could not answer.
  **Never cached**, retried no sooner than `RETRY_AFTER_S`.

Nothing here touches the network; providers do (`providers.py`). This module
decides who to ask, how often, what to believe and what to remember.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
import time
import unicodedata
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path

logger = logging.getLogger("gexis_core.enrichment")

DEFAULT_PATH = Path("/var/lib/gexis-core/enrichment.db")

#: How long a provider's "I have nothing for this" is believed. Long enough
#: that a track played daily is not re-queried daily; short enough that a
#: biography added upstream shows up in a week.
MISSING_TTL_S = 7 * 24 * 3600

#: How long before a provider that could not answer is asked again. Short,
#: because this is a transient failure, not an answer.
RETRY_AFTER_S = 900.0

#: Below this, show nothing (ADR-0012). MusicBrainz scores a search hit 0-100
#: and answered 100 for every correct match in Finding 036, so the bar is set
#: where a wrong answer is unlikely rather than where matches are plentiful.
CONFIDENCE_MIN = 90

#: Warmed as soon as a track starts, because they are on this network and
#: cost nothing anyone else pays for. Everything else waits until somebody
#: opens the tab.
PREFETCH_PROVIDERS = ("lms", "lms-release")

#: How long a track must have been playing before its enrichment is warmed.
#: Skipping through an album would otherwise cost one lookup per track.
PREFETCH_AFTER_S = 8.0


class Outcome(str, Enum):
    FOUND = "found"
    MISSING = "missing"
    UNAVAILABLE = "unavailable"


#: Apostrophes are *deleted*, not turned into spaces like other punctuation.
#: The curly one is dropped by the ASCII fold below and the straight one is
#: not, so treating them like other punctuation splits "School's Out" from
#: "School’s Out" into "school s out" and "schools out" - the two
#: spellings Finding 036 saw for the same album, in George's tags and in
#: MusicBrainz's reply.
_APOSTROPHES = str.maketrans("", "", "'‘’ʼ´`")


def _fold(text: str | None) -> str:
    """One spelling for a cache key. Case, accents and punctuation must not
    split the cache."""
    if not text:
        return ""
    folded = unicodedata.normalize("NFKD", text.translate(_APOSTROPHES))
    folded = folded.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", folded.lower()).strip()


@dataclass(frozen=True)
class TrackKey:
    """What a track is, for cache purposes. Duration is rounded to the second
    because renderers disagree in the decimals, and dropped entirely when a
    renderer does not report one (Bluetooth often does not)."""

    artist: str = ""
    album: str = ""
    title: str = ""
    duration: int | None = None

    @classmethod
    def of(cls, metadata) -> "TrackKey":
        duration = getattr(metadata, "duration", None)
        return cls(
            artist=_fold(getattr(metadata, "artist", None)),
            album=_fold(getattr(metadata, "album", None)),
            title=_fold(getattr(metadata, "title", None)),
            duration=int(duration) if duration else None,
        )

    def as_text(self) -> str:
        return json.dumps([self.artist, self.album, self.title, self.duration])

    def is_empty(self) -> bool:
        """Nothing to look anything up with. A stopped renderer, or a stream
        whose text is a single space (Finding 029 §8a)."""
        return not (self.artist or self.title)


@dataclass(frozen=True)
class Enrichment:
    """What was found. Every field is optional and every field is an
    *addition*: the panel keeps showing what the renderer said."""

    biography: str | None = None
    #: Where the biography came from, because Wikipedia's CC BY-SA and
    #: MusicBrainz's CC BY-NC-SA both require it on screen (ADR-0040 §4).
    biography_source: str | None = None
    biography_url: str | None = None
    similar: tuple[str, ...] = ()
    artist_image: str | None = None
    label: str | None = None
    release_type: str | None = None
    track_count: int | None = None
    #: The release's own note - LMS's plugin calls it an album review.
    album_note: str | None = None
    album_note_source: str | None = None
    released: str | None = None
    #: Total playing time of the release, in seconds.
    length_s: float | None = None
    lyrics: str | None = None
    lyrics_synced: str | None = None
    lyrics_source: str | None = None
    instrumental: bool = False
    #: Which providers contributed, in the order they were asked.
    sources: tuple[str, ...] = ()

    def merged_with(self, other: "Enrichment") -> "Enrichment":
        """`self` wins: the first provider to answer a field keeps it, which
        is what makes ADR-0040 §1's "LMS first" mean anything."""
        fields = {}
        for name, mine in self.__dict__.items():
            if name == "sources":
                continue
            theirs = getattr(other, name)
            fields[name] = mine if mine else theirs
        sources = self.sources + tuple(s for s in other.sources if s not in self.sources)
        return replace(self, **fields, sources=sources)

    def is_empty(self) -> bool:
        return not any(
            getattr(self, name)
            for name in ("biography", "similar", "artist_image", "label",
                         "release_type", "track_count", "album_note", "released",
                         "length_s", "lyrics", "lyrics_synced")
        )

    def to_json(self) -> dict:
        return {
            "biography": self.biography,
            "biography_source": self.biography_source,
            "biography_url": self.biography_url,
            "similar": list(self.similar),
            "artist_image": self.artist_image,
            "label": self.label,
            "release_type": self.release_type,
            "track_count": self.track_count,
            "album_note": self.album_note,
            "album_note_source": self.album_note_source,
            "released": self.released,
            "length_s": self.length_s,
            "lyrics": self.lyrics,
            "lyrics_synced": self.lyrics_synced,
            "lyrics_source": self.lyrics_source,
            "instrumental": self.instrumental,
            "sources": list(self.sources),
        }


@dataclass
class Answer:
    """What a provider gives back: an outcome, and what it found."""

    outcome: Outcome
    enrichment: Enrichment = field(default_factory=Enrichment)
    #: 0-100 where a provider scores its own match (MusicBrainz does).
    confidence: int = 100


class Limiter:
    """One per provider, not one for the service (ADR-0040 §5; ADR-0012 said
    one shared bucket, when the phase assumed a single provider).

    A minimum interval rather than a bucket: MusicBrainz does not throttle
    when exceeded, it answers 503 to *everything* until the rate drops, so
    there is no benefit in saving up allowance to spend in a burst.
    """

    def __init__(self, interval_s: float, *, clock=time.monotonic, sleep=asyncio.sleep) -> None:
        self._interval = interval_s
        self._clock = clock
        self._sleep = sleep
        self._next_at = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        # The lock is what makes this a limiter rather than a suggestion:
        # without it, ten coroutines all read the same `_next_at`, all decide
        # they may go, and the provider sees ten requests at once.
        async with self._lock:
            now = self._clock()
            delay = self._next_at - now
            if delay > 0:
                await self._sleep(delay)
                now = self._clock()
            self._next_at = now + self._interval


class Cache:
    """Persistent, because the alternative is re-querying the same tracks on
    every restart, and the providers have asked us not to (ADR-0012)."""

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS enrichment (
        key TEXT NOT NULL,
        provider TEXT NOT NULL,
        outcome TEXT NOT NULL,
        value TEXT NOT NULL,
        stored_at REAL NOT NULL,
        PRIMARY KEY (key, provider)
    )
    """

    def __init__(self, path: Path = DEFAULT_PATH, *, clock=time.time) -> None:
        self.path = path
        self._clock = clock
        if path != Path(":memory:"):
            path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.execute(self._SCHEMA)
        self._conn.commit()

    def get(self, key: TrackKey, provider: str) -> Answer | None:
        row = self._conn.execute(
            "SELECT outcome, value, stored_at FROM enrichment WHERE key = ? AND provider = ?",
            (key.as_text(), provider),
        ).fetchone()
        if row is None:
            return None
        outcome, value, stored_at = row
        if outcome == Outcome.MISSING.value and self._clock() - stored_at > MISSING_TTL_S:
            # A provider that had nothing a week ago may have something now.
            self.forget(key, provider)
            return None
        return Answer(Outcome(outcome), Enrichment(**_rehydrate(json.loads(value))))

    def put(self, key: TrackKey, provider: str, answer: Answer) -> None:
        if answer.outcome is Outcome.UNAVAILABLE:
            # **The rule Finding 036 exists for.** A provider that could not
            # be asked has not told us there is nothing; caching that would
            # deny a track its enrichment permanently because a server was
            # busy once.
            return
        self._conn.execute(
            "INSERT INTO enrichment (key, provider, outcome, value, stored_at) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(key, provider) DO UPDATE SET "
            "outcome = excluded.outcome, value = excluded.value, stored_at = excluded.stored_at",
            (key.as_text(), provider, answer.outcome.value,
             json.dumps(answer.enrichment.to_json()), self._clock()),
        )
        self._conn.commit()

    def forget(self, key: TrackKey, provider: str) -> None:
        self._conn.execute(
            "DELETE FROM enrichment WHERE key = ? AND provider = ?",
            (key.as_text(), provider),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


def _rehydrate(raw: dict) -> dict:
    """JSON gives lists where the dataclass holds tuples, and carries fields
    an older version may not know."""
    known = set(Enrichment.__dataclass_fields__)
    out = {k: v for k, v in raw.items() if k in known}
    for name in ("similar", "sources"):
        if name in out and out[name] is not None:
            out[name] = tuple(out[name])
    return out


class EnrichmentService:
    """Asks the providers in order, remembers what they said, and publishes
    once. Never on a screen's path: `for_track` is awaited by whatever is
    filling a tab, and now playing has already rendered (ADR-0012)."""

    def __init__(self, providers, cache: Cache, *, clock=time.monotonic,
                 confidence_min: int = CONFIDENCE_MIN) -> None:
        #: In the order they are asked. ADR-0040 §1: LMS's own plugin first
        #: where it answers, the key-free set behind it.
        self._providers = list(providers)
        self._cache = cache
        self._clock = clock
        self._confidence_min = confidence_min
        self._unavailable_until: dict[str, float] = {}

    async def for_track(self, key: TrackKey, *, renderer: str | None = None,
                        only: tuple[str, ...] | None = None) -> Enrichment:
        """`only` names the providers to ask; the rest are left for when
        somebody actually looks (see `prefetch`)."""
        if key.is_empty():
            return Enrichment()
        found = Enrichment()
        for provider in self._providers:
            if only is not None and provider.name not in only:
                continue
            if not provider.serves(renderer):
                continue
            answer = await self._ask(provider, key)
            if answer.outcome is not Outcome.FOUND:
                continue
            if answer.confidence < self._confidence_min:
                # ADR-0012: a confidently wrong biography is worse than a
                # blank panel.
                logger.info("enrichment: %s scored %d for %r, below %d - ignored",
                            provider.name, answer.confidence, key.title, self._confidence_min)
                continue
            found = found.merged_with(answer.enrichment)
        return found

    async def prefetch(self, key: TrackKey, *, renderer: str | None = None) -> None:
        """Warm the cache for a track that has just started, so the Artist
        tab is already filled when somebody opens it (George, 2026-09-18).

        **Only the providers on the local network.** LMS's own plugin costs
        386-1005 ms for a biography and needs no key and no rate limit
        (Finding 035). The key-free providers are a different matter: one
        biography is four requests, MusicBrainz allows one a second and
        answered 503 to 4 of 9 searches (Finding 036), and its own guidance
        discourages speculative polling. Fetching those for every track that
        plays would spend most of that allowance on tabs nobody opens.
        """
        try:
            await self.for_track(key, renderer=renderer, only=PREFETCH_PROVIDERS)
        except Exception as exc:  # a warm cache is a convenience, never a duty
            logger.info("enrichment: prefetch failed: %s", exc)

    async def _ask(self, provider, key: TrackKey) -> Answer:
        cached = self._cache.get(key, provider.name)
        if cached is not None:
            return cached
        until = self._unavailable_until.get(provider.name)
        if until is not None and self._clock() < until:
            return Answer(Outcome.UNAVAILABLE)
        try:
            answer = await provider.fetch(key)
        except Exception as exc:  # a provider must never take the service down
            logger.warning("enrichment: %s failed: %s", provider.name, exc)
            answer = Answer(Outcome.UNAVAILABLE)
        if answer.outcome is Outcome.UNAVAILABLE:
            self._unavailable_until[provider.name] = self._clock() + RETRY_AFTER_S
        else:
            self._unavailable_until.pop(provider.name, None)
        self._cache.put(key, provider.name, answer)
        return answer
