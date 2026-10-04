# SPDX-License-Identifier: GPL-3.0-or-later
"""**A volume control's scale, as the card declares it** (ADR-0117 decision 1).

The DAC2 HD's scale used to be constants in `volume.py` (ADR-0018: 0-240,
-120 dB, 0.5 dB a step). Every number of it is on the control's own
`amixer contents` lines, so it is read from there, whatever the board:

    numid=1,iface=MIXER,name='DAC Playback Volume'
      ; type=INTEGER,access=rw---R--,values=2,min=0,max=240,step=0
      : values=202,202
      | dBscale-min=-120.00dB,step=0.50dB,mute=1

**A control that gives no dB is not a volume the player can use** (ADR-0117,
George: *"Yes agreed with a"*): without dB the curve cannot be applied, and
treating the raw numbers as linear is the bunched-up slider ADR-0054 removed.
Its output is fixed. `dBscale` (a step) and `dBminmax` (two ends, linear in
dB between) carry what is needed; `dBlinear` and `dBrange` do not, as one
line, and count as none.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Scale:
    raw_min: int
    raw_max: int
    db_min: float      # at raw_min
    db_step: float     # per raw step

    @property
    def top(self) -> int:
        """**The loudest raw value the player writes: 0 dB, never above.**
        Some controls go past it - the Pi's headphone jack to +4 dB, a
        PCM512x's digital volume (the IQaudio DAC+) to +24 dB - and above
        0 dB a full-scale track clips. A control that stops below 0 dB
        tops out at its maximum."""
        zero = self.raw_min + math.floor(-self.db_min / self.db_step + 1e-9)
        return max(self.raw_min, min(self.raw_max, zero))

    def db(self, raw: int) -> float:
        return self.db_min + (raw - self.raw_min) * self.db_step

    def raw(self, db: float) -> int:
        return max(self.raw_min, min(self.top, self.raw_min + round((db - self.db_min) / self.db_step)))


#: The HiFiBerry DAC2 HD's, as ADR-0018 measured it and the card reports it.
#: What the player assumes until an output's own scale is known.
DAC2_HD = Scale(raw_min=0, raw_max=240, db_min=-120.0, db_step=0.5)

_RANGE = re.compile(r"type=INTEGER,[^\n]*?min=(-?\d+),max=(-?\d+)")
_DBSCALE = re.compile(r"dBscale-min=(-?[\d.]+)dB,step=([\d.]+)dB")
_DBMINMAX = re.compile(r"dBminmax-min=(-?[\d.]+)dB,max=(-?[\d.]+)dB")


def parse(block: str) -> Scale | None:
    """One control's lines of `amixer contents` to its scale, or None when
    they give no usable dB."""
    rng = _RANGE.search(block)
    if not rng:
        return None
    lo, hi = int(rng.group(1)), int(rng.group(2))
    if hi <= lo:
        return None
    if m := _DBSCALE.search(block):
        step = float(m.group(2))
        return Scale(lo, hi, float(m.group(1)), step) if step > 0 else None
    if m := _DBMINMAX.search(block):
        db_lo, db_hi = float(m.group(1)), float(m.group(2))
        return Scale(lo, hi, db_lo, (db_hi - db_lo) / (hi - lo)) if db_hi > db_lo else None
    return None


def playback_controls(contents: str) -> list[tuple[str, Scale | None]]:
    """Every `* Playback Volume` integer control in `amixer contents`, in the
    card's order, with its scale or None."""
    out = []
    for block in re.split(r"(?m)^(?=numid=)", contents):
        name = re.match(r"numid=\d+,iface=MIXER,name='([^']+) Playback Volume'", block)
        if name and "type=INTEGER" in block:
            out.append((name.group(1), parse(block)))
    return out
