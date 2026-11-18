# SPDX-License-Identifier: GPL-3.0-or-later
"""**The Plex library the Plexamp plugin lends** ([ADR-0184](../../../docs/decisions/0184-plex-information-through-plexamps-claim.md)).

The plugin reads which server Plexamp plays from, that server's address on
this network and its token, and lends them through the contract's `library`
event. They are held here **in memory only**: never in `settings.db`, a
backup or a problem report, and gone when the plugin disconnects.

**What it answers: an album's cover** (Phase 32, acceptance 5), **and an
artist's biography, picture, similar artists and popular tracks** (the
second step, 2026-11-17). From one index of the library's albums and
artists, fetched when first needed and again every few hours, matched on
the same reduced titles and folded names the other providers use - and,
after a miss, by the artist's MusicBrainz id (the third step). **And a
track's lyrics, behind LRCLIB's** (the fourth step, 2026-11-18), asked as
Plexamp asks and only while they are on screen: the server serves about
five every ten minutes (Finding 153). Pictures are served by the core, `/plex/cover/<key>/<stamp>`: a Plex picture's
address needs the token, and the enrichment cache keeps what it finds on
disk and the state goes to every phone on the network.

**Nothing here logs an address, a token or a name.**
"""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import aiohttp

from gexis_core.enrichment import Answer, Enrichment, Outcome, fold, match_title
from gexis_core.providers import lead_artist

logger = logging.getLogger("gexis_core.plex")

#: The one plugin whose library is taken (ADR-0184, how it is built, 1).
LENDER = "plexamp"

#: A sleeping server costs one wait this long, then the provider is not
#: asked again for `RETRY_AFTER_S` (the enrichment service's own backoff).
#: On the local network a Plex server answers in 87-143 ms (Finding 086).
CONNECT_S = 2.0
#: The whole index: a few thousand albums, a page at a time.
INDEX_TIMEOUT_S = 30.0
COVER_TIMEOUT_S = 10.0
#: How long an index is believed. An album added since is found after this,
#: or after the plugin lends again.
INDEX_TTL_S = 6 * 3600.0
#: Albums per page, and at most this many pages (200,000 albums).
PAGE = 500
MAX_PAGES = 400

#: The covers' sizes, in pixels, for `/plex/cover`: Plex scales them. 600 is
#: what the artist page's pictures are; the Cover Art Archive's is 500.
COVER_SIZE = 600
COVER_SIZES = range(100, 1201)

#: A Plex album's or artist's picture: `/library/metadata/<ratingKey>/thumb/<stamp>`.
#: Only these are served through the core, never another of the server's paths.
_THUMB = re.compile(r"^/library/metadata/(\d+)/thumb/(\d+)$")
_DIGITS = re.compile(r"^\d{1,12}$")
#: What the sweep stores of a picture: `<ratingKey>/<stamp>`.
_STORED = re.compile(r"^(\d{1,12})/(\d{1,12})$")
#: An artist's MusicBrainz id among Plex's guids: `mbid://<uuid>`.
_MBID = re.compile(r"^mbid://([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$")

#: The providers' names, in the enrichment cache and ADR-0040's list.
PROVIDER = "plex-release"
ARTIST_PROVIDER = "plex-artist"
#: Where the server whose answers the cache holds is remembered.
NOTES = "plex"
#: **Once: the misses answered before the artist's id was asked** (ADR-0184,
#: third step). Believed for a week otherwise, and the id may find them.
MISSES_FORGOTTEN = "misses-before-ids"
#: **Where ADR-0059's sweep keeps what Plex answered** (ADR-0184, second
#: step, 4): `<key>/<stamp>`, or None for "asked, it has none". Apart from
#: fanart's, so that fanart's are still there when Plex is not.
SWEPT_ARTISTS = "plex-artist"
SWEPT_ALBUMS = "plex-album"

#: An artist's popular tracks: as many as Plexamp's own DJ asks for.
POPULAR = 10
#: Plex keeps up to 30 similar artists (Finding 086).
SIMILAR = 30
#: An artist's own record and popular tracks: 13-17 ms on the LAN (sofapi,
#: 2026-11-17), so this is a server in trouble, not a slow one.
ARTIST_TIMEOUT_S = 10.0

#: **A track's lyrics** (ADR-0184, fourth step): its own provider, so a
#: refusal backs off nothing else (Finding 153).
LYRICS_PROVIDER = "plex-lyrics"
LYRICS_TIMEOUT_S = 10.0
#: Plexamp's order among a track's lyric streams (`LyricPlayerStore`,
#: 4.13.2): the library's own file, else a timed one, else the first.
LOCAL_LYRICS = "com.plexapp.agents.localmedia"
LYRICFIND = "com.plexapp.agents.lyricfind"
#: Lyrics are a few kilobytes (Finding 153: a median of 3,243 bytes).
LYRICS_MAX_BYTES = 512 * 1024


def picture_path(key: str, stamp: str, size: int | None = None) -> str:
    """The core's address of one of the server's pictures."""
    path = f"/plex/cover/{key}/{stamp}"
    return f"{path}?size={size}" if size else path


def swept(store, namespace: str, key: str, size: int) -> str | None:
    """**The picture the sweep found in the Plex library**, as the core's
    address, or None: never asked, asked and none, or not readable."""
    if store is None:
        return None
    try:
        value = store.recall(namespace, key)
    except KeyError:
        return None
    except Exception as exc:  # noqa: BLE001 - a cache that cannot say is not a picture
        logger.info("plex: could not read the sweep's %s (%s)", namespace, type(exc).__name__)
        return None
    match = _STORED.match(value) if isinstance(value, str) else None
    return picture_path(*match.groups(), size) if match else None


@dataclass(frozen=True)
class Lent:
    server: str
    url: str
    token: str = field(repr=False)


def _lendable(message: dict) -> Lent | None:
    """The event's library, or None for nothing lent - or for one that is not
    what the plugin promises: an address of a server on this network."""
    server, url, token = (message.get(k) for k in ("server", "url", "token"))
    if not (isinstance(server, str) and isinstance(url, str) and isinstance(token, str)):
        return None
    if not (server and token):
        return None
    try:
        parts = urlsplit(url)
        parts.port
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.path not in ("", "/"):
        return None
    if not _local(parts.hostname):
        return None
    return Lent(server, url.rstrip("/"), token)


_PLEX_DIRECT = re.compile(r"^(\d+)-(\d+)-(\d+)-(\d+)\.[0-9a-f]+\.plex\.direct$")


def _local(host: str) -> bool:
    """**The core checks it too**: the token goes nowhere that is not on this
    network, whatever a plugin says."""
    match = _PLEX_DIRECT.match(host)
    address = ".".join(match.groups()) if match else host
    try:
        return not ipaddress.ip_address(address).is_global
    except ValueError:
        return False


@dataclass
class _Index:
    """The library's albums, by reduced title: `(artist, key, stamp)`; and
    its artists, by folded name: `(key, stamp or None, section)`. **Behind
    the names** (ADR-0184, third step): its artists by MusicBrainz id, and
    each artist's albums by reduced title, `(key, stamp)`."""

    lent: Lent
    made: float
    albums: dict[str, list[tuple[str, str, str]]]
    artists: dict[str, list[tuple[str, str | None, str]]] = field(default_factory=dict)
    by_mbid: dict[str, tuple[str, str | None, str]] = field(default_factory=dict)
    albums_of: dict[str, dict[str, tuple[str, str]]] = field(default_factory=dict)
    #: **Every album's own key, cover or not** (the fourth step: a track's
    #: lyrics are reached through its album): by reduced title,
    #: `(artist, key)`; and by its artist's key and title.
    album_keys: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    keys_of: dict[str, dict[str, str]] = field(default_factory=dict)


class PlexLibrary:
    """What is lent, and what is asked of it."""

    def __init__(self, *, store=None, clock=time.monotonic, session_factory=None,
                 allowed=lambda: True) -> None:
        #: The enrichment cache: which server its Plex answers came from.
        self._store = store
        self._clock = clock
        #: *Information from Plex* (`plexamp.plex_info`): off, and nothing
        #: Plex said is shown - the sweep's pictures included.
        self._allowed = allowed
        self._session_factory = session_factory
        self._session: aiohttp.ClientSession | None = None
        self._lent: Lent | None = None
        self._index: _Index | None = None
        self._indexing: asyncio.Lock | None = None

    # --- what is lent -------------------------------------------------------

    @property
    def lent(self) -> bool:
        return self._lent is not None

    def ready(self) -> bool:
        """Lent, and *Information from Plex* on."""
        return self._lent is not None and bool(self._allowed())

    def lend(self, plugin_id: str, message: dict) -> bool:
        """A plugin's `library` event. Returns whether what is lent changed."""
        if plugin_id != LENDER:
            logger.info("plex: %s lent a library; only %s's is taken", plugin_id, LENDER)
            return False
        if message.get("kind") != "plex":
            logger.info("plex: a library of another kind was lent, and left")
            return False
        now = _lendable(message)
        if now is None and message.get("url") is not None:
            logger.warning("plex: the library lent is not on this network, or not whole; not taken")
        if now == self._lent:
            return False
        self._lent = now
        self._index = None
        if now is not None:
            self._same_server(now.server)
        logger.info("plex: %s", "a library is lent" if now else "no library is lent")
        return True

    def withdraw(self, plugin_id: str) -> bool:
        """The plugin disconnected: what it lent goes with it."""
        if plugin_id != LENDER or self._lent is None:
            return False
        self._lent = None
        self._index = None
        logger.info("plex: no library is lent (the plugin left)")
        return True

    def _same_server(self, server: str) -> None:
        """**Pictures found on another server are not this one's**: its keys
        mean other albums and artists. The cache's Plex answers and the
        sweep's go when the server changes - not when the same one is lent
        again after a restart."""
        if self._store is None:
            return
        try:
            before = self._store.recall(NOTES, "server")
        except KeyError:
            before = None
        except Exception as exc:  # noqa: BLE001 - a cache that cannot say is no reason to stop
            logger.info("plex: cannot read which server the cache is for (%s)", type(exc).__name__)
            return
        self._forget_misses_once()
        if before == server:
            return
        try:
            if before is not None:
                self._store.forget_providers(PROVIDER, ARTIST_PROVIDER)
                self._store.forget_namespace(SWEPT_ARTISTS)
                self._store.forget_namespace(SWEPT_ALBUMS)
                logger.info("plex: another server than before; what it said is forgotten")
            self._store.remember(NOTES, "server", server)
        except Exception as exc:  # noqa: BLE001
            logger.info("plex: cannot note the server in the cache (%s)", type(exc).__name__)

    def _forget_misses_once(self) -> None:
        try:
            self._store.recall(NOTES, MISSES_FORGOTTEN)
            return
        except KeyError:
            pass
        except Exception as exc:  # noqa: BLE001 - housekeeping
            logger.info("plex: cannot read the misses marker (%s)", type(exc).__name__)
            return
        try:
            gone = self._store.forget_misses(PROVIDER, ARTIST_PROVIDER)
            self._store.remember(NOTES, MISSES_FORGOTTEN, True)
            logger.info("plex: %d misses from before the MusicBrainz ids forgotten", gone)
        except Exception as exc:  # noqa: BLE001
            logger.info("plex: cannot forget the misses (%s)", type(exc).__name__)

    # --- asking it ----------------------------------------------------------

    async def _ensure(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            if self._session_factory is not None:
                self._session = self._session_factory()
            else:
                self._session = aiohttp.ClientSession(
                    headers={"Accept": "application/json", "X-Plex-Product": "Gexis Player"},
                )
        return self._session

    async def _get(self, lent: Lent, path: str, params: dict, *, total: float, raw: bool = False,
                   accept: str = "image/*"):
        """One request to the lent server. `None` when it could not be asked
        or did not answer as it should: the caller's UNAVAILABLE."""
        session = await self._ensure()
        timeout = aiohttp.ClientTimeout(total=total, sock_connect=CONNECT_S)
        try:
            headers = {"X-Plex-Token": lent.token}
            if raw:
                headers["Accept"] = accept
            async with session.get(f"{lent.url}{path}", params=params, timeout=timeout,
                                   headers=headers) as answer:
                if answer.status != 200:
                    logger.info("plex: the server answered %s", answer.status)
                    return None
                if raw:
                    return answer.headers.get("Content-Type", "image/jpeg"), await answer.read()
                return await answer.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            # The exception's class only: its text carries the address.
            logger.info("plex: the server could not be asked (%s)", type(exc).__name__)
            return None

    async def _library(self) -> _Index | None:
        """The index, made now if there is none or it is old."""
        lent = self._lent
        if lent is None:
            return None
        index = self._index
        if index is not None and index.lent == lent and self._clock() - index.made < INDEX_TTL_S:
            return index
        if self._indexing is None:
            self._indexing = asyncio.Lock()
        async with self._indexing:
            index = self._index
            if index is not None and index.lent == lent and self._clock() - index.made < INDEX_TTL_S:
                return index
            started = time.monotonic()
            read = await self._read_library(lent)
            if read is None:
                return None
            if self._lent != lent:
                return None  # lent again meanwhile: this one is not it
            albums, artists, by_mbid, albums_of, album_keys, keys_of = read
            self._index = _Index(lent, self._clock(), albums, artists, by_mbid, albums_of,
                                 album_keys, keys_of)
            logger.info("plex: %d album titles and %d artist names indexed in %.1f s",
                        len(albums), len(artists), time.monotonic() - started)
            return self._index

    async def _read_library(self, lent: Lent) -> tuple[dict, ...] | None:
        sections = await self._get(lent, "/library/sections", {}, total=INDEX_TIMEOUT_S)
        if sections is None:
            return None
        albums: dict[str, list[tuple[str, str, str]]] = {}
        artists: dict[str, list[tuple[str, str | None, str]]] = {}
        by_mbid: dict[str, tuple[str, str | None, str]] = {}
        albums_of: dict[str, dict[str, tuple[str, str]]] = {}
        album_keys: dict[str, list[tuple[str, str]]] = {}
        keys_of: dict[str, dict[str, str]] = {}
        directories = (sections.get("MediaContainer") or {}).get("Directory") or []
        for section in directories:
            if not isinstance(section, dict) or section.get("type") != "artist":
                continue
            key = str(section.get("key") or "")
            if not _DIGITS.match(key):
                continue
            # Albums (type 9), then artists (type 8) with their guids: a page
            # of 500 at a time, summaries left out - a biography is asked
            # when wanted.
            for kind, add in (("9", lambda item: (_add(albums, item, albums_of),
                                                  _add_key(album_keys, keys_of, item))),
                              ("8", lambda item, key=key: _add_artist(artists, item, key, by_mbid))):
                if not await self._pages(lent, key, kind, add):
                    return None
        return albums, artists, by_mbid, albums_of, album_keys, keys_of

    async def _pages(self, lent: Lent, section: str, kind: str, add) -> bool:
        start = 0
        for _page in range(MAX_PAGES):
            page = await self._get(lent, f"/library/sections/{section}/all", {
                "type": kind, "excludeFields": "summary",
                **({"includeGuids": "1"} if kind == "8" else {}),
                "X-Plex-Container-Start": str(start), "X-Plex-Container-Size": str(PAGE),
            }, total=INDEX_TIMEOUT_S)
            if page is None:
                return False
            container = page.get("MediaContainer") or {}
            items = container.get("Metadata") or []
            for item in items:
                add(item)
            start += len(items)
            total = container.get("totalSize")
            if not items or (isinstance(total, int) and start >= total) or len(items) < PAGE:
                break
        return True

    async def album(self, artist: str, title: str,
                    mbid: str | None = None) -> tuple[Outcome, tuple[str, str] | None]:
        """An album's cover, as `(key, stamp)`: FOUND, MISSING, or
        UNAVAILABLE when the server could not be asked. By the title and the
        artist's name; **else, given the artist's MusicBrainz id, by that
        artist's album of the title** (ADR-0184, third step)."""
        index = await self._library()
        if index is None:
            return Outcome.UNAVAILABLE, None
        title = match_title(title)
        wanted = {fold(artist), fold(lead_artist(artist))} - {""}
        for theirs, key, stamp in index.albums.get(title, ()):
            if theirs in wanted:
                return Outcome.FOUND, (key, stamp)
        theirs = index.by_mbid.get(mbid) if mbid else None
        found = index.albums_of.get(theirs[0], {}).get(title) if theirs and title else None
        return (Outcome.FOUND, found) if found else (Outcome.MISSING, None)

    async def artist(self, name: str,
                     mbid: str | None = None) -> tuple[Outcome, tuple[str, str | None, str] | None]:
        """An artist in the library, as `(key, picture stamp or None,
        section)`: by the folded name, else by the lead artist's - *A feat.
        B* is A's - **else by the MusicBrainz id given** (ADR-0184, third
        step). FOUND, MISSING, or UNAVAILABLE."""
        index = await self._library()
        if index is None:
            return Outcome.UNAVAILABLE, None
        for wanted in (fold(name), fold(lead_artist(name))):
            found = index.artists.get(wanted) if wanted else None
            if found:
                return Outcome.FOUND, found[0]
        found = index.by_mbid.get(mbid) if mbid else None
        return (Outcome.FOUND, found) if found else (Outcome.MISSING, None)

    async def about(self, name: str, mbid: str | None = None) -> tuple[Outcome, dict | None]:
        """**What the library knows of an artist**: `biography`, `picture`
        (`(key, stamp)` or None), `similar` and `popular` - the artist's
        tracks in the library the wider world plays most, as Plexamp's own
        DJ asks for them (`sort=ratingCount:desc`, one per recording)."""
        outcome, found = await self.artist(name, mbid)
        if outcome is not Outcome.FOUND:
            return outcome, None
        lent = self._lent
        if lent is None:
            return Outcome.UNAVAILABLE, None
        key, stamp, section = found
        record = await self._get(lent, f"/library/metadata/{key}", {}, total=ARTIST_TIMEOUT_S)
        if record is None:
            return Outcome.UNAVAILABLE, None
        item = ((record.get("MediaContainer") or {}).get("Metadata") or [{}])[0]
        if not isinstance(item, dict):
            return Outcome.MISSING, None
        similar = tuple(_tags(item.get("Similar")))[:SIMILAR]
        # **A popular list that cannot be read is an empty one**, not a
        # failed answer: the biography and the picture are already here, and
        # a server that will not sort by popularity would otherwise never
        # give them.
        tracks = await self._get(lent, f"/library/sections/{section}/all", {
            "artist.id": key, "type": "10", "sort": "ratingCount:desc", "group": "guid",
            "limit": str(POPULAR), "X-Plex-Container-Start": "0", "X-Plex-Container-Size": str(POPULAR),
        }, total=ARTIST_TIMEOUT_S)
        popular = []
        for track in ((tracks or {}).get("MediaContainer") or {}).get("Metadata") or []:
            title = str(track.get("title") or "").strip() if isinstance(track, dict) else ""
            if title and track.get("ratingCount") and title not in popular:
                popular.append(title)
        summary = str(item.get("summary") or "").strip()
        match = _THUMB.match(str(item.get("thumb") or ""))
        return Outcome.FOUND, {
            "biography": summary or None,
            "picture": match.groups() if match and match.group(1) == key else
                       ((key, stamp) if stamp else None),
            "similar": similar,
            "popular": tuple(popular[:POPULAR]),
        }

    async def album_key(self, artist: str, title: str,
                        mbid: str | None = None) -> tuple[Outcome, str | None]:
        """**An album's own key, cover or not** (the fourth step), found as
        `album` finds a cover: the title and the artist's name, else the
        artist's MusicBrainz id."""
        index = await self._library()
        if index is None:
            return Outcome.UNAVAILABLE, None
        title = match_title(title)
        wanted = {fold(artist), fold(lead_artist(artist))} - {""}
        for theirs, key in index.album_keys.get(title, ()):
            if theirs in wanted:
                return Outcome.FOUND, key
        theirs = index.by_mbid.get(mbid) if mbid else None
        found = index.keys_of.get(theirs[0], {}).get(title) if theirs and title else None
        return (Outcome.FOUND, found) if found else (Outcome.MISSING, None)

    async def lyrics(self, album: str, title: str,
                     duration: int | None = None) -> tuple[Outcome, dict | None]:
        """**A track's lyrics, as Plexamp asks for them** (ADR-0184, fourth
        step): the album's track of the folded `title` (of two, the one
        nearer `duration`, in seconds); its lyric streams, from its own
        record - an album's track list does not carry them; the one Plexamp
        would choose, fetched as Plexamp fetches it. `{"timed", "provider",
        "lines": [(start in ms or None, text)]}`.

        MISSING: no such track, or it lists no lyric stream. **UNAVAILABLE
        when a stream it lists is refused**: the server serves about five
        every ten minutes and answers 404 after (Finding 153), which is not "none"."""
        lent = self._lent
        if lent is None or not _DIGITS.match(album):
            return Outcome.UNAVAILABLE, None
        children = await self._get(lent, f"/library/metadata/{album}/children", {},
                                   total=LYRICS_TIMEOUT_S)
        if children is None:
            return Outcome.UNAVAILABLE, None
        tracks = [track for track in (children.get("MediaContainer") or {}).get("Metadata") or ()
                  if isinstance(track, dict) and _DIGITS.match(str(track.get("ratingKey") or ""))
                  and fold(str(track.get("title") or "")) == title]
        if not tracks:
            return Outcome.MISSING, None
        if duration:
            tracks.sort(key=lambda track: abs(_number(track.get("duration")) / 1000 - duration))
        record = await self._get(lent, f"/library/metadata/{tracks[0]['ratingKey']}", {},
                                 total=LYRICS_TIMEOUT_S)
        if record is None:
            return Outcome.UNAVAILABLE, None
        items = (record.get("MediaContainer") or {}).get("Metadata") or [{}]
        streams = _lyric_streams(items[0])
        if not streams:
            return Outcome.MISSING, None
        chosen = (next((s for s in streams if s.get("provider") == LOCAL_LYRICS), None)
                  or next((s for s in streams if str(s.get("timed")) == "1"), None)
                  or streams[0])
        got = await self._get(lent, str(chosen["key"]),
                              {"format": "xml", "includeInlineAttribution": "1"},
                              total=LYRICS_TIMEOUT_S, raw=True, accept="*/*")
        if got is None:
            return Outcome.UNAVAILABLE, None
        found = _lyric_set(got[1])
        if found is None:
            logger.info("plex: a lyric came back in a form not known")
            return Outcome.UNAVAILABLE, None
        return Outcome.FOUND, found

    async def cover(self, key: str, stamp: str, size: int = COVER_SIZE):
        """`(content_type, bytes)` of one of the server's pictures - an
        album's cover or an artist's - at `size`, or None. Through Plex's own
        scaler, as Plex's apps ask for theirs; the picture as it is stored if
        the scaler will not."""
        lent = self._lent
        if lent is None or not (_DIGITS.match(key) and _DIGITS.match(stamp)):
            return None
        thumb = f"/library/metadata/{key}/thumb/{stamp}"
        scaled = await self._get(lent, "/photo/:/transcode", {
            "url": thumb, "width": str(size), "height": str(size), "minSize": "1", "upscale": "0",
        }, total=COVER_TIMEOUT_S, raw=True)
        if scaled is not None:
            return scaled
        return await self._get(lent, thumb, {}, total=COVER_TIMEOUT_S, raw=True)

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()


def _add(found: dict, album, albums_of: dict | None = None) -> None:
    if not isinstance(album, dict):
        return
    match = _THUMB.match(str(album.get("thumb") or ""))
    title = match_title(str(album.get("title") or ""))
    artist = str(album.get("parentTitle") or "")
    if not (match and title):
        return
    key, stamp = match.groups()
    parent = str(album.get("parentRatingKey") or "")
    if albums_of is not None and _DIGITS.match(parent):
        albums_of.setdefault(parent, {}).setdefault(title, (key, stamp))
    if not artist:
        return
    for name in {fold(artist), fold(lead_artist(artist))} - {""}:
        found.setdefault(title, []).append((name, key, stamp))


def _add_artist(found: dict, artist, section: str, by_mbid: dict | None = None) -> None:
    if not isinstance(artist, dict):
        return
    key = str(artist.get("ratingKey") or "")
    name = fold(str(artist.get("title") or ""))
    if not (_DIGITS.match(key) and name):
        return
    match = _THUMB.match(str(artist.get("thumb") or ""))
    stamp = match.group(2) if match and match.group(1) == key else None
    found.setdefault(name, []).append((key, stamp, section))
    if by_mbid is not None:
        for guid in artist.get("Guid") or ():
            ids = _MBID.match(str(guid.get("id") or "").lower()) if isinstance(guid, dict) else None
            if ids:
                by_mbid.setdefault(ids.group(1), (key, stamp, section))


def _add_key(found: dict, keys_of: dict, album) -> None:
    """Every album by its own key, cover or not (`_Index.album_keys`)."""
    if not isinstance(album, dict):
        return
    key = str(album.get("ratingKey") or "")
    title = match_title(str(album.get("title") or ""))
    if not (_DIGITS.match(key) and title):
        return
    parent = str(album.get("parentRatingKey") or "")
    if _DIGITS.match(parent):
        keys_of.setdefault(parent, {}).setdefault(title, key)
    artist = str(album.get("parentTitle") or "")
    for name in {fold(artist), fold(lead_artist(artist))} - {""}:
        found.setdefault(title, []).append((name, key))


#: A lyric stream's key, as the server lists it: asked only in this shape.
_STREAM = re.compile(r"^/library/streams/\d{1,12}$")


def _number(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _lyric_streams(item) -> list[dict]:
    """A track record's lyric streams (`streamType` 4), in the server's order."""
    if not isinstance(item, dict):
        return []
    return [stream
            for media in item.get("Media") or () if isinstance(media, dict)
            for part in media.get("Part") or () if isinstance(part, dict)
            for stream in part.get("Stream") or () if isinstance(stream, dict)
            if str(stream.get("streamType")) == "4" and _STREAM.match(str(stream.get("key") or ""))]


def _lyric_set(body: bytes) -> dict | None:
    """**Plex's lyric answer**, as Plexamp's own parser reads it:
    `<MediaContainer><Lyrics timed provider><Line startOffset><Span text>`.
    An empty container is no lines; None is not an answer at all."""
    if not body or len(body) > LYRICS_MAX_BYTES:
        return None
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return None
    if root.tag != "MediaContainer":
        return None
    lyrics = root.find("Lyrics")
    if lyrics is None:
        return {"timed": False, "provider": "", "lines": []}
    lines = []
    for line in lyrics.findall("Line"):
        text = "".join(span.get("text") or "" for span in line.findall("Span")).strip()
        start = str(line.get("startOffset") or "")
        lines.append((int(start) if start.isdigit() else None, text))
    return {"timed": lyrics.get("timed") == "1", "provider": str(lyrics.get("provider") or ""),
            "lines": lines}


def _stamp(ms: int) -> str:
    """An LRC time, `[mm:ss.xx]`."""
    hundredths = ms // 10
    return f"[{hundredths // 6000:02d}:{hundredths % 6000 // 100:02d}.{hundredths % 100:02d}]"


def lyric_enrichment(lyric: dict) -> Enrichment | None:
    """A lyric as the panel reads lyrics: the words, every line; **timed,
    the lines with a time as LRC** - a line without one (the licensor's
    credit, at the end) stays in the words only; the source, the licensor
    named when there is one. None when it has no words."""
    lines = lyric["lines"]
    if not any(text for _, text in lines):
        return None
    stamped = [(start, text) for start, text in lines if start is not None]
    synced = None
    if lyric["timed"] and any(text for _, text in stamped):
        synced = "\n".join(f"{_stamp(start)}{text}" for start, text in stamped)
    return Enrichment(
        lyrics="\n".join(text for _, text in lines).strip(),
        lyrics_synced=synced,
        lyrics_source="Plex · LyricFind" if lyric["provider"] == LYRICFIND else "Plex",
        sources=("plex",),
    )


def _tags(values) -> list[str]:
    names = []
    for value in values or ():
        tag = str(value.get("tag") or "").strip() if isinstance(value, dict) else ""
        if tag and tag not in names:
            names.append(tag)
    return names


class PlexRelease:
    """**An album's cover from the Plex library, ahead of the internet's**
    (ADR-0184; Phase 32, acceptances 2 and 5). Asked only while a library is
    lent and *Information from Plex* is on."""

    name = PROVIDER

    def __init__(self, plex: PlexLibrary, allowed=lambda: True, identity=None) -> None:
        self._plex = plex
        self._allowed = allowed
        self._identity = identity

    def serves(self, renderer) -> bool:
        # The internet radio's album line is the station's name (ADR-0180).
        return renderer != "radio"

    def ready(self) -> bool:
        return self._plex.lent and bool(self._allowed())

    async def fetch(self, key) -> Answer:
        if not (key.artist and key.album):
            return Answer(Outcome.MISSING)
        artist, album = key.raw_artist or key.artist, key.raw_album or key.album
        outcome, found = await self._plex.album(artist, album)
        score = 100
        if outcome is Outcome.MISSING:
            outcome, found, score = await _by_id(self._identity, key,
                                                 lambda mbid: self._plex.album(artist, album, mbid))
        if outcome is not Outcome.FOUND:
            return Answer(outcome)
        return Answer(Outcome.FOUND, Enrichment(album_art=picture_path(*found),
                                                sources=("plex",)), confidence=score)


async def _by_id(identity, key, ask):
    """**The artist's MusicBrainz id, after a miss by name** (ADR-0184, third
    step): the id the other providers use, from `ArtistIdentity`, and its
    score as the answer's confidence - the service drops one below its
    threshold, as it does theirs. `(outcome, found, score)`; a miss stays a
    miss when MusicBrainz could not be asked, so the providers behind are
    asked as before."""
    if identity is None:
        return Outcome.MISSING, None, 100
    who = await identity.resolve(key.artist, raw=key.raw_artist or None)
    if not who:
        return Outcome.MISSING, None, 100
    mbid, score = who
    outcome, found = await ask(mbid)
    return outcome, found, int(score)


class PlexArtist:
    """**An artist from the Plex library, ahead of everyone else's** (ADR-0184,
    second step, 1): the biography, the picture, similar artists and popular
    tracks. Asked as `PlexRelease` is."""

    name = ARTIST_PROVIDER

    def __init__(self, plex: PlexLibrary, allowed=lambda: True, identity=None) -> None:
        self._plex = plex
        self._allowed = allowed
        self._identity = identity

    def serves(self, renderer) -> bool:
        return True

    def ready(self) -> bool:
        return self._plex.lent and bool(self._allowed())

    async def fetch(self, key) -> Answer:
        if not key.artist:
            return Answer(Outcome.MISSING)
        name = key.raw_artist or key.artist
        outcome, about = await self._plex.about(name)
        score = 100
        if outcome is Outcome.MISSING:
            outcome, about, score = await _by_id(self._identity, key,
                                                 lambda mbid: self._plex.about(name, mbid))
        if outcome is not Outcome.FOUND:
            return Answer(outcome)
        found = Enrichment(
            biography=about["biography"],
            biography_source="Plex" if about["biography"] else None,
            artist_image=picture_path(*about["picture"]) if about["picture"] else None,
            similar=about["similar"],
            popular=about["popular"],
            sources=("plex",),
        )
        return Answer(Outcome.MISSING) if found.is_empty() else Answer(Outcome.FOUND, found, confidence=score)


class PlexLyrics:
    """**A track's lyrics from the Plex library, behind LRCLIB's** (ADR-0184,
    fourth step; George, 2026-11-18). Asked only while a library is lent and
    *Information from Plex* is on; started once LRCLIB has answered, and only
    when that answer has no timed words (`behind`, `wanted`); and - the
    panel's route decides - only while lyrics are on screen. Found by its
    album as the covers are, then by title."""

    name = LYRICS_PROVIDER
    #: Asked after LRCLIB, and only with it (`EnrichmentService.for_track`).
    behind = "lrclib"

    def __init__(self, plex: PlexLibrary, allowed=lambda: True, identity=None) -> None:
        self._plex = plex
        self._allowed = allowed
        self._identity = identity

    def serves(self, renderer) -> bool:
        return renderer != "radio"

    def ready(self) -> bool:
        return self._plex.lent and bool(self._allowed())

    @staticmethod
    def wanted(before: Enrichment) -> bool:
        """Whether LRCLIB's answer leaves something to add: no timed words,
        and not "instrumental"."""
        return not (before.lyrics_synced or before.instrumental)

    async def fetch(self, key) -> Answer:
        if not (key.artist and key.album and key.title):
            return Answer(Outcome.MISSING)
        artist, album = key.raw_artist or key.artist, key.raw_album or key.album
        outcome, found = await self._plex.album_key(artist, album)
        score = 100
        if outcome is Outcome.MISSING:
            outcome, found, score = await _by_id(self._identity, key,
                                                 lambda mbid: self._plex.album_key(artist, album, mbid))
        if outcome is not Outcome.FOUND:
            return Answer(outcome)
        outcome, lyric = await self._plex.lyrics(found, key.title, key.duration)
        if outcome is not Outcome.FOUND:
            return Answer(outcome)
        words = lyric_enrichment(lyric)
        return Answer(Outcome.FOUND, words, confidence=score) if words else Answer(Outcome.MISSING)
