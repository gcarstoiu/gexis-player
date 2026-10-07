# SPDX-License-Identifier: GPL-3.0-or-later
"""Applying a screen (ADR-0109): the chosen model and rotation become
`/etc/gexis/screen.env`, which the kiosk reads at start, and - when the model
needs a mode the screen does not offer by itself - a `video=` entry on the
kernel's command line. Either way the device restarts, and - when that
changes the picture - the panel asks *Keep this screen?* (decision 5, as
amended 2026-10-02); with no answer it goes back.

**Under full KMS** (this image) the firmware's `hdmi_timings`/`hdmi_mode` from
the presets do not apply (Finding 100); the kernel's `video=` and the
compositor's rotation do. A preset's `video_mode` becomes `video=`; a model
without one is driven at the mode its own EDID prefers.

The state of the last change is `/var/lib/gexis/screen.json`:
`current`, `previous`, and whether the current one is still `pending` a
Keep. Nothing here restarts anything; the caller does.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

from . import screens

SCREEN_ENV = Path("/etc/gexis/screen.env")
STATE = Path("/var/lib/gexis/screen.json")
CMDLINE = Path("/boot/firmware/cmdline.txt")
CONNECTOR = "HDMI-A-1"

#: The logical size each family lays out at (ADR-0109): Standard is 1280
#: wide, a bar 400 tall.
STANDARD_WIDTH = 1280
BAR_HEIGHT = 400

#: The two rotations offered (decision 6), as degrees.
ROTATIONS = {"0°": 0, "180°": 180}

#: wlr-randr's names for a rotation.
TRANSFORMS = {0: "normal", 90: "90", 180: "180", 270: "270"}


@dataclass(frozen=True)
class Applied:
    screen_id: str
    rotation: int                 # the user's: 0 or 180

    def to_json(self) -> dict:
        return {"screen": self.screen_id, "rotation": self.rotation}


def env_for(screen: screens.Screen, rotation: int, connector: str = CONNECTOR) -> str:
    """screen.env: what the kiosk needs to put the page on this screen."""
    turn = (screen.rotation + rotation) % 360
    if screen.family == "bar":
        scale = screen.height / BAR_HEIGHT
    else:
        scale = screen.width / STANDARD_WIDTH
    lines = [
        "# Written by gexis-core when a screen is chosen (ADR-0109). Do not edit:",
        "# choose the screen in Settings -> Display -> Attached screen.",
        f"GEXIS_SCREEN_ID={screen.id}",
        f"GEXIS_SCREEN_FAMILY={screen.family}",
        f"GEXIS_SCREEN_WIDTH={screen.width}",
        f"GEXIS_SCREEN_HEIGHT={screen.height}",
        f"GEXIS_SCREEN_CONNECTOR={connector}",
        f"GEXIS_SCREEN_TRANSFORM={TRANSFORMS[turn]}",
        f"GEXIS_SCREEN_SCALE={scale:g}",
    ]
    return "\n".join(lines) + "\n"


#: **The panel's orientation, for the kernel** (George, 2026-10-04, "A": the
#: boot logo on the 11.9" bar was "zoomed in a lot" - drawn landscape into a
#: portrait panel). Told through `video=`, the kernel sets the connector's
#: panel orientation; plymouth draws turned by it, and so does the console.
#: The compositor turns the panel itself (`TRANSFORMS`). **To be confirmed
#: on the bar** - and it was (2026-10-04, the 11.9" at 180, a total turn of
#: 270): left_side_up drew plymouth upside down, so 90 and 270 are the other
#: way about; the compositor does not turn it a second time.
PANEL_ORIENTATION = {90: "left_side_up", 180: "upside_down", 270: "right_side_up"}


def video_for(screen: screens.Screen, connector: str = CONNECTOR, rotation: int = 0) -> str | None:
    """The kernel's `video=` for a model that needs its own mode - with the
    panel's orientation when it is used turned."""
    if screen.interface != "hdmi" or not screen.video_mode:
        return None
    orientation = PANEL_ORIENTATION.get((screen.rotation + rotation) % 360)
    # **The resolution alone, so the kernel takes the panel's own mode**
    # (2026-10-04, the 11.9" bar): the presets' `M@60` makes the kernel
    # calculate CVT timings for 60 Hz, which the bar did not display - it
    # stayed dark until the compositor set its EDID mode (57.7 Hz, 59.4 MHz),
    # ~27 s into the boot. Without M or a rate, the kernel picks the EDID's
    # mode of that size, and calculates one only when there is none.
    size = re.match(r"\d+x\d+", screen.video_mode)
    mode = size.group(0) if size else screen.video_mode
    return f"video={connector}:{mode}" + (f",panel_orientation={orientation}" if orientation else "")


def with_video(cmdline: str, video: str | None, connector: str = CONNECTOR) -> str:
    """cmdline.txt with this connector's `video=` replaced, added or removed.
    One line, other entries untouched."""
    words = [w for w in cmdline.split() if not w.startswith(f"video={connector}:")]
    if video:
        words.append(video)
    return " ".join(words) + "\n"


def picture(env: Path = SCREEN_ENV, cmdline: Path = CMDLINE, connector: str = CONNECTOR) -> tuple:
    """**What the screen shows**, as far as a choice can change it: the
    forced mode, the scale and the rotation. No screen.env is the screen's
    own mode at scale 1, unrotated."""
    try:
        fields = dict(l.split("=", 1) for l in env.read_text().splitlines() if "=" in l and not l.startswith("#"))
    except OSError:
        fields = {}
    try:
        words = cmdline.read_text().split()
    except OSError:
        words = []
    video = next((w for w in words if w.startswith(f"video={connector}:")), None)
    return video, float(fields.get("GEXIS_SCREEN_SCALE", 1)), fields.get("GEXIS_SCREEN_TRANSFORM", "normal")


def picture_of(applied: Applied, connector: str = CONNECTOR) -> tuple:
    """`picture()` as it will be once `applied` is written."""
    screen = screens.by_id(applied.screen_id)
    if screen is None:
        raise ValueError(f"no such screen {applied.screen_id!r}")
    fields = dict(l.split("=", 1) for l in env_for(screen, applied.rotation, connector).splitlines()
                  if "=" in l and not l.startswith("#"))
    return video_for(screen, connector, applied.rotation), float(fields["GEXIS_SCREEN_SCALE"]), fields["GEXIS_SCREEN_TRANSFORM"]


def would_ask(applied: Applied, *, env: Path = SCREEN_ENV, cmdline: Path = CMDLINE) -> bool:
    """Whether choosing `applied` will ask *Keep this screen?*."""
    return picture_of(applied) != picture(env, cmdline)


def read_state(path: Path = STATE) -> dict:
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(data: dict, path: Path = STATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1))
    tmp.replace(path)


def confirmed(path: Path = STATE) -> bool:
    """Whether a screen has been kept on the panel (decision 5: until then the
    setup network uses the fixed password)."""
    data = read_state(path)
    # A screen applied during setup (ADR-0109 amended 2026-10-07) is not one
    # anybody has confirmed is readable.
    return bool(data.get("current")) and not data.get("pending") and not data.get("provisional")


def write_files(applied: Applied | None, *, env: Path = SCREEN_ENV, cmdline: Path = CMDLINE) -> bool:
    """screen.env and cmdline.txt for `applied` (None: no screen chosen - the
    screen's own preferred mode, no scale). True when cmdline.txt changed,
    which only a restart makes effective."""
    screen = screens.by_id(applied.screen_id) if applied else None
    if applied and screen is None:
        raise ValueError(f"no such screen {applied.screen_id!r}")
    env.parent.mkdir(parents=True, exist_ok=True)
    if screen is None:
        env.unlink(missing_ok=True)
    else:
        tmp = env.with_name(env.name + ".tmp")
        tmp.write_text(env_for(screen, applied.rotation))
        tmp.replace(env)
    try:
        before = cmdline.read_text()
    except OSError:
        return False
    after = with_video(before.strip(), video_for(screen, rotation=applied.rotation) if screen else None)
    if after.strip() == before.strip():
        return False
    cmdline.write_text(after)
    return True


def choose(applied: Applied, *, state: Path = STATE, env: Path = SCREEN_ENV, cmdline: Path = CMDLINE,
           now: float | None = None, after_setup: bool = False) -> bool:
    """Make `applied` the screen, pending a Keep; remember the one before for
    going back. The caller restarts the device.

    **Kept without asking when the picture stays as it is** (ADR-0109 as
    amended 2026-10-02): the question guards against a screen left dark or
    unreadable, which a change of nothing but the model's name cannot do.
    True when it waits for a Keep. **After setup** the question waits longer:
    setup ends on the phone, not beside the panel."""
    data = read_state(state)
    previous = data.get("current") if not data.get("pending") else data.get("previous")
    asks = would_ask(applied, env=env, cmdline=cmdline)
    write_files(applied, env=env, cmdline=cmdline)
    write_state({"current": applied.to_json(), "previous": previous, "pending": asks,
                 "after_setup": after_setup, "since": now if now is not None else time.time()}, state)
    return asks


def refresh(*, state: Path = STATE, env: Path = SCREEN_ENV, cmdline: Path = CMDLINE) -> bool:
    """**The kept screen's files as this version writes them** (2026-10-04:
    a bar's `video=` now carries the panel's orientation, and a bar set up
    before has it without). Rewritten only when they differ, and not while a
    choice waits for Keep. True when cmdline.txt changed - for the next
    start; nothing is restarted."""
    data = read_state(state)
    current = data.get("current")
    if not current or data.get("pending") or screens.by_id(current["screen"]) is None:
        return False
    return write_files(Applied(current["screen"], int(current.get("rotation", 0))), env=env, cmdline=cmdline)


def keep(*, state: Path = STATE) -> None:
    data = read_state(state)
    if data.get("pending"):
        data["pending"] = False
        write_state(data, state)


def revert(*, state: Path = STATE, env: Path = SCREEN_ENV, cmdline: Path = CMDLINE) -> None:
    """Back to the screen before, or to none (decision 3: at first setup,
    *no screen chosen* - the screen's own mode)."""
    data = read_state(state)
    previous = data.get("previous")
    applied = Applied(previous["screen"], int(previous.get("rotation", 0))) if previous else None
    write_files(applied, env=env, cmdline=cmdline)
    write_state({"current": previous, "previous": None, "pending": False, "reverted": data.get("current")}, state)


def settings_of(path: Path = STATE) -> dict[str, str | None]:
    """What Settings' *Attached screen* and *Screen rotation* say for the
    current screen - after a go-back, the screen before, or none (ADR-0109
    as amended 2026-10-02: Settings no longer names a screen undone)."""
    current = read_state(path).get("current")
    screen = screens.by_id(current["screen"]) if current else None
    turn = int(current.get("rotation", 0)) if current else 0
    return {"screen": screen.label if screen else None,
            "rotation": next(k for k, v in ROTATIONS.items() if v == turn) if screen else None}


def parse_rotation(value: str | None) -> int:
    return ROTATIONS.get(value or "0°", 0)

