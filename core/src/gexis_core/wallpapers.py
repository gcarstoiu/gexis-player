# SPDX-License-Identifier: GPL-3.0-or-later
"""The idle screen's online wallpapers, from Pixabay (ADR-0047 §2a).

**Chosen on the pictures** (George, 2026-09-21), from the three stock
services whose terms permit a background feature inside a product that
stands up without it. What its terms impose is most of this file:

- **The device is the cache.** *"Permanent hotlinking of images (using
  Pixabay URLs in your app) is not allowed. If you intend to use the images,
  please download them to your server first."* Its URLs expire after 24
  hours anyway, and its terms require responses to be cached for 24 hours -
  so a category is asked about once a day and the pictures live on disk.
- **A key per owner.** Pixabay allows this use; it does not allow a
  credential shipped inside a public repository, so `wallpaper_key` is a row
  the owner fills in.
- **One category per request**, which is why the rotation below is ours.

**Random per refresh, across every chosen category** (George: *"the photos
should come randomly from all the categories, not be stuck in only one of
the many"*). Each change picks a category at random from those selected and
then a picture at random from that category's cached page. Round-robin was
the alternative and is worse on a screen watched for hours: it is
predictable, and with one category chosen the two are the same thing anyway.

**Attribution is Pixabay's condition too** - *"Show your users where the
images and videos are from"* - so every picture carries its photographer and
its page, and the panel draws them.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)

API_URL = "https://pixabay.com/api/"
TIMEOUT_S = 10.0
DOWNLOAD_TIMEOUT_S = 30.0

#: Pixabay's own categories, lowercase on the wire. The settings row offers
#: them capitalised and nothing of ours: George, on whether to invent topic
#: words that map to searches - *"We start with categories and see later if
#: we need to add queries too. I think not though as it should be enough."*
CATEGORIES = (
    "backgrounds", "fashion", "nature", "science", "education", "feelings",
    "health", "people", "religion", "places", "animals", "industry",
    "computer", "food", "sports", "transportation", "travel", "buildings",
    "business", "music",
)

#: Their own rule, not a number we chose: *"Requests must be cached for 24
#: hours."* One page per category per day, and every picture until the next
#: one comes from it.
PAGE_TTL_S = 24 * 60 * 60

#: Enough to choose from without asking for a hundred results nobody sees.
PER_PAGE = 50

#: What the panel is: a 1280x800 screen. Asking Pixabay to filter means the
#: rejects never travel, and `largeImageURL` is the biggest size a per-owner
#: key is served - `fullHDURL` and `imageURL` need approved full API access.
MIN_WIDTH = 1280
MIN_HEIGHT = 800

#: How many downloaded pictures to keep. A wallpaper is ~200-400 KB, so this
#: is tens of megabytes on a card with room, and it means a device offline
#: in the morning still has something to show.
KEEP = 40

CREDIT_NOTE = "Photos from Pixabay"

#: What "Wallpapers on device" reads. **How files get here is ADR-0047's
#: open question** and this does not answer it: today they arrive over SSH
#: or on a card, and whatever is decided - a USB import, a share, an action
#: row - writes into this directory rather than changing this code.
LOCAL_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp")


def local(directory: Path) -> list[str]:
    """The pictures somebody put on this device, newest first."""
    try:
        return sorted(
            (p.name for p in Path(directory).iterdir()
             if p.is_file() and p.suffix.lower() in LOCAL_SUFFIXES),
        )
    except OSError:
        return []


class Wallpapers:
    """One device's wallpaper source: a cached page per category, a
    directory of downloaded pictures, and a random pick across both."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        cache_dir: Path,
        *,
        local_dir: Path | None = None,
        keep: int = KEEP,
    ) -> None:
        self._session = session
        self._dir = Path(cache_dir)
        #: Kept apart from the downloaded cache on purpose: this one is
        #: somebody's own pictures and **nothing here ever deletes from
        #: it**, where the cache above evicts as it fills.
        self._local_dir = Path(local_dir) if local_dir else Path(cache_dir).parent / "pictures"
        self._keep = keep
        self._pages: dict[str, tuple[float, list[dict]]] = {}
        self._lock = asyncio.Lock()

    # ── the page a category answers with ────────────────────────────────

    async def _page(self, key: str, category: str) -> list[dict]:
        """This category's pictures, from cache or from Pixabay.

        A failed request leaves whatever is cached in place, including a
        stale page: yesterday's pictures are a better idle screen than an
        empty one, and the terms cap how often we may ask, not how long we
        may look at the answer.
        """
        cached = self._pages.get(category)
        if cached is not None and time.monotonic() - cached[0] < PAGE_TTL_S:
            return cached[1]
        params = {
            "key": key,
            "category": category,
            "image_type": "photo",
            "orientation": "horizontal",
            "safesearch": "true",
            "min_width": MIN_WIDTH,
            "min_height": MIN_HEIGHT,
            "order": "popular",
            "per_page": PER_PAGE,
        }
        try:
            async with self._session.get(
                API_URL, params=params, timeout=aiohttp.ClientTimeout(total=TIMEOUT_S)
            ) as response:
                if response.status >= 400:
                    logger.info(
                        "wallpapers: %s answered HTTP %s", category, response.status
                    )
                    return cached[1] if cached else []
                body = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            logger.info("wallpapers: %s failed: %s", category, exc)
            return cached[1] if cached else []
        hits = [h for h in (body.get("hits") or []) if h.get("largeImageURL")]
        self._pages[category] = (time.monotonic(), hits)
        logger.info("wallpapers: %s has %d pictures", category, len(hits))
        return hits

    # ── the picture on screen ───────────────────────────────────────────

    async def next(self, key: str, topics: list[str]) -> dict:
        """One picture, ready to draw, or an `error` saying why not.

        `file` is a name inside the cache directory rather than a URL: what
        serves it is the daemon's business and this does not need to know
        the route.
        """
        chosen = [t.lower() for t in (topics or []) if t.lower() in CATEGORIES]
        if not key:
            return {"error": "No Pixabay key yet."}
        if not chosen:
            return {"error": "No topics chosen."}
        async with self._lock:
            # Random across the selected categories, per refresh. Shuffled
            # rather than picked once, so a category that answers with
            # nothing falls through to another instead of blanking the
            # screen until the next change.
            for category in random.sample(chosen, len(chosen)):
                hits = await self._page(key, category)
                if not hits:
                    continue
                hit = random.choice(hits)
                name = await self._download(hit)
                if name is None:
                    continue
                return {
                    "file": name,
                    "topic": category,
                    "by": hit.get("user") or "",
                    "page": hit.get("pageURL") or "",
                    "credit": CREDIT_NOTE,
                    "error": None,
                }
        return {"error": "No pictures came back."}

    async def _download(self, hit: dict) -> str | None:
        """Fetch the picture to disk, and answer with the file's name.

        Named after Pixabay's own id, so the same picture twice is the same
        file once: the cache is a set, not a log.
        """
        name = f"{hit.get('id')}.jpg"
        path = self._dir / name
        if path.is_file() and path.stat().st_size > 0:
            path.touch()
            return name
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            async with self._session.get(
                hit["largeImageURL"],
                timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT_S),
            ) as response:
                if response.status >= 400:
                    logger.info("wallpapers: image HTTP %s", response.status)
                    return None
                body = await response.read()
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
            logger.info("wallpapers: could not fetch a picture: %s", exc)
            return None
        try:
            # Written beside and moved into place: a half-written file that
            # the panel picks up is a broken picture on screen, and the
            # screen reads this directory without asking anyone.
            scratch = path.with_suffix(".part")
            scratch.write_bytes(body)
            scratch.replace(path)
        except OSError as exc:
            logger.warning("wallpapers: could not store a picture: %s", exc)
            return None
        self._evict()
        return name

    def local_names(self) -> list[str]:
        """The pictures on this device, for "Wallpapers on device"."""
        return local(self._local_dir)

    def local_path(self, name: str) -> Path | None:
        if name != Path(name).name or Path(name).suffix.lower() not in LOCAL_SUFFIXES:
            return None
        path = self._local_dir / name
        return path if path.is_file() else None

    def path_of(self, name: str) -> Path | None:
        """The file behind a name this class handed out, or None.

        The name is checked against the directory rather than trusted:
        whatever asks for it reached the daemon over the LAN.
        """
        if name != Path(name).name:
            return None
        path = self._dir / name
        return path if path.is_file() else None

    def _evict(self) -> None:
        """Keep the newest `keep` pictures and drop the rest."""
        try:
            files = sorted(
                (p for p in self._dir.glob("*.jpg") if p.is_file()),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except OSError:
            return
        for old in files[self._keep:]:
            try:
                old.unlink()
            except OSError:
                pass
