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


def set_enabled(unit: str, enabled: bool, *, now: bool = True) -> None:
    """**ADR-0077: a source that is off is not running, and stays off across a
    reboot.**

    `enable --now` / `disable --now` rather than `start`/`stop`: a row whose
    effect ends at the next boot is a row that lies the second time you look
    at it. `--now` folds the start or stop in, so this is one call rather than
    two that can disagree.

    `now=False` for a unit that only makes sense at boot - the panel's warm-up
    reads the kiosk's binaries into the page cache and says so in its own unit
    file: "if the kiosk has already started, warming is pointless". Enabling it
    mid-session should ask for it at the next boot, not run it now.

    `disable --now` stops, it does not kill, which is what `stop_unit` above
    is careful about for the same reason - systemd does not restart a unit it
    was asked to stop, so nothing races the ALSA device on the way out.

    Not `mask`: masking is for a unit that must never run and leaves a symlink
    to `/dev/null` for a later image update to reason about. Nothing in this
    image pulls these units in as a dependency, so `disable` says the same
    thing reversibly (ADR-0077's reversal condition is exactly that changing).
    """
    verb = "enable" if enabled else "disable"
    argv = ["systemctl", verb] + (["--now"] if now else []) + [unit]
    logger.info("%s", " ".join(argv))
    result = subprocess.run(
        argv,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.warning(
            "%s failed (%s): %s",
            " ".join(argv),
            result.returncode,
            (result.stderr or "").strip(),
        )


def restart_if_enabled(unit: str) -> None:
    """Restart a unit that is *supposed* to be running, and only that (ADR-0088).

    A plugin's environment is read once at exec, so a changed credential means a
    restart. The question is which units that applies to, and the first answer
    was wrong: `systemctl try-restart` touches a unit that is **active**, and the
    Beszel agent's first real state was **failed** - switched on before anyone had
    typed a token, refusing to start without one, exactly as it should. Typing the
    token then changed the file and `try-restart` did nothing, because a failed
    unit is not active. The credential arrived and nothing used it until a reboot.
    Found on the device 2026-09-25 (Finding 079).

    **So the gate is `is-enabled`, not `is-active`**: enabled means somebody asked
    for this to run, and a value they just typed is how it gets to. Disabled means
    off, and off stays off - which is the one case `try-restart` got right and
    this keeps.

    `reset-failed` first: a unit that has hit `StartLimitBurst` refuses a plain
    restart with "start request repeated too quickly", and an agent that spent its
    five tries before being configured is the *expected* path here, not an edge
    case. Harmless on a healthy unit.
    """
    if not is_enabled(unit):
        logger.info("plugins: %s is disabled, not restarting it", unit)
        return
    logger.info("systemctl reset-failed + restart %s", unit)
    subprocess.run(["systemctl", "reset-failed", unit], check=False, capture_output=True)
    subprocess.run(["systemctl", "restart", unit], check=False, capture_output=True)


def is_enabled(unit: str) -> bool:
    """Whether systemd will start this unit at boot.

    **The truth a synthesised `Enabled` row defaults to** (ADR-0086 as amended,
    ADR-0088). A declared default would be a second statement of the same fact,
    and found on the device 2026-09-25: a manifest defaulting its switch to
    *on* beside an image that installs the unit *disabled* puts a row on the
    screen reading "Enabled" for something that is not running and will not
    start. Asking systemd cannot disagree with systemd.

    `enabled-runtime` counts as enabled - it is, until the next boot - and
    everything else does not, including `static` and `masked`: neither is a
    thing this switch can meaningfully turn on.
    """
    result = subprocess.run(
        ["systemctl", "is-enabled", unit], check=False, capture_output=True, text=True,
    )
    state = (result.stdout or "").strip()
    return state in ("enabled", "enabled-runtime")
