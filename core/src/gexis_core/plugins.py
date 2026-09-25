# SPDX-License-Identifier: GPL-3.0-or-later
"""**What the core knows about a plugin before it is running** (ADR-0086).

A plugin ships `plugin.json` beside a `mark.png` under
`/usr/share/gexis/plugins/<id>/`, and the core reads it whether or not the
plugin's process is up. That is the whole reason a manifest exists rather than
only the `hello` of `docs/PLUGIN-CONTRACT.md`: **a renderer that is switched
off never connects, and its `Enabled` row still has to be there to switch on.**

**The three built-ins are described this way too.** Not for tidiness - so that
the generic path is the one exercised on every boot. A plugin's glyph drawn by
code nothing else runs is how the first external plugin finds a hole
(ADR-0013's own argument, turned on presentation).
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("gexis_core.plugins")

#: Installed by a package, not edited by hand - so `/usr/share`, not `/etc`
#: (ADR-0086).
DEFAULT_DIR = Path("/usr/share/gexis/plugins")

#: An id is a directory name, a settings-row prefix and a URL path segment, so
#: it is held to what all three can carry.
ID = re.compile(r"^[a-z][a-z0-9-]{1,30}$")

KINDS = ("renderer", "service")


@dataclass(frozen=True)
class Plugin:
    """One manifest, validated. Presentation and identity only - what it can
    *do* arrives in `hello` at runtime."""

    id: str
    name: str
    kind: str
    unit: str
    #: The moOde-compatible status line (`metadata_file.py`). Absent means the
    #: file says nothing for this renderer, which is what it did before any of
    #: this existed.
    label: str | None = None
    #: A CSS colour for the UI's accent. Absent means the panel's default.
    accent: str | None = None
    #: The waiting screen's second line - "Listening", "Pairable".
    status: str | None = None
    #: `mark.png` beside the manifest, or None. Served at
    #: `/plugins/<id>/mark`, never read from the filesystem by the panel.
    mark: Path | None = None
    #: Rows to merge into the settings registry, untouched here: the registry
    #: owns that vocabulary and validates it (ADR-0044).
    settings: tuple[dict, ...] = field(default_factory=tuple)
    #: **The row that switches this plugin off** (ADR-0086 as amended
    #: 2026-09-25). A plugin that cannot be switched off is one the contract
    #: cannot express, which `docs/DEVELOPMENT.md` names as the test a
    #: non-renderer exists to apply. Left unset, the core makes one -
    #: `<id>.enabled` - and wires it to the plugin's unit. Set, it names a row
    #: that already exists, which is how the three built-ins keep the keys
    #: they have always had rather than growing a second switch each.
    enabled_row: str | None = None
    #: True for the three this repository ships. They are not special in how
    #: they are read - only in who wrote them.
    built_in: bool = False

    def to_json(self) -> dict:
        """What the panel needs to draw this source without knowing it."""
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "accent": self.accent,
            "status": self.status,
            "mark": f"/plugins/{self.id}/mark" if self.mark else None,
        }


class BadManifest(ValueError):
    """Said out loud rather than skipped: a plugin that ships a manifest the
    core cannot read has a bug its author needs to hear about."""


def parse(raw: dict, *, directory: Path | None = None, built_in: bool = False) -> Plugin:
    for required in ("id", "name", "kind", "unit"):
        if not raw.get(required):
            raise BadManifest(f"missing {required!r}")
    if not ID.match(raw["id"]):
        raise BadManifest(f"{raw['id']!r} is not a usable id")
    if raw["kind"] not in KINDS:
        raise BadManifest(f"{raw['kind']!r} is not one of {KINDS}")
    settings = raw.get("settings") or []
    if not isinstance(settings, list) or any(not isinstance(r, dict) for r in settings):
        raise BadManifest("settings must be a list of rows")
    mark = None
    if directory is not None:
        candidate = directory / "mark.png"
        mark = candidate if candidate.is_file() else None
    return Plugin(
        id=raw["id"],
        name=raw["name"],
        kind=raw["kind"],
        unit=raw["unit"],
        label=raw.get("label"),
        enabled_row=raw.get("enabled_row"),
        accent=raw.get("accent"),
        status=raw.get("status"),
        mark=mark,
        settings=tuple(settings),
        built_in=built_in,
    )


def installed(directory: Path = DEFAULT_DIR) -> list[Plugin]:
    """Every readable manifest, by id.

    **One bad manifest does not stop the others.** A plugin somebody is
    halfway through packaging must not take the renderers down with it, so a
    manifest that will not parse is logged and skipped - loudly, because the
    author cannot see this log and the packager can.
    """
    try:
        entries = sorted(p for p in directory.iterdir() if p.is_dir())
    except OSError:
        return []
    found: dict[str, Plugin] = {}
    for entry in entries:
        manifest = entry / "plugin.json"
        if not manifest.is_file():
            continue
        try:
            plugin = parse(json.loads(manifest.read_text()), directory=entry)
        except (OSError, ValueError) as exc:
            logger.warning("plugins: ignoring %s: %s", manifest, exc)
            continue
        if plugin.id != entry.name:
            logger.warning(
                "plugins: ignoring %s: id %r does not match its directory",
                manifest, plugin.id,
            )
            continue
        if plugin.id in found:
            logger.warning("plugins: %s is installed twice, keeping the first", plugin.id)
            continue
        found[plugin.id] = plugin
    return list(found.values())
