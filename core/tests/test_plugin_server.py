# SPDX-License-Identifier: GPL-3.0-or-later
"""**The socket a plugin connects to** (ADR-0084).

Driven over a real Unix socket rather than by calling methods: the handshake
*is* the contract, and a test that skips it tests something else. Most of what
is here is refusals, because a plugin author cannot see this device's log and
the wire is the only place they can be told.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from gexis_core.plugin_server import CONTRACT, PluginGone, PluginServer
from gexis_core.plugins import Plugin


RENDERER = Plugin(id="plexamp", name="Plexamp", kind="renderer", unit="plexamp.service")
SERVICE = Plugin(id="beszel", name="Beszel agent", kind="service", unit="beszel.service")


class Harness:
    """A running server and a client socket, torn down together."""

    def __init__(self, tmp_path, **kwargs):
        self.path = tmp_path / "plugins.sock"
        self.events: list[tuple[str, str, dict]] = []
        self.connected: list[str] = []
        self.gone: list[str] = []
        self.server = PluginServer(
            kwargs.pop("plugins", [RENDERER, SERVICE]),
            path=self.path,
            on_event=lambda s, t, m: self.events.append((s.id, t, m)),
            on_connect=lambda s: self.connected.append(s.id),
            on_disconnect=lambda s: self.gone.append(s.id),
            **kwargs,
        )

    async def __aenter__(self):
        self._task = asyncio.ensure_future(self.server.run())
        for _ in range(100):
            if self.path.exists():
                break
            await asyncio.sleep(0.01)
        return self

    async def __aexit__(self, *exc):
        self._task.cancel()
        try:
            await self._task
        except (asyncio.CancelledError, Exception):
            pass

    async def connect(self):
        return await asyncio.open_unix_connection(str(self.path))


async def _say(writer, message):
    writer.write((json.dumps(message) + "\n").encode())
    await writer.drain()


async def _hear(reader):
    line = await asyncio.wait_for(reader.readline(), 3)
    return json.loads(line) if line else None


async def _hello(h, **overrides):
    reader, writer = await h.connect()
    await _say(writer, {"t": "hello", "contract": CONTRACT, "id": "plexamp",
                        "kind": "renderer", **overrides})
    return reader, writer, await _hear(reader)


# ---------------------------------------------------------------------------
# The handshake
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_good_hello_is_welcomed(tmp_path):
    async with Harness(tmp_path) as h:
        reader, writer, answer = await _hello(h)
        assert answer == {"t": "welcome", "contract": CONTRACT}
        assert h.connected == ["plexamp"]
        writer.close()


@pytest.mark.asyncio
async def test_a_service_needs_nothing_a_renderer_needs(tmp_path):
    """**The shape the Beszel agent has to fit.** If this cannot be said, the
    contract is a renderer API wearing a plugin's name."""
    async with Harness(tmp_path) as h:
        reader, writer = await h.connect()
        await _say(writer, {"t": "hello", "contract": CONTRACT, "id": "beszel"})
        assert (await _hear(reader))["t"] == "welcome"
        assert h.server.sessions["beszel"].kind == "service"
        writer.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("hello, because", [
    ({"t": "hello", "contract": 2, "id": "plexamp"}, "not served here"),
    ({"t": "hello", "id": "plexamp"}, "not served here"),
    ({"t": "hello", "contract": CONTRACT, "id": "qobuz"}, "not installed"),
    ({"t": "acquire"}, "not 'hello'"),
    ({"t": "hello", "contract": CONTRACT, "id": "plexamp", "kind": "service"},
     "its manifest says"),
    # **ADR-0089: the manifest owns the unit name.** The release ladder
    # attributes a still-busy device to it, so a renderer that could name its
    # own at runtime could point process-level escalation at any unit here.
    ({"t": "hello", "contract": CONTRACT, "id": "plexamp", "unit": "sshd.service"},
     "the release ladder uses"),
])
async def test_what_is_refused_and_why(tmp_path, hello, because):
    """Refused **on the wire**, with a reason. The log is on a device the
    plugin's author cannot read."""
    async with Harness(tmp_path) as h:
        reader, writer = await h.connect()
        await _say(writer, hello)
        answer = await _hear(reader)
        assert answer["t"] == "refused"
        assert because in answer["reason"]
        assert h.connected == []
        writer.close()


@pytest.mark.asyncio
async def test_a_first_line_that_is_not_json_is_refused(tmp_path):
    async with Harness(tmp_path) as h:
        reader, writer = await h.connect()
        writer.write(b"hello there\n")
        await writer.drain()
        assert "not JSON" in (await _hear(reader))["reason"]
        writer.close()


@pytest.mark.asyncio
async def test_the_same_plugin_cannot_connect_twice(tmp_path):
    """Two connections claiming one id means one of them gets commands meant
    for the other."""
    async with Harness(tmp_path) as h:
        r1, w1, first = await _hello(h)
        assert first["t"] == "welcome"
        r2, w2, second = await _hello(h)
        assert second["t"] == "refused"
        assert "already connected" in second["reason"]
        w1.close(); w2.close()


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_events_reach_the_daemon(tmp_path):
    async with Harness(tmp_path) as h:
        reader, writer, _ = await _hello(h)
        await _say(writer, {"t": "acquire"})
        await _say(writer, {"t": "metadata", "metadata": {"title": "Song"}})
        for _ in range(100):
            if len(h.events) >= 2:
                break
            await asyncio.sleep(0.01)
        assert [(i, t) for i, t, _ in h.events] == [("plexamp", "acquire"), ("plexamp", "metadata")]
        assert h.events[1][2]["metadata"]["title"] == "Song"
        writer.close()


@pytest.mark.asyncio
async def test_something_that_is_not_an_event_is_dropped_not_dispatched(tmp_path):
    async with Harness(tmp_path) as h:
        reader, writer, _ = await _hello(h)
        await _say(writer, {"t": "take_over_everything"})
        await _say(writer, {"t": "release"})
        for _ in range(100):
            if h.events:
                break
            await asyncio.sleep(0.01)
        assert [t for _, t, _ in h.events] == ["release"]
        writer.close()


@pytest.mark.asyncio
async def test_a_handler_that_raises_does_not_drop_the_connection(tmp_path):
    """One bad event must not cost a renderer its session."""
    async with Harness(tmp_path) as h:
        h.server._on_event = lambda *a: (_ for _ in ()).throw(RuntimeError("boom"))
        reader, writer, _ = await _hello(h)
        await _say(writer, {"t": "acquire"})
        await asyncio.sleep(0.05)
        assert "plexamp" in h.server.sessions
        writer.close()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_command_gets_its_answer(tmp_path):
    async with Harness(tmp_path) as h:
        reader, writer, _ = await _hello(h)
        session = h.server.sessions["plexamp"]

        async def plugin():
            command = await _hear(reader)
            assert command["t"] == "release"
            await _say(writer, {"t": "ok", "id": command["id"], "result": True})

        answer, _ = await asyncio.gather(session.send("release"), plugin())
        assert answer is True
        writer.close()


@pytest.mark.asyncio
async def test_an_error_reaches_the_caller(tmp_path):
    async with Harness(tmp_path) as h:
        reader, writer, _ = await _hello(h)
        session = h.server.sessions["plexamp"]

        async def plugin():
            command = await _hear(reader)
            await _say(writer, {"t": "error", "id": command["id"], "message": "no can do"})

        with pytest.raises(PluginGone, match="no can do"):
            await asyncio.gather(session.send("release"), plugin())
        writer.close()


@pytest.mark.asyncio
async def test_disconnecting_fails_whatever_was_waiting(tmp_path):
    """The supervisor is on the other end of this. A command that hangs for
    ever is a takeover that never completes."""
    async with Harness(tmp_path) as h:
        reader, writer, _ = await _hello(h)
        session = h.server.sessions["plexamp"]
        pending = asyncio.ensure_future(session.send("release"))
        await asyncio.sleep(0.05)
        writer.close()
        with pytest.raises(PluginGone):
            await asyncio.wait_for(pending, 3)


@pytest.mark.asyncio
async def test_a_reply_to_nothing_is_ignored(tmp_path):
    async with Harness(tmp_path) as h:
        reader, writer, _ = await _hello(h)
        await _say(writer, {"t": "ok", "id": 999, "result": True})
        await _say(writer, {"t": "acquire"})
        for _ in range(100):
            if h.events:
                break
            await asyncio.sleep(0.01)
        assert [t for _, t, _ in h.events] == ["acquire"]
        writer.close()


@pytest.mark.asyncio
async def test_a_disconnect_is_announced(tmp_path):
    async with Harness(tmp_path) as h:
        reader, writer, _ = await _hello(h)
        writer.close()
        for _ in range(100):
            if h.gone:
                break
            await asyncio.sleep(0.01)
        assert h.gone == ["plexamp"]
        assert "plexamp" not in h.server.sessions


@pytest.mark.asyncio
async def test_the_socket_is_not_world_writable(tmp_path):
    """ADR-0084: the permission on the socket is the authorisation."""
    async with Harness(tmp_path) as h:
        assert h.path.stat().st_mode & 0o007 == 0


@pytest.mark.asyncio
async def test_a_unit_that_matches_the_manifest_is_fine(tmp_path):
    """Saying it is allowed; disagreeing is not. A plugin author who writes it
    twice should not be punished for agreeing with themselves."""
    async with Harness(tmp_path) as h:
        reader, writer = await h.connect()
        await _say(writer, {"t": "hello", "contract": CONTRACT, "id": "plexamp",
                            "unit": h.server._installed["plexamp"].unit})
        assert (await _hear(reader))["t"] == "welcome"
        writer.close()


@pytest.mark.asyncio
async def test_on_connect_can_refuse_the_connection(tmp_path):
    """**ADR-0089.** The daemon builds a renderer's adapter in `on_connect`,
    and a declaration it cannot act on has to cost the plugin its connection
    rather than its arbitration - a renderer registered with wrong capabilities
    would be offered on the panel, chosen, and then fail to do what it said.

    So it runs **before** `welcome`, and this module still knows nothing about
    adapters: it calls a callable and reports what came back.
    """
    async with Harness(tmp_path) as h:
        def refuse(session):
            raise ValueError("unknown controls: ['fly']")

        h.server._on_connect = refuse
        reader, writer = await h.connect()
        await _say(writer, {"t": "hello", "contract": CONTRACT, "id": "plexamp"})
        answer = await _hear(reader)
        assert answer["t"] == "refused"
        assert "unknown controls" in answer["reason"]
        # And it left nothing behind: a refused plugin is not connected.
        assert "plexamp" not in h.server.sessions
        writer.close()
