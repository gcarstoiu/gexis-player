# SPDX-License-Identifier: GPL-3.0-or-later
"""The starting volume, held for a moment after it is handed over.

ADR-0054 §5 (amended 2026-09-28): Spotify starts no louder than `start_max`.
The core lowers the DAC and hands Spotify the level - and on 2026-10-05,
0.9 s later, Spotify reported 100 and the core followed it to full scale
(George: *"it actually didn't respect the 60%"*). A phone taking a Spotify
Connect device sends its own slider's position as it connects; that is the
100, not a hand on the slider.

So for `HOLD_S` after a level is handed, a report **above** it is answered
by handing the level again rather than followed. A lower one is followed,
and after the hold every report is - a person turning it up is heard.
"""
from __future__ import annotations

#: Long enough for the phone's own level to arrive (0.9 s measured), short
#: enough that a person reaching for the slider is not overruled.
HOLD_S = 3.0
#: **A renderer not yet told its level** (2026-10-07, George on guestpi:
#: *"Volume did start at 100% which shouldn't have happened"*): Spotify's
#: session became active 3.7 s after it took the device, so the handoff ran
#: out of time before Spotify was told anything. Until it is told - at most
#: this long - its reports above the starting volume are answered, not
#: followed; the hold of `HOLD_S` starts once it has been told.
UNTOLD_MAX_S = 15.0


class StartGuard:
    """Levels in **percent** of the renderer's own scale, so the guard can
    start the moment the DAC comes down - before the renderer has said what
    its scale is."""

    def __init__(self, hold_s: float = HOLD_S, untold_max_s: float = UNTOLD_MAX_S) -> None:
        self._hold_s = hold_s
        self._untold_max_s = untold_max_s
        #: renderer -> [hold until, percent, told, since]
        self._handed: dict[str, list] = {}

    def handed(self, renderer_id: str, percent: float, now: float, told: bool = True) -> None:
        """`renderer_id` starts at `percent`; `told` once it has been sent it."""
        self._handed[renderer_id] = [now + self._hold_s, percent, told, now]

    def told(self, renderer_id: str, now: float) -> None:
        """The renderer has just been sent its starting level: hold from now."""
        held = self._handed.get(renderer_id)
        if held is not None:
            held[0], held[2] = now + self._hold_s, True

    def held(self, renderer_id: str, now: float) -> float | None:
        """The starting level, in percent, while a report above it must be
        answered rather than followed; None to follow every report."""
        held = self._handed.get(renderer_id)
        if held is None:
            return None
        until, percent, told, since = held
        if not told and now - since < self._untold_max_s:
            return percent
        if now >= until:
            del self._handed[renderer_id]
            return None
        return percent
