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
from gexis_core.renderer_volume import RendererVolumeMemory
from gexis_core.volume import VolumeBridge, set_raw

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("gexis_core")


async def main() -> None:
    config = Config.load()

    lms = LmsAdapter(config.lms_host, config.lms_port, config.lms_player_name)
    spotify = SpotifyAdapter(config.go_librespot_host, config.go_librespot_port)
    bluetooth = BluetoothAdapter()
    adapters = {BASE_RENDERER: lms, "spotify": spotify, "bluetooth": bluetooth}

    # George's decision, 2026-09-07: each renderer keeps its own volume,
    # restored when it becomes active - not reset to the boot-safe level
    # on every takeover. A renderer with no remembered level (never used
    # yet, or Bluetooth, out of scope for now - see renderer_volume.py)
    # gets that same safe level as its starting point.
    volume_memory = RendererVolumeMemory()

    async def restore_volume(renderer_id: str) -> None:
        raw = volume_memory.get(renderer_id)
        if raw is None:
            raw = config.boot_volume_steps
        logger.info("volume: restoring %s to %s/240", renderer_id, raw)
        await set_raw(config.mixer_name, raw)

    supervisor = Supervisor(
        adapters, device_busy=lambda: alsa.device_busy(), restore_volume=restore_volume
    )

    def make_on_acquire(renderer_id: str):
        def _on_acquire() -> None:
            asyncio.create_task(supervisor.acquire(renderer_id))

        return _on_acquire

    volume_bridge = VolumeBridge(
        config.mixer_name,
        spotify,
        volume_memory=volume_memory,
        get_active_renderer=lambda: supervisor.active,
    )

    logger.info("gexis-core starting: adapters=%s", list(adapters))
    await asyncio.gather(
        *(adapter.run(make_on_acquire(rid)) for rid, adapter in adapters.items()),
        volume_bridge.run(),
    )


if __name__ == "__main__":
    asyncio.run(main())
