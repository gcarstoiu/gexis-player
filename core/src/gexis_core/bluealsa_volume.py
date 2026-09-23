"""ADR-0054 §1 — Bluetooth's level, straight from bluealsa, not through a mixer.

**Why this module exists.** Until 2026-09-23 the phone's AVRCP level reached
us through an ALSA mixer control: `bluealsa-aplay --volume=mixer` wrote
`gexisbtvol` and read it back, and our daemon watched that control. That
round trip is a loop, and it was measured wrong one time in three — 59 of
179 in George's own session, five of them jumping straight to 127 — because
bluealsa's AVRCP curve is about 10 dB per doubling while the control is
linear in dB, so converting between them quantises differently in each
direction (Finding 047 §2).

It also explained his *"connected and the volume was low even though on the
phone it was at max"*. `bluealsa-aplay(1)`: *"When the audio stream starts
then bluealsa-aplay will change the Bluetooth volume to match the current
setting of the ALSA mixer control."* The stale mixer value overwrites the
phone, by documented design.

So the mixer leaves the path. `--volume=none` keeps bluealsa's own volume
mode **native ("pass-through")**, which is the half worth having — the
stream still reaches the DAC at full scale, nothing is attenuated in
software — and the man page names this exact use: *"it can be used to allow
some other application to apply remote volume change requests."* This is
that application.

**The API**, from `org.bluealsa.PCM1(7)` on the device:

    uint16 Volume [readwrite]
      ... channel 1 (left) in the upper byte, channel 2 (right) in the
      lower byte. The highest bit of both bytes determines whether the
      channel is muted.  A2DP: 0-127

One writer in each direction and no mixer in between, so there is nothing
for a ratchet to live in.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from dbus_next import Variant
from dbus_next.aio import MessageBus
from dbus_next.constants import BusType

logger = logging.getLogger("gexis_core.bluealsa_volume")

SERVICE = "org.bluealsa"
ROOT = "/org/bluealsa"
PCM_INTERFACE = "org.bluealsa.PCM1"
#: AVRCP's own range, and the one the property documents.
STEPS = 127


def decode(value: int) -> int:
    """The louder of the two channels, ignoring mute.

    **Mute is deliberately not carried through.** It shares the byte with
    the level, and this device has its own mute (ADR-0034) which is not the
    phone's; conflating them would let a phone's mute strand the panel
    showing a level nobody can hear, or the reverse.
    """
    return max((value >> 8) & 0x7F, value & 0x7F)


def encode(level: int) -> int:
    """`level` on both channels, unmuted. Balance is not ours to set."""
    level = max(0, min(STEPS, int(level)))
    return (level << 8) | level


class BluealsaVolume:
    """Follows the A2DP sink PCM's `Volume`, and sets it.

    Survives bluealsa not being there: it is a separate service that has
    crashed before (Finding 045 §10), and nothing here may take the daemon
    with it.
    """

    def __init__(self, on_value: Callable[[int, int], None]) -> None:
        self._on_value = on_value
        self._bus: MessageBus | None = None
        self._path: str | None = None
        self._level: int | None = None

    @property
    def level(self) -> int | None:
        """The phone's own level, or None when nothing is connected."""
        return self._level

    async def run(self) -> None:
        while True:
            try:
                await self._watch()
            except Exception as exc:  # noqa: BLE001 - bluealsa is a separate service
                logger.warning("bluealsa: volume watch failed (%s), retrying in 5s", exc)
            self._forget()
            await asyncio.sleep(5)

    async def _watch(self) -> None:
        self._bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        introspection = await self._bus.introspect(SERVICE, ROOT)
        root = self._bus.get_proxy_object(SERVICE, ROOT, introspection)
        manager = root.get_interface("org.freedesktop.DBus.ObjectManager")

        def added(path, interfaces):
            if PCM_INTERFACE in interfaces:
                asyncio.ensure_future(self._adopt(path, interfaces[PCM_INTERFACE]))

        def removed(path, interfaces):
            if path == self._path and PCM_INTERFACE in interfaces:
                logger.info("bluealsa: %s went away", path)
                self._forget()

        manager.on_interfaces_added(added)
        manager.on_interfaces_removed(removed)

        for path, interfaces in (await manager.call_get_managed_objects()).items():
            if PCM_INTERFACE in interfaces:
                await self._adopt(path, interfaces[PCM_INTERFACE])

        await self._bus.wait_for_disconnect()

    @staticmethod
    def _is_sink(properties: dict) -> bool:
        """The stream coming *from* the phone. bluealsa exports a PCM per
        direction, and a phone that can also receive audio would otherwise
        give us two."""
        def value(key, default=""):
            variant = properties.get(key)
            return variant.value if isinstance(variant, Variant) else default

        return value("Mode") == "sink" and value("Transport").startswith("A2DP")

    async def _adopt(self, path: str, properties: dict) -> None:
        if not self._is_sink(properties):
            return
        if self._bus is None:
            return
        self._path = path
        logger.info("bluealsa: following %s", path)
        introspection = await self._bus.introspect(SERVICE, path)
        obj = self._bus.get_proxy_object(SERVICE, path, introspection)
        self._pcm = obj.get_interface(PCM_INTERFACE)
        self._properties = obj.get_interface("org.freedesktop.DBus.Properties")

        def changed(interface, changed_properties, invalidated):
            if interface != PCM_INTERFACE or "Volume" not in changed_properties:
                return
            self._report(changed_properties["Volume"].value)

        self._properties.on_properties_changed(changed)

        raw = properties.get("Volume")
        if isinstance(raw, Variant):
            # **The level the phone already has, at the moment it connects.**
            # George, 2026-09-23: "doesn't the bluetooth protocol pass along
            # as well the volume upon connection so the phone and panel show
            # the same thing?" It does, and this is where we listen to it.
            self._report(raw.value)

    def _report(self, encoded: int) -> None:
        level = decode(encoded)
        if level == self._level:
            return
        self._level = level
        self._on_value(level, STEPS)

    def _forget(self) -> None:
        self._path = None
        self._level = None
        self._bus = None

    async def set(self, level: int) -> None:
        """Put `level` on the phone. **Only ever a panel-originated value** —
        ADR-0053's invariant is that what a renderer reported is never sent
        back to it, and this is the one place that could break it."""
        if self._path is None or self._bus is None:
            logger.debug("bluealsa: nothing connected, %s not sent", level)
            return
        try:
            await self._properties.call_set(
                PCM_INTERFACE, "Volume", Variant("q", encode(level))
            )
        except Exception as exc:  # noqa: BLE001 - a phone that will not take it
            logger.warning("bluealsa: setting volume to %s failed: %s", level, exc)
