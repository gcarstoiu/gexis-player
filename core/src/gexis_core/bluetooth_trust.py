"""Auto-trust newly paired Bluetooth devices (ADR-0024: PIN-free pairing).

`bt-agent` (bluez-tools, `gexis-bt-agent.service`) answers the pairing
handshake itself but does not set `Trusted` - BlueZ leaves that as a
separate step, normally left to a companion app or a manual
`bluetoothctl trust <mac>`. Found on hardware, 2026-09-08: without it, a
paired-but-untrusted device's `bluealsa-aplay` stream opened the PCM and
then immediately logged "BT device marked as inactive," pulling no
audio - `bluetoothctl trust <mac>` fixed it by hand. PIN-free pairing
that still needs a manual step afterwards isn't what ADR-0024 decided.

**Polls, doesn't subscribe to D-Bus PropertiesChanged** - a deliberate
choice, not the ADR-0018 "subscribed, not polled" principle being
ignored: that principle is about not adding visible lag to a
live-updating value (the volume slider). Pairing is a rare, human-paced
event; a couple of seconds' latency between "phone finishes pairing" and
"trusted" is imperceptible, and a poll loop watching
`GetManagedObjects` is far simpler to get right than matching
`PropertiesChanged` signals across every `Device1` object BlueZ might
expose, for a difference nobody would notice.

Standalone, not part of `gexis-core.service` - Bluetooth pairing is
foundational Bluetooth support, same reasoning as
`gexis-bluetooth-setup.service` and `gexis-bt-agent.service` living
outside the arbitration core (`image/stage-gexis/02-renderers`).
"""
from __future__ import annotations

import asyncio
import logging

from dbus_next import BusType, Variant
from dbus_next.aio import MessageBus

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("gexis_core.bluetooth_trust")

BLUEZ_SERVICE = "org.bluez"
OBJECT_MANAGER_IFACE = "org.freedesktop.DBus.ObjectManager"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
DEVICE_IFACE = "org.bluez.Device1"
POLL_INTERVAL_S = 2.0


async def _trust_untrusted_paired_devices(bus: MessageBus, obj_manager) -> None:
    managed = await obj_manager.call_get_managed_objects()
    for path, ifaces in managed.items():
        device = ifaces.get(DEVICE_IFACE)
        if device is None:
            continue
        paired = device.get("Paired")
        trusted = device.get("Trusted")
        if not (paired and paired.value) or (trusted and trusted.value):
            continue
        try:
            introspection = await bus.introspect(BLUEZ_SERVICE, path)
            props = bus.get_proxy_object(BLUEZ_SERVICE, path, introspection).get_interface(
                PROPERTIES_IFACE
            )
            await props.call_set(DEVICE_IFACE, "Trusted", Variant("b", True))
            logger.info("trusted newly paired device at %s", path)
        except Exception as exc:  # noqa: BLE001 - keep polling regardless
            logger.warning("failed to trust %s: %s", path, exc)


async def _watch() -> None:
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    introspection = await bus.introspect(BLUEZ_SERVICE, "/")
    root = bus.get_proxy_object(BLUEZ_SERVICE, "/", introspection)
    obj_manager = root.get_interface(OBJECT_MANAGER_IFACE)

    while True:
        await _trust_untrusted_paired_devices(bus, obj_manager)
        await asyncio.sleep(POLL_INTERVAL_S)


async def main() -> None:
    while True:
        try:
            await _watch()
        except Exception as exc:  # noqa: BLE001
            logger.warning("D-Bus connection failed (%s), retrying in 5s", exc)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
