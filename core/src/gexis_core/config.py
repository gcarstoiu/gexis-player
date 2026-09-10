# SPDX-License-Identifier: GPL-3.0-or-later
"""Core configuration.

Loaded from a TOML file rather than baked into the package, so values like
the safe boot volume are a configuration change, not a code change - ADR-
0018 is explicit that the specific safe level "is a configuration value,
not a decision for this record", i.e. this file, not arbitration.py.

stdlib `tomllib` (3.11+, read-only) rather than PyYAML: one less pinned
dependency, one less wheel to trust, for a format we only ever read.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("/etc/gexis/core.toml")


@dataclass(frozen=True)
class Config:
    # ALSA mixer steps, 0-240 (ADR-0018: 240 steps of 0.5dB, 0=mute,
    # 240=0dB). Confirmed by George, 2026-09-06 (HANDOFF.md) - -90dB,
    # deliberately quiet. This is the *boot* default only - it is not
    # subject to restore_volume_floor_db below, on purpose (see
    # __main__.py's restore_volume).
    boot_volume_steps: int = 60

    # dB floor applied only when *restoring a renderer's own remembered
    # volume* (criterion 5, per-renderer memory) - never to the boot
    # default above. Found necessary on hardware, 2026-09-08: a
    # renderer with no memory yet falling back to the boot level (-90dB)
    # was indistinguishable from a broken renderer - inaudible, no
    # obvious cause, nothing to diagnose (the exact "state the user
    # cannot account for" ADR-0010/0018 both warn against). PLACEHOLDER
    # value - a reasonable "clearly audible" floor, not confirmed by
    # George. See HANDOFF.md.
    restore_volume_floor_db: float = -40.0

    mixer_name: str = "DAC"

    # LMS runs on its own machine, not on gexis - there is no sane
    # localhost default here (unlike go-librespot, which is local).
    # image/stage-gexis/03-core/files/core.toml overrides this for the
    # actual deployment; the class default below is only a fallback for
    # ad hoc/test use off the image.
    lms_host: str = "192.168.178.188"
    lms_port: int = 9000
    lms_player_name: str = "gexis"

    go_librespot_host: str = "127.0.0.1"
    go_librespot_port: int = 3678

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG_PATH) -> "Config":
        if not path.exists():
            return cls()
        data = tomllib.loads(path.read_text())
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"{path}: unknown config key(s): {sorted(unknown)}")
        return cls(**data)
