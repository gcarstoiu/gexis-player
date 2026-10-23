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

#: **ADR-0158 D2: a DSI panel recognised, before anyone picks its model.**
#: The Touch Display v1's overlay drives 23 listed models from 4.3" to 8",
#: all 800 x 480, and none can be told from another: no EDID, the same
#: driver. A model picked from the list is shown by its own name; this is
#: what setup suggests until then.
TOUCH_DISPLAY_CLASS = "dsi-touch-display-class"

#: ADR-0109 decision 1: the models George owns, marked tested. George,
#: 2026-10-01: *"All of them are waveshare with hdmi inputs"* - the 10.1" (B)
#: that sofa-pi runs, and the 13.3" and two bars that step 6 tries on the
#: hardware before a release offers them.
TESTED: frozenset[str] = frozenset({
    "waveshare-10.1-hdmi-b",
    "waveshare-13.3-hdmi-h",
    "waveshare-7.9-hdmi",
    "waveshare-11.9-hdmi",
    # George, 2026-10-20 (sofapi): "Record it as tested" - the non-touch 7".
    "hmtech-7-hdmi",
    # And the non-touch 10.1", the same evening (OUR_PRESETS below).
    "hmtech-10.1-hdmi-monitor",
    # ADR-0158: George's DSI panel on bedroompi, 2026-10-23 (*"Yes
    # hoysond"*), and the class it is recognised as - which is what was
    # tested, since nothing the Pi reads tells the class's makers apart.
    "hosyond-7-dsi",
    TOUCH_DISPLAY_CLASS,
})

#: **Screens George owns that the vendored list lacks** (`display_presets.json`
#: is pi_screen_setup's, kept as it is). Merged into it when the list loads.
#: The HMTECH 10.1" there is the touch model; George's, on sofapi 2026-10-20,
#: has none ("No touch display"), and a touch entry would ask *Keep this
#: screen?* on a screen nobody can tap.
OUR_PRESETS: dict[str, dict] = {
    "hmtech-10.1-hdmi-monitor": {
        "name": "HMTECH 10.1\" HDMI Monitor (1024x600)",
        "type": "hdmi",
        "description": "IPS display, non-touch",
        "native_resolution": "1024x600",
        "recommended_rotation": 0,
        "notes": "No touch. EDID reads Dell TLD1280. Tested on sofapi, 2026-10-20.",
    },
    TOUCH_DISPLAY_CLASS: {
        "name": "Raspberry Pi Touch Display or compatible (DSI, 800x480)",
        "type": "dsi",
        "description": "DSI touch screen on the Touch Display's own driver",
        "native_resolution": "800x480",
        "config": {"dtoverlay": "vc4-kms-dsi-7inch"},
        "recommended_rotation": 0,
        "notes": "Recognised by its driver: the original Touch Display and the panels built to answer as one. "
                 "Tested as the Hosyond 7\" on bedroompi, 2026-10-23.",
    },
}

#: The aspect ratio from which a screen is a bar (lib/family.svelte.js: the
#: same boundary).
BAR_FROM = 2.4

#: Not screens: a mode that asks the screen, and one that wants timings typed.
NOT_MODELS = frozenset({"auto", "custom"})

#: Below this a screen is square or round, which no family lays out. George,
#: 2026-10-01: *"Leave them out"* (11 models, 480x480 to 1080x1080).
SQUARE_BELOW = 1.3

#: HDMI screens, and **DSI screens since ADR-0158** (George, 2026-10-23:
#: *"For all that we have in the dsi list that we deferred until now"*).
#: DPI screens stay out: they take the GPIO header, where the DACs sit.
INTERFACES = frozenset({"hdmi", "dsi"})

#: **The overlays the firmware loads by itself** (`display_auto_detect=1`,
#: Raspberry Pi OS's own `config.txt`): a panel answering as the Touch
#: Display v1 is brought up with nothing written (ADR-0158, measured on
#: bedroompi). Every other DSI model's overlay is written (`screen_apply`).
FIRMWARE_FINDS = frozenset({"vc4-kms-dsi-7inch"})

#: **Overlays Raspberry Pi OS does not carry** (ADR-0158 D1; bedroompi's
#: `/boot/firmware/overlays`, 2026-10-23): Waveshare's own, downloaded from
#: its site. A model needing one is left out - written, it would leave the
#: panel dark until the restart went back.
NOT_SHIPPED = frozenset({"waveshare_35DSI"})

#: **A case is not a screen** (George, 2026-10-03: *"In general the box and
#: non box i would say are the same"* - his 10.1" (B) came in Waveshare's case,
#: and the list offered it twice). A preset "with Case" is listed as its panel:
#: dropped where the bare panel is listed too, renamed where it is not, and a
#: choice saved under the old name still finds it.
CASE = re.compile(r"\s+with Case\b", re.IGNORECASE)

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
    #: ADR-0158: the `dtoverlay=` lines a DSI model needs in config.txt -
    #: none for an HDMI screen or one the firmware finds by itself.
    overlays: tuple[str, ...] = ()

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


def _overlays(preset: dict) -> tuple[str, ...]:
    """The `dtoverlay=` values a DSI preset needs written, in the list's
    order (`dtoverlay`, then `dtoverlay_2`); none for one the firmware finds."""
    if preset.get("type") != "dsi":
        return ()
    config = preset.get("config") or {}
    found = tuple(str(config[k]) for k in sorted(config) if k.startswith("dtoverlay") and config[k])
    return () if set(found) <= FIRMWARE_FINDS else found


@lru_cache(maxsize=1)
def all_screens(path: Path = PRESETS) -> tuple[Screen, ...]:
    raw = {**json.loads(path.read_text())["presets"], **OUR_PRESETS}
    out = []
    for key, preset in raw.items():
        if not isinstance(preset, dict) or "name" not in preset or key in NOT_MODELS:
            continue
        panel = key.removesuffix("-case")
        if panel != key and panel in raw:
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
        if preset.get("type", "hdmi") not in INTERFACES:
            continue
        if preset.get("emit_dsi_overlay") is False:
            # ADR-0158 D1: run only with `vc4-kms-v3d` removed, which the
            # compositor needs (Waveshare 4.3" rev 1, PiTFT50 v1.0, DFRobot 5").
            continue
        if any(o.split(",", 1)[0] in NOT_SHIPPED for o in _overlays(preset)):
            continue
        maker, model = _maker_and_model(CASE.sub("", preset["name"]))
        out.append(Screen(
            id=key,
            maker=maker,
            model=model,
            interface=preset.get("type", "hdmi"),
            width=used[0],
            height=used[1],
            rotation=rotation,
            tested=panel in TESTED,
            video_mode=preset.get("video_mode"),
            notes=preset.get("notes"),
            overlays=_overlays(preset),
        ))
    return tuple(sorted(out, key=lambda s: (s.maker.lower(), s.model.lower())))


#: A screen known only by its own preferred mode (ADR-0109, amended
#: 2026-10-04): `other-<W>x<H>`, its size as used - landscape - and
#: `-turned` for a portrait panel used sideways.
OTHER = re.compile(r"^other-(\d+)x(\d+)(-turned|-capped)?$")

#: **The most a screen in no list is run at** (ADR-0147 D4, George
#: 2026-10-13: a TV as the screen, *"1920x1080 at most"*). A TV reports its
#: 4K mode as preferred; the 1920x1080 skin packs fit 1080p, and the Pi 4's
#: browser stays light there. The TV scales it to its full screen.
CAP = (1920, 1080)


def other(native_width: int, native_height: int, capped: bool = False) -> Screen:
    """**A screen that is in no list, laid out from its own mode.** Used
    landscape: a panel taller than it is wide is turned (90°, as the listed
    bars are), so a bar arrives as a bar. Its family follows from the shape.
    **Capped** (`other-1920x1080-capped`): a larger screen run at that size,
    which the kernel is told by a `video=` line, as a bar's mode is."""
    portrait = native_height > native_width
    width, height = (native_height, native_width) if portrait else (native_width, native_height)
    suffix = "-turned" if portrait else ("-capped" if capped else "")
    return Screen(id=f"other-{width}x{height}{suffix}", maker="Other screen", model=f"{width} × {height}",
                  interface="hdmi", width=width, height=height, rotation=90 if portrait else 0,
                  tested=False, video_mode=f"{width}x{height}" if capped and not portrait else None, notes=None)


def fitted(native_width: int, native_height: int) -> Screen:
    """`other()`, held to `CAP` when the screen is a 16:9 one larger than it
    - a TV or monitor at 1440p or 4K. Any other shape larger than that keeps
    its own mode: a size the screen does not offer would be calculated, and
    may not show at all."""
    width, height = CAP
    larger = native_width > width or native_height > height
    if larger and native_width > native_height and abs(native_width * height - native_height * width) <= native_height * 16:
        return other(width, height, capped=True)
    return other(native_width, native_height)


def by_id(screen_id: str) -> Screen | None:
    if m := OTHER.match(screen_id or ""):
        width, height = int(m.group(1)), int(m.group(2))
        if m.group(3) == "-turned":
            return other(height, width)
        return other(width, height, capped=m.group(3) == "-capped")
    found = next((s for s in all_screens() if s.id == screen_id), None)
    if found is None and screen_id.endswith("-case"):  # merged into its panel
        found = next((s for s in all_screens() if s.id == screen_id.removesuffix("-case")), None)
    return found


#: What `other()` is called in Settings: `Other screen/W × H`.
OTHER_LABEL = re.compile(r"^Other screen/(\d+) × (\d+)$")


def by_label(label: str) -> Screen | None:
    """The screen Settings names `label`. **An "Other screen" too** (ADR-0109;
    George, 2026-10-12: *Screen rotation* on one turned nothing - its name was
    in no list). Its name does not say whether the panel is used turned;
    `screen_apply.named` asks the screen in use first, and this is the
    landscape one."""
    if m := OTHER_LABEL.match(label or ""):
        return other(int(m.group(1)), int(m.group(2)))
    label = CASE.sub("", label)
    return next((s for s in all_screens() if s.label == label), None)
