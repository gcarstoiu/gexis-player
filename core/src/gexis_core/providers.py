# SPDX-License-Identifier: GPL-3.0-or-later
"""Who the enrichment service asks (ADR-0040 §1 and §2).

Each provider answers one `Answer`: an outcome, what it found, and how sure
it is. The service (`enrichment.py`) decides what to do with that; nothing
here caches, retries or gives up on its own.

**The outcome mapping is the part worth reading.** Finding 036 watched
MusicBrainz answer `503 "the web server is currently busy"` to 4 of 9
searches while lookups by id answered 4 of 4. So:

- an answer with nothing in it is `MISSING` - the provider looked, and has
  nothing;
- a 503, a timeout, a connection error or an unparseable reply is
  `UNAVAILABLE` - we could not ask, which is **not** the same thing and is
  never cached.

Getting that backwards means an album loses its biography permanently
because a server was busy once.
"""
from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import quote

import aiohttp

from gexis_core.enrichment import Answer, Enrichment, Limiter, Outcome, fold

logger = logging.getLogger("gexis_core.providers")

#: MusicBrainz requires a User-Agent that identifies the application and a
#: way to contact whoever runs it; LRCLIB asks for the same. A generic one
#: is what gets a client blocked.
USER_AGENT = "gexis-player/0.2 ( https://github.com/gcarstoiu/gexis-player )"

#: Per host, from Finding 030's reading of each provider's rules.
RATES = {
    "musicbrainz.org": 1.1,
    "coverartarchive.org": 0.0,
    "api.listenbrainz.org": 1.1,
    "labs.api.listenbrainz.org": 1.1,
    "www.wikidata.org": 0.3,
    "en.wikipedia.org": 0.3,
    "lrclib.net": 0.4,
}

#: Generous, because a MusicBrainz lookup took 5.3 s in Finding 036 and
#: nothing here is on a screen's path.
TIMEOUT_S = 15.0

#: MusicBrainz answers `503 "the web server is currently busy"` often enough
#: to matter - 4 of 9 searches in Finding 036 - and **four providers depend
#: on the same search**: the biography, similar artists, the popularity list
#: and a stream's artwork. It is transient, so it is retried rather than
#: reported, with the host's own limiter still between attempts.
RETRY_ON = (500, 502, 503, 504)
RETRIES = 2


class Http:
    """One session and one limiter per host, shared by every provider."""

    def __init__(self, session_factory=None, *, rates=None) -> None:
        self._session_factory = session_factory
        self._session: aiohttp.ClientSession | None = None
        self._limiters = {host: Limiter(gap) for host, gap in (rates or RATES).items()}

    async def _ensure(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            if self._session_factory is not None:
                self._session = self._session_factory()
            else:
                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=TIMEOUT_S),
                    headers={"User-Agent": USER_AGENT},
                )
        return self._session

    async def json(self, url: str, params: dict | None = None,
                   headers: dict | None = None):
        """The parsed body, or None when the provider could not be asked.

        None means `UNAVAILABLE`, never "nothing found": a caller that cannot
        tell those apart will cache a busy server's 503 forever.
        """
        host = url.split("/")[2]
        for attempt in range(RETRIES + 1):
            limiter = self._limiters.get(host)
            if limiter is not None:
                await limiter.wait()
            session = await self._ensure()
            try:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 404:
                        # The provider answered: it has no such thing.
                        return {}
                    if response.status in RETRY_ON and attempt < RETRIES:
                        logger.info("providers: %s answered %s, retrying", host, response.status)
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    if response.status >= 400:
                        logger.info("providers: %s answered %s", host, response.status)
                        return None
                    return await response.json(content_type=None)
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
                if attempt < RETRIES:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                logger.info("providers: %s did not answer (%s)", host, exc)
                return None
        return None

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()


class ArtistIdentity:
    """Who this artist is on MusicBrainz, resolved once and shared.

    Both the biography and the similar-artists providers need the same
    artist MBID, and each was searching for it separately: two searches, two
    1.1 s waits on the same limiter, against the one endpoint measured
    answering `503 "currently busy"` for 4 of 9 tries (Finding 036). One
    cold open of the Artist tab was seen taking 22 s that way.

    The score comes back with the id, because it is MusicBrainz's own
    opinion of the match and the confidence threshold reads it (ADR-0012).
    """

    #: Where resolved ids are kept between restarts.
    NAMESPACE = "mb-artist"

    def __init__(self, http: Http, store=None) -> None:
        self._http = http
        #: folded artist name -> (mbid, score), or None for "asked, nothing".
        self._known: dict[str, tuple[str, int] | None] = {}
        #: Persistent, when given. An artist's MusicBrainz id does not change
        #: because the daemon restarted, and every lookup of it is a search
        #: against the one endpoint that answers 503 most often.
        self._store = store

    async def resolve(self, artist: str) -> tuple[str, int] | None | bool:
        """`(mbid, score)`, `None` when MusicBrainz has no such artist, and
        `False` when it could not be asked - the three outcomes again."""
        if not artist:
            return None
        if artist in self._known:
            return self._known[artist]
        if self._store is not None:
            try:
                remembered = self._store.recall(self.NAMESPACE, artist)
                self._known[artist] = tuple(remembered) if remembered else None
                return self._known[artist]
            except KeyError:
                pass
            except Exception as exc:
                logger.info("providers: could not read a stored artist id (%s)", exc)
        found = await self._http.json(
            "https://musicbrainz.org/ws/2/artist/",
            {"query": f'artist:"{artist}"', "fmt": "json", "limit": "1"},
        )
        if found is None:
            return False
        artists = found.get("artists") or []
        identity = (artists[0]["id"], int(artists[0].get("score") or 0)) if artists else None
        self._known[artist] = identity
        if self._store is not None:
            try:
                self._store.remember(self.NAMESPACE, artist, list(identity) if identity else None)
            except Exception as exc:
                logger.info("providers: could not store an artist id (%s)", exc)
        return identity


class LmsArtistProvider:
    """LMS's own plugin, first in the order (ADR-0040 §1).

    Serves LMS only: its answers are keyed on an LMS artist id, and a Spotify
    or Bluetooth track has none.
    """

    name = "lms"

    def __init__(self, artistinfo, current_artist_id) -> None:
        self._info = artistinfo
        self._current_artist_id = current_artist_id

    def serves(self, renderer) -> bool:
        return renderer == "lms"

    async def fetch(self, key) -> Answer:
        artist_id = self._current_artist_id()
        if not artist_id:
            return Answer(Outcome.MISSING)
        photos = await self._info.photos([artist_id], size=300)
        biography = await self._info.biography(artist_id)
        if not biography and not photos.get(artist_id):
            return Answer(Outcome.MISSING)
        return Answer(Outcome.FOUND, Enrichment(
            biography=biography,
            # ADR-0040 §4: the line on the panel names whoever actually
            # answered, and here that is the server, not us.
            biography_source="LMS" if biography else None,
            artist_image=photos.get(artist_id),
            sources=("lms",),
        ))


class LmsReleaseProvider:
    """What LMS already knows about the release, plus its plugin's review.

    Everything here but the note is in the library the device is already
    reading: the album's year, its release type, how many tracks it has and
    how long it runs (ADR-0038 §1). Asking a provider on the internet for
    facts the server holds would be slower and no more true.
    """

    name = "lms-release"

    def __init__(self, library, artistinfo, current_album_id) -> None:
        self._library = library
        self._info = artistinfo
        self._current_album_id = current_album_id

    def serves(self, renderer) -> bool:
        return renderer == "lms"

    async def fetch(self, key) -> Answer:
        album_id = self._current_album_id()
        if not album_id:
            return Answer(Outcome.MISSING)
        try:
            album = await self._library.album(album_id)
        except Exception as exc:
            logger.info("providers: the library could not answer for album %s (%s)", album_id, exc)
            return Answer(Outcome.UNAVAILABLE)
        tracks = album.get("tracks") or []
        note = await self._info.album_note(album_id)
        length = sum(t.get("duration") or 0 for t in tracks) or None
        return Answer(Outcome.FOUND, Enrichment(
            release_type=album.get("release_type"),
            track_count=len(tracks) or None,
            released=str(album["year"]) if album.get("year") else None,
            length_s=length,
            album_note=note,
            album_note_source="LMS" if note else None,
            sources=("lms-release",),
        ))


class ListenBrainzPopular:
    """What the wider world plays most by this artist (ADR-0040 §2).

    The panel keeps only the ones this library holds, so the list is
    something to press rather than something to want: a chart of tracks
    nobody here can play would be an advertisement.
    """

    name = "popular"
    LIMIT = 30

    #: **Blocked, 2026-09-18.** This endpoint answered 200 with 878
    #: recordings in the morning and `401 "Due to bad actors and AI scrapers
    #: causing undue traffic on our sites, you need to provide an Auth token
    #: for this endpoint"` in the afternoon. A token is a per-user setting,
    #: which ADR-0040 chose this provider set specifically to avoid. The
    #: provider is left in place because it costs nothing when it fails -
    #: 401 is `UNAVAILABLE`, the section simply does not draw - and because
    #: the decision about what to do instead is George's.

    def __init__(self, http: Http, identity: ArtistIdentity, token=None) -> None:
        self._http = http
        self._identity = identity
        #: Read on every call rather than held: a token typed into Settings
        #: has to work without restarting the daemon.
        self._token = token or (lambda: None)

    def serves(self, renderer) -> bool:
        return True

    def ready(self) -> bool:
        """No token, nothing to ask. Answered here rather than by failing a
        request, so that typing one into Settings works at once instead of
        after the service's backoff expires."""
        return bool(self._token())

    async def fetch(self, key) -> Answer:
        token = self._token()
        if not token:
            # Not "nothing found": the list exists and we may not have it.
            return Answer(Outcome.UNAVAILABLE)
        if not key.artist:
            return Answer(Outcome.MISSING)
        who = await self._identity.resolve(key.artist)
        if who is False:
            return Answer(Outcome.UNAVAILABLE)
        if who is None:
            return Answer(Outcome.MISSING)
        mbid, score = who
        found = await self._http.json(
            f"https://api.listenbrainz.org/1/popularity/top-recordings-for-artist/{mbid}",
            headers={"Authorization": f"Token {token}"},
        )
        if found is None:
            return Answer(Outcome.UNAVAILABLE, confidence=score)
        names = tuple(
            str(entry["recording_name"]) for entry in (found or [])
            if isinstance(entry, dict) and entry.get("recording_name")
        )[: self.LIMIT]
        if not names:
            return Answer(Outcome.MISSING, confidence=score)
        return Answer(Outcome.FOUND, Enrichment(popular=names, sources=("popular",)),
                      confidence=score)


class FanartArtistImage:
    """Artist pictures from fanart.tv (George, 2026-09-18).

    **Keyed on the MusicBrainz artist id**, which this daemon already
    resolves and now remembers on disk - so the cost here is one fanart call
    per artist, not a search as well.

    Finding 030's notes still apply: a personal key sees an image about two
    days after it is added where a project key waits seven, and fanart's own
    guidance prefers one project key to a key per user. This reads whatever
    key is in Settings and sends it as `api_key`; there is nothing to send
    when it is empty, so the provider simply is not ready.
    """

    name = "fanart"
    BASE = "https://webservice.fanart.tv/v3/music"
    #: In the order the panel would rather have them: a portrait first,
    #: then the wide background, then the logo-free thumb.
    PREFERRED = ("artistthumb", "artistbackground", "musicbanner")

    #: What the panel draws an artist picture at: 262px on the artist page,
    #: 64px on now playing's Artist tab. ADR-0038 §7's ladder.
    SIZE = 300

    def __init__(self, http: Http, identity: ArtistIdentity, key=None,
                 proxy_base: str | None = None) -> None:
        self._http = http
        self._identity = identity
        self._key = key or (lambda: None)
        #: fanart serves the original: measured 2026-09-18 at 246-826 KB for
        #: five artists, for circles 132px and 64px across. LMS's image
        #: proxy resizes anything remote (the same route the artist plugin's
        #: own remote pictures take), so the panel is handed a sized JPEG
        #: rather than most of a megabyte.
        self._proxy_base = (proxy_base or "").rstrip("/")

    def serves(self, renderer) -> bool:
        return True

    def ready(self) -> bool:
        return bool(self._key())

    async def fetch(self, key) -> Answer:
        api_key = self._key()
        if not api_key:
            return Answer(Outcome.UNAVAILABLE)
        if not key.artist:
            return Answer(Outcome.MISSING)
        who = await self._identity.resolve(key.artist)
        if who is False:
            return Answer(Outcome.UNAVAILABLE)
        if who is None:
            return Answer(Outcome.MISSING)
        mbid, score = who
        found = await self._http.json(f"{self.BASE}/{mbid}", {"api_key": api_key})
        if found is None:
            return Answer(Outcome.UNAVAILABLE, confidence=score)
        for kind in self.PREFERRED:
            images = found.get(kind) or []
            url = next((i.get("url") for i in images if isinstance(i, dict) and i.get("url")), None)
            if url:
                return Answer(Outcome.FOUND,
                              Enrichment(artist_image=self._sized(url), sources=("fanart",)),
                              confidence=score)
        return Answer(Outcome.MISSING, confidence=score)

    def _sized(self, url: str) -> str:
        if not self._proxy_base:
            return url
        return f"{self._proxy_base}/imageproxy/{url}/image_{self.SIZE}x{self.SIZE}_o.jpg"


#: What a renderer adds to a title and a lyrics site does not: a take
#: number, a remaster year, a live tag. Everything from the first bracket
#: or " - " onwards.
_QUALIFIER = re.compile(r"\s*(?:[\(\[].*|-\s+.*)$")


def _without_qualifier(raw_title: str) -> str:
    """"Long Black Limousine  (Take 9)" -> "long black limousine".

    Reads the title as the renderer gave it, because the folded key has
    already lost the brackets and the dash that say where the qualifier
    begins - by then "take 9" is indistinguishable from part of the name.
    """
    return fold(_QUALIFIER.sub("", raw_title or ""))


class MusicBrainzRelease:
    """The release facts for a renderer with no library behind it
    (ADR-0040 §2).

    LMS answers all of this from the library it already holds, so this is
    for Spotify and Bluetooth - which had an empty Release tab with a
    perfectly good album name on screen (George, 2026-09-18).

    One search does it: MusicBrainz's release query returns the label, the
    date, the track count and the release group's type together, with its
    own score for the match.
    """

    name = "mb-release"

    def __init__(self, http: Http) -> None:
        self._http = http

    def serves(self, renderer) -> bool:
        return True

    async def fetch(self, key) -> Answer:
        if not (key.artist and key.album):
            return Answer(Outcome.MISSING)
        found = await self._http.json(
            "https://musicbrainz.org/ws/2/release/",
            {"query": f'artist:"{key.artist}" AND release:"{key.album}"',
             "fmt": "json", "limit": "1"},
        )
        if found is None:
            return Answer(Outcome.UNAVAILABLE)
        releases = found.get("releases") or []
        if not releases:
            return Answer(Outcome.MISSING)
        release = releases[0]
        score = int(release.get("score") or 0)
        labels = [
            (entry.get("label") or {}).get("name")
            for entry in (release.get("label-info") or [])
        ]
        enrichment = Enrichment(
            label=next((name for name in labels if name), None),
            release_type=(release.get("release-group") or {}).get("primary-type"),
            track_count=release.get("track-count"),
            # MusicBrainz gives a year alone as often as a full date, and
            # the panel shows whichever it is.
            released=str(release["date"]) if release.get("date") else None,
            sources=("mb-release",),
        )
        if enrichment.is_empty():
            return Answer(Outcome.MISSING, confidence=score)
        return Answer(Outcome.FOUND, enrichment, confidence=score)


class LrclibLyrics:
    """Lyrics, plain and time-synced, from LRCLIB (ADR-0040 §3).

    **Two ways in, and they are not equally trustworthy.** `/api/get` wants
    artist, track, album *and* a duration within ±2 s, and when it answers it
    has matched the recording. `/api/search` needs no duration - which is how
    Bluetooth has to ask, since it often reports none - but returns up to 20
    unpaged results, and Finding 036 measured 0, 8, 16 and 19 of them
    carrying synced lyrics for four real tracks. **The top hit is not
    automatically the right one**, so a search result has to match the artist
    and title exactly, after folding, or it is not used at all.

    ADR-0040 §3 records what is being accepted here: LRCLIB states no licence
    for the lyrics themselves.
    """

    name = "lrclib"
    #: What a fold-exact search hit is worth. Above `CONFIDENCE_MIN`, but
    #: below a `/api/get` match, which LRCLIB made itself.
    SEARCH_CONFIDENCE = 95
    #: And what a hit on the title *without its qualifier* is worth - still
    #: above the threshold, because the artist has to match exactly and the
    #: words of a take, a remaster or a live cut are the same words.
    BASE_TITLE_CONFIDENCE = 92

    def __init__(self, http: Http) -> None:
        self._http = http

    def serves(self, renderer) -> bool:
        return True

    async def fetch(self, key) -> Answer:
        if not (key.artist and key.title):
            return Answer(Outcome.MISSING)
        if key.duration:
            found = await self._http.json("https://lrclib.net/api/get", {
                "artist_name": key.artist,
                "track_name": key.title,
                "album_name": key.album or key.title,
                "duration": str(key.duration),
            })
            if found is None:
                return Answer(Outcome.UNAVAILABLE)
            if found:
                return self._answer(found, 100)
        return await self._search(key)

    async def _search(self, key) -> Answer:
        answer = await self._search_for(key.title, key, self.SEARCH_CONFIDENCE)
        if answer.outcome is not Outcome.MISSING:
            return answer
        # **Then without the qualifier.** A renderer gives the title as the
        # file has it: measured live over Bluetooth, "Long Black Limousine
        # (Take 9)" found nothing at all while "Long Black Limousine"
        # returned twenty hits, every one of them Elvis Presley with synced
        # words (2026-09-18). A take, a remaster or a live cut is the same
        # song; the artist still has to match exactly, so this loosens which
        # *recording* is accepted and not whose.
        base = _without_qualifier(key.raw_title)
        if base and base != key.title:
            return await self._search_for(base, key, self.BASE_TITLE_CONFIDENCE)
        return answer

    async def _search_for(self, title: str, key, confidence: int) -> Answer:
        hits = await self._http.json("https://lrclib.net/api/search", {
            "artist_name": key.artist, "track_name": title,
        })
        if hits is None:
            return Answer(Outcome.UNAVAILABLE)
        if not isinstance(hits, list):
            return Answer(Outcome.MISSING)
        exact = [
            hit for hit in hits
            if fold(hit.get("artistName")) == key.artist
            and fold(hit.get("trackName")) == title
        ]
        # A synced hit is worth more than an earlier plain one.
        exact.sort(key=lambda hit: bool(hit.get("syncedLyrics")), reverse=True)
        if not exact:
            return Answer(Outcome.MISSING)
        return self._answer(exact[0], confidence)

    def _answer(self, hit: dict, confidence: int) -> Answer:
        plain = (hit.get("plainLyrics") or "").strip() or None
        synced = (hit.get("syncedLyrics") or "").strip() or None
        if hit.get("instrumental"):
            # An answer, and a useful one: the tab says so rather than
            # looking broken.
            return Answer(Outcome.FOUND, Enrichment(
                instrumental=True, lyrics_source="LRCLIB", sources=("lrclib",),
            ), confidence=confidence)
        if not plain and not synced:
            return Answer(Outcome.MISSING)
        return Answer(Outcome.FOUND, Enrichment(
            lyrics=plain, lyrics_synced=synced, lyrics_source="LRCLIB",
            sources=("lrclib",),
        ), confidence=confidence)


class CoverArtProvider:
    """Cover art for a release the renderer has none for (ADR-0040 §2).

    **Who this is for.** LMS hands the panel its own artwork and Spotify
    sends a URL; Bluetooth often sends neither, and a screen with no cover
    is the poorest source the design is meant to degrade to rather than the
    one it should stay at (George, 2026-09-18: no artwork over Bluetooth).

    MusicBrainz identifies the release group, then the Cover Art Archive
    serves the image. `release-group` rather than `release`, because AVRCP
    gives an album name and nothing that says *which* pressing of it.
    """

    name = "coverart"
    #: The archive resizes; 500 is now playing's well (ADR-0038 §7).
    SIZE = 500

    def __init__(self, http: Http) -> None:
        self._http = http

    def serves(self, renderer) -> bool:
        return True

    async def fetch(self, key) -> Answer:
        if not (key.artist and key.album):
            return Answer(Outcome.MISSING)
        found = await self._http.json(
            "https://musicbrainz.org/ws/2/release-group/",
            {"query": f'artist:"{key.artist}" AND releasegroup:"{key.album}"',
             "fmt": "json", "limit": "1"},
        )
        if found is None:
            return Answer(Outcome.UNAVAILABLE)
        groups = found.get("release-groups") or []
        if not groups:
            return Answer(Outcome.MISSING)
        group = groups[0]
        score = int(group.get("score") or 0)
        # The archive answers 404 for a release group it has no art for,
        # which `Http.json` turns into an empty body - an answer, not a
        # failure.
        art = await self._http.json(f"https://coverartarchive.org/release-group/{group['id']}")
        if art is None:
            return Answer(Outcome.UNAVAILABLE, confidence=score)
        images = art.get("images") or []
        front = next((i for i in images if i.get("front")), images[0] if images else None)
        if not front:
            return Answer(Outcome.MISSING, confidence=score)
        thumbnails = front.get("thumbnails") or {}
        url = thumbnails.get(str(self.SIZE)) or thumbnails.get("large") or front.get("image")
        if not url:
            return Answer(Outcome.MISSING, confidence=score)
        return Answer(Outcome.FOUND, Enrichment(album_art=url, sources=("coverart",)),
                      confidence=score)


class RecordingArtProvider:
    """Cover art for a track with no album to look one up by (Phase 8
    criterion 7, ADR-0038 §8a).

    **This is the radio case.** A station's metadata carries the song and
    its artist, and the *station's* name where an album would be (§8a), so
    the album-based lookup above cannot help: it would be searching for a
    release called "Paradiso Berlin". This one matches on the recording
    instead, which is all a stream gives.

    **And it is the weakest evidence in the phase.** No album and no
    duration to corroborate the match, and stream text is not always a song
    at all - Phase 6 saw "KissFM  Live!" arrive as an artist. So the
    provider asks for two things before it believes a hit: MusicBrainz's own
    score, which the service then holds to `CONFIDENCE_MIN`, and the artist
    credit folding to the one we asked about. A wrong cover on a screen
    nobody can correct is worse than the design's pending glyph.
    """

    name = "recording-art"
    SIZE = 500

    def __init__(self, http: Http) -> None:
        self._http = http

    def serves(self, renderer) -> bool:
        return True

    async def fetch(self, key) -> Answer:
        if not (key.artist and key.title):
            return Answer(Outcome.MISSING)
        found = await self._http.json(
            "https://musicbrainz.org/ws/2/recording/",
            {"query": f'recording:"{key.title}" AND artist:"{key.artist}"',
             "fmt": "json", "limit": "3"},
        )
        if found is None:
            return Answer(Outcome.UNAVAILABLE)
        recordings = found.get("recordings") or []
        if not recordings:
            return Answer(Outcome.MISSING)
        top = recordings[0]
        score = int(top.get("score") or 0)
        credited = " ".join(
            str((c.get("artist") or {}).get("name") or c.get("name") or "")
            for c in (top.get("artist-credit") or [])
        )
        if fold(credited) != key.artist:
            # A high score on somebody else is exactly how a station name
            # would get a cover put against it.
            return Answer(Outcome.MISSING, confidence=score)
        release = (top.get("releases") or [{}])[0]
        group = (release.get("release-group") or {}).get("id")
        where = (f"https://coverartarchive.org/release-group/{group}" if group
                 else f"https://coverartarchive.org/release/{release['id']}"
                 if release.get("id") else None)
        if where is None:
            return Answer(Outcome.MISSING, confidence=score)
        art = await self._http.json(where)
        if art is None:
            return Answer(Outcome.UNAVAILABLE, confidence=score)
        images = art.get("images") or []
        front = next((i for i in images if i.get("front")), images[0] if images else None)
        if not front:
            return Answer(Outcome.MISSING, confidence=score)
        thumbnails = front.get("thumbnails") or {}
        url = thumbnails.get(str(self.SIZE)) or thumbnails.get("large") or front.get("image")
        if not url:
            return Answer(Outcome.MISSING, confidence=score)
        return Answer(Outcome.FOUND, Enrichment(album_art=url, sources=("recording-art",)),
                      confidence=score)


class WikipediaBiography:
    """A biography for any renderer, reached the long way round: MusicBrainz
    for the artist's id, its Wikidata relation for the article, then
    Wikipedia's REST summary (ADR-0040 §2).

    **Why not search Wikipedia by name.** Artist names are ambiguous and
    Wikipedia's search has no idea it is being asked about a musician;
    MusicBrainz does, and scores its own match, which is what the confidence
    threshold reads.
    """

    name = "wikipedia"

    def __init__(self, http: Http, identity: ArtistIdentity) -> None:
        self._http = http
        self._identity = identity

    def serves(self, renderer) -> bool:
        return True

    async def fetch(self, key) -> Answer:
        if not key.artist:
            return Answer(Outcome.MISSING)
        who = await self._identity.resolve(key.artist)
        if who is False:
            return Answer(Outcome.UNAVAILABLE)
        if who is None:
            return Answer(Outcome.MISSING)
        mbid, score = who

        relations = await self._http.json(
            f"https://musicbrainz.org/ws/2/artist/{mbid}",
            {"fmt": "json", "inc": "url-rels"},
        )
        if relations is None:
            return Answer(Outcome.UNAVAILABLE, confidence=score)
        wikidata_id = _wikidata_id(relations)
        if not wikidata_id:
            return Answer(Outcome.MISSING, confidence=score)

        entities = await self._http.json(
            "https://www.wikidata.org/w/api.php",
            {"action": "wbgetentities", "ids": wikidata_id, "props": "sitelinks",
             "sitefilter": "enwiki", "format": "json"},
        )
        if entities is None:
            return Answer(Outcome.UNAVAILABLE, confidence=score)
        title = (((entities.get("entities") or {}).get(wikidata_id) or {})
                 .get("sitelinks", {}).get("enwiki", {}) or {}).get("title")
        if not title:
            return Answer(Outcome.MISSING, confidence=score)

        summary = await self._http.json(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title.replace(' ', '_'), safe='')}"
        )
        if summary is None:
            return Answer(Outcome.UNAVAILABLE, confidence=score)
        extract = (summary.get("extract") or "").strip()
        if not extract:
            return Answer(Outcome.MISSING, confidence=score)
        return Answer(Outcome.FOUND, Enrichment(
            biography=extract,
            # CC BY-SA: the credit and the link are the licence's terms, not
            # decoration (ADR-0040 §4).
            biography_source="Wikipedia, CC BY-SA",
            biography_url=((summary.get("content_urls") or {}).get("desktop") or {}).get("page"),
            sources=("wikipedia",),
        ), confidence=score)


def _wikidata_id(relations: dict) -> str | None:
    for relation in relations.get("relations") or []:
        if relation.get("type") != "wikidata":
            continue
        url = ((relation.get("url") or {}).get("resource") or "")
        if "/wiki/" in url:
            return url.rsplit("/wiki/", 1)[1]
    return None


class ListenBrainzSimilar:
    """Similar artists, without a token (ADR-0040 §2).

    **`algorithm` is an enum that has already changed under us.** The value
    in ListenBrainz's own older examples is rejected today (Finding 036), and
    the endpoint carries no stability promise. Every failure here is a
    missing section, never an error on screen.
    """

    name = "listenbrainz"

    #: Accepted 2026-09-18; the reply to a rejected one lists the current set,
    #: which is how the next person finds a replacement.
    ALGORITHM = "session_based_days_7500_session_300_contribution_5_threshold_10_limit_100_filter_True_skip_30"
    LIMIT = 8

    def __init__(self, http: Http, identity: ArtistIdentity) -> None:
        self._http = http
        self._identity = identity

    def serves(self, renderer) -> bool:
        return True

    async def fetch(self, key) -> Answer:
        if not key.artist:
            return Answer(Outcome.MISSING)
        who = await self._identity.resolve(key.artist)
        if who is False:
            return Answer(Outcome.UNAVAILABLE)
        if who is None:
            return Answer(Outcome.MISSING)
        mbid, score = who
        similar = await self._http.json(
            "https://labs.api.listenbrainz.org/similar-artists/json",
            {"artist_mbids": mbid, "algorithm": self.ALGORITHM},
        )
        if similar is None:
            return Answer(Outcome.UNAVAILABLE, confidence=score)
        names = tuple(
            str(entry["name"]) for entry in similar
            if isinstance(entry, dict) and entry.get("name")
        )[: self.LIMIT]
        if not names:
            return Answer(Outcome.MISSING, confidence=score)
        return Answer(Outcome.FOUND, Enrichment(similar=names, sources=("listenbrainz",)),
                      confidence=score)
