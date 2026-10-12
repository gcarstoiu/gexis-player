# SPDX-License-Identifier: GPL-3.0-or-later
"""**Debug logs** (ADR-0103): the journal kept on the card across restarts,
when the user asks.

The image keeps it in memory (Raspberry Pi OS's `40-rpi-volatile-storage.conf`,
`Storage=volatile`), and a reboot loses it - which cost George the logs of a bug
he had just reproduced. On, a drop-in of our own with a higher number makes it
persistent, capped at 100 MB; off, the drop-in and the kept logs go, and the
image's own setting applies again.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("gexis_core.journal")

DROPIN = Path("/etc/systemd/journald.conf.d/60-gexis-debug-logs.conf")
KEPT = Path("/var/log/journal")
CONTENT = "[Journal]\nStorage=persistent\nSystemMaxUse=100M\n"


def is_kept(dropin: Path = DROPIN) -> bool:
    """Whether the device is keeping its logs now: our drop-in, as we write it."""
    try:
        return dropin.read_text() == CONTENT
    except OSError:
        return False


def has_kept_logs(kept: Path = KEPT) -> bool:
    """Whether any journal files are on the card. **Files, not the folder:**
    systemd's tmpfiles creates `/var/log/journal` empty on the image, and
    journald ignores it while storage is volatile. Counting the folder made the
    startup check restart journald on a device that had never used the switch
    (found on gexis, 2026-09-28)."""
    try:
        return any(kept.rglob("*.journal*"))
    except OSError:
        return False


def matches(on: bool, dropin: Path = DROPIN, kept: Path = KEPT) -> bool:
    """Whether the device already does what the switch says. Off also means no
    kept logs left behind."""
    if on:
        return is_kept(dropin)
    return not dropin.exists() and not has_kept_logs(kept)


def apply(on: bool, *, dropin: Path = DROPIN, kept: Path = KEPT, run=subprocess.run) -> None:
    """Make the device keep its logs, or stop and delete them. Blocking: the
    caller runs it off the event loop."""
    if on:
        dropin.parent.mkdir(parents=True, exist_ok=True)
        tmp = dropin.with_name(dropin.name + ".tmp")
        tmp.write_text(CONTENT)
        tmp.replace(dropin)
        run(["systemctl", "restart", "systemd-journald"], check=False, capture_output=True)
        # What is already in memory goes to the card too: the logs from just
        # before the switch are the ones a problem is usually in.
        run(["journalctl", "--flush"], check=False, capture_output=True)
        logger.info("journal: kept on the card, up to 100 MB (ADR-0103)")
    else:
        dropin.unlink(missing_ok=True)
        run(["systemctl", "restart", "systemd-journald"], check=False, capture_output=True)
        # The files, not the folder, which systemd's tmpfiles owns.
        if kept.is_dir():
            for entry in kept.iterdir():
                if entry.is_dir():
                    shutil.rmtree(entry, ignore_errors=True)
                else:
                    entry.unlink(missing_ok=True)
        logger.info("journal: in memory again; the kept logs are deleted (ADR-0103)")
