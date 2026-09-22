# SPDX-License-Identifier: GPL-3.0-or-later
"""Per-renderer volume memory (criterion 5), George's decision 2026-09-07:
each renderer keeps its own volume, restored when it becomes active
again. The safe boot level (criterion 6, ADR-0018) applies once, at
boot, not on every takeover - a renderer with no remembered level gets
that same safe value as a starting point, not because a takeover resets
to it.

**Which renderers are managed is a declared capability
(`Adapter.capabilities.volume_managed`), not a name hardcoded here**
(criterion 3, fixed 2026-09-12 - this module used to hardcode
`MANAGED_RENDERERS = ("lms", "spotify")` directly). Today that's still
LMS and Spotify, not Bluetooth: both are observed and controlled through
the shared hardware mixer in a well-understood way, while Bluetooth's own
volume path mixes confirmed hardware-mixer control with an unconfirmed
software-attenuation regime below ~96% raw (see docs/findings/006-
bluetooth-volume-partial-software.md) - restoring a remembered level
there would write to a mixer that doesn't fully govern what the user
actually hears, until that's understood. The *reasoning* hasn't changed,
only where it's declared - `__main__.py` derives the managed set from
`adapters`, so a new renderer's own adapter file is the only place that
needs to say which side of this it's on.

Persisted to a small JSON file so it survives the daemon restarting, not
just within one run - cheap to add given the state is this small, and
"restored when active" reads as a durable property, not a
happens-to-still-be-in-RAM one.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from gexis_core.volume import db_to_raw, raw_to_db

logger = logging.getLogger("gexis_core.renderer_volume")

DEFAULT_STATE_PATH = Path("/var/lib/gexis-core/volume.json")


class RendererVolumeMemory:
    def __init__(self, path: Path = DEFAULT_STATE_PATH, *, managed_renderers: frozenset[str]) -> None:
        self._path = path
        self._managed_renderers = frozenset(managed_renderers)
        self._levels: dict[str, int] = self._load()

    def resolve_restore(
        self,
        renderer_id: str,
        *,
        boot_default: int,
        floor_db: float,
        ceiling_db: float | None = None,
    ) -> int | None:
        """The raw value to write to the hardware mixer when
        `renderer_id` becomes active, or None if this renderer's volume
        should be left untouched entirely (not in `managed_renderers` -
        see the module docstring on why Bluetooth is excluded today).

        `boot_default` (a remembered-nothing-yet fallback) is
        deliberately NOT subject to `floor_db` - that's a separate,
        already-confirmed-quiet value (ADR-0018's boot volume), not a
        degenerate remembered one. The floor only guards against
        restoring a *remembered* level so low it reads as broken rather
        than quiet - found necessary on hardware, 2026-09-08 (see
        HANDOFF.md and config.py's restore_volume_floor_db).
        """
        if renderer_id not in self._managed_renderers:
            return None
        raw = self.get(renderer_id)
        if raw is None:
            return boot_default
        if raw_to_db(raw) < floor_db:
            return db_to_raw(floor_db)
        # **And a ceiling** (ADR-0052 §1). Measured on the device: the level
        # rose 53 dB thirteen seconds after a boot, untouched, because the
        # first renderer to connect restored what it remembered - and
        # connecting Spotify put the DAC at 0.00 dB the same way (Finding
        # 045 §5, §7). A renderer may not make the device that loud on its
        # own; above this the user has to ask.
        if ceiling_db is not None and raw_to_db(raw) > ceiling_db:
            return db_to_raw(ceiling_db)
        return raw

    def _load(self) -> dict[str, int]:
        try:
            data = json.loads(self._path.read_text())
            return {k: int(v) for k, v in data.items() if k in self._managed_renderers}
        except FileNotFoundError:
            return {}
        except (ValueError, OSError) as exc:
            logger.warning("renderer_volume: failed to load %s: %s", self._path, exc)
            return {}

    def remember(self, renderer_id: str, raw: int) -> None:
        if renderer_id not in self._managed_renderers:
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
