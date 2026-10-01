# SPDX-License-Identifier: GPL-3.0-or-later
"""The core's side of updates (ADR-0105 §6, Phase 13c step 5): what is
installed, what the updater last said, and starting it.

The updater itself is `/usr/lib/gexis/gexis-update`, run by its own units and
never by the core: an install restarts the core, and has to outlive it. The
core only starts those units and reads the status file the updater writes.
"""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("gexis_core.updates")

STATUS = Path("/var/lib/gexis/updates/status.json")
CHECK_UNIT = "gexis-update-check.service"
INSTALL_UNIT = "gexis-update-install.service"


def installed_release() -> str | None:
    """The installed `gexis-player` - the release (ADR-0107), which an
    update changes and the image stamp does not."""
    try:
        out = subprocess.run(["dpkg-query", "-W", "-f", "${Version}", "gexis-player"],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() or None


def status(path: Path = STATUS) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def short(version: str | None) -> str | None:
    """ADR-0110 §1: a release is shown by its number - `0.2.4`, not
    `0.2.1+git871.c73ea29`. A build without a number shows the part before
    `+`; the long form stays on the Image build row."""
    return version.split("+", 1)[0] if version else version


#: The updater's states while an install runs (ADR-0110 §6: the panel is
#: locked for all of them).
INSTALLING = frozenset({"downloading", "backing-up", "stopping", "installing", "restarting",
                        "checking-device", "going-back", "waiting"})


def sentence(path: Path = STATUS, installed: str | None = None) -> str:
    """The Release tile's line (ADR-0110 §2): the installed number and its
    state, or the number that is waiting."""
    doc = status(path)
    state = doc.get("state")
    here = short(installed if installed is not None else installed_release()) or "unknown"
    release = short(doc.get("release")) or ""
    if not state:
        return f"{here} · Not checked yet"
    if state == "checking":
        return f"{here} · Checking…"
    if state == "current":
        return f"{here} · Up to date"
    if state == "available":
        return f"{release} available"
    if state == "done":
        return f"{here} · Updated"
    if state == "failed":
        return f"{here} · Did not update"
    if state == "going-back":
        return f"Going back to {short(doc.get('previous')) or here}…"
    return f"Updating to {release}…"


def view(path: Path = STATUS, installed: str | None = None, running: bool | None = None) -> dict:
    """What `/state` publishes as `update` (ADR-0110): enough for the modal
    and for the panel's lock, read from the updater's file - so it survives
    the core's restart in the middle of an install.

    **`active` needs the install unit running**, not only the file saying so:
    an updater killed mid-way would otherwise leave the panel locked for
    ever behind a stale *installing*."""
    doc = status(path)
    state = doc.get("state")
    if running is None:
        running = state in INSTALLING and unit_running(INSTALL_UNIT)
    return {
        "installed": short(installed if installed is not None else installed_release()),
        "state": state,
        "release": short(doc.get("release")),
        "previous": short(doc.get("previous")),
        "attempted": short(doc.get("attempted")),
        "steps": doc.get("steps"),
        "progress": doc.get("progress"),
        "whats_new": doc.get("whats_new"),
        "message": doc.get("message"),
        "reboot": bool(doc.get("reboot")),
        "at": doc.get("at"),
        "active": bool(running and state in INSTALLING),
    }


def unit_running(unit: str) -> bool:
    try:
        out = subprocess.run(["systemctl", "is-active", unit], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return False
    return out.stdout.strip() in ("active", "activating")


def notes(path: Path = STATUS) -> str | None:
    """Where the waiting release says what changed."""
    return status(path).get("notes")


def whats_new(path: Path = STATUS) -> str | None:
    """The Release row's note: what the waiting or just-installed release
    says changed, in its own words (2026-10-01, George). None when the
    release has no notes, or the state is anything else."""
    doc = status(path)
    text = doc.get("whats_new")
    if not text or doc.get("state") not in ("available", "done"):
        return None
    return f"What's new in {short(doc.get('release')) or 'this release'}: {text}"


def start(unit: str) -> None:
    """Start the updater's unit and return at once: an install takes minutes
    and restarts the core, so nothing here waits for it."""
    try:
        subprocess.run(["systemctl", "start", "--no-block", unit], check=True,
                       capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("updates: could not start %s: %s", unit, exc)
