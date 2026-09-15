# SPDX-License-Identifier: GPL-3.0-or-later
"""The settings registry and its API behaviour (ADR-0035).

`settings_registry.json` is the executable form of ADR-0022's inventory,
keyed by the design's own keys. A row is *wired* when some feature reads its
value; only wired rows accept writes. Adding a setting is one row here plus
the code that reads it, in the same change as its feature.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Callable

from gexis_core.settings import SettingsStore

REGISTRY_PATH = Path(__file__).with_name("settings_registry.json")

SETTABLE = {"toggle", "choice", "number", "text"}
TYPES = SETTABLE | {"readonly", "action", "group"}
TEXT_MAX = 500


class UnknownSetting(KeyError):
    pass


class NotWired(Exception):
    pass


class InvalidValue(ValueError):
    pass


class NotSettable(Exception):
    pass


def load_registry(path: Path = REGISTRY_PATH) -> list[dict]:
    groups = json.loads(path.read_text())
    seen: set[str] = set()
    for group in groups:
        for row in group["rows"]:
            kind = row["type"]
            if kind not in TYPES:
                raise ValueError(f"{row}: unknown row type {kind!r}")
            if kind == "group":
                continue
            key = row["key"]
            if key in seen:
                raise ValueError(f"duplicate setting key {key!r}")
            seen.add(key)
            if kind == "number" and ("min" not in row or "max" not in row):
                raise ValueError(f"{key}: a number row needs min and max (ADR-0035)")
            if kind == "choice" and not row.get("options"):
                raise ValueError(f"{key}: a choice row needs options")
    return groups


def validate(row: dict, value: Any) -> Any:
    kind = row["type"]
    if kind not in SETTABLE:
        raise NotSettable(f"{row['key']} is {kind} and takes no value")
    if kind == "toggle":
        if not isinstance(value, bool):
            raise InvalidValue("expected true or false")
    elif kind == "choice":
        if value not in row["options"]:
            raise InvalidValue(f"expected one of {row['options']}")
    elif kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise InvalidValue("expected a number")
        if not row["min"] <= value <= row["max"]:
            raise InvalidValue(f"expected {row['min']} to {row['max']}")
    elif kind == "text":
        if not isinstance(value, str):
            raise InvalidValue("expected text")
        value = value.strip()
        if len(value) > TEXT_MAX:
            raise InvalidValue(f"at most {TEXT_MAX} characters")
    return value


class Settings:
    """`defaults` maps a key to a callable giving its value from deployment
    config or the running system; it overrides the registry default, and a
    stored value overrides both (ADR-0035 §4). `wired` maps a key to a callback
    run after a write, or None when the feature reads the store itself."""

    def __init__(
        self,
        store: SettingsStore,
        *,
        registry: list[dict] | None = None,
        defaults: dict[str, Callable[[], Any]] | None = None,
        wired: dict[str, Callable[[Any], None] | None] | None = None,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        self._store = store
        self._groups = registry if registry is not None else load_registry()
        self._rows = {r["key"]: r for g in self._groups for r in g["rows"] if r["type"] != "group"}
        self._defaults = defaults or {}
        self._wired = wired or {}
        self._on_change = on_change
        unknown = (set(self._defaults) | set(self._wired)) - set(self._rows)
        if unknown:
            raise ValueError(f"not in the registry: {sorted(unknown)}")

    def row(self, key: str) -> dict:
        try:
            return self._rows[key]
        except KeyError:
            raise UnknownSetting(key) from None

    def value(self, key: str) -> Any:
        row = self.row(key)
        stored = self._store.get(key, _MISSING)
        if stored is not _MISSING:
            return stored
        if key in self._defaults:
            return self._defaults[key]()
        return row.get("default")

    def to_json(self) -> list[dict]:
        groups = []
        for group in self._groups:
            rows = []
            for row in group["rows"]:
                if row["type"] == "group":
                    rows.append(row)
                    continue
                public = {k: v for k, v in row.items() if k != "default"}
                public["value"] = self.value(row["key"])
                public["wired"] = row["key"] in self._wired
                rows.append(public)
            groups.append({**group, "rows": rows})
        return groups

    def set(self, key: str, value: Any) -> Any:
        row = self.row(key)
        if row["type"] not in SETTABLE:
            raise NotSettable(f"{key} is {row['type']} and takes no value")
        if key not in self._wired:
            raise NotWired(f"{key} is not wired yet")
        value = validate(row, value)
        if value == "" and row["type"] == "text":
            # Clearing a text value falls back to deployment config (ADR-0035 §4).
            self._store.delete(key)
            value = self.value(key)
        else:
            self._store.set(key, value)
        callback = self._wired[key]
        if callback is not None:
            callback(value)
        if self._on_change is not None:
            self._on_change()
        return value

    def run(self, key: str) -> None:
        row = self.row(key)
        if row["type"] != "action":
            raise NotSettable(f"{key} is {row['type']}, not an action")
        if row.get("navigation") or key not in self._wired:
            raise NotWired(f"{key} is not wired yet")
        callback = self._wired[key]
        if callback is not None:
            callback(None)


_MISSING = object()
