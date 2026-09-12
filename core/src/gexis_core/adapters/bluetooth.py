# SPDX-License-Identifier: GPL-3.0-or-later
"""Bluetooth (A2DP) adapter, via BlueZ's system D-Bus API.

Transport per ARCHITECTURE.md §8's adapter table: `org.bluez.MediaPlayer1`,
watched via D-Bus `PropertiesChanged`. Acquisition is "A2DP profile
connect" (ADR-0010's table), not stream start - so this watches for a
MediaPlayer1 object to *appear* (via ObjectManager's InterfacesAdded),
which BlueZ only exposes once a phone has connected the A2DP+AVRCP
profiles, rather than watching PlaybackStatus on an object that may
already exist from a previous connection. Confirmed against a live phone
connect on `gexis`, 2026-09-08 - MediaPlayer1 does appear reliably on
connect.

**Second, earlier trigger added 2026-09-10 (Finding 010 §3, ADR-0010
amendment): also acquire on `org.bluez.MediaTransport1` appearing**, at
a `.../dev_XX/fdN` object path - confirmed both against BlueZ's own
doc/media-api.txt ("MediaTransport1 hierarchy", object path
`.../dev_XX_XX_XX_XX_XX_XX/fdX`) and directly in `gexis`'s own bluealsa
log, which shows `fdN` appearing via InterfacesAdded well before
`bluealsa-aplay` ever attempts to open its ALSA playback PCM. Finding
010 measured a ~1s gap between transport-start and `bluealsa-aplay`'s
PCM-open attempt racing our old MediaPlayer1-only trigger; this closes
it by acquiring at the earliest BlueZ control-plane signal available,
same "not stream start" spirit as MediaPlayer1 (the transport object
exists once profile negotiation begins, independent of whether audio is
flowing yet - it starts in "idle"/"pending" state, matching
media-api.txt's own State property, not "active"). Whichever of the two
signals arrives first wins; the other is a harmless idempotent re-fire
into `on_acquire()`.

release() disconnects the Device1 that owns the MediaPlayer1 - matches
ADR-0010's "Bluetooth: disconnect" (the AVRCP-pause alternative was
designed and explicitly rejected, see ADR-0010's "Rejected alternatives").
"""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

from dbus_next import BusType
from dbus_next.aio import MessageBus

from gexis_core.adapters.base import Adapter, Capabilities, ReleaseAction, VolumeMechanism
from gexis_core.model import TrackMetadata
from gexis_core.systemd import kill_unit
from gexis_core.volume import DUMMY_CARD_BLUETOOTH

logger = logging.getLogger("gexis_core.adapters.bluetooth")

BLUEZ_SERVICE = "org.bluez"
OBJECT_MANAGER_IFACE = "org.freedesktop.DBus.ObjectManager"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
DEVICE_IFACE = "org.bluez.Device1"
MEDIA_PLAYER_IFACE = "org.bluez.MediaPlayer1"
MEDIA_TRANSPORT_IFACE = "org.bluez.MediaTransport1"
UNIT_NAME = "bluealsa-aplay.service"


def _ms_to_s(value) -> float | None:
    return value / 1000.0 if isinstance(value, (int, float)) else None


#: BlueZ's `MediaPlayer1.Status` values (org.bluez.MediaPlayer.rst) mapped
#: onto the normalised transport vocabulary (Phase 4 criterion 3). The two
#: seek states report as playing because that is what they are - audio is
#: running, the position is moving unusually - and "error" reports as None
#: rather than being invented as stopped, since we genuinely do not know.
TRANSPORT_STATUS = {
    "playing": "playing",
    "paused": "paused",
    "stopped": "stopped",
    "forward-seek": "playing",
    "reverse-seek": "playing",
}

#: A2DP codec IDs as they appear in `MediaTransport1.Codec` (a byte).
#: Phase 4 criterion 3 shows this where a sample rate would otherwise go,
#: per ADR-0019: "the decode rate is the codec's, not the source's."
#: 0xFF is A2DP's vendor-specific escape - aptX, LDAC and friends live
#: behind it and need the vendor ID parsed out of `Configuration` to name,
#: which is not done here: "vendor" is honest, a guess would not be.
A2DP_CODECS = {0x00: "SBC", 0x01: "MP3", 0x02: "AAC", 0x04: "ATRAC", 0xFF: "vendor"}


def _unwrap(props: dict) -> dict:
    """`org.freedesktop.DBus.ObjectManager`/`PropertiesChanged` values are
    dbus_next `Variant`s - `.value` unwraps to a plain Python value.
    Matches bluetooth_trust.py's own `device.get("Paired").value` idiom
    rather than dbus_next's introspection-generated property getters, so
    this doesn't depend on BlueZ's introspection XML shape being what
    dbus_next's codegen expects.
    """
    return {key: variant.value for key, variant in props.items()}


class BluetoothAdapter(Adapter):
    renderer_id = "bluetooth"
    release_action = ReleaseAction.DISCONNECT
    unit_name = UNIT_NAME
    # Phase 3 criterion 2. Two acquisition signals (Finding 010 §3,
    # ADR-0010 amendment): MediaTransport1 fires earlier than
    # MediaPlayer1 during profile negotiation, closing a ~1s race a
    # MediaPlayer1-only trigger used to lose. No artwork or sample rate -
    # MediaPlayer1's Track dict (org.bluez.MediaPlayer.rst) has no such
    # fields at all, confirmed by BlueZ's own doc and by a live phone
    # connection, 2026-09-12 (HANDOFF.md), matching ADR-0014's expectation.
    capabilities = Capabilities(
        audio_connection="output",
        acquisition_events=frozenset({"media_player_appeared", "media_transport_appeared"}),
        supports_artwork=False,
        supports_sample_rate=False,
        # Finding 006: Bluetooth's own volume path isn't understood well
        # enough yet to restore a remembered level for it - not the same
        # question as *how* its live volume gets bridged (below), which
        # is unrelated and already correctly wired.
        volume_managed=False,
        volume_mechanism=VolumeMechanism.DUMMY_MIXER,
        dummy_mixer_card=DUMMY_CARD_BLUETOOTH,
    )

    def __init__(self) -> None:
        self._bus: MessageBus | None = None
        self._connected_device_path: str | None = None
        self._on_metadata: Callable[[TrackMetadata], None] | None = None
        self._on_availability: Callable[[bool], None] | None = None
        #: Track dict and Position (ms) are separate D-Bus properties that
        #: can change independently - merged the same way Spotify's
        #: "seek" event merges onto its last "metadata" event, so a
        #: Position-only update doesn't report a blank title/artist/album.
        self._last_track: dict = {}
        self._last_position_ms: int | None = None
        #: MediaPlayer1.Status, normalised (Phase 4 criterion 3).
        self._last_transport: str | None = None
        #: MediaTransport1.Codec, resolved to a name (criterion 3 shows it
        #: where a sample rate would go). Kept separately from the track
        #: because it belongs to the *connection*, not the track, and
        #: survives track changes within one session.
        self._last_codec: str | None = None

    def on_metadata_change(self, callback: Callable[[TrackMetadata], None]) -> None:
        """state.py hooks in here (Phase 3 criterion 1)."""
        self._on_metadata = callback

    def on_availability_change(self, callback: Callable[[bool], None]) -> None:
        """George's decision, 2026-09-12: "available" means BlueZ is
        reachable over D-Bus, independent of whether a phone is connected.
        True once the system bus connects, False while `run()`'s outer loop
        is in its retry sleep after losing the connection.
        """
        self._on_availability = callback

    def _report_metadata(self) -> None:
        if self._on_metadata is None:
            return
        self._on_metadata(
            TrackMetadata(
                title=self._last_track.get("Title"),
                artist=self._last_track.get("Artist"),
                album=self._last_track.get("Album"),
                # No artwork or sample rate over AVRCP - MediaPlayer1's
                # Track dict (doc/org.bluez.MediaPlayer.rst) has no such
                # fields, matching ADR-0014's "Bluetooth supplies no
                # artwork" expectation rather than an omission here.
                position=_ms_to_s(self._last_position_ms),
                duration=_ms_to_s(self._last_track.get("Duration")),
                source_type="bluetooth",
                transport=self._last_transport,
                codec=self._last_codec,
            )
        )

    async def run(self, on_acquire, on_release) -> None:
        while True:
            try:
                await self._watch(on_acquire, on_release)
            except Exception as exc:  # noqa: BLE001 - keep watching regardless
                logger.warning("bluetooth: D-Bus watch failed (%s), retrying in 5s", exc)
                if self._on_availability is not None:
                    self._on_availability(False)
                await asyncio.sleep(5)

    async def _watch(self, on_acquire, on_release) -> None:
        self._bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        introspection = await self._bus.introspect(BLUEZ_SERVICE, "/")
        root = self._bus.get_proxy_object(BLUEZ_SERVICE, "/", introspection)
        obj_manager = root.get_interface(OBJECT_MANAGER_IFACE)

        if self._on_availability is not None:
            self._on_availability(True)

        managed = await obj_manager.call_get_managed_objects()
        for path, ifaces in managed.items():
            if MEDIA_PLAYER_IFACE in ifaces:
                self._connected_device_path = self._device_path_for_player(path)
                logger.info("bluetooth: MediaPlayer1 already present at %s on startup", path)
                self._seed_metadata(ifaces[MEDIA_PLAYER_IFACE])
                asyncio.create_task(self._attach_media_player(path))
            if MEDIA_TRANSPORT_IFACE in ifaces:
                # A phone already connected when the daemon started - its
                # codec is readable right now and would otherwise not be
                # known until the next reconnection.
                self._seed_codec(ifaces[MEDIA_TRANSPORT_IFACE])

        obj_manager.on_interfaces_added(
            lambda path, interfaces: self._handle_interfaces_added(path, interfaces, on_acquire)
        )
        obj_manager.on_interfaces_removed(
            lambda path, interfaces: self._handle_interfaces_removed(path, interfaces, on_release)
        )

        # Idle forever; callbacks above do the work. Exits (and the outer
        # loop reconnects) only if the bus connection itself drops.
        await self._bus.wait_for_disconnect()

    def _handle_interfaces_added(self, path: str, interfaces: dict, on_acquire) -> None:
        """Extracted from `_watch` as a bound method, not a closure, so it's
        directly unit-testable - the closure shape is exactly how the
        `on_properties_changed` bug (found live, 2026-09-12) went
        unnoticed: nothing exercised it without real D-Bus."""
        if MEDIA_PLAYER_IFACE in interfaces:
            self._connected_device_path = self._device_path_for_player(path)
            logger.info("bluetooth: MediaPlayer1 appeared at %s (acquisition)", path)
            self._seed_metadata(interfaces[MEDIA_PLAYER_IFACE])
            asyncio.create_task(self._attach_media_player(path))
            on_acquire()
        if MEDIA_TRANSPORT_IFACE in interfaces:
            self._connected_device_path = self._device_path_for_player(path)
            logger.info("bluetooth: MediaTransport1 appeared at %s (acquisition)", path)
            self._seed_codec(interfaces[MEDIA_TRANSPORT_IFACE])
            on_acquire()

    def _handle_interfaces_removed(self, path: str, interfaces: dict, on_release) -> None:
        if MEDIA_PLAYER_IFACE in interfaces and path.startswith(
            self._connected_device_path or "\0"
        ):
            logger.info("bluetooth: MediaPlayer1 removed at %s (release)", path)
            self._connected_device_path = None
            self._last_track = {}
            self._last_position_ms = None
            self._last_transport = None
            self._last_codec = None
            self._report_metadata()
            # George, 2026-09-12: found live via the state WebSocket - a
            # Bluetooth disconnect never told the supervisor, so `active`
            # stayed pointed at Bluetooth indefinitely instead of going
            # back to "nobody" (ADR-0027) even though the metadata above
            # was already (separately) blanked. An oversight in the
            # original ADR-0027 work, not a deliberate deferral - same
            # shape as SpotifyAdapter's identical fix. Safe to call
            # unconditionally: Supervisor.relinquish() ignores this unless
            # bluetooth is still the active renderer, so the echo of our
            # own takeover-driven Device1.Disconnect() (which also removes
            # MediaPlayer1) is a no-op.
            on_release()

    def _seed_metadata(self, player_props: dict) -> None:
        """`player_props` is straight from ObjectManager (Variant-valued) -
        the initial snapshot, before any PropertiesChanged signal fires."""
        props = _unwrap(player_props)
        if "Track" in props:
            self._last_track = _unwrap(props["Track"])
        if "Position" in props:
            self._last_position_ms = props["Position"]
        if "Status" in props:
            self._last_transport = TRANSPORT_STATUS.get(props["Status"])
        self._report_metadata()

    def _seed_codec(self, transport_props: dict) -> None:
        """`transport_props` is `MediaTransport1`'s own snapshot from
        ObjectManager. The codec belongs to the connection rather than the
        track, so it is read once per connection here and then left alone -
        it does not change mid-session (a codec renegotiation would take a
        new transport object, which arrives as a fresh InterfacesAdded).
        """
        codec = _unwrap(transport_props).get("Codec")
        if codec is None:
            return
        self._last_codec = A2DP_CODECS.get(codec, "vendor")
        logger.info("bluetooth: codec %s (MediaTransport1.Codec=%s)", self._last_codec, codec)
        self._report_metadata()

    async def _attach_media_player(self, player_path: str) -> None:
        """Subscribes to this MediaPlayer1's own PropertiesChanged, so track
        changes and position updates after the initial snapshot are
        reported too - not just the acquisition edge `on_acquire()` needs.

        **Found broken on hardware, 2026-09-12** (George, testing against a
        real phone): `MediaPlayer1`'s own proxy interface has no
        `on_properties_changed` at all - confirmed by introspection,
        `PropertiesChanged` is a signal of the generic
        `org.freedesktop.DBus.Properties` interface, not of `MediaPlayer1`
        itself (whose own introspected `signals` list is empty). The fix is
        to get *that* interface's proxy instead - matching
        `bluetooth_trust.py`'s existing `PROPERTIES_IFACE` idiom for
        `call_set`, just for a signal instead of a method call. The
        double-unwrap for a dict-valued property like `Track` is unchanged
        and still not independently confirmed against a live payload
        (the crash above meant no payload was ever received to check).
        """
        try:
            introspection = await self._bus.introspect(BLUEZ_SERVICE, player_path)
            props = self._bus.get_proxy_object(
                BLUEZ_SERVICE, player_path, introspection
            ).get_interface(PROPERTIES_IFACE)
        except Exception as exc:  # noqa: BLE001 - metadata is best-effort
            logger.warning("bluetooth: could not attach to %s: %s", player_path, exc)
            return

        def on_properties_changed(interface_name, changed, invalidated):
            if interface_name != MEDIA_PLAYER_IFACE:
                # PropertiesChanged is per-object-path, not per-interface -
                # this object path could in principle carry another
                # interface's own changes too. Not observed in practice,
                # guarded rather than assumed away.
                return
            # `changed`'s values are Variants; "Track" is itself a
            # `dict[str, Variant]` (D-Bus `a{sv}`) once unwrapped once, so
            # it needs a second unwrap - the same two-level shape
            # `_seed_metadata` handles for the ObjectManager snapshot.
            changed = _unwrap(changed)
            if "Track" in changed:
                self._last_track = _unwrap(changed["Track"])
            if "Position" in changed:
                self._last_position_ms = changed["Position"]
            if "Status" in changed:
                self._last_transport = TRANSPORT_STATUS.get(changed["Status"])
            if {"Track", "Position", "Status"} & changed.keys():
                self._report_metadata()

        props.on_properties_changed(on_properties_changed)

    @staticmethod
    def _device_path_for_player(player_path: str) -> str:
        # BlueZ nests MediaPlayer1 under its owning Device1, e.g.
        # /org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF/player0 -> strip the
        # trailing /playerN segment to get the Device1 path.
        return player_path.rsplit("/", 1)[0]

    async def release(self) -> bool:
        if self._bus is None or self._connected_device_path is None:
            logger.warning("bluetooth: release() called with no known connected device")
            return False
        try:
            introspection = await self._bus.introspect(
                BLUEZ_SERVICE, self._connected_device_path
            )
            device = self._bus.get_proxy_object(
                BLUEZ_SERVICE, self._connected_device_path, introspection
            ).get_interface(DEVICE_IFACE)
            await device.call_disconnect()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("bluetooth: Device1.Disconnect() failed: %s", exc)
            return False

    async def signal_stop(self, force: bool) -> None:
        kill_unit(UNIT_NAME, force=force)
