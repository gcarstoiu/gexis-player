#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Measure what the panel actually presents, while a real finger drives it.

Phase 7a criteria 2 and 3. Three faults from
`docs/findings/032-panel-frame-times-during-a-scroll.md` this is built not to
repeat:

1. **`requestAnimationFrame` measures the main thread.** A scroll that runs
   off it reports a flat 16.8 ms while frames are being dropped elsewhere.
   So the numbers here come from the compositor's own `PipelineReporter`
   events, never from the page.
2. **The trace needs the `cc` category** or it contains no frame events at
   all, which reads exactly like "nothing was dropped". And a frame's fate
   is in `args.frame_reporter.state`, not `args.state`.
3. **Synthesised touches bypass the browser's gesture pipeline.** Input here
   comes from `panel-touch.py`, which writes to `/dev/uinput`, so it travels
   kernel -> libinput -> labwc -> Chromium like a finger.

And one discipline: **runs, not a run.** Findings 003/004 and 032's first
pass were both misled by single-run comparisons, so every interaction is
repeated and the result is a distribution.

Run **on the device, as root**, with the kiosk started on a debug port
(`GEXIS_KIOSK_DEBUG_PORT` in `/etc/gexis/kiosk.env`):

    sudo /opt/gexis-core/venv/bin/python panel-frames.py --runs 20

It prints one line per interaction and a JSON blob for the finding.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time

import aiohttp

sys.path.insert(0, "/tmp")
from panel_touch import Touchscreen  # noqa: E402  (deployed beside this file)

#: `cc` is the one that matters - without it the trace has no frames.
CATEGORIES = ",".join([
    "cc",
    "benchmark",
    "viz",
    "input",
    "latency",
    "disabled-by-default-devtools.timeline.frame",
])

#: How a frame ended, in `args.frame_reporter.state`. **`PRESENTED_PARTIAL`
#: reached the screen** - part of the update (typically the main thread's)
#: was not in it, but the frame was shown. Counting it as dropped is how the
#: first version of this tool reported 17.9 % on a panel nobody was
#: touching. Dropped means `STATE_DROPPED`: never presented at all.
PRESENTED = ("STATE_PRESENTED_ALL", "STATE_PRESENTED_PARTIAL")
DROPPED = "STATE_DROPPED"

#: **A dropped frame that nobody could see is not a dropped frame.** The
#: compositor marks each one `affects_smoothness`, and Chromium's own
#: "percent dropped frames" counts only those. Counting every
#: `STATE_DROPPED` nearly doubles the figure: measured on one artist-grid
#: scroll, **19 of 36 dropped frames affected smoothness and 17 did not**
#: (2026-09-24). The tenth instrument fault, and the one that moves every
#: number this tool has ever printed.
SMOOTHNESS = "affects_smoothness"
#: Not a frame anyone wanted: the compositor began one and found nothing to
#: draw. Counting these in the denominator flatters every result, so they
#: are excluded and reported separately.
NO_UPDATE = "STATE_NO_UPDATE_DESIRED"

#: A run with a handful of frames cannot carry a percentage: 1 dropped of 3
#: is "33 %" and means nothing. Runs below this are counted and reported,
#: never averaged in. A 420 ms gesture at 60 Hz should produce about 25
#: frames, and a trace window covering it about twice that.
MIN_FRAMES = 25


#: **The same gesture everywhere.** A swipe used to span 70 % of whatever
#: element it was in, so the artist grid (600 px tall) was dragged 420 px and
#: the browse screen's artist pane (250 px tall) only 175 - a different
#: *velocity*, which is a different amount of scrolling to draw per frame.
#: Finding 058 compared them anyway. Now every scroll is dragged the same
#: distance over the same time - about 400 px/s - clamped where an element is
#: too small to hold it, and each run reports how far it actually travelled.
SWIPE_PX = 170
SWIPE_MS = 420


class Panel:
    """One DevTools session against the kiosk's page.

    **One reader, always.** The protocol interleaves command replies with
    `Tracing.dataCollected` events on the same socket, and two coroutines
    reading it is an error, not a race you get away with
    (`RuntimeError: Concurrent call to receive()`). So a single task reads
    and dispatches: replies to the future that asked, trace events to a list.
    """

    def __init__(self, ws):
        self._ws = ws
        self._id = 0
        self._waiting: dict[int, asyncio.Future] = {}
        self._events: list[dict] = []
        self._complete = asyncio.Event()
        #: Called with every protocol event that is not trace data. A second
        #: opinion on the frame rate needs one: `PipelineReporter` is the
        #: compositor's own bookkeeping, and a scroll that moves *to* the
        #: compositor produces fewer of those reporters - so a flag that
        #: changes where the scroll runs cannot be judged by it alone
        #: (2026-09-24).
        self.on_event = None
        self._reader = asyncio.ensure_future(self._read())

    @classmethod
    async def connect(cls, session, port: int):
        async with session.get(f"http://127.0.0.1:{port}/json") as resp:
            targets = await resp.json()
        page = next(t for t in targets if t["type"] == "page")
        ws = await session.ws_connect(page["webSocketDebuggerUrl"], max_msg_size=0)
        return cls(ws)

    async def _read(self) -> None:
        async for message in self._ws:
            if message.type is not aiohttp.WSMsgType.TEXT:
                continue
            data = json.loads(message.data)
            if "id" in data:
                future = self._waiting.pop(data["id"], None)
                if future is not None and not future.done():
                    future.set_result(data.get("result", {}))
            elif data.get("method") == "Tracing.dataCollected":
                self._events.extend(data["params"]["value"])
            elif data.get("method") == "Tracing.tracingComplete":
                self._complete.set()
            elif self.on_event is not None:
                self.on_event(data.get("method"), data.get("params") or {})

    async def send(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        future = asyncio.get_running_loop().create_future()
        self._waiting[self._id] = future
        await self._ws.send_json({"id": self._id, "method": method, "params": params or {}})
        return await asyncio.wait_for(future, timeout=30)

    async def evaluate(self, expression: str):
        result = await self.send("Runtime.evaluate", {
            "expression": expression, "awaitPromise": True, "returnByValue": True})
        return result.get("result", {}).get("value")

    async def trace(self, run) -> dict:
        """Trace one interaction and count how its frames ended."""
        self._events.clear()
        self._complete.clear()
        await self.send("Tracing.start", {
            "categories": CATEGORIES,
            "transferMode": "ReportEvents",
            "options": "record-until-full",
        })
        await asyncio.sleep(0.3)
        # Chromium's trace timestamps are CLOCK_MONOTONIC microseconds on
        # Linux, the same clock as time.monotonic(), so the gesture's own
        # window can be cut out of the trace afterwards.
        started = time.monotonic()
        await run()
        ended = time.monotonic()
        await asyncio.sleep(0.6)
        await self.send("Tracing.end")
        try:
            await asyncio.wait_for(self._complete.wait(), timeout=30)
        except asyncio.TimeoutError:
            pass

        # **Each frame is two events**, `ph: "b"` and `ph: "e"` - an async
        # pair, not two frames. Counting both doubles everything, which is
        # how the first version of this metric reported 102 fps on a 60 Hz
        # panel. `frame_source` + `frame_sequence` is the frame's identity.
        frames: dict[tuple, tuple[str, float]] = {}
        for event in self._events:
            if event.get("name") != "PipelineReporter":
                continue
            reporter = (event.get("args") or {}).get("frame_reporter") or {}
            state = reporter.get("state")
            if not state:
                continue
            key = (reporter.get("frame_source"), reporter.get("frame_sequence"))
            frames.setdefault(key, (state, event.get("ts", 0) / 1e6,
                                    bool(reporter.get(SMOOTHNESS)),
                                    reporter.get("scroll_state")))

        # **A frame counter that is not the compositor's own bookkeeping.**
        # `PipelineReporter` under-counts a scroll the compositor drives: on
        # the artist grid with `--disable-lcd-text` it read 10.4 fps while
        # the display was drawing 58 frames a second. `DrawToScheduleOverlay`
        # is one per frame drawn, and with the flag off it agrees with
        # `PipelineReporter` to within a frame - 25.5 against 25.4 on the
        # grid, 39.1 against 37.2 on the rail - which is what makes it
        # trustworthy where the other is not (2026-09-24).
        drawn = sum(1 for e in self._events
                    if e.get("name") == "DrawToScheduleOverlay"
                    and e.get("ph") not in ("e", "E", "n")
                    and started <= e.get("ts", 0) / 1e6 <= ended)

        states: dict[str, int] = {}
        scrolls: dict[str, int] = {}
        in_window = 0
        invisible = 0
        for state, ts, smooth, scroll in frames.values():
            states[state] = states.get(state, 0) + 1
            if scroll:
                scrolls[scroll] = scrolls.get(scroll, 0) + 1
            if state == DROPPED and not smooth:
                invisible += 1
            if state in PRESENTED and started <= ts <= ended:
                in_window += 1
        wanted = sum(v for k, v in states.items() if k != NO_UPDATE)
        total = sum(states.values())
        # Only the ones a person could have seen (see SMOOTHNESS).
        dropped = states.get(DROPPED, 0) - invisible
        partial = states.get("STATE_PRESENTED_PARTIAL", 0)
        return {
            "frames": total,
            "wanted": wanted,
            "presented": sum(states.get(s, 0) for s in PRESENTED),
            "partial": partial,
            "dropped": dropped,
            "dropped_invisible": invisible,
            "scroll_states": scrolls,
            "dropped_pct": round(dropped / wanted * 100, 2) if wanted else None,
            "partial_pct": round(partial / wanted * 100, 2) if wanted else None,
            "states": states,
            # What the eye actually gets: frames put on the screen during
            # the gesture, per second of it. A percentage's denominator
            # moves with whatever else happens to be animating - now
            # playing's progress bar alone changes it - so the rate is the
            # honest number and 60 is the ceiling this panel can reach.
            # The trace covers roughly three times the gesture, so any
            # count taken over the whole trace is inflated by that much.
            # A second opinion has to use the same window this does.
            "window": (started, ended),
            "gesture_s": round(ended - started, 3),
            "presented_in_gesture": in_window,
            "drawn_fps": round(drawn / (ended - started), 1) if ended > started else None,
            "fps": round(in_window / (ended - started), 1) if ended > started else None,
        }

    async def close(self):
        self._reader.cancel()
        await self._ws.close()


#: The panel's own class names. Verified rather than assumed: the first
#: version of this tool swiped at coordinates where the New Music strip
#: lives *on Home*, while the panel was showing now playing - and reported a
#: confident 25-31 %. Every step below therefore says where it must be, and
#: fails loudly if it is somewhere else.
HOME_BUTTON = '.btn[aria-label="Home"]'
QUEUE_BUTTON = ".btn--queue"
MINI_STRIP = ".mini"
ARTISTS_CARD = ".card--artists"
NEW_MUSIC = ".new__scroll"
ARTIST_GRID = ".grid__scroll"
RAIL_LIST = ".rail__list"
RAIL_OPEN = ".rail.is-open"
#: **Everything on the panel, not only the three screens Finding 034
#: measured** - George's ruling when he approved criterion 0's plan
#: (2026-09-24). Settings, the library's other panes, the artist page and
#: the two sheets each get their own scene below.
BROWSE_CARD = ".card--browse"
PLAYLISTS_CARD = ".card--playlists"
RADIO_CARD = ".card--radio"
SETTINGS_CARD = ".card--settings"
SETTINGS_SCREEN = ".settings"
SETTINGS_RAIL = ".settings .rail"
SETTINGS_LIST = ".settings .list"
#: The Display section, which is the long one. Audio has five rows and
#: does not scroll at all - a swipe there produced 31 frames of
#: NO_UPDATE_DESIRED, which the harness correctly refused to report.
SETTINGS_DISPLAY = ".settings .cat"
PANE_LIST = ".pane__list"
#: The artist page's own scroller. `.tracks__list` is the *album*
#: page's; the artist page scrolls `.artistright`, and asking for the
#: wrong one lost a twenty-minute run on its last scene (2026-09-24).
TRACKS_LIST = ".tracks__list"
ARTIST_RIGHT = ".artistright"
ARTIST_FACE = ".grid__scroll .face, .grid__scroll .artist"
#: **The page's own disc, not a card's.** `.artist__disc` is the class on
#: every card in the grid too, so `has(ARTIST_PAGE)` was true while still
#: on the grid - `go_artist_page` then believed it had arrived and
#: measured the grid instead (2026-09-25).
ARTIST_PAGE = ".artist__disc--big"
VOLUME_TRIGGER = '.btn[aria-label="Volume"], .mini__volume'
VOLUME_DRAWER = ".drawer.is-open, .volume.is-open"
#: **Not `.btn`.** Settings' back is `<button class="back" aria-label="Back">`
#: and its picker's is `.back--small` labelled "Back to list"; a selector that
#: insisted on `.btn` matched neither, so a run that ended inside a settings
#: picker could not get out and every scene after it failed on the wrong
#: assertion (2026-09-24).
BACK_BUTTON = '[aria-label="Back to list"], [aria-label="Back"]'
LYRICS = ".lyrics__scroller"
#: Any sheet's dimming layer. Used to assert that nothing is covering the
#: panel before a measurement that assumes nothing is.
SCRIM = ".scrim, .sw-scrim"

RECT = """(() => {{ const e = document.querySelector({selector!r});
  if (!e) return null; const r = e.getBoundingClientRect();
  return [r.x, r.y, r.width, r.height]; }})()"""

#: Put a scroller back at the top. **The sixth instrument fault** (2026-09-24):
#: a scroll scene that arrives on a list already scrolled to its end measures
#: a gesture with nothing left to draw, and reports 31 frames of
#: `NO_UPDATE_DESIRED` - which reads as "smooth" to anything that does not
#: check. Settings' Display section runs out in one swipe; the artist grid
#: does not, which is why four rounds of scrutiny never met this.
#: **Is anything actually covering the panel?** A rect is not the test: this
#: UI keeps its scrims mounted at full size with `opacity: 0` between
#: transitions, so `querySelector('.scrim')` is truthy on a clear screen. The
#: seventh instrument fault, and the same shape as the first six - a selector
#: believed to mean what it appears to mean (2026-09-24).
COVERING = """(() => {{ return [...document.querySelectorAll({selector!r})].some(e => {{
    const s = getComputedStyle(e);
    if (s.display === 'none' || s.visibility === 'hidden') return false;
    if (parseFloat(s.opacity || '1') < 0.05) return false;
    const r = e.getBoundingClientRect();
    return r.width > 4 && r.height > 4;
  }}); }})()"""

TOP = """(() => {{ const e = document.querySelector({selector!r});
  if (!e) return false; e.scrollTop = 0; e.scrollLeft = 0; return true; }})()"""

#: The nth match rather than the first - a settings section is one of a list
#: of identical buttons, and only its position tells them apart.
RECT_NTH = """(() => {{ const e = document.querySelectorAll({selector!r})[{index}];
  if (!e) return null; const r = e.getBoundingClientRect();
  return [r.x, r.y, r.width, r.height]; }})()"""


class Screen:
    """Drives the panel by tapping what is on it, and checks it arrived."""

    def __init__(self, panel: "Panel", finger) -> None:
        self._panel, self._finger = panel, finger

    async def rect(self, selector: str):
        return await self._panel.evaluate(RECT.format(selector=selector))

    async def to_top(self, selector: str) -> None:
        """Put a scroller back where a run starts, so every run measures the
        same gesture. See `TOP`."""
        if not await self._panel.evaluate(TOP.format(selector=selector)):
            raise RuntimeError(f"cannot reset: {selector} is not on the panel")
        await asyncio.sleep(0.25)

    async def covering(self, selector: str = SCRIM) -> bool:
        """Whether anything matching `selector` is really on top. See
        `COVERING`."""
        return bool(await self._panel.evaluate(COVERING.format(selector=selector)))

    async def has(self, selector: str) -> bool:
        return bool(await self.rect(selector))

    async def tap(self, selector: str, settle: float = 1.4) -> None:
        box = await self.rect(selector)
        if box is None:
            raise RuntimeError(f"nothing to tap: {selector} is not on the panel")
        x, y, w, h = box
        self._finger.tap(round(x + w / 2), round(y + h / 2))
        await asyncio.sleep(settle)

    async def tap_nth(self, selector: str, index: int, settle: float = 1.4) -> None:
        box = await self._panel.evaluate(RECT_NTH.format(selector=selector, index=index))
        if box is None:
            raise RuntimeError(f"nothing to tap: {selector}[{index}] is not on the panel")
        x, y, w, h = box
        self._finger.tap(round(x + w / 2), round(y + h / 2))
        await asyncio.sleep(settle)

    async def swipe(self, selector: str, axis: str = "y",
                    span: int = SWIPE_PX, ms: int = SWIPE_MS) -> None:
        """A swipe *inside* an element, so it scrolls that element and not
        whatever happens to be under a fixed coordinate - and **the same
        gesture in every scene**. See `SWIPE_PX`."""
        box = await self.rect(selector)
        if box is None:
            raise RuntimeError(f"nothing to swipe: {selector} is not on the panel")
        x, y, w, h = box
        cx, cy = x + w / 2, y + h / 2
        extent = w if axis == "x" else h
        reach = min(span, round(extent * 0.8)) / 2
        if reach < 20:
            raise RuntimeError(f"{selector} is {extent} px across: too small to swipe")
        if axis == "x":
            self._finger.swipe(round(cx + reach), round(cy), round(cx - reach), round(cy), ms=ms)
        else:
            self._finger.swipe(round(cx), round(cy + reach), round(cx), round(cy - reach), ms=ms)

    async def must_be(self, selector: str, where: str) -> None:
        if not await self.has(selector):
            raise RuntimeError(f"expected to be on {where} ({selector}), but it is not there")

    # --- places -------------------------------------------------------------

    async def go_now_playing(self) -> None:
        """Back to now playing **from wherever the panel is**.

        Settings has no mini strip, only a Back button, so a scene that
        ended there used to strand every scene after it: the harness tapped
        nothing and then failed the assertion two levels down, reporting
        "not on now playing" rather than "still in Settings" (2026-09-24).
        """
        await self.close_sheets()
        for _ in range(3):
            if await self.has(QUEUE_BUTTON):
                return
            if await self.has(MINI_STRIP):
                await self.tap(MINI_STRIP)
            elif await self.has(BACK_BUTTON):
                await self.tap(BACK_BUTTON)
            else:
                break
        await self.must_be(QUEUE_BUTTON, "now playing")

    async def go_home(self) -> None:
        if not await self.has(NEW_MUSIC):
            await self.go_now_playing()
            await self.tap(HOME_BUTTON)
        await self.must_be(NEW_MUSIC, "home")

    async def go_artist_grid(self) -> None:
        if not await self.has(ARTIST_GRID):
            await self.go_home()
            await self.tap(ARTISTS_CARD, settle=2.5)
        await self.must_be(ARTIST_GRID, "the artist grid")

    async def go_queue_rail(self) -> None:
        await self.close_sheets()
        await self.go_now_playing()
        if not await self.has(RAIL_OPEN):
            await self.tap(QUEUE_BUTTON)
        await self.must_be(RAIL_OPEN, "the queue rail")

    async def arrive_scroll(self, arrive, selector: str) -> None:
        """Arrive, then put the list back at the top."""
        await arrive()
        await self.to_top(selector)

    async def scroll_top(self, selector: str):
        """Where a scroller is now, so a run can say whether it moved."""
        # One f-string, one set of escapes: the second half used to be a
        # plain literal whose `}}` stayed doubled, so every probe was a
        # syntax error answering `null`.
        return await self._panel.evaluate(
            f"(() => {{ const e = document.querySelector({selector!r});"
            f" return e ? e.scrollTop + e.scrollLeft : null; }})()"
        )

    async def go_settings(self) -> None:
        """Settings, which is reached from the library root's card and
        nowhere else on the panel (`design/screens.md`, Navigation)."""
        if not await self.has(SETTINGS_SCREEN):
            await self.go_home()
            await self.tap(SETTINGS_CARD, settle=1.2)
        await self.must_be(SETTINGS_SCREEN, "settings")

    async def go_settings_display(self) -> None:
        """Settings, on the section that actually has a list to scroll."""
        await self.go_settings()
        await self.tap_nth(SETTINGS_DISPLAY, 3, settle=0.6)   # Audio, Sources, Handoff, Display
        await self.must_be(SETTINGS_LIST, "the settings list")

    async def go_card(self, card: str, wait: str, where: str,
                      settle: float = 2.0) -> None:
        """One of the library root's cards, and the pane it opens."""
        if not await self.has(wait):
            await self.go_home()
            await self.tap(card, settle=settle)
        await self.must_be(wait, where)

    async def go_artist_page(self) -> None:
        """An artist's own page, opened from the grid."""
        if not await self.has(ARTIST_PAGE):
            await self.go_artist_grid()
            await self.tap(ARTIST_FACE, settle=2.0)
        await self.must_be(ARTIST_PAGE, "an artist page")

    async def close_sheets(self) -> None:
        """Dismiss anything with a scrim.

        A sheet left open is measured by whatever runs next: Finding 034's
        idle control reported 71 % of frames dropped on an "untouched" panel
        because a previous run had left the queue rail open behind it, and
        its blurred scrim costs that much on its own (Finding 037). A sheet
        left open also swallows the next tap.
        """
        for _ in range(4):
            if not await self.covering(SCRIM):
                return
            # A settings picker is a sheet with its own way out: its scrim is
            # not tappable in the same place, and it answers to Back.
            if await self.has(BACK_BUTTON):
                await self.tap(BACK_BUTTON, settle=0.7)
                continue
            # The far left is scrim in every other sheet this panel has.
            self._finger.tap(60, 400)
            await asyncio.sleep(0.9)


async def state(session) -> dict:
    """One frame of the daemon's published state. The panel is a different
    machine to measure depending on it: with music playing, now playing
    animates and the Peppy meter renders *behind* the kiosk, so a run that
    does not record the transport is not repeatable."""
    try:
        async with session.ws_connect("http://127.0.0.1:8090/state") as ws:
            payload = await asyncio.wait_for(ws.receive_json(), 5)
    except Exception as exc:  # the daemon is not this tool's subject
        return {"error": str(exc)}
    queue = payload.get("queue") or {}
    return {
        "transport": (payload.get("metadata") or {}).get("transport"),
        "queue_index": queue.get("index"),
        "queue_len": len(queue.get("items", [])),
    }


async def set_playback(session, want: str) -> None:
    """`playing` or `paused`, so a measurement says which panel it measured.

    **And it insists**, because asking is not getting: a queue that has run
    out answers `play` with nothing, the panel goes to the idle screen, and
    every run after that measures a screen nobody asked for. That happened
    on 2026-09-24 and read as "NO USABLE RUN" - a paused panel asks for
    almost no frames at all, which is true and was not the question.
    """
    for attempt in range(3):
        now = await state(session)
        if now.get("transport") == want:
            return
        command = "play" if want == "playing" else "pause"
        async with session.post(f"http://127.0.0.1:8090/transport/{command}") as resp:
            await resp.read()
        await asyncio.sleep(2.0 + attempt)
    now = await state(session)
    if now.get("transport") != want:
        raise RuntimeError(
            f"asked for {want} and the transport is {now.get('transport')!r}; "
            "a measurement now would be of a screen nobody chose"
        )


async def measure(port: int, runs: int, only: str | None, playback: str | None) -> dict:
    """Phase 7a's fixed interaction set, `runs` times each, plus an idle
    control so a reader can see what the panel costs when untouched."""
    results: dict[str, list[dict]] = {}
    async with aiohttp.ClientSession() as session:
        if playback:
            await set_playback(session, playback)
        panel = await Panel.connect(session, port)
        with Touchscreen() as finger:
            screen = Screen(panel, finger)

            async def idle():
                await asyncio.sleep(0.5)

            async def arrive_idle():
                """Nothing open, nothing covering the panel - the state this
                control believes it is measuring (Finding 037)."""
                await screen.close_sheets()
                await screen.go_now_playing()
                if await screen.covering(SCRIM):
                    raise RuntimeError("something is still covering the panel; "
                                       "an idle measurement would be of that")

            steps = {
                "idle-control": (arrive_idle, idle),
                # **A second control, on a screen with no playhead.** Now
                # playing redraws its progress bar twice a second while
                # music plays; the artist grid sitting still does not. If
                # the two differ, the "idle" panel is not idle - it is
                # drawing the playhead (2026-09-24).
                "grid-still": (lambda: screen.go_artist_grid(), idle),
                "home-open": (lambda: screen.go_now_playing(),
                              lambda: screen.tap(HOME_BUTTON, settle=0.2)),
                "new-music-scroll": (lambda: screen.arrive_scroll(screen.go_home, NEW_MUSIC),
                                     lambda: screen.swipe(NEW_MUSIC, "x")),
                "artist-grid-open": (lambda: screen.go_home(),
                                     lambda: screen.tap(ARTISTS_CARD, settle=0.2)),
                "artist-grid-scroll": (lambda: screen.arrive_scroll(screen.go_artist_grid, ARTIST_GRID),
                                       lambda: screen.swipe(ARTIST_GRID, "y")),
                "queue-rail-open": (lambda: screen.go_now_playing(),
                                    lambda: screen.tap(QUEUE_BUTTON, settle=0.2)),
                "queue-rail-scroll": (lambda: screen.arrive_scroll(screen.go_queue_rail, RAIL_LIST),
                                      lambda: screen.swipe(RAIL_LIST, "y")),
                # **The rest of the panel** (George, 2026-09-24: "everything
                # on the panel, not just the three screens"). Each arrives
                # through the same asserted route, so a scene that did not
                # get there fails loudly rather than measuring whatever was
                # already on screen - which is how the void idle control
                # happened.
                "settings-open": (lambda: screen.go_home(),
                                  lambda: screen.tap(SETTINGS_CARD, settle=0.2)),
                "settings-scroll": (lambda: screen.arrive_scroll(screen.go_settings_display, SETTINGS_LIST),
                                    lambda: screen.swipe(SETTINGS_LIST, "y")),
                "albums-open": (lambda: screen.go_home(),
                                lambda: screen.tap(BROWSE_CARD, settle=0.2)),
                # The browse screen's **artist** pane: three `.pane__list`
                # boxes are stacked there and this is the first, 917 rows in
                # a 250 px window. Named for the list, not the screen, since
                # "albums-scroll" was measuring this one (2026-09-24).
                "browse-artists-scroll": (lambda: screen.arrive_scroll(
                                     lambda: screen.go_card(BROWSE_CARD, PANE_LIST, "browse"), PANE_LIST),
                                  lambda: screen.swipe(PANE_LIST, "y")),
                "playlists-open": (lambda: screen.go_home(),
                                   lambda: screen.tap(PLAYLISTS_CARD, settle=0.2)),
                "radio-open": (lambda: screen.go_home(),
                               lambda: screen.tap(RADIO_CARD, settle=0.2)),
                "artist-page-open": (lambda: screen.go_artist_grid(),
                                     lambda: screen.tap(ARTIST_FACE, settle=0.2)),
                "artist-page-scroll": (lambda: screen.arrive_scroll(screen.go_artist_page, ARTIST_RIGHT),
                                       lambda: screen.swipe(ARTIST_RIGHT, "y")),
            }
            if only:
                steps = {k: v for k, v in steps.items() if k == only}

            #: Which element each scroll scene moves, so a run that produced
            #: no repaint can say whether it *scrolled*. Settings' list is
            #: text that is already rasterised: dragging it is a compositor
            #: transform with nothing to draw, which looked identical to a
            #: gesture that missed until this told them apart (2026-09-24).
            scrollers = {
                "new-music-scroll": NEW_MUSIC,
                "artist-grid-scroll": ARTIST_GRID,
                "queue-rail-scroll": RAIL_LIST,
                "settings-scroll": SETTINGS_LIST,
                "browse-artists-scroll": PANE_LIST,
                "artist-page-scroll": ARTIST_RIGHT,
            }

            for name, (arrive, interact) in steps.items():
                per_run = []
                # **A scene that cannot run loses itself, not the run.** The
                # first full pass died on its last scene - the wrong
                # selector for the artist page - and took twenty minutes of
                # everything else with it (2026-09-24).
                try:
                    await _scene(name, arrive, interact, runs, per_run,
                                 panel, screen, session, playback, scrollers)
                except Exception as exc:
                    results[name] = [{"error": f"{type(exc).__name__}: {exc}"}]
                    print(f"  {name}: FAILED - {exc}", file=sys.stderr)
                    continue
                results[name] = per_run
                print(f"  {name}: done", file=sys.stderr)
        await panel.close()
    return results


async def _scene(name, arrive, interact, runs, per_run,
                 panel, screen, session, playback, scrollers) -> None:
    """One scene, `runs` times."""
    for _ in range(runs):
        if playback:
            await set_playback(session, playback)
        await arrive()
        before = await state(session)
        scroller = scrollers.get(name)
        was = await screen.scroll_top(scroller) if scroller else None
        result = await panel.trace(interact)
        now = await screen.scroll_top(scroller) if scroller else None
        result["scrolled_px"] = (
            None if was is None or now is None else round(abs(now - was))
        )
        after = await state(session)
        # A gesture that changed the track changed the panel's work as well,
        # so the run says so rather than being averaged in silently.
        result["playback"] = before
        result["disturbed"] = (
            before.get("queue_index") != after.get("queue_index")
            or before.get("transport") != after.get("transport")
        )
        per_run.append(result)
        await asyncio.sleep(0.4)



#: Scenes with no gesture. For these, **few frames is the answer, not a
#: broken run**: a still screen that asks for almost nothing is a still
#: screen that costs almost nothing. Removing the badge pulse took now
#: playing from 86 frames a run to under 25, and the report called that a
#: failure (Finding 056, 2026-09-24).
STILL = ("idle-control", "grid-still")

#: **How far a scroll has to travel to be a scroll.** The queue rail was
#: reported at 50 fps and 11% dropped in Finding 055, and at 0.00% dropped
#: after the metric was corrected - on a queue of sixteen tracks that fits
#: the screen and **moved 0 px**. A gesture that moves nothing is not a
#: fast scroll (2026-09-24). With `SWIPE_PX` constant, a scroll with room to
#: move travels 170 px and some momentum beyond it; well under that means the
#: list ran out of room, not that the panel is fast.
SCROLLED_MIN_PX = 120


def report(results: dict) -> None:
    print()
    for name, runs in results.items():
        failed = [r for r in runs if r.get("error")]
        if failed:
            print(f"{name:20} FAILED - {failed[0]['error']}")
            continue
        usable = [r for r in runs if (r.get("wanted") or 0) >= MIN_FRAMES]
        if name in STILL and len(usable) < len(runs) / 2:
            asked = sorted(r.get("wanted") or 0 for r in runs)
            drops = sum(r.get("dropped") or 0 for r in runs)
            print(f"{name:20} asks for almost nothing - {asked[len(asked)//2]} frames a run "
                  f"(min {asked[0]} max {asked[-1]}), {drops} dropped in {len(runs)} runs")
            continue
        thin = len(runs) - len(usable)
        pcts = [r["dropped_pct"] for r in usable if r["dropped_pct"] is not None]
        partials = [r["partial_pct"] for r in usable if r["partial_pct"] is not None]
        frames = [r["wanted"] for r in usable]
        disturbed = sum(1 for r in usable if r.get("disturbed"))
        moved = [r.get("scrolled_px") for r in runs if r.get("scrolled_px") is not None]
        if moved and statistics.median(moved) < SCROLLED_MIN_PX and max(moved) > 0:
            print(f"{name:20} BARELY MOVED - {statistics.median(moved):.0f} px median "
                  f"(max {max(moved):.0f}). Nothing here is a scroll measurement.")
            continue
        if moved and max(moved) == 0:
            print(f"{name:20} DID NOT MOVE - there is nothing to scroll on this screen.")
            continue
        if not pcts and moved and min(moved) > 0:
            # **It scrolled and asked for nothing to be drawn.** A list of
            # already-rasterised text moves as a compositor transform; there
            # is no frame to drop because there is no frame to make. Not the
            # same as a gesture that missed, which moves nothing.
            print(f"{name:20} composited scroll - moved {min(moved)}-{max(moved)} px "
                  f"with no repaint asked for, over {len(runs)} runs")
            continue
        if not pcts:
            print(f"{name:20} NO USABLE RUN - every run had under {MIN_FRAMES} frames. "
                  f"A broken measurement, not a smooth panel.")
            continue
        fps = [r["fps"] for r in usable if r.get("fps") is not None]
        fps_note = f"fps median {statistics.median(fps):4.1f}   " if fps else ""
        drawn = [r["drawn_fps"] for r in runs if r.get("drawn_fps") is not None]
        if drawn:
            fps_note += f"drawn/s {statistics.median(drawn):4.1f}   "
        # **Where the scroll ran.** A scroll the compositor handles alone
        # survives a busy main thread; one on the main thread does not, and
        # that is the difference between the queue rail and the artist grid
        # (2026-09-24).
        main = sum(r.get("scroll_states", {}).get("SCROLL_MAIN_THREAD", 0) for r in usable)
        composited = sum(
            v for r in usable for k, v in r.get("scroll_states", {}).items()
            if k not in ("SCROLL_MAIN_THREAD", "SCROLL_NONE")
        )
        where = ""
        if main or composited:
            where = f"   scroll on the {'MAIN THREAD' if main > composited else 'compositor'}"
        invisible = sum(r.get("dropped_invisible", 0) for r in usable)
        # **How far it went, in the same line as what it cost.** Two scenes
        # are only comparable if the gesture moved them the same distance;
        # Finding 058 compared 574 px against 191 (2026-09-24).
        travel = f"   moved {statistics.median(moved):.0f} px" if moved else ""
        print(f"{name:20} {fps_note}dropped median {statistics.median(pcts):5.2f} %  "
              f"(min {min(pcts):5.2f} max {max(pcts):5.2f})   "
              f"partial median {statistics.median(partials):5.2f} %   "
              f"frames/run {statistics.median(frames):.0f}   n={len(pcts)}"
              + travel
              + where
              + (f"   invisible-drops {invisible}" if invisible else "")
              + (f"   thin {thin}" if thin else "")
              + (f"   DISTURBED {disturbed}" if disturbed else ""))
    print()
    print(json.dumps(results))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--only", default=None)
    parser.add_argument("--playback", choices=("playing", "paused"), default=None,
                        help="hold the player in this state for every run")
    args = parser.parse_args()
    report(asyncio.run(measure(args.port, args.runs, args.only, args.playback)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
