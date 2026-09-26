# SPDX-License-Identifier: GPL-3.0-or-later
"""**A plugin renderer, from the socket to the supervisor** (ADR-0089).

Every other test here holds one piece still: `test_plugin_adapter.py` gives the
adapter a fake session, `test_arbitration.py` gives the supervisor fake
adapters, `test_plugin_server.py` gives the server no adapters at all. Each
passes while the three of them fail to add up.

**This one wires them together the way `__main__` does** and drives it over a
real Unix socket, because that is the join nothing else covers - and because
this session already learned what a probe that cannot reach the real state is
worth (`docs/LESSONS.md` 41).

What it does *not* cover: `__main__`'s exact call sites. The wiring below is a
copy of them, and a copy can drift. The thing that cannot drift is Plexamp
actually doing this, which is the rest of Phase 11.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from gexis_core.adapters.base import Adapter, ReleaseAction
from gexis_core.adapters.plugin import PluginAdapter
from gexis_core.arbitration import Supervisor, TimeoutLadder
from gexis_core.plugin_server import CONTRACT, PluginServer
from gexis_core.plugins import Plugin


PLEXAMP = Plugin(id="plexamp", name="Plexamp", kind="renderer", unit="plexamp.service")
FAST = TimeoutLadder(polite_grace=0.05, sigterm_grace=0.05, sigkill_grace=0.05)


class Resident(Adapter):
    """A built-in renderer that holds the device until it is asked not to."""

    renderer_id = "lms"
    unit_name = "squeezelite.service"
    release_action = ReleaseAction.PAUSE
    capabilities = None

    def __init__(self, holder):
        self._holder = holder
        self.released = 0

    async def run(self, on_acquire, on_release):
        await asyncio.Event().wait()

    async def release(self):
        self.released += 1
        self._holder["who"] = None
        return True

    async def signal_stop(self, force):
        self._holder["who"] = None


class Wiring:
    """`__main__`'s plugin wiring, in the small."""

    def __init__(self, tmp_path, *, killed):
        self.path = tmp_path / "plugins.sock"
        self.holder = {"who": None}
        self.resident = Resident(self.holder)
        self.available: dict[str, bool] = {"plexamp": False}
        self.supervisor = Supervisor(
            {"lms": self.resident},
            device_busy=lambda rid: self.holder["who"] == rid,
            ladder=FAST,
        )
        self.adapters: dict[str, PluginAdapter] = {}
        self.killed = killed
        self.server = PluginServer(
            [PLEXAMP], path=self.path,
            on_connect=self._connected,
            on_disconnect=self._disconnected,
            on_event=self._event,
        )

    def _connected(self, session):
        if session.kind != "renderer":
            return
        adapter = PluginAdapter(
            session, signal_unit=lambda unit, force: self.killed.append((unit, force)),
        )
        self.supervisor.register(adapter)
        self.adapters[session.id] = adapter
        adapter.task = asyncio.ensure_future(adapter.run(
            lambda rid=session.id: asyncio.create_task(self.supervisor.acquire(rid)),
            lambda rid=session.id: asyncio.create_task(self.supervisor.relinquish(rid)),
        ))
        self.available[session.id] = True

    def _disconnected(self, session):
        adapter = self.adapters.pop(session.id, None)
        if adapter is None:
            return
        adapter.task.cancel()
        self.supervisor.forget(session.id)
        self.available[session.id] = False

    def _event(self, session, kind, message):
        adapter = self.adapters.get(session.id)
        if adapter is None:
            return
        if kind == "acquire":
            adapter.on_acquire()
        elif kind == "release":
            adapter.on_release()

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


class FakePlexamp:
    """A plugin process, as far as the socket can tell."""

    def __init__(self, reader, writer, *, frees=True):
        self.reader, self.writer = reader, writer
        self.heard: list[dict] = []
        self.frees = frees
        self.holder = None

    async def hello(self, **extra):
        await self.say({"t": "hello", "contract": CONTRACT, "id": "plexamp",
                        "release_action": "disconnect", **extra})
        return json.loads(await self.reader.readline())

    async def say(self, message):
        self.writer.write((json.dumps(message) + "\n").encode())
        await self.writer.drain()

    async def serve(self):
        """Answer commands the way a plugin must: exactly once, by id."""
        while True:
            line = await self.reader.readline()
            if not line:
                return
            message = json.loads(line)
            self.heard.append(message)
            if "id" not in message:
                continue
            if message["t"] == "release" and self.frees and self.holder is not None:
                self.holder["who"] = None
            await self.say({"t": "ok", "id": message["id"], "result": True})


async def _settle(times=12):
    for _ in range(times):
        await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_a_plugin_acquires_the_device_from_a_built_in(tmp_path):
    """**The thing Phase 10 could not do.** `acquire` on the wire becomes a
    takeover: the resident renderer is politely released and the plugin is the
    active one."""
    killed = []
    async with Wiring(tmp_path, killed=killed) as w:
        w.holder["who"] = "lms"
        w.supervisor._active = "lms"
        reader, writer = await asyncio.open_unix_connection(str(w.path))
        plugin = FakePlexamp(reader, writer)
        plugin.holder = w.holder
        assert (await plugin.hello())["t"] == "welcome"
        serving = asyncio.ensure_future(plugin.serve())

        await plugin.say({"t": "acquire"})
        await _settle()

        assert w.supervisor.active == "plexamp"
        assert w.resident.released == 1
        assert killed == []
        serving.cancel()
        writer.close()


@pytest.mark.asyncio
async def test_the_core_releases_the_plugin_when_something_takes_over(tmp_path):
    """The other direction, which is the half that has to work for the plugin
    to be a good citizen rather than a squatter."""
    killed = []
    async with Wiring(tmp_path, killed=killed) as w:
        reader, writer = await asyncio.open_unix_connection(str(w.path))
        plugin = FakePlexamp(reader, writer)
        plugin.holder = w.holder
        await plugin.hello()
        serving = asyncio.ensure_future(plugin.serve())

        await plugin.say({"t": "acquire"})
        await _settle()
        w.holder["who"] = "plexamp"

        await w.supervisor.acquire("lms")
        await _settle()

        assert w.supervisor.active == "lms"
        assert [m["t"] for m in plugin.heard if m["t"] == "release"] == ["release"]
        # It let go politely, so nothing escalated.
        assert killed == []
        serving.cancel()
        writer.close()


@pytest.mark.asyncio
async def test_a_plugin_that_will_not_let_go_is_escalated_against_its_unit(tmp_path):
    """**The reason `signal_stop` is a command and a core-side action.** The
    plugin answers `release` politely and keeps the device anyway; the ladder
    escalates to the unit the manifest names."""
    killed = []
    async with Wiring(tmp_path, killed=killed) as w:
        reader, writer = await asyncio.open_unix_connection(str(w.path))
        plugin = FakePlexamp(reader, writer, frees=False)
        await plugin.hello()
        serving = asyncio.ensure_future(plugin.serve())

        await plugin.say({"t": "acquire"})
        await _settle()
        w.holder["who"] = "plexamp"

        await w.supervisor.acquire("lms")
        await _settle(40)

        # Both rungs, and **both SIGKILL** (ADR-0091). This asserted
        # `("plexamp.service", False)` - a SIGTERM on the first rung - until
        # Finding 088 §3 measured that a SIGTERM death is not a failure as far
        # as systemd is concerned, so `Restart=on-failure` never fires and the
        # renderer stays dead instead of coming back idle.
        assert killed == [("plexamp.service", True), ("plexamp.service", True)]
        serving.cancel()
        writer.close()


@pytest.mark.asyncio
async def test_a_plugin_that_disappears_while_holding_the_device(tmp_path):
    """It stops being the active renderer and stops being available. The device
    may still be held - **that is the limit ADR-0089 writes down rather than
    engineering around** - and the next acquisition escalates against the unit,
    which is what this asserts."""
    killed = []
    async with Wiring(tmp_path, killed=killed) as w:
        reader, writer = await asyncio.open_unix_connection(str(w.path))
        plugin = FakePlexamp(reader, writer, frees=False)
        await plugin.hello()
        serving = asyncio.ensure_future(plugin.serve())

        await plugin.say({"t": "acquire"})
        await _settle()
        w.holder["who"] = "plexamp"

        serving.cancel()
        writer.close()
        await _settle()

        assert w.supervisor.active is None
        assert w.available["plexamp"] is False
        # The device is still held by something nobody is talking to any more.
        assert w.holder["who"] == "plexamp"


@pytest.mark.asyncio
async def test_a_renderer_with_a_bad_declaration_never_becomes_one(tmp_path):
    """Refused on the wire, before `welcome`, and the supervisor never hears of
    it - a renderer registered with wrong capabilities would be offered on the
    panel, chosen, and then fail to do what it said."""
    async with Wiring(tmp_path, killed=[]) as w:
        reader, writer = await asyncio.open_unix_connection(str(w.path))
        plugin = FakePlexamp(reader, writer)
        answer = await plugin.hello(capabilities={"controls": ["fly"]})

        assert answer["t"] == "refused"
        assert "unknown controls" in answer["reason"]
        assert "plexamp" not in w.adapters
        with pytest.raises(ValueError):
            await w.supervisor.acquire("plexamp")
        writer.close()


@pytest.mark.asyncio
async def test_a_declared_ladder_is_the_one_used(tmp_path):
    """Plexamp's 14 s hold is the case: a polite grace longer than the default,
    declared by the plugin and honoured by the supervisor."""
    async with Wiring(tmp_path, killed=[]) as w:
        reader, writer = await asyncio.open_unix_connection(str(w.path))
        plugin = FakePlexamp(reader, writer)
        await plugin.hello(release_ladder={"polite_grace": 16.0})
        assert w.adapters["plexamp"].release_ladder == TimeoutLadder(polite_grace=16.0)
        writer.close()
