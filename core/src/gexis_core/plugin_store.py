# SPDX-License-Identifier: GPL-3.0-or-later
"""**One store for every plugin** (ADR-0169).

The Plugins page lists what is added to this player; *Add plugins* lists the
rest: ours not added beside the catalogue's. An uploaded or catalogue plugin is
added while its package is installed. Ours ship with the player, so *added* is
a record of its own, `_plugins_added` in the settings store (a backup carries
it): *Add* sets it and switches the plugin on, *Remove* switches it off,
deletes what it downloaded and clears it. The visualiser skins are one of ours
here, under their own id.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable

#: The record, a list of ids; absent until setup or the first start after an
#: update writes it.
ADDED = "_plugins_added"
#: The visualiser skins, which are a switch and a pack rather than a manifest.
SKINS = "visualiser-skins"
SKINS_TILE = {
    "id": SKINS, "name": "Visualiser skins", "kind": "service", "area": "display",
    "summary": "The meters and spectra drawn for this screen's size.",
}


def optional(installed: Iterable) -> list:
    """Ours that may be added or removed: neither the three sources the
    player is built around (George, 2026-10-30) nor anyone else's."""
    return [p for p in installed if not getattr(p, "built_in", False) and not getattr(p, "uploaded", False)]


def first(ids: Iterable[str], *, on: Callable[[str], bool], downloaded: Callable[[str], bool],
          skins: bool) -> list[str]:
    """What an updated player starts with (George, 2026-10-30): each of ours
    that is on, or has downloaded its software; the rest wait in *Add
    plugins*."""
    added = {pid for pid in ids if on(pid) or downloaded(pid)}
    if skins:
        added.add(SKINS)
    return sorted(added)


def read(value: object) -> set[str] | None:
    """The record as stored, or None when there is none yet."""
    if not isinstance(value, list):
        return None
    return {pid for pid in value if isinstance(pid, str)}


def tiles(plugins: Iterable, added: set[str], *, skins: bool = True) -> list[dict]:
    """Ours for *Add plugins*, with whether each is added: the page shows the
    rest as tiles."""
    out = [{"id": p.id, "name": p.name, "kind": p.kind, "area": p.area, "summary": p.summary,
            "tag": p.tag, "notice": p.notice, "added": p.id in added} for p in plugins]
    if skins:
        out.append({**SKINS_TILE, "tag": None, "notice": None, "added": SKINS in added})
    return sorted(out, key=lambda t: t["name"].lower())
