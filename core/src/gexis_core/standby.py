# SPDX-License-Identifier: GPL-3.0-or-later
"""**Display standby** (ADR-0135): the panel's screen off, the player still
playing.

Off is the HDMI output off, in the kiosk's own labwc session - the core runs
as root, the session as the kiosk's user - and on is the output back with the
turn the kiosk gave it at start, which re-enabling an output does not keep on
every compositor. **On is almost instant** (George, 2026-10-20: powering the
display down instead, with `wlopm`, took about 3 s to come back - "too
much"). Measured on the 10.1" (2026-10-11): the backlight goes dark,
the screen shows its own "No signal" box for about 10 s some 30 s in, then
stays dark; a touch still reaches the panel's page there. **Not on a screen
whose touch is mapped to its output** (`<touch mapToOutput>`, ADR-0109 - the
bars): with the output off its taps land nowhere in the compositor
(ShelvesPi, 2026-10-20). So while the screen is off, the core also listens to
the touchscreens itself, in the kernel (`TouchWatch`), and any finger wakes
it.

**A DSI panel's backlight instead** (ADR-0158 D4, George 2026-10-23:
*"Agreed"*): the player can set it (`/sys/class/backlight`), so standby
turns the backlight off and leaves the output on, with the black cover drawn
- the picture is back as fast as the backlight, and the touch keeps reaching
the compositor. An HDMI screen has no backlight the player can reach.

`Standby` holds the state and is told what wakes it; it does not decide when
to sleep. While it is on, the panel also draws black over everything, so a
screen whose output could not be switched still goes dark.
"""
from __future__ import annotations

import asyncio
import datetime
import logging
import os
import pwd
import struct
import time
from pathlib import Path
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

SCREEN_ENV = Path("/etc/gexis/screen.env")
KIOSK_USER = "pi"
WAYLAND_DISPLAY = "wayland-0"
DEFAULT_CONNECTOR = "HDMI-A-1"
TIMEOUT_S = 10.0
#: The kernel's input devices; BTN_TOUCH, which a touchscreen reports.
INPUT_SYS = Path("/sys/class/input")
#: ADR-0158 D4: the backlights the kernel exposes; a DSI panel's is there.
BACKLIGHTS = Path("/sys/class/backlight")
#: `bl_power`'s values: FB_BLANK_UNBLANK and FB_BLANK_POWERDOWN.
BL_ON, BL_OFF = "0", "4"
EV_KEY, BTN_TOUCH = 1, 330
#: struct input_event on a 64-bit kernel: two longs of time, type, code, value.
EVENT = struct.Struct("qqHHi")


def screen_env(path: Path = SCREEN_ENV) -> dict[str, str]:
    """What the core wrote for the kiosk (ADR-0109); empty when unreadable."""
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return {}
    pairs = (line.split("=", 1) for line in lines if "=" in line and not line.lstrip().startswith("#"))
    return {k.strip(): v.strip() for k, v in pairs}


def seen_connector() -> str:
    """The port a screen is connected to now, for a player with no screen
    chosen - whose screen.env names none - else HDMI-A-1. Not always the
    first port (ADR-0109; George, 2026-10-12)."""
    from . import screen_detect
    try:
        seen = screen_detect.seen()
    except OSError:
        return DEFAULT_CONNECTOR
    return seen.connector if seen.connected and seen.connector else DEFAULT_CONNECTOR


def backlight(connector: str | None, root: Path | None = None) -> Path | None:
    """**The screen's backlight, if the player can set it** (ADR-0158): on a
    DSI connector, the panel's - the only backlight a Pi 4 has with a DSI
    panel on it (bedroompi, 2026-10-23: `10-0045`, the Touch Display's
    controller). None on HDMI, or when there is none."""
    if not (connector or "").startswith("DSI-"):
        return None
    try:
        found = sorted(d for d in (root or BACKLIGHTS).iterdir() if (d / "bl_power").exists())
    except OSError:
        return None
    return found[0] if found else None


def backlight_on(device: Path) -> bool | None:
    """Whether the backlight is lit; None when it cannot be read."""
    try:
        return (device / "bl_power").read_text().strip() == BL_ON
    except OSError:
        return None


def set_backlight(device: Path, on: bool) -> bool:
    """The backlight on or off. False, and logged, when it could not be."""
    try:
        (device / "bl_power").write_text(BL_ON if on else BL_OFF)
    except OSError as exc:
        logger.warning("standby: could not turn the backlight %s: %s", "on" if on else "off", exc)
        return False
    return True


def screen_backlight() -> Path | None:
    """The backlight of the screen in use, if the player can set it."""
    return backlight(screen_env().get("GEXIS_SCREEN_CONNECTOR") or seen_connector())


def set_brightness(percent, device: Path | None = None) -> bool:
    """**Screen brightness** (ADR-0158 D5, George 2026-10-23: *"Agreed"*):
    the backlight at `percent` of its maximum, never fully dark - standby
    is what turns it off, and waking comes back to this. False when there
    is no backlight to set, or it refused."""
    device = device if device is not None else screen_backlight()
    if device is None or percent is None:
        return False
    try:
        top = int((device / "max_brightness").read_text().strip())
        level = max(1, round(top * min(100, max(10, int(percent))) / 100))
        (device / "brightness").write_text(str(level))
    except (OSError, ValueError) as exc:
        logger.warning("brightness: could not set the backlight to %s%%: %s", percent, exc)
        return False
    logger.info("brightness: the backlight at %s%% (%d)", percent, level)
    return True


def _session(uid: int) -> list[str]:
    """Run as the kiosk's user, in its Wayland session."""
    return ["runuser", "-u", KIOSK_USER, "--", "env", f"WAYLAND_DISPLAY={WAYLAND_DISPLAY}",
            f"XDG_RUNTIME_DIR=/run/user/{uid}"]


def output_command(on: bool, env: dict[str, str], uid: int, fallback: str = DEFAULT_CONNECTOR) -> list[str]:
    """`wlr-randr` for the kiosk's output, run as the kiosk's user in its
    session. Waking re-applies the turn the kiosk set. The output is the one
    the core applied the screen on (screen.env); `fallback` when it names
    none."""
    connector = env.get("GEXIS_SCREEN_CONNECTOR") or fallback
    args = _session(uid) + ["wlr-randr", "--output", connector]
    if not on:
        return args + ["--off"]
    args.append("--on")
    turn = env.get("GEXIS_SCREEN_TRANSFORM")
    if turn and turn != "normal":
        args += ["--transform", turn]
    return args


def carries_sound(connector: str) -> bool:
    """Whether the sound plays to `connector`'s HDMI port now."""
    from . import alsa, outputs
    card = outputs.CARD_FOR_CONNECTOR.get(connector)
    return card is not None and alsa.card() == card


async def switch_output(on: bool) -> bool:
    """The screen's output on or off. False, and logged, when it could not be."""
    try:
        uid = pwd.getpwnam(KIOSK_USER).pw_uid
    except KeyError:
        logger.warning("standby: no %s user; the screen stays as it is", KIOSK_USER)
        return False
    env = screen_env()
    connector = env.get("GEXIS_SCREEN_CONNECTOR") or seen_connector()
    if (light := backlight(connector)) is not None:
        # ADR-0158 D4: the output stays on; the backlight goes.
        if set_backlight(light, on):
            logger.info("standby: %s's backlight %s", connector, "on" if on else "off")
            return True
    if not on and carries_sound(connector):
        # **Black, and the sound goes on** (ADR-0147 as amended; George,
        # 2026-10-13: a TV through a receiver went silent with the screen -
        # HDMI's sound rides on its picture). The panel's black cover is the
        # standby; the output stays on.
        logger.info("standby: %s carries the sound; the picture goes black, the output stays on", connector)
        return True
    # The ports are looked at only when screen.env names none.
    args = output_command(on, env, uid, connector)
    try:
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        _, err = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_S)
    except (OSError, asyncio.TimeoutError) as exc:
        logger.warning("standby: could not turn the screen %s: %s", "on" if on else "off", exc)
        return False
    if proc.returncode != 0:
        logger.warning("standby: wlr-randr refused to turn the screen %s: %s",
                       "on" if on else "off", (err or b"").decode(errors="replace").strip())
        return False
    return True


def lit(enabled: bool | None) -> bool | None:
    """Whether the screen shows a picture, from `wlr-randr --json`'s
    `enabled`; None when it could not be read."""
    return enabled


async def read_output() -> bool | None:
    """**The screen's real state**, from the kiosk's session - which outlives
    a core restart, as a standby does (ShelvesPi, 2026-10-20: a standby asked
    for at 22:50 outlived the update's restart at 03:45, and the new core
    called the screen on). None when it cannot be read."""
    import json
    try:
        uid = pwd.getpwnam(KIOSK_USER).pw_uid
    except KeyError:
        return None
    connector = screen_env().get("GEXIS_SCREEN_CONNECTOR") or seen_connector()
    if (light := backlight(connector)) is not None:
        # ADR-0158 D4: the output is on all along; the backlight says.
        return backlight_on(light)

    async def run(args: list[str]) -> str | None:
        try:
            proc = await asyncio.create_subprocess_exec(
                *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            out, _ = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_S)
        except (OSError, asyncio.TimeoutError):
            return None
        return out.decode(errors="replace") if proc.returncode == 0 else None

    enabled = None
    text = await run(_session(uid) + ["wlr-randr", "--json"])
    try:
        for output in json.loads(text) if text else []:
            if output.get("name") == connector:
                enabled = bool(output.get("enabled"))
    except (ValueError, TypeError, AttributeError):
        enabled = None
    return lit(enabled)


def touchscreens(root: Path = INPUT_SYS) -> list[Path]:
    """The kernel's touchscreens: event devices that report BTN_TOUCH. The
    `key` capability is hex words, the last the lowest bits."""
    found = []
    for dev in sorted(root.glob("event*")):
        try:
            words = (dev / "device" / "capabilities" / "key").read_text().split()
        except OSError:
            continue
        bits = 0
        for word in words:
            bits = (bits << 64) | int(word, 16)
        if bits >> BTN_TOUCH & 1:
            found.append(Path("/dev/input") / dev.name)
    return found


def finger_downs(data: bytes) -> int:
    """How many fingers came down in a read of `struct input_event`s."""
    n = 0
    for i in range(0, len(data) - EVENT.size + 1, EVENT.size):
        _, _, typ, code, value = EVENT.unpack_from(data, i)
        if typ == EV_KEY and code == BTN_TOUCH and value == 1:
            n += 1
    return n


class TouchWatch:
    """**A finger on a dark screen, seen in the kernel** (ADR-0135 as amended
    2026-10-20). Reading an event device does not take it from the
    compositor; it reads while the screen is off and stops when it wakes."""

    def __init__(self, on_touch: Callable[[], None], devices: Callable[[], list[Path]] = touchscreens) -> None:
        self._on_touch = on_touch
        self._devices = devices
        self._open: list[int] = []

    def start(self) -> None:
        if self._open:
            return
        loop = asyncio.get_running_loop()
        for path in self._devices():
            try:
                fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            except OSError as exc:
                logger.warning("standby: cannot read %s for a touch: %s", path, exc)
                continue
            loop.add_reader(fd, self._read, fd)
            self._open.append(fd)
        if self._open:
            logger.info("standby: listening for a touch on %d touchscreen(s)", len(self._open))

    def _read(self, fd: int) -> None:
        try:
            data = os.read(fd, EVENT.size * 64)
        except BlockingIOError:
            return
        except OSError:
            self._close(fd)
            return
        if finger_downs(data):
            self._on_touch()

    def _close(self, fd: int) -> None:
        try:
            asyncio.get_running_loop().remove_reader(fd)
        except RuntimeError:
            pass
        try:
            os.close(fd)
        except OSError:
            pass
        if fd in self._open:
            self._open.remove(fd)

    def stop(self) -> None:
        for fd in list(self._open):
            self._close(fd)


class Standby:
    """Whether the screen is in standby, and the two moves between.

    `switch(on)` turns the output; `publish(off, reason)` tells the panel and
    the phones. Asleep twice or awake twice is nothing: every wake source
    calls `wake` without asking first."""

    def __init__(self, switch: Callable[[bool], Awaitable[bool]] = switch_output,
                 publish: Callable[[bool, str | None], None] | None = None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._switch = switch
        self._publish = publish or (lambda off, reason: None)
        #: While off, the core listens to the touchscreens itself.
        self.touch_watch = TouchWatch(lambda: asyncio.ensure_future(self.wake("touch")))
        self.off = False
        self.reason: str | None = None
        #: Whether the output was last switched on, as far as this process
        #: knows: None until it has switched it. **The output's state lives in
        #: the kiosk's session, which outlives a core restart** (review,
        #: 2026-10-12): `off` starts False, so a restart during standby (a
        #: plugin upload, a crash) left a dark panel nothing could wake.
        self._output_on: bool | None = None
        self._lock = asyncio.Lock()
        #: When the screen was last used: a touch, music playing, a wake.
        #: The schedule counts *Back to standby after* from here.
        self._clock = clock
        self.last_use = clock()

    def used(self) -> None:
        self.last_use = self._clock()

    @property
    def may_be_dark(self) -> bool:
        """In standby, or the output not switched on since the core started:
        what a touch checks before waking."""
        return self.off or self._output_on is not True

    async def sleep(self, reason: str) -> None:
        async with self._lock:
            if self.off:
                return
            self.off, self.reason = True, reason
            # Published before the output goes: the panel's black cover is
            # drawn while there is still a picture to replace.
            self._publish(True, reason)
            await self._switch(False)
            self._output_on = False
            self.touch_watch.start()
            logger.info("standby: screen off (%s)", reason)

    async def reconcile(self, shown: bool | None, inside_standby_time: bool) -> None:
        """At start: the screen as it really is (`read_output`). Dark inside a
        standby time, it is the schedule's standby, said as such - the phone
        offers to wake it, a touch wakes it, and the schedule wakes it when
        the time ends. Dark outside one, nothing would wake it: it is woken.
        Lit, it is known to be on."""
        if shown is True:
            self._output_on = True
            return
        if shown is None:
            return
        if inside_standby_time:
            async with self._lock:
                self.off, self.reason, self._output_on = True, "schedule", False
                self._publish(True, "schedule")
                self.touch_watch.start()
            logger.info("standby: the screen was dark at start, inside a standby time; kept so")
        else:
            logger.info("standby: the screen was dark at start, outside a standby time; waking it")
            await self.wake("start")

    async def wake(self, reason: str) -> None:
        async with self._lock:
            if not self.off:
                # Not in standby here - but the output may still be off from
                # before a restart. Switched on once, and again until it takes.
                if self._output_on is not True and await self._switch(True):
                    self._output_on = True
                    logger.info("standby: screen on (%s; its state was unknown)", reason)
                return
            self.touch_watch.stop()
            self._output_on = True if await self._switch(True) else None
            self.off, self.reason = False, None
            self.used()
            self._publish(False, None)
            logger.info("standby: screen on (%s)", reason)


DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def _minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def in_standby_time(now: datetime.datetime, intervals: list[dict]) -> bool:
    """Whether `now` is inside any of the owner's standby times. An interval
    belongs to the days it starts on, so 23:00-07:00 on Friday covers early
    Saturday too."""
    minute = now.hour * 60 + now.minute
    today = DAYS[now.weekday()]
    yesterday = DAYS[(now.weekday() - 1) % 7]
    for interval in intervals or []:
        try:
            start, end = _minutes(interval["from"]), _minutes(interval["until"])
            days = interval.get("days") or []
        except (KeyError, ValueError, AttributeError, TypeError):
            continue
        if start < end:
            if today in days and start <= minute < end:
                return True
        elif (today in days and minute >= start) or (yesterday in days and minute < end):
            return True
    return False


class Schedule:
    """**ADR-0135: scheduled standby.** Inside a standby time the screen goes
    off once nothing is playing and nobody has used it for *Back to standby
    after*; outside them, a screen the schedule put off wakes. A screen the
    owner put off stays off until something wakes it.

    `value(key)` reads a setting; `playing()` says whether music plays;
    `blocked()` whether the screen is asking something that must be seen."""

    def __init__(self, standby: Standby, value, playing, *, clock=time.monotonic,
                 now=datetime.datetime.now, blocked=lambda: False) -> None:
        self._standby = standby
        self._value = value
        self._playing = playing
        self._clock = clock
        self._now = now
        self._blocked = blocked

    def inside_now(self) -> bool:
        """Inside one of the owner's standby times now, with the schedule on."""
        on = self._value("standby_schedule") is True and self._value("headless") is not True
        return on and in_standby_time(self._now(), self._value("standby_times") or [])

    async def tick(self) -> None:
        on = self._value("standby_schedule") is True and self._value("headless") is not True
        # **Not over Keep this screen?** (Finding 125 #17, 2026-10-14): its
        # countdown starts when it is drawn, some seconds after the core
        # starts, and the schedule put the black cover over it at *Back to
        # standby after* from the start; the change went back unseen. A
        # question on the screen is use, as music is.
        if self._playing() or self._blocked():
            self._standby.used()
        inside = on and in_standby_time(self._now(), self._value("standby_times") or [])
        if not inside:
            if self._standby.off and self._standby.reason == "schedule":
                await self._standby.wake("schedule")
            return
        if self._standby.off or self._playing():
            return
        try:
            after_s = max(1, min(30, int(self._value("standby_wake") or 2))) * 60
        except (TypeError, ValueError):
            after_s = 120
        if self._clock() - self._standby.last_use >= after_s:
            await self._standby.sleep("schedule")

    async def run(self, every: float = 15.0) -> None:
        while True:
            await asyncio.sleep(every)
            try:
                await self.tick()
            except Exception:  # noqa: BLE001 - a schedule must not die quietly
                logger.exception("standby: the schedule's tick failed")
