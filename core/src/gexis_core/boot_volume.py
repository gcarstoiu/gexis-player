# SPDX-License-Identifier: GPL-3.0-or-later
"""Boot volume (criterion 6): set the mixer to a fixed safe level on every
boot. Not restored from the previous session - ADR-0018 is explicit that
`alsactl` state must not be used to restore volume across boots ("a device
that was left loud and boots into playback is a real hazard").

Standalone entrypoint (`python -m gexis_core.boot_volume`), not part of
the core daemon's own startup: this needs to run and exit before anything
else touches the mixer, as its own systemd unit ordered before the
renderers (see image/stage-gexis/03-core/files/gexis-boot-volume.service),
not as a side effect of the core daemon happening to start early.
"""
from __future__ import annotations

import asyncio
import logging
import sys

from gexis_core.config import Config
from gexis_core.settings import SettingsStore
from gexis_core.volume import db_to_raw, set_raw

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("gexis_core.boot_volume")


def _chosen_level(config: Config) -> tuple[int, str]:
    """The level to write, and where it came from.

    **ADR-0022's `boot_volume` row, wired 2026-09-23.** The row is in dB,
    which is the unit a person can reason about; `core.toml`'s
    `boot_volume_steps` stays as the fallback and the row's own default.

    Read straight from the store rather than through `settings_registry`:
    this runs before the daemon, as its own unit, and needs no registry,
    no defaults and no validation beyond "is it a number in range". A
    settings file that cannot be read must not stop the safe level being
    written - that is the whole point of this unit - so every failure
    falls back to the configured value.
    """
    try:
        store = SettingsStore()
        try:
            stored = store.get("boot_volume")
        finally:
            store.close()
    except Exception as exc:  # noqa: BLE001 - the safe level still gets written
        logger.warning("boot volume: settings unreadable (%s), using core.toml", exc)
        return config.boot_volume_steps, "core.toml"
    if stored is None:
        return config.boot_volume_steps, "core.toml default"
    try:
        db = float(stored)
    except (TypeError, ValueError):
        logger.warning("boot volume: %r is not a number, using core.toml", stored)
        return config.boot_volume_steps, "core.toml"
    return db_to_raw(db), f"settings, {db:g} dB"


async def _main() -> int:
    config = Config.load()
    level, source = _chosen_level(config)
    logger.info(
        "boot volume: setting %r to %s/240 from %s (fixed safe level, not restored)",
        config.mixer_name,
        level,
        source,
    )
    await set_raw(config.mixer_name, level)
    return 0


def main() -> None:
    sys.exit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
