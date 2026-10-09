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
import datetime
import json
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

#: **The most Pixabay gives at once, and a different page each day**, turning
#: through `PAGES` (ADR-0047 §2e, George, 2026-10-05). Fifty a page was the
#: top of the *popular* order every day - mostly the same fifty - and at a
#: change a minute every one came back within the hour. Still one request
#: per category per day.
PER_PAGE = 200
PAGES = 3

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
        #: **Kept on disk** (ADR-0047 §2e): each slot's page with when it was
        #: asked for, and which of its pictures have been shown - so a
        #: restart neither asks Pixabay again inside its day nor starts the
        #: pictures over. The page lived in memory until 2026-10-05 and was
        #: asked for again at every restart.
        self._state_path = self._dir / "state.json"
        self._state = self._load_state()
        self._pages: dict[tuple, tuple[float, list[dict]]] = {
            tuple(json.loads(k)): (v["at"], v["hits"]) for k, v in self._state["pages"].items()
        }
        #: Per source, how many of the pictures its pages held were wide
        #: enough for a bar, and how many there were: **the order a bar asks
        #: them in is measured as the player runs** (ADR-0120 §3).
        self._wide_seen: dict[str, list[int]] = {}
        self._lock = asyncio.Lock()

    # ── what is kept across restarts ─────────────────────────────────────

    def _load_state(self) -> dict:
        try:
            state = json.loads(self._state_path.read_text())
            if isinstance(state, dict):
                return {"pages": dict(state.get("pages") or {}), "shown": dict(state.get("shown") or {}),
                        "local_shown": list(state.get("local_shown") or [])}
        except (OSError, ValueError):
            pass
        return {"pages": {}, "shown": {}, "local_shown": []}

    def _save_state(self) -> None:
        self._state["pages"] = {json.dumps(list(k)): {"at": at, "hits": hits}
                                for k, (at, hits) in self._pages.items()}
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            scratch = self._state_path.with_suffix(".part")
            scratch.write_text(json.dumps(self._state))
            scratch.replace(self._state_path)
        except OSError as exc:
            logger.warning("wallpapers: could not keep what was shown: %s", exc)

    @staticmethod
    def _today_page() -> int:
        """Which page today is: 1, 2 or 3, turning with the date."""
        return 1 + datetime.date.today().toordinal() % PAGES

    def _fresh(self, slot: tuple) -> list[dict] | None:
        cached = self._pages.get(slot)
        if cached is not None and time.time() - cached[0] < PAGE_TTL_S:
            return cached[1]
        return None

    def _keep_page(self, slot: tuple, hits: list[dict]) -> None:
        """A new page for this slot: what had been shown and is still on it
        stays shown; the rest is forgotten."""
        self._pages[slot] = (time.time(), hits)
        key = json.dumps(list(slot))
        ids = {h["id"] for h in hits}
        self._state["shown"][key] = [i for i in self._state["shown"].get(key, []) if i in ids]
        self._save_state()

    def _unshown(self, slot: tuple, hits: list[dict], avoid: str | None) -> list[dict]:
        """**No picture twice until every one has been shown** (ADR-0047
        §2e); then the round starts again - never with the one on screen,
        when there is another."""
        shown = set(self._state["shown"].get(json.dumps(list(slot)), []))
        fresh = [h for h in hits if h["id"] not in shown and f"{h['id']}.jpg" != avoid]
        if fresh:
            return fresh
        self._state["shown"][json.dumps(list(slot))] = []
        return [h for h in hits if f"{h['id']}.jpg" != avoid] or hits

    def _shown(self, slot: tuple, hit: dict) -> None:
        key = json.dumps(list(slot))
        self._state["shown"].setdefault(key, []).append(hit["id"])
        self._save_state()

    def next_local(self, avoid: str | None = None) -> str | None:
        """The next of the device's own pictures, by the same rule: none
        twice until every one has been shown."""
        names = self.local_names()
        if not names:
            return None
        shown = set(self._state["local_shown"])
        fresh = [n for n in names if n not in shown and n != avoid]
        if not fresh:
            self._state["local_shown"] = []
            fresh = [n for n in names if n != avoid] or names
        name = random.choice(fresh)
        self._state["local_shown"].append(name)
        self._save_state()
        return name

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
        fresh = self._fresh(slot)
        if fresh is not None:
            return fresh
        cached = self._pages.get(slot)
        hits = await self._pixabay(key, category, wide, self._today_page())
        if hits is None:
            return cached[1] if cached else []
        if not hits and self._today_page() > 1:
            # A category with fewer than three pages: its first.
            hits = await self._pixabay(key, category, wide, 1)
            if hits is None:
                return cached[1] if cached else []
        self._keep_page(slot, hits)
        logger.info("wallpapers: %s has %d %spictures", category, len(hits), "wide " if wide else "")
        return hits

    async def _pixabay(self, key: str, category: str, wide: bool, page: int) -> list[dict] | None:
        """One page of a category, filtered as the screen needs; None when
        the request failed."""
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
            "page": page,
        }
        try:
            async with self._session.get(
                API_URL, params=params, timeout=aiohttp.ClientTimeout(total=TIMEOUT_S)
            ) as response:
                if response.status >= 400:
                    logger.info("wallpapers: %s page %d answered HTTP %s", category, page, response.status)
                    # Past the last page Pixabay answers 400: no pictures,
                    # not a failure.
                    return [] if response.status == 400 and page > 1 else None
                body = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            logger.info("wallpapers: %s failed: %s", category, exc)
            return None
        hits = [h for h in (body.get("hits") or []) if h.get("largeImageURL")]
        self._count("pixabay", hits, _ratio)
        if wide:
            hits = [h for h in hits if _ratio(h) >= WIDE_RATIO]
        return [{"id": str(h.get("id")), "url": h["largeImageURL"], "user": h.get("user") or "",
                 "page": h.get("pageURL") or "", "source": "pixabay"} for h in hits]

    # ── the picture on screen ───────────────────────────────────────────

    def _order(self, sources: list[str], wide: bool) -> list[str]:
        """The sources in the order to ask them. On a bar, **the one measured
        wider first**; one not yet measured is tried as if it were the best,
        so it gets measured. Elsewhere, a fair shuffle."""
        if not wide:
            return random.sample(sources, len(sources))
        return sorted(sources, key=lambda s: -(self.wide_share(s) if self.wide_share(s) is not None else 1.0))

    async def next(self, key: str, topics: list[str], avoid: str | None = None, wide: bool = False) -> dict:
        """One picture, ready to draw, or an `error` saying why not.

        `file` is a name inside the cache directory rather than a URL: what
        serves it is the daemon's business and this does not need to know
        the route. Pixabay with its key (ADR-0120 §3; Pexels removed 2026-10-07,
        George: "they are not providing API keys anymore").
        """
        chosen = [t.lower() for t in (topics or []) if t.lower() in CATEGORIES]
        sources = ["pixabay"] if key else []
        if not sources:
            return {"error": "No Pixabay key yet."}
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
                hits = await self._page(key, category, w)
                slot = (category, w)
                if not hits:
                    continue
                hit = random.choice(self._unshown(slot, hits, avoid))
                name = await self._download(hit)
                if name is None:
                    continue
                self._shown(slot, hit)
                return {
                    "file": name,
                    "topic": category,
                    "by": hit["user"],
                    "page": hit["page"],
                    "credit": CREDIT_NOTE,
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
