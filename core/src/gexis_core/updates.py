# SPDX-License-Identifier: GPL-3.0-or-later
"""The core's side of updates (ADR-0105 §6, Phase 13c step 5): what is
installed, what the updater last said, and starting it.

The updater itself is `/usr/lib/gexis/gexis-update`, run by its own units and
never by the core: an install restarts the core, and has to outlive it. The
core only starts those units and reads the status file the updater writes.
"""
from __future__ import annotations

import calendar
import json
import logging
import subprocess
import time
from pathlib import Path

logger = logging.getLogger("gexis_core.updates")

STATUS = Path("/var/lib/gexis/updates/status.json")
#: What "Check for updates" starts: a check, never an install. The nightly
#: timer's unit, gexis-update-check.service, runs `scheduled`, which installs
#: when Updates is Automatic - wrong for a button that says it installs
#: nothing (2026-10-06).
CHECK_UNIT = "gexis-update-checknow.service"
INSTALL_UNIT = "gexis-update-install.service"


#: dpkg's own record of what is installed. Its change time is when the
#: answer below can have changed.
DPKG_STATUS = Path("/var/lib/dpkg/status")
_installed: tuple[float | None, str | None] = (None, None)


def installed_release(status_file: Path | None = None) -> str | None:
    """The installed `gexis-player` - the release (ADR-0107), which an
    update changes and the image stamp does not.

    **Asked of dpkg once per change of its status file**, not per call: four
    Settings rows read it, on every `GET /settings`, and at 31 ms a
    `dpkg-query` it was most of what made saving a setting slow (George,
    2026-10-05: the button stayed disabled for seconds).
    """
    global _installed
    try:
        stamp = (status_file or DPKG_STATUS).stat().st_mtime
    except OSError:
        stamp = None
    if stamp is not None and _installed[0] == stamp:
        return _installed[1]
    try:
        out = subprocess.run(["dpkg-query", "-W", "-f", "${Version}", "gexis-player"],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    version = out.stdout.strip() or None
    _installed = (stamp, version)
    return version


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


def checked_when(at: str | None, now: float | None = None) -> str | None:
    """`today 03:12`, `yesterday 03:12`, or `28 Sep`: when the updater last
    answered, in the device's time."""
    if not at:
        return None
    try:
        then = calendar.timegm(time.strptime(at, "%Y-%m-%dT%H:%M:%SZ"))
    except ValueError:
        return None
    local = time.localtime(then)
    today = time.localtime(now if now is not None else time.time())
    day = (today.tm_year, today.tm_yday)
    if (local.tm_year, local.tm_yday) == day:
        return time.strftime("today %H:%M", local)
    yesterday = time.localtime((now if now is not None else time.time()) - 86400)
    if (local.tm_year, local.tm_yday) == (yesterday.tm_year, yesterday.tm_yday):
        return time.strftime("yesterday %H:%M", local)
    return time.strftime("%-d %b", local)


def release_line(channel: str | None, installed: str | None = None) -> str:
    """The Release row (George, 2026-10-01): only what this device runs, and
    the channel it follows - `0.3.1 · Testing`."""
    here = short(installed if installed is not None else installed_release()) or "unknown"
    return f"{here} · {channel}" if channel else here


def sentence(path: Path = STATUS, installed: str | None = None, now: float | None = None) -> str:
    """The Software update tile's line (George, 2026-10-01; ADR-0110 §2 as
    amended): what the updater last found, and when."""
    doc = status(path)
    state = doc.get("state")
    here = short(installed if installed is not None else installed_release()) or "unknown"
    release = short(doc.get("release")) or ""
    if not state:
        return "Not checked yet"
    if state == "checking":
        return "Checking…"
    if state == "current":
        when = checked_when(doc.get("at"), now)
        return f"Up to date · checked {when}" if when else "Up to date"
    if state == "available":
        return f"{release} available"
    if state == "done":
        return f"Updated to {here}"
    if state == "failed":
        return "Did not update"
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
    """The Release row's note: what the waiting release says changed, in its
    own words (2026-10-01, George). None when the release has no notes, or
    the state is anything else - once installed, its notes are under Change
    logs (ADR-0116: *"Once the update is done though there is no point in
    [showing] it there anymore"*)."""
    doc = status(path)
    text = doc.get("whats_new")
    if not text or doc.get("state") != "available":
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
