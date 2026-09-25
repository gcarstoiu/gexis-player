# SPDX-License-Identifier: GPL-3.0-or-later
"""`bt_discoverable`, which has never worked (ADR-0045, Phase 9 subphase 9f).

The row offered Always / 3 min after boot / Off and the device reported
`Discoverable: no` with `DiscoverableTimeout: 180` - BlueZ's default,
reverting an untimed `discoverable on`. None of the three options was
implemented and the middle one was never chosen by anything.
"""
from __future__ import annotations

import pytest

from gexis_core import bluetooth_adapter_state as state


class FakeProperties:
    def __init__(self, store, calls):
        self._store = store
        self._calls = calls

    async def call_set(self, iface, name, variant):
        self._calls.append((name, variant.value))
        self._store[name] = variant.value

    async def call_get_all(self, iface):
        from dbus_next import Variant

        return {k: Variant("v", v) for k, v in self._store.items()}


class FakeObject:
    def __init__(self, interfaces):
        self._interfaces = interfaces

    def get_interface(self, name):
        return self._interfaces[name]


class FakeManager:
    def __init__(self, objects):
        self._objects = objects

    async def call_get_managed_objects(self):
        return self._objects


class FakeBus:
    """Enough of dbus_next's surface for these calls, and no more."""

    def __init__(self, adapters=("/org/bluez/hci0",)):
        self.props = {}
        self.calls = []
        self._objects = {p: {state.ADAPTER_IFACE: {}} for p in adapters}
        self._objects["/org/bluez"] = {"org.bluez.AgentManager1": {}}

    async def introspect(self, service, path):
        return None

    def get_proxy_object(self, service, path, introspection):
        if path == "/":
            return FakeObject({state.OBJECT_MANAGER_IFACE: FakeManager(self._objects)})
        return FakeObject({state.PROPERTIES_IFACE: FakeProperties(self.props, self.calls)})


@pytest.mark.asyncio
async def test_always_means_always_which_needs_a_zero_timeout():
    """`Always` with BlueZ's 180 s default is "three minutes", which is what
    the device did for the life of the project."""
    bus = FakeBus()
    assert await state.apply_discoverable(bus, "Always") is True
    assert bus.props["DiscoverableTimeout"] == 0
    assert bus.props["Discoverable"] is True


@pytest.mark.asyncio
async def test_the_timeout_is_set_before_the_switch():
    """**The whole defect in one assertion.** `DiscoverableTimeout` is what
    the countdown reads when `Discoverable` is set; setting it afterwards
    changes nothing about the window already running."""
    bus = FakeBus()
    await state.apply_discoverable(bus, "Always")
    names = [name for name, _ in bus.calls]
    assert names.index("DiscoverableTimeout") < names.index("Discoverable")
    assert names.index("PairableTimeout") < names.index("Pairable")


@pytest.mark.asyncio
async def test_three_minutes_is_the_one_mode_that_keeps_blue_zs_default():
    bus = FakeBus()
    await state.apply_discoverable(bus, "3 min after boot")
    assert bus.props["DiscoverableTimeout"] == state.BOOT_WINDOW_S
    assert bus.props["Discoverable"] is True


@pytest.mark.asyncio
async def test_off_is_off():
    bus = FakeBus()
    await state.apply_discoverable(bus, "Off")
    assert bus.props["Discoverable"] is False


@pytest.mark.asyncio
async def test_pairable_is_set_too_and_never_expires():
    """Discoverable and not pairable is worse than either: the device shows
    up in the phone's list and then refuses."""
    bus = FakeBus()
    await state.apply_discoverable(bus, "Always")
    assert bus.props["Pairable"] is True and bus.props["PairableTimeout"] == 0


@pytest.mark.asyncio
async def test_an_unknown_mode_falls_back_rather_than_leaving_it_as_it_was():
    """A value the registry no longer offers must not leave the adapter in
    whatever state it happened to be in."""
    bus = FakeBus()
    await state.apply_discoverable(bus, "Whatever the store had")
    assert bus.props["DiscoverableTimeout"] == state.BOOT_WINDOW_S


@pytest.mark.asyncio
async def test_no_adapter_is_reported_rather_than_raised():
    """The daemon can be up before `gexis-bluetooth-setup` has powered one.
    The caller retries; it must be told, not crashed."""
    bus = FakeBus(adapters=())
    assert await state.apply_discoverable(bus, "Always") is False


@pytest.mark.asyncio
async def test_the_adapter_is_found_rather_than_assumed_to_be_hci0():
    """The same reason ADR-0006 forbids an ALSA card index: `hci0` is the
    name of a position, not of a thing."""
    bus = FakeBus(adapters=("/org/bluez/hci7",))
    assert await state.find_adapter(bus) == "/org/bluez/hci7"
    assert await state.apply_discoverable(bus, "Always") is True


@pytest.mark.asyncio
async def test_every_mode_the_registry_offers_is_implemented():
    """The row offered three options and none of them did anything. This
    fails if the registry grows a fourth without the code following."""
    import json
    from pathlib import Path

    registry = json.loads(
        (Path(__file__).parents[1] / "src/gexis_core/settings_registry.json").read_text()
    )
    row = next(
        r for g in registry for r in g["rows"] if r.get("key") == "bt_discoverable"
    )
    assert set(row["options"]) == set(state.MODES)
    assert row["default"] in state.MODES


# ---------------------------------------------------------------------------
# ADR-0077: Bluetooth off is the radio off, not just the audio path.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_powering_off_stops_advertising_first():
    """A radio that comes back up still advertising is a radio that ignored
    the row for as long as it was off. Discoverable and Pairable go down
    before Powered so there is nothing left set to come back to."""
    bus = FakeBus()
    assert await state.set_powered(bus, False) is True
    names = [name for name, _ in bus.calls]
    assert names.index("Discoverable") < names.index("Powered")
    assert names.index("Pairable") < names.index("Powered")
    assert bus.props["Powered"] is False
    assert bus.props["Discoverable"] is False
    assert bus.props["Pairable"] is False


@pytest.mark.asyncio
async def test_powering_on_touches_powered_and_nothing_else():
    """Discoverability is the other row's business (`bt_discoverable`), and
    `_apply_renderer` applies it after this. Setting it here as well would
    make Always mean three minutes again by writing `Discoverable` without
    its timeout."""
    bus = FakeBus()
    assert await state.set_powered(bus, True) is True
    assert [name for name, _ in bus.calls] == ["Powered"]
    assert bus.props["Powered"] is True


@pytest.mark.asyncio
async def test_no_adapter_on_the_bus_is_reported_not_raised():
    """A device with the radio removed or rfkill-blocked hard: the row is
    still written, and the daemon does not come down over it."""
    bus = FakeBus(adapters=())
    assert await state.set_powered(bus, False) is False
