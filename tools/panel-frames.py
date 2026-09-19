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
#: Not a frame anyone wanted: the compositor began one and found nothing to
#: draw. Counting these in the denominator flatters every result, so they
#: are excluded and reported separately.
NO_UPDATE = "STATE_NO_UPDATE_DESIRED"

#: A run with a handful of frames cannot carry a percentage: 1 dropped of 3
#: is "33 %" and means nothing. Runs below this are counted and reported,
#: never averaged in. A 420 ms gesture at 60 Hz should produce about 25
#: frames, and a trace window covering it about twice that.
MIN_FRAMES = 25


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
            frames.setdefault(key, (state, event.get("ts", 0) / 1e6))

        states: dict[str, int] = {}
        in_window = 0
        for state, ts in frames.values():
            states[state] = states.get(state, 0) + 1
            if state in PRESENTED and started <= ts <= ended:
                in_window += 1
        wanted = sum(v for k, v in states.items() if k != NO_UPDATE)
        total = sum(states.values())
        dropped = states.get(DROPPED, 0)
        partial = states.get("STATE_PRESENTED_PARTIAL", 0)
        return {
            "frames": total,
            "wanted": wanted,
            "presented": sum(states.get(s, 0) for s in PRESENTED),
            "partial": partial,
            "dropped": dropped,
            "dropped_pct": round(dropped / wanted * 100, 2) if wanted else None,
            "partial_pct": round(partial / wanted * 100, 2) if wanted else None,
            "states": states,
            # What the eye actually gets: frames put on the screen during
            # the gesture, per second of it. A percentage's denominator
            # moves with whatever else happens to be animating - now
            # playing's progress bar alone changes it - so the rate is the
            # honest number and 60 is the ceiling this panel can reach.
            "gesture_s": round(ended - started, 3),
            "presented_in_gesture": in_window,
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
#: Any sheet's dimming layer. Used to assert that nothing is covering the
#: panel before a measurement that assumes nothing is.
SCRIM = ".scrim, .sw-scrim"

RECT = """(() => {{ const e = document.querySelector({selector!r});
  if (!e) return null; const r = e.getBoundingClientRect();
  return [r.x, r.y, r.width, r.height]; }})()"""


class Screen:
    """Drives the panel by tapping what is on it, and checks it arrived."""

    def __init__(self, panel: "Panel", finger) -> None:
        self._panel, self._finger = panel, finger

    async def rect(self, selector: str):
        return await self._panel.evaluate(RECT.format(selector=selector))

    async def has(self, selector: str) -> bool:
        return bool(await self.rect(selector))

    async def tap(self, selector: str, settle: float = 1.4) -> None:
        box = await self.rect(selector)
        if box is None:
            raise RuntimeError(f"nothing to tap: {selector} is not on the panel")
        x, y, w, h = box
        self._finger.tap(round(x + w / 2), round(y + h / 2))
        await asyncio.sleep(settle)

    async def swipe(self, selector: str, axis: str = "y", fraction: float = 0.7,
                    ms: int = 420) -> None:
        """A swipe *inside* an element, so it scrolls that element and not
        whatever happens to be under a fixed coordinate."""
        box = await self.rect(selector)
        if box is None:
            raise RuntimeError(f"nothing to swipe: {selector} is not on the panel")
        x, y, w, h = box
        cx, cy = x + w / 2, y + h / 2
        if axis == "x":
            span = w * fraction / 2
            self._finger.swipe(round(cx + span), round(cy), round(cx - span), round(cy), ms=ms)
        else:
            span = h * fraction / 2
            self._finger.swipe(round(cx), round(cy + span), round(cx), round(cy - span), ms=ms)

    async def must_be(self, selector: str, where: str) -> None:
        if not await self.has(selector):
            raise RuntimeError(f"expected to be on {where} ({selector}), but it is not there")

    # --- places -------------------------------------------------------------

    async def go_now_playing(self) -> None:
        if await self.has(MINI_STRIP):
            await self.tap(MINI_STRIP)
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

    async def close_sheets(self) -> None:
        """Dismiss anything with a scrim.

        A sheet left open is measured by whatever runs next: Finding 034's
        idle control reported 71 % of frames dropped on an "untouched" panel
        because a previous run had left the queue rail open behind it, and
        its blurred scrim costs that much on its own (Finding 037). A sheet
        left open also swallows the next tap.
        """
        for _ in range(3):
            if not await self.has(SCRIM):
                return
            # The far left is scrim in every sheet this panel has.
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
    """`playing` or `paused`, so a measurement says which panel it measured."""
    now = await state(session)
    if now.get("transport") == want:
        return
    command = "play" if want == "playing" else "pause"
    async with session.post(f"http://127.0.0.1:8090/transport/{command}") as resp:
        await resp.read()
    await asyncio.sleep(2.0)


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
                if await screen.has(SCRIM):
                    raise RuntimeError("something is still covering the panel; "
                                       "an idle measurement would be of that")

            steps = {
                "idle-control": (arrive_idle, idle),
                "home-open": (lambda: screen.go_now_playing(),
                              lambda: screen.tap(HOME_BUTTON, settle=0.2)),
                "new-music-scroll": (lambda: screen.go_home(),
                                     lambda: screen.swipe(NEW_MUSIC, "x")),
                "artist-grid-open": (lambda: screen.go_home(),
                                     lambda: screen.tap(ARTISTS_CARD, settle=0.2)),
                "artist-grid-scroll": (lambda: screen.go_artist_grid(),
                                       lambda: screen.swipe(ARTIST_GRID, "y")),
                "queue-rail-open": (lambda: screen.go_now_playing(),
                                    lambda: screen.tap(QUEUE_BUTTON, settle=0.2)),
                "queue-rail-scroll": (lambda: screen.go_queue_rail(),
                                      lambda: screen.swipe(RAIL_LIST, "y")),
            }
            if only:
                steps = {k: v for k, v in steps.items() if k == only}

            for name, (arrive, interact) in steps.items():
                per_run = []
                for _ in range(runs):
                    if playback:
                        await set_playback(session, playback)
                    await arrive()
                    before = await state(session)
                    result = await panel.trace(interact)
                    after = await state(session)
                    # A gesture that changed the track changed the panel's
                    # work as well, so the run says so rather than being
                    # averaged in silently.
                    result["playback"] = before
                    result["disturbed"] = (
                        before.get("queue_index") != after.get("queue_index")
                        or before.get("transport") != after.get("transport")
                    )
                    per_run.append(result)
                    await asyncio.sleep(0.4)
                results[name] = per_run
                print(f"  {name}: done", file=sys.stderr)
        await panel.close()
    return results


def report(results: dict) -> None:
    print()
    for name, runs in results.items():
        usable = [r for r in runs if (r.get("wanted") or 0) >= MIN_FRAMES]
        thin = len(runs) - len(usable)
        pcts = [r["dropped_pct"] for r in usable if r["dropped_pct"] is not None]
        partials = [r["partial_pct"] for r in usable if r["partial_pct"] is not None]
        frames = [r["wanted"] for r in usable]
        disturbed = sum(1 for r in usable if r.get("disturbed"))
        if not pcts:
            print(f"{name:20} NO USABLE RUN - every run had under {MIN_FRAMES} frames. "
                  f"A broken measurement, not a smooth panel.")
            continue
        fps = [r["fps"] for r in usable if r.get("fps") is not None]
        fps_note = f"fps median {statistics.median(fps):4.1f}   " if fps else ""
        print(f"{name:20} {fps_note}dropped median {statistics.median(pcts):5.2f} %  "
              f"(min {min(pcts):5.2f} max {max(pcts):5.2f})   "
              f"partial median {statistics.median(partials):5.2f} %   "
              f"frames/run {statistics.median(frames):.0f}   n={len(pcts)}"
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
