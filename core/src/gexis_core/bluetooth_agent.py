# SPDX-License-Identifier: GPL-3.0-or-later
"""The pairing agent, asking on the panel (ADR-0045).

This replaces `gexis-bt-agent.service`, which ran `bt-agent
--capability=NoInputNoOutput` from bluez-tools: a binary that answers the
handshake on its own console and has no route to anything. So this was
never a capability flag on an existing agent - it is a BlueZ `Agent1` of
our own, registered on the system bus, which is the only way the question
can reach a screen.

**`DisplayYesNo` is what makes BlueZ produce a code.** With
`NoInputNoOutput` both ends agree there is nothing to compare and pairing
runs "Just Works" - no code exists to show. The capability is a claim about
what the device can do, and claiming a display is what turns the exchange
into `RequestConfirmation(device, passkey)` with six digits to match against
the phone's.

**The timeout is this agent's, and that is the load-bearing part**
(ADR-0045). `RequestConfirmation` blocks until someone answers; BlueZ is
holding the handshake open for exactly as long as we take. A panel-side
timer would be a second clock, and a frame still offering Accept after the
phone gave up is a lie - tapping it would trust a device whose request no
longer exists. So the panel's countdown is a display of this one, and the
frame goes away when this says so, not when the animation ends.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable

from dbus_next import DBusError, Variant
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method

#: Two things about dbus_next's `@method()`, both found the hard way:
#: every annotation on an exported method is read as a D-Bus signature
#: string, so a void one carries no return annotation at all (`-> None` is
#: a ValueError at import); and the decorator returns a wrapper that calls
#: the function and **discards its result**, keeping the original only as
#: dispatch metadata. So the exported names are unusable from Python - they
#: always answer None - and every one below is a thin shell over a normal
#: method that holds the logic and can be called and tested directly.

logger = logging.getLogger(__name__)

BLUEZ_SERVICE = "org.bluez"
AGENT_MANAGER_IFACE = "org.bluez.AgentManager1"
AGENT_IFACE = "org.bluez.Agent1"
DEVICE_IFACE = "org.bluez.Device1"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"

#: Where our agent lives on the bus. Any free path; namespaced so it is
#: obvious whose it is in `busctl tree`.
AGENT_PATH = "/gexis/bluetooth/agent"

#: "DisplayYesNo" produces a six-digit code and calls RequestConfirmation.
#: "NoInputNoOutput" is ADR-0024's Just Works, kept for `bt_pairing:
#: PIN-free` - see `capability_for`.
CONFIRM_CAPABILITY = "DisplayYesNo"
PINFREE_CAPABILITY = "NoInputNoOutput"

#: ADR-0045: thirty seconds, then the request is gone.
WINDOW_S = 30.0
#: How long "Request expired" or "Rejected" stays up before the frame goes.
#: The panel holds it too; this is what stops the request lingering in the
#: published state after nobody is looking at it.
LINGER_S = 2.0

REJECTED = "org.bluez.Error.Rejected"
CANCELED = "org.bluez.Error.Canceled"


@dataclass(frozen=True)
class PairingRequest:
    """What the panel draws. `window` is the whole allowance, not what is
    left: the panel starts counting when it receives this, which is within
    a frame of the agent starting its own timer, and the frame is dismissed
    by `state` changing rather than by the count reaching zero."""

    device: str
    code: str
    window: float = WINDOW_S
    #: asking -> accepted | rejected | expired
    state: str = "asking"

    def to_json(self) -> dict:
        return {
            "device": self.device,
            "code": self.code,
            "window": self.window,
            "state": self.state,
        }


def capability_for(pairing: str | None) -> str:
    """ADR-0045: confirmation is the default, PIN-free stays a choice."""
    return PINFREE_CAPABILITY if pairing == "PIN-free" else CONFIRM_CAPABILITY


class Agent(ServiceInterface):
    """`org.bluez.Agent1`.

    Every method BlueZ may call is implemented, including the ones this
    capability should never see: an agent that omits one answers
    `UnknownMethod` mid-handshake, and the failure surfaces as "pairing
    failed" on the phone with nothing on our side to say why.
    """

    def __init__(
        self,
        *,
        publish: Callable[[PairingRequest | None], None],
        confirm_required: Callable[[], bool] = lambda: True,
        should_trust: Callable[[], bool] = lambda: True,
        window: float = WINDOW_S,
        linger: float = LINGER_S,
    ) -> None:
        super().__init__(AGENT_IFACE)
        self._publish = publish
        self._confirm_required = confirm_required
        self._should_trust = should_trust
        self._window = window
        self._linger = linger
        self._pending: asyncio.Future | None = None
        #: Held rather than fired and forgotten: a linger from the previous
        #: request would otherwise clear the frame of the next one.
        self._linger_task: asyncio.Task | None = None
        self._device_path: str | None = None
        self._bus: MessageBus | None = None

    # ── what the daemon calls ────────────────────────────────────────────

    def answer(self, accept: bool) -> bool:
        """The panel's answer. False if nothing is being asked - a tap that
        arrives after the window closed must not land on the next request."""
        if self._pending is None or self._pending.done():
            return False
        self._pending.set_result(accept)
        return True

    @property
    def asking(self) -> bool:
        return self._pending is not None and not self._pending.done()

    # ── the interface BlueZ drives ───────────────────────────────────────

    @method()
    def Release(self):  # noqa: N802 - D-Bus method name
        logger.info("bt-agent: released by BlueZ")
        self._finish(None)

    @method()
    async def RequestConfirmation(self, device: "o", passkey: "u"):
        return await self._confirm(device, passkey)

    @method()
    async def RequestAuthorization(self, device: "o"):
        return await self._authorize(device)

    @method()
    async def AuthorizeService(self, device: "o", uuid: "s"):  # noqa: N802,F821
        # A service on an *already paired* device. ADR-0045: the question is
        # "should this device be allowed", not "is this you again" - so a
        # trusted device is not asked about again, per service, forever.
        return await self._authorize_service(device, uuid)

    @method()
    def Cancel(self):  # noqa: N802
        # The phone gave up first, and the frame must go with it.
        self._cancel()

    @method()
    def RequestPinCode(self, device: "o") -> "s":  # noqa: N802,F821
        raise DBusError(REJECTED, "this device does not take a PIN")

    @method()
    def RequestPasskey(self, device: "o") -> "u":  # noqa: N802,F821
        raise DBusError(REJECTED, "this device has no keypad")

    @method()
    def DisplayPinCode(self, device: "o", pincode: "s"):  # noqa: N802,F821
        logger.info("bt-agent: PIN %s for %s (not shown)", pincode, device)

    @method()
    def DisplayPasskey(self, device: "o", passkey: "u", entered: "q"):  # noqa: N802,F821
        logger.info("bt-agent: passkey %06d for %s (not shown)", passkey, device)

    # ── the logic those shells carry ─────────────────────────────────────

    async def _confirm(self, device: str, passkey: int) -> None:
        """Six digits, shown on both ends, and a human says whether they
        match. Returning normally accepts; raising Rejected refuses - to
        BlueZ, coming back without an error *is* consent."""
        # BlueZ hands over an integer: 1234 is `001234` on the phone, and a
        # frame showing `1234` is a frame nobody can match.
        code = f"{passkey:06d}"
        if not self._confirm_required():
            logger.info("bt-agent: PIN-free, accepting %s without asking", device)
            await self._trust(device)
            return
        name = await self._name_of(device)
        logger.info("bt-agent: confirmation for %r, code %s", name, code)
        if not await self._ask(PairingRequest(device=name, code=code), device):
            raise DBusError(REJECTED, "rejected on the panel")
        await self._trust(device)

    async def _authorize(self, device: str) -> None:
        """No code to compare - the other end has no display either. The
        question is still worth asking, so the frame shows no digits."""
        if not self._confirm_required():
            await self._trust(device)
            return
        name = await self._name_of(device)
        if not await self._ask(PairingRequest(device=name, code=""), device):
            raise DBusError(REJECTED, "rejected on the panel")
        await self._trust(device)

    async def _authorize_service(self, device: str, uuid: str) -> None:
        logger.info("bt-agent: authorising %s for %s", uuid, device)

    def _cancel(self) -> None:
        logger.info("bt-agent: cancelled by the remote end")
        if self._pending is not None and not self._pending.done():
            self._pending.set_result(False)

    # ── the waiting itself ───────────────────────────────────────────────

    async def _ask(self, request: PairingRequest, device_path: str) -> bool:
        # A new question cancels the last one's fade-out, so the frame it is
        # about to draw is not cleared two seconds later by the old timer.
        self.close()
        if self.asking:
            # One at a time. A second phone arriving mid-question would
            # otherwise replace the frame and the first tap would answer
            # the wrong request.
            raise DBusError(REJECTED, "another pairing request is open")
        loop = asyncio.get_running_loop()
        self._pending = loop.create_future()
        self._device_path = device_path
        self._publish(request)
        try:
            accepted = await asyncio.wait_for(self._pending, self._window)
            outcome = "accepted" if accepted else "rejected"
        except asyncio.TimeoutError:
            # **The agent's timeout, not the panel's.** BlueZ is still
            # holding the handshake; letting go here is what ends it.
            accepted, outcome = False, "expired"
            logger.info("bt-agent: %r expired after %ss", request.device, self._window)
        self._publish(PairingRequest(request.device, request.code, request.window, outcome))
        self._pending = None
        if self._linger_task is not None:
            self._linger_task.cancel()
        self._linger_task = asyncio.ensure_future(self._clear_after_linger())
        return accepted

    async def _clear_after_linger(self) -> None:
        try:
            await asyncio.sleep(self._linger)
        except asyncio.CancelledError:
            return
        if not self.asking:
            self._publish(None)

    def close(self) -> None:
        """Stop the linger timer. For tests and for a clean shutdown."""
        if self._linger_task is not None:
            self._linger_task.cancel()
            self._linger_task = None

    def _finish(self, _unused) -> None:
        if self._pending is not None and not self._pending.done():
            self._pending.set_result(False)
        self._publish(None)

    # ── BlueZ lookups ────────────────────────────────────────────────────

    async def _name_of(self, path: str) -> str:
        """The phone's own name, falling back to its address. A frame that
        says "a device wants to pair" gives nobody enough to decide."""
        if self._bus is None:
            return path.rsplit("/", 1)[-1].replace("dev_", "").replace("_", ":")
        try:
            introspection = await self._bus.introspect(BLUEZ_SERVICE, path)
            obj = self._bus.get_proxy_object(BLUEZ_SERVICE, path, introspection)
            props = await obj.get_interface(PROPERTIES_IFACE).call_get_all(DEVICE_IFACE)
            for key in ("Alias", "Name", "Address"):
                value = props.get(key)
                if value is not None and value.value:
                    return str(value.value)
        except Exception as exc:
            logger.info("bt-agent: could not read %s: %s", path, exc)
        return path.rsplit("/", 1)[-1].replace("dev_", "").replace("_", ":")

    async def _trust(self, path: str) -> None:
        """Trust what was just confirmed, and only that.

        ADR-0045 flagged `bt_autotrust` for re-examination and this is the
        answer. The separate `gexis-bluetooth-trust.service` trusts *every*
        paired-but-untrusted device on a 2 s poll, which would grant exactly
        what a human was asked about and might have refused - the
        confirmation would decide nothing, and the poll would not know a
        rejection had happened. Trusting here ties it to the answer, and
        `bt_autotrust` becomes a real switch rather than a description of
        something that happened regardless.
        """
        if self._bus is None or not self._should_trust():
            return
        try:
            introspection = await self._bus.introspect(BLUEZ_SERVICE, path)
            obj = self._bus.get_proxy_object(BLUEZ_SERVICE, path, introspection)
            await obj.get_interface(PROPERTIES_IFACE).call_set(
                DEVICE_IFACE, "Trusted", Variant("b", True)
            )
            logger.info("bt-agent: trusted %s", path)
        except Exception as exc:
            logger.warning("bt-agent: could not trust %s: %s", path, exc)


async def unregister(bus: MessageBus) -> bool:
    """Give up being BlueZ's default agent, so a new capability can be
    registered in its place (ADR-0022's `bt_pairing`, 2026-09-25).

    **The capability is fixed at registration**, so changing between
    confirmation and PIN-free means unregistering and registering again.
    BlueZ allows one agent per path, and re-registering without this fails
    with `AlreadyExists`.
    """
    try:
        introspection = await bus.introspect(BLUEZ_SERVICE, "/org/bluez")
        obj = bus.get_proxy_object(BLUEZ_SERVICE, "/org/bluez", introspection)
        await obj.get_interface(AGENT_MANAGER_IFACE).call_unregister_agent(AGENT_PATH)
        return True
    except DBusError as exc:
        logger.warning("bt-agent: could not unregister: %s", exc)
        return False


async def register(bus: MessageBus, agent: Agent, capability: str) -> bool:
    """Export the agent and make it BlueZ's default.

    **Default matters**: without `RequestDefaultAgent` BlueZ keeps whatever
    agent registered first - whatever else is on the bus - and ours is never
    called, which looks exactly like pairing silently not asking.
    """
    agent._bus = bus
    # Exporting a path twice raises; re-registering with a new capability
    # goes through here again with the same agent.
    if not getattr(agent, "_exported", False):
        bus.export(AGENT_PATH, agent)
        agent._exported = True
    introspection = await bus.introspect(BLUEZ_SERVICE, "/org/bluez")
    obj = bus.get_proxy_object(BLUEZ_SERVICE, "/org/bluez", introspection)
    manager = obj.get_interface(AGENT_MANAGER_IFACE)
    try:
        await manager.call_register_agent(AGENT_PATH, capability)
        await manager.call_request_default_agent(AGENT_PATH)
    except DBusError as exc:
        logger.warning("bt-agent: could not register (%s): %s", capability, exc)
        return False
    logger.info("bt-agent: registered as %s with capability %s", AGENT_PATH, capability)
    return True
