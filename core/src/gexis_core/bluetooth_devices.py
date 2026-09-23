# SPDX-License-Identifier: GPL-3.0-or-later
"""Remembered Bluetooth devices, for `bt_trusted` (ADR-0044 §1, ADR-0045).

The last of the three `list` rows to get a source. Wi-Fi came from
NetworkManager and Lyrion servers from a UDP broadcast; these come from
BlueZ's own object tree, which is already how `adapters/bluetooth.py`
learns about everything else.

**Forgetting is `Adapter1.RemoveDevice`, not `Trusted = false`.** Clearing
the trust flag leaves the bond in place: the phone still holds its key, the
device still answers to it, and it reconnects. Removing the device drops
the bond, which is what "forget" means everywhere else and what the row's
note promises - *"forgetting a device breaks its automatic reconnection"*.

It also means **the phone keeps its half**, and will try the key it still
has rather than pairing again. That is not something this end can fix; it
is why the row says what it says.
"""
from __future__ import annotations

import logging

from dbus_next.aio import MessageBus

from gexis_core.bluetooth_adapter_state import (
    ADAPTER_IFACE,
    BLUEZ_SERVICE,
    OBJECT_MANAGER_IFACE,
    find_adapter,
)

logger = logging.getLogger(__name__)

DEVICE_IFACE = "org.bluez.Device1"


def _value(properties: dict, key: str, fallback=None):
    """ObjectManager hands back `Variant`s; `.value` unwraps one."""
    variant = properties.get(key)
    return fallback if variant is None else variant.value


async def known(bus: MessageBus) -> list[dict]:
    """Every device BlueZ remembers, as the settings sheet draws an item.

    **Paired only.** BlueZ's tree also carries whatever the adapter has
    merely *seen* while discoverable - every phone and laptop that walked
    past - and a list of strangers under "Trusted devices" would be a list
    of things the user cannot act on and did not choose.

    The connected one comes first, then the rest by name, because the list
    is read from the top and the device in use is the one being looked for.
    """
    introspection = await bus.introspect(BLUEZ_SERVICE, "/")
    root = bus.get_proxy_object(BLUEZ_SERVICE, "/", introspection)
    manager = root.get_interface(OBJECT_MANAGER_IFACE)
    items = []
    for path, interfaces in (await manager.call_get_managed_objects()).items():
        properties = interfaces.get(DEVICE_IFACE)
        if properties is None or not _value(properties, "Paired", False):
            continue
        connected = bool(_value(properties, "Connected", False))
        trusted = bool(_value(properties, "Trusted", False))
        name = (
            _value(properties, "Alias")
            or _value(properties, "Name")
            or _value(properties, "Address")
            or path.rsplit("/", 1)[-1]
        )
        items.append(
            {
                "name": str(name),
                # The meta line says what the row can act on, not a
                # timestamp: BlueZ keeps no "last connected" and inventing
                # one from the object's mtime would be a guess wearing a
                # fact's clothes. The design shows "Connected 2 hours ago";
                # this shows what is true.
                "meta": "Connected" if connected else ("Trusted" if trusted else "Paired"),
                "bars": None,
                "state": "connected" if connected else "saved",
                "path": path,
                "address": str(_value(properties, "Address", "")),
            }
        )
    order = {"connected": 0, "saved": 1}
    return sorted(items, key=lambda i: (order[i["state"]], i["name"].lower()))


async def forget(bus: MessageBus, name: str) -> tuple[bool, str | None]:
    """Drop the bond for the device with this name.

    Matched by name because that is what the sheet shows and sends back.
    Two devices with the same name is possible and the first is taken -
    the alternative is showing an address nobody recognises to disambiguate
    a case that needs two identical phones in one house.
    """
    adapter = await find_adapter(bus)
    if adapter is None:
        return False, "No Bluetooth adapter."
    match = next((d for d in await known(bus) if d["name"] == name), None)
    if match is None:
        return False, "That device is not paired."
    try:
        introspection = await bus.introspect(BLUEZ_SERVICE, adapter)
        obj = bus.get_proxy_object(BLUEZ_SERVICE, adapter, introspection)
        await obj.get_interface(ADAPTER_IFACE).call_remove_device(match["path"])
    except Exception as exc:
        logger.warning("bluetooth: could not forget %s: %s", name, exc)
        return False, "Could not forget that device."
    logger.info("bluetooth: forgot %s (%s)", name, match["address"])
    return True, None
