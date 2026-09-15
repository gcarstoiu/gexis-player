# SPDX-License-Identifier: GPL-3.0-or-later
"""Arbitration core entrypoint (`python -m gexis_core`). Runs the
supervisor and every adapter for the process lifetime - this is
`gexis-core.service` (image/stage-gexis/03-core).
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from gexis_core import alsa
from gexis_core.adapters.base import VolumeMechanism
from gexis_core.adapters.bluetooth import BluetoothAdapter
from gexis_core.adapters.lms import LmsAdapter
from gexis_core.adapters.spotify import SpotifyAdapter
from gexis_core.arbitration import Supervisor
from gexis_core.config import Config
from gexis_core.metadata_file import MetadataFileWriter
from gexis_core.renderer_volume import RendererVolumeMemory
from gexis_core.settings import SettingsStore
from gexis_core.state import StateStore
from gexis_core.volume import (
    DUMMY_CONTROL,
    DummyMixerBridge,
    VolumeBridge,
    db_to_raw,
    get_raw,
    percent_to_raw,
    raw_to_db,
)
from gexis_core.wsserver import StateServer

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

    # Criterion 5: opened for the process lifetime, schema created if
    # missing. Nothing reads or writes a real setting through it yet -
    # ADR-0022's inventory (output mode, boot volume, device name, ...)
    # has no UI to change any of it before Phase 4 - but the store itself
    # is exercised for real here, not just in unit tests: this is what
    # proves the DB file and schema actually come up clean on the image.
    settings_store = SettingsStore()
    logger.info("settings: store ready at %s", settings_store.path)

    lms = LmsAdapter(config.lms_host, config.lms_port, config.lms_player_name)
    spotify = SpotifyAdapter(config.go_librespot_host, config.go_librespot_port)
    bluetooth = BluetoothAdapter()
    adapters = {"lms": lms, "spotify": spotify, "bluetooth": bluetooth}

    # Criterion 3, 2026-09-12: which renderers are volume-managed is a
    # declared capability (adapters/base.py), not a name hardcoded here -
    # this used to be renderer_volume.py's own MANAGED_RENDERERS tuple.
    volume_memory = RendererVolumeMemory(
        managed_renderers=frozenset(
            rid for rid, adapter in adapters.items() if adapter.capabilities.volume_managed
        )
    )

    # Phase 3 criteria 1-2: the normalised playback model plus each
    # adapter's declared capabilities, published over the state WebSocket.
    # Wired to the supervisor's active-renderer changes and each adapter's
    # own metadata/availability reports below - constructed before
    # Supervisor for the same closure reason as volume_bridge (its
    # callbacks reference `supervisor`, assigned later).
    state_store = StateStore(
        {rid: adapter.capabilities for rid, adapter in adapters.items()},
        handoff_exempt_pairs=config.handoff_exempt_pairs,
    )

    # Criterion 4: moOde-compatible metadata file, subscribed the same way
    # StateServer is - a plain callback on every published state change.
    metadata_file_writer = MetadataFileWriter(Path(config.metadata_file_path))
    state_store.subscribe(metadata_file_writer.write)

    # Criterion 3, 2026-09-12: which volume-bridging mechanism a renderer
    # needs is a declared capability (VolumeMechanism), not hardcoded by
    # name here - this section used to construct one VolumeBridge for
    # "spotify" and two DummyMixerBridge instances for "lms"/"bluetooth"
    # by hand.
    #
    # Exactly one SOFTWARE_API adapter is assumed below - the only case
    # that exists today (Spotify). A second one would need this revisited
    # (which one restore_volume's shared write_hardware() should use),
    # not because the capability model can't express two, but because
    # there is no real second example yet to derive that from (ADR-0013's
    # own instruction: derive from a working implementation, not ahead of
    # one).
    software_api_adapters = [
        adapter
        for adapter in adapters.values()
        if adapter.capabilities.volume_mechanism is VolumeMechanism.SOFTWARE_API
    ]
    if len(software_api_adapters) != 1:
        raise RuntimeError(
            f"expected exactly one SOFTWARE_API adapter, found {len(software_api_adapters)}"
        )

    # Constructed before Supervisor/restore_volume, which both need to
    # write through it (write_hardware()) rather than around it - its
    # get_active_renderer callback references `supervisor` by closure, so
    # it's fine that `supervisor` itself doesn't exist yet here; nothing
    # calls the callback until well after `supervisor` is assigned below.
    volume_bridge = VolumeBridge(
        config.mixer_name,
        software_api_adapters[0],
        volume_memory=volume_memory,
        get_active_renderer=lambda: supervisor.active,
        on_hardware_level=state_store.set_volume_raw,
    )
    restore_volume = make_restore_volume(config, volume_memory, volume_bridge)

    supervisor = Supervisor(
        adapters,
        device_busy=lambda renderer_id: alsa.device_held_by(adapters[renderer_id].unit_name),
        restore_volume=restore_volume,
        on_active_change=state_store.set_active,
        on_handoff_change=state_store.set_handoff,
    )

    for renderer_id, adapter in adapters.items():
        adapter.on_metadata_change(lambda metadata, rid=renderer_id: state_store.set_metadata(rid, metadata))
        adapter.on_availability_change(
            lambda available, rid=renderer_id: state_store.set_available(rid, available)
        )

    # ADR-0028's command surface. Both handlers live here rather than in
    # wsserver.py so that module stays transport-only and knows nothing
    # about adapters or mixer scales.
    async def activate(renderer_id: str) -> bool:
        adapter = adapters[renderer_id]
        activate_method = getattr(adapter, "activate", None)
        if activate_method is None:
            # Declared `activate` in capabilities but has no method - a
            # contract violation on our own side, not a user error.
            logger.error("command: %s declares activate but implements none", renderer_id)
            return False
        return await activate_method()

    async def set_volume(percent: float) -> bool:
        raw = percent_to_raw(percent)
        logger.info("command: volume -> %.0f%% (raw %s/240)", percent, raw)
        # Through the bridge, never set_raw() directly - the echo window is
        # what stops this write being read back as an external change and
        # bounced out to the active renderer (Finding 009 §1, which cost a
        # round of "volume is behind/inverted" reports).
        await volume_bridge.write_hardware(raw)
        return True

    # Serve the UI only if a build is actually present. A configured path
    # that does not exist is normal, not an error: the core ships and runs
    # independently of the UI, and saying so in the log beats a stack trace
    # on a route nobody has installed yet.
    ui_dir = Path(config.ui_dir) if config.ui_dir else None
    if ui_dir is not None and not (ui_dir / "index.html").is_file():
        logger.info("wsserver: no UI build at %s, serving the API only", ui_dir)
        ui_dir = None

    state_server = StateServer(
        state_store,
        host=config.state_host,
        port=config.state_port,
        activate=activate,
        set_volume=set_volume,
        ui_dir=ui_dir,
    )

    # The mixer's level at startup, so the published state carries one
    # before anybody touches the volume. `None` if amixer's output could
    # not be parsed, which stays None in the payload rather than becoming
    # a guessed number.
    initial_raw = await get_raw(config.mixer_name)
    if initial_raw is not None:
        state_store.set_volume_raw(initial_raw)

    def make_on_acquire(renderer_id: str):
        def _on_acquire() -> None:
            asyncio.create_task(supervisor.acquire(renderer_id))

        return _on_acquire

    def make_on_release(renderer_id: str):
        def _on_release() -> None:
            asyncio.create_task(supervisor.relinquish(renderer_id))

        return _on_release
    # B2, George's decision 2026-09-08: a DUMMY_MIXER renderer writes to
    # its own private snd-dummy control (image/stage-gexis/00-alsa's
    # modprobe config), not the real DAC directly - this mirrors that
    # control onto real hardware only while its renderer is active. See
    # volume.py's module docstring. One instance per such renderer (LMS,
    # Bluetooth today), built from each adapter's own declared capability
    # rather than named by hand.
    dummy_mixer_bridges = [
        DummyMixerBridge(
            renderer_id,
            adapter.capabilities.dummy_mixer_card,
            DUMMY_CONTROL,
            config.mixer_name,
            volume_memory=volume_memory,
            get_active_renderer=lambda: supervisor.active,
        )
        for renderer_id, adapter in adapters.items()
        if adapter.capabilities.volume_mechanism is VolumeMechanism.DUMMY_MIXER
    ]

    logger.info("gexis-core starting: adapters=%s", list(adapters))
    await asyncio.gather(
        *(
            adapter.run(make_on_acquire(rid), make_on_release(rid))
            for rid, adapter in adapters.items()
        ),
        volume_bridge.run(),
        *(bridge.run() for bridge in dummy_mixer_bridges),
        state_server.run(),
    )


if __name__ == "__main__":
    asyncio.run(main())
