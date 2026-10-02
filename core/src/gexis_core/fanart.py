# SPDX-License-Identifier: GPL-3.0-or-later
"""**The artist's photos for the visualiser's fanart frame** (ADR-0112).

72 skins reserve a frame for a slideshow of the playing artist. This finds the
artist in LMS, asks the Music & Artist Information plugin for its photo list
(`artistphotos`: Discogs, Last.fm, the music folder - Finding 108), and keeps
up to `PER_ARTIST` of them on the device, so the visualiser draws from local
files and never goes to the network.

Who gets photos (George, 2026-10-02, *"B"*): LMS's own tracks by artist id;
any other source when its artist's name matches an LMS artist exactly,
letter case aside. A collaboration ("X feat. Y", "X & Y") that matches no
artist as a whole gets its first named artist's photos (*"Agree"*). Nothing
matched means no photos, and the frame keeps the skin's own background.
"""
from __future__ import annotations

import asyncio
import logging
import re
import shutil
from pathlib import Path
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

DEFAULT_DIR = Path("/var/cache/gexis-core/fanart")
#: At most this many photos per artist (ADR-0112: bounded).
PER_ARTIST = 10
#: The cache is trimmed, oldest artist first, above this many artists.
ARTISTS_KEPT = 60
#: Asked of LMS's image proxy: no frame in the packs is wider than 1920, and
#: the proxy only scales down - Discogs' are about 600 px anyway.
PROXY_SIZE = 1280
CALL_TIMEOUT_S = 20.0

#: "X feat. Y", "X ft. Y", "X featuring Y", "X & Y", "X, Y", "X / Y", "X; Y".
_JOINS = re.compile(r"\s+(?:feat\.?|ft\.?|featuring)\s+|\s*[&,/;]\s*", re.IGNORECASE)


def first_artist(name: str) -> str | None:
    """The first artist a collaboration credits, or None if it is one name."""
    parts = [p.strip() for p in _JOINS.split(name) if p and p.strip()]
    return parts[0] if len(parts) > 1 else None


def proxied(base: str, url: str, size: int = PROXY_SIZE) -> str:
    """A photo the plugin names, fetched through LMS's own image proxy - one
    host, scaled down by LMS - in the two shapes `LmsArtistInfo._url` knows."""
    url = url.strip()
    if url.startswith(("http://", "https://")):
        return f"{base}/imageproxy/{url}/image_{size}x{size}_o.jpg"
    path = url.strip("/")
    folder, _, _ = path.rpartition("/")
    return f"{base}/{folder}/image_{size}x{size}_o.jpg"


class Fanart:
    def __init__(
        self,
        rpc: Callable[..., Awaitable[dict]],
        download: Callable[[str], Awaitable[bytes | None]],
        base_url: str,
        directory: Path = DEFAULT_DIR,
    ) -> None:
        self._rpc = rpc
        self._download = download
        self._base = base_url.rstrip("/")
        self._dir = directory
        self._ids: dict[str, int | None] = {}
        self._busy: dict[int, asyncio.Task] = {}

    async def _ask(self, command: list) -> dict:
        try:
            return await self._rpc(command, timeout=CALL_TIMEOUT_S) or {}
        except Exception as exc:  # LMS away or the plugin absent: no photos, not a failure
            logger.info("fanart: %s did not answer (%r)", command[:2], exc)
            return {}

    async def artist_id(self, name: str | None) -> int | None:
        """LMS's id for an artist named exactly so, letter case aside; for a
        collaboration that is no artist of its own, its first artist's."""
        if not name:
            return None
        key = name.strip().lower()
        if key not in self._ids:
            found = await self._exact(name)
            if found is None and (first := first_artist(name)):
                found = await self._exact(first)
            self._ids[key] = found
        return self._ids[key]

    async def _exact(self, name: str) -> int | None:
        result = await self._ask(["artists", 0, 20, f"search:{name}"])
        for artist in result.get("artists_loop") or []:
            if str(artist.get("artist", "")).strip().lower() == name.strip().lower():
                try:
                    return int(artist["id"])
                except (KeyError, TypeError, ValueError):
                    return None
        return None

    async def for_artist(self, name: str | None, artist_id: int | None = None) -> list[Path]:
        """**The photos for a track's artist**: LMS's id when the track is
        LMS's own, else the exact name. LMS lists a collaboration as an
        artist of its own ("Snoop Dogg feat. Mystikal" is one on George's
        server), almost always without photos; then the first named
        artist's are used, as George chose."""
        if artist_id is None:
            artist_id = await self.artist_id(name)
        found = await self.photos(artist_id)
        if not found and name and (first := first_artist(name)):
            found = await self.photos(await self.artist_id(first))
        return found

    async def photos(self, artist_id: int | None) -> list[Path]:
        """The artist's photos on disk, fetching them the first time. One
        fetch per artist at a time: a prefetch and a track change share it."""
        if artist_id is None:
            return []
        folder = self._dir / str(artist_id)
        if (folder / ".done").exists():
            folder.touch()
            return sorted(p for p in folder.iterdir() if p.suffix == ".jpg")
        task = self._busy.get(artist_id)
        if task is None:
            task = asyncio.ensure_future(self._fetch(artist_id, folder))
            self._busy[artist_id] = task
            task.add_done_callback(lambda _t: self._busy.pop(artist_id, None))
        return await task

    async def _fetch(self, artist_id: int, folder: Path) -> list[Path]:
        result = await self._ask(["musicartistinfo", "artistphotos", f"artist_id:{artist_id}"])
        urls = [str(p["url"]) for p in (result.get("item_loop") or []) if p.get("url")][:PER_ARTIST]
        folder.mkdir(parents=True, exist_ok=True)
        kept = []
        for n, url in enumerate(urls):
            data = await self._download(proxied(self._base, url))
            if not data:
                continue
            path = folder / f"{n:02d}.jpg"
            path.write_bytes(data)
            kept.append(path)
        # Remembered even when empty: "asked, LMS has none" is an answer, and
        # asking again on every track of that artist costs 0.75 s each.
        (folder / ".done").touch()
        logger.info("fanart: %d photos for artist %d", len(kept), artist_id)
        self._trim()
        return kept

    def _trim(self) -> None:
        """Oldest artists out above `ARTISTS_KEPT` (a folder is touched each
        time it is used)."""
        try:
            folders = sorted((p for p in self._dir.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime)
        except OSError:
            return
        for old in folders[:-ARTISTS_KEPT] if len(folders) > ARTISTS_KEPT else []:
            shutil.rmtree(old, ignore_errors=True)
