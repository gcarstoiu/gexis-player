# SPDX-License-Identifier: GPL-3.0-or-later
"""**What a backup restores, by Settings section** (ADR-0131 amended
2026-10-18; George: *"Each item should be on its own line with a checkmark
grouped by the section the setting is in"*).

Each setting the backup stores, by its row's label - under the subgroup it
sits in, when it has one - in the section Settings shows it in, in
Settings' own order; then what the backup carries besides settings (a
Spotify sign-in, paired devices, playlists...) in the section that owns it.
A plugin's switch, when the backup has it on, is under Plugins; a plugin's
own rows are in its area, after its name. Rows nobody sees - internal keys,
rows Settings never shows, actions - are left out: the list says what the
person will find again, not how the store is laid out.

Pure: the registry and the plugins are passed in.
"""
from __future__ import annotations

from typing import Iterable

SKIPPED_TYPES = {"group", "action", "readonly", "document"}
PLUGINS = "plugins"


def sections(values: dict, carried: Iterable[tuple[str, str]], registry: list[dict],
             plugins: Iterable = ()) -> list[dict]:
    """`values`: the backup's stored settings. `carried`: (section id, text)
    for what it holds besides settings. Returns `[{"id", "label", "items"}]`,
    sections with nothing left out."""
    items: dict[str, list[str]] = {g["id"]: [] for g in registry}
    labels = {g["id"]: g.get("label") or g["id"] for g in registry}
    for group in registry:
        sub = None
        for row in group["rows"]:
            if row.get("type") == "group":
                sub = row.get("label")
                continue
            key = row.get("key")
            shown_as = row.get("shownAs")
            if shown_as and row.get("surfaced") is False and key in values:
                # A row drawn as another (the two navigation switches, under
                # Navigation): that one, once.
                other = next((r for r in group["rows"] if r.get("key") == shown_as), None)
                if other is not None:
                    label = other.get("label") or shown_as
                    line = f"{sub} · {label}" if sub and sub != label else label
                    if line not in items[group["id"]]:
                        items[group["id"]].append(line)
                continue
            if (not key or key not in values or row.get("type") in SKIPPED_TYPES
                    or row.get("surfaced") is False):
                continue
            label = row.get("label") or key
            items[group["id"]].append(f"{sub} · {label}" if sub and sub != label else label)
    for plugin in plugins:
        if values.get(f"{plugin.id}.enabled") is True and PLUGINS in items:
            items[PLUGINS].append(f"{plugin.name}, switched on")
        area = plugin.area if plugin.area in items else None
        for row in plugin.settings:
            key = f"{plugin.id}.{row.get('key')}"
            if (area is None or key not in values or row.get("type") in SKIPPED_TYPES
                    or row.get("secret") or row.get("key") == "enabled"):
                continue
            items[area].append(f"{plugin.name} · {row.get('label') or row.get('key')}")
    for section, text in carried:
        if section in items:
            items[section].append(text)
    return [{"id": g["id"], "label": labels[g["id"]], "items": items[g["id"]]}
            for g in registry if items[g["id"]]]
