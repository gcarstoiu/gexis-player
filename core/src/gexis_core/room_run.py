# SPDX-License-Identifier: GPL-3.0-or-later
"""**A measurement of the room, from start to *Keep it*** (ADR-0175 items
4-7; the flow George settled on 2026-11-04 and 2026-11-05).

It runs on the player, so a phone page closed and opened again shows where
it is (the design's R18), and the panel shows that it is running. The steps:

1. *place* - the device taken (what plays stops, nothing else can start),
   waiting for *Start*;
2. *level* - the quiet room listened to, then soft noise, louder in steps
   until the seat hears about 60 dB, never above the output's maximum level;
3. *timing* - short sweeps from each speaker in one recording: how much
   nearer one is, and whether one has + and - swapped (ADR-0185 D2, C1),
   which stops the run; the nearer is delayed from here on, so both arrive
   together; more than `FAR_S` apart, *far* waits for *Measure anyway*;
   then *measure* - each speaker alone, then both together (George,
   2026-11-05: as heard, shown and never corrected), two sweeps that agree
   each, at position 1;
   then *move* (waiting for *Measure here*), a 3-second *countdown*, and
   *measure* again, to the last position - at position 2 *timing* again
   first: 40 cm to the left the left speaker must be nearer than at 1, or
   the speakers are swapped and the run stops (ADR-0185 D1);
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
import math
from dataclasses import dataclass, replace
from typing import Awaitable, Callable

from gexis_core import room_correction as rc

logger = logging.getLogger("gexis_core.room_run")

#: Decision, 2026-11-04: a tap, then a countdown.
COUNTDOWN_S = 3
#: George, 2026-11-05: a run waiting for a tap is cancelled after this.
TIMEOUT_S = 600
#: **The level aimed for at the seat** (George, 2026-11-05): 60 dB in every
#: room - over the 75 dB first proposed, which sofapi's run found far too
#: loud, and the 50 a quiet room's noise gave, at which sofapi's sweeps
#: often had to be repeated; and how close is close enough. A level that
#: cannot reach it is still taken from 45 dB and 15 dB above the noise.
AIM_DB = 60.0
AIM_WITHIN = 1.5
TAKE_MIN = 45.0
TAKE_ABOVE_NOISE = 15.0
#: How long the quiet room is listened to first: 3 s (ADR-0185 C3, from
#: 1.5), its noise kept to judge every sweep by.
NOISE_S = 3.0
#: The level step: from this, in these steps - the signal's part; the volume
#: is at the output's maximum (`host.loud`). The noise goes no higher than
#: its cap, where its peaks come near full scale; the sweeps further, set
#: from the noise's last reading as the chain is linear (George, 2026-11-05:
#: 60 dB; sofapi reached 50 at -18 dBFS), until their peaks reach
#: `SWEEP_PEAK_DBFS` - the level in the band that is depends on how much of
#: the sweep lies in it (`Run._sweep_cap`: -6 dBFS for Phase 29's to 1 kHz,
#: about -8 for one to 20 kHz).
LEVEL_START_DBFS = -54.0
LEVEL_STEP_DB = 3.0
LEVEL_CAP_DBFS = -12.0
SWEEP_PEAK_DBFS = -1.5
LEVEL_BURST_S = 1.0
#: Where in a burst's recording the level is read: from the lead's end and
#: the chain's start to before the burst's fade - the noise alone.
LEVEL_WINDOW_S = (0.5, 1.2)
LEVEL_TAIL_S = 0.2
#: The noise is raised only while the microphone follows it: once it is
#: clearly heard (`LEVEL_HEARD_OVER` above the room's noise), steps that
#: move the reading by less than `LEVEL_HEARD_DB`, this many in a row, end
#: it. Until it is heard the cap alone bounds it: the first steps may be
#: well under the room's noise.
LEVEL_HEARD_OVER = 6.0
LEVEL_HEARD_DB = 1.5
LEVEL_UNHEARD_STEPS = 4
#: Item 4: sweeps per speaker at a position, and how many tries before the
#: two that agree best are taken.
SWEEPS = 2
MAX_SWEEPS = 6
#: **ADR-0185**: the two timings taken agree within this (1 cm, C1); more
#: than `FAR_S` (1 ms, 34 cm) apart the screen says a speaker or the seat
#: looks out of place (C2); at position 2 the left must be heard at least
#: `SIDES_S` (10 cm) nearer than at 1, or - that much the other way - the
#: speakers are swapped (D1). 40 cm to the side moves the difference by
#: about 2 x 40 cm x sin(half the angle between the speakers): 40 cm at
#: ±30°, 21 cm at ±15°, so 10 cm is under half the least.
TIMING_AGREE_S = 0.01 / 343.0
FAR_S = 0.001
SIDES_S = 0.10 / 343.0
TIMING_TAIL_S = 0.3


class Cancelled(Exception):
    pass


class _Skipped(Exception):
    """*Skip* pressed while the check sweeps."""


@dataclass(frozen=True)
class RunState:
    """What every screen shows of a run (the design's *State*)."""
    step: str                       # place level timing far measure move countdown correction nothing checking result
    position: int = 1               # 1 to rc.POSITIONS
    speaker: str | None = None      # "L" / "R" / "both" while one plays
    sweep: int = 0                  # 1-2 while one plays
    sweeps: int = 0                 # how many the set takes: 2, the check more (ADR-0185 C3)
    noise: bool = False             # the last sweep was spoiled and is repeated
    level_db: float | None = None   # at the seat, in the level step and after
    aim_db: float | None = None     # the level aimed for
    count: int = 0                  # the countdown's number
    checking: bool = False          # the check's positions, not the run's
    progress: float = 0.0           # 0-1, as the design's §3
    done: tuple[int, ...] = ()      # the positions measured (or checked) so far
    expected: bool = False          # the result is expected, the check skipped
    too_quiet: bool = False         # the level step could not reach the aim
    resumed_from: str | None = None
    #: ADR-0185: how much further the right speaker is than the left (cm,
    #: negative: the left is further), once timed at position 1.
    distance_cm: float | None = None

    def as_dict(self) -> dict:
        return {"step": self.step, "position": self.position, "speaker": self.speaker, "sweep": self.sweep,
                "sweeps": self.sweeps,
                "noise": self.noise, "level_db": None if self.level_db is None else round(self.level_db),
                "aim_db": None if self.aim_db is None else round(self.aim_db),
                "count": self.count, "checking": self.checking, "progress": round(self.progress, 3),
                "done": list(self.done), "expected": self.expected, "too_quiet": self.too_quiet,
                "positions": rc.POSITIONS,
                "distance_cm": None if self.distance_cm is None else round(self.distance_cm, 1),
                "far_cm": round(FAR_S * 343.0 * 100)}


def _screen(state: RunState) -> tuple:
    """What a tap answers: the step, the position and *Too quiet*."""
    return state.step, state.position, state.checking, state.too_quiet


def _progress(step: str, position: int = 1, speaker: str | None = None, sweep: int = 0,
              checking: bool = False) -> float:
    """The design's §3: the level 5 %; positions 8 to 78 % (each an equal
    share for the left, the right and both, half of it a sweep); checking 80
    to 100 %."""
    share = 1 / len(rc.SWEPT)
    part = rc.SWEPT.index(speaker) * share if speaker in rc.SWEPT else 0.0
    if checking:
        return 0.8 + 0.2 * (position - 1 + (part if step == "checking" else 0)) / rc.POSITIONS
    if step == "level":
        return 0.05
    if step == "place":
        return 0.0
    base = 0.08 + 0.7 * (position - 1) / rc.POSITIONS
    if step == "measure":
        base += 0.7 / rc.POSITIONS * (part + share / SWEEPS * max(0, min(sweep, SWEEPS) - 1))
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
        #: The most a sweep's level in the band may be: its peaks at
        #: `SWEEP_PEAK_DBFS`.
        self._sweep_cap = SWEEP_PEAK_DBFS + self._dsp.band_level_db(self._dsp.log_sweep(seconds=self._sweep_s))
        self._taps: asyncio.Queue = asyncio.Queue()
        #: The screen the phone shows, numbered: one more at each new step,
        #: position or *Too quiet* (`_set`); a tap carries the one it was
        #: sent on.
        self._shown = 0
        self._task: asyncio.Task | None = None
        self.state = RunState("place")
        self.pending: rc.Measurement | None = None
        self.ended: dict | None = None        # {"how": cancelled|kept|discarded|done|failed, ...}
        self._level_dbfs = LEVEL_START_DBFS
        self._aim: float | None = None
        self._positions: dict[str, list] = {c: [] for c in rc.SWEPT}
        self._checked: dict[str, list] = {c: [] for c in rc.SWEPT}
        #: Both speakers' positions on the bass's finer grid (ADR-0187 C5).
        self._fine: list = []
        self._designs: dict = {}
        #: How much lower the check's sweeps play: the broad corrections'
        #: highest point (ADR-0177 item 7) - the stage takes no headroom for
        #: them while a run measures, so the run's level stays the run's.
        self._check_db = 0.0
        #: ADR-0185 C3: the quiet room's noise per grid point (`band_power`),
        #: and each position's averaged signal over it, by speaker.
        self._noise = None
        self._noise_curves: dict = {}     # by (recording's length, sweep's amplitude)
        self._snrs: dict[str, list] = {c: [] for c in rc.SWEPT}
        #: ADR-0185 C1-C2: position 1's timing, and the delay on each channel
        #: (ms) that brings both speakers' sound to the seat together.
        self._timing = None
        self._delay = (0.0, 0.0)
        self._waiting = False
        self._prep: asyncio.Future | None = None
        self._finishing = False
        #: The player put back after the run: no other source until then.
        self.released = False

    # -- what the control calls ----------------------------------------------------

    async def start(self) -> None:
        """**Begins at once** (George, 2026-11-05: Measure was slow to
        answer): the run shows *place* from here, and the player is prepared
        behind it - the device taken, the stage in the path, the level - while
        the microphone is put in place. *Start* waits for that."""
        self._set(RunState("place"))
        self._prep = asyncio.ensure_future(self._prepare())
        self._task = asyncio.create_task(self._running())

    async def _prepare(self) -> None:
        await self._host.take()
        await self._host.stage(None)
        await self._host.loud()

    def tap(self, what: str) -> None:
        """`start`, `next` (*Measure here*), `check` (*Check it*), `skip`,
        `keep`, `discard`, `again` (*Try again*), `done`. **A tap is for the
        screen it was sent on** (the review of 1.16.1): a second *Measure
        here* that came after the run had moved on answered the next
        position's, which was then swept where the last one was."""
        self._taps.put_nowait((what, self._shown))

    def cancel(self) -> None:
        """**Cancel is instant** (George, 2026-11-05): the end is shown at
        once and the sound stops (the run's task is cancelled, which stops
        what plays); putting the player back follows, and other sources are
        let in once it has (`released`)."""
        if self.ended is None:
            self.ended = {"how": "cancelled", "why": "cancel"}
            self._host.publish(None, dict(self.ended))
        if self._task is not None and not self._task.done():
            self._task.cancel()

    async def wait(self) -> None:
        """Until the run, its putting back included, is over."""
        if self._task is not None:
            try:
                await asyncio.shield(self._task)
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
        if state.aim_db is None and self._aim is not None:
            state = replace(state, aim_db=self._aim)
        if state.distance_cm is None and self._timing is not None:
            state = replace(state, distance_cm=self._timing.cm)
        if _screen(state) != _screen(self.state):
            self._shown += 1
        self.state = state
        self._host.publish(state, None)

    async def _wait(self, *accepted: str) -> str:
        """The phone's next tap among `accepted`, sent on this screen;
        *cancel* never comes here (it cancels the task). After `TIMEOUT_S`
        the run is cancelled."""
        self._waiting = True
        try:
            while True:
                try:
                    what, shown = await asyncio.wait_for(self._taps.get(), self._timeout)
                except asyncio.TimeoutError:
                    logger.info("room: nobody tapped for %d s, the run is cancelled", self._timeout)
                    raise Cancelled("timeout")
                if what in accepted and shown == self._shown:
                    return what
                logger.debug("room: %s ignored while waiting for %s", what, "/".join(accepted))
        finally:
            self._waiting = False

    async def _running(self) -> None:
        how, why = "failed", None
        try:
            # Shielded: cancelling never stops it halfway through a rewrite
            # of the chain; `_end` waits for it before putting things back.
            await asyncio.shield(self._prep)
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
        await self._align()
        for n in range(1, rc.POSITIONS + 1):
            if n > 1:
                await self._move(n, checking=False)
            if n == 2:
                await self._sides()
            await self._measure(n, checking=False)
        self._design()
        all_done = tuple(range(1, rc.POSITIONS + 1))
        if self.pending.nothing_to_correct:
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
        if self.ended is None:
            self.ended = {"how": how, "why": why}
            self._host.publish(None, dict(self.ended))
        if self._finishing:
            return
        self._finishing = True
        if self._prep is not None and not self._prep.done():
            await asyncio.wait([self._prep])
        try:
            await self._host.finish(self.pending if self.ended["how"] == "kept" else None)
        except Exception:  # noqa: BLE001
            logger.exception("room: could not put the player back")
        self.released = True
        logger.info("room: the run ended (%s%s)", self.ended["how"],
                    f", {self.ended['why']}" if self.ended.get("why") else "")
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
        """**The level step** (item 4): the quiet room listened to first;
        then pink noise from `LEVEL_START_DBFS`, 3 dB a step, until the seat
        hears about the aim - only while the microphone follows, and never
        above the noise's cap; from there the sweeps go the rest of the way,
        up to their own. A level short of the aim is taken from `TAKE_MIN`
        and `TAKE_ABOVE_NOISE` over the noise; below that, False (*Too
        quiet*)."""
        self._set(RunState("level", progress=0.05))
        dsp = self._dsp
        import numpy as np
        quiet = await self._audio.play(np.zeros(int(NOISE_S * dsp.FS)), channel=None, tail_s=LEVEL_TAIL_S)
        lo, hi = (int(t * dsp.FS) for t in LEVEL_WINDOW_S)
        room_noise = self._spl(quiet[lo:])
        self._noise = dsp.band_power(quiet[lo:])
        aim = AIM_DB
        self._aim = aim
        take = max(TAKE_MIN, room_noise + TAKE_ABOVE_NOISE)
        self._set(replace(self.state, aim_db=aim))
        logger.info("room: the room's noise %.0f dB at the seat; aiming for %.0f dB", room_noise, aim)
        noise = dsp.pink_noise(LEVEL_BURST_S)
        level = LEVEL_START_DBFS
        last = None
        unheard = 0
        heard = False
        while True:
            recording = await self._audio.play(noise * 10 ** (level / 20), channel=None, tail_s=LEVEL_TAIL_S)
            spl = self._spl(recording[lo:hi])
            self._set(replace(self.state, level_db=spl))
            if abs(spl - aim) <= AIM_WITHIN:
                break
            if spl > aim:
                level -= max(1.0, spl - aim)
                if level < LEVEL_START_DBFS - 30:
                    break
                continue
            heard = heard or spl >= room_noise + LEVEL_HEARD_OVER
            if heard and last is not None and spl - last < LEVEL_HEARD_DB:
                unheard += 1
            else:
                unheard = 0
            last = spl if heard else None
            step = min(LEVEL_STEP_DB, max(1.0, aim - spl))
            if level + step > LEVEL_CAP_DBFS or unheard >= LEVEL_UNHEARD_STEPS:
                if heard and unheard == 0:
                    # The noise at its cap and the microphone following it:
                    # the sweeps the rest of the way, up to their own cap.
                    sweep = min(self._sweep_cap, level + aim - spl)
                    logger.info("room: %.0f dB at the seat at %.0f dBFS, the noise's most; the sweeps at %.0f",
                                spl, level, sweep)
                    spl, level = spl + sweep - level, sweep
                    self._set(replace(self.state, level_db=spl))
                if spl >= aim - AIM_WITHIN and unheard < LEVEL_UNHEARD_STEPS:
                    break
                if spl >= take and unheard < LEVEL_UNHEARD_STEPS:
                    logger.info("room: %.0f dB at the seat at %.0f dBFS, short of %.0f: taken", spl, level, aim)
                    break
                logger.info("room: %.0f dB at the seat at %.0f dBFS: too quiet", spl, level)
                return False
            level += step
        self._level_dbfs = level
        logger.info("room: %.0f dB at the seat at %.0f dBFS", self.state.level_db, level)
        return True

    # -- the speakers' timing (ADR-0185) -------------------------------------------

    async def _time(self, n: int):
        """**The right's arrival against the left's** at position `n` (C1):
        one recording of short sweeps, left, right, left, taken until two
        agree within `TIMING_AGREE_S` and on the polarity, up to
        `MAX_SWEEPS`. The stage's own delay is taken back out, so it is the
        room's. None when no two agree: nothing is said and nothing is
        delayed - a reading that does not repeat is not one."""
        dsp = self._dsp
        self._set(RunState("timing", position=n, done=tuple(range(1, n)), level_db=self.state.level_db,
                           progress=_progress("timing", n)))
        signal = dsp.timing_signal(min(1.0, self._sweep_scale()))
        found = []
        pair = None
        for _ in range(MAX_SWEEPS):
            lit = asyncio.ensure_future(self._light_timing())
            try:
                recording = await self._audio.play(signal, channel=None, tail_s=TIMING_TAIL_S)
            finally:
                lit.cancel()
                self._set(replace(self.state, speaker=None))
            got = dsp.timing(recording)
            if got is None:
                continue
            for other in found:
                if (other.same_polarity == got.same_polarity
                        and abs(other.late_s - got.late_s) <= TIMING_AGREE_S):
                    pair = (other, got)
                    break
            found.append(got)
            if pair is not None:
                break
        if pair is None:
            logger.info("room: position %d: the speakers' timing could not be read - %d of %d readings, "
                        "none two agreeing", n, len(found), MAX_SWEEPS)
            return None
        # The stage delays the left by `_delay[0]` and the right by `[1]`.
        late = (pair[0].late_s + pair[1].late_s) / 2 + (self._delay[0] - self._delay[1]) / 1000
        timing = dsp.Timing(late, pair[0].same_polarity, min(pair[0].alike, pair[1].alike))
        logger.info("room: position %d: the right %+.1f cm against the left (%.1f cm between the two taken, "
                    "%d readings), %s polarity, %.2f alike", n, timing.cm, abs(pair[0].cm - pair[1].cm),
                    len(found), "the same" if timing.same_polarity else "opposite", timing.alike)
        return timing

    async def _light_timing(self) -> None:
        """**The short sweeps light the speaker they come from** (George,
        2026-11-23, as the measuring sweeps do): the left, the right, the
        left again, a slot each, from when the signal starts."""
        await self._sleep(getattr(self._audio, "lead_s", 0.0))
        for channel in ("L", "R", "L"):
            self._set(replace(self.state, speaker=channel))
            await self._sleep(self._dsp.TIMING_SLOT_S)

    async def _align(self) -> None:
        """**Position 1, before the sweeps** (D2): the speakers timed; one
        with + and - swapped stops the run; the nearer is delayed so both
        arrive together, on the stage from here on - the sweeps measure
        what will play; more than `FAR_S` apart, *far* waits for *Measure
        anyway*."""
        timing = await self._time(1)
        if timing is None:
            return
        if not timing.same_polarity:
            raise Cancelled("polarity")
        self._timing = timing
        ms = abs(timing.late_s) * 1000
        self._delay = (ms, 0.0) if timing.late_s > 0 else (0.0, ms)
        await self._host.stage(self._play())
        if abs(timing.late_s) > FAR_S:
            self._set(RunState("far", position=1, level_db=self.state.level_db, progress=_progress("timing", 1)))
            await self._wait("next")

    async def _sides(self) -> None:
        """**Position 2, 40 cm to the left** (D1): the left must be nearer
        than at position 1. The other way by `SIDES_S` or more, the speakers
        are swapped - or the microphone went to the right - and the run
        stops; less either way, nothing is said."""
        if self._timing is None:
            return
        timing = await self._time(2)
        if timing is None:
            return
        moved = timing.late_s - self._timing.late_s
        if moved <= -SIDES_S:
            logger.info("room: position 2: the left %.0f cm further than at position 1 - swapped", -moved * 34300)
            raise Cancelled("swapped")
        if moved < SIDES_S:
            logger.info("room: position 2: the left only %.0f cm nearer than at position 1 - left and right "
                        "not told apart", moved * 34300)

    def _play(self, cuts=((), ()), above=((), ())):
        """What the stage plays during the run: `cuts` and `above` (none
        until the check), with the speakers' delay."""
        from gexis_core import equaliser as eq
        return eq.RoomPlay(cuts, above, None, self._delay)

    # -- the sweeps ------------------------------------------------------------------

    def _sweep_scale(self) -> float:
        """The sweeps' amplitude: their level in the band matched to the
        noise's (`_level`)."""
        dsp = self._dsp
        sweep = dsp.log_sweep(seconds=self._sweep_s)
        return 10 ** (self._level_dbfs / 20) / 10 ** (dsp.band_level_db(sweep) / 20)

    async def _curve(self, channel: str) -> tuple:
        """One sweep: its curve, how far it stood over the room's noise at
        each point (ADR-0185 C3; None before the level step heard it), and
        for both speakers in the run its curve on the bass's finer grid
        (ADR-0187 C5; else None)."""
        import numpy as np
        dsp = self._dsp
        sweep = dsp.log_sweep(seconds=self._sweep_s)
        # The sweep's level in the band, matched to the noise's; both
        # speakers 6 dB lower each, so the two adding in the bass are no
        # louder than one; in the check lower by what the corrections raise.
        scale = self._sweep_scale()
        if self.state.checking:
            scale *= 10 ** (-self._check_db / 20)
        both = channel == rc.BOTH
        played = sweep * scale * (0.5 if both else 1.0)
        # ADR-0187 C4: every sweep after its timing mark, the timing step's
        # sweep on the left at the timing step's level (lower in the check,
        # with the sweeps).
        columns = (0, 1) if both else (rc.CHANNELS.index(channel),)
        mark_amp = min(1.0, self._sweep_scale())
        if self.state.checking:
            mark_amp *= 10 ** (-self._check_db / 20)
        recording = await self._audio.play(dsp.marked(played, columns, mark_amp),
                                           channel=columns if both else columns[0])
        played = dsp.mark_reference(played)
        self._mark = dsp.mark_at(recording)
        ir = dsp.transfer(recording, played)
        curve = dsp.response_db(ir)
        fine = dsp.response_fine(ir) - self._calibration_fine() if both and not self.state.checking else None
        snr = None
        if self._noise is not None:
            key = (len(recording), round(float(np.max(np.abs(played))), 9))
            if key not in self._noise_curves:
                self._noise_curves[key] = dsp.noise_curve(self._noise, played, len(recording))
            snr = dsp.snr_db(curve, self._noise_curves[key])
        return curve - self._calibration_curve(), snr, fine

    def _calibration_fine(self):
        if not hasattr(self, "_cal_fine"):
            import numpy as np
            self._cal_fine = np.array([self._cal.db_at(float(f)) for f in self._dsp.FINE_GRID])
        return self._cal_fine

    def _calibration_curve(self):
        if not hasattr(self, "_cal_curve"):
            import numpy as np
            self._cal_curve = np.array([self._cal.db_at(float(f)) for f in self._dsp.GRID])
        return self._cal_curve

    def _sweeps_wanted(self, checking: bool) -> int:
        """Two; **the check more, for its lower level** (ADR-0185 C3): as
        many more as make up the power it plays below the run, within
        `MAX_SWEEPS` less one, so a disturbed one can still be repeated."""
        if not checking or self._check_db <= 0:
            return SWEEPS
        return min(MAX_SWEEPS - 1, math.ceil(SWEEPS * 10 ** (self._check_db / 10) - 1e-9))

    def _undisturbed(self, curves, snrs):
        """**The sweeps no noise disturbed** (ADR-0185 C3): the two that
        agree best, compared only where both stand `JUDGE_SNR_DB` over the
        room's noise, and every other that agrees with both of them there.
        With them, for the log, the two's gap, where it was and how far over
        the noise they stood there; the sweeps are None when the two do not
        agree."""
        import numpy as np
        dsp = self._dsp

        def judged(i, j):
            if snrs[i] is None or snrs[j] is None:
                return None
            return (np.asarray(snrs[i]) >= dsp.JUDGE_SNR_DB) & (np.asarray(snrs[j]) >= dsp.JUDGE_SNR_DB)

        best = None
        for i in range(len(curves)):
            for j in range(i + 1, len(curves)):
                gap, where = dsp.gap_at(curves[i], curves[j], judged=judged(i, j))
                if best is None or gap < best[0]:
                    best = (gap, where, i, j)
        gap, where, i, j = best
        there = None
        if where is not None and snrs[i] is not None:
            k = int(np.argmin(np.abs(np.asarray(dsp.GRID) - where)))
            there = float(min(snrs[i][k], snrs[j][k]))
        if gap > dsp.AGREE_DB:
            return None, (gap, where, there, (i, j))
        kept = [k for k in range(len(curves))
                if k in (i, j) or all(dsp.agree_db(curves[k], curves[m], judged=judged(k, m)) <= dsp.AGREE_DB
                                      for m in (i, j))]
        return kept, (gap, where, there, (i, j))

    async def _measure(self, n: int, checking: bool) -> None:
        """Each speaker alone at position `n` (item 4), then both: sweeps
        until those no noise disturbed agree (`_undisturbed`), up to
        `MAX_SWEEPS`, then the two closest; all of those averaged."""
        dsp = self._dsp
        step = "checking" if checking else "measure"
        done = tuple(range(1, n))
        wanted = self._sweeps_wanted(checking)
        for channel in rc.SWEPT:
            curves, snrs, fines = [], [], []
            noise = False
            while True:
                k = len(curves) + 1
                self._set(RunState(step, position=n, speaker=channel, sweep=min(k, wanted), sweeps=wanted,
                                   noise=noise, checking=checking, done=done, level_db=self.state.level_db,
                                   progress=_progress(step, n, channel, min(k, SWEEPS), checking)))
                curve, snr, fine = await self._curve(channel)
                curves.append(curve)
                snrs.append(snr)
                fines.append(fine)
                if checking and self._skip_sent():
                    raise _Skipped()
                if len(curves) < wanted:
                    continue
                kept, (gap, where, there, pair) = self._undisturbed(curves, snrs)
                self._log_sweeps(n, channel, checking, curves, snrs, gap, where, there, kept)
                if kept is not None:
                    break
                if len(curves) >= MAX_SWEEPS:
                    kept = list(pair)
                    break
                noise = True
            chosen = [curves[k] for k in kept]
            (self._checked if checking else self._positions)[channel].append(dsp.power_average(chosen))
            if fines[0] is not None:
                self._fine.append(dsp.power_average([fines[k] for k in kept]))
            if not checking:
                got = [snrs[k] for k in kept if snrs[k] is not None]
                self._snrs[channel].append(dsp.averaged_snr(got) if got else None)

    def _log_sweeps(self, n, channel, checking, curves, snrs, gap, where, there, kept) -> None:
        """**ADR-0185 C4: every comparison, as numbers**, so `AGREE_DB` and
        `JUDGE_SNR_DB` are settled from runs: the closest two's gap, where,
        and how far over the noise they stood there; how much of 20-250 Hz
        was judged, and the least a sweep stood over the noise there."""
        import numpy as np
        dsp = self._dsp
        grid = np.asarray(dsp.GRID)
        bass = (grid >= dsp.FIT_LO) & (grid <= dsp.LIMIT)
        got = [np.asarray(x)[bass] for x in snrs if x is not None]
        judged = int(np.sum(np.all([x >= dsp.JUDGE_SNR_DB for x in got], axis=0))) if got else 0
        least = float(min(np.min(x) for x in got)) if got else float("nan")
        logger.info("room: %s %d, %s: %d sweeps, the closest two %.1f dB apart at %s Hz (%s dB over the noise "
                    "there); %d of %d points judged, the least %.0f dB over the noise; %s",
                    "check" if checking else "position", n, channel, len(curves), gap,
                    "-" if where is None else f"{where:.0f}", "-" if there is None else f"{there:.0f}",
                    judged, int(np.sum(bass)), least,
                    "again" if kept is None and len(curves) < MAX_SWEEPS
                    else f"{len(kept or ())} averaged" if kept else "the closest two taken")

    def _skip_sent(self) -> bool:
        """Whether *Skip* came while the check swept (the design: Skip on
        every check screen); any other tap then is dropped, as it would be
        ignored."""
        found = False
        while not self._taps.empty():
            found = self._taps.get_nowait()[0] == "skip" or found
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
        """The bass's cuts from both speakers together, the same on both
        (ADR-0175's amendment), fitted on the finer grid (ADR-0187 C5);
        above the bass each speaker's own. The head counts as much as the
        other positions together throughout (D5; both kept on Finding 158)."""
        fine = self._fine if len(self._fine) == len(self._positions[rc.BOTH]) else None
        both = self._dsp.together(self._positions[rc.BOTH], trust=self._trust(rc.BOTH), head=True, fine=fine)
        self._designs[rc.BOTH] = both
        speakers = {rc.BOTH: _speaker(both)}
        for channel in rc.CHANNELS:
            d = self._dsp.design(self._positions[channel], cuts=both.cuts, trust=self._trust(channel), head=True)
            self._designs[channel] = d
            speakers[channel] = _speaker(d)
        self.pending = rc.Measurement(self._today(), False, speakers, range=rc.FULL, delay=self._delay,
                                      distance_cm=None if self._timing is None else round(self._timing.cm, 1))

    def _trust(self, channel: str):
        """Where every position's averaged sweeps stand `TRUST_SNR_DB` over
        the room's noise (ADR-0185 C3); None (everywhere) when not read."""
        import numpy as np
        got = self._snrs[channel]
        if not got or any(x is None for x in got):
            return None
        trust = np.min(np.asarray(got), axis=0) >= self._dsp.TRUST_SNR_DB
        grid = np.asarray(self._dsp.GRID)
        bass = (grid >= self._dsp.FIT_LO) & (grid <= self._dsp.LIMIT)
        if not trust[bass].all():
            low = grid[bass & ~trust]
            logger.info("room: %s: %d points left uncorrected, under %.0f dB over the noise (%.0f-%.0f Hz)",
                        channel, int(np.sum(~trust)), self._dsp.TRUST_SNR_DB, low.min(), low.max())
        return trust

    def _cuts(self):
        """**What the check plays** (ADR-0177 item 8): the full range, the
        correction a new measurement starts with - with no headroom taken
        for its raises; its sweeps play that much lower instead."""
        from gexis_core import equaliser as eq
        cuts = tuple(self.pending.cuts(c) for c in rc.CHANNELS)
        above = tuple(self.pending.above(c) for c in rc.CHANNELS)
        self._check_db = eq.headroom_db(eq.FLAT, tuple(c + a for c, a in zip(cuts, above)))
        return self._play(cuts, above)

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
            # *Bass*: the broad corrections taken out of what was measured,
            # exact for filters one after another.
            after_bass = after - self._dsp.cuts_db(d.broad, self._dsp.GRID)
            speakers[channel] = replace(self.pending.speakers[channel], after=tuple(after),
                                        after_bass=tuple(after_bass),
                                        within=self._dsp.within_db(after, d.target))
            # Above the bass each speaker's own corrections are judged on it.
            worse += self._dsp.worse_positions(d.positions, measured, d.target, list(d.broad))
        # The bass's cuts on what they were designed from: both together.
        d = self._designs[rc.BOTH]
        measured = [c - d.offset for c in self._checked[rc.BOTH]]
        after = self._dsp.power_average(measured)
        speakers[rc.BOTH] = replace(self.pending.speakers[rc.BOTH], after=tuple(after), after_bass=tuple(after))
        worse += self._dsp.worse_positions(d.positions, measured, d.target, list(d.cuts))
        found = {}
        for n, db in worse:
            found[n] = max(db, found.get(n, 0))
        self.pending = replace(self.pending, checked=True, speakers=speakers,
                               worse=tuple(sorted(found.items())))


def _speaker(d) -> rc.Speaker:
    """What the store keeps of one design (`room_dsp.Design`)."""
    return rc.Speaker(cuts=tuple((c.freq, c.gain, c.q) for c in d.cuts),
                      before=tuple(d.before), target=tuple(d.target),
                      after=tuple(d.after), positions=tuple(tuple(p) for p in d.positions),
                      above=tuple((b.freq, b.gain, b.q) for b in d.broad),
                      after_bass=tuple(d.after_bass), within=d.within, room_within=d.room_within)


def redesign(m: rc.Measurement, dsp=None) -> rc.Measurement | None:
    """**A measurement kept from before ADR-0175's amendment** (George,
    2026-11-17: redesigned when the player starts): the bass's cuts designed
    again from its *Both* sweeps, against the targets it keeps, the same on
    both speakers; above the bass each speaker's corrections again with
    them in place (a full-range one only). Its after is then the expected
    one, *Not checked*, until the room is measured again. None when it
    cannot be: no *Both* sweeps (one from before they were taken)."""
    both = m.speakers.get(rc.BOTH)
    if both is None or not both.positions or any(c not in m.speakers for c in rc.CHANNELS):
        return None
    import numpy as np
    if dsp is None:
        from gexis_core import room_dsp as dsp
    grid = rc.grid(len(both.before))
    shared = dsp.together(both.positions, grid, target=both.target)
    speakers = {rc.BOTH: _speaker(shared)}
    for channel in rc.CHANNELS:
        s = m.speakers[channel]
        if m.range == rc.FULL:
            speakers[channel] = _speaker(dsp.design(s.positions, grid, cuts=shared.cuts, target=s.target))
        else:
            # Measured for the bass only (to 500 Hz before Phase 30): no
            # corrections above it to design again.
            after = tuple(dsp.power_average(np.asarray(s.positions) + dsp.cuts_db(shared.cuts, np.asarray(grid))))
            speakers[channel] = replace(s, cuts=tuple((c.freq, c.gain, c.q) for c in shared.cuts),
                                        after=after, after_bass=after)
    return replace(m, checked=False, worse=(), speakers=speakers, bass_from=rc.BOTH)
