# SPDX-License-Identifier: GPL-3.0-or-later
"""Arbitration core entrypoint (`python -m gexis_core`). Runs the
supervisor and every adapter for the process lifetime - this is
`gexis-core.service` (image/stage-gexis/03-core).
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import aiohttp
from dbus_next import BusType
from dbus_next.aio import MessageBus

from gexis_core import alsa, bluetooth_adapter_state, bluetooth_agent, device_name, meters, skins, wifi
from gexis_core.adapters.base import VolumeMechanism
from gexis_core.adapters.bluetooth import BluetoothAdapter
from gexis_core.adapters.lms import LmsAdapter
from gexis_core.library import LmsLibrary
from gexis_core.radio import RadioBrowser
from gexis_core.adapters.spotify import SpotifyAdapter
from gexis_core.arbitration import Supervisor
from dataclasses import replace

from gexis_core.config import Config
from gexis_core.idle_page import probe as probe_idle_page
from gexis_core.wallpapers import Wallpapers
from gexis_core.weather import Weather
from gexis_core.metadata_file import MetadataFileWriter
from gexis_core.artistinfo import LmsArtistInfo
from gexis_core.enrichment import PREFETCH_AFTER_S, Cache, EnrichmentService, TrackKey
from gexis_core.providers import (
    FANART_BACKGROUND,
    ArtistIdentity,
    CoverArtProvider,
    FanartArtistImage,
    Http,
    ListenBrainzPopular,
    ListenBrainzSimilar,
    LmsArtistProvider,
    LrclibLyrics,
    LmsReleaseProvider,
    MusicBrainzRelease,
    RecordingArtProvider,
    WikipediaBiography,
)
from gexis_core.peppy import PeppyController, PeppyScreen, UnattendedPlayback
from gexis_core.peppy_metadata import PeppyMetadataWriter
from gexis_core.renderer_volume import RendererVolumeMemory
from gexis_core.settings import SettingsStore
from gexis_core.settings_registry import Settings
from gexis_core.splash import Splash
from gexis_core.state import StateStore
from gexis_core import bluealsa_volume
from gexis_core.bluealsa_volume import BluealsaVolume
from gexis_core.remote_volume import RemoteVolume
from gexis_core.volume import (
    DUMMY_CONTROL,
    DUMMY_MAX_RAW,
    DummyMixerBridge,
    VolumeBridge,
    db_to_raw,
    get_raw,
    Mute,
    renderer_value_to_hardware_raw,
    set_ceiling_reader,
    set_curve_reader,
    set_raw,
    slider_percent_to_raw,
    raw_to_db,
)
from gexis_core.wsserver import StateServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

#: How a renderer is named to a person. Only where the id is not simply its
#: name capitalised, which today is LMS alone.
RENDERER_LABELS = {"lms": "LMS"}
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


def make_restore_volume(
    config: Config,
    volume_memory: RendererVolumeMemory,
    volume_bridge: VolumeBridge,
    acquire_volume=None,
):
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
        # ADR-0054 §5: ask the renderer where it is before reaching for a
        # remembered level. Only if it will not say does the memory answer.
        #
        # George, 2026-09-23, on a phone that connected quiet while showing
        # maximum: *"doesn't the bluetooth protocol pass along as well the
        # volume upon connection so the phone and panel show the same
        # thing? Same question for all renderers in the end."* It does, and
        # this is the line that listens.
        if acquire_volume is not None and await acquire_volume(renderer_id):
            return
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


def _chosen_server(config: Config, store: SettingsStore) -> Config:
    """`config`, with `lms_server` applied if one was chosen and is usable.

    A stored value that cannot be read as host:port is ignored with a log
    line rather than taking the daemon down on the next boot - the settings
    DB is user-writable and a bad value there must not brick the player.
    """
    chosen = store.get("lms_server")
    if not chosen:
        return config
    host, _, port = str(chosen).rpartition(":")
    try:
        config = replace(config, lms_host=host or str(chosen), lms_port=int(port))
    except ValueError:
        logger.warning("settings: ignoring lms_server %r: not host:port", chosen)
        return config
    logger.info("settings: lms_server chosen, using %s:%s", config.lms_host, config.lms_port)
    return config


async def _apply_discoverable(mode: str, attempts: int = 1) -> bool:
    """`bt_discoverable`, on the adapter. Live: discoverability is not
    audible and nothing about it is mid-session, so unlike a rename there
    is nothing to defer.

    `attempts` is for the one at startup. `gexis-bluetooth-setup.service`
    powers the adapter and nothing orders this after it, so the adapter can
    still be absent from the bus when the daemon comes up - and a setting
    that silently did not apply at boot is the defect this replaces, not one
    to reintroduce.
    """
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    try:
        for attempt in range(attempts):
            if await bluetooth_adapter_state.apply_discoverable(bus, mode):
                return True
            if attempt + 1 < attempts:
                await asyncio.sleep(2)
        return False
    finally:
        bus.disconnect()


def apply_device_name(name: str) -> None:
    """One name to four services (ADR-0048). Nothing restarts: the rename is
    restart-gated, and the panel says so. A target that refuses is logged
    here and reported to whoever asked - a half-renamed device with nothing
    on screen to say so only surfaces at the restart, hours after the cause.
    """
    written = device_name.apply(name)
    if written.ok:
        logger.info("device name: %r written, hostname %s", name, written.hostname)
    else:
        logger.warning("device name: %r not taken by %s", name, ", ".join(written.failed))


async def _set_timezone(zone: str) -> None:
    """`timedatectl`, which moves /etc/localtime and tells the clock. The
    daemon is root on this image, so there is no polkit prompt to answer."""
    process = await asyncio.create_subprocess_exec(
        "timedatectl", "set-timezone", zone,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await process.communicate()
    if process.returncode:
        logger.warning("timezone: %s", err.decode("utf-8", "replace").strip())
    else:
        logger.info("timezone: set to %s", zone)


async def _reboot() -> None:
    logger.info("reboot: requested from settings")
    await asyncio.create_subprocess_exec("systemctl", "reboot")


def read_timezone(localtime: Path = Path("/etc/localtime")) -> str | None:
    # The /etc/localtime link is what the clock uses; /etc/timezone can be
    # stale (timedatectl updates only the link).
    target = str(localtime.resolve())
    marker = "/zoneinfo/"
    return target.split(marker, 1)[1] if marker in target else None


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

    # A server chosen from the Settings sheet (ADR-0044 §1's `kind: server`)
    # wins over the deployment's own address - but only from here, at
    # startup. Moving a running daemon to another server means dropping a
    # CometD subscription, re-resolving the player and re-arbitrating; that
    # is its own piece of work and its own record. **So the write is stored
    # and the switch happens on the next start**, which is what the panel
    # says when a server is picked.
    config = _chosen_server(config, settings_store)

    lms = LmsAdapter(config.lms_host, config.lms_port, config.lms_player_name)
    spotify = SpotifyAdapter(config.go_librespot_host, config.go_librespot_port)
    bluetooth = BluetoothAdapter()
    adapters = {"lms": lms, "spotify": spotify, "bluetooth": bluetooth}

    # Criterion 3, 2026-09-12: which renderers are volume-managed is a
    # declared capability (adapters/base.py), not a name hardcoded here -
    # this used to be renderer_volume.py's own MANAGED_RENDERERS tuple.
    volume_memory = RendererVolumeMemory(
        enabled=lambda: settings.value("per_renderer_volume") is not False,
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
        on_hardware_level=lambda raw: publish_volume(raw),
        # ADR-0053: Spotify says where its own volume is, and the panel
        # shows that rather than a second number derived from the DAC.
        on_renderer_value=lambda rid, value, steps: report_renderer_volume(
            rid, value, steps
        ),
        # ADR-0052 §3: the backstop for an absolute level that was never a
        # slider position - see `_capped`. The ceiling proper is the shift
        # installed by `set_ceiling_reader` below. `_number` is defined
        # further down `main()` and resolved when this is called, not now.
        ceiling_db=lambda: _number("max_ceiling"),
    )
    restore_volume = make_restore_volume(
        config,
        volume_memory,
        volume_bridge,
        acquire_volume=lambda renderer_id: acquire_volume(renderer_id),
    )

    # ADR-0034. Observes every level before it is published, so a change
    # from anywhere else ends mute in the same broadcast that shows it.
    mute = Mute(
        volume_bridge.write_hardware,
        lambda: state_store.state.volume.raw if state_store.state.volume else None,
    )

    #: ADR-0053. The panel's volume control is the active renderer's, so
    #: what the panel shows is the renderer's own number and what the panel
    #: sends goes to the renderer. `remote.percent()` is None when there is
    #: nothing to be a remote for, and then the hardware's own percentage is
    #: published exactly as before.
    remote = RemoteVolume(
        get_active_renderer=lambda: supervisor.active,
        on_change=lambda: publish_volume(),
        # ADR-0054 §6: the hardware hears the panel at once rather than
        # after the trip through the renderer and back.
        on_level=lambda value, steps: asyncio.ensure_future(
            volume_bridge.write_hardware(renderer_value_to_hardware_raw(value, steps))
        ),
    )

    def publish_volume(raw: int | None = None) -> None:
        """One place builds the published level.

        `raw` is the hardware's, and `None` means "the same level as before,
        but something about how it should be *described* changed" - a
        renderer reported its own number, the active renderer changed, or
        the ceiling moved the scale.
        """
        if raw is None:
            volume = state_store.state.volume
            if volume is None:
                return
            raw = volume.raw
        mute.observe(raw)
        state_store.set_volume_raw(raw, muted=mute.muted, percent=remote.percent())

    def report_renderer_volume(renderer_id: str, value: int, steps: int) -> None:
        """**The one path from a renderer's number to the DAC** (ADR-0054 §3).

        Inbound only, and it must stay that way: `RemoteVolume.report` never
        sends, because 101 panel positions cannot name AVRCP's 128 values
        and closing that loop rebuilds Finding 045 §12's ratchet.

        Until 2026-09-23 there were three paths and three curves - Spotify's
        through `VolumeBridge`, LMS's and Bluetooth's through their dummy
        controls' declared dB, each derived by the renderer rather than by
        us. Now there is one, and the curve is
        `renderer_value_to_hardware_raw`.
        """
        remote.set_steps(renderer_id, steps)
        remote.report(renderer_id, value)
        raw = renderer_value_to_hardware_raw(value, steps)
        # Remembered whoever is active: `remember()` no-ops for renderers
        # outside MANAGED_RENDERERS, and since ADR-0054 §5 a remembered
        # level is the fallback for a renderer that will not say where it
        # is, not the normal path.
        volume_memory.remember(renderer_id, raw)
        if supervisor.active != renderer_id:
            logger.debug(
                "volume: %s reported %s/%s while inactive, remembered but not applied",
                renderer_id, value, steps,
            )
            return
        logger.info(
            "volume: %s -> hardware (%s/%s -> %s/240)", renderer_id, value, steps, raw
        )
        asyncio.ensure_future(volume_bridge.write_hardware(raw))

    async def renderer_volume_moved(renderer_id: str) -> None:
        """A renderer's control moved; ask the renderer what it means.

        ADR-0054 §2: squeezelite's write to its dummy control is the fastest
        signal that LMS's volume changed (0.1 ms), but the value is
        squeezelite's curve of LMS's number, not the number. One RPC, ~13 ms,
        answers it; the status push that would also answer takes 525 ms.
        """
        adapter = adapters.get(renderer_id)
        getter = getattr(adapter, "get_volume", None)
        if getter is None:
            return
        value = await getter()
        if value is None:
            return
        report_renderer_volume(
            renderer_id, value, getattr(adapter, "VOLUME_STEPS", 100)
        )

    async def acquire_volume(renderer_id: str) -> bool:
        """ADR-0054 §5: a renderer is *asked* where it is when it takes the
        device, rather than having a remembered level written under it.

        George, 2026-09-23: *"when first connecting the volume was low even
        though on the phone it was at max... doesn't the bluetooth protocol
        pass along as well the volume upon connection so the phone and panel
        show the same thing?"* It does, and so do the other two - this is
        where we start listening to it. Returns False when the renderer has
        nothing to say, and the remembered level is used instead.
        """
        adapter = adapters.get(renderer_id)
        if adapter is not None and adapter.capabilities.volume_over_bluealsa:
            # The phone announced its level when it connected; bluealsa has
            # been holding it since (ADR-0054 §1).
            value, steps = bluetooth_volume.level, bluealsa_volume.STEPS
            if value is None:
                return False
            logger.info("volume: bluetooth says it is at %s on acquisition", value)
            report_renderer_volume(renderer_id, value, steps)
            return True
        getter = getattr(adapter, "get_volume", None)
        if getter is None:
            return False
        value = await getter()
        if value is None:
            return False
        logger.info("volume: %s says it is at %s on acquisition", renderer_id, value)
        report_renderer_volume(
            renderer_id, value, getattr(adapter, "VOLUME_STEPS", 100)
        )
        return True

    # ADR-0052 §3, amended: the ceiling is the top of every scale, so the
    # row has to be readable from inside `volume.py`'s pure mapping
    # functions - a reader rather than a value, resolved per map.
    set_ceiling_reader(lambda: _number("max_ceiling"))
    # ADR-0022's inventory, wired 2026-09-23: which of the two curves maps
    # the slider's travel onto loudness (ADR-0054 §3).
    set_curve_reader(lambda: settings.value("travel_curve"))

    def _reapply_level() -> None:
        """Put the level back where the *position* now says it belongs.

        Both `max_ceiling` and the volume curve change what a position
        means without anybody touching the volume, so the hardware has to
        be re-derived from the position rather than left where it is -
        otherwise a ceiling that came down leaves the device too loud, and
        a curve change leaves the slider pointing at the wrong level.

        Through the bridge, so it ramps rather than drops, and so the panel
        is republished: the number may not have moved but what it describes
        has.
        """
        level = remote.level()
        if level is not None:
            value, steps = level
            raw = renderer_value_to_hardware_raw(value, steps)
        else:
            volume = state_store.state.volume
            if volume is None:
                return
            raw = slider_percent_to_raw(volume.percent)
        asyncio.ensure_future(volume_bridge.write_hardware(raw))

    def on_active_change(renderer_id: str | None) -> None:
        state_store.set_active(renderer_id)
        # ADR-0053: the number on the panel belongs to whoever holds the
        # device, so a takeover changes what it means - from one renderer's
        # scale to another's, or to the hardware's own with nobody active.
        publish_volume()

    # ADR-0054 §1. Constructed before the supervisor because
    # `restore_volume` reaches it through `acquire_volume`; its own watch is
    # started with the rest of the long-running tasks below.
    bluetooth_volume = BluealsaVolume(
        on_value=lambda level, steps: report_renderer_volume("bluetooth", level, steps)
    )

    supervisor = Supervisor(
        adapters,
        device_busy=lambda renderer_id: alsa.device_held_by(adapters[renderer_id].unit_name),
        restore_volume=restore_volume,
        on_active_change=lambda renderer_id: on_active_change(renderer_id),
        on_handoff_change=state_store.set_handoff,
    )

    # ADR-0053's three channels. A renderer with a `set_volume` is driven
    # through it; Bluetooth has no API of its own and is driven through the
    # control `bluealsa-aplay` pushes out over AVRCP; a renderer with
    # neither would still show its number and keep the panel's own slider.
    for renderer_id, adapter in adapters.items():
        capabilities = adapter.capabilities
        if hasattr(adapter, "set_volume"):
            remote.register(
                renderer_id,
                steps=getattr(adapter, "VOLUME_STEPS", 100),
                send=adapter.set_volume,
            )
        elif capabilities.volume_over_bluealsa:
            # ADR-0054 §1. Not the mixer: `--volume=mixer` made a loop that
            # was measured wrong one time in three, and pushed a stale mixer
            # value at the phone whenever a stream started (Finding 047 §2).
            remote.register(
                renderer_id, steps=bluealsa_volume.STEPS, send=bluetooth_volume.set
            )
        if (
            hasattr(adapter, "on_volume_change")
            and capabilities.volume_mechanism is not VolumeMechanism.SOFTWARE_API
        ):
            # A SOFTWARE_API renderer's reports already reach
            # `report_renderer_volume` through VolumeBridge, which holds
            # this same callback and would be unsubscribed by a second
            # registration - `on_volume_change` keeps one, not a list.
            adapter.on_volume_change(
                lambda value, steps, rid=renderer_id: report_renderer_volume(
                    rid, value, steps
                )
            )

    for renderer_id, adapter in adapters.items():
        adapter.on_metadata_change(lambda metadata, rid=renderer_id: state_store.set_metadata(rid, metadata))
        # Only LMS has a queue to report (ADR-0038 §5); the others hand us
        # a stream.
        if hasattr(adapter, "on_queue_change"):
            adapter.on_queue_change(lambda queue, rid=renderer_id: state_store.set_queue(rid, queue))
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

    async def transport(renderer_id: str, command: str, argument=None) -> bool:
        # ADR-0037. The route has already checked the declaration; a
        # declared command with no method is our own contract violation.
        method = getattr(adapters[renderer_id], command, None)
        if method is None:
            logger.error("command: %s declares %s but implements none", renderer_id, command)
            return False
        logger.info("command: %s %s%s", command, renderer_id, "" if argument is None else f" {argument}")
        return await (method() if argument is None else method(argument))

    async def set_volume(percent: float) -> bool:
        # **ADR-0053: the panel is a remote first.** With something playing,
        # the position goes to that renderer's own control and reaches the
        # DAC the way its changes always have. `send` returns False only
        # when there is nothing to be a remote for, and then this is the
        # panel's own slider exactly as before.
        if await remote.send(percent):
            return True
        raw = slider_percent_to_raw(percent)
        logger.info("command: volume -> %.0f%% (raw %s/240)", percent, raw)
        # Through the bridge, never set_raw() directly - the echo window is
        # what stops this write being read back as an external change and
        # bounced out to the active renderer (Finding 009 §1, which cost a
        # round of "volume is behind/inverted" reports).
        await volume_bridge.write_hardware(raw)
        return True

    async def set_mute(muted: bool) -> bool:
        logger.info("command: %s", "mute" if muted else "unmute")
        ok = await mute.set(muted)
        volume = state_store.state.volume
        if ok and volume is not None:
            state_store.set_volume_raw(volume.raw, muted=mute.muted)
        return ok

    # Serve the UI only if a build is actually present. A configured path
    # that does not exist is normal, not an error: the core ships and runs
    # independently of the UI, and saying so in the log beats a stack trace
    # on a route nobody has installed yet.
    ui_dir = Path(config.ui_dir) if config.ui_dir else None
    if ui_dir is not None and not (ui_dir / "index.html").is_file():
        logger.info("wsserver: no UI build at %s, serving the API only", ui_dir)
        ui_dir = None

    idle_session = aiohttp.ClientSession()

    async def idle_page() -> dict:
        return await probe_idle_page(settings.value("idle_url") or "", idle_session)

    # ADR-0047 §2a. Both share the idle screen's session: one screen, three
    # things it asks for, and a fourth connection pool would be a pool for
    # something that runs once every fifteen minutes.
    forecast = Weather(idle_session)
    # Beside the settings database rather than in /tmp: the pictures are
    # what the screen shows when the network is down, so they have to
    # survive a reboot (ADR-0047 §2a - the device is the cache).
    wallpapers = Wallpapers(
        idle_session, config.wallpaper_dir, local_dir=Path(config.pictures_dir)
    )

    # ADR-0051. The three visualisation rows describe what the renderer
    # draws, and the renderer is another process: it learns of a change by
    # re-reading one small file, on the same poll that already carries the
    # track. `settings` is assigned by this very statement and read only when
    # one of these is called, which is after it exists.
    skins_root = Path(config.peppy_skins_dir)

    def skins_offered() -> list[str]:
        return skins.names(skins_root, str(settings.value("skin_corpus") or skins.ALL))

    def first_skin() -> str | None:
        offered = skins_offered()
        return offered[0] if offered else None

    def publish_visualisation(_value: object = None) -> None:
        skins.write_selection(
            str(settings.value("skin_corpus") or skins.ALL),
            settings.value("skin"),
            settings.value("skin_rotate") is not False,
        )

    def apply_corpus(word: object) -> None:
        """A narrower corpus takes the skin in use with it (ADR-0051 §4).

        **A write, not a substitution.** If the stored skin is not in the new
        corpus the first one that is gets stored, so the row, the picker and
        the screen all say the same thing; `set` publishes on its way out.
        """
        offered = skins_offered()
        if settings.value("skin") in offered:
            publish_visualisation()
            return
        if offered:
            settings.set("skin", offered[0])
        else:
            publish_visualisation()

    # ADR-0035. Defaults are what is true of this deployment today. A wired
    # row is read where it is used - the idle page probe here, the rest by
    # the UI - so none needs a callback.
    settings = Settings(
        settings_store,
        defaults={
            "boot_volume": lambda: raw_to_db(config.boot_volume_steps),
            "restore_floor": lambda: config.restore_volume_floor_db,
            "lms_server": lambda: f"{config.lms_host}:{config.lms_port}",
            "lms_player": lambda: config.lms_player_name,
            "idle_url": lambda: config.idle_url or None,
            "device_name": device_name.hostname,
            "timezone": read_timezone,
            "wifi": wifi.connected_ssid,
            # Nothing stored means the first skin the corpus offers, so the
            # picker opens on something rather than on nothing.
            "skin": first_skin,
            # ADR-0022's inventory: readonly, and it now reports what the
            # adapters actually declare rather than a literal that could
            # drift from them (`capabilities.volume_managed`).
            "volume_managed": lambda: ", ".join(
                sorted(
                    RENDERER_LABELS.get(renderer_id, renderer_id.capitalize())
                    for renderer_id, adapter in adapters.items()
                    if adapter.capabilities.volume_managed
                )
            )
            or "None",
        },
        # ADR-0051 §4: which skins there are depends on where they are
        # installed and on what `skin_corpus` holds, neither of which the
        # registry module can know.
        options={"skin_corpus": skins_offered},
        # Wired = something reads it (ADR-0035). The token is read on every
        # Popular lookup, so it takes effect as soon as it is typed.
        # Wired = something reads it, or something happens. `lms_server` is
        # read at the next start (see `_chosen_server`); `timezone` and
        # `reboot` act at once.
        # ADR-0047's rows are read where they are used: the two routes above
        # read the weather and wallpaper rows on every request, and the panel
        # reads the rest as it draws. None of them needs a callback, and all
        # of them are wired, because something reads every one.
        wired={"idle_url": None, "idle_timeout": None, "drawer_on_external": None,
               "drawer_autohide": None, "listenbrainz_token": None,
               "fanart_key": None, "lms_server": None,
               "idle_screen": None, "idle_background": None,
               "background_brightness": None, "background_interval": None,
               "wallpaper_key": None, "wallpaper_topics": None,
               "idle_weather": None,
               "weather_location": None, "idle_forecast": None,
               "idle_icons": None,
               "viz_timeout": None, "viz_stop": None,
               # ADR-0052 §3: read on every map between a position and a
               # level, and re-applied here when it changes so the level
               # comes down at once if it is now above the ceiling.
               "max_ceiling": lambda _value=None: _reapply_level(),
               # ADR-0054 §3's two curves, wired 2026-09-23. A change moves
               # the level under a slider that has not been touched, so it
               # is re-applied rather than waiting for the next change.
               "travel_curve": lambda _value=None: _reapply_level(),
               # Readonly: nothing to do on a write, and the value is the
               # live one below rather than the registry's literal.
               "volume_managed": None,
               # Read by `gexis_core.boot_volume`, which runs as its own
               # unit before any renderer can play, so this takes effect at
               # the next boot rather than now - which is what a *boot*
               # volume means.
               "boot_volume": None,
               # Wired where it is used - `RendererVolumeMemory` reads it
               # on every remember and every restore.
               "per_renderer_volume": None,
               # ADR-0051: read by the driver, through the file these write.
               "skin": publish_visualisation,
               "skin_rotate": publish_visualisation,
               "skin_corpus": apply_corpus,
               "home_strip": None, "home_strip_count": None,
               "idle_clock": None,
               "device_name": apply_device_name,
               "bt_discoverable": lambda mode: asyncio.ensure_future(
                   _apply_discoverable(mode)
               ),
               "timezone": lambda zone: asyncio.ensure_future(_set_timezone(zone)),
               "reboot": lambda _: asyncio.ensure_future(_reboot())},
        on_change=state_store.bump_settings_revision,
    )

    # The fourth corpus word was `Random` until 2026-09-22 and is `All`
    # now; a device that stored the old one is moved over rather than left
    # holding a value its own row no longer offers.
    if settings.value("skin_corpus") == "Random":
        settings.set("skin_corpus", skins.ALL)

    # **The visualiser's four pipes, made by the one process that can.**
    # peppyalsa (inside each renderer) and the meter service open them; this
    # daemon is root and owns /run/gexis, so it creates them. Until
    # 2026-09-22 they lived in /tmp, where `bluealsa-aplay`'s `PrivateTmp=yes`
    # hid ours from it and the visualiser was blind for the whole of
    # Bluetooth (ADR-0011, amended).
    for fifo in (
        config.meter_fifo,
        config.spectrum_fifo,
        config.meter_passthrough,
        config.spectrum_passthrough,
    ):
        meters.ensure_fifo(fifo)

    # The driver starts with whatever this says, so it is written once here
    # rather than only on a change: a device that has never touched the three
    # rows still has to tell the renderer what they hold (ADR-0051 §1).
    publish_visualisation()

    # ADR-0045: the adapter's own switches, applied from the stored setting
    # rather than left to a shell script that could not express them, and
    # our own Agent1 so the question can reach the panel at all.
    pairing_agent = bluetooth_agent.Agent(
        # `to_json` here, not in the store: the agent publishes its own
        # object and the store holds what goes on the wire. Passing the
        # dataclass straight through made `json.dumps` raise inside the
        # broadcast, which took **every** state update with it for as long
        # as a request was open - not just the pairing field.
        publish=lambda request: _publish_pairing(request),
        # Read per request, not captured: changing either takes effect on
        # the next pair rather than on the next boot.
        confirm_required=lambda: settings.value("bt_pairing") != "PIN-free",
        should_trust=lambda: settings.value("bt_autotrust") is not False,
    )

    def _publish_pairing(request) -> None:
        """The request, and the screen it needs.

        **The visualiser is a separate process window, not a layer.** The
        panel can draw the pairing frame over its own idle screen because
        that is a div; it cannot draw over PeppyMeter, which is another
        X client entirely. A request arriving while the meter is up would
        be invisible for its whole thirty seconds and then lapse, with
        nothing on screen to explain it - ADR-0045's open question about
        what a request takes the screen from, answered: it takes it, and
        here is the half the panel cannot do for itself.

        `peppy` is assigned further down `main()`; a lambda would resolve
        it at call time and so does this, which is why the reference is
        safe despite reading like it is out of order.
        """
        state_store.set_pairing(request.to_json() if request is not None else None)
        if request is not None and request.state == "asking":
            peppy.request("hide")

    async def _bluetooth_setup() -> None:
        await _apply_discoverable(
            settings.value("bt_discoverable") or "3 min after boot", attempts=10
        )
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        await bluetooth_agent.register(
            bus,
            pairing_agent,
            bluetooth_agent.capability_for(settings.value("bt_pairing")),
        )
        # The bus stays open for the process: an agent whose connection
        # closes is unregistered by BlueZ, silently, and pairing goes back
        # to whatever answered before.
        await bus.wait_for_disconnect()

    asyncio.ensure_future(_bluetooth_setup())

    # Phase 5 criteria 6 and 8 (ADR-0036). The meter process keeps running
    # whether or not it is on screen; this only raises and lowers it.
    # **Minutes, and read per tick** (9h). The row is in minutes because the
    # design draws it that way and because a number nobody can see the unit
    # of is a number nobody can set; reading it through a callable means a
    # change from the phone lands on the next tick rather than the next
    # restart.
    def _number(key: str) -> float | None:
        """A number row's value, or None when it is unset - the shape
        `max_ceiling` wants (ADR-0052 §3)."""
        try:
            value = settings.value(key)
        except Exception:  # noqa: BLE001 - a row that is not there is None
            return None
        return None if value is None else float(value)

    def minutes(key: str, fallback: float):
        def read() -> float:
            value = settings.value(key)
            return float(value) * 60 if value else fallback
        return read

    peppy = PeppyController(
        PeppyScreen(
            runtime_dir=config.peppy_runtime_dir,
            wayland_display=config.peppy_wayland_display,
        ),
        UnattendedPlayback(
            minutes("viz_timeout", 600),
            stop_after_s=minutes("viz_stop", 300),
        ),
    )

    previous_active = state_store.state.active

    def follow_playback(state) -> None:
        nonlocal previous_active
        if state.active != previous_active:
            previous_active = state.active
            peppy.on_active_change(state.active)
        peppy.on_metadata(state.metadata)

    state_store.subscribe(follow_playback)


    # What the Peppy screen draws (criterion 7). A separate file from
    # currentsong.txt, which is moOde's format for moOde's readers.
    state_store.subscribe(PeppyMetadataWriter().write)

    # Phase 7 (ADR-0038): the same server, and the same player, the renderer
    # adapter talks to. Radio shares its HTTP session.
    library = LmsLibrary(config.lms_host, config.lms_port, player_id=lambda: lms.player_id)
    # LMS's own artist photos and biographies, where the server has the
    # plugin (ADR-0040 §1). Shares the library's HTTP session.
    enrichment_cache = Cache()
    artistinfo = LmsArtistInfo(library.rpc, f"http://{config.lms_host}:{config.lms_port}",
                               store=enrichment_cache)
    # ADR-0040 §1: LMS's own plugin first where it answers, the key-free
    # providers behind it and for the renderers that have no LMS ids.
    http = Http()
    # One MusicBrainz lookup for the artist, shared: two providers needed the
    # same id and each was searching for it (see ArtistIdentity).
    identity = ArtistIdentity(http, store=enrichment_cache)
    enrichment = EnrichmentService(
        [
            # **Pictures before LMS, text after it** (George, 2026-09-18,
            # once the speed was measured). Fanart has a portrait for
            # artists the plugin has nothing for, and this list merges
            # field by field - fanart offers only a picture, so putting it
            # first takes the picture and leaves the biography to LMS.
            FanartArtistImage(http, identity, lambda: settings.value("fanart_key"),
                              proxy_base=f"http://{config.lms_host}:{config.lms_port}"),
            # The same source, asked for the other shape: the idle screen's
            # background (ADR-0047 §1b). Only the idle route asks for it by
            # name, so no other screen pays for it.
            FanartArtistImage(http, identity, lambda: settings.value("fanart_key"),
                              proxy_base=f"http://{config.lms_host}:{config.lms_port}",
                              **FANART_BACKGROUND),
            LmsArtistProvider(artistinfo, lambda: lms.current_artist_id),
            LmsReleaseProvider(library, artistinfo, lambda: lms.current_album_id),
            WikipediaBiography(http, identity),
            ListenBrainzSimilar(http, identity),
            # ADR-0022's inventory: a per-user token, read fresh so one
            # typed into Settings works without a restart.
            ListenBrainzPopular(http, identity,
                                lambda: settings.value("listenbrainz_token")),
            # Behind the LMS one, which answers from the library itself
            # and wins the merge where it has anything.
            MusicBrainzRelease(http),
            LrclibLyrics(http),
            CoverArtProvider(http),
            # Last: the radio case, where there is no album to match on
            # (Phase 8 criterion 7).
            RecordingArtProvider(http),
        ],
        enrichment_cache,
    )
    # Warm the Artist tab while the track plays, so opening it shows
    # something rather than a skeleton (George, 2026-09-18). Debounced,
    # because skipping through an album would otherwise fire a lookup per
    # track, and local-only: see EnrichmentService.prefetch for why the
    # key-free providers are not warmed speculatively.
    prefetch_task: asyncio.Task | None = None

    def warm_enrichment(state) -> None:
        nonlocal prefetch_task
        key = TrackKey.of(state.metadata)
        if key.is_empty() or state.metadata.transport != "playing":
            return
        if prefetch_task is not None and not prefetch_task.done():
            if getattr(prefetch_task, "gexis_key", None) == key:
                return
            prefetch_task.cancel()

        async def warm() -> None:
            # Long enough that a skipped track never costs a lookup.
            await asyncio.sleep(PREFETCH_AFTER_S)
            await enrichment.prefetch(key, renderer=state.active)

        prefetch_task = asyncio.ensure_future(warm())
        prefetch_task.gexis_key = key

    state_store.subscribe(warm_enrichment)

    state_server = StateServer(
        state_store,
        host=config.state_host,
        port=config.state_port,
        activate=activate,
        transport=transport,
        set_volume=set_volume,
        set_mute=set_mute,
        idle_page=idle_page,
        settings=settings,
        peppy=peppy,
        # Phase 7 (ADR-0038): the same server, and the same player, the
        # renderer adapter talks to.
        library=library,
        artistinfo=artistinfo,
        enrichment=enrichment,
        # ADR-0038 §8: the one SlimBrowse subtree, browsed by handles the
        # core issues.
        radio=RadioBrowser(library.rpc, lambda: lms.player_id),
        # ADR-0045: the panel's answer, back to the agent that is holding
        # BlueZ's handshake open waiting for it.
        pairing_answer=pairing_agent.answer,
        # ADR-0043: the panel reports its first painted frame and the boot
        # animation ends there, not when the kiosk unit goes active.
        splash=Splash(),
        # ADR-0047: the idle screen's two providers.
        weather=forecast,
        wallpapers=wallpapers,
        # ADR-0050: the picker's previews are the skins' own pictures.
        skins_dir=Path(config.peppy_skins_dir),
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
    dummy_mixer_bridges = {
        renderer_id: DummyMixerBridge(
            renderer_id,
            adapter.capabilities.dummy_mixer_card,
            DUMMY_CONTROL,
            config.mixer_name,
            volume_memory=volume_memory,
            get_active_renderer=lambda: supervisor.active,
            # LMS fades the player out on pause by sending volume steps;
            # mirroring those published the user's volume as 0% and
            # remembered the faded level (George, 2026-09-17 - see
            # DummyMixerBridge, which waits for the control to settle
            # before reading this). Bluetooth's volume does not fade, so it
            # passes none and keeps its immediate mirroring.
            is_playing=(
                (lambda a=adapter: a.last_transport == "playing")
                if hasattr(adapter, "last_transport")
                else None
            ),
            # ADR-0053: only where the control holds the renderer's own
            # number, which each adapter declares. Bluetooth's does; LMS's
            # is squeezelite's curve of it.
            # ADR-0054 §2: the control's movement is an event, and the
            # number is read back from the renderer itself.
            on_moved=renderer_volume_moved,
        )
        for renderer_id, adapter in adapters.items()
        if adapter.capabilities.volume_mechanism is VolumeMechanism.DUMMY_MIXER
        # ADR-0054 §1: Bluetooth's control is nobody's any more - nothing
        # writes it and nothing reads it - so it gets no watcher.
        and not adapter.capabilities.volume_over_bluealsa
    }

    logger.info("gexis-core starting: adapters=%s", list(adapters))
    await asyncio.gather(
        *(
            adapter.run(make_on_acquire(rid), make_on_release(rid))
            for rid, adapter in adapters.items()
        ),
        volume_bridge.run(),
        bluetooth_volume.run(),
        *(bridge.run() for bridge in dummy_mixer_bridges.values()),
        peppy.run(),
        # The `wifi` row's value, kept current from here rather than read on
        # the request path - where it measured 3.2 s and blocked everything.
        wifi.watch_connected(),
        state_server.run(),
    )


if __name__ == "__main__":
    asyncio.run(main())
