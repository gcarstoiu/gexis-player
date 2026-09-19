# SPDX-License-Identifier: GPL-3.0-or-later
"""Dropping the boot splash when the panel has actually painted (ADR-0043).

The splash has to outlive `multi-user.target`: the panel is still a second
or two from its first frame at that point, and that gap is exactly where a
flash of black would show. Plymouth's own quit units are masked in the
image, so the only thing that ends the animation in a healthy boot is the
panel saying it has painted.

`--retain-splash` leaves the last frame on screen rather than clearing to
black, and the UI draws over it. The artwork is built for that: every frame
is the panel's own ground colour with a small mark on it, so any frame is a
safe thing to be underneath the first painted screen.
"""
from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger("gexis_core.splash")

PLYMOUTH = "/bin/plymouth"


class Splash:
    """Ends the boot animation, once.

    Called from a request handler the panel can retry, and a panel that
    reloads will report a first frame again - so this has to be safe to call
    repeatedly and after plymouth is long gone. It is: every failure mode
    here is "there is no splash to quit", which is not an error worth
    surfacing to a panel that is otherwise working.
    """

    def __init__(self, *, plymouth: str = PLYMOUTH) -> None:
        self._plymouth = plymouth
        self._done = False

    @property
    def dropped(self) -> bool:
        return self._done

    def drop(self) -> bool:
        """True if this call is what ended the splash."""
        if self._done:
            return False
        self._done = True
        try:
            result = subprocess.run(
                [self._plymouth, "quit", "--retain-splash"],
                check=False,
                capture_output=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            # No plymouth on a development machine, and none on a device
            # booted without the splash. Neither is a fault.
            logger.info("splash: nothing to quit (%s)", exc)
            return False
        if result.returncode != 0:
            logger.info(
                "splash: plymouth quit returned %s (%s)",
                result.returncode,
                result.stderr.decode(errors="replace").strip() or "no message",
            )
            return False
        logger.info("splash: dropped, the panel has painted")
        return True
