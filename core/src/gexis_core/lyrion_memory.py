# SPDX-License-Identifier: GPL-3.0-or-later
"""**The Lyrion server and the player's memory** (ADR-0115 decision 18;
George, 2026-10-03: *"I just wonder what happens if someone with 1 or 2 GB
try a large library"*, then *"A plus B"*).

Lyrion's scanner grows with the library: about 27 KB a file, 1,876 MB for
Lyrion as a whole with George's tens of thousands of files (Finding 109). The unit may use
the player's memory less 1 GB (`lyrion-memory-limit`). Here:

- a player below 1.5 GB (a 1 GB Pi) is not offered the server at all;
- a scan stopped at the limit is said on the server's row, with about how
  many files fit - otherwise the library is simply half there, unexplained,
  since Lyrion rescans by itself only when its library is empty.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

MEMINFO = Path("/proc/meminfo")
CGROUP = Path("/sys/fs/cgroup/system.slice/gexis-lyrion.service")
STOPPED = Path("/var/lib/gexis/lyrion-scan-stopped.json")

#: Below this the player cannot spare the 1 GB it keeps and still give
#: Lyrion a useful share (a 1 GB Pi reports about 900 MB).
MIN_MB = 1536
#: What the scanner adds per file, by Lyrion's "Database Memory Config"
#: (`dbhighmem`), measured with George's tens of thousands of files (Finding 109): Normal
#: about 13 KB, High about 27 KB; Maximum's scanner is High's.
PER_FILE_KB = {0: 13, 1: 27, 2: 27}
#: Lyrion before its first file: the server, its cache, the kernel's share.
BASE_MB = 400


def total_mb(meminfo: Path = MEMINFO) -> int | None:
    try:
        for line in meminfo.read_text().splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def too_small(total: int | None) -> str | None:
    """Why this player is not offered the server, or None."""
    if total is None or total >= MIN_MB:
        return None
    return (f"This player has {round(total / 1024, 1):g} GB of memory. The Lyrion server needs a "
            f"player with 2 GB or more.")


def files_that_fit(limit_mb: int, highmem: int = 1) -> int:
    """About how many files a scan fits in `limit_mb`, to the thousand."""
    fit = max(0, limit_mb - BASE_MB) * 1024 // PER_FILE_KB.get(highmem, PER_FILE_KB[1])
    return int(round(fit, -3))


def oom_kills(cgroup: Path = CGROUP) -> int | None:
    """How many times the unit's processes were stopped for memory since it
    started (its cgroup's own count), or None when it is not running."""
    try:
        for line in (cgroup / "memory.events").read_text().splitlines():
            key, _, value = line.partition(" ")
            if key == "oom_kill":
                return int(value)
    except (OSError, ValueError):
        pass
    return None


def limit_mb(cgroup: Path = CGROUP) -> int | None:
    try:
        raw = (cgroup / "memory.max").read_text().strip()
        return None if raw == "max" else int(raw) // 1048576
    except (OSError, ValueError):
        return None


def remember_stopped(limit: int | None, highmem: int | None, path: Path = STOPPED) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"at": int(time.time()), "limit_mb": limit, "highmem": highmem}))


def forget_stopped(path: Path = STOPPED) -> None:
    path.unlink(missing_ok=True)


def stopped_note(path: Path = STOPPED) -> str | None:
    """The row's note after a scan was stopped for memory, or None."""
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    limit, highmem = doc.get("limit_mb"), doc.get("highmem")
    highmem = highmem if highmem in PER_FILE_KB else 1
    text = ("The last scan was stopped: this library is too large for this player's memory, so "
            "part of it is missing.")
    if isinstance(limit, int):
        text += f" About {files_that_fit(limit, highmem):,} files fit."
        if highmem != 0:
            # George, 2026-10-03: "an user with 4gb of ram and more than 90k
            # tracks can always go to normal and still have the library
            # scanning."
            text += (f" Set Database Memory Config to Normal (Lyrion's settings, Performance) and "
                     f"about {files_that_fit(limit, 0):,} fit; then scan again.")
    return text


class Watch:
    """Follows the running unit: a stop for memory is remembered; a scan that
    finishes without one clears it. The count is per start of the unit, so a
    lower number than last time is a new start, not a recovery."""

    def __init__(self, path: Path = STOPPED, cgroup: Path = CGROUP) -> None:
        self._path = path
        self._cgroup = cgroup
        self._seen: int | None = None
        self._scanning = False
        #: A stop during the scan under way: its end is then no recovery.
        self._stopped = False

    def update(self, scanning: bool, highmem: int | None = None) -> bool:
        """True when the note changed."""
        changed = False
        if scanning and not self._scanning:
            self._stopped = False
        kills = oom_kills(self._cgroup)
        if kills is not None and self._seen is not None and kills > self._seen:
            remember_stopped(limit_mb(self._cgroup), highmem, self._path)
            self._stopped = changed = True
        elif self._scanning and not scanning and not self._stopped and self._path.exists():
            forget_stopped(self._path)
            changed = True
        self._seen = kills
        self._scanning = scanning
        return changed
