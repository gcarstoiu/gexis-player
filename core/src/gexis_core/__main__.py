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
    # yet) gets that same safe level as its starting point.
    volume_memory = RendererVolumeMemory()

    async def restore_volume(renderer_id: str) -> None:
        # Bluetooth (or anything else not volume-managed) comes back as
        # None here and is left alone entirely - not just "not
        # remembered," genuinely untouched. Bug found on hardware,
        # 2026-09-08: this used to fall through to the boot-safe default
        # (-90dB) for *any* unmanaged renderer, so every Bluetooth
        # acquisition silently muted it regardless of the phone's own
        # volume - the actual cause of "Bluetooth outputs no sound" that
        # session, nothing to do with bluealsa-aplay or routing.
        # Bluetooth's own volume path isn't understood well enough yet
        # to manage here at all (Finding 006).
        raw = volume_memory.resolve_restore(
            renderer_id,
            boot_default=config.boot_volume_steps,
            floor_db=config.restore_volume_floor_db,
        )
        if raw is None:
            logger.debug("volume: %s is not volume-managed, leaving mixer as-is", renderer_id)
            return
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
