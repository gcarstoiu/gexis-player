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

import hashlib

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
#: **Where a plugin's rows go in Settings** (George, 2026-09-30: "Let's add
#: it. It would keep things organised"): a Settings page, as its name reads,
#: to the registry's id for it. Optional in a manifest; absent, the kind
#: decides, as it always did - a renderer in Sources, a service in System.
AREAS = {
    "audio": "audio", "sources": "sources", "handoff": "handoff",
    "display": "display", "enrichment": "enrich", "device": "device", "system": "system",
}


def default_area(kind: str) -> str:
    return "sources" if kind == "renderer" else "system"

#: What a row's `env` may be named (ADR-0088). Duplicated from
#: `plugin_env.NAME` deliberately: importing it here would make the manifest
#: reader depend on the exporter, and this module is read by things that never
#: write a file.
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class Plugin:
    """One manifest, validated. Presentation and identity only - what it can
    *do* arrives in `hello` at runtime."""

    id: str
    name: str
    kind: str
    unit: str
    #: The registry id of the Settings page its rows go to (`AREAS`).
    area: str = ""
    #: The moOde-compatible status line (`metadata_file.py`). Absent means the
    #: file says nothing for this renderer, which is what it did before any of
    #: this existed.
    label: str | None = None
    #: A CSS colour for the UI's accent. Absent means the panel's default.
    accent: str | None = None
    #: The waiting screen's second line - "Listening", "Pairable".
    status: str | None = None
    #: A web page of its own on this device, by port (ADR-0114: the Beszel
    #: hub's 8095). Its switch shows `http://<name>.local:<port>`.
    port: int | None = None
    #: Its group goes first on its page rather than last (George, 2026-10-03:
    #: the Lyrion server at the top of Sources, the client beneath it).
    first: bool = False
    #: What Remove deletes besides the software, said in its confirmation
    #: (ADR-0115 decision 14); absent, the settings stay and it says so.
    removes: str | None = None
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
    #: **ADR-0098: what the user must read before switching it on**, shown as
    #: a confirmation by the panel.
    notice: str | None = None
    #: **One line on what it is** (ADR-0128): the setup step's description.
    summary: str | None = None
    #: **ADR-0129: a service that connects somewhere** - its switch says
    #: *Connected*, *Connecting* or *Not connected*, read by the core from the
    #: connections its unit's user holds.
    connection: bool = False
    #: True for the three this repository ships. They are not special in how
    #: they are read - only in who wrote them.
    built_in: bool = False
    #: **ADR-0106: uploaded by the user**, not part of Gexis Player. Run under
    #: the player's own sandboxed unit; the screen tags it so.
    uploaded: bool = False

    def to_json(self) -> dict:
        """What the panel needs to draw this source without knowing it."""
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "accent": self.accent,
            "status": self.status,
            "mark": self.mark_url(),
        }

    def mark_url(self) -> str | None:
        """**The URL names the file's content, not just the plugin** (found
        2026-09-26). The mark is served with a day's `max-age`, so a mark
        replaced under the same URL stayed cached on the panel and on phones:
        George's panel went on drawing the old Plexamp arrow after the file was
        swapped for Plex's chevron. A new file is a new URL, so the long cache is
        safe and nothing has to be told to reload."""
        if self.mark is None:
            return None
        try:
            digest = hashlib.sha256(self.mark.read_bytes()).hexdigest()[:12]
        except OSError:
            return f"/plugins/{self.id}/mark"
        return f"/plugins/{self.id}/mark?v={digest}"


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
    area = raw.get("area")
    if area is not None and area not in AREAS:
        raise BadManifest(f"{area!r} is not one of {tuple(AREAS)}")
    settings = raw.get("settings") or []
    if not isinstance(settings, list) or any(not isinstance(r, dict) for r in settings):
        raise BadManifest("settings must be a list of rows")
    for row in settings:
        # ADR-0088. Refused here rather than dropped at export: a variable name
        # the shell cannot carry is a typo, and a plugin whose credential
        # silently never reaches its process is the hardest kind of broken to
        # see - it starts, it runs, it just never authenticates.
        name = row.get("env")
        if name is not None and (not isinstance(name, str) or not ENV_NAME.match(name)):
            raise BadManifest(f"{name!r} is not a usable environment variable name")
    mark = None
    if directory is not None:
        candidate = directory / "mark.png"
        mark = candidate if candidate.is_file() else None
    return Plugin(
        id=raw["id"],
        name=raw["name"],
        kind=raw["kind"],
        unit=raw["unit"],
        area=AREAS[area] if area is not None else default_area(raw["kind"]),
        label=raw.get("label"),
        enabled_row=raw.get("enabled_row"),
        accent=raw.get("accent"),
        status=raw.get("status"),
        port=raw["port"] if isinstance(raw.get("port"), int) and 0 < raw["port"] < 65536 else None,
        first=raw.get("first") is True,
        removes=raw["removes"] if isinstance(raw.get("removes"), str) else None,
        notice=raw.get("notice"),
        summary=raw["summary"] if isinstance(raw.get("summary"), str) else None,
        connection=raw.get("connection") is True and raw["kind"] == "service",
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
