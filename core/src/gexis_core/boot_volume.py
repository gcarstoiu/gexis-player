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
from gexis_core.volume import set_raw

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("gexis_core.boot_volume")


async def _main() -> int:
    config = Config.load()
    logger.info(
        "boot volume: setting %r to %s/240 (fixed safe level, not restored)",
        config.mixer_name,
        config.boot_volume_steps,
    )
    await set_raw(config.mixer_name, config.boot_volume_steps)
    return 0


def main() -> None:
    sys.exit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
