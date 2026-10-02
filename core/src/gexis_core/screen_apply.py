# SPDX-License-Identifier: GPL-3.0-or-later
"""Applying a screen (ADR-0109): the chosen model and rotation become
`/etc/gexis/screen.env`, which the kiosk reads at start, and - when the model
needs a mode the screen does not offer by itself - a `video=` entry on the
kernel's command line. Either way the device restarts, and the panel asks
*Keep this screen?* (decision 5); with no answer it goes back.

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


def video_for(screen: screens.Screen, connector: str = CONNECTOR) -> str | None:
    """The kernel's `video=` for a model that needs its own mode."""
    if screen.interface != "hdmi" or not screen.video_mode:
        return None
    return f"video={connector}:{screen.video_mode}"


def with_video(cmdline: str, video: str | None, connector: str = CONNECTOR) -> str:
    """cmdline.txt with this connector's `video=` replaced, added or removed.
    One line, other entries untouched."""
    words = [w for w in cmdline.split() if not w.startswith(f"video={connector}:")]
    if video:
        words.append(video)
    return " ".join(words) + "\n"


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
    return bool(data.get("current")) and not data.get("pending")


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
    after = with_video(before.strip(), video_for(screen) if screen else None)
    if after.strip() == before.strip():
        return False
    cmdline.write_text(after)
    return True


def choose(applied: Applied, *, state: Path = STATE, env: Path = SCREEN_ENV, cmdline: Path = CMDLINE,
           now: float | None = None) -> None:
    """Make `applied` the screen, pending a Keep; remember the one before for
    going back. The caller restarts the device."""
    data = read_state(state)
    previous = data.get("current") if not data.get("pending") else data.get("previous")
    write_files(applied, env=env, cmdline=cmdline)
    write_state({"current": applied.to_json(), "previous": previous, "pending": True,
                 "since": now if now is not None else time.time()}, state)


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

