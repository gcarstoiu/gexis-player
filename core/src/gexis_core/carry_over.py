# SPDX-License-Identifier: GPL-3.0-or-later
"""**Ours that moved to the catalogue, carried over** (ADR-0174).

Beszel's agent and hub shipped with the player until ADR-0174 made them
catalogue plugins (Plexamp follows). The release that moved them removes
their packages - `gexis-player` conflicts with them - and their data, which
is not package files, stays where it was. At the first start without a
package:

- **its old service is stopped first**: our packages never stopped it when
  they were removed, and one found on sofapi (2026-11-03) went on running
  beside the catalogue's, the same agent twice;
- **its data moves into the plugin's own folder** (the sandbox's state
  directory, which systemd hands to the plugin's user when it starts), used
  or not, so a plugin removed with *Keep its settings and sign-in* still
  finds them when added again;
- **a player that used it gets it from the catalogue** without being asked
  (George, 2026-11-03): it is recorded as a plugin from the catalogue whose
  package is missing, which the restore's path installs (ADR-0168), at
  every start until it is there;
- **switched on again** once installed, if it was on;
- the user its package made goes once no package needs it.

*Used* is what ADR-0169 calls in use: switched on (its stored switch, or its
old unit still enabled - a switch nobody touched reads systemd), or on the
Plugins page.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from gexis_core import uploads

logger = logging.getLogger("gexis_core.carry_over")

WANTS = Path("/etc/systemd/system/multi-user.target.wants")


@dataclass(frozen=True)
class Moved:
    id: str
    name: str
    kind: str
    #: The unit its package ran it under.
    unit: str
    #: What it kept, each moved into the plugin's own folder whole.
    data: tuple[Path, ...]
    #: The package that installed it, gone from the release.
    package: str
    #: System users its package made, deleted when no such package is left.
    users: tuple[str, ...] = ()


MOVED: tuple[Moved, ...] = (
    Moved("beszel", "Beszel", "service", "beszel-agent.service",
          (Path("/var/lib/beszel-agent"),), "gexis-beszel-agent", ("beszel",)),
    Moved("beszel-hub", "Beszel hub", "service", "beszel-hub.service",
          (Path("/var/lib/beszel-hub"),), "gexis-beszel-hub", ("beszel",)),
)

#: The record's flag: switch it on once its package is installed.
SWITCH_ON = "carried_on"


def used(moved: Moved, *, stored: object, added: set[str] | None, wants: Path = WANTS) -> tuple[bool, bool]:
    """(carried, switched on): whether the player used it, and whether it was on."""
    on = stored is True or (stored is None and (wants / moved.unit).is_symlink())
    return (on or moved.id in (added or set()), on)


def move_data(moved: Moved, private: Path = uploads.STATE_PRIVATE) -> bool:
    """Its old places' contents into its own folder, once: a file already
    there is the plugin's own and stays. True when something moved."""
    target = private / moved.id
    did = False
    for old in moved.data:
        if not old.is_dir() or old.is_symlink():
            continue
        if not private.parent.exists():
            # /var/lib/private: systemd makes it 0700 for DynamicUser units.
            private.parent.mkdir(mode=0o700, parents=True)
        target.mkdir(parents=True, exist_ok=True)
        for item in sorted(old.iterdir()):
            if (target / item.name).exists():
                logger.warning("carry-over: %s already has %s; the old one stays in %s",
                               moved.id, item.name, old)
                continue
            shutil.move(str(item), str(target / item.name))
            did = True
        try:
            old.rmdir()
        except OSError:
            pass
    return did


def carry(*, ours: set[str], stored: Callable[[str], object], added: set[str] | None,
          known: Path = uploads.KNOWN, private: Path = uploads.STATE_PRIVATE,
          wants: Path = WANTS, installed_packages: Callable[[], set[str]] | None = None,
          versions: Callable[[], dict[str, str]] = uploads.versions,
          stop: Callable[[str], None] | None = None,
          moved: Iterable[Moved] = MOVED) -> list[str]:
    """Everything owed at this start, before the restore's list is read.
    Returns the ids recorded to be installed from the catalogue."""
    recorded = []
    left = [m for m in moved if m.id not in ours]
    for m in left:
        (stop or _stop)(m.unit)
        if move_data(m, private):
            logger.info("carry-over: %s's data moved into its own folder", m.id)
        carried, on = used(m, stored=stored(f"{m.id}.enabled"), added=added, wants=wants)
        link = wants / m.unit
        if link.is_symlink() and not link.exists():
            link.unlink()  # the old unit's, left by its package's removal
        if not carried or m.id in uploads.origins(known) or m.id in versions():
            continue
        uploads.record_missing(m.id, {"name": m.name, "kind": m.kind, "version": None,
                                      "origin": uploads.CATALOGUE, SWITCH_ON: on}, known)
        recorded.append(m.id)
        logger.info("carry-over: %s will be installed from the catalogue%s", m.id, ", and switched on" if on else "")
    _drop_users([m for m in moved if m.id in ours], left, installed_packages)
    return recorded


def _stop(unit: str) -> None:
    """The old unit, stopped if it still runs: its file went with its
    package, but systemd keeps a running unit until it is stopped."""
    subprocess.run(["systemctl", "stop", unit], check=False, capture_output=True)


def _drop_users(still: list[Moved], gone: list[Moved],
                installed_packages: Callable[[], set[str]] | None) -> None:
    needed = {u for m in still for u in m.users}
    for user in sorted({u for m in gone for u in m.users} - needed):
        packages = installed_packages() if installed_packages else set()
        if any(m.package in packages for m in gone if user in m.users):
            continue
        result = subprocess.run(["getent", "passwd", user], check=False, capture_output=True)
        if result.returncode != 0:
            continue
        result = subprocess.run(["userdel", user], check=False, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("carry-over: user %s deleted; no package of ours needs it", user)
        else:
            logger.warning("carry-over: user %s not deleted: %s", user, (result.stderr or "").strip())


def to_switch_on(installed: set[str], known: Path = uploads.KNOWN) -> list[str]:
    """Carried plugins now installed that were on: their flag cleared, to be
    switched on by the caller."""
    ids = []
    for plugin_id, info in uploads.known(known).items():
        if plugin_id in installed and isinstance(info, dict) and SWITCH_ON in info:
            if info[SWITCH_ON]:
                ids.append(plugin_id)
            uploads.clear_flag(plugin_id, SWITCH_ON, known)
    return ids


def installed_packages() -> set[str]:
    """The names dpkg calls installed, for the old packages' users."""
    result = subprocess.run(["dpkg-query", "-W", "-f=${Package} ${db:Status-Abbrev}\\n"],
                            check=False, capture_output=True, text=True, env={**os.environ, "LC_ALL": "C"})
    return {line.split()[0] for line in (result.stdout or "").splitlines()
            if len(line.split()) > 1 and line.split()[1].startswith("ii")}
