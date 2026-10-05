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

#: **On a bar, wide pictures only** (George, 2026-10-04, "C": the bars'
#: wallpapers "do not come in the ratio of a bar which is making them look
#: strange"). Pixabay has no panorama filter but reports every picture's
#: size, so the page is filtered here: at least 2.4 to 1, the family boundary
#: (ADR-0109), which a 1280 x 400 bar crops by at most a quarter. The bar's
#: page asks for the most results Pixabay gives at once and a lower height,
#: since panoramas are a small share of any category. A bar whose categories
#: have none falls back to the usual pictures, which the idle screen crops.
WIDE_RATIO = 2.4
WIDE_PER_PAGE = 200
WIDE_MIN_HEIGHT = 400

#: How many downloaded pictures to keep. A wallpaper is ~200-400 KB, so this
#: is tens of megabytes on a card with room, and it means a device offline
#: in the morning still has something to show.
KEEP = 40

CREDIT_NOTE = "Photos from Pixabay"

#: **Pexels, beside Pixabay** (ADR-0120 §3). The owner's own key, sent as the
#: `Authorization` header; the chosen topic words are its search terms, since
#: it has no categories (George, 2026-10-05: "that is fine for pexels"). Its
#: terms want the credit on screen, drawn as Pixabay's is. **Written to its
#: published API and not yet tried against it**: Pexels issued no new keys
#: when this was built.
PEXELS_URL = "https://api.pexels.com/v1/search"
#: The most results Pexels gives at once.
PEXELS_PER_PAGE = 80
PEXELS_CREDIT = "Photos from Pexels"


def _ratio(hit: dict) -> float:
    try:
        return float(hit.get("imageWidth") or 0) / float(hit.get("imageHeight") or 1)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0

#: What "Wallpapers on device" reads. **How files get here is ADR-0047's
#: open question** and this does not answer it: today they arrive over SSH
#: or on a card, and whatever is decided - a USB import, a share, an action
#: row - writes into this directory rather than changing this code.
LOCAL_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp")


def local(directory: Path) -> list[str]:
    """Every picture under this directory, **folders and all**.

    A share invites folders - the first thing anyone copying from a
    computer does is drag one in - and the first version of this looked
    only at the top level, so a picture inside `Holidays/` was on the disk
    and invisible to the screen (George asked, 2026-09-21).

    Names come back relative to the directory and with forward slashes, so
    `Holidays/beach.png` is what the route is later asked for.

    **A symlink pointing out of the folder is skipped**, not followed: this
    directory is writable by anyone on the LAN (ADR-0049), and a link is
    the one thing in it that can name a file somewhere else. `rglob` does
    not descend through symlinked directories, and the check below catches
    a symlinked file.
    """
    root = Path(directory)
    try:
        resolved_root = root.resolve()
    except OSError:
        return []
    found = []
    try:
        for path in root.rglob("*"):
            if path.suffix.lower() not in LOCAL_SUFFIXES or not path.is_file():
                continue
            try:
                relative = path.resolve().relative_to(resolved_root)
            except (OSError, ValueError):
                continue
            found.append(relative.as_posix())
    except OSError:
        return []
    return sorted(found)


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
        self._pages: dict[tuple, tuple[float, list[dict]]] = {}
        #: Per source, how many of the pictures its pages held were wide
        #: enough for a bar, and how many there were: **the order a bar asks
        #: them in is measured as the player runs** (ADR-0120 §3).
        self._wide_seen: dict[str, list[int]] = {}
        self._lock = asyncio.Lock()

    # ── the page a category answers with ────────────────────────────────

    def wide_share(self, source: str) -> float | None:
        """The share of this source's pictures wide enough for a bar, as
        measured so far; None before any page has been read."""
        wide, total = self._wide_seen.get(source, (0, 0))
        return wide / total if total else None

    def _count(self, source: str, hits: list[dict], ratio) -> None:
        seen = self._wide_seen.setdefault(source, [0, 0])
        seen[0] += sum(1 for h in hits if ratio(h) >= WIDE_RATIO)
        seen[1] += len(hits)

    async def _page(self, key: str, category: str, wide: bool = False) -> list[dict]:
        """This category's pictures, from cache or from Pixabay.

        A failed request leaves whatever is cached in place, including a
        stale page: yesterday's pictures are a better idle screen than an
        empty one, and the terms cap how often we may ask, not how long we
        may look at the answer.
        """
        slot = (category, wide)
        cached = self._pages.get(slot)
        if cached is not None and time.monotonic() - cached[0] < PAGE_TTL_S:
            return cached[1]
        params = {
            "key": key,
            "category": category,
            "image_type": "photo",
            "orientation": "horizontal",
            "safesearch": "true",
            "min_width": MIN_WIDTH,
            "min_height": WIDE_MIN_HEIGHT if wide else MIN_HEIGHT,
            "order": "popular",
            "per_page": WIDE_PER_PAGE if wide else PER_PAGE,
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
        self._count("pixabay", hits, _ratio)
        if wide:
            hits = [h for h in hits if _ratio(h) >= WIDE_RATIO]
        hits = [{"id": str(h.get("id")), "url": h["largeImageURL"], "user": h.get("user") or "",
                 "page": h.get("pageURL") or "", "source": "pixabay"} for h in hits]
        self._pages[slot] = (time.monotonic(), hits)
        logger.info("wallpapers: %s has %d %spictures", category, len(hits), "wide " if wide else "")
        return hits

    # ── the picture on screen ───────────────────────────────────────────

    async def _pexels_page(self, key: str, topic: str, wide: bool = False) -> list[dict]:
        """This topic's pictures from Pexels, from cache or asked: the topic
        word as the search. Cached a day, as Pixabay's pages are - Pexels
        asks for no more, and its 200 requests an hour are never near."""
        slot = ("pexels", topic, wide)
        cached = self._pages.get(slot)
        if cached is not None and time.monotonic() - cached[0] < PAGE_TTL_S:
            return cached[1]
        params = {"query": topic, "orientation": "landscape", "per_page": PEXELS_PER_PAGE}
        try:
            async with self._session.get(
                PEXELS_URL, params=params, headers={"Authorization": key},
                timeout=aiohttp.ClientTimeout(total=TIMEOUT_S),
            ) as response:
                if response.status >= 400:
                    logger.info("wallpapers: Pexels %s answered HTTP %s", topic, response.status)
                    return cached[1] if cached else []
                body = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            logger.info("wallpapers: Pexels %s failed: %s", topic, exc)
            return cached[1] if cached else []

        def ratio(photo: dict) -> float:
            try:
                return float(photo.get("width") or 0) / float(photo.get("height") or 1)
            except (TypeError, ValueError, ZeroDivisionError):
                return 0.0

        photos = [p for p in (body.get("photos") or []) if (p.get("src") or {}).get("large2x")]
        self._count("pexels", photos, ratio)
        if wide:
            photos = [p for p in photos if ratio(p) >= WIDE_RATIO]
        hits = [{"id": f"pexels-{p.get('id')}", "url": p["src"]["large2x"],
                 "user": p.get("photographer") or "", "page": p.get("url") or "", "source": "pexels"}
                for p in photos]
        self._pages[slot] = (time.monotonic(), hits)
        logger.info("wallpapers: Pexels %s has %d %spictures", topic, len(hits), "wide " if wide else "")
        return hits

    def _order(self, sources: list[str], wide: bool) -> list[str]:
        """The sources in the order to ask them. On a bar, **the one measured
        wider first**; one not yet measured is tried as if it were the best,
        so it gets measured. Elsewhere, a fair shuffle."""
        if not wide:
            return random.sample(sources, len(sources))
        return sorted(sources, key=lambda s: -(self.wide_share(s) if self.wide_share(s) is not None else 1.0))

    async def next(self, key: str, topics: list[str], avoid: str | None = None, wide: bool = False,
                   pexels_key: str | None = None) -> dict:
        """One picture, ready to draw, or an `error` saying why not.

        `file` is a name inside the cache directory rather than a URL: what
        serves it is the daemon's business and this does not need to know
        the route. Pixabay with its key, Pexels with its own, both when both
        are typed (ADR-0120 §3).
        """
        chosen = [t.lower() for t in (topics or []) if t.lower() in CATEGORIES]
        sources = [s for s, k in (("pixabay", key), ("pexels", pexels_key)) if k]
        if not sources:
            return {"error": "No Pixabay or Pexels key yet."}
        if not chosen:
            return {"error": "No topics chosen."}
        async with self._lock:
            # Random across the selected categories, per refresh. Shuffled
            # rather than picked once, so a category that answers with
            # nothing falls through to another instead of blanking the
            # screen until the next change.
            # A bar asks for wide pictures first - from the source measured
            # wider first - then the usual ones.
            rounds = []
            for w in ((True, False) if wide else (False,)):
                for source in self._order(sources, w):
                    rounds += [(source, c, w) for c in random.sample(chosen, len(chosen))]
            for source, category, w in rounds:
                if source == "pexels":
                    hits = await self._pexels_page(pexels_key, category, w)
                else:
                    hits = await self._page(key, category, w)
                if not hits:
                    continue
                # Not the one already on screen, when there is another.
                choices = [h for h in hits if f"{h['id']}.jpg" != avoid] or hits
                hit = random.choice(choices)
                name = await self._download(hit)
                if name is None:
                    continue
                return {
                    "file": name,
                    "topic": category,
                    "by": hit["user"],
                    "page": hit["page"],
                    "credit": PEXELS_CREDIT if source == "pexels" else CREDIT_NOTE,
                    "source": source,
                    "error": None,
                }
        return {"error": "No pictures came back."}

    async def _download(self, hit: dict) -> str | None:
        """Fetch the picture to disk, and answer with the file's name.

        Named after Pixabay's own id, so the same picture twice is the same
        file once: the cache is a set, not a log.
        """
        name = f"{hit['id']}.jpg"
        path = self._dir / name
        if path.is_file() and path.stat().st_size > 0:
            path.touch()
            return name
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            async with self._session.get(
                hit["url"],
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
        """The file behind a name `local()` handed out, or None.

        **The name may now contain folders**, so "one path segment" is no
        longer the check. What replaces it is stronger: resolve the whole
        thing and require the result to still be inside the directory. That
        refuses `../../etc/shadow` and a symlink to it alike, which matters
        because this route is reachable from the LAN and the folder behind
        it is writable by anyone on it.
        """
        if Path(name).suffix.lower() not in LOCAL_SUFFIXES:
            return None
        try:
            root = self._local_dir.resolve()
            path = (self._local_dir / name).resolve()
        except OSError:
            return None
        if not path.is_relative_to(root) or not path.is_file():
            return None
        return path

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
