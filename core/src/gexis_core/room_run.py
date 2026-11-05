# SPDX-License-Identifier: GPL-3.0-or-later
"""**A measurement of the room, from start to *Keep it*** (ADR-0175 items
4-7; the flow George settled on 2026-11-04 and 2026-11-05).

It runs on the player, so a phone page closed and opened again shows where
it is (the design's R18), and the panel shows that it is running. The steps:

1. *place* - the device taken (what plays stops, nothing else can start),
   waiting for *Start*;
2. *level* - soft noise, louder in steps until the seat hears about 75 dB,
   never above the output's maximum level;
3. *measure* - each speaker alone, two sweeps that agree, at position 1;
   then *move* (waiting for *Measure here*), a 3-second *countdown*, and
   *measure* again, to position 5;
4. *correction* (or *nothing* to cut) - waiting for *Check it*;
5. the check: *move*, *countdown* and *checking* at each position with the
   correction on - *Skip* on every one;
6. *result* - measured, or expected when skipped - waiting for *Keep it*.

*Cancel* ends it at any step; a step waiting for a tap for 10 minutes is
cancelled (George, 2026-11-05). It never moves to a new position without
the tap.

What it plays and hears goes through `audio` (`room_mic.Audio` on the
player, a made-up room in the tests); what it changes on the player goes
through `host`. Nothing is stored until *Keep it*.
"""
from __future__ import annotations

import asyncio
import datetime
import logging
from dataclasses import dataclass, replace
from typing import Awaitable, Callable

from gexis_core import room_correction as rc

logger = logging.getLogger("gexis_core.room_run")

#: Decision, 2026-11-04: a tap, then a countdown.
COUNTDOWN_S = 3
#: George, 2026-11-05: a run waiting for a tap is cancelled after this.
TIMEOUT_S = 600
#: Item 4: the level aimed for at the seat, and how close is close enough.
AIM_SPL = 75.0
AIM_WITHIN = 1.5
#: The level step: from this, in these steps, never above the cap - the
#: signal's part; the volume is at the output's maximum (`host.loud`).
LEVEL_START_DBFS = -54.0
LEVEL_STEP_DB = 3.0
LEVEL_CAP_DBFS = -12.0
LEVEL_BURST_S = 1.0
#: The noise is raised only while the microphone follows it: steps that
#: move the reading by less than this did not reach it. The first steps may
#: be under the room's own noise, so it takes this many in a row (24 dB)
#: to stop.
LEVEL_HEARD_DB = 1.5
LEVEL_UNHEARD_STEPS = 8
#: Item 4: sweeps per speaker at a position, and how many tries before the
#: two that agree best are taken.
SWEEPS = 2
MAX_SWEEPS = 6


class Cancelled(Exception):
    pass


class _Skipped(Exception):
    """*Skip* pressed while the check sweeps."""


@dataclass(frozen=True)
class RunState:
    """What every screen shows of a run (the design's *State*)."""
    step: str                       # place level measure move countdown correction nothing checking result
    position: int = 1               # 1-5
    speaker: str | None = None      # "L" / "R" while one plays
    sweep: int = 0                  # 1-2 while one plays
    noise: bool = False             # the last sweep was spoiled and is repeated
    level_db: float | None = None   # at the seat, in the level step and after
    count: int = 0                  # the countdown's number
    checking: bool = False          # the check's positions, not the run's
    progress: float = 0.0           # 0-1, as the design's §3
    done: tuple[int, ...] = ()      # the positions measured (or checked) so far
    expected: bool = False          # the result is expected, the check skipped
    too_quiet: bool = False         # the level step could not reach the aim
    resumed_from: str | None = None

    def as_dict(self) -> dict:
        return {"step": self.step, "position": self.position, "speaker": self.speaker, "sweep": self.sweep,
                "noise": self.noise, "level_db": None if self.level_db is None else round(self.level_db),
                "count": self.count, "checking": self.checking, "progress": round(self.progress, 3),
                "done": list(self.done), "expected": self.expected, "too_quiet": self.too_quiet}


def _progress(step: str, position: int = 1, speaker: str | None = None, sweep: int = 0,
              checking: bool = False) -> float:
    """The design's §3: the level 5 %; positions 8 to 78 % (each a half per
    speaker, a quarter per sweep); checking 80 to 100 %."""
    right = 0.5 if speaker == "R" else 0.0
    if checking:
        return 0.8 + 0.2 * (position - 1 + (right if step == "checking" else 0)) / rc.POSITIONS
    if step == "level":
        return 0.05
    if step == "place":
        return 0.0
    base = 0.08 + 0.7 * (position - 1) / rc.POSITIONS
    if step == "measure":
        base += 0.7 / rc.POSITIONS * (right + 0.25 * max(0, min(sweep, SWEEPS) - 1))
    return base


@dataclass
class Host:
    """What a run changes on the player, each an async callable."""
    #: The device taken for the run: what plays stopped politely, nothing
    #: else let in.
    take: Callable[[], Awaitable[None]]
    #: The stage for measuring: the equaliser flat, and room correction's
    #: cuts (None: none, the room as it is; else the cuts being checked).
    stage: Callable[[object], Awaitable[None]]
    #: The output at its maximum level for the run.
    loud: Callable[[], Awaitable[None]]
    #: The run over: the measurement kept (or None), then the level, the
    #: stage and the device as they were.
    finish: Callable[[rc.Measurement | None], Awaitable[None]]
    #: Every change of the run's state, for the screens.
    publish: Callable[[RunState | None, dict | None], None] = lambda state, ended: None


class Run:
    """One run, for one output. `start()` begins it; `tap(what)` is the
    phone's buttons; `cancel()` ends it. `state` is what the screens show,
    `pending` the measurement made, before *Keep it*."""

    def __init__(self, card: str, audio, calibration: rc.Calibration, host: Host, *,
                 sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
                 timeout_s: float = TIMEOUT_S, today: Callable[[], str] | None = None,
                 dsp=None, sweep_s: float | None = None):
        from gexis_core import room_dsp
        self.card = card
        self._audio = audio
        self._cal = calibration
        self._host = host
        self._sleep = sleep
        self._timeout = timeout_s
        self._today = today or (lambda: datetime.date.today().isoformat())
        self._dsp = dsp or room_dsp
        self._sweep_s = sweep_s or self._dsp.SWEEP_S
        self._taps: asyncio.Queue = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self.state = RunState("place")
        self.pending: rc.Measurement | None = None
        self.ended: dict | None = None        # {"how": cancelled|kept|discarded|done|failed, ...}
        self._level_dbfs = LEVEL_START_DBFS
        self._positions: dict[str, list] = {c: [] for c in rc.CHANNELS}
        self._checked: dict[str, list] = {c: [] for c in rc.CHANNELS}
        self._designs: dict = {}
        self._waiting = False

    # -- what the control calls ----------------------------------------------------

    async def start(self) -> None:
        try:
            await self._host.take()
            await self._host.stage(None)
            await self._host.loud()
        except Exception:
            await self._end("failed")
            raise
        self._set(RunState("place"))
        self._task = asyncio.create_task(self._running())

    def tap(self, what: str) -> None:
        """`start`, `next` (*Measure here*), `check` (*Check it*), `skip`,
        `keep`, `discard`, `again` (*Try again*), `done`."""
        self._taps.put_nowait(what)

    async def cancel(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def waiting(self) -> bool:
        """Waiting on the phone (a tap), not sweeping."""
        return self._waiting

    # -- the run ---------------------------------------------------------------------

    def _set(self, state: RunState) -> None:
        self.state = state
        self._host.publish(state, None)

    async def _wait(self, *accepted: str) -> str:
        """The phone's next tap among `accepted`; *cancel* never comes here
        (it cancels the task). After `TIMEOUT_S` the run is cancelled."""
        self._waiting = True
        try:
            while True:
                try:
                    what = await asyncio.wait_for(self._taps.get(), self._timeout)
                except asyncio.TimeoutError:
                    logger.info("room: nobody tapped for %d s, the run is cancelled", self._timeout)
                    raise Cancelled("timeout")
                if what in accepted:
                    return what
                logger.debug("room: %s ignored while waiting for %s", what, "/".join(accepted))
        finally:
            self._waiting = False

    async def _running(self) -> None:
        how, why = "failed", None
        try:
            how = await self._steps()
        except Cancelled as exc:
            how, why = "cancelled", str(exc)
        except asyncio.CancelledError:
            await self._end("cancelled", "cancel")
            raise
        except Exception:  # noqa: BLE001 - whatever broke, the device is given back
            logger.exception("room: the run failed")
            how = "failed"
        await self._end(how, why)

    async def _steps(self) -> str:
        """The run's steps; how it ended: done, discarded or kept."""
        await self._wait("start")
        while not await self._level():
            self._set(replace(self.state, step="level", too_quiet=True))
            await self._wait("again")
        for n in range(1, rc.POSITIONS + 1):
            if n > 1:
                await self._move(n, checking=False)
            await self._measure(n, checking=False)
        self._design()
        all_done = tuple(range(1, rc.POSITIONS + 1))
        if self.pending.nothing_to_cut:
            self._set(RunState("nothing", position=rc.POSITIONS, progress=0.8, done=all_done,
                               level_db=self.state.level_db))
            await self._wait("done", "discard")
            return "done"
        self._set(RunState("correction", position=rc.POSITIONS, progress=0.8, done=all_done,
                           level_db=self.state.level_db))
        if await self._wait("check", "discard") == "discard":
            return "discarded"
        await self._host.stage(self._cuts())
        skipped = False
        try:
            for n in range(1, rc.POSITIONS + 1):
                if await self._move(n, checking=True) == "skip":
                    skipped = True
                    break
                await self._measure(n, checking=True)
        except _Skipped:
            skipped = True
        self._result(skipped)
        self._set(RunState("result", position=rc.POSITIONS, progress=1.0, expected=skipped, done=all_done,
                           level_db=self.state.level_db))
        return "kept" if await self._wait("keep", "discard") == "keep" else "discarded"

    async def _end(self, how: str, why: str | None = None) -> None:
        if self.ended is not None:
            return
        self.ended = {"how": how, "why": why}
        try:
            await self._host.finish(self.pending if how == "kept" else None)
        except Exception:  # noqa: BLE001
            logger.exception("room: could not put the player back")
        logger.info("room: the run ended (%s%s)", how, f", {why}" if why else "")
        self._host.publish(None, dict(self.ended))

    async def _move(self, n: int, checking: bool) -> str:
        done = tuple(range(1, n))
        self._set(RunState("move", position=n, checking=checking, done=done, level_db=self.state.level_db,
                           progress=_progress("move", n, checking=checking)))
        what = await self._wait("next", "skip") if checking else await self._wait("next")
        if what == "skip":
            return what
        for count in range(COUNTDOWN_S, 0, -1):
            self._set(replace(self.state, step="countdown", count=count))
            await self._sleep(1)
        return what

    # -- the level ---------------------------------------------------------------------

    def _spl(self, recording) -> float:
        return self._dsp.band_level_db(recording) + self._audio.spl_offset(self._cal)

    async def _level(self) -> bool:
        """**The level step** (item 4): pink noise from `LEVEL_START_DBFS`,
        3 dB a step, until the seat hears about 75 dB; never above the cap,
        and only while the microphone follows. False when it cannot get
        there (*Too quiet*)."""
        self._set(RunState("level", progress=0.05))
        dsp = self._dsp
        noise = dsp.pink_noise(LEVEL_BURST_S)
        level = LEVEL_START_DBFS
        last = None
        unheard = 0
        while True:
            recording = await self._audio.play(noise * 10 ** (level / 20), channel=None)
            spl = self._spl(recording[int(0.2 * dsp.FS):])
            self._set(replace(self.state, level_db=spl))
            if abs(spl - AIM_SPL) <= AIM_WITHIN:
                break
            if spl > AIM_SPL:
                level -= max(1.0, spl - AIM_SPL)
                if level < LEVEL_START_DBFS - 30:
                    break
                continue
            if last is not None and spl - last < LEVEL_HEARD_DB:
                unheard += 1
            else:
                unheard = 0
            last = spl
            step = min(LEVEL_STEP_DB, max(1.0, AIM_SPL - spl))
            if level + step > LEVEL_CAP_DBFS or unheard >= LEVEL_UNHEARD_STEPS:
                logger.info("room: %.0f dB at the seat at %.0f dBFS: too quiet", spl, level)
                return False
            level += step
        self._level_dbfs = level
        logger.info("room: %.0f dB at the seat at %.0f dBFS", self.state.level_db, level)
        return True

    # -- the sweeps ------------------------------------------------------------------

    async def _curve(self, channel: str) -> object:
        dsp = self._dsp
        sweep = dsp.log_sweep(seconds=self._sweep_s)
        # The sweep's level in the band, matched to the noise's.
        scale = 10 ** (self._level_dbfs / 20) / 10 ** (dsp.band_level_db(sweep) / 20)
        played = sweep * scale
        recording = await self._audio.play(played, channel=rc.CHANNELS.index(channel))
        curve = dsp.response_db(dsp.transfer(recording, played))
        return curve - self._calibration_curve()

    def _calibration_curve(self):
        if not hasattr(self, "_cal_curve"):
            import numpy as np
            self._cal_curve = np.array([self._cal.db_at(float(f)) for f in self._dsp.GRID])
        return self._cal_curve

    async def _measure(self, n: int, checking: bool) -> None:
        """Each speaker alone at position `n` (item 4): sweeps until two
        agree, up to `MAX_SWEEPS`, then the two closest."""
        dsp = self._dsp
        step = "checking" if checking else "measure"
        done = tuple(range(1, n))
        for channel in rc.CHANNELS:
            curves = []
            noise = False
            while True:
                k = len(curves) + 1
                self._set(RunState(step, position=n, speaker=channel, sweep=min(k, SWEEPS), noise=noise,
                                   checking=checking, done=done, level_db=self.state.level_db,
                                   progress=_progress(step, n, channel, min(k, SWEEPS), checking)))
                curves.append(await self._curve(channel))
                if checking and self._skip_sent():
                    raise _Skipped()
                if len(curves) < SWEEPS:
                    continue
                pair = self._closest(curves)
                if dsp.agree_db(*pair) <= dsp.AGREE_DB or len(curves) >= MAX_SWEEPS:
                    break
                noise = True
                logger.info("room: position %d, %s: two sweeps disagree by %.1f dB, again",
                            n, channel, dsp.agree_db(curves[-2], curves[-1]))
            (self._checked if checking else self._positions)[channel].append(dsp.power_average(list(pair)))

    def _skip_sent(self) -> bool:
        """Whether *Skip* came while the check swept (the design: Skip on
        every check screen); any other tap then is dropped, as it would be
        ignored."""
        found = False
        while not self._taps.empty():
            found = self._taps.get_nowait() == "skip" or found
        return found

    def _closest(self, curves):
        best = None
        for i in range(len(curves)):
            for j in range(i + 1, len(curves)):
                d = self._dsp.agree_db(curves[i], curves[j])
                if best is None or d < best[0]:
                    best = (d, curves[i], curves[j])
        return best[1], best[2]

    # -- the correction ---------------------------------------------------------------

    def _design(self) -> None:
        speakers = {}
        for channel in rc.CHANNELS:
            d = self._dsp.design(self._positions[channel])
            self._designs[channel] = d
            speakers[channel] = rc.Speaker(cuts=tuple((c.freq, c.gain, c.q) for c in d.cuts),
                                           before=tuple(d.before), target=tuple(d.target),
                                           after=tuple(d.after), positions=tuple(tuple(p) for p in d.positions))
        self.pending = rc.Measurement(self._today(), False, speakers)

    def _cuts(self):
        return self.pending.cuts("L"), self.pending.cuts("R")

    def _result(self, skipped: bool) -> None:
        """The after, measured at every position (decision 5), or the
        expected one kept when the check was skipped."""
        if skipped:
            return
        speakers = {}
        worse = []
        for channel in rc.CHANNELS:
            d = self._designs[channel]
            measured = [c - d.offset for c in self._checked[channel]]
            after = self._dsp.power_average(measured)
            speakers[channel] = replace(self.pending.speakers[channel], after=tuple(after))
            worse += self._dsp.worse_positions(d.positions, measured, d.target, d.cuts)
        found = {}
        for n, db in worse:
            found[n] = max(db, found.get(n, 0))
        self.pending = replace(self.pending, checked=True, speakers=speakers,
                               worse=tuple(sorted(found.items())))
