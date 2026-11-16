# SPDX-License-Identifier: GPL-3.0-or-later
"""**The Plex library the Plexamp plugin lends** ([ADR-0184](../../../docs/decisions/0184-plex-information-through-plexamps-claim.md)).

The plugin reads which server Plexamp plays from, that server's address on
this network and its token, and lends them through the contract's `library`
event. They are held here **in memory only**: never in `settings.db`, a
backup or a problem report, and gone when the plugin disconnects.

**What it answers, first: an album's cover** (Phase 32, acceptance 5). From
one index of the library's albums, fetched when first needed and again
every few hours, matched on the same reduced titles the cover providers
use. The cover itself is served by the core, `/plex/cover/<key>/<stamp>`:
a Plex picture's address needs the token, and the enrichment cache keeps
what it finds on disk and the state goes to every phone on the network.

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

#: A Plex album's picture: `/library/metadata/<ratingKey>/thumb/<stamp>`. Only
#: these are served through the core, never another of the server's paths.
_THUMB = re.compile(r"^/library/metadata/(\d+)/thumb/(\d+)$")
_DIGITS = re.compile(r"^\d{1,12}$")

#: The provider's name, in the enrichment cache and ADR-0040's list.
PROVIDER = "plex-release"
#: Where the server whose answers the cache holds is remembered.
NOTES = "plex"


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
    """The library's albums, by reduced title: `(artist, key, stamp)`."""

    lent: Lent
    made: float
    albums: dict[str, list[tuple[str, str, str]]]


class PlexLibrary:
    """What is lent, and what is asked of it."""

    def __init__(self, *, store=None, clock=time.monotonic, session_factory=None) -> None:
        #: The enrichment cache: which server its Plex answers came from.
        self._store = store
        self._clock = clock
        self._session_factory = session_factory
        self._session: aiohttp.ClientSession | None = None
        self._lent: Lent | None = None
        self._index: _Index | None = None
        self._indexing: asyncio.Lock | None = None

    # --- what is lent -------------------------------------------------------

    @property
    def lent(self) -> bool:
        return self._lent is not None

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
        """**Covers found on another server are not this one's**: its keys
        mean other albums. The cache's Plex answers go when the server
        changes - not when the same one is lent again after a restart."""
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
                self._store.forget_providers(PROVIDER)
                logger.info("plex: another server than before; its covers are forgotten")
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

    async def _albums(self) -> _Index | None:
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
            albums = await self._read_albums(lent)
            if albums is None:
                return None
            if self._lent != lent:
                return None  # lent again meanwhile: this one is not it
            self._index = _Index(lent, self._clock(), albums)
            logger.info("plex: %d album titles indexed in %.1f s",
                        len(albums), time.monotonic() - started)
            return self._index

    async def _read_albums(self, lent: Lent) -> dict | None:
        sections = await self._get(lent, "/library/sections", {}, total=INDEX_TIMEOUT_S)
        if sections is None:
            return None
        found: dict[str, list[tuple[str, str, str]]] = {}
        directories = (sections.get("MediaContainer") or {}).get("Directory") or []
        for section in directories:
            if not isinstance(section, dict) or section.get("type") != "artist":
                continue
            key = str(section.get("key") or "")
            if not _DIGITS.match(key):
                continue
            start = 0
            for _page in range(MAX_PAGES):
                page = await self._get(lent, f"/library/sections/{key}/all", {
                    "type": "9", "excludeFields": "summary",
                    "X-Plex-Container-Start": str(start), "X-Plex-Container-Size": str(PAGE),
                }, total=INDEX_TIMEOUT_S)
                if page is None:
                    return None
                container = page.get("MediaContainer") or {}
                items = container.get("Metadata") or []
                for album in items:
                    _add(found, album)
                start += len(items)
                total = container.get("totalSize")
                if not items or (isinstance(total, int) and start >= total) or len(items) < PAGE:
                    break
        return found

    async def album(self, artist: str, title: str) -> tuple[Outcome, tuple[str, str] | None]:
        """An album's cover, as `(key, stamp)`: FOUND, MISSING, or
        UNAVAILABLE when the server could not be asked."""
        index = await self._albums()
        if index is None:
            return Outcome.UNAVAILABLE, None
        wanted = {fold(artist), fold(lead_artist(artist))} - {""}
        for theirs, key, stamp in index.albums.get(match_title(title), ()):
            if theirs in wanted:
                return Outcome.FOUND, (key, stamp)
        return Outcome.MISSING, None

    async def cover(self, key: str, stamp: str, size: int = COVER_SIZE):
        """`(content_type, bytes)` of an album's cover at `size`, or None.
        Through Plex's own scaler, as Plex's apps ask for theirs; the picture
        as it is stored if the scaler will not."""
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
        rating_key, stamp = found
        return Answer(Outcome.FOUND, Enrichment(album_art=f"/plex/cover/{rating_key}/{stamp}",
                                                sources=("plex",)))
