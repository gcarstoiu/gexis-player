# SPDX-License-Identifier: GPL-3.0-or-later
"""**Display standby** (ADR-0135): the panel's screen off, the player still
playing.

Off is the HDMI output off, in the kiosk's own labwc session - the core runs
as root, the session as the kiosk's user - and on is the output back with the
turn the kiosk gave it at start, which re-enabling an output does not keep on
every compositor. Measured on the 10.1" (2026-10-11): the backlight goes dark,
the screen shows its own "No signal" box for about 10 s some 30 s in, then
stays dark; a touch still reaches the panel's page, which is how a touch
wakes it.

`Standby` holds the state and is told what wakes it; it does not decide when
to sleep. While it is on, the panel also draws black over everything, so a
screen whose output could not be switched still goes dark.
"""
from __future__ import annotations

import asyncio
import datetime
import logging
import pwd
import time
from pathlib import Path
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

SCREEN_ENV = Path("/etc/gexis/screen.env")
KIOSK_USER = "pi"
WAYLAND_DISPLAY = "wayland-0"
DEFAULT_CONNECTOR = "HDMI-A-1"
TIMEOUT_S = 10.0


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


def output_command(on: bool, env: dict[str, str], uid: int, fallback: str = DEFAULT_CONNECTOR) -> list[str]:
    """`wlr-randr` for the kiosk's output, run as the kiosk's user in its
    session. Waking re-applies the turn the kiosk set. The output is the one
    the core applied the screen on (screen.env); `fallback` when it names
    none."""
    connector = env.get("GEXIS_SCREEN_CONNECTOR") or fallback
    args = ["runuser", "-u", KIOSK_USER, "--", "env", f"WAYLAND_DISPLAY={WAYLAND_DISPLAY}",
            f"XDG_RUNTIME_DIR=/run/user/{uid}", "wlr-randr", "--output", connector]
    if not on:
        return args + ["--off"]
    args.append("--on")
    turn = env.get("GEXIS_SCREEN_TRANSFORM")
    if turn and turn != "normal":
        args += ["--transform", turn]
    return args


async def switch_output(on: bool) -> bool:
    """The screen's output on or off. False, and logged, when it could not be."""
    try:
        uid = pwd.getpwnam(KIOSK_USER).pw_uid
    except KeyError:
        logger.warning("standby: no %s user; the screen stays as it is", KIOSK_USER)
        return False
    env = screen_env()
    # The ports are looked at only when screen.env names none.
    args = output_command(on, env, uid, env.get("GEXIS_SCREEN_CONNECTOR") or seen_connector())
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
            logger.info("standby: screen off (%s)", reason)

    async def wake(self, reason: str) -> None:
        async with self._lock:
            if not self.off:
                # Not in standby here - but the output may still be off from
                # before a restart. Switched on once, and again until it takes.
                if self._output_on is not True and await self._switch(True):
                    self._output_on = True
                    logger.info("standby: screen on (%s; its state was unknown)", reason)
                return
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

    `value(key)` reads a setting; `playing()` says whether music plays."""

    def __init__(self, standby: Standby, value, playing, *, clock=time.monotonic,
                 now=datetime.datetime.now) -> None:
        self._standby = standby
        self._value = value
        self._playing = playing
        self._clock = clock
        self._now = now

    async def tick(self) -> None:
        on = self._value("standby_schedule") is True and self._value("headless") is not True
        if self._playing():
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
