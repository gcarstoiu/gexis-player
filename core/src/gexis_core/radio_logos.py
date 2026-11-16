# SPDX-License-Identifier: GPL-3.0-or-later
"""**Station logos, through the player** (ADR-0180, George 2026-11-14).

The panel and the phone never fetch a logo from a station's site: the core
does, keeps it, and serves it at `/stations/logo/<key>`, so only the player's
address reaches the site - what the FAQ says leaves the player stays true.

- **Only an address the core handed out** is fetched: each logo the core
  puts in a station it gives a screen is remembered under its key (the first
  16 hexadecimal digits of the address's sha256). A key the core never gave
  is not a way to make the player fetch something.
- **Never the home network**: the directory is public and anyone may edit
  it, so a logo's address could name a device on the owner's network. A
  host that resolves to a private, loopback or link-local address is
  refused, and each redirect is checked the same way.
- **Pictures only**: PNG, JPEG, GIF or WebP, told by their first bytes, not
  by what the site says. SVG is refused (it can carry script and would be
  served from the player's own address), and `.ico` counts as none already
  (`radio_directory.logo_of`).
- **Kept on the device** for 30 days; a logo that could not be fetched is not
  asked for again for a day. At most `MOST_BYTES` each.
"""
from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import logging
import socket
import time
from collections import OrderedDict
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlsplit

import aiohttp

logger = logging.getLogger("gexis_core.radio_logos")

CACHE_DIR = Path("/var/cache/gexis-core/radio-logos")
PREFIX = "/stations/logo/"
FRESH_S = 30 * 24 * 3600
FAILED_S = 24 * 3600
TIMEOUT_S = 6.0
MOST_BYTES = 512 * 1024
#: Addresses remembered in memory, the oldest forgotten first.
REMEMBERED = 5000
#: Logos kept on the card.
KEEP = 600
REDIRECTS = 3

#: The first bytes of each picture taken, and the type it is served as.
MAGIC = ((b"\x89PNG\r\n\x1a\n", "image/png"), (b"\xff\xd8\xff", "image/jpeg"),
         (b"GIF87a", "image/gif"), (b"GIF89a", "image/gif"))


def sniff(data: bytes) -> str | None:
    for magic, kind in MAGIC:
        if data.startswith(magic):
            return kind
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def key_of(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


class Logos:
    def __init__(self, *, user_agent: str, cache_dir: Path = CACHE_DIR,
                 session_factory: Callable[[], aiohttp.ClientSession] | None = None,
                 clock: Callable[[], float] = time.time) -> None:
        self._user_agent = user_agent
        self._dir = cache_dir
        self._session_factory = session_factory
        self._session: aiohttp.ClientSession | None = None
        self._clock = clock
        self._urls: OrderedDict[str, str] = OrderedDict()
        #: One fetch per key at a time: a list of fifty rows asks at once.
        self._fetching: dict[str, asyncio.Future] = {}

    def path(self, url: str | None) -> str | None:
        """The player's address for a logo, remembering where it comes from;
        None for none."""
        if not url:
            return None
        key = key_of(url)
        self._urls[key] = url
        self._urls.move_to_end(key)
        while len(self._urls) > REMEMBERED:
            self._urls.popitem(last=False)
        return PREFIX + key

    def source(self, path: str | None) -> str | None:
        """The logo's own address for one of ours, or None. A logo given as a
        site's address is taken as it is."""
        if not isinstance(path, str):
            return None
        if path.startswith(PREFIX):
            return self._urls.get(path[len(PREFIX):])
        return path

    async def get(self, key: str) -> tuple[str, bytes] | None:
        """`(type, bytes)`, from the card or fetched; None when there is none
        or it cannot be had."""
        if len(key) != 16 or any(c not in "0123456789abcdef" for c in key):
            return None
        kept = self._read(key)
        if kept is not None:
            return kept if kept[0] else None
        url = self._urls.get(key)
        if url is None:
            return None
        if key in self._fetching:
            return await asyncio.shield(self._fetching[key])
        future = asyncio.get_running_loop().create_future()
        self._fetching[key] = future
        try:
            found = await self._fetch(url)
            self._write(key, url, found)
            future.set_result(found)
            return found
        except Exception as exc:  # noqa: BLE001 - a logo is never worth an error
            logger.info("radio logos: %s: %s", url, exc)
            future.set_result(None)
            return None
        finally:
            del self._fetching[key]

    async def _fetch(self, url: str) -> tuple[str, bytes] | None:
        session = self._ensure()
        data = bytearray()
        try:
            for _ in range(REDIRECTS + 1):
                if not await self._public(url):
                    logger.info("radio logos: %s is not on the internet, not fetched", url)
                    return None
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT_S),
                                       allow_redirects=False) as response:
                    if response.status in (301, 302, 303, 307, 308) and response.headers.get("Location"):
                        url = urljoin(url, response.headers["Location"])
                        continue
                    if response.status != 200:
                        return None
                    async for chunk in response.content.iter_chunked(1 << 14):
                        data += chunk
                        if len(data) > MOST_BYTES:
                            logger.info("radio logos: %s is over %d bytes", url, MOST_BYTES)
                            return None
                    break
            else:
                return None
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            logger.info("radio logos: %s did not answer (%s)", url, exc or type(exc).__name__)
            return None
        kind = sniff(bytes(data[:16]))
        if kind is None:
            logger.info("radio logos: %s is not a picture taken", url)
            return None
        return kind, bytes(data)

    @staticmethod
    async def _public(url: str) -> bool:
        """Whether every address the host resolves to is on the internet."""
        try:
            parts = urlsplit(url)
            if parts.scheme not in ("http", "https") or not parts.hostname:
                return False
            infos = await asyncio.get_running_loop().getaddrinfo(
                parts.hostname, parts.port or (443 if parts.scheme == "https" else 80),
                proto=socket.IPPROTO_TCP)
        except (OSError, ValueError):
            return False
        addresses = {info[4][0] for info in infos}
        return bool(addresses) and all(ipaddress.ip_address(a.split("%")[0]).is_global for a in addresses)

    def _ensure(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            if self._session_factory is not None:
                self._session = self._session_factory()
            else:
                self._session = aiohttp.ClientSession(headers={"User-Agent": self._user_agent})
        return self._session

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()

    def _read(self, key: str) -> tuple[str | None, bytes] | None:
        """`(type, bytes)` kept and fresh; `(None, b"")` for a failure still
        remembered; None when nothing is kept or it is old."""
        try:
            meta = json.loads((self._dir / f"{key}.json").read_text())
        except (OSError, ValueError):
            return None
        age = self._clock() - meta.get("at", 0)
        if meta.get("type") is None:
            return (None, b"") if 0 <= age < FAILED_S else None
        if not 0 <= age < FRESH_S:
            return None
        try:
            data = (self._dir / f"{key}.img").read_bytes()
        except OSError:
            return None
        return meta["type"], data

    def _write(self, key: str, url: str, found: tuple[str, bytes] | None) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            if found is not None:
                temporary = self._dir / f"{key}.img.tmp"
                temporary.write_bytes(found[1])
                temporary.replace(self._dir / f"{key}.img")
            (self._dir / f"{key}.json").write_text(json.dumps(
                {"at": self._clock(), "url": url, "type": found[0] if found else None}))
            self._trim()
        except OSError as exc:
            logger.warning("radio logos: cannot keep %s: %s", url, exc)

    def _trim(self) -> None:
        metas = list(self._dir.glob("*.json"))
        if len(metas) <= KEEP:
            return
        metas.sort(key=lambda p: p.stat().st_mtime)
        for meta in metas[:len(metas) - KEEP]:
            meta.unlink(missing_ok=True)
            meta.with_suffix(".img").unlink(missing_ok=True)
