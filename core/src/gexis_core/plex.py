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
the same reduced titles and folded names the other providers use. Pictures
are served by the core, `/plex/cover/<key>/<stamp>`: a Plex picture's
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

#: The providers' names, in the enrichment cache and ADR-0040's list.
PROVIDER = "plex-release"
ARTIST_PROVIDER = "plex-artist"
#: Where the server whose answers the cache holds is remembered.
NOTES = "plex"
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
    its artists, by folded name: `(key, stamp or None, section)`."""

    lent: Lent
    made: float
    albums: dict[str, list[tuple[str, str, str]]]
    artists: dict[str, list[tuple[str, str | None, str]]] = field(default_factory=dict)


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

    async def _get(self, lent: Lent, path: str, params: dict, *, total: float, raw: bool = False):
        """One request to the lent server. `None` when it could not be asked
        or did not answer as it should: the caller's UNAVAILABLE."""
        session = await self._ensure()
        timeout = aiohttp.ClientTimeout(total=total, sock_connect=CONNECT_S)
        try:
            headers = {"X-Plex-Token": lent.token}
            if raw:
                headers["Accept"] = "image/*"
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
            albums, artists = read
            self._index = _Index(lent, self._clock(), albums, artists)
            logger.info("plex: %d album titles and %d artist names indexed in %.1f s",
                        len(albums), len(artists), time.monotonic() - started)
            return self._index

    async def _read_library(self, lent: Lent) -> tuple[dict, dict] | None:
        sections = await self._get(lent, "/library/sections", {}, total=INDEX_TIMEOUT_S)
        if sections is None:
            return None
        albums: dict[str, list[tuple[str, str, str]]] = {}
        artists: dict[str, list[tuple[str, str | None, str]]] = {}
        directories = (sections.get("MediaContainer") or {}).get("Directory") or []
        for section in directories:
            if not isinstance(section, dict) or section.get("type") != "artist":
                continue
            key = str(section.get("key") or "")
            if not _DIGITS.match(key):
                continue
            # Albums (type 9), then artists (type 8): a page of 500 at a
            # time, summaries left out - a biography is asked when wanted.
            for kind, add in (("9", lambda item: _add(albums, item)),
                              ("8", lambda item, key=key: _add_artist(artists, item, key))):
                if not await self._pages(lent, key, kind, add):
                    return None
        return albums, artists

    async def _pages(self, lent: Lent, section: str, kind: str, add) -> bool:
        start = 0
        for _page in range(MAX_PAGES):
            page = await self._get(lent, f"/library/sections/{section}/all", {
                "type": kind, "excludeFields": "summary",
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

    async def album(self, artist: str, title: str) -> tuple[Outcome, tuple[str, str] | None]:
        """An album's cover, as `(key, stamp)`: FOUND, MISSING, or
        UNAVAILABLE when the server could not be asked."""
        index = await self._library()
        if index is None:
            return Outcome.UNAVAILABLE, None
        wanted = {fold(artist), fold(lead_artist(artist))} - {""}
        for theirs, key, stamp in index.albums.get(match_title(title), ()):
            if theirs in wanted:
                return Outcome.FOUND, (key, stamp)
        return Outcome.MISSING, None

    async def artist(self, name: str) -> tuple[Outcome, tuple[str, str | None, str] | None]:
        """An artist in the library, as `(key, picture stamp or None,
        section)`: by the folded name, else by the lead artist's - *A feat.
        B* is A's. FOUND, MISSING, or UNAVAILABLE."""
        index = await self._library()
        if index is None:
            return Outcome.UNAVAILABLE, None
        for wanted in (fold(name), fold(lead_artist(name))):
            found = index.artists.get(wanted) if wanted else None
            if found:
                return Outcome.FOUND, found[0]
        return Outcome.MISSING, None

    async def about(self, name: str) -> tuple[Outcome, dict | None]:
        """**What the library knows of an artist**: `biography`, `picture`
        (`(key, stamp)` or None), `similar` and `popular` - the artist's
        tracks in the library the wider world plays most, as Plexamp's own
        DJ asks for them (`sort=ratingCount:desc`, one per recording)."""
        outcome, found = await self.artist(name)
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


def _add(found: dict, album) -> None:
    if not isinstance(album, dict):
        return
    match = _THUMB.match(str(album.get("thumb") or ""))
    title = match_title(str(album.get("title") or ""))
    artist = str(album.get("parentTitle") or "")
    if not (match and title and artist):
        return
    key, stamp = match.groups()
    for name in {fold(artist), fold(lead_artist(artist))} - {""}:
        found.setdefault(title, []).append((name, key, stamp))


def _add_artist(found: dict, artist, section: str) -> None:
    if not isinstance(artist, dict):
        return
    key = str(artist.get("ratingKey") or "")
    name = fold(str(artist.get("title") or ""))
    if not (_DIGITS.match(key) and name):
        return
    match = _THUMB.match(str(artist.get("thumb") or ""))
    stamp = match.group(2) if match and match.group(1) == key else None
    found.setdefault(name, []).append((key, stamp, section))


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

    def __init__(self, plex: PlexLibrary, allowed=lambda: True) -> None:
        self._plex = plex
        self._allowed = allowed

    def serves(self, renderer) -> bool:
        # The internet radio's album line is the station's name (ADR-0180).
        return renderer != "radio"

    def ready(self) -> bool:
        return self._plex.lent and bool(self._allowed())

    async def fetch(self, key) -> Answer:
        if not (key.artist and key.album):
            return Answer(Outcome.MISSING)
        outcome, found = await self._plex.album(key.raw_artist or key.artist,
                                                key.raw_album or key.album)
        if outcome is not Outcome.FOUND:
            return Answer(outcome)
        return Answer(Outcome.FOUND, Enrichment(album_art=picture_path(*found),
                                                sources=("plex",)))


class PlexArtist:
    """**An artist from the Plex library, ahead of everyone else's** (ADR-0184,
    second step, 1): the biography, the picture, similar artists and popular
    tracks. Asked as `PlexRelease` is."""

    name = ARTIST_PROVIDER

    def __init__(self, plex: PlexLibrary, allowed=lambda: True) -> None:
        self._plex = plex
        self._allowed = allowed

    def serves(self, renderer) -> bool:
        return True

    def ready(self) -> bool:
        return self._plex.lent and bool(self._allowed())

    async def fetch(self, key) -> Answer:
        if not key.artist:
            return Answer(Outcome.MISSING)
        outcome, about = await self._plex.about(key.raw_artist or key.artist)
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
        return Answer(Outcome.MISSING) if found.is_empty() else Answer(Outcome.FOUND, found)
