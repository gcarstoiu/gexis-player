# SPDX-License-Identifier: GPL-3.0-or-later
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
from gexis_core.arbitration import Supervisor
from gexis_core.config import Config
from gexis_core.renderer_volume import RendererVolumeMemory
from gexis_core import volume
from gexis_core.volume import DummyMixerBridge, VolumeBridge, db_to_raw, get_raw, raw_to_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("gexis_core")


def unmanaged_floor_raw(current: int | None, floor_db: float) -> int | None:
    """The raw value to bump an *unmanaged* renderer's shared mixer to,
    or None if it's already fine as-is.

    Not volume-managed (e.g. Bluetooth, Finding 006) means "not
    remembered or restored" - it does NOT mean "the mixer can be left at
    whatever the previous renderer happened to set." Found on hardware,
    2026-09-08: George reported Bluetooth "silent even at max" - AVRCP
    volume updates were confirmed reaching the hardware mixer correctly
    once the phone's slider was actively moved (bluealsa's own log:
    "Updating A2DP volume: ... [-4.80 dB]"), but nothing set a starting
    level on acquire, so a quiet level left by whichever renderer was
    active before carried straight over until the user happened to nudge
    their phone's slider. One-directional: bump up to the floor if
    below it, never push down or fight a level that's already
    reasonable - not "managing" the renderer's volume, just refusing to
    hand it an inaudible starting point.
    """
    if current is None or raw_to_db(current) >= floor_db:
        return None
    return db_to_raw(floor_db)


def make_restore_volume(config: Config, volume_memory: RendererVolumeMemory, volume_bridge: VolumeBridge):
    async def restore_volume(renderer_id: str) -> None:
        # George's decision, 2026-09-07: each renderer keeps its own
        # volume, restored when it becomes active - not reset to the
        # boot-safe level on every takeover. A renderer with no
        # remembered level (never used yet) gets that same safe level as
        # its starting point.
        #
        # Writes go through volume_bridge.write_hardware(), not set_raw()
        # directly, so this doesn't arrive on `alsactl monitor` looking
        # like an external change - found on hardware, 2026-09-08 (see
        # write_hardware's own docstring): a direct set_raw() here was
        # getting echoed straight back out to Spotify on every
        # acquisition, racing go-librespot's own volume report.
        raw = volume_memory.resolve_restore(
            renderer_id,
            boot_default=config.boot_volume_steps,
            floor_db=config.restore_volume_floor_db,
        )
        if raw is not None:
            logger.info("volume: restoring %s to %s/240", renderer_id, raw)
            await volume_bridge.write_hardware(raw)
            return

        # Not volume-managed (None above) - genuinely not remembered or
        # restored, not the boot-safe-default bug fixed 2026-09-08
        # (every Bluetooth acquisition silently muted to -90dB
        # regardless of the phone's own volume). Bluetooth's own volume
        # path isn't understood well enough yet to manage here at all
        # (Finding 006) - but see unmanaged_floor_raw for why "not
        # managed" still isn't "leave it at whatever's there."
        current = await get_raw(config.mixer_name)
        floor_raw = unmanaged_floor_raw(current, config.restore_volume_floor_db)
        if floor_raw is None:
            logger.debug("volume: %s is not volume-managed, leaving mixer as-is", renderer_id)
            return
        logger.info(
            "volume: %s is not volume-managed, but the mixer was left at "
            "%.1fdB - bumping to the %.1fdB floor rather than starting silent",
            renderer_id,
            raw_to_db(current),
            config.restore_volume_floor_db,
        )
        await volume_bridge.write_hardware(floor_raw)

    return restore_volume


async def main() -> None:
    config = Config.load()

    lms = LmsAdapter(config.lms_host, config.lms_port, config.lms_player_name)
    spotify = SpotifyAdapter(config.go_librespot_host, config.go_librespot_port)
    bluetooth = BluetoothAdapter()
    adapters = {"lms": lms, "spotify": spotify, "bluetooth": bluetooth}

    volume_memory = RendererVolumeMemory()

    # Constructed before Supervisor/restore_volume, which both need to
    # write through it (write_hardware()) rather than around it - its
    # get_active_renderer callback references `supervisor` by closure, so
    # it's fine that `supervisor` itself doesn't exist yet here; nothing
    # calls the callback until well after `supervisor` is assigned below.
    volume_bridge = VolumeBridge(
        config.mixer_name,
        spotify,
        volume_memory=volume_memory,
        get_active_renderer=lambda: supervisor.active,
    )
    restore_volume = make_restore_volume(config, volume_memory, volume_bridge)

    supervisor = Supervisor(
        adapters,
        device_busy=lambda renderer_id: alsa.device_held_by(adapters[renderer_id].unit_name),
        restore_volume=restore_volume,
    )

    def make_on_acquire(renderer_id: str):
        def _on_acquire() -> None:
            asyncio.create_task(supervisor.acquire(renderer_id))

        return _on_acquire

    def make_on_release(renderer_id: str):
        def _on_release() -> None:
            asyncio.create_task(supervisor.relinquish(renderer_id))

        return _on_release
    # B2, George's decision 2026-09-08: LMS and Bluetooth each write to
    # their own private snd-dummy control (image/stage-gexis/00-alsa's
    # modprobe config), not the real DAC directly - these mirror that
    # control onto real hardware only while its renderer is active. See
    # volume.py's module docstring.
    lms_volume_bridge = DummyMixerBridge(
        "lms",
        volume.DUMMY_CARD_LMS,
        volume.DUMMY_CONTROL,
        config.mixer_name,
        volume_memory=volume_memory,
        get_active_renderer=lambda: supervisor.active,
    )
    bluetooth_volume_bridge = DummyMixerBridge(
        "bluetooth",
        volume.DUMMY_CARD_BLUETOOTH,
        volume.DUMMY_CONTROL,
        config.mixer_name,
        volume_memory=volume_memory,
        get_active_renderer=lambda: supervisor.active,
    )

    logger.info("gexis-core starting: adapters=%s", list(adapters))
    await asyncio.gather(
        *(
            adapter.run(make_on_acquire(rid), make_on_release(rid))
            for rid, adapter in adapters.items()
        ),
        volume_bridge.run(),
        lms_volume_bridge.run(),
        bluetooth_volume_bridge.run(),
    )


if __name__ == "__main__":
    asyncio.run(main())
