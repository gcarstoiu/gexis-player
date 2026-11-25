# SPDX-License-Identifier: GPL-3.0-or-later
"""**Room correction as the player keeps it** (ADR-0175, Phase 29; ADR-0177,
Phase 30): for each output whether it is on, whether *Hear it without* is
set, how far it reaches (*Bass* or *Full range*), and the last measurement
with the corrections made from it; and each microphone's calibration.

Nothing here touches a device or needs numpy: the state is read from the
settings store (`KEY`, so it is in backups and cleared by a factory reset,
item 10) leniently, as the equaliser's is, and turned into what the stage
plays (`stage`) and what the screens draw (`summary`, `chart`).
"""
from __future__ import annotations

import functools
import math
import re
from dataclasses import dataclass, field, replace

from gexis_core import equaliser as eq

KEY = "_room_correction"

#: The speakers, as the screens and the store name them.
CHANNELS = ("L", "R")
#: The most a speaker is delayed (ADR-0185 D2): what the timing can find
#: (`room_dsp.TIMING_REACH_S`, about 5 m).
MAX_DELAY_MS = 15.0
#: Less than this (1 cm) the speakers are as far as the timing can tell.
ALIGN_MIN_MS = 0.01 / 343.0 * 1000
#: ADR-0187 D2: a level match the reading can tell from none (its two
#: readings agree within 0.25 dB; C2).
LEVEL_MIN_DB = 0.1
#: **Both speakers together** (George, 2026-11-05): swept at each position
#: in the run and in the check, as heard. The bass's cuts are designed from
#: them and go on both speakers (ADR-0175's amendment, George 2026-11-17);
#: above the bass the corrections are each speaker's.
BOTH = "both"
#: A measurement's bass designed for each speaker alone, as before the
#: amendment: redesigned from its *Both* sweeps when the player starts.
EACH = "each"
SWEPT = CHANNELS + (BOTH,)
#: Where a run measures (George, 2026-11-05: three, over the five first
#: drawn - the head and 40 cm to either side). A measurement keeps its own
#: number, so one made at five still reads as five. Five, around the head
#: (ADR-0187 D3, George, 2026-11-20).
POSITIONS = 5

#: The grid the curves are kept on (`room_dsp.GRID`: 1/24 octave from
#: 15 Hz; to 500 Hz before Phase 30, to 20 kHz from it).
GRID_LO = 15.0
GRID_STEPS = 24
#: The bass limit (ADR-0175 decision 3).
LIMIT = 250.0

#: **How far it reaches** (ADR-0177; George, 2026-11-07): the bass alone, or
#: the full range. A measurement's range is how far it was made: one from
#: before Phase 30 covers the bass only, and holds its output at *Bass*.
BASS, FULL = "bass", "full"
REACHES = (BASS, FULL)
#: A broad correction above the bass is at most this, up or down.
ABOVE_DB = 3.0


def grid(n: int) -> list[float]:
    return [round(GRID_LO * 2 ** (k / GRID_STEPS), 2) for k in range(n)]


class RoomError(ValueError):
    """A request room correction refuses; its message is for the person."""


def _floats(value, n: int | None = None) -> tuple[float, ...]:
    if not isinstance(value, (list, tuple)) or (n is not None and len(value) != n):
        raise TypeError
    out = []
    for v in value:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise TypeError
        out.append(float(v))
    return tuple(out)


def _round(values, digits: int = 2) -> list[float]:
    """Curves to a hundredth of a decibel: the chart's ±5 dB pane above the
    bass shows a tenth's steps (ADR-0177)."""
    return [round(float(v), digits) for v in values]


def _filters(value, up: bool) -> list[tuple[float, float, float]]:
    out = []
    for c in value or []:
        f, g, q = _floats([c["freq"], c["gain"], c["q"]])
        if f > 0 and q > 0 and (abs(g) <= ABOVE_DB if up else g <= 0):
            out.append((f, g, q))
    return out


def _dicts(filters) -> list[dict]:
    return [{"freq": round(f, 1), "gain": round(g, 1), "q": round(q, 2)} for f, g, q in filters]


def _rings(ringing) -> list[dict]:
    return [{"hz": round(hz, 1), "before": round(b, 1), "after": None if a is None else round(a, 1)}
            for hz, b, a in ringing]


#: **What a dip is put down to** (ADR-0187 D8, C9): the two speakers
#: cancelling, only some places, a wall or the floor near one speaker (or
#: both); none named.
DIP_CAUSES = ("cancel", "local", "wall", None)


def _dip(value) -> tuple:
    """A dip as kept: `(freq, depth, cause, speaker, distance_m)`."""
    freq, depth = _floats([value["freq"], value["depth"]])
    cause = value.get("cause")
    speaker = value.get("speaker")
    distance = value.get("distance_m")
    if cause not in DIP_CAUSES or speaker not in (None, "L", "R", BOTH):
        raise TypeError
    return (freq, depth, cause, speaker, None if distance is None else _floats([distance])[0])


def _aligned(delay) -> bool:
    return max(delay) >= ALIGN_MIN_MS


def _matched(level) -> bool:
    return min(level) <= -LEVEL_MIN_DB


def _delay(value) -> tuple[float, float]:
    delay = tuple(max(0.0, min(MAX_DELAY_MS, float(d))) for d in value or (0.0, 0.0))
    if len(delay) != 2:
        raise TypeError
    return delay


def _level(value) -> tuple[float, float]:
    level = tuple(max(-eq.MAX_LEVEL_DB, min(0.0, float(g))) for g in value or (0.0, 0.0))
    if len(level) != 2:
        raise TypeError
    return level


@dataclass(frozen=True)
class Speaker:
    """One speaker's part of a measurement: its cuts in the bass, its broad
    corrections above it (`above`, ADR-0177), and its curves on the grid,
    relative to the target's level: the after with all of them, and
    (`after_bass`) with the cuts alone. `within` and `room_within` are the
    design's *within N dB of the speaker's own balance*, after and before."""
    cuts: tuple[tuple[float, float, float], ...] = ()
    before: tuple[float, ...] = ()
    target: tuple[float, ...] = ()
    after: tuple[float, ...] = ()
    positions: tuple[tuple[float, ...], ...] = ()
    above: tuple[tuple[float, float, float], ...] = ()
    after_bass: tuple[float, ...] = ()
    within: float | None = None
    room_within: float | None = None
    #: **The bass's ringing** (ADR-0187 D7, C6): per third octave, the
    #: level 0.2 s after the arrival at the head (dB, against the first
    #: 50 ms before the correction) - `(hz, before, after)`, after None when
    #: not read.
    ringing: tuple[tuple[float, float, float | None], ...] = ()
    #: **The check at each position** (ADR-0187, 2026-11-25, George:
    #: always kept): the curve measured with the correction on, as
    #: `positions`; empty when the check was skipped or not kept.
    checks: tuple[tuple[float, ...], ...] = ()
    #: **What the check took out** (ADR-0187 D9): broad corrections the
    #: design gave that made it worse at the positions placed again, as
    #: `above`; `checks` are without them.
    taken: tuple[tuple[float, float, float], ...] = ()

    def as_dict(self) -> dict:
        out = {"cuts": _dicts(self.cuts),
               "before": _round(self.before), "target": _round(self.target), "after": _round(self.after),
               "positions": [_round(p) for p in self.positions]}
        if self.above:
            out["above"] = _dicts(self.above)
        if self.after_bass:
            out["after_bass"] = _round(self.after_bass)
        if self.within is not None:
            out["within"] = self.within
        if self.room_within is not None:
            out["room_within"] = self.room_within
        if self.ringing:
            out["ringing"] = _rings(self.ringing)
        if self.checks:
            out["checks"] = [_round(p) for p in self.checks]
        if self.taken:
            out["taken"] = _dicts(self.taken)
        return out

    @classmethod
    def from_dict(cls, value) -> Speaker:
        before = _floats(value.get("before") or [])
        n = len(before)
        target = _floats(value.get("target") or [], n)
        # None for both speakers when the check was skipped.
        after = _floats(value.get("after") or [], n if value.get("after") else None)
        after_bass = _floats(value.get("after_bass") or [], n if value.get("after_bass") else None)
        positions = tuple(_floats(p, n) for p in value.get("positions") or [])
        within, room_within = value.get("within"), value.get("room_within")
        try:
            checks = tuple(_floats(c, n) for c in value.get("checks") or [])
        except TypeError:
            checks = ()     # what the check found is kept to show; never loses the measurement
        ringing = []
        for r in value.get("ringing") or []:
            try:
                hz, was = _floats([r["hz"], r["before"]])
                now = None if r.get("after") is None else _floats([r["after"]])[0]
            except (KeyError, TypeError):
                continue
            ringing.append((hz, was, now))
        return cls(tuple(_filters(value.get("cuts"), False)[:eq.ROOM_SLOTS]), before, target, after, positions,
                   tuple(_filters(value.get("above"), True)[:eq.ABOVE_SLOTS]), after_bass,
                   None if within is None else _floats([within])[0],
                   None if room_within is None else _floats([room_within])[0], tuple(ringing), checks,
                   tuple(_filters(value.get("taken"), True)[:eq.ABOVE_SLOTS]))

    def peaks_down(self) -> float:
        """*Peaks down by up to N dB*: the most taken off below the limit."""
        top = 0.0
        for f, b, a in zip(grid(len(self.before)), self.before, self.after):
            if f <= LIMIT:
                top = max(top, b - a)
        return top


@dataclass(frozen=True)
class Measurement:
    """The last measurement of an output (item 10): when, at how many
    positions, whether its check was done (*Not checked* when skipped), how
    far it was made (`range`: one kept before Phase 30 says nothing, and is
    the bass's), what its bass was designed from (`bass_from`: one kept
    before ADR-0175's amendment says nothing, and is each speaker's), and
    each speaker's part."""
    date: str
    checked: bool
    speakers: dict = field(default_factory=dict)     # "L"/"R"/"both" -> Speaker
    positions: int = POSITIONS
    #: Positions the check found further from the target, as (n, dB).
    worse: tuple[tuple[int, float], ...] = ()
    range: str = FULL
    bass_from: str = BOTH
    #: **ADR-0185 D2**: the delay on each speaker (ms; the nearer one's), so
    #: both arrive at the seat together, and how much further the right is
    #: than the left (cm; None: not timed - one kept from before, or not read).
    delay: tuple[float, float] = (0.0, 0.0)
    distance_cm: float | None = None
    #: **ADR-0187 D2**: each speaker's level (dB; the louder one's cut), so
    #: both are as loud at the seat; (0, 0) for one kept from before, or not
    #: read.
    level: tuple[float, float] = (0.0, 0.0)
    #: **The dips the correction leaves** (ADR-0187 D8, C9), deepest first:
    #: `(freq, depth under the target, cause, speaker, distance_m)`.
    dips: tuple[tuple, ...] = ()

    def as_dict(self) -> dict:
        out = {"date": self.date, "checked": self.checked, "positions": self.positions, "range": self.range,
               "bass_from": self.bass_from, "worse": [list(w) for w in self.worse],
               "delay": [round(d, 4) for d in self.delay], "distance_cm": self.distance_cm,
               "level": [round(g, 2) for g in self.level],
               "speakers": {k: v.as_dict() for k, v in self.speakers.items()}}
        if self.dips:
            out["dips"] = dips_shown(self.dips)
        return out

    @classmethod
    def from_dict(cls, value) -> Measurement:
        date = value["date"]
        if not isinstance(date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            raise TypeError
        speakers = {k: Speaker.from_dict(value["speakers"][k]) for k in CHANNELS}
        if isinstance(value["speakers"].get(BOTH), dict):
            speakers[BOTH] = Speaker.from_dict(value["speakers"][BOTH])
        worse = tuple((int(n), float(db)) for n, db in value.get("worse") or [])
        made = value.get("range", BASS)
        delay = _delay(value.get("delay"))
        distance = value.get("distance_cm")
        level = _level(value.get("level"))
        dips = []
        for d in value.get("dips") or []:
            try:
                dips.append(_dip(d))
            except (KeyError, TypeError, AttributeError):
                continue
        return cls(date, bool(value.get("checked", False)), speakers,
                   int(value.get("positions", POSITIONS)), worse, made if made in REACHES else BASS,
                   BOTH if value.get("bass_from") == BOTH else EACH, delay,
                   None if distance is None else float(distance), level, tuple(dips))

    def cuts(self, channel: str) -> tuple[tuple[float, float, float], ...]:
        s = self.speakers.get(channel)
        return s.cuts if s else ()

    def above(self, channel: str) -> tuple[tuple[float, float, float], ...]:
        s = self.speakers.get(channel)
        return s.above if (s and self.range == FULL) else ()

    @property
    def nothing_to_cut(self) -> bool:
        return not any(self.cuts(c) for c in CHANNELS)

    @property
    def nothing_above(self) -> bool:
        return not any(self.above(c) for c in CHANNELS)

    @property
    def aligned(self) -> bool:
        """**A speaker delayed** (ADR-0185 D2) by more than the timing can
        tell from none (1 cm)."""
        return _aligned(self.delay)

    @property
    def matched(self) -> bool:
        """**A speaker turned down** (ADR-0187 D2) to match the other."""
        return _matched(self.level)

    @property
    def nothing_to_correct(self) -> bool:
        """*Nothing to correct* (the design): no cut, no broad correction, no
        speaker to delay (ADR-0185) and none to turn down (ADR-0187 D2)."""
        return self.nothing_to_cut and self.nothing_above and not self.aligned and not self.matched

    def peaks_down(self) -> float:
        return max((self.speakers[c].peaks_down() for c in CHANNELS if c in self.speakers), default=0.0)

    def within(self, room: bool = False) -> float | None:
        """*Within N dB of the speaker's own balance*: the larger of the two
        speakers', after (or the room's own); None before Phase 30."""
        got = [getattr(self.speakers[c], "room_within" if room else "within") for c in CHANNELS
               if c in self.speakers]
        got = [w for w in got if w is not None]
        return max(got) if got else None


def dips_shown(dips) -> list[dict]:
    return [{"freq": round(f, 1), "depth": round(d, 1), "cause": c, "speaker": k,
             "distance_m": None if m is None else round(m, 2)} for f, d, c, k, m in dips]


#: **When room correction no longer fits** (ADR-0188 C4): a pair adding in
#: phase would move by more than this somewhere in the bass - the check's
#: own guard for a place worse than before (`room_dsp.WORSE_DB`).
STALE_DB = 1.0


def pair_moves_db(was_delay, was_level, delay, level) -> float:
    """**How far the two speakers' sum moves** (ADR-0188 C4) when their
    delay and level change from `was_*` to these: the most, from 20 Hz to
    the bass limit, that a pair adding in phase rises or falls (dB)."""
    late = ((delay[0] - delay[1]) - (was_delay[0] - was_delay[1])) / 1000
    gain = 10 ** (((level[1] - level[0]) - (was_level[1] - was_level[0])) / 20)
    worst = 0.0
    for f in grid(int(GRID_STEPS * math.log2(LIMIT / GRID_LO)) + 1):
        if f < 20:
            continue
        phase = 2 * math.pi * f * late
        size = math.hypot(1 + gain * math.cos(phase), gain * math.sin(phase)) / 2
        worst = max(worst, abs(20 * math.log10(max(size, 1e-6))))
    return worst


@dataclass(frozen=True)
class Alignment:
    """**The speakers' alignment, on its own** (ADR-0188): whether it plays,
    when it was checked, the delay on each speaker (ms; the nearer one's)
    and the level (dB; the louder one's cut), how much further the right is
    than the left (cm; None: not timed), what the check found of left and
    right ("right"; "unsure": not told apart; None: not checked) and how
    much louder the right was than the left (dB; None: not read)."""
    on: bool = True
    date: str = ""
    delay: tuple[float, float] = (0.0, 0.0)
    level: tuple[float, float] = (0.0, 0.0)
    distance_cm: float | None = None
    sides: str | None = None
    right_db: float | None = None

    @property
    def plays(self) -> bool:
        """Something to delay or turn down."""
        return _aligned(self.delay) or _matched(self.level)

    def as_dict(self) -> dict:
        return {"on": self.on, "date": self.date, "delay": [round(d, 4) for d in self.delay],
                "level": [round(g, 2) for g in self.level], "distance_cm": self.distance_cm, "sides": self.sides,
                "right_db": None if self.right_db is None else round(self.right_db, 2)}

    @classmethod
    def from_dict(cls, value) -> Alignment:
        date = value.get("date") or ""
        if not isinstance(date, str):
            raise TypeError
        distance = value.get("distance_cm")
        sides = value.get("sides")
        right = value.get("right_db")
        return cls(bool(value.get("on", False)), date, _delay(value.get("delay")), _level(value.get("level")),
                   None if distance is None else _floats([distance])[0],
                   sides if sides in ("right", "unsure") else None,
                   None if right is None else _floats([right])[0])

    @classmethod
    def of(cls, m: Measurement, on: bool = True) -> Alignment:
        """What a measurement was made with (ADR-0188 C1); the level as read
        only where one was turned down."""
        return cls(on, m.date, m.delay, m.level, m.distance_cm, None,
                   m.level[0] - m.level[1] if m.matched else None)


@dataclass(frozen=True)
class OutputRoom:
    """What one output keeps: on, *Hear it without* (saved, George
    2026-11-04), how far it reaches (saved, the design), its last
    measurement, and the speakers' alignment (ADR-0188)."""
    on: bool = False
    without: bool = False
    measured: Measurement | None = None
    reach: str = FULL
    speakers: Alignment | None = None

    @property
    def aligning(self) -> bool:
        """The alignment switched on (ADR-0188 D1)."""
        return self.speakers is not None and self.speakers.on

    @property
    def stale(self) -> bool:
        """**Room correction no longer fits exactly** (ADR-0188 D2, C4): the
        alignment kept moves the speakers' sum in the bass by more than
        `STALE_DB` against what the room was measured with. Only where
        there are cuts in the bass."""
        m, a = self.measured, self.speakers
        if m is None or a is None or m.nothing_to_cut:
            return False
        return pair_moves_db(m.delay, m.level, a.delay, a.level) > STALE_DB

    def as_dict(self) -> dict:
        return {"on": self.on, "without": self.without, "reach": self.reach,
                "measured": self.measured.as_dict() if self.measured else None,
                "speakers": self.speakers.as_dict() if self.speakers else None}


@dataclass(frozen=True)
class Calibration:
    """**A microphone's calibration** (decision 4 as changed, item 9): the
    90° file from miniDSP, given by the owner - its serial, sensitivity line,
    the gain it was made at, and the points."""
    serial: str
    sens_db: float
    points: tuple[tuple[float, float], ...]
    date: str
    gain_db: float | None = None
    angle: int = 90

    def as_dict(self) -> dict:
        return {"serial": self.serial, "sens_db": self.sens_db, "date": self.date, "gain_db": self.gain_db,
                "angle": self.angle, "points": [[round(f, 3), round(d, 3)] for f, d in self.points]}

    @classmethod
    def from_dict(cls, value) -> Calibration:
        serial = value["serial"]
        if not isinstance(serial, str) or not SERIAL.fullmatch(serial):
            raise TypeError
        points = tuple(_floats(p, 2) for p in value["points"])
        if len(points) < 2:
            raise TypeError
        gain = value.get("gain_db")
        return cls(serial, float(value["sens_db"]), points, str(value.get("date", "")),
                   None if gain is None else float(gain), int(value.get("angle", 90)))

    @property
    def full(self) -> bool:
        return self.points[-1][0] >= FULL_FROM

    def db_at(self, f: float) -> float:
        """The file's correction at `f`, interpolated on a log axis; held
        at its ends."""
        pts = self.points
        if f <= pts[0][0]:
            return pts[0][1]
        if f >= pts[-1][0]:
            return pts[-1][1]
        lo, hi = 0, len(pts) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if pts[mid][0] <= f:
                lo = mid
            else:
                hi = mid
        (f0, d0), (f1, d1) = pts[lo], pts[hi]
        t = (math.log(f) - math.log(f0)) / (math.log(f1) - math.log(f0))
        return d0 + t * (d1 - d0)


#: A UMIK-1's serial as the files name it (7001234; its label prints
#: 700-1234).
SERIAL = re.compile(r"\d{7}")


def shown_serial(serial: str) -> str:
    """As the label prints it: 707-1234."""
    return f"{serial[:3]}-{serial[3:]}" if len(serial) == 7 else serial


_SENS = re.compile(r"Sens\s*Factor\s*=\s*([-+]?\d*\.?\d+)\s*dB", re.IGNORECASE)
_SERNO = re.compile(r"SERNO:\s*(\d+)", re.IGNORECASE)
_AGAIN = re.compile(r"AGain\s*=\s*(-?\d+(?:\.\d+)?)\s*dB", re.IGNORECASE)
_POINT = re.compile(r"^\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)[\s,;]+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")
#: **A calibration for the full range** (Phase 30) reaches this far; the
#: files go to 20 kHz. Phase 29 kept them to 2 kHz only, so one given
#: before is asked for again (George, 2026-11-08: *Choose its file again*).
FULL_FROM = 15000.0


def parse_calibration(text: str, date: str, name: str | None = None) -> Calibration:
    """**A calibration file checked as one** (item 9): a sensitivity line
    naming the microphone, then frequency and dB columns, rising, from the
    bass to the treble, all kept; the 90° one (its second line or its name
    says so). Anything else is refused - a web page or an error saved in its
    place included."""
    not_one = "That is not a calibration file from miniDSP."
    if not isinstance(text, str) or len(text) > 400_000:
        raise RoomError(not_one)
    sens = serial = gain = None
    ninety = bool(name and re.search(r"_90deg", name, re.IGNORECASE))
    points: list[tuple[float, float]] = []
    for line in text.splitlines():
        if "90-degree" in line.lower() or "90 degree" in line.lower():
            ninety = True
        if sens is None:
            m = _SENS.search(line)
            if m:
                sens = float(m.group(1))
                found = _SERNO.search(line)
                serial = found.group(1) if found else None
                g = _AGAIN.search(line)
                gain = float(g.group(1)) if g else None
                continue
        m = _POINT.match(line)
        if m:
            f, d = float(m.group(1)), float(m.group(2))
            if not (math.isfinite(f) and math.isfinite(d)) or f <= 0 or abs(d) > 40:
                raise RoomError(not_one)
            if points and f <= points[-1][0]:
                raise RoomError(not_one)
            points.append((f, d))
    if sens is None or abs(sens) > 40:
        raise RoomError(not_one)
    if len(points) < 10 or points[0][0] > 20 or points[-1][0] < FULL_FROM:
        raise RoomError(not_one)
    if serial is None or not SERIAL.fullmatch(serial):
        raise RoomError("That file does not say which microphone it is for.")
    if not ninety:
        raise RoomError("That is the 0° file. Choose the 90° one: its name ends in _90deg.")
    return Calibration(serial, sens, tuple(points), date, gain)


@dataclass(frozen=True)
class Room:
    outputs: dict = field(default_factory=dict)       # card -> OutputRoom
    microphones: dict = field(default_factory=dict)   # serial -> Calibration
    #: The calibration in use: the last given. The UMIK-1 does not say which
    #: unit is plugged in, so it is taken to be that one until another file
    #: is given.
    current: str | None = None

    def calibration(self) -> Calibration | None:
        return self.microphones.get(self.current) if self.current else None

    def output(self, card: str) -> OutputRoom:
        return self.outputs.get(card, OutputRoom())

    def _with(self, card: str, room: OutputRoom) -> Room:
        outputs = dict(self.outputs)
        outputs[card] = room
        return replace(self, outputs=outputs)

    # -- the operations; each returns a new Room --

    def set_on(self, card: str, on: bool) -> Room:
        here = self.output(card)
        if on and (here.measured is None or here.measured.nothing_to_correct):
            raise RoomError("Measure first.")
        return self._with(card, replace(here, on=bool(on)))

    def set_without(self, card: str, without: bool) -> Room:
        """*Hear it without* (George, 2026-11-04): saved; only while room
        correction or the speakers' alignment is on (ADR-0188 C2)."""
        here = self.output(card)
        if not here.on and not here.aligning:
            raise RoomError("Only while room correction or the speakers' alignment is on.")
        return self._with(card, replace(here, without=bool(without)))

    def set_speakers(self, card: str, on: bool) -> Room:
        """**The speakers' alignment on or off** (ADR-0188 D1); *Hear it
        without* goes with the last of the two switched off."""
        here = self.output(card)
        if here.speakers is None:
            raise RoomError("Check the speakers first.")
        here = replace(here, speakers=replace(here.speakers, on=bool(on)))
        if not here.on and not here.aligning:
            here = replace(here, without=False)
        return self._with(card, here)

    def keep_speakers(self, card: str, alignment: Alignment) -> Room:
        """*Keep* after the check on its own (ADR-0188 D1): the alignment
        replaces the last and plays; room correction stays as measured."""
        return self._with(card, replace(self.output(card), speakers=replace(alignment, on=True)))

    def set_reach(self, card: str, reach: str) -> Room:
        """**How far it reaches** (ADR-0177): saved, heard at once; only
        while on (the design: inert while off), and the full range only from
        a measurement made that far."""
        here = self.output(card)
        if reach not in REACHES:
            raise RoomError("It reaches the bass or the full range.")
        if not here.on:
            raise RoomError("Only while room correction is on.")
        if reach == FULL and here.measured.range != FULL:
            raise RoomError("This measurement covers the bass only. Measure again to reach the full range.")
        return self._with(card, replace(here, reach=reach))

    def keep(self, card: str, measurement: Measurement, alignment: Alignment | None = None) -> Room:
        """*Keep it*: the new measurement replaces the old one, and the
        correction is switched on, compared from the start again, reaching as
        far as it was made (George, 2026-11-07: a new one starts at the full
        range). Its check is kept as the speakers' alignment, switched on
        (ADR-0188 C1): the sweeps were made with it."""
        return self._with(card, OutputRoom(on=not measurement.nothing_to_correct, without=False,
                                           measured=measurement, reach=measurement.range,
                                           speakers=replace(alignment or Alignment.of(measurement), on=True)))

    def with_calibration(self, cal: Calibration) -> Room:
        microphones = dict(self.microphones)
        microphones[cal.serial] = cal
        return replace(self, microphones=microphones, current=cal.serial)

    # -- what the stage plays --

    def stage(self, card: str) -> eq.RoomPlay | None:
        """What the stage plays on `card` (`equaliser.room_stage`'s
        argument): None when room correction is off or never measured and
        the speakers' alignment is off - every slot idle; else the cuts and
        the broad corrections, the broad ones at 0 dB under *Bass* and all
        at 0 dB while *Hear it without* is set, with every filter as
        measured for the headroom (ADR-0177 items 6-7); and the alignment's
        delay and level while it is on (ADR-0188 C2), whatever room
        correction does, none *without*."""
        here = self.output(card)
        room = here.on and here.measured is not None
        if not room and not (here.aligning and here.speakers.plays):
            return None

        def at(filters, play: bool):
            return tuple((f, g if play else 0.0, q) for f, g, q in filters)
        m = here.measured if room else None
        cuts = tuple(at(m.cuts(c), not here.without) if m else () for c in CHANNELS)
        above = tuple(at(m.above(c), not here.without and here.reach == FULL) if m else () for c in CHANNELS)
        a = here.speakers if (here.aligning and not here.without) else None
        return eq.RoomPlay(cuts, above, self.lift(card), a.delay if a else (0.0, 0.0),
                           a.level if a else (0.0, 0.0))

    def lift(self, card: str) -> tuple | None:
        """Room correction's filters on `card` as measured, for the headroom
        (ADR-0177 item 7: the same whatever plays); None when off."""
        here = self.output(card)
        if not here.on or here.measured is None:
            return None
        return tuple(here.measured.cuts(c) + here.measured.above(c) for c in CHANNELS)

    def in_path(self, card: str) -> bool:
        """Whether room correction needs the stage on `card`: on, *Without*
        included (the stage stays in the path with the cuts at 0 dB); or the
        speakers' alignment on with something to delay or turn down
        (ADR-0188 C2)."""
        here = self.output(card)
        return (here.on and here.measured is not None) or (here.aligning and here.speakers.plays)

    # -- stored as settings --

    def to_settings(self) -> dict:
        return {"outputs": {k: v.as_dict() for k, v in sorted(self.outputs.items())},
                "microphones": {k: v.as_dict() for k, v in sorted(self.microphones.items())},
                "current": self.current}

    @classmethod
    def from_settings(cls, value) -> Room:
        """Whatever is stored, read leniently: a bad entry is dropped, not
        fatal, as the equaliser's are."""
        value = value if isinstance(value, dict) else {}

        def table(name: str) -> dict:
            got = value.get(name)
            return got if isinstance(got, dict) else {}
        outputs = {}
        for k, item in table("outputs").items():
            try:
                measured = None
                if item.get("measured"):
                    try:
                        measured = Measurement.from_dict(item["measured"])
                    except (KeyError, TypeError, ValueError, AttributeError):
                        measured = None
                on = bool(item.get("on", False)) and measured is not None and not measured.nothing_to_correct
                reach = item.get("reach", FULL)
                if reach not in REACHES or measured is None or measured.range != FULL:
                    reach = BASS if (measured is not None and measured.range != FULL) else FULL
                speakers = None
                if isinstance(item.get("speakers"), dict):
                    try:
                        speakers = Alignment.from_dict(item["speakers"])
                    except (KeyError, TypeError, ValueError, AttributeError):
                        speakers = None
                elif "speakers" not in item and measured is not None and (measured.aligned or measured.matched):
                    # ADR-0188 C1: a measurement kept from before brings its
                    # delay and level across, switched as room correction
                    # was - nothing heard changes.
                    speakers = Alignment.of(measured, on=on)
                aligning = speakers is not None and speakers.on
                outputs[str(k)] = OutputRoom(on, (on or aligning) and bool(item.get("without", False)), measured,
                                             reach, speakers)
            except AttributeError:
                continue
        microphones = {}
        for k, item in table("microphones").items():
            try:
                cal = Calibration.from_dict(item)
            except (KeyError, TypeError, ValueError, AttributeError):
                continue
            if cal.serial == k:
                microphones[k] = cal
        current = value.get("current")
        return cls(outputs, microphones, current if current in microphones else None)


def shown(filters) -> list[dict]:
    """A list of corrections as the screens show them: the frequency to
    the hertz, the gain to a tenth."""
    return [{"freq": round(f), "gain": round(g, 1)} for f, g, _ in filters]


#: The rate the corrections are designed at (`room_dsp.FS`).
DESIGN_FS = 48000


@functools.lru_cache(maxsize=16)
def _filters_db(filters: tuple, n: int) -> tuple[float, ...]:
    """**What `filters` (freq, gain, q) do together** at the first `n` grid
    points, in dB, as designed (ADR-0186 C1)."""
    return tuple(sum(eq.band_db(f0, g, f, DESIGN_FS, q) for f0, g, q in filters) for f in grid(n))


def chart(measurement: Measurement | None, expected: bool | None = None) -> dict | None:
    """**What the chart draws** (the design's §2), for each speaker, on the
    whole grid the measurement has (to 20 kHz, or to 500 Hz for one kept
    before Phase 30): before, each position, the target, after - measured,
    or expected when the check was skipped - with everything and with the
    bass's cuts alone (`after_bass`, for *Bass*), and the corrections.
    **What the shading draws** (ADR-0186 D2): before with the corrections
    kept (`corrected`; `corrected_bass` with the cuts alone) - exact, the
    filters being the same on every position."""
    if measurement is None:
        return None
    first = next(iter(measurement.speakers.values()), None)
    n = len(first.before) if first else 0
    out = {"freqs": grid(n), "limit": int(LIMIT), "range": measurement.range, "speakers": {}}
    for k, s in measurement.speakers.items():
        cuts = _filters_db(tuple(s.cuts), len(s.before))
        broad = _filters_db(tuple(measurement.above(k)), len(s.before))
        out["speakers"][k] = {
            "before": _round(s.before), "target": _round(s.target), "after": _round(s.after),
            "after_bass": _round(s.after_bass or s.after), "positions": [_round(p) for p in s.positions],
            "corrected": _round(tuple(b + c + a for b, c, a in zip(s.before, cuts, broad))),
            "corrected_bass": _round(tuple(b + c for b, c in zip(s.before, cuts))),
            "cuts": shown(s.cuts), "above": shown(measurement.above(k)),
            "peaks_down": round(s.peaks_down()), "within": s.within, "room_within": s.room_within,
            "ringing": _rings(s.ringing),
        }
    out["dips"] = dips_shown(measurement.dips)
    out["after_kind"] = "measured" if (measurement.checked if expected is None else not expected) else "expected"
    return out
