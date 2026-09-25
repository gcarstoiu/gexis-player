# SPDX-License-Identifier: GPL-3.0-or-later
"""**A renderer that lives in another process** (ADR-0089).

Every other adapter in this package watches something - D-Bus, a WebSocket, a
poll - and acts through that renderer's own API. This one watches nothing and
acts through [ADR-0084](../../../../docs/decisions/0084-plugins-speak-json-lines-over-a-unix-socket.md)'s
socket: **its implementation is "send that message on this session"**, and its
events arrive on a connection `plugin_server` is already reading.

That is the whole of it, and it is meant to be. `docs/PLUGIN-CONTRACT.md`
specifies both directions in full and `Adapter` is an abstract class with
exactly those methods; if this file needed cleverness, one of the two would be
wrong.
"""
from __future__ import annotations

import asyncio
import logging

from gexis_core.adapters.base import Adapter, Capabilities, ReleaseAction, VolumeMechanism
from gexis_core.arbitration import TimeoutLadder
from gexis_core.plugin_server import PluginGone
from gexis_core.systemd import kill_unit

logger = logging.getLogger("gexis_core.adapters.plugin")

#: What `capabilities.controls` may contain. The same set the three built-ins
#: declare, plus `activate`; an unknown one is refused rather than dropped,
#: because a control the panel offers and nothing implements is worse than one
#: that was never offered.
CONTROLS = frozenset(
    {"play", "pause", "next", "previous", "repeat", "shuffle", "activate"}
)


class BadDeclaration(ValueError):
    """A `hello` this core cannot act on.

    **Refused, not defaulted.** A renderer whose capabilities are wrong is
    worse than one that never connected: it would be offered on the panel,
    chosen, and then fail to do what it said.
    """


def _ladder(raw) -> TimeoutLadder | None:
    """A declared release ladder, or None for the supervisor's default.

    **Plexamp needs one**: 14 s of hold after a stop its own API confirms
    instantly ([Finding 077](../../../../docs/findings/077-plexamp-on-gexis.md)),
    against a default sized for go-librespot's sub-100 ms.
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise BadDeclaration("release_ladder must be an object")
    unknown = set(raw) - {"polite_grace", "sigterm_grace", "sigkill_grace"}
    if unknown:
        raise BadDeclaration(f"release_ladder has unknown keys: {sorted(unknown)}")
    values = {}
    for key, value in raw.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            raise BadDeclaration(f"release_ladder.{key} must be a number of seconds")
        values[key] = float(value)
    return TimeoutLadder(**values)


def capabilities_from(raw) -> Capabilities:
    """`Capabilities` from what a plugin declared, or `BadDeclaration`."""
    if not isinstance(raw, dict):
        raise BadDeclaration("capabilities must be an object")
    try:
        mechanism = VolumeMechanism(raw.get("volume_mechanism", "software_api"))
    except ValueError:
        raise BadDeclaration(
            f"unknown volume_mechanism {raw.get('volume_mechanism')!r}"
        ) from None
    # `x or []` would turn an empty list *and* a `0` *and* a `""` into
    # defaults - a plugin that sent the wrong shape would be silently given the
    # quiet one. Absent is the only thing that means "I did not say".
    events = raw.get("acquisition_events", [])
    controls = raw.get("controls", [])
    events = [] if events is None else events
    controls = [] if controls is None else controls
    for name, value in (("acquisition_events", events), ("controls", controls)):
        if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
            raise BadDeclaration(f"{name} must be a list of strings")
    unknown = set(controls) - CONTROLS
    if unknown:
        raise BadDeclaration(f"unknown controls: {sorted(unknown)}")
    if mechanism is VolumeMechanism.DUMMY_MIXER and not raw.get("dummy_mixer_card"):
        # The bridge has nothing to point at otherwise, and would mirror the
        # renderer's level onto the real DAC's control - which is the fight
        # ADR-0018's amendment exists to prevent.
        raise BadDeclaration("dummy_mixer needs a dummy_mixer_card")
    return Capabilities(
        audio_connection=str(raw.get("audio_connection", "output")),
        acquisition_events=frozenset(events),
        supports_artwork=bool(raw.get("supports_artwork", False)),
        supports_sample_rate=bool(raw.get("supports_sample_rate", False)),
        volume_managed=bool(raw.get("volume_managed", False)),
        volume_mechanism=mechanism,
        dummy_mixer_card=raw.get("dummy_mixer_card"),
        volume_over_bluealsa=bool(raw.get("volume_over_bluealsa", False)),
        controls=frozenset(controls),
    )


class PluginAdapter(Adapter):
    """One connected renderer plugin, as the supervisor sees it."""

    def __init__(self, session, *, signal_unit=None) -> None:
        """`signal_unit` is how the core escalates by itself - a callable
        taking `(unit, force)`. It defaults to `systemd.kill_unit`, which is
        what the three built-ins use.

        **It is not optional, and it is not the plugin's.** `release()` on a
        dead session raises `PluginGone`, which the ladder reads as a polite
        stop that did not work; the step that actually frees the device is this
        one, against the unit the *manifest* names. A plugin cannot strand the
        device by dying, because the thing that frees it never needed the
        plugin's cooperation (ADR-0089).
        """
        declaration = session.declaration
        self._session = session
        self._signal_unit = signal_unit if signal_unit is not None else kill_unit
        self.renderer_id = session.id
        # **The manifest's unit, never the handshake's.** The release ladder
        # attributes a still-busy device to this name, so a renderer that could
        # name its own could point the escalation at any process on the device.
        self.unit_name = session.plugin.unit
        try:
            self.release_action = ReleaseAction(
                declaration.get("release_action", "disconnect")
            )
        except ValueError:
            raise BadDeclaration(
                f"unknown release_action {declaration.get('release_action')!r}"
            ) from None
        declared = declaration.get("capabilities", {})
        self.capabilities = capabilities_from({} if declared is None else declared)
        self.release_ladder = _ladder(declaration.get("release_ladder"))

    async def run(self, on_acquire, on_release) -> None:
        """**Parks.** The socket is the watch.

        `PluginServer` is already reading this connection, so there is nothing
        here to read: the plugin's `acquire` and `release` lines call these two
        through `on_event`. Held open anyway, because `Adapter.run` is what the
        supervisor's lifecycle is written around and a plugin renderer that
        returned immediately would be a renderer whose task had finished.
        """
        self.on_acquire = on_acquire
        self.on_release = on_release
        logger.info("plugins: %s is watching through its own connection", self.renderer_id)
        await asyncio.Event().wait()

    async def release(self) -> bool:
        """The polite stop, through the plugin's own control channel.

        True means **its API confirmed the action**, never that the device is
        free - the supervisor checks that separately, and for Plexamp the two
        are fourteen seconds apart.
        """
        try:
            return bool(await self._session.send("release"))
        except PluginGone as exc:
            # Not an error to shout about: a renderer that disconnected has
            # certainly stopped answering, and the ladder's next step does not
            # need it. Said at info because it changes what happens next.
            logger.info("plugins: %s did not answer release (%s)", self.renderer_id, exc)
            return False

    async def signal_stop(self, force: bool) -> None:
        """Process-level escalation. **Told, then done.**

        The plugin is given the chance to act first - it may know something
        about its own process that we do not - and the core then acts on the
        unit regardless. Not either/or: a plugin that answered `true` and did
        nothing would otherwise leave the device held with the ladder believing
        it had escalated.
        """
        try:
            await self._session.send("signal_stop", force=force)
        except PluginGone:
            pass
        self._signal_unit(self.unit_name, force=force)

    #: The scale `set_volume` is sent on. The contract carries `value` and
    #: `steps` together, so a plugin never has to guess which scale a number is
    #: on - and 100 is what every renderer here is normalised to before the
    #: hardware curve is applied (ADR-0054).
    VOLUME_STEPS = 100

    async def set_volume(self, value: int) -> None:
        """Drive this renderer's own volume (ADR-0053: the panel is a remote).

        Errors are swallowed for the same reason `release` does not raise: a
        renderer that has gone cannot be told anything, and the volume path runs
        on every drag of a slider. It is not a place to take the daemon down.
        """
        try:
            await self._session.send("set_volume", value=int(value), steps=self.VOLUME_STEPS)
        except PluginGone as exc:
            logger.info("plugins: %s did not take a volume (%s)", self.renderer_id, exc)

    async def device_freed(self) -> None:
        await self._tell("device_freed")

    async def restart_after_release(self) -> None:
        await self._tell("restart_after_release")

    async def _tell(self, command: str) -> None:
        """One of the two hooks that exist because of measured races rather
        than design (Findings 013 §1 and 014). A plugin with nothing to do
        answers `true`; one that has gone is past caring."""
        try:
            await self._session.send(command)
        except PluginGone:
            pass
