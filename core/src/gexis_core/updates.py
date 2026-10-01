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


#: The updater's states, in the words the row shows.
_WORDS = {
    "checking": "Checking…",
    "downloading": "Downloading {release}…",
    "backing-up": "Backing up before {release}…",
    "waiting": "{release} is ready: waiting until nothing plays",
    "installing": "Installing {release}…",
    "going-back": "Putting the release before back…",
}


def sentence(path: Path = STATUS) -> str:
    """One line for the Release row: what the updater last said."""
    doc = status(path)
    state = doc.get("state")
    release = doc.get("release") or ""
    if not state:
        return "Not checked yet"
    if state == "current":
        return f"Up to date ({doc.get('channel', '')})".replace(" ()", "")
    if state == "available":
        return f"{release} is waiting"
    if state == "done":
        return f"Updated to {release}"
    if state == "failed":
        return "Did not update: " + (doc.get("message") or "see the device's log")
    return _WORDS.get(state, state).format(release=release)


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
    return f"What's new in {doc.get('release', 'this release')}: {text}"


def start(unit: str) -> None:
    """Start the updater's unit and return at once: an install takes minutes
    and restarts the core, so nothing here waits for it."""
    try:
        subprocess.run(["systemctl", "start", "--no-block", unit], check=True,
                       capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("updates: could not start %s: %s", unit, exc)
