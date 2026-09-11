# SPDX-License-Identifier: GPL-3.0-or-later
"""Process-level escalation via systemd, shared by every adapter.

`systemctl kill` rather than hunting PIDs directly: every renderer is
already a systemd unit, this is the same mechanism an operator would use by
hand, and it avoids the ALSA-node/fuser fragility of finding "the right"
PID ourselves. Requires the core daemon to have kill authority over these
units - see the core's own systemd unit (User=root; see commit message for
why a polkit rule wasn't used instead).
"""
from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger("gexis_core.systemd")


def kill_unit(unit: str, *, force: bool) -> None:
    sig = "SIGKILL" if force else "SIGTERM"
    logger.info("systemctl kill --signal=%s %s", sig, unit)
    subprocess.run(
        ["systemctl", "kill", f"--signal={sig}", unit],
        check=False,
        capture_output=True,
    )


def stop_unit(unit: str) -> None:
    """`systemctl stop`, not a raw signal - found necessary 2026-09-11
    (Finding 013 §1's recurrence, ADR-0010). `systemctl kill` marks the
    unit's exit as a *failure* even when we caused it deliberately, which
    is what makes `Restart=on-failure` fire - the whole reason
    `adapters/lms.py` used it in the first place, to get squeezelite back
    after a SIGTERM it exits cleanly on. But that same automatic restart
    then races the ALSA device against whoever just took it over,
    independently of and in parallel with the arbitration ladder's own
    timing, for as long as the device stays busy - repeated fast enough,
    for long enough, to exhaust even a raised `StartLimitBurst`. `stop`
    marks the unit's target state as deliberately inactive instead -
    systemd does not restart a unit that was asked to stop, regardless of
    how the underlying process actually exits (including a forced kill if
    it doesn't respond to the stop request in time, per the unit's own
    `TimeoutStopSec`) - so nothing retries automatically at all once this
    is called. See `start_unit` for how the renderer comes back under our
    own control instead.
    """
    logger.info("systemctl stop %s", unit)
    subprocess.run(["systemctl", "stop", unit], check=False, capture_output=True)


def start_unit(unit: str) -> None:
    """Idempotent against an already-running unit (a plain success,
    no restart, no interruption) - callers don't need to track whether
    they actually stopped it first before calling this."""
    logger.info("systemctl start %s", unit)
    subprocess.run(["systemctl", "start", unit], check=False, capture_output=True)
