# SPDX-License-Identifier: GPL-3.0-or-later
"""Arbitration core entrypoint (`python -m gexis_core`). Runs the
supervisor and every adapter for the process lifetime - this is
`gexis-core.service` (image/stage-gexis/03-core).
"""
from __future__ import annotations

import asyncio
import functools
import logging
import re
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
from gexis_core.enrichment import (
    CONFIDENCE_MIN,
    PREFETCH_AFTER_S,
    Cache,
    EnrichmentService,
    TrackKey,
)
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
# `set_meter_smoothing` by name, not the module: `peppy` is a local
# further down (the controller), and a module import of the same name
# is shadowed by it - which is a 500 on the row, not an import error.
from gexis_core.peppy import (
    PeppyController,
    PeppyScreen,
    UnattendedPlayback,
    set_meter_smoothing,
)
from gexis_core.peppy_metadata import PeppyMetadataWriter
from gexis_core.settings import SettingsStore
from gexis_core.settings_registry import Settings
from gexis_core.splash import Splash
from gexis_core.state import StateStore
from gexis_core import backups, bluealsa_volume, outputs, plugins
from gexis_core.systemd import set_enabled as _set_unit_enabled
from gexis_core.artwork_sweep import ArtworkSweep
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
    HARDWARE_MAX,
    set_ceiling_reader,
    set_curve_reader,
    set_fixed_output_reader,
    set_raw,
    slider_percent_to_raw,
    raw_to_db,
)
from gexis_core.wsserver import StateServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

#: How a renderer is named to a person. Only where the id is not simply its
#: name capitalised, which today is LMS alone.
RENDERER_LABELS = {"lms": "LMS"}

#: **ADR-0077.** Which Settings row switches each source on and off. The three
#: rows are `R` in ADR-0022's inventory - the design has always had them - and
#: until 2026-09-25 they stored a value and switched nothing off.
RENDERER_ROWS = {
    "lms": "lms_enabled",
    "spotify": "spotify_enabled",
    "bluetooth": "bt_enabled",
}

#: **ADR-0077: `headless` turns off three units, not one.** The kiosk is the
#: screen; the warm-up exists only to read the kiosk's binaries into the page
#: cache and is pure boot cost without it; PeppyMeter has nowhere to draw. The
#: core, the phone UI and audio are untouched.
#: `now` is False for the warm-up: its own unit file says warming is pointless
#: once the kiosk has started, so enabling it asks for it at the next boot
#: rather than running it here.
SCREEN_UNITS = (
    ("gexis-kiosk.service", True),
    ("gexis-panel-warmup.service", False),
    ("gexis-peppy.service", True),
)

#: **ADR-0081: how many times the daemon looks for a cover.** `for_track`
#: answers with what it has after its own wait and lets a slow provider finish
#: behind it, caching the result - so one ask can return nothing for a track
#: whose cover arrives a second later. Three looks, six seconds apart, which
#: is the panel's own shape in `enrichment.js` for the same reason.
COVER_LOOKS = 3
COVER_LOOK_BACK_S = 6.0

#: `bt_enabled` off powers the radio down as well as stopping the audio path,
#: and this is the unit that unblocks rfkill and powers it up at boot - so it
#: goes with it, or a reboot turns Bluetooth back on behind the row's back.
BLUETOOTH_SETUP_UNIT = "gexis-bluetooth-setup.service"

logger = logging.getLogger("gexis_core")


async def set_unit_enabled(unit: str, enabled: bool, *, now: bool = True) -> None:
    """`systemd.set_enabled` off the event loop.

    Measured on the device 2026-09-25: `systemctl disable --now
    go-librespot.service` took **7.0 s**, all of it stopping the unit, and run
    inline that is 7 s in which the daemon answers nothing - no state pushes,
    no panel, no phone. The renderer being switched off is the one thing that
    is *expected* to take time, so this is the one call that must not be made
    inline.
    """
    await asyncio.to_thread(functools.partial(_set_unit_enabled, unit, enabled, now=now))


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


async def _restore_done() -> None:
    """**ADR-0083: a restore reboots.** The archive is already written back by
    the time this runs; the pause is only so the answer reaches whoever asked
    before the device goes down under them."""
    logger.warning("restore: rebooting to come up on the restored state")
    await asyncio.sleep(1.5)
    await asyncio.create_subprocess_exec("systemctl", "reboot")


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

    # **ADR-0055: the output decides the mixer control's name.** `DAC` on
    # this HAT, `PCM` on the Pi's own jack, none at all on HDMI - and the
    # card is discovered from its EEPROM, so the name is a property of
    # whatever board is fitted rather than of this project. Read from the
    # store directly, like `lms_server` above, because it has to be settled
    # before the volume bridges are built.
    chosen_output = outputs.resolve(settings_store.get("output_device"))
    if chosen_output is None:
        logger.error("outputs: no playback output found at all")
    else:
        if outputs.write(chosen_output):
            logger.warning(
                "outputs: output.conf did not match %s and was rewritten; "
                "renderers pick it up on their next open",
                chosen_output.label,
            )
        # ADR-0055: arbitration asks about the output the device is
        # playing to, not about the card it shipped with (Finding 048 §5).
        alsa.set_card(chosen_output.card)
        if chosen_output.control:
            config = replace(config, mixer_name=chosen_output.control)
        logger.info(
            "outputs: playing to %s (hw:%s, control %s)",
            chosen_output.label,
            chosen_output.card,
            chosen_output.control or "none - fixed output",
        )
        # ADR-0055 §6: a converted chain carries no meter, so the
        # visualiser has nothing to draw and its button is not offered.
        meters_available = outputs.needs_plug(chosen_output.card) is not True

    lms = LmsAdapter(config.lms_host, config.lms_port, config.lms_player_name)
    spotify = SpotifyAdapter(config.go_librespot_host, config.go_librespot_port)
    bluetooth = BluetoothAdapter()
    adapters = {"lms": lms, "spotify": spotify, "bluetooth": bluetooth}


    # Phase 3 criteria 1-2: the normalised playback model plus each
    # adapter's declared capabilities, published over the state WebSocket.
    # Wired to the supervisor's active-renderer changes and each adapter's
    # own metadata/availability reports below - constructed before
    # Supervisor for the same closure reason as volume_bridge (its
    # callbacks reference `supervisor`, assigned later).
    # **ADR-0086: every source describes itself in a manifest**, the three
    # built-ins included, so the panel's generic path is the one exercised on
    # every boot rather than a fallback nothing runs.
    installed_plugins = plugins.installed()
    if installed_plugins:
        logger.info(
            "plugins: %s", ", ".join(f"{p.id} ({p.kind})" for p in installed_plugins)
        )
    else:
        logger.warning(
            "plugins: no manifests under %s - the panel will draw sources "
            "without names or marks", plugins.DEFAULT_DIR,
        )

    state_store = StateStore(
        {rid: adapter.capabilities for rid, adapter in adapters.items()},
        handoff_exempt_pairs=config.handoff_exempt_pairs,
        sources=tuple(p.to_json() for p in installed_plugins),
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
    async def restore_volume(renderer_id: str) -> None:
        """**ADR-0054 §5, and since 2026-09-23 there is nothing behind it.**

        The renderer is asked where it is and that is the answer. There is
        no remembered level to fall back to any more: the renderer's own
        memory is the real one - LMS keeps it per player, Spotify per
        device, a phone per device - and ours was a second, worse copy of
        it. Measured before deleting it: 12 acquisitions after §5 landed,
        12 answers, **0 fallbacks**.

        **A renderer that does not answer is left alone, deliberately.**
        Every one of them has an inbound path that will correct it within a
        second - bluealsa's PCM appearing, LMS's status push, Spotify's
        volume event - so the level self-corrects, and guessing at one
        meanwhile can only be wrong in a way nobody asked for.
        """
        if not await acquire_volume(renderer_id):
            logger.info(
                "volume: %s did not say where it is; leaving the level alone "
                "until it does",
                renderer_id,
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
        if supervisor.active != renderer_id:
            logger.debug(
                "volume: %s reported %s/%s while inactive, not applied",
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
    # ADR-0046. `output_mode` is what the *user* has chosen; `_fixed_now`
    # is what is in force, which lags it while something is playing.
    # **An output with no volume control forces fixed output** (ADR-0055
    # §4). Not a side effect: the device cannot attenuate, so ADR-0046's
    # behaviour is the only honest one, and the row below cannot override
    # it.
    forced_fixed = chosen_output is not None and chosen_output.control is None  # noqa: F841
    fixed_wanted = {"value": forced_fixed}
    fixed_now = {"value": False}
    set_fixed_output_reader(lambda: fixed_now["value"])

    async def _apply_output_mode() -> None:
        """Put the chosen mode into force, if now is a legal moment.

        **ADR-0018 requires the change to apply on the next track or after
        stop, and ADR-0046 keeps that**: switching to fixed output while
        music is playing would take the level to full scale mid-track, into
        an amplifier set for whatever it was hearing a second earlier.
        That is the loudest mistake this device can make, so it waits.
        """
        wanted = fixed_wanted["value"]
        if wanted == fixed_now["value"]:
            return
        if state_store.state.metadata.transport == "playing":
            logger.info(
                "output: %s is chosen but something is playing; it applies after stop",
                "fixed" if wanted else "variable",
            )
            return
        fixed_now["value"] = wanted
        state_store.set_fixed_output(wanted)
        if wanted:
            # Nothing is attenuating, so the one level the DAC may hold is
            # full scale. Written directly: `write_hardware` now refuses
            # every write in this mode, including this one.
            logger.info("output: fixed - DAC to full scale, the panel can no longer lower it")
            await set_raw(config.mixer_name, HARDWARE_MAX)
        else:
            logger.info("output: variable - the device attenuates again")
            _reapply_level()

    def _restrict_output_mode(output) -> None:
        """Grey `Variable` out on an output that cannot attenuate.

        ADR-0055 §5. The row still opens and still draws both options -
        George: *"I wouldn't hide this time as settings is different than
        the now playing screen when it comes to capabilities"* - and the
        one that cannot be had says why.
        """
        if output is not None and output.control is None:
            settings.restrict(
                "output_mode",
                {"Variable": f"{output.label} has no volume control of its own."},
            )
        else:
            settings.restrict("output_mode", {})

    async def _switch_output() -> None:
        """Put the chosen output into `output.conf` and reopen everything.

        **ADR-0055 §2, George: a switch may interrupt playback.** ALSA reads
        this file when a PCM is *opened*, so a renderer already playing
        would carry on to the old card indefinitely; restarting them is
        what makes the change mean something.

        **This daemon restarts with them**, and that is deliberate rather
        than lazy: the chosen card brings its own volume control name -
        `DAC` here, `PCM` on the headphone jack, none at all on HDMI - and
        rediscovering it at startup is one path instead of three mutable
        ones threaded through the bridges.
        """
        chosen = outputs.resolve(settings.value("output_device"))
        if chosen is None:
            logger.error("outputs: nothing to switch to")
            return

        # **Everything the user can see changes now, before the slow part**
        # (George: *"Changing the output is slow at changing the volume
        # output type. It should be nearly instant."*). None of it needs
        # the sound card: the mode, the greyed option, the padlock and the
        # visualiser button are all consequences of *which output was
        # chosen*, which is already known.
        nonlocal forced_fixed
        forced_fixed = chosen.control is None
        alsa.set_card(chosen.card)
        _restrict_output_mode(chosen)
        volume_bridge.set_mixer_name(chosen.control or config.mixer_name)
        # The monitor watches one card and was spawned for the old one; its
        # own loop restarts it, so ending it is enough to move it.
        volume_bridge.restart_monitor()
        state_store.set_meters(outputs.needs_plug(chosen.card) is not True)
        _choose_output_mode()
        state_store.bump_settings_revision()

        # Long enough for the settings write to have been answered.
        await asyncio.sleep(0.5)
        # **Stopped before the file is written, not after.** The config is
        # rewritten under whoever holds the old card otherwise - and worse,
        # `needs_plug` has to *open* the new card to ask what it takes, so
        # a renderer still holding it makes the question unanswerable. That
        # is how HDMI was written back with no conversion layer at all on
        # 2026-09-23: the card was busy, the query returned nothing, and
        # nothing was taken for "needs nothing".
        logger.info("outputs: stopping the renderers to switch to %s", chosen.label)
        stop = await asyncio.create_subprocess_exec(
            "systemctl", "stop", "squeezelite.service", "go-librespot.service",
            "bluealsa-aplay.service",
        )
        await stop.wait()
        outputs.write(chosen, tuning=_tuning())
        # **This daemon is not restarted any more.** It was, to pick up the
        # new card's control name; that name is now settable in place
        # (`VolumeBridge.set_mixer_name`), and the restart was most of what
        # made the switch feel slow - the panel lost its websocket and
        # everything with it.
        logger.info("outputs: starting the renderers again for %s", chosen.label)
        await asyncio.create_subprocess_exec(
            "systemctl", "restart", "squeezelite.service", "go-librespot.service",
            "bluealsa-aplay.service",
        )

    def _tuning() -> outputs.Tuning:
        """ADR-0058's two peppyalsa numbers, as the settings have them."""
        return outputs.Tuning(
            decay_ms=int(settings.value("meter_fall") or outputs.DECAY_MS),
            smoothing_factor=int(
                settings.value("spectrum_smoothing")
                if settings.value("spectrum_smoothing") is not None
                else outputs.SMOOTHING_FACTOR
            ),
        )

    async def _rewrite_output_conf(reason: str) -> None:
        """Put the current output and tuning in `output.conf` and reopen.

        **The renderers stop first.** Not for politeness: `outputs.write`
        has to *open* the card to ask whether it needs a conversion layer,
        and a card someone is holding answers nothing (LESSONS case 21).
        They restart afterwards, which is also what makes the new file
        mean anything - ALSA reads it when a PCM is opened.
        """
        chosen = outputs.resolve(settings.value("output_device"))
        if chosen is None:
            logger.error("outputs: nothing to write the tuning to")
            return
        logger.info("outputs: stopping the renderers - %s", reason)
        stop = await asyncio.create_subprocess_exec(
            "systemctl", "stop", "squeezelite.service", "go-librespot.service",
            "bluealsa-aplay.service",
        )
        await stop.wait()
        outputs.write(chosen, tuning=_tuning())
        await asyncio.create_subprocess_exec(
            "systemctl", "restart", "squeezelite.service", "go-librespot.service",
            "bluealsa-aplay.service",
        )

    def _apply_scope_tuning(_value=None) -> None:
        """`spectrum_smoothing` and `meter_fall` both live in `output.conf`."""
        asyncio.ensure_future(_rewrite_output_conf("the visualisation was retuned"))

    def _apply_meter_smoothing(value=None) -> None:
        """`meter_smoothing` lives in PeppyMeter's own config, which it reads
        once at start - so this restarts the visualiser, and only when the
        file actually changed."""
        window = int(value if value is not None else (settings.value("meter_smoothing") or 240))
        if not set_meter_smoothing(window, Path(config.meter_consumer_config)):
            return

        async def restart() -> None:
            await asyncio.create_subprocess_exec(
                "systemctl", "restart", "gexis-peppy.service"
            )

        asyncio.ensure_future(restart())

    def _start_sweep(kind: str) -> None:
        """ADR-0059. Refused rather than queued while the other one runs."""
        if not sweep.start(kind):
            logger.info("sweep: %s not started", kind)
        state_store.bump_settings_revision()

    def _choose_output_mode(value=None) -> None:
        fixed_wanted["value"] = forced_fixed or (
            value or settings.value("output_mode")
        ) == "Fixed"
        asyncio.ensure_future(_apply_output_mode())

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

    async def _reclaim_lms() -> None:
        """**Take the device back for LMS when a session ends** (ADR-0022's
        `reclaim_lms`, wired 2026-09-25).

        **Off by design and opt-in by row.** ADR-0027 declines to do this:
        nothing is restored because nothing was stored, and the reclaims
        that were measured were spurious - a Spotify session ending because
        the phone locked would drag LMS back on. Somebody who wants it can
        have it; nobody gets it by accident.
        """
        lms_adapter = adapters.get("lms")
        if lms_adapter is None or not hasattr(lms_adapter, "activate"):
            return
        # ADR-0077: nothing reclaims the device for a source that is off.
        if not renderer_enabled("lms"):
            return
        try:
            await lms_adapter.activate()
            logger.info("reclaim: LMS taken back after the session ended")
        except Exception as exc:
            # Whoever released the device has already released it; failing
            # to take it back is not that renderer's problem.
            logger.warning("reclaim: could not take the device back for LMS: %s", exc)

    def on_active_change(renderer_id: str | None) -> None:
        state_store.set_active(renderer_id)
        # ADR-0053: the number on the panel belongs to whoever holds the
        # device, so a takeover changes what it means - from one renderer's
        # scale to another's, or to the hardware's own with nobody active.
        publish_volume()
        # Nobody holds it, and somebody asked for LMS to step in.
        if renderer_id is None and settings.value("reclaim_lms"):
            asyncio.ensure_future(_reclaim_lms())

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
        # ADR-0077: a source that is switched off does not take the device,
        # whatever fired - an event from an instance that had not died yet,
        # `activate` from a phone, the reclaim above.
        enabled=lambda renderer_id: renderer_enabled(renderer_id),
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
        # ADR-0077. The supervisor refuses it too, but refusing here means a
        # renderer that is off is not woken up first and then ignored - LMS's
        # `activate` powers a player on.
        if not renderer_enabled(renderer_id):
            logger.info("command: %s is switched off, not activating", renderer_id)
            return False
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

    def image_info() -> dict[str, str]:
        """What the image stage wrote about this build, or nothing.

        `key=value` a line, because it is read by a shell during the build
        as readily as by this. Unreadable or absent is not a failure: a
        device flashed before the stage existed simply does not know.

        **`built` falls back to `/etc/rpi-issue`**, which pi-gen writes on
        every image it makes, ours included - so a device flashed before the
        stage existed still reports the date its image was built, which is
        what the row asks. There is no equivalent for `version`: the git
        describe is ours and nothing else on the device carries it, so that
        one stays honest and says it does not know.
        """
        out = {}
        try:
            text = Path("/etc/gexis/image.info").read_text()
        except OSError:
            text = ""
        for line in text.splitlines():
            name, _, value = line.partition("=")
            if value:
                out[name.strip()] = value.strip()
        if not out.get("built"):
            try:
                # "Raspberry Pi reference 2026-09-19" on its first line.
                first = Path("/etc/rpi-issue").read_text().splitlines()[0]
            except (OSError, IndexError):
                first = ""
            stamp = re.search(r"\d{4}-\d{2}-\d{2}", first)
            if stamp:
                out["built"] = stamp.group(0)
        return out

    # ADR-0035. Defaults are what is true of this deployment today. A wired
    # row is read where it is used - the idle page probe here, the rest by
    # the UI - so none needs a callback.
    settings = Settings(
        settings_store,
        defaults={
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
            # ADR-0059. George's own wording: "X out of Y processed (searched
            # for), Z artist portraits found."
            "sweep_status": lambda: sweep.progress.sentence,
            # **Which build this is** (ADR-0022's `version` row, wired
            # 2026-09-25). The image writes `/etc/gexis/image.info` because
            # nothing on a running device reported it: the `.info` beside
            # the image in `deploy/` is on the build host, not here. A
            # device flashed before that stage existed says so rather than
            # showing an empty row.
            "version": lambda: image_info().get("version") or "unknown",
            "image_build": lambda: image_info().get("built") or "unknown",
        },
        # ADR-0051 §4: which skins there are depends on where they are
        # installed and on what `skin_corpus` holds, neither of which the
        # registry module can know.
        options={
            "skin_corpus": skins_offered,
            # ADR-0055 §1: discovered, not written down. Re-read on every
            # `/settings`, so plugging an HDMI cable in changes the list
            # without a restart.
            "output_device": lambda: [o.option for o in outputs.discover()],
        },
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
               # ADR-0059: read on every ask through `gate` and
               # `confidence_min`, so nothing has to happen on the write.
               "enrichment": None, "lyrics": None, "artwork_lookup": None,
               "confidence": None,
               "idle_screen": None, "idle_background": None,
               "background_brightness": None, "background_interval": None,
               "wallpaper_key": None, "wallpaper_topics": None,
               "idle_weather": None,
               "weather_location": None, "idle_forecast": None,
               "idle_icons": None,
               "viz_timeout": None, "viz_stop": None,
               # ADR-0022's handoff rows, wired 2026-09-25. Read where they
               # are used - the adapter at a takeover, the panel for the
               # transition screen - so none needs a callback.
               "restore_transport": None, "reclaim_lms": None,
               # ADR-0078: read by the panel, which is where the screen is
               # drawn and therefore where the wait belongs. Nothing in the
               # daemon has an opinion on it.
               "handoff_threshold": None,
               # The agent reads both per request; `bt_pairing` also needs
               # BlueZ told, because the capability is fixed when the agent
               # registers and `NoInputNoOutput` means BlueZ never asks.
               "bt_pairing": lambda mode: asyncio.ensure_future(_apply_pairing(mode)),
               "bt_autotrust": None,
               # ADR-0077's three source toggles, wired 2026-09-25. Off stops
               # and disables the renderer's unit, stops its adapter watching,
               # reports it unavailable and makes arbitration refuse it - a row
               # that only the panel honoured would not be a switch, because
               # all three sources are reachable without the panel.
               "lms_enabled": lambda _=None: asyncio.ensure_future(
                   _apply_renderer("lms")
               ),
               "spotify_enabled": lambda _=None: asyncio.ensure_future(
                   _apply_renderer("spotify")
               ),
               "bt_enabled": lambda _=None: asyncio.ensure_future(
                   _apply_renderer("bluetooth")
               ),
               # ADR-0077. Turning this on from the panel closes the panel; it
               # is reversible from a phone, and only from a phone.
               "headless": lambda value: asyncio.ensure_future(
                   _apply_headless(value)
               ),
               "show_transition": None, "handoff_duration": None,
               # ADR-0052 §3: read on every map between a position and a
               # level, and re-applied here when it changes so the level
               # comes down at once if it is now above the ceiling.
               "max_ceiling": lambda _value=None: _reapply_level(),
               # ADR-0054 §3's two curves, wired 2026-09-23. A change moves
               # the level under a slider that has not been touched, so it
               # is re-applied rather than waiting for the next change.
               "travel_curve": lambda _value=None: _reapply_level(),
               # ADR-0046: chosen now, in force at the next legal moment.
               "output_mode": _choose_output_mode,
               # ADR-0055: rewrites output.conf, then restarts everything
               # that holds a PCM - including this daemon, which is how the
               # new card's control name gets picked up.
               "output_device": lambda _value=None: asyncio.ensure_future(
                   _switch_output()
               ),
               # Readonly: nothing to do on a write, and the value is the
               # live one below rather than the registry's literal.
               "volume_managed": None,
               # ADR-0051: read by the driver, through the file these write.
               "skin": publish_visualisation,
               "skin_rotate": publish_visualisation,
               "skin_corpus": apply_corpus,
               # ADR-0058. Two of the three are peppyalsa's and go in
               # `output.conf`; the third is PeppyMeter's own.
               "spectrum_smoothing": _apply_scope_tuning,
               "meter_fall": _apply_scope_tuning,
               "meter_smoothing": _apply_meter_smoothing,
               "home_strip": None, "home_strip_count": None,
               "idle_clock": None,
               "device_name": apply_device_name,
               "bt_discoverable": lambda mode: asyncio.ensure_future(
                   _apply_discoverable(mode)
               ),
               "timezone": lambda zone: asyncio.ensure_future(_set_timezone(zone)),
               # ADR-0059's two buttons. `start` refuses rather than queues
               # while the other is running - a queued button is a progress
               # bar that lies.
               "sweep_portraits": lambda _=None: _start_sweep("portraits"),
               "sweep_covers": lambda _=None: _start_sweep("covers"),
               "sweep_status": None,
               # Readonly, and listed here for the same reason
               # `volume_managed` is: it is how a row says it reports
               # something rather than nothing (ADR-0022's `version`).
               "version": None, "image_build": None,
               "reboot": lambda _: asyncio.ensure_future(_reboot()),
               # **ADR-0083.** A backup that stays on the device does not
               # survive the event it exists for, so this writes into a share
               # of its own. `restore` is the other half and is a `list` row -
               # its items are what is in that share, so one copied in from
               # another machine is offered too.
               "backup": lambda _=None: asyncio.ensure_future(_make_backup()),
               "restore": None},
        # **Phase 9 criterion 2.** These two act through
        # `POST /settings/{key}/items`, not through `set` - joining a network
        # and forgetting a device - so they are wired, and saying otherwise
        # made the panel mark two working rows `data-unwired`. `lms_server`
        # is a list too and is already in `wired` above, because something
        # also reads its value.
        lists={"wifi", "bt_trusted"},
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

    #: The agent's own bus, kept so the capability can be changed without a
    #: restart (ADR-0022's `bt_pairing`).
    pairing_bus: list = []

    async def _apply_pairing(mode: str) -> None:
        """Confirmation or PIN-free, applied now rather than at next boot.

        The capability is fixed when the agent registers, so this
        unregisters and registers again. George, 2026-09-25: *"confirmation
        is default, pin free as viable option."*
        """
        if not pairing_bus:
            return
        bus = pairing_bus[0]
        await bluetooth_agent.unregister(bus)
        await bluetooth_agent.register(
            bus, pairing_agent, bluetooth_agent.capability_for(mode)
        )

    async def _make_backup() -> None:
        """**Everything a flash destroys, into the Backups share** (ADR-0083).

        Off the loop: it reads the enrichment cache, which was 12 MB on
        George's device, and gzips it.
        """
        try:
            name = await asyncio.to_thread(
                backups.create, settings.value("device_name") or "gexis"
            )
        except Exception as exc:  # noqa: BLE001 - a backup is never fatal
            logger.warning("backup: failed: %s", exc)
            return
        logger.info("backup: %s", name)
        # The Restore row lists the share, so a new archive has to reach the
        # panel without it being reopened.
        state_store.bump_settings_revision()

    def renderer_enabled(renderer_id: str) -> bool:
        """**ADR-0077.** Whether that source is switched on.

        Unset reads as on: the rows default to true and an absent value is a
        device that has never been to Settings, not a device with no sources.
        A row that is not in `RENDERER_ROWS` - a plugin renderer, one day - has
        no switch and is always on.
        """
        row = RENDERER_ROWS.get(renderer_id)
        if row is None:
            return True
        return settings.value(row) is not False

    #: Set when a source row flips, so the run gates below re-read rather than
    #: poll. One event for all three: a wakeup is cheap and a gate that finds
    #: its own row unchanged goes straight back to waiting.
    sources_changed = asyncio.Event()

    async def _run_renderer(renderer_id: str, adapter, on_acquire, on_release) -> None:
        """**Run the adapter while its row is on, and not while it is off**
        (ADR-0077).

        The gate is here rather than inside the adapter because ADR-0013 says
        the three defaults implement the public plugin contract and are not
        special-cased - a plugin that read a settings row named after itself to
        decide whether to run would put that row in the contract. Whether a
        renderer runs at all is the core's business.

        Cancellation is the mechanism and it is safe to use: all three `run()`
        methods catch `Exception`, not `BaseException`, so a cancel propagates
        out of their retry loops instead of being swallowed and retried, and
        each holds its connection in an `async with` that closes on the way
        out. It also settles what would otherwise be permanent noise - with
        `go-librespot` stopped, the Spotify adapter's watch retries every five
        seconds forever, logging a warning each time.
        """
        task: asyncio.Task | None = None
        try:
            while True:
                wanted = renderer_enabled(renderer_id)
                if wanted and task is None:
                    logger.info("sources: %s is on, watching", renderer_id)
                    task = asyncio.ensure_future(adapter.run(on_acquire, on_release))
                elif not wanted and task is not None:
                    logger.info("sources: %s is off, stopping its watch", renderer_id)
                    task.cancel()
                    # The adapter is gone, so nothing will report this itself.
                    # Said here rather than left at whatever it was, or the
                    # panel keeps offering a source that is switched off.
                    state_store.set_available(renderer_id, False)
                    task = None
                sources_changed.clear()
                await sources_changed.wait()
        finally:
            if task is not None:
                task.cancel()

    async def _apply_renderer(renderer_id: str) -> None:
        """A source row was written: make the device match it (ADR-0077)."""
        on = renderer_enabled(renderer_id)
        adapter = adapters.get(renderer_id)
        if adapter is None:
            return
        # The unit first. Off, this stops the renderer and keeps it stopped
        # across a reboot; on, it starts it and asks for it at the next boot
        # too. Both are idempotent, so a row rewritten to the value it already
        # had is a no-op rather than a restart.
        await set_unit_enabled(adapter.unit_name, on)
        if renderer_id == "bluetooth":
            await set_unit_enabled(BLUETOOTH_SETUP_UNIT, on)
            bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
            try:
                await bluetooth_adapter_state.set_powered(bus, on)
                if on:
                    # Powering up does not restore what the row asked for, and
                    # `gexis-bluetooth-setup.service` may not have re-run yet.
                    await bluetooth_adapter_state.apply_discoverable(
                        bus, settings.value("bt_discoverable") or "3 min after boot"
                    )
            finally:
                bus.disconnect()
        if not on:
            # **The renderer that was switched off must not stay the active
            # one** (found on the panel 2026-09-25, building ADR-0079: with
            # Spotify switched off mid-track, Now Playing went on showing its
            # track indefinitely). Its adapter's watch is cancelled below, so
            # the `inactive` event that would normally release the device
            # never arrives - nobody is left to report it. Said here instead,
            # which is what the adapter would have said.
            #
            # `relinquish` is ignored unless this renderer is still the active
            # one, so this is safe whatever was holding the device.
            await supervisor.relinquish(renderer_id)
            state_store.set_available(renderer_id, False)
        # Last, so the watch starts against a unit that is already running and
        # stops after the unit it was watching has gone.
        sources_changed.set()

    async def _apply_headless(headless) -> None:
        """**ADR-0077: `headless` turns off three units, not one.**

        Turning this on from the panel closes the panel - that is the row doing
        what it says, and it is reversible from a phone. The kiosk unit's own
        `ExecStopPost` puts the text console back, so the screen shows a
        console rather than a black panel nobody can tell from a failed boot.
        """
        wanted = not headless
        logger.info("display: headless=%s, local screen %s", bool(headless), "on" if wanted else "off")
        for unit, now in SCREEN_UNITS:
            await set_unit_enabled(unit, wanted, now=now)

    async def _reconcile_sources() -> None:
        """**Make the device match the rows at startup** (ADR-0077).

        Only the rows that are *off* are enforced. A row that is on wants what
        the image ships - the unit enabled - so there is nothing to do, and
        `enable --now` on every boot would re-run Bluetooth's power-up and
        discoverability on top of `_bluetooth_setup` for no reason.

        Off is enforced because the two can drift: the settings DB survives an
        image update that re-enables the unit, and then the row would say off
        while the renderer ran.
        """
        for renderer_id in RENDERER_ROWS:
            if renderer_id in adapters and not renderer_enabled(renderer_id):
                logger.info("sources: %s is off at startup, enforcing", renderer_id)
                await _apply_renderer(renderer_id)
        if settings.value("headless"):
            await _apply_headless(True)

    async def _bluetooth_setup() -> None:
        # ADR-0077: nothing advertises a radio the row says is off. The agent
        # below still registers - it costs nothing, and turning the row back on
        # then has one rather than pairing falling back to whatever BlueZ's
        # default answers.
        if renderer_enabled("bluetooth"):
            await _apply_discoverable(
                settings.value("bt_discoverable") or "3 min after boot", attempts=10
            )
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        pairing_bus.append(bus)
        await bluetooth_agent.register(
            bus,
            pairing_agent,
            bluetooth_agent.capability_for(settings.value("bt_pairing")),
        )
        # The bus stays open for the process: an agent whose connection
        # closes is unregistered by BlueZ, silently, and pairing goes back
        # to whatever answered before.
        await bus.wait_for_disconnect()

    asyncio.ensure_future(_reconcile_sources())
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
        # ADR-0055 §6: nothing raises a screen this output cannot feed.
        has_levels=lambda: state_store.state.meters,
    )

    # **ADR-0055 §5.** An output with no volume control takes the choice
    # away, so the row says Fixed and refuses a write rather than offering
    # one that cannot be honoured. The user's own choice is never
    # overwritten - the lock sits *over* the stored value - so switching
    # back to an output that can attenuate hands it straight back.
    _restrict_output_mode(chosen_output)
    if forced_fixed:
        asyncio.ensure_future(_apply_output_mode())

    state_store.set_meters(meters_available)

    previous_active = state_store.state.active

    async def _find_cover(renderer_id: str, metadata) -> None:
        """**The cover for a track the renderer sent none for** (ADR-0081).

        Through the same `EnrichmentService` and cache the panel's
        `/enrichment` route uses, so the panel's own request - which arrives a
        moment later for the same track and asks every provider - is answered
        from the cache rather than repeating this.
        """
        key = TrackKey.of(metadata)
        for attempt in range(COVER_LOOKS):
            # The track may have changed while the last look was in flight.
            # `set_found_artwork` keys on the track so a late answer cannot
            # apply to the wrong one, but there is no point asking again.
            current = state_store.state
            if current.active != renderer_id or TrackKey.of(current.metadata) != key:
                return
            pending: list[str] = []
            try:
                found = await enrichment.for_track(key, renderer=renderer_id,
                                                   only=ARTWORK_PROVIDERS,
                                                   pending=pending)
            except Exception as exc:  # noqa: BLE001 - a lookup is never fatal
                logger.warning("cover: could not look one up for %r: %s", key.title, exc)
                return
            # **`for_track` answers with what it has after `WAIT_S` and lets
            # the slow ones finish behind it.** Found on the device
            # 2026-09-25: the first ask returned nothing and logged "coverart
            # is still going", the provider cached its answer a moment later,
            # and nobody ever asked again - so the cover existed on this
            # device and the meter still drew none. The panel already looks
            # back for exactly this reason (`enrichment.js`); the daemon has
            # to as well, or it is the panel's fallback all over again.
            if found.album_art or not pending:
                break
            if attempt + 1 < COVER_LOOKS:
                await asyncio.sleep(COVER_LOOK_BACK_S)
        state_store.set_found_artwork(renderer_id, metadata, found.album_art)

    def follow_playback(state) -> None:
        nonlocal previous_active
        # ADR-0018/0046: a mode change waits for playback to stop, and this
        # is where stopping is noticed.
        if fixed_wanted["value"] != fixed_now["value"]:
            asyncio.ensure_future(_apply_output_mode())
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
    # LMS's own artist photos and biographies, where the server has the
    # plugin (ADR-0040 §1). Shares the library's HTTP session.
    enrichment_cache = Cache()
    library = LmsLibrary(config.lms_host, config.lms_port, player_id=lambda: lms.player_id,
                         # ADR-0059: fanart covers the sweep found, LMS's otherwise.
                         store=enrichment_cache)
    # ADR-0071: a queue this daemon changed is re-read at once, instead of
    # waiting about 1.2s for LMS to report back something we just did.
    library.on_queue_changed(lms.queue_changed_by_us)
    # ADR-0022's `restore_transport`, wired 2026-09-25. Read at the moment
    # of the takeover rather than held, so a change takes effect without a
    # restart. `settings` is built below, hence the late binding.
    lms.on_restore_transport(lambda: settings.value("restore_transport"))
    artistinfo = LmsArtistInfo(library.rpc, f"http://{config.lms_host}:{config.lms_port}",
                               store=enrichment_cache)
    # ADR-0040 §1: LMS's own plugin first where it answers, the key-free
    # providers behind it and for the renderers that have no LMS ids.
    http = Http()
    # One MusicBrainz lookup for the artist, shared: two providers needed the
    # same id and each was searching for it (see ArtistIdentity).
    identity = ArtistIdentity(http, store=enrichment_cache)
    # ADR-0059's two buttons, which share this walk: the album artists, their
    # MusicBrainz ids, and one fanart call each that answers the portrait and
    # every album cover at once (Finding 054 §9).
    sweep = ArtworkSweep(
        library,
        identity,
        http,
        enrichment_cache,
        fanart_key=lambda: settings.value("fanart_key"),
        # George, 2026-09-24: *"Use the confidence level for sure."* `Head`
        # resolved at 100 and there is no telling it is the right Head.
        confidence=lambda: int(settings.value("confidence") or 0),
        on_change=state_store.bump_settings_revision,
        # Once at the end: the panel's answer to this is to drop every
        # artist photo it holds and ask again.
        on_finish=state_store.bump_pictures_revision,
    )
    #: ADR-0059: Enrichment's own rows, wired at last. Each is a reason not
    #: to *ask* somebody rather than a reason to throw their answer away.
    #: `artwork_lookup` is the automatic half of the album-cover button
    #: (George, 2026-09-24: *"automatic way for sure"*) - new albums get a
    #: cover as they arrive, and the button does the library on demand.
    LYRIC_PROVIDERS = ("lrclib",)
    ARTWORK_PROVIDERS = ("coverart", "recording-art")

    def _may_ask(name: str) -> bool:
        if settings.value("enrichment") is False:
            return False
        if name in LYRIC_PROVIDERS and settings.value("lyrics") is False:
            return False
        if name in ARTWORK_PROVIDERS and settings.value("artwork_lookup") is False:
            return False
        return True

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
        # ADR-0022's rows, wired 2026-09-24. Read on every ask, not captured
        # at startup: a threshold typed into Settings has to mean something
        # before the next reboot.
        confidence_min=lambda: int(
            settings.value("confidence") if settings.value("confidence") is not None
            else CONFIDENCE_MIN
        ),
        gate=_may_ask,
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
            # **ADR-0081: and the cover, for a renderer that sent none.**
            # Bluetooth over AVRCP, a radio stream. Here rather than when a
            # panel happens to ask, because PeppyMeter is another process
            # with no client for `/state` (ADR-0014) and its artwork cannot
            # depend on a browser page being alive and un-occluded - which is
            # exactly what raising the meter over the panel makes unlikely.
            #
            # **Not speculative, so `prefetch`'s local-only rule does not
            # bind it** (Finding 036): this is a track that demonstrably has
            # no cover, and the panel's own `/enrichment` asks these same two
            # providers for it moments later anyway. It rides this debounce
            # so that skipping through an album still costs nothing.
            if state.active and state.metadata.artwork is None:
                await _find_cover(state.active, state.metadata)

        prefetch_task = asyncio.ensure_future(warm())
        prefetch_task.gexis_key = key

    state_store.subscribe(warm_enrichment)

    async def _check_lms_volume_control() -> None:
        """**Say so when LMS's player is on fixed volume** (Phase 9 criterion
        4, from the handoff's issues list).

        `digitalVolumeControl` at 0 means LMS moves its own number and always
        sends full level, so **no LMS volume change ever reaches the device**.
        George hit it on 2026-09-16 as *"phone volume does nothing while the
        panel is muted, and LMS's volume bar is frozen"* - and mute became a
        trap, because the one change that ends it (ADR-0034) never arrived.
        Nothing in this repository sets it and nobody set it by hand; the
        cause is still unknown.

        **This only says so.** Writing a pref on somebody's music server
        because we disagree with it is not ours to do, and the value is a
        real choice for anybody driving the DAC from elsewhere. A line in the
        journal turns an unexplainable symptom into a greppable one, which is
        the whole of what was missing.
        """
        for _ in range(15):
            if lms.player_id:
                break
            await asyncio.sleep(2)
        else:
            return
        try:
            answer = await library.rpc(
                ["playerpref", "digitalVolumeControl", "?"], lms.player_id
            )
        except Exception as exc:  # noqa: BLE001 - a check is never fatal
            logger.info("lms: could not read digitalVolumeControl: %s", exc)
            return
        value = str((answer or {}).get("_p2", ""))
        if value == "0":
            logger.warning(
                "lms: player %s has digitalVolumeControl=0 (fixed volume). LMS will "
                "move its own number and always send full level, so no volume change "
                "from LMS or a phone reaches this device, and mute cannot be ended "
                "from there. Set it to 1 in LMS's player settings.",
                lms.player_id,
            )
        elif value:
            logger.info("lms: digitalVolumeControl=%s on %s", value, lms.player_id)

    if renderer_enabled("lms"):
        asyncio.ensure_future(_check_lms_volume_control())

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
        # ADR-0059: where the artwork sweep leaves what it found.
        notes=enrichment_cache,
        # ADR-0038 §8: the one SlimBrowse subtree, browsed by handles the
        # core issues.
        radio=RadioBrowser(library.rpc, lambda: lms.player_id),
        # ADR-0045: the panel's answer, back to the agent that is holding
        # BlueZ's handshake open waiting for it.
        pairing_answer=pairing_agent.answer,
        # ADR-0083: what "restart the device" means is the daemon's to say.
        restore=_restore_done,
        # ADR-0086: the panel asks for a source's mark by id; the daemon is
        # the only thing that knows where manifests live.
        plugins=installed_plugins,
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
        # ADR-0077: through the gate, not directly - an adapter runs while its
        # source row is on and not while it is off.
        *(
            _run_renderer(rid, adapter, make_on_acquire(rid), make_on_release(rid))
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
