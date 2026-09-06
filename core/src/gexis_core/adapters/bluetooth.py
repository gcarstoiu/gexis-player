"""Bluetooth (A2DP) adapter, via BlueZ's system D-Bus API.

Transport per ARCHITECTURE.md §8's adapter table: `org.bluez.MediaPlayer1`,
watched via D-Bus `PropertiesChanged`. Acquisition is "A2DP profile
connect" (ADR-0010's table), not stream start - so this watches for a
MediaPlayer1 object to *appear* (via ObjectManager's InterfacesAdded),
which BlueZ only exposes once a phone has connected the A2DP+AVRCP
profiles, rather than watching PlaybackStatus on an object that may
already exist from a previous connection.

**UNVERIFIED - flagged, not silently assumed:** this has not been
confirmed against a live phone connect. Whether MediaPlayer1's appearance
is the cleanest signal, versus e.g. Device1.Connected, needs one real BT
connect/disconnect cycle on `gexis` to confirm - the interactive
iteration loop this project already uses for units/config
(docs/DEVELOPMENT.md) applies here, not a rebuild-to-find-out.

release() disconnects the Device1 that owns the MediaPlayer1 - matches
ADR-0010's "Bluetooth: disconnect" (the AVRCP-pause alternative was
designed and explicitly rejected, see ADR-0010's "Rejected alternatives").
"""
from __future__ import annotations

import asyncio
import logging

from dbus_next import BusType
from dbus_next.aio import MessageBus

from gexis_core.adapters.base import Adapter, ReleaseAction
from gexis_core.systemd import kill_unit

logger = logging.getLogger("gexis_core.adapters.bluetooth")

BLUEZ_SERVICE = "org.bluez"
OBJECT_MANAGER_IFACE = "org.freedesktop.DBus.ObjectManager"
DEVICE_IFACE = "org.bluez.Device1"
MEDIA_PLAYER_IFACE = "org.bluez.MediaPlayer1"
UNIT_NAME = "bluealsa-aplay.service"


class BluetoothAdapter(Adapter):
    renderer_id = "bluetooth"
    release_action = ReleaseAction.DISCONNECT

    def __init__(self) -> None:
        self._bus: MessageBus | None = None
        self._connected_device_path: str | None = None

    async def run(self, on_acquire) -> None:
        while True:
            try:
                await self._watch(on_acquire)
            except Exception as exc:  # noqa: BLE001 - keep watching regardless
                logger.warning("bluetooth: D-Bus watch failed (%s), retrying in 5s", exc)
                await asyncio.sleep(5)

    async def _watch(self, on_acquire) -> None:
        self._bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        introspection = await self._bus.introspect(BLUEZ_SERVICE, "/")
        root = self._bus.get_proxy_object(BLUEZ_SERVICE, "/", introspection)
        obj_manager = root.get_interface(OBJECT_MANAGER_IFACE)

        managed = await obj_manager.call_get_managed_objects()
        for path, ifaces in managed.items():
            if MEDIA_PLAYER_IFACE in ifaces:
                self._connected_device_path = self._device_path_for_player(path)
                logger.info("bluetooth: MediaPlayer1 already present at %s on startup", path)

        def on_interfaces_added(path, interfaces):
            if MEDIA_PLAYER_IFACE in interfaces:
                self._connected_device_path = self._device_path_for_player(path)
                logger.info("bluetooth: MediaPlayer1 appeared at %s (acquisition)", path)
                on_acquire()

        def on_interfaces_removed(path, interfaces):
            if MEDIA_PLAYER_IFACE in interfaces and path.startswith(
                self._connected_device_path or "\0"
            ):
                logger.info("bluetooth: MediaPlayer1 removed at %s", path)
                self._connected_device_path = None

        obj_manager.on_interfaces_added(on_interfaces_added)
        obj_manager.on_interfaces_removed(on_interfaces_removed)

        # Idle forever; callbacks above do the work. Exits (and the outer
        # loop reconnects) only if the bus connection itself drops.
        await self._bus.wait_for_disconnect()

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
