# SPDX-License-Identifier: GPL-3.0-or-later
"""SQLite-backed settings store (Phase 3 criterion 5).

Generic key-value persistence for future user-editable settings
(ADR-0022's inventory - output mode, boot volume level, skin corpus,
idle timeouts, device name, Bluetooth trusted devices, and more still to
come from Phase 4 onward). Holds no real setting yet: none of ADR-0022's
inventory has a UI to edit it before Phase 4 exists. Building the storage
mechanism now, ahead of what will use it, matches how criteria 1-4 built
daemon-side infrastructure (the state model, the WebSocket, the metadata
file) before a UI exists to consume any of it.

JSON-encoded values in one table, not one column per setting: ADR-0022's
inventory is heterogeneous (toggles, choices, sliders, free text, and at
least one list - Bluetooth's trusted-device list) and will keep growing -
a new setting should never need a schema migration, only a new key.

**Distinct from config.py's `Config`**: that is deployment-time, baked
into the image and edited by hand over SSH (TOML, `image/stage-gexis/
03-core/files/core.toml`). This is runtime state, meant to be changed by
a user through a future settings screen (ADR-0022: "Settings are a
separate screen") and to survive exactly what the criterion names - a
service restart, not a rebuild.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger("gexis_core.settings")

DEFAULT_PATH = Path("/var/lib/gexis-core/settings.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
"""


class SettingsStore:
    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def get(self, key: str, default: Any = None) -> Any:
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return default
        return json.loads(row[0])

    def set(self, key: str, value: Any) -> None:
        self._conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)),
        )
        self._conn.commit()

    def delete(self, key: str) -> None:
        self._conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
