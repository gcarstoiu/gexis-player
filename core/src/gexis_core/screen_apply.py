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

**A DSI model's overlay goes in `config.txt`** (ADR-0158): in a block of
our own at its end, read by the firmware at the next boot as `cmdline.txt`
is by the kernel. A panel the firmware finds by itself, an HDMI screen or
no screen leaves the block empty, and nothing else in the file is touched.

The state of the last change is `/var/lib/gexis/screen.json`:
`current`, `previous`, and whether the current one is still `pending` a
Keep. Nothing here restarts anything; the caller does.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from . import screens

SCREEN_ENV = Path("/etc/gexis/screen.env")
STATE = Path("/var/lib/gexis/screen.json")
CMDLINE = Path("/boot/firmware/cmdline.txt")
CONFIG = Path("/boot/firmware/config.txt")
#: ADR-0158: the lines between these two are ours, under `[all]`.
CONFIG_BEGIN = "# gexis screen (ADR-0158): written by the player - choose the screen in Settings"
CONFIG_END = "# end gexis screen"
#: The DSI connector a DSI model is applied on before its panel is seen: a
#: panel whose overlay is not written yet has no connector at all. The Pi 4
#: has one DSI connector on the board.
DSI_CONNECTOR = "DSI-1"
#: **The connector when none is known** - nothing connected, or a state
#: written before the connector was kept, which every one of those players
#: ran on. Otherwise the screen is applied on the connector it was seen on
#: (ADR-0109; George, 2026-10-12: a screen on the second HDMI port was given
#: the first one's mode, touch and standby).
CONNECTOR = "HDMI-A-1"
#: Every `video=` this writes is for an HDMI connector, and a screen moved
#: from one to the other must not leave its mode behind on the first.
HDMI_VIDEO = "video=HDMI-A-"

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
    connector: str = CONNECTOR    # the HDMI port the screen is on
    #: **The port was chosen under *Screen port*** (ADR-0147 D1): it holds
    #: while something is connected to it, over a known panel on the other
    #: port. False is the port the screen was found on, which follows it.
    chosen: bool = False

    def to_json(self) -> dict:
        doc = {"screen": self.screen_id, "rotation": self.rotation, "connector": self.connector}
        return {**doc, "chosen": True} if self.chosen else doc

    @classmethod
    def of(cls, data: dict) -> "Applied":
        """From screen.json. A state without a connector was written when
        every screen was applied on HDMI-A-1, so it reads as that."""
        return cls(data["screen"], int(data.get("rotation", 0)), data.get("connector") or CONNECTOR,
                   bool(data.get("chosen")))


def connector_now(seen=None, state: Path | None = None) -> str:
    """**The connector to apply a screen on**: the one a screen is connected
    to now; with none connected (switched off at the boot, or not there) the
    one applied last, rather than moving the panel's settings to a port
    nothing was seen on; and HDMI-A-1 when there is neither."""
    if seen is None:
        from . import screen_detect
        try:
            seen = screen_detect.seen()
        except OSError:
            seen = None
    if seen is not None and seen.connected and seen.connector:
        return seen.connector
    current = read_state(state or STATE).get("current")
    return (current.get("connector") if isinstance(current, dict) else None) or CONNECTOR


def connector_for(screen: screens.Screen, seen=None, state: Path | None = None, ports=None) -> str:
    """**The connector to apply `screen` on** (ADR-0158). A DSI model goes on
    the DSI connector: the one a panel is seen on, else `DSI_CONNECTOR` - a
    panel whose overlay is not written yet has no connector at all, and is
    seen only after the restart. Any other screen where `connector_now`
    finds the screen, which is a DSI panel when one is connected (D3)."""
    if screen.interface == "dsi":
        if ports is None:
            from . import screen_detect
            try:
                ports = screen_detect.ports()
            except OSError:
                ports = []
        return next((p.connector for p in ports if p.dsi and p.connected), DSI_CONNECTOR)
    return connector_now(seen, state)


def applied_on(screen_id: str, rotation: int, connector: str, state: Path | None = None) -> Applied:
    """**A screen chosen in Settings, on `connector`, keeping the port's
    choice** (Finding 125 #7, 2026-10-14): a rotation or another model on a
    port chosen under *Screen port* (ADR-0147 D1) is still that port's
    choice. Built without the mark, the next start found the panel on the
    other port and moved the TV's settings onto it."""
    current = read_state(state or STATE).get("current")
    chosen = isinstance(current, dict) and bool(current.get("chosen")) and current.get("connector") == connector
    return Applied(screen_id, rotation, connector, chosen=chosen)


def env_for(screen: screens.Screen, rotation: int, connector: str = CONNECTOR, off: tuple = ()) -> str:
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
        # ADR-0147 D5 as amended: a touch panel on another port while a
        # screen without touch is in use (a TV) - its output is turned off by
        # the kiosk, backlight and all.
        f"GEXIS_OUTPUTS_OFF={' '.join(off)}",
        # **The mode a TV is run at, set by the compositor too** (George,
        # 2026-10-13: the TV "extremely zoomed in"): the kernel's `video=`
        # held 1920 x 1080 for the boot, then labwc took the receiver's
        # preferred 1280 x 720 while the page was scaled for 1080p.
        f"GEXIS_SCREEN_MODE={screen.video_mode if screens.OTHER.match(screen.id) and screen.video_mode else ''}",
    ]
    return "\n".join(lines) + "\n"


def panels_off(screen_id: str, connector: str, ports=None) -> list[str]:
    """The ports with a known touch panel on them, other than the screen's,
    while the screen has no touch of its own (ADR-0147 D5 as amended)."""
    from . import screen_detect
    if screen_detect.has_touch(screen_id):
        return []
    try:
        ports = screen_detect.ports() if ports is None else ports
    except OSError:
        return []
    return [p.connector for p in ports
            if p.connected and p.connector != connector and screen_detect.suggest(p) is not None]


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


def with_video(cmdline: str, video: str | None) -> str:
    """cmdline.txt with the HDMI `video=` replaced, added or removed - on
    either connector, so a screen that moved port takes its mode with it.
    One line, other entries untouched."""
    words = [w for w in cmdline.split() if not w.startswith(HDMI_VIDEO)]
    if video:
        words.append(video)
    return " ".join(words) + "\n"


def with_overlays(config: str, overlays: tuple[str, ...]) -> str:
    """config.txt with our block replaced, added or removed (ADR-0158).
    The block starts with `[all]`, so a section filter above it (`[pi5]`)
    does not swallow it; every other line stays as it was."""
    lines = config.splitlines()
    out, inside = [], False
    for line in lines:
        if line.strip() == CONFIG_BEGIN:
            inside = True
            # The `[all]` the block opened with goes with it.
            if out and out[-1].strip() == "[all]":
                out.pop()
            continue
        if inside:
            inside = line.strip() != CONFIG_END
            continue
        out.append(line)
    while out and not out[-1].strip():
        out.pop()
    if overlays:
        out += ["", "[all]", CONFIG_BEGIN, *(f"dtoverlay={o}" for o in overlays), CONFIG_END]
    return "\n".join(out) + "\n"


def overlays_in(config: str) -> tuple[str, ...]:
    """The overlays our block holds now."""
    found, inside = [], False
    for line in config.splitlines():
        if line.strip() == CONFIG_BEGIN:
            inside = True
        elif line.strip() == CONFIG_END:
            inside = False
        elif inside and line.startswith("dtoverlay="):
            found.append(line.split("=", 1)[1].strip())
    return tuple(found)


def picture(env: Path = SCREEN_ENV, cmdline: Path = CMDLINE, config: Path = CONFIG) -> tuple:
    """**What the screen shows**, as far as a choice can change it: what the
    boot sets (the forced mode, and a DSI panel's overlay, ADR-0158), the
    scale and the rotation. No screen.env is the screen's own mode at scale
    1, unrotated. The mode names its connector, so the same bar moved to the
    other port is a different picture, and asks Keep; a screen without a
    forced mode looks the same on either. The first part is what only a
    restart changes."""
    try:
        fields = dict(l.split("=", 1) for l in env.read_text().splitlines() if "=" in l and not l.startswith("#"))
    except OSError:
        fields = {}
    try:
        words = cmdline.read_text().split()
    except OSError:
        words = []
    video = next((w for w in words if w.startswith(HDMI_VIDEO)), None)
    try:
        overlays = overlays_in(config.read_text())
    except OSError:
        overlays = ()
    return ((video, overlays), float(fields.get("GEXIS_SCREEN_SCALE", 1)),
            fields.get("GEXIS_SCREEN_TRANSFORM", "normal"))


def picture_of(applied: Applied) -> tuple:
    """`picture()` as it will be once `applied` is written."""
    screen = screens.by_id(applied.screen_id)
    if screen is None:
        raise ValueError(f"no such screen {applied.screen_id!r}")
    fields = dict(l.split("=", 1) for l in env_for(screen, applied.rotation, applied.connector).splitlines()
                  if "=" in l and not l.startswith("#"))
    return ((video_for(screen, applied.connector, applied.rotation), screen.overlays),
            float(fields["GEXIS_SCREEN_SCALE"]), fields["GEXIS_SCREEN_TRANSFORM"])


def would_ask(applied: Applied, *, env: Path = SCREEN_ENV, cmdline: Path = CMDLINE, config: Path = CONFIG) -> bool:
    """Whether choosing `applied` will ask *Keep this screen?*."""
    return picture_of(applied) != picture(env, cmdline, config)


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


def write_files(applied: Applied | None, *, env: Path = SCREEN_ENV, cmdline: Path = CMDLINE,
                config: Path = CONFIG) -> bool:
    """screen.env, cmdline.txt and config.txt's block for `applied` (None: no
    screen chosen - the screen's own preferred mode, no scale). True when a
    boot file changed, which only a restart makes effective."""
    screen = screens.by_id(applied.screen_id) if applied else None
    if applied and screen is None:
        raise ValueError(f"no such screen {applied.screen_id!r}")
    env.parent.mkdir(parents=True, exist_ok=True)
    if screen is None:
        env.unlink(missing_ok=True)
    else:
        tmp = env.with_name(env.name + ".tmp")
        tmp.write_text(env_for(screen, applied.rotation, applied.connector,
                               tuple(panels_off(applied.screen_id, applied.connector))))
        tmp.replace(env)
    changed = False
    try:
        before = config.read_text()
    except OSError:
        before = None
    if before is not None:
        after = with_overlays(before, screen.overlays if screen else ())
        if overlays_in(after) != overlays_in(before):
            _replace_durably(config, after)
            changed = True
    try:
        before = cmdline.read_text()
    except OSError:
        return changed
    after = with_video(before.strip(), video_for(screen, applied.connector, applied.rotation) if screen else None)
    if after.strip() == before.strip():
        return changed
    _replace_durably(cmdline, after)
    return True


def _replace_durably(path: Path, text: str) -> None:
    """**cmdline.txt is never rewritten in place** (review, 2026-10-12).
    Truncate-then-write on the FAT boot partition, on a player switched off
    at the wall (ADR-0019), can leave it empty: no `root=`, and a Pi that
    does not boot until someone edits the card by hand. So: written beside
    it, on the card before the rename, then renamed over it, and the rename
    itself on the card. On vfat a rename is not atomic the way it is on ext4,
    which is why both syncs are here and not only the rename."""
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w") as out:
            out.write(text)
            out.flush()
            os.fsync(out.fileno())
        tmp.replace(path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    try:
        folder = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(folder)
        finally:
            os.close(folder)
    except OSError:
        pass  # the file is in place; the kernel's own writeback finishes the rest


def choose(applied: Applied, *, state: Path = STATE, env: Path = SCREEN_ENV, cmdline: Path = CMDLINE,
           config: Path = CONFIG, now: float | None = None, after_setup: bool = False) -> bool:
    """Make `applied` the screen, pending a Keep; remember the one before for
    going back. The caller restarts the device.

    **Kept without asking when the picture stays as it is** (ADR-0109 as
    amended 2026-10-02): the question guards against a screen left dark or
    unreadable, which a change of nothing but the model's name cannot do.
    True when it waits for a Keep. **After setup** the question waits longer:
    setup ends on the phone, not beside the panel."""
    data = read_state(state)
    previous = data.get("current") if not data.get("pending") else data.get("previous")
    asks = would_ask(applied, env=env, cmdline=cmdline, config=config)
    write_files(applied, env=env, cmdline=cmdline, config=config)
    write_state({"current": applied.to_json(), "previous": previous, "pending": asks,
                 "after_setup": after_setup, "since": now if now is not None else time.time()}, state)
    return asks


def refresh(*, state: Path = STATE, env: Path = SCREEN_ENV, cmdline: Path = CMDLINE, config: Path = CONFIG) -> bool:
    """**The kept screen's files as this version writes them** (2026-10-04:
    a bar's `video=` now carries the panel's orientation, and a bar set up
    before has it without). Rewritten only when they differ, and not while a
    choice waits for Keep. True when cmdline.txt changed - for the next
    start; nothing is restarted."""
    data = read_state(state)
    current = data.get("current")
    if not current or data.get("pending") or screens.by_id(current["screen"]) is None:
        return False
    return write_files(Applied.of(current), env=env, cmdline=cmdline, config=config)


def confirm_provisional(label: str, *, state: Path = STATE) -> bool:
    """**Setup's Screen step keeps the screen setup applied** (ADR-0109 as
    amended 2026-10-07). Choosing the very screen applied provisionally
    changes no setting, so nothing reached `choose` and the flag stayed: the
    bar, found 2026-10-12, still provisional long after setup - and with it
    the setup network's fixed password (decision 5). True when it cleared
    the flag; a different screen goes through `choose`, which clears it."""
    data = read_state(state)
    current = data.get("current")
    if not data.get("provisional") or not isinstance(current, dict):
        return False
    model = screens.by_id(current.get("screen") or "")
    if model is None or model.label != label:
        return False
    data.pop("provisional", None)
    write_state(data, state)
    return True


def keep(*, state: Path = STATE) -> None:
    data = read_state(state)
    if data.get("pending"):
        data["pending"] = False
        write_state(data, state)


def revert(*, state: Path = STATE, env: Path = SCREEN_ENV, cmdline: Path = CMDLINE, config: Path = CONFIG) -> None:
    """Back to the screen before, or to none (decision 3: at first setup,
    *no screen chosen* - the screen's own mode)."""
    data = read_state(state)
    previous = data.get("previous")
    applied = Applied.of(previous) if previous else None
    write_files(applied, env=env, cmdline=cmdline, config=config)
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


def named(label: str | None, path: Path | None = None) -> screens.Screen | None:
    """**The screen Settings' *Attached screen* names** - the one in use when
    it is called that, else the one the list calls that. ADR-0109; George,
    2026-10-12: changing *Screen rotation* on a screen laid out from its own
    mode logged "not a screen gexis knows" and turned nothing, because
    `Other screen/W × H` is in no list. And a portrait panel used sideways
    (`other-WxH-turned`) is called what the landscape one of its size is: the
    stored id keeps its turn when it is rotated."""
    if not label:
        return None
    current = read_state(path or STATE).get("current")
    in_use = screens.by_id(current["screen"]) if current else None
    if in_use is not None and in_use.label == label:
        return in_use
    return screens.by_label(label)


def parse_rotation(value: str | None) -> int:
    return ROTATIONS.get(value or "0°", 0)

