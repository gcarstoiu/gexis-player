# SPDX-License-Identifier: GPL-3.0-or-later
"""The pairing agent (ADR-0045), Phase 9 subphase 9f.

The load-bearing property is the timeout: it is the agent's, because BlueZ
holds the handshake open for exactly as long as `RequestConfirmation`
takes. A panel-side timer would be a second clock, and a frame still
offering Accept after the phone gave up would trust a device whose request
no longer exists.
"""
from __future__ import annotations

import asyncio

import pytest
from dbus_next import DBusError

from gexis_core import bluetooth_agent as ba


def _agent(**kw):
    published = []
    agent = ba.Agent(
        publish=lambda r: published.append(r.to_json() if r else None),
        window=kw.pop("window", 0.2),
        linger=kw.pop("linger", 0.05),
        **kw,
    )
    made.append(agent)
    return agent, published


def test_the_capability_is_what_makes_blue_z_produce_a_code():
    """With NoInputNoOutput both ends agree there is nothing to compare and
    pairing runs Just Works - there is no code to show. Claiming a display
    is what turns it into RequestConfirmation."""
    assert ba.capability_for("Confirmation required") == "DisplayYesNo"
    assert ba.capability_for(None) == "DisplayYesNo", "confirmation is the default"
    assert ba.capability_for("PIN-free") == "NoInputNoOutput"


@pytest.fixture(autouse=True)
async def _no_dangling_lingers():
    """Every agent built here is closed, and **inside the loop** - a
    teardown that cancels a task after the loop has gone raises, which is
    its own small lesson about where cleanup has to run."""
    made.clear()
    yield
    for agent in made:
        agent.close()
    # Let the cancellations be delivered before the loop closes.
    await asyncio.sleep(0)


made = []


@pytest.mark.asyncio
async def test_accepting_returns_and_the_panel_is_told_each_step():
    agent, published = _agent()
    task = asyncio.ensure_future(agent._confirm("/org/bluez/dev_AA", 483920))
    await asyncio.sleep(0.02)
    assert published[0]["code"] == "483920" and published[0]["state"] == "asking"
    assert agent.answer(True) is True
    await task
    assert published[1]["state"] == "accepted"
    # And the frame is taken away rather than left on the last thing it said.
    await asyncio.sleep(0.1)
    assert published[-1] is None


@pytest.mark.asyncio
async def test_rejecting_raises_the_error_blue_z_understands():
    """Returning normally is consent. A refusal has to be an error, or the
    phone pairs anyway."""
    agent, published = _agent()
    task = asyncio.ensure_future(agent._confirm("/org/bluez/dev_AA", 1))
    await asyncio.sleep(0.02)
    agent.answer(False)
    with pytest.raises(DBusError) as raised:
        await task
    assert raised.value.type == ba.REJECTED
    assert published[1]["state"] == "rejected"


@pytest.mark.asyncio
async def test_the_window_expires_on_its_own_and_refuses():
    """**The agent's timeout.** Nobody answers; BlueZ is let go of here."""
    agent, published = _agent(window=0.08)
    with pytest.raises(DBusError):
        await agent._confirm("/org/bluez/dev_AA", 7)
    assert published[1]["state"] == "expired"
    assert agent.asking is False


@pytest.mark.asyncio
async def test_an_answer_after_the_window_is_refused_rather_than_ignored():
    """A tap that arrives late must not land on the next request, and the
    panel has to hear that it did not land."""
    agent, _ = _agent(window=0.05)
    with pytest.raises(DBusError):
        await agent._confirm("/org/bluez/dev_AA", 7)
    assert agent.answer(True) is False


@pytest.mark.asyncio
async def test_a_second_request_while_one_is_open_is_refused():
    """Otherwise it replaces the frame and the pending tap answers the
    wrong phone."""
    agent, _ = _agent(window=0.3)
    first = asyncio.ensure_future(agent._confirm("/org/bluez/dev_AA", 1))
    await asyncio.sleep(0.02)
    with pytest.raises(DBusError):
        await agent._confirm("/org/bluez/dev_BB", 2)
    agent.answer(True)
    await first


@pytest.mark.asyncio
async def test_the_remote_end_giving_up_takes_the_frame_with_it():
    """BlueZ calls Cancel when the phone walks away. A frame still offering
    Accept would be offering something that cannot be delivered."""
    agent, published = _agent(window=5)
    task = asyncio.ensure_future(agent._confirm("/org/bluez/dev_AA", 1))
    await asyncio.sleep(0.02)
    agent._cancel()
    with pytest.raises(DBusError):
        await task
    assert published[1]["state"] == "rejected"


@pytest.mark.asyncio
async def test_pin_free_does_not_ask_at_all():
    """ADR-0024's behaviour, kept as a choice: nothing reaches the panel."""
    agent, published = _agent(confirm_required=lambda: False)
    await agent._confirm("/org/bluez/dev_AA", 1)
    assert published == []


@pytest.mark.asyncio
async def test_an_already_paired_device_is_not_asked_about_per_service():
    """ADR-0045: the question is "should this device be allowed", not "is
    this you again"."""
    agent, published = _agent()
    await agent._authorize_service("/org/bluez/dev_AA", "0000110b-0000-1000-8000-00805f9b34fb")
    assert published == []


@pytest.mark.asyncio
async def test_a_keypad_request_is_refused_rather_than_unimplemented():
    """An agent that omits a method answers UnknownMethod mid-handshake,
    which surfaces as "pairing failed" with nothing to say why."""
    agent, _ = _agent()
    for call in (
        lambda: agent.RequestPinCode("/org/bluez/dev_AA"),
        lambda: agent.RequestPasskey("/org/bluez/dev_AA"),
    ):
        with pytest.raises(DBusError):
            call()


@pytest.mark.asyncio
async def test_the_code_is_six_digits_including_the_leading_zeros():
    """BlueZ hands over an integer; `1234` is the code `001234` on the
    phone's screen, and a frame showing `1234` is a frame nobody can
    match."""
    agent, published = _agent(window=0.05)
    with pytest.raises(DBusError):
        await agent._confirm("/org/bluez/dev_AA", 1234)
    assert published[0]["code"] == "001234"


@pytest.mark.asyncio
async def test_a_device_with_no_name_still_says_something_useful():
    """A frame that says "a device wants to pair" gives nobody enough to
    decide. With no bus to ask, the address in the object path is the
    answer."""
    agent, published = _agent(window=0.05)
    with pytest.raises(DBusError):
        await agent._confirm("/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF", 1)
    assert published[0]["device"] == "AA:BB:CC:DD:EE:FF"


@pytest.mark.asyncio
async def test_bt_autotrust_off_means_the_confirmation_does_not_trust():
    """It was a description of something that happened regardless - the
    separate trust unit polled and trusted everything. Now it decides."""
    agent, _ = _agent(should_trust=lambda: False, window=0.3)
    task = asyncio.ensure_future(agent._confirm("/org/bluez/dev_AA", 1))
    await asyncio.sleep(0.02)
    agent.answer(True)
    await task  # no bus, so this only has to not raise


# ── what actually goes on the wire ────────────────────────────────────────

def test_the_published_state_survives_json():
    """**The whole path, in one assertion.** The agent publishes its own
    object; the store holds what goes over the socket. Passing the dataclass
    straight through made `json.dumps` raise *inside the broadcast*, which
    took every other state update with it for as long as a request was open
    - the panel saw no pairing, and no volume, and no metadata either.

    Unit tests all passed: each side was right on its own. Only driving the
    agent over the real bus showed it (2026-09-21)."""
    import json

    from gexis_core.state import StateStore

    store = StateStore({})
    request = ba.PairingRequest(device="George's iPhone", code="001234")
    store.set_pairing(request.to_json())
    payload = json.loads(json.dumps(store.state.to_json()))
    assert payload["pairing"] == {
        "device": "George's iPhone",
        "code": "001234",
        "window": ba.WINDOW_S,
        "state": "asking",
    }


def test_the_store_refuses_the_agents_object():
    """So the next caller finds out here rather than in the broadcast."""
    from gexis_core.state import StateStore

    with pytest.raises(TypeError):
        StateStore({}).set_pairing(ba.PairingRequest(device="x", code="1"))


def test_only_an_open_question_takes_the_screen():
    """The outcome states and the clear are published like any other, but
    they must not lower the visualiser again: by then the request has been
    answered and whatever was on screen should come back on its own."""
    taken = []

    def publish(request):
        if request is not None and request.state == "asking":
            taken.append(request.device)

    for state in ("asking", "accepted", "rejected", "expired"):
        publish(ba.PairingRequest(device=state, code="1", state=state))
    publish(None)
    assert taken == ["asking"]


# ── the remembered devices (`bt_trusted`) ────────────────────────────────

class _Variant:
    """ObjectManager hands back `Variant`s and the code reads `.value`.

    A real `dbus_next.Variant` validates its signature against the value,
    so building one per type here would be a test about dbus_next. This is
    the only thing the code under test touches."""

    def __init__(self, value):
        self.value = value


def _Props(**kw):
    return {k: _Variant(v) for k, v in kw.items()}


class _Tree:
    def __init__(self, objects):
        self._objects = objects

    async def call_get_managed_objects(self):
        return self._objects


class _Obj:
    def __init__(self, iface, impl):
        self._ifaces = {iface: impl}

    def get_interface(self, name):
        return self._ifaces[name]


class _Remover:
    def __init__(self):
        self.removed = []

    async def call_remove_device(self, path):
        self.removed.append(path)


class _Bus:
    def __init__(self, objects, remover=None):
        self._objects = objects
        self.remover = remover or _Remover()

    async def introspect(self, service, path):
        return None

    def get_proxy_object(self, service, path, introspection):
        from gexis_core import bluetooth_adapter_state as bas

        if path == "/":
            return _Obj(bas.OBJECT_MANAGER_IFACE, _Tree(self._objects))
        return _Obj(bas.ADAPTER_IFACE, self.remover)

    def disconnect(self):
        pass


def _tree():
    from gexis_core import bluetooth_adapter_state as bas
    from gexis_core.bluetooth_devices import DEVICE_IFACE

    return {
        "/org/bluez/hci0": {bas.ADAPTER_IFACE: {}},
        "/org/bluez/hci0/dev_A": {
            DEVICE_IFACE: _Props(Paired=True, Trusted=True, Connected=True, Alias="Pixel 10 Pro", Address="64:9D:38:E3:E5:2A")
        },
        "/org/bluez/hci0/dev_B": {
            DEVICE_IFACE: _Props(Paired=True, Trusted=False, Connected=False, Alias="Kitchen Echo", Address="AA:BB:CC:DD:EE:FF")
        },
        # Seen while discoverable and never paired: a stranger who walked
        # past with Bluetooth on.
        "/org/bluez/hci0/dev_C": {
            DEVICE_IFACE: _Props(Paired=False, Trusted=False, Connected=False, Alias="Someone's Laptop", Address="11:22:33:44:55:66")
        },
    }


@pytest.mark.asyncio
async def test_only_paired_devices_are_listed():
    """BlueZ's tree also carries every phone and laptop that walked past
    while the adapter was discoverable. A list of strangers under "Trusted
    devices" would be things the user never chose and cannot act on."""
    from gexis_core import bluetooth_devices as bd

    items = await bd.known(_Bus(_tree()))
    assert [i["name"] for i in items] == ["Pixel 10 Pro", "Kitchen Echo"]
    assert items[0]["state"] == "connected" and items[0]["meta"] == "Connected"
    assert items[1]["state"] == "saved" and items[1]["meta"] == "Paired"


@pytest.mark.asyncio
async def test_forgetting_removes_the_bond_not_just_the_trust_flag():
    """`Trusted = false` leaves the bond: the phone still holds its key, the
    device still answers to it, and it reconnects. The row's note promises
    that forgetting "breaks its automatic reconnection"."""
    from gexis_core import bluetooth_devices as bd

    bus = _Bus(_tree())
    assert await bd.forget(bus, "Pixel 10 Pro") == (True, None)
    assert bus.remover.removed == ["/org/bluez/hci0/dev_A"]


@pytest.mark.asyncio
async def test_forgetting_something_that_is_not_paired_says_so():
    from gexis_core import bluetooth_devices as bd

    bus = _Bus(_tree())
    assert await bd.forget(bus, "Someone's Laptop") == (False, "That device is not paired.")
    assert bus.remover.removed == []
