# SPDX-License-Identifier: GPL-3.0-or-later
"""**Plugins a user uploads** (ADR-0106, Phase 13a).

Not part of Gexis Player, installed and run at the user's own risk. What this
module owns is the part that must be right whoever built the package:

- **Checked before anything is written.** The manifest parses and passes the
  contract's own validation; its id is nobody else's; no path in the archive
  escapes it; the command it names exists and is built for this machine.
- **Installed where nothing of ours lives**: `/var/lib/gexis/plugins/<id>/
  <version>/`, with `current` pointing at it and the previous version kept for
  one step back. Never under `/usr` or `/etc`.
- **Run by a unit the player writes.** The manifest carries no `unit`; the
  plugin runs under `gexis-uploaded-<kind>@<id>.service`, a template in the
  image with the sandbox in it (ADR-0106): a temporary user per run, the system
  read-only, the sound card only for a renderer, the network open.
"""
from __future__ import annotations

import io
import json
import logging
import re
import shutil
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from gexis_core import plugins

logger = logging.getLogger("gexis_core.uploads")

UPLOADS = Path("/var/lib/gexis/plugins")
#: What the archive may weigh. Plexamp, the largest renderer this device
#: runs, is 14 MB compressed; this is room for a good deal more than that.
MAX_BYTES = 200 * 1024 * 1024
#: What it may unpack to, so a small archive cannot fill the card.
MAX_UNPACKED = 600 * 1024 * 1024
VERSION = re.compile(r"^[0-9A-Za-z][0-9A-Za-z.+~-]{0,39}$")
#: ELF's `e_machine` for AArch64 - the Pi 4 running a 64-bit system.
EM_AARCH64 = 0xB7


class Refused(ValueError):
    """Why a package was not installed, in words a person can act on."""


@dataclass(frozen=True)
class Checked:
    manifest: dict
    id: str
    version: str
    kind: str
    run: str


def unit_for(plugin_id: str, kind: str) -> str:
    """The unit an uploaded plugin runs under - never one it brings."""
    return f"gexis-uploaded-{kind}@{plugin_id}.service"


def _members(tar: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members = tar.getmembers()
    total = 0
    for m in members:
        path = PurePosixPath(m.name)
        if path.is_absolute() or ".." in path.parts:
            raise Refused(f"{m.name} points outside the package")
        if m.isdev() or m.isfifo():
            raise Refused(f"{m.name} is a device or a pipe")
        if m.issym() or m.islnk():
            target = PurePosixPath(m.linkname)
            resolved = (path.parent / target) if m.issym() else target
            if target.is_absolute() or ".." in PurePosixPath(*resolved.parts).parts:
                raise Refused(f"{m.name} links outside the package")
        total += max(m.size, 0)
        if total > MAX_UNPACKED:
            raise Refused("it unpacks to more than 600 MB")
    return members


def _executable_for_this_machine(data: bytes) -> bool:
    """An aarch64 ELF, or a script with an interpreter line."""
    if data[:4] == b"\x7fELF":
        return len(data) > 20 and int.from_bytes(data[18:20], "little") == EM_AARCH64
    return data[:2] == b"#!"


def check(archive: bytes, *, ours: set[str], installed: dict[str, str]) -> Checked:
    """Everything that decides whether the package goes in, before it does.

    `ours` are the ids that belong to the player (built in or shipped);
    `installed` maps an uploaded plugin's id to its installed version.
    """
    if len(archive) > MAX_BYTES:
        raise Refused("it is larger than 200 MB")
    try:
        tar = tarfile.open(fileobj=io.BytesIO(archive), mode="r:*")
    except (tarfile.TarError, OSError):
        raise Refused("it is not a .tar.gz package") from None
    with tar:
        members = _members(tar)
        names = {PurePosixPath(m.name).as_posix().lstrip("./") or ".": m for m in members}
        if "plugin.json" not in names:
            raise Refused("plugin.json is not at the top of the package")
        try:
            raw = json.loads(tar.extractfile(names["plugin.json"]).read())
        except (ValueError, AttributeError):
            raise Refused("plugin.json is not readable JSON") from None
        if not isinstance(raw, dict):
            raise Refused("plugin.json is not an object")
        if "unit" in raw:
            raise Refused("an uploaded plugin may not bring its own unit; the player writes it")
        for field in ("version", "run"):
            if not isinstance(raw.get(field), str) or not raw[field]:
                raise Refused(f"plugin.json has no {field!r}")
        if not VERSION.match(raw["version"]):
            raise Refused(f"{raw['version']!r} is not a usable version")
        try:
            parsed = plugins.parse({**raw, "unit": "placeholder.service"})
        except plugins.BadManifest as exc:
            raise Refused(f"plugin.json: {exc}") from None
        if parsed.id in ours:
            raise Refused(f"{parsed.id!r} belongs to the player")
        if installed.get(parsed.id) == raw["version"]:
            raise Refused(f"version {raw['version']} of {parsed.id} is already installed")
        run = PurePosixPath(raw["run"])
        if run.is_absolute() or ".." in run.parts or run.as_posix() not in names:
            raise Refused(f"the command {raw['run']!r} is not in the package")
        member = names[run.as_posix()]
        if not member.isfile():
            raise Refused(f"the command {raw['run']!r} is not a file")
        head = tar.extractfile(member).read(64)
        if not _executable_for_this_machine(head):
            raise Refused(f"{raw['run']!r} is not built for this player (aarch64) or a script")
    return Checked(manifest=raw, id=parsed.id, version=raw["version"], kind=parsed.kind, run=run.as_posix())


def install(archive: bytes, *, ours: set[str], root: Path = UPLOADS) -> Checked:
    """Check, then unpack beside what is there and switch `current` over.
    The version before it stays; anything older goes."""
    installed = {p.id: v for p, v in _installed_versions(root)}
    checked = check(archive, ours=ours, installed=installed)
    home = root / checked.id
    home.mkdir(parents=True, exist_ok=True)
    staging = home / f".{checked.version}.partial"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as tar:
        # `data` refuses what `_members` already refused, as a second guard,
        # and drops setuid bits and ownership.
        tar.extractall(staging, filter="data")
    (staging / checked.run).chmod((staging / checked.run).stat().st_mode | 0o555)
    target = home / checked.version
    shutil.rmtree(target, ignore_errors=True)
    staging.rename(target)
    previous = (home / "current").resolve().name if (home / "current").is_symlink() else None
    link = home / ".current.new"
    link.unlink(missing_ok=True)
    link.symlink_to(checked.version)
    link.replace(home / "current")
    for old in home.iterdir():
        if old.name.startswith(".") or old.name in ("current", checked.version, previous):
            continue
        if old.is_dir():
            shutil.rmtree(old, ignore_errors=True)
    logger.info("uploads: %s %s installed (previous %s)", checked.id, checked.version, previous)
    return checked


def _installed_versions(root: Path) -> list[tuple[plugins.Plugin, str]]:
    found = []
    try:
        homes = sorted(p for p in root.iterdir() if p.is_dir())
    except OSError:
        return found
    for home in homes:
        current = home / "current"
        manifest = current / "plugin.json"
        if not manifest.is_file():
            continue
        try:
            raw = json.loads(manifest.read_text())
            plugin = plugins.parse({**raw, "unit": unit_for(raw.get("id", ""), raw.get("kind", ""))},
                                   directory=current)
        except (OSError, ValueError) as exc:
            logger.warning("uploads: ignoring %s: %s", manifest, exc)
            continue
        if plugin.id != home.name:
            logger.warning("uploads: %s declares id %r; ignored", home, plugin.id)
            continue
        found.append((plugin, str(raw.get("version", ""))))
    return found


def installed(root: Path = UPLOADS) -> list[plugins.Plugin]:
    """Every uploaded plugin whose current version reads, with the unit the
    player gives it."""
    return [p for p, _ in _installed_versions(root)]


def remove(plugin_id: str, root: Path = UPLOADS) -> bool:
    """Delete an uploaded plugin's versions. Its unit is stopped by the
    caller first; its data (the unit's state directory) goes with the unit."""
    home = root / plugin_id
    if not home.is_dir():
        return False
    shutil.rmtree(home)
    logger.info("uploads: %s removed", plugin_id)
    return True
