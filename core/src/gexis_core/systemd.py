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
