# SPDX-License-Identifier: GPL-3.0-or-later
"""The adapter's own switches: discoverable, pairable (ADR-0045).

**`bt_discoverable` has never worked.** The row offers Always / 3 min after
boot / Off and reported the middle one, but nothing chose three minutes:
`bluetooth-setup.sh` runs `bluetoothctl discoverable on` and never touches
`DiscoverableTimeout`, so BlueZ's 180 s default reverts it and the device
settles at `Discoverable: no`. Measured on the device 2026-09-21, hours
after boot: `Discoverable: no`, `DiscoverableTimeout: 0x000000b4 (180)`.
**A device nobody can discover cannot be paired with**, confirmed or not,
which is why this comes first in the subphase.

`docs/LESSONS.md` records the same trap costing a blocker and 1h36m, and
the script still hit it. The shape is worth restating: **`discoverable on`
is not a state, it is a state with a timer attached**, and the timer is a
separate property that has to be set first. Setting it after has no effect
on the countdown already running.

Done over D-Bus rather than by shelling out to `bluetoothctl`, because
`org.bluez.Adapter1` carries both as plain properties and the daemon is
already on the bus for the A2DP adapter. It also makes the setting live:
changing it applies now, with no restart and nothing to schedule.
"""
from __future__ import annotations

import logging

from dbus_next import BusType, Variant
from dbus_next.aio import MessageBus

logger = logging.getLogger(__name__)

BLUEZ_SERVICE = "org.bluez"
ADAPTER_IFACE = "org.bluez.Adapter1"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
OBJECT_MANAGER_IFACE = "org.freedesktop.DBus.ObjectManager"

#: BlueZ's own default, and what "3 min after boot" has always meant even
#: though nothing chose it.
BOOT_WINDOW_S = 180

#: `bt_discoverable` -> (timeout seconds, discoverable). Zero is BlueZ's
#: "no timeout", which is the only way Always can mean always.
MODES = {
    "Always": (0, True),
    "3 min after boot": (BOOT_WINDOW_S, True),
    "Off": (BOOT_WINDOW_S, False),
}
DEFAULT_MODE = "3 min after boot"


async def find_adapter(bus: MessageBus) -> str | None:
    """The first `org.bluez.Adapter1` path, or None.

    Not hardcoded to `/org/bluez/hci0`: the same reason ADR-0006 forbids an
    ALSA card index. It is the name of a position, not of a thing.
    """
    introspection = await bus.introspect(BLUEZ_SERVICE, "/")
    root = bus.get_proxy_object(BLUEZ_SERVICE, "/", introspection)
    manager = root.get_interface(OBJECT_MANAGER_IFACE)
    for path, interfaces in (await manager.call_get_managed_objects()).items():
        if ADAPTER_IFACE in interfaces:
            return path
    return None


async def _set(bus: MessageBus, path: str, name: str, value: Variant) -> None:
    introspection = await bus.introspect(BLUEZ_SERVICE, path)
    obj = bus.get_proxy_object(BLUEZ_SERVICE, path, introspection)
    await obj.get_interface(PROPERTIES_IFACE).call_set(ADAPTER_IFACE, name, value)


async def apply_discoverable(bus: MessageBus, mode: str) -> bool:
    """Put the adapter into one of the three states the row offers.

    **Timeout first, then the switch.** `DiscoverableTimeout` is what the
    countdown reads when `Discoverable` is set, so setting it afterwards
    changes nothing about the window already running - which is exactly how
    "Always" came to mean "three minutes" for the life of this project.
    """
    timeout, discoverable = MODES.get(mode, MODES[DEFAULT_MODE])
    path = await find_adapter(bus)
    if path is None:
        logger.warning("bluetooth: no adapter on the bus; %r not applied", mode)
        return False
    try:
        await _set(bus, path, "DiscoverableTimeout", Variant("u", timeout))
        await _set(bus, path, "Discoverable", Variant("b", discoverable))
        # Pairable carries its own timeout with the same trap. A device that
        # is discoverable and not pairable is worse than either: it shows up
        # and then refuses.
        await _set(bus, path, "PairableTimeout", Variant("u", 0))
        await _set(bus, path, "Pairable", Variant("b", True))
    except Exception as exc:  # dbus_next raises DBusError and friends
        logger.warning("bluetooth: could not apply %r: %s", mode, exc)
        return False
    logger.info(
        "bluetooth: discoverable=%s timeout=%ss (%r) on %s",
        discoverable,
        timeout,
        mode,
        path,
    )
    return True


async def read_state(bus: MessageBus) -> dict:
    """What the adapter actually reports, for checking the above rather than
    trusting it."""
    path = await find_adapter(bus)
    if path is None:
        return {}
    introspection = await bus.introspect(BLUEZ_SERVICE, path)
    obj = bus.get_proxy_object(BLUEZ_SERVICE, path, introspection)
    props = await obj.get_interface(PROPERTIES_IFACE).call_get_all(ADAPTER_IFACE)
    return {
        key: props[key].value
        for key in ("Powered", "Discoverable", "DiscoverableTimeout", "Pairable", "Alias")
        if key in props
    }
