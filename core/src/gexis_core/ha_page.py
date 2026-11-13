# SPDX-License-Identifier: GPL-3.0-or-later
"""**ADR-0176: a page from Home Assistant on the screen, for a while.**

Home Assistant puts a page of its own over whatever the panel shows - live
cameras when the doorbell rings - and takes it down again; so do a touch,
any D-pad key, its time limit, the heat (P8) and the owner's switch. What
was there comes back: the panel's screens stay as they were under it, and
the visualiser and standby are put back as they were (P5, P6).

One page can be kept loaded and hidden (the amendment, K1-K8): Home
Assistant gives its address, the panel frames it hidden from the start, and
a show of that address only reveals it - a doorbell does not wait for Home
Assistant to load. Every close hides it again.

The side effects are the caller's - `prepare` before a page comes up over
nothing, `restore` as the last one goes, before the panel is told - so this
keeps only who is up, until when, and why the last one went.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Awaitable, Callable
from urllib.parse import urlsplit

logger = logging.getLogger("gexis_core.ha_page")

#: Why a page went: `closed.by` in `/state` (P2).
TOUCH = "touch"
KEY = "key"
LIMIT = "limit"
ASKED = "asked"
REPLACED = "replaced"
HEAT = "heat"
OFF = "off"

#: [H] 10 minutes when the call gives none (George, 2026-11-07).
DEFAULT_S = 600
MIN_S = 10
#: [H] the longest a call may ask (George, 2026-11-07, over none).
MAX_S = 3600
#: [H] where the Pi 4's firmware starts slowing the processor (P8).
HEAT_C = 80.0
#: `get_throttled`'s bits for now: the frequency capped, throttled, the soft
#: temperature limit. Under-voltage (bit 0) is not heat.
THROTTLED_NOW = 0x2 | 0x4 | 0x8
HEAT_EVERY_S = 5.0
ID_MAX = 64
#: K1: the page kept loaded, saved so a restart loads it again - not in the
#: settings, `/state` or a backup (P2: an address can carry a token). Root's
#: alone (the review of 1.16.1): written 0644, every plugin's user read it.
PRELOAD_PATH = Path("/var/lib/gexis-core/page-preload.json")


class Refused(Exception):
    """A show the player will not do, with the status and the sentence the
    caller gets (P1: the action fails in Home Assistant with a sentence)."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def parse(body) -> tuple[str, str, int]:
    """The show call: `{"url", "id"?, "seconds"?}` as `(url, id, seconds)`."""
    if not isinstance(body, dict):
        raise Refused(400, 'body must be {"url": "...", "id": "...", "seconds": N}')
    url = body.get("url")
    if not isinstance(url, str) or not url.strip():
        raise Refused(400, "url is required")
    url = _address(url)
    page_id = body.get("id", "page")
    if not isinstance(page_id, str) or not page_id.strip() or len(page_id.strip()) > ID_MAX:
        raise Refused(400, f"id must be text of 1 to {ID_MAX} characters")
    seconds = body.get("seconds", DEFAULT_S)
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not MIN_S <= seconds <= MAX_S:
        raise Refused(400, f"seconds must be from {MIN_S} to {MAX_S}")
    return url, page_id.strip(), int(seconds)


def _address(url: str) -> str:
    url = url.strip()
    try:
        parts = urlsplit(url)
    except ValueError:  # a bracketed host that does not parse (the review of 1.16.1)
        parts = None
    if parts is None or parts.scheme not in ("http", "https") or not parts.netloc:
        raise Refused(400, "url must be an http or https address")
    return url


def parse_preload(body) -> str | None:
    """K1: `{"url": "..."}` keeps that page loaded; `{"url": null}` or `""`
    clears it (None)."""
    if not isinstance(body, dict) or "url" not in body:
        raise Refused(400, 'body must be {"url": "..."}, or {"url": null} to clear it')
    url = body["url"]
    if url is None or (isinstance(url, str) and not url.strip()):
        return None
    if not isinstance(url, str):
        raise Refused(400, "url must be an http or https address")
    return _address(url)


def _read_preload(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        os.chmod(path, 0o600)  # one saved 0644 by 1.16.1
        url = json.loads(path.read_text()).get("url")
    except (OSError, ValueError, AttributeError):
        return None
    try:
        return _address(url) if isinstance(url, str) and url.strip() else None
    except Refused:
        return None


#: What the caller is told when the page cannot be framed (P1), as the
#: dashboard's panel says it (ADR-0156 decision 8: set in Home Assistant).
REASONS = {
    "unreachable": "The page's address does not answer. Check it, and that Home Assistant is running.",
    "refuses framing": "Home Assistant does not allow its pages to be shown inside another page. In Home Assistant, turn off Send X-Frame-Options (Settings → System → Network → HTTP server → More options).",
}


def explain(reason: str | None) -> str:
    if reason and reason.startswith("http "):
        return f"The page's address answers with an error ({reason[5:]})."
    return REASONS.get(reason or "", "The page cannot be shown on this player.")


def too_hot(temp_c: float | None, throttled: int | None) -> bool:
    """P8: at 80 °C, or the firmware throttling now."""
    return (temp_c is not None and temp_c >= HEAT_C) or bool((throttled or 0) & THROTTLED_NOW)


def read_heat() -> tuple[float | None, int | None]:
    """The processor's temperature and the firmware's throttling bits, each
    None when it cannot be read (off a Pi). Blocks: run it in a thread."""
    temp = None
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            temp = int(f.read().strip()) / 1000
    except (OSError, ValueError):
        pass
    bits = None
    try:
        out = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=3).stdout
        bits = int(out.strip().split("=")[-1], 16)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return temp, bits


async def _nothing() -> dict:
    return {}


async def _nothing_back(token: dict, back: bool) -> None:
    return None


class Page:
    """Up or not, which, until when, and why the last one went; and the page
    kept loaded, if any. `publish(state)` tells the panel (`panel.page`);
    `available()` is the owner's switch on a player with a screen."""

    def __init__(self, publish: Callable[[dict], None], *,
                 prepare: Callable[[], Awaitable[dict]] = _nothing,
                 restore: Callable[[dict, bool], Awaitable[None]] = _nothing_back,
                 heat: Callable[[], tuple[float | None, int | None]] | None = None,
                 clock: Callable[[], float] = time.time,
                 heat_every: float = HEAT_EVERY_S,
                 available: Callable[[], bool] = lambda: True,
                 preload_path: Path | None = None) -> None:
        self._publish = publish
        self._prepare = prepare
        self._restore = restore
        self._heat = heat
        self._clock = clock
        self._heat_every = heat_every
        self._available = available
        self._preload_path = preload_path
        #: K1: the address kept loaded, and one more each time it is given
        #: (the same address again loads it afresh).
        self.preload: str | None = _read_preload(preload_path)
        self.preload_n = 0
        self.shown = False
        self.id: str | None = None
        self.url: str | None = None
        self.until: float | None = None
        self.closed: dict | None = None
        #: One more each time the panel has a page to load: a new one, or the
        #: same id at a new address. The address itself stays off `/state`.
        self.seq = 0
        self._token: dict | None = None
        self._limit_task: asyncio.Task | None = None
        self._heat_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    @property
    def preloaded(self) -> bool:
        """K2: a page to keep loaded, and the switch on with a screen (K5)."""
        return self.preload is not None and self._available()

    def state(self) -> dict:
        return {"shown": self.shown, "id": self.id, "until": self.until,
                "seq": self.seq, "closed": self.closed, "preloaded": self.preloaded}

    def refresh(self) -> None:
        """The switch or the screen changed: `preloaded` with it (K5)."""
        self._publish(self.state())

    def set_preload(self, url: str | None) -> None:
        """K1: keep this page loaded, or none; saved for the next start. The
        panel loads it afresh even at the same address."""
        self.preload = url
        self.preload_n += 1
        self.seq += 1
        if self._preload_path is not None:
            try:
                tmp = self._preload_path.with_suffix(".tmp")
                fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "w") as out:
                    os.fchmod(out.fileno(), 0o600)
                    out.write(json.dumps({"url": url}))
                os.replace(tmp, self._preload_path)
            except OSError:
                logger.exception("page: the page kept loaded could not be saved")
        self._publish(self.state())
        logger.info("page: %s", "a page kept loaded" if url else "no page kept loaded")

    async def show(self, url: str, page_id: str, seconds: int) -> None:
        """Up, or the one up replaced; the same id again restarts its limit
        (a second ring) and reloads only for a new address."""
        async with self._lock:
            if not self.shown:
                self._token = await self._prepare()
            elif page_id != self.id:
                self.closed = {"id": self.id, "by": REPLACED, "at": round(self._clock(), 1)}
                logger.info("page: %s replaced by %s", self.id, page_id)
            if not (self.shown and page_id == self.id and url == self.url):
                self.seq += 1
            self.shown, self.id, self.url = True, page_id, url
            self.until = round(self._clock() + seconds, 1)
            self._start_timers(seconds)
            self._publish(self.state())
            logger.info("page: %s up for %d s", page_id, seconds)

    async def hide(self, by: str, *, page_id: str | None = None, back: bool = True,
                   then: Callable[[], Awaitable[None]] | None = None) -> bool:
        """Down, and what was there put back - unless `back` is False: a
        person who asked the panel for something else (P5) wants that, not
        the visualiser or standby from before; `then` does it, in the page's
        place as a put-back would be. With `page_id`, only that page: an
        automation never closes another's."""
        async with self._lock:
            if not self.shown or (page_id is not None and page_id != self.id):
                return False
            self._stop_timers()
            self.closed = {"id": self.id, "by": by, "at": round(self._clock(), 1)}
            self.shown, self.id, self.url, self.until = False, None, None, None
            token, self._token = self._token or {}, None
            # What was there goes back before the panel is told: the
            # visualiser is a window over the panel's, so raised first it
            # covers the page as it goes, where the panel otherwise showed
            # now playing for the raise (sofapi, 2026-11-08). Standby alike.
            try:
                await self._restore(token, back)
                if then is not None:
                    await then()
            finally:
                self._publish(self.state())
            logger.info("page: down (%s)", by)
        return True

    def _start_timers(self, seconds: int) -> None:
        self._stop_timers()
        self._limit_task = asyncio.ensure_future(self._limit(seconds))
        if self._heat is not None:
            self._heat_task = asyncio.ensure_future(self._watch_heat())

    def _stop_timers(self) -> None:
        me = asyncio.current_task()
        for task in (self._limit_task, self._heat_task):
            if task is not None and task is not me:
                task.cancel()
        self._limit_task = self._heat_task = None

    async def _limit(self, seconds: int) -> None:
        await asyncio.sleep(seconds)
        await self.hide(LIMIT)

    async def _watch_heat(self) -> None:
        while True:
            await asyncio.sleep(self._heat_every)
            try:
                temp, bits = await asyncio.to_thread(self._heat)
            except Exception:  # noqa: BLE001 - a reading is no reason to stop watching
                logger.exception("page: the heat could not be read")
                continue
            if too_hot(temp, bits):
                logger.warning("page: taken down for the heat (%s °C, throttled %s)",
                               temp, hex(bits) if bits is not None else None)
                await self.hide(HEAT)
                return
