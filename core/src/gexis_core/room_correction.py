# SPDX-License-Identifier: GPL-3.0-or-later
"""**Room correction as the player keeps it** (ADR-0175, Phase 29): for each
output whether it is on, whether *Hear it without* is set, and the last
measurement with the cuts made from it; and each microphone's calibration.

Nothing here touches a device or needs numpy: the state is read from the
settings store (`KEY`, so it is in backups and cleared by a factory reset,
item 10) leniently, as the equaliser's is, and turned into what the stage
plays (`stage`) and what the screens draw (`summary`, `chart`).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, replace

KEY = "_room_correction"

#: The speakers, as the screens and the store name them.
CHANNELS = ("L", "R")
#: **Both speakers together** (George, 2026-11-05): swept at each position
#: in the run and in the check, as heard; shown, never corrected - the cuts
#: are each speaker's.
BOTH = "both"
SWEPT = CHANNELS + (BOTH,)
#: Where a run measures (George, 2026-11-05: three, over the five first
#: drawn - the head and 40 cm to either side). A measurement keeps its own
#: number, so one made at five still reads as five.
POSITIONS = 3

#: The grid the curves are kept on (`room_dsp.GRID`: 1/24 octave from
#: 15 Hz), and how many of its points the chart draws (up to 300 Hz).
GRID_LO = 15.0
GRID_STEPS = 24
CHART_HI = 300.0


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


def _round(values, digits: int = 1) -> list[float]:
    return [round(float(v), digits) for v in values]


@dataclass(frozen=True)
class Speaker:
    """One speaker's part of a measurement: its cuts, and its curves on the
    grid, relative to the target's level."""
    cuts: tuple[tuple[float, float, float], ...] = ()
    before: tuple[float, ...] = ()
    target: tuple[float, ...] = ()
    after: tuple[float, ...] = ()
    positions: tuple[tuple[float, ...], ...] = ()

    def as_dict(self) -> dict:
        return {"cuts": [{"freq": round(f, 1), "gain": round(g, 1), "q": round(q, 2)} for f, g, q in self.cuts],
                "before": _round(self.before), "target": _round(self.target), "after": _round(self.after),
                "positions": [_round(p) for p in self.positions]}

    @classmethod
    def from_dict(cls, value) -> Speaker:
        cuts = []
        for c in value.get("cuts") or []:
            f, g, q = _floats([c["freq"], c["gain"], c["q"]])
            if f > 0 and q > 0 and g <= 0:
                cuts.append((f, g, q))
        before = _floats(value.get("before") or [])
        n = len(before)
        target = _floats(value.get("target") or [], n)
        # None for both speakers when the check was skipped.
        after = _floats(value.get("after") or [], n if value.get("after") else None)
        positions = tuple(_floats(p, n) for p in value.get("positions") or [])
        return cls(tuple(cuts[:8]), before, target, after, positions)

    def peaks_down(self) -> float:
        """*Peaks down by up to N dB*: the most taken off below the limit."""
        top = 0.0
        for f, b, a in zip(grid(len(self.before)), self.before, self.after):
            if f <= 250:
                top = max(top, b - a)
        return top


@dataclass(frozen=True)
class Measurement:
    """The last measurement of an output (item 10): when, at how many
    positions, whether its check was done (*Not checked* when skipped), and
    each speaker's part."""
    date: str
    checked: bool
    speakers: dict = field(default_factory=dict)     # "L"/"R"/"both" -> Speaker
    positions: int = POSITIONS
    #: Positions the check found further from the target, as (n, dB).
    worse: tuple[tuple[int, float], ...] = ()

    def as_dict(self) -> dict:
        return {"date": self.date, "checked": self.checked, "positions": self.positions,
                "worse": [list(w) for w in self.worse],
                "speakers": {k: v.as_dict() for k, v in self.speakers.items()}}

    @classmethod
    def from_dict(cls, value) -> Measurement:
        date = value["date"]
        if not isinstance(date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            raise TypeError
        speakers = {k: Speaker.from_dict(value["speakers"][k]) for k in CHANNELS}
        if isinstance(value["speakers"].get(BOTH), dict):
            speakers[BOTH] = Speaker.from_dict(value["speakers"][BOTH])
        worse = tuple((int(n), float(db)) for n, db in value.get("worse") or [])
        return cls(date, bool(value.get("checked", False)), speakers,
                   int(value.get("positions", POSITIONS)), worse)

    def cuts(self, channel: str) -> tuple[tuple[float, float, float], ...]:
        s = self.speakers.get(channel)
        return s.cuts if s else ()

    @property
    def nothing_to_cut(self) -> bool:
        return not any(self.cuts(c) for c in CHANNELS)

    def peaks_down(self) -> float:
        return max((self.speakers[c].peaks_down() for c in CHANNELS if c in self.speakers), default=0.0)


@dataclass(frozen=True)
class OutputRoom:
    """What one output keeps: on, *Hear it without* (saved, George
    2026-11-04), and its last measurement."""
    on: bool = False
    without: bool = False
    measured: Measurement | None = None

    def as_dict(self) -> dict:
        return {"on": self.on, "without": self.without,
                "measured": self.measured.as_dict() if self.measured else None}


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
#: The points kept: the bass and well above it; the file goes to 20 kHz.
KEEP_UP_TO = 2000.0


def parse_calibration(text: str, date: str, name: str | None = None) -> Calibration:
    """**A calibration file checked as one** (item 9): a sensitivity line
    naming the microphone, then frequency and dB columns, rising, covering
    the bass; the 90° one (its second line or its name says so). Anything
    else is refused - a web page or an error saved in its place included."""
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
            if f <= KEEP_UP_TO:
                points.append((f, d))
    if sens is None or abs(sens) > 40:
        raise RoomError(not_one)
    if len(points) < 10 or points[0][0] > 20 or points[-1][0] < 500:
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
        if on and (here.measured is None or here.measured.nothing_to_cut):
            raise RoomError("Measure first.")
        return self._with(card, replace(here, on=bool(on)))

    def set_without(self, card: str, without: bool) -> Room:
        """*Hear it without* (George, 2026-11-04): saved; only while on
        (the design: inert while off)."""
        here = self.output(card)
        if not here.on:
            raise RoomError("Only while room correction is on.")
        return self._with(card, replace(here, without=bool(without)))

    def keep(self, card: str, measurement: Measurement) -> Room:
        """*Keep it*: the new measurement replaces the old one, and the
        correction is switched on, compared from the start again."""
        return self._with(card, OutputRoom(on=not measurement.nothing_to_cut, without=False,
                                           measured=measurement))

    def with_calibration(self, cal: Calibration) -> Room:
        microphones = dict(self.microphones)
        microphones[cal.serial] = cal
        return replace(self, microphones=microphones, current=cal.serial)

    # -- what the stage plays --

    def stage(self, card: str):
        """The cuts for the stage on `card` (`equaliser.room_stage`'s
        argument): None when off or never measured - every slot idle, or
        the cuts at 0 dB while *Hear it without* is set."""
        here = self.output(card)
        if not here.on or here.measured is None:
            return None
        left, right = here.measured.cuts("L"), here.measured.cuts("R")
        if here.without:
            left = tuple((f, 0.0, q) for f, _, q in left)
            right = tuple((f, 0.0, q) for f, _, q in right)
        return left, right

    def in_path(self, card: str) -> bool:
        """Whether room correction needs the stage on `card`: on, *Without*
        included (the stage stays in the path with the cuts at 0 dB)."""
        here = self.output(card)
        return here.on and here.measured is not None

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
                on = bool(item.get("on", False)) and measured is not None and not measured.nothing_to_cut
                outputs[str(k)] = OutputRoom(on, on and bool(item.get("without", False)), measured)
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


def chart(measurement: Measurement | None, expected: bool | None = None) -> dict | None:
    """**What the chart draws** (the design's §5), for each speaker, up to
    300 Hz: before, each position, the target, after - measured, or
    expected when the check was skipped - and the cuts."""
    if measurement is None:
        return None
    first = next(iter(measurement.speakers.values()), None)
    n = len(first.before) if first else 0
    points = grid(n)
    keep = sum(1 for f in points if f <= CHART_HI)
    out = {"freqs": points[:keep], "limit": 250, "speakers": {}}
    for k, s in measurement.speakers.items():
        out["speakers"][k] = {
            "before": _round(s.before[:keep]), "target": _round(s.target[:keep]),
            "after": _round(s.after[:keep]), "positions": [_round(p[:keep]) for p in s.positions],
            "cuts": [{"freq": round(f), "gain": round(g, 1)} for f, g, _ in s.cuts],
            "peaks_down": round(s.peaks_down()),
        }
    out["after_kind"] = "measured" if (measurement.checked if expected is None else not expected) else "expected"
    return out
