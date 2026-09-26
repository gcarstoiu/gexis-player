# SPDX-License-Identifier: GPL-3.0-or-later
"""**ADR-0089: arbitration carries a plugin renderer.**

The adapter itself is meant to be dull - "send that message on this session" -
so what is tested here is the two places it is allowed to be opinionated: what
it refuses to accept from a plugin, and what it does when the plugin is not
there any more.
"""
from __future__ import annotations

import asyncio

import pytest

from gexis_core.adapters.base import ReleaseAction, VolumeMechanism
from gexis_core.adapters.plugin import BadDeclaration, PluginAdapter, capabilities_from
from gexis_core.arbitration import TimeoutLadder
from gexis_core.plugin_server import PluginGone
from gexis_core.plugins import Plugin


def _plugin(**over):
    fields = {"id": "plexamp", "name": "Plexamp", "kind": "renderer",
              "unit": "plexamp.service"}
    return Plugin(**{**fields, **over})


class FakeSession:
    """A session that records what was sent and answers as told."""

    def __init__(self, declaration=None, *, answers=None, gone=False, plugin=None):
        self.plugin = plugin or _plugin()
        self.declaration = declaration if declaration is not None else {}
        self.sent = []
        self._answers = answers or {}
        self._gone = gone

    @property
    def id(self):
        return self.plugin.id

    async def send(self, t, **fields):
        self.sent.append((t, fields))
        if self._gone:
            raise PluginGone(f"{self.id}: no answer to {t}")
        return self._answers.get(t, True)


def _adapter(declaration=None, **kw):
    killed = []
    session = FakeSession(declaration, **kw)
    adapter = PluginAdapter(session, signal_unit=lambda unit, force: killed.append((unit, force)))
    return adapter, session, killed


# --- what it refuses ---------------------------------------------------------

@pytest.mark.parametrize("declaration, why", [
    ({"release_action": "explode"}, "release_action"),
    ({"capabilities": []}, "capabilities must be an object"),
    ({"capabilities": {"volume_mechanism": "telepathy"}}, "volume_mechanism"),
    ({"capabilities": {"controls": ["play", "fly"]}}, "unknown controls"),
    ({"capabilities": {"controls": "play"}}, "list of strings"),
    ({"capabilities": {"acquisition_events": [1]}}, "list of strings"),
    ({"capabilities": {"volume_mechanism": "dummy_mixer"}}, "dummy_mixer_card"),
    ({"release_ladder": 3}, "release_ladder must be an object"),
    ({"release_ladder": {"polite_grace": "soon"}}, "number of seconds"),
    ({"release_ladder": {"polite_grace": -1}}, "number of seconds"),
    ({"release_ladder": {"grace": 1}}, "unknown keys"),
])
def test_a_declaration_this_core_cannot_act_on_is_refused(declaration, why):
    """**Refused, not defaulted.** A renderer whose capabilities are wrong is
    worse than one that never connected: it would be offered on the panel,
    chosen, and then fail to do what it said."""
    with pytest.raises(BadDeclaration) as caught:
        PluginAdapter(FakeSession(declaration))
    assert why in str(caught.value)


def test_a_true_boolean_is_not_a_number_of_seconds():
    """`isinstance(True, int)` is the trap. A ladder of `True` seconds would
    pass a naive check and then time a release."""
    with pytest.raises(BadDeclaration):
        PluginAdapter(FakeSession({"release_ladder": {"polite_grace": True}}))


# --- what it takes -----------------------------------------------------------

def test_plexamps_own_declaration():
    """The shape Finding 077 says Plexamp needs: 14 s of hold after a stop its
    own API confirms instantly, so a polite grace longer than the default 3 s."""
    adapter = PluginAdapter(FakeSession({
        "release_action": "disconnect",
        "release_ladder": {"polite_grace": 16.0},
        "capabilities": {
            "audio_connection": "output",
            "acquisition_events": ["play from a Plex controller"],
            "supports_artwork": True, "supports_sample_rate": True,
            "volume_managed": True, "volume_mechanism": "software_api",
            "controls": ["play", "pause", "next", "previous"],
        },
    }))
    assert adapter.renderer_id == "plexamp"
    assert adapter.release_action is ReleaseAction.DISCONNECT
    assert adapter.release_ladder == TimeoutLadder(polite_grace=16.0)
    assert adapter.capabilities.volume_mechanism is VolumeMechanism.SOFTWARE_API
    assert adapter.capabilities.supports_artwork is True
    assert "next" in adapter.capabilities.controls


def test_no_ladder_means_the_supervisors_default():
    assert PluginAdapter(FakeSession({})).release_ladder is None


def test_the_manifest_owns_the_unit_not_the_declaration():
    """**ADR-0089.** The release ladder attributes a still-busy device to this
    name, so a renderer that could name its own could point process-level
    escalation at any unit on the device. The handshake refuses a mismatch;
    this is the same rule at the other end, where the value is used."""
    adapter = PluginAdapter(FakeSession({"unit": "sshd.service"}))
    assert adapter.unit_name == "plexamp.service"


# --- what it does ------------------------------------------------------------

async def test_release_is_the_polite_stop_and_nothing_more():
    adapter, session, killed = _adapter({})
    assert await adapter.release() is True
    assert session.sent == [("release", {})]
    assert killed == []


async def test_a_gone_plugin_reads_as_a_polite_stop_that_did_not_work():
    """Which is what it is. The ladder then escalates, and the step that
    actually frees the device never needed the plugin."""
    adapter, _, _ = _adapter({}, gone=True)
    assert await adapter.release() is False


async def test_signal_stop_tells_the_plugin_and_then_acts_itself():
    """**Not either/or** (ADR-0089). A plugin that answered `true` and did
    nothing would otherwise leave the device held with the ladder believing it
    had escalated."""
    adapter, session, killed = _adapter({})
    await adapter.signal_stop(force=False)
    await adapter.signal_stop(force=True)
    # `force` still reaches the plugin, so it can tell the two rungs apart.
    assert session.sent == [("signal_stop", {"force": False}), ("signal_stop", {"force": True})]
    # **But the signal is SIGKILL on both** (ADR-0091). This asserted
    # `(unit, False)` first - a real SIGTERM - until Finding 088 §3 measured
    # what that does: the unit goes `inactive` with `Result=success` and
    # `NRestarts=0`, because systemd does not count a SIGTERM death as a
    # failure, so `Restart=on-failure` never fires and the renderer does not
    # come back at all. `LmsAdapter.signal_stop` reached the same conclusion
    # for squeezelite.
    assert killed == [("plexamp.service", True), ("plexamp.service", True)]


async def test_a_gone_plugin_is_still_escalatable():
    """The whole reason `signal_stop` is a command *and* a core-side action: a
    plugin cannot strand the device by dying."""
    adapter, _, killed = _adapter({}, gone=True)
    await adapter.signal_stop(force=True)
    assert killed == [("plexamp.service", True)]


async def test_the_two_race_hooks_are_sent_and_survive_a_dead_plugin():
    adapter, session, _ = _adapter({})
    await adapter.device_freed()
    await adapter.restart_after_release()
    assert [t for t, _ in session.sent] == ["device_freed", "restart_after_release"]

    gone, _, _ = _adapter({}, gone=True)
    await gone.device_freed()
    await gone.restart_after_release()


async def test_run_parks_and_keeps_the_callbacks():
    """**The socket is the watch.** There is nothing to read here - the server
    is already reading it - but `run` is what holds the two callbacks, and a
    renderer whose task finished is a renderer that stopped watching."""
    adapter, _, _ = _adapter({})
    seen = []
    task = asyncio.ensure_future(adapter.run(lambda: seen.append("a"), lambda: seen.append("r")))
    await asyncio.sleep(0)
    assert not task.done()
    adapter.on_acquire()
    adapter.on_release()
    assert seen == ["a", "r"]
    task.cancel()


def test_defaults_are_the_quiet_ones():
    """A renderer that declares nothing gets a renderer that claims nothing -
    no artwork, no managed volume, no controls. The panel then offers none of
    it, which is right: it did not say it could."""
    caps = capabilities_from({})
    assert caps.supports_artwork is False
    assert caps.supports_sample_rate is False
    assert caps.volume_managed is False
    assert caps.controls == frozenset()
    assert caps.audio_connection == "output"


# --- ADR-0037's transport, which the core dispatches by method name ----------


@pytest.mark.parametrize("command, argument, wire", [
    ("play", None, ("transport", {"command": "play", "argument": None})),
    ("pause", None, ("transport", {"command": "pause", "argument": None})),
    ("next", None, ("transport", {"command": "next", "argument": None})),
    ("previous", None, ("transport", {"command": "previous", "argument": None})),
    ("shuffle", True, ("transport", {"command": "shuffle", "argument": True})),
    ("repeat", "all", ("transport", {"command": "repeat", "argument": "all"})),
])
async def test_each_declared_control_is_a_method_the_core_can_call(command, argument, wire):
    """**Found by pressing them** (Phase 11 criterion 5). `__main__.transport`
    does `getattr(adapter, command)`; the three built-ins each define these, and
    a plugin renderer without them declares controls the panel offers and then
    answers *"declares next but implements none"* with a 502."""
    adapter, session, _ = _adapter({})
    method = getattr(adapter, command)
    assert await (method() if argument is None else method(argument)) is True
    assert session.sent == [wire]


async def test_activate_is_its_own_message_not_a_transport_command():
    """The contract has `activate` at the top level, beside `transport`, because
    taking the device is not the same kind of act as changing what is playing."""
    adapter, session, _ = _adapter({})
    assert await adapter.activate() is True
    assert session.sent == [("activate", {})]


async def test_a_refusal_is_an_answer_not_an_exception():
    """The panel asked a renderer to do something and it would not. That is a
    502 at the route, not a traceback in the daemon."""
    adapter, _, _ = _adapter({}, gone=True)
    assert await adapter.next() is False
