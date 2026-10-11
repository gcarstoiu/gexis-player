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
import logging
import pwd
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


def output_command(on: bool, env: dict[str, str], uid: int) -> list[str]:
    """`wlr-randr` for the kiosk's output, run as the kiosk's user in its
    session. Waking re-applies the turn the kiosk set."""
    connector = env.get("GEXIS_SCREEN_CONNECTOR") or DEFAULT_CONNECTOR
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
    args = output_command(on, screen_env(), uid)
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
                 publish: Callable[[bool, str | None], None] | None = None) -> None:
        self._switch = switch
        self._publish = publish or (lambda off, reason: None)
        self.off = False
        self.reason: str | None = None
        self._lock = asyncio.Lock()

    async def sleep(self, reason: str) -> None:
        async with self._lock:
            if self.off:
                return
            self.off, self.reason = True, reason
            # Published before the output goes: the panel's black cover is
            # drawn while there is still a picture to replace.
            self._publish(True, reason)
            await self._switch(False)
            logger.info("standby: screen off (%s)", reason)

    async def wake(self, reason: str) -> None:
        async with self._lock:
            if not self.off:
                return
            await self._switch(True)
            self.off, self.reason = False, None
            self._publish(False, None)
            logger.info("standby: screen on (%s)", reason)
