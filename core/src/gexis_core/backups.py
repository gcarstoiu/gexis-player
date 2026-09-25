# SPDX-License-Identifier: GPL-3.0-or-later
"""**What a flash destroys, in one file** (ADR-0083).

Assembled by asking what the card holds that nobody can type back in: the
settings store, the enrichment cache the sweeps fill, the two files in
`/etc/gexis` that carry the LMS address and the idle URL, and BlueZ's
pairings. Written into a share of its own, because **a backup that stays on
the device does not survive the event it exists for.**

Everything here is deliberately dumb - `tar`, a directory listing, and a
restore that puts files back and asks for a reboot. A button somebody presses
once a month is the wrong place for a mechanism.
"""
from __future__ import annotations

import logging
import re
import subprocess
import tarfile
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("gexis_core.backups")

#: The share (ADR-0083). A sibling of `pictures`, not a parent of anything.
DEFAULT_DIR = Path("/var/lib/gexis-core/backups")

#: What goes in, relative to `/`. Missing members are skipped rather than
#: failing the archive: a device that has never paired anything has no
#: `/var/lib/bluetooth`, and that is not an error.
MEMBERS = (
    "var/lib/gexis-core/settings.db",
    "var/lib/gexis-core/enrichment.db",
    "etc/gexis/core.toml",
    "etc/gexis/device-name.env",
    "var/lib/bluetooth",
)

#: `gexis-<name>-<stamp>.tgz`. The name is the device's, so an archive says
#: where it came from - ADR-0083 does not prevent restoring one device's
#: archive onto another, and this is what makes it visible.
NAME = re.compile(r"^gexis-.*-\d{8}-\d{6}\.tgz$")

#: Nothing outside the backup directory is ever read or written by name, and a
#: name that tries is refused rather than sanitised.
SAFE = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class Archive:
    name: str
    made: float
    size: int

    def to_item(self) -> dict:
        """The shape a `list` row's items take (ADR-0044 §1)."""
        when = time.strftime("%-d %b %Y, %H:%M", time.localtime(self.made))
        return {
            "name": self.name,
            "meta": f"{when} · {self.size / 1_048_576:.1f} MB",
            "state": "saved",
            "bars": None,
        }


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", (text or "gexis").strip()).strip("-")
    return (cleaned or "gexis").lower()


def available(directory: Path = DEFAULT_DIR) -> list[Archive]:
    """Every archive in the share, **newest first**.

    A file that is not one of ours is ignored rather than listed: the share is
    writable by anyone on the LAN, so it can hold anything at all.
    """
    try:
        entries = list(directory.iterdir())
    except OSError:
        return []
    found = []
    for entry in entries:
        if not entry.is_file() or not NAME.match(entry.name):
            continue
        try:
            stat = entry.stat()
        except OSError:
            continue
        found.append(Archive(entry.name, stat.st_mtime, stat.st_size))
    return sorted(found, key=lambda a: a.made, reverse=True)


def create(device_name: str, directory: Path = DEFAULT_DIR, root: Path = Path("/")) -> str:
    """Write one, and return its name.

    **Written to a temporary name and renamed**, so a half-written archive is
    never listed as a whole one - the share is read by a person who cannot
    tell the difference.
    """
    directory.mkdir(parents=True, exist_ok=True)
    name = f"gexis-{_slug(device_name)}-{time.strftime('%Y%m%d-%H%M%S')}.tgz"
    final = directory / name
    partial = directory / f".{name}.part"
    try:
        with tarfile.open(partial, "w:gz") as archive:
            for member in MEMBERS:
                source = root / member
                if not source.exists():
                    logger.info("backup: %s is not here, skipping", member)
                    continue
                archive.add(source, arcname=member)
        partial.replace(final)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    # The share is `force user = pi`; an archive root wrote has to be
    # replaceable by the next writer.
    try:
        subprocess.run(["chown", "pi:pi", str(final)], check=False, capture_output=True)
    except OSError:
        pass
    logger.info("backup: wrote %s (%d bytes)", name, final.stat().st_size)
    return name


def restore(name: str, directory: Path = DEFAULT_DIR, root: Path = Path("/")) -> None:
    """Put one back. **The caller reboots** (ADR-0083).

    Refuses a name that is not ours and a member that would land outside the
    paths this module writes - the share is guest-writable, so an archive in
    it is not necessarily one we made.
    """
    if not SAFE.match(name) or not NAME.match(name):
        raise ValueError(f"not a backup name: {name!r}")
    path = directory / name
    if not path.is_file():
        raise FileNotFoundError(str(path))
    allowed = tuple(MEMBERS)
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            if not member.name.startswith(allowed):
                raise ValueError(f"{name}: refuses to write {member.name!r}")
            if member.issym() or member.islnk():
                raise ValueError(f"{name}: refuses a link, {member.name!r}")
        archive.extractall(root, members=members)
    logger.warning("backup: restored %s over %d path(s); a reboot follows", name, len(members))


def forget(name: str, directory: Path = DEFAULT_DIR) -> None:
    if not SAFE.match(name) or not NAME.match(name):
        raise ValueError(f"not a backup name: {name!r}")
    (directory / name).unlink(missing_ok=True)
    logger.info("backup: deleted %s", name)
