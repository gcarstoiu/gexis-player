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


class StartGuard:
    def __init__(self, hold_s: float = HOLD_S) -> None:
        self._hold_s = hold_s
        self._handed: dict[str, tuple[float, int]] = {}

    def handed(self, renderer_id: str, value: int, now: float) -> None:
        """`renderer_id` was just handed `value` as its starting level."""
        self._handed[renderer_id] = (now + self._hold_s, value)

    def holding(self, renderer_id: str, value: int, now: float) -> int | None:
        """The level to hand again when this report must not be followed;
        None to follow it."""
        held = self._handed.get(renderer_id)
        if held is None:
            return None
        until, level = held
        if now >= until:
            del self._handed[renderer_id]
            return None
        return level if value > level else None
