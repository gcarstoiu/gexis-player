# SPDX-License-Identifier: GPL-3.0-or-later
"""The screens gexis knows (ADR-0109, Phase 13b): the list Attached screen and
setup's Screen step offer.

**Seeded from foonerd's presets** - `pi_screen_setup`'s `display_presets.json`,
version 1.5.9 at commit 8c0896b3 (2026-03-24), MIT, kept as it came in
`screens_data/` with its licence (THIRD-PARTY.md). Finding 100: 197 entries,
195 of them models (the other two are *Auto Detect* and *Custom HDMI Timings*,
which are not screens); no recognition data.

**What we add:** each model's maker and name apart (the picker groups by
maker), the landscape size it is used at, the layout family that size gives,
and whether George has tested it (ADR-0109 decision 1: every model listed, the
tested ones marked; recognition only ever suggests a tested one).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PRESETS = Path(__file__).with_name("screens_data") / "display_presets.json"

#: ADR-0109 decision 1: the models George owns, marked tested. George,
#: 2026-10-01: *"All of them are waveshare with hdmi inputs"* - the 10.1" (B)
#: that sofa-pi runs, and the 13.3" and two bars that step 6 tries on the
#: hardware before a release offers them.
TESTED: frozenset[str] = frozenset({
    "waveshare-10.1-hdmi-b",
    "waveshare-13.3-hdmi-h",
    "waveshare-7.9-hdmi",
    "waveshare-11.9-hdmi",
})

#: The aspect ratio from which a screen is a bar (lib/family.svelte.js: the
#: same boundary).
BAR_FROM = 2.4

#: Not screens: a mode that asks the screen, and one that wants timings typed.
NOT_MODELS = frozenset({"auto", "custom"})

#: Below this a screen is square or round, which no family lays out. George,
#: 2026-10-01: *"Leave them out"* (11 models, 480x480 to 1080x1080).
SQUARE_BELOW = 1.3

#: The maker as the picker shows it, where the preset's first word is not one.
_MAKER_NAMES = {
    "GeeekPi/52Pi": "GeeekPi",
    "Raspberry": "Raspberry Pi",
    "Custom/Generic": "Generic",
    "Custom": "Generic",
    "4K": "Generic",
    "720p": "Generic",
    "1080p": "Generic",
    "VGA666": "Generic",
}


@dataclass(frozen=True)
class Screen:
    id: str
    maker: str
    model: str
    interface: str           # hdmi, dsi or dpi
    width: int               # as used: landscape
    height: int
    rotation: int            # what the panel needs to be used that way
    tested: bool
    video_mode: str | None   # the preset's cmdline mode, when it gives one
    notes: str | None

    @property
    def family(self) -> str:
        return "bar" if self.width / self.height >= BAR_FROM else "standard"

    @property
    def label(self) -> str:
        """`Maker/Model` - the grouped picker's option (Settings splits at
        the first "/")."""
        return f"{self.maker}/{self.model}"


def _size(text: str | None) -> tuple[int, int] | None:
    m = re.match(r"^\s*(\d+)\s*x\s*(\d+)\s*$", text or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def _maker_and_model(name: str) -> tuple[str, str]:
    first, _, rest = name.partition(" ")
    if first == "Raspberry" and rest.startswith("Pi "):
        rest = rest[3:]
    maker = _MAKER_NAMES.get(first, first)
    return maker, (rest.strip() or name).replace("/", "-")


@lru_cache(maxsize=1)
def all_screens(path: Path = PRESETS) -> tuple[Screen, ...]:
    raw = json.loads(path.read_text())["presets"]
    out = []
    for key, preset in raw.items():
        if not isinstance(preset, dict) or "name" not in preset or key in NOT_MODELS:
            continue
        native = _size(preset.get("native_resolution"))
        if native is None:
            continue
        used = _size(preset.get("rotated_resolution"))
        rotation = int(preset.get("recommended_rotation") or 0)
        if used is None:
            used = (native[1], native[0]) if rotation in (90, 270) else native
        if used[0] < used[1]:
            # ADR-0109 decision 6: 0° is the model's landscape and portrait is
            # not designed - a panel the preset uses upright is turned, and
            # its entry carries the turn. Untested, so it says so when chosen.
            used = (used[1], used[0])
            rotation = (rotation + 90) % 360
        if used[0] / used[1] < SQUARE_BELOW:
            continue
        maker, model = _maker_and_model(preset["name"])
        out.append(Screen(
            id=key,
            maker=maker,
            model=model,
            interface=preset.get("type", "hdmi"),
            width=used[0],
            height=used[1],
            rotation=rotation,
            tested=key in TESTED,
            video_mode=preset.get("video_mode"),
            notes=preset.get("notes"),
        ))
    return tuple(sorted(out, key=lambda s: (s.maker.lower(), s.model.lower())))


def by_id(screen_id: str) -> Screen | None:
    return next((s for s in all_screens() if s.id == screen_id), None)


def by_label(label: str) -> Screen | None:
    return next((s for s in all_screens() if s.label == label), None)
