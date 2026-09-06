"""Arbitration core entrypoint (`python -m gexis_core`). Runs the
supervisor and every adapter for the process lifetime - this is
`gexis-core.service` (image/stage-gexis/03-core).
"""
from __future__ import annotations

import asyncio
import logging

from gexis_core import alsa
from gexis_core.adapters.bluetooth import BluetoothAdapter
from gexis_core.adapters.lms import LmsAdapter
from gexis_core.adapters.spotify import SpotifyAdapter
from gexis_core.arbitration import BASE_RENDERER, Supervisor
from gexis_core.config import Config
from gexis_core.volume import VolumeBridge

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("gexis_core")


async def main() -> None:
    config = Config.load()

    lms = LmsAdapter(config.lms_host, config.lms_port, config.lms_player_name)
    spotify = SpotifyAdapter(config.go_librespot_host, config.go_librespot_port)
    bluetooth = BluetoothAdapter()
    adapters = {BASE_RENDERER: lms, "spotify": spotify, "bluetooth": bluetooth}

    supervisor = Supervisor(
        adapters, device_busy=lambda: alsa.device_busy()
    )

    def make_on_acquire(renderer_id: str):
        def _on_acquire() -> None:
            asyncio.create_task(supervisor.acquire(renderer_id))

        return _on_acquire

    volume_bridge = VolumeBridge(config.mixer_name, spotify)

    logger.info("gexis-core starting: adapters=%s", list(adapters))
    await asyncio.gather(
        *(adapter.run(make_on_acquire(rid)) for rid, adapter in adapters.items()),
        volume_bridge.run(),
    )


if __name__ == "__main__":
    asyncio.run(main())
