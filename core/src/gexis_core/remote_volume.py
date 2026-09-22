"""ADR-0053 — the panel's volume control *is* the active renderer's.

Before this, the panel's slider and the renderer's slider were two controls
in series: one sound, two numbers. Measured on the device (Finding 046 §1),
LMS at 25 put the DAC at −30 dB, which the panel published as **33**.
George: *"If LMS is at 25 I expect the volume on the panel to also 25."*

So the panel stops having a volume of its own while something is playing. It
sends the position to the renderer, the renderer does what it always does,
and the number the panel shows is the renderer's own — the same number the
LMS app, the Spotify app or a phone's slider is showing.

**The invariant this class exists to hold** (ADR-0053's risk section, and
`test_volume.py::TestTheRemoteRoundTripDoesNotRatchet`):

    A renderer's own value is never sent back to it.

`report()` is inbound only and never causes a `send()`. This is not fussiness
about layering: 101 panel positions cannot name AVRCP's 128 values, so a
Bluetooth level shown as a percentage and pushed back out lands somewhere
else for 27 of them — raw 101 shows as 80%, and 80% sends 102. Closing that
loop rebuilds Finding 045 §12's ratchet, which ended with bluealsa dying of
it.

**Three channels, measured** (Finding 046):

- **LMS** — the server's JSON-RPC, 16–26 ms. It has to be the server:
  squeezelite does not carry an external mixer change back to LMS (ten
  seconds, no change), so writing its control would leave LMS showing one
  number and the device at another.
- **Spotify** — go-librespot's local API, 2–5 ms. Already built; this only
  routes to it.
- **Bluetooth** — its own dummy control, which `bluealsa-aplay
  --volume=mixer` pushes out over AVRCP. ~6 ms to write. **The outbound leg
  is inference until a phone is seen to follow it.**

What reaches the DAC is unchanged: the renderer's control moves, and the
mirrors in `volume.py` carry it to the hardware exactly as before. This
class adds no path to the hardware; it removes the panel's private one.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from gexis_core.volume import renderer_percent_to_value, renderer_value_to_percent

logger = logging.getLogger("gexis_core.remote_volume")


@dataclass
class _Channel:
    """One renderer's scale, its way out, and the last value it reported."""

    steps: int
    send: Callable[[int], Awaitable[object]] | None = None
    value: int | None = None


class RemoteVolume:
    def __init__(
        self,
        get_active_renderer: Callable[[], str | None],
        on_change: Callable[[], None],
    ) -> None:
        self._get_active_renderer = get_active_renderer
        self._on_change = on_change
        self._channels: dict[str, _Channel] = {}

    def register(self, renderer_id: str, *, steps: int, send=None) -> None:
        """`steps` is the renderer's maximum, so its scale has `steps + 1`
        positions. `send` is None for a renderer we can read but not drive -
        it keeps its number on the panel and the panel keeps its own
        slider."""
        self._channels[renderer_id] = _Channel(steps=steps, send=send)

    def set_steps(self, renderer_id: str, steps: int) -> None:
        """Spotify's scale is whatever `/status` says, and that answer
        arrives after the wiring does."""
        channel = self._channels.get(renderer_id)
        if channel is None or steps <= 0 or channel.steps == steps:
            return
        channel.steps = steps
        if self._get_active_renderer() == renderer_id:
            self._on_change()

    def report(self, renderer_id: str, value: int) -> None:
        """A renderer says where its own volume is. **Inbound only.**

        Nothing here may lead to a `send()`, now or ever - see the module
        docstring. The value is recorded, and if this renderer is the one
        holding the device, the panel's number follows it.
        """
        channel = self._channels.get(renderer_id)
        if channel is None or channel.value == value:
            return
        channel.value = value
        if self._get_active_renderer() == renderer_id:
            self._on_change()

    def percent(self) -> int | None:
        """The number to show, or None when there is nothing to be a remote
        for - no renderer active, or one that has not said where it is. The
        caller then falls back to the hardware's own percentage, which is
        what the panel showed before this record."""
        channel = self._active()
        if channel is None or channel.value is None:
            return None
        return renderer_value_to_percent(channel.value, channel.steps)

    async def send(self, percent: float) -> bool:
        """Put the panel's position on the active renderer's control.

        True if it went to a renderer; False if the caller should write the
        hardware itself, which is what happens with nothing playing.

        The value is recorded as this renderer's *before* it is sent, so the
        panel's number moves with the finger rather than waiting for the
        renderer to agree - LMS's own confirmation is measured at ~525 ms
        (Finding 046 §8), which is far too slow to drag against. Whatever
        the renderer reports afterwards, including a value it quantised
        differently, replaces it.
        """
        renderer_id = self._get_active_renderer()
        channel = self._active()
        if channel is None or channel.send is None:
            return False
        value = renderer_percent_to_value(percent, channel.steps)
        channel.value = value
        self._on_change()
        logger.info(
            "volume: %.0f%% -> %s's own control (%s/%s)",
            percent,
            renderer_id,
            value,
            channel.steps,
        )
        try:
            await channel.send(value)
        except Exception:  # noqa: BLE001 - a renderer that will not take it
            logger.exception("volume: %s refused %s", renderer_id, value)
        return True

    def _active(self) -> _Channel | None:
        renderer_id = self._get_active_renderer()
        return None if renderer_id is None else self._channels.get(renderer_id)
