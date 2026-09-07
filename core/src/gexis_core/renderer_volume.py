"""Per-renderer volume memory (criterion 5), George's decision 2026-09-07:
each renderer keeps its own volume, restored when it becomes active
again. The safe boot level (criterion 6, ADR-0018) applies once, at
boot, not on every takeover - a renderer with no remembered level gets
that same safe value as a starting point, not because a takeover resets
to it.

**Scope: LMS and Spotify only.** Both are observed and controlled
through the shared hardware mixer in a well-understood way. Bluetooth is
deliberately left out here - its own volume path mixes confirmed
hardware-mixer control with an unconfirmed software-attenuation regime
below ~96% raw (see docs/findings/006-bluetooth-volume-partial-
software.md). Restoring a remembered level for Bluetooth would write to
a mixer that doesn't fully govern what the user actually hears, until
that's understood.

Persisted to a small JSON file so it survives the daemon restarting, not
just within one run - cheap to add given the state is this small, and
"restored when active" reads as a durable property, not a
happens-to-still-be-in-RAM one.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger("gexis_core.renderer_volume")

DEFAULT_STATE_PATH = Path("/var/lib/gexis-core/volume.json")
MANAGED_RENDERERS = ("lms", "spotify")


class RendererVolumeMemory:
    def __init__(self, path: Path = DEFAULT_STATE_PATH) -> None:
        self._path = path
        self._levels: dict[str, int] = self._load()

    def _load(self) -> dict[str, int]:
        try:
            data = json.loads(self._path.read_text())
            return {k: int(v) for k, v in data.items() if k in MANAGED_RENDERERS}
        except FileNotFoundError:
            return {}
        except (ValueError, OSError) as exc:
            logger.warning("renderer_volume: failed to load %s: %s", self._path, exc)
            return {}

    def remember(self, renderer_id: str, raw: int) -> None:
        if renderer_id not in MANAGED_RENDERERS:
            return
        if self._levels.get(renderer_id) == raw:
            return
        self._levels[renderer_id] = raw
        self._save()

    def get(self, renderer_id: str) -> int | None:
        return self._levels.get(renderer_id)

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._levels))
        except OSError as exc:
            logger.warning("renderer_volume: failed to persist %s: %s", self._path, exc)
