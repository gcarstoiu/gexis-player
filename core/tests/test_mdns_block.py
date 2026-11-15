# SPDX-License-Identifier: GPL-3.0-or-later
"""The uploaded plugins' port-5353 block set again after systemd reloads
(ADR-0142 as amended, Finding 148)."""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

from dbus_next import Message, MessageType

from gexis_core import mdns_block

ROOT = Path(__file__).resolve().parents[2]
UNITS = ROOT / "image/stage-gexis/03-core/files"

LISTED = ("gexis-uploaded-renderer@example.service loaded active running Uploaded plugin example\n"
          "gexis-uploaded-service@beszel.service loaded active running Uploaded plugin beszel\n")


class Systemctl:
    """`systemctl` stood in for: what it was asked, and its answers."""

    def __init__(self, listed: str = LISTED, failing: str | None = None):
        self.listed, self.failing, self.calls = listed, failing, []

    def __call__(self, argv, **_):
        self.calls.append(argv)
        if argv[1] == "list-units":
            return subprocess.CompletedProcess(argv, 0, stdout=self.listed, stderr="")
        code = 1 if self.failing and self.failing in argv else 0
        return subprocess.CompletedProcess(argv, code, stdout="", stderr="Access denied" if code else "")


def test_the_block_is_the_units_own():
    for name in ("gexis-uploaded-renderer@.service", "gexis-uploaded-service@.service"):
        lines = (UNITS / name).read_text().splitlines()
        assert tuple(line.split("=", 1)[1] for line in lines if line.startswith("SocketBindDeny=")) == mdns_block.DENY


def test_only_running_uploaded_plugins_are_asked_for():
    run = Systemctl()
    assert mdns_block.running(run) == ["gexis-uploaded-renderer@example.service",
                                       "gexis-uploaded-service@beszel.service"]
    argv = run.calls[0]
    assert "--state=active" in argv and set(mdns_block.UNITS) <= set(argv)


def test_set_again_emptied_first_so_it_does_not_grow():
    assert mdns_block.command("gexis-uploaded-renderer@example.service") == [
        "systemctl", "set-property", "--runtime", "gexis-uploaded-renderer@example.service",
        "SocketBindDeny=", "SocketBindDeny=ipv4:udp:5353", "SocketBindDeny=ipv6:udp:5353"]


def test_every_running_plugin_is_done_and_one_refused_does_not_stop_the_rest(caplog):
    run = Systemctl(failing="gexis-uploaded-renderer@example.service")
    assert mdns_block.reapply(run) == ["gexis-uploaded-service@beszel.service"]
    assert [c[3] for c in run.calls if c[1] == "set-property"] == [
        "gexis-uploaded-renderer@example.service", "gexis-uploaded-service@beszel.service"]
    assert "not denied again for gexis-uploaded-renderer@example.service: Access denied" in caplog.text


def test_none_running_is_nothing_to_do():
    run = Systemctl(listed="")
    assert mdns_block.reapply(run) == []
    assert len(run.calls) == 1


def reloading(active: bool, member: str = "Reloading") -> Message:
    return Message(message_type=MessageType.SIGNAL, path="/org/freedesktop/systemd1",
                   interface="org.freedesktop.systemd1.Manager", member=member,
                   signature="b", body=[active])


def test_only_the_end_of_a_reload_counts():
    assert mdns_block.reload_ended(reloading(False))
    assert not mdns_block.reload_ended(reloading(True))
    assert not mdns_block.reload_ended(reloading(False, member="UnitNew"))


class Bus:
    def __init__(self):
        self.rules, self.handlers = [], []
        self.gone = asyncio.Event()

    async def call(self, message):
        self.rules.append(message.body[0])

    def add_message_handler(self, handler):
        self.handlers.append(handler)

    def say(self, message):
        for handler in self.handlers:
            handler(message)

    async def wait_for_disconnect(self):
        await self.gone.wait()


async def settle():
    for _ in range(20):
        await asyncio.sleep(0)
    await asyncio.sleep(0.05)


def test_set_on_connecting_and_after_each_reload_and_followed_again_after_a_lost_bus():
    async def go():
        buses, done = [], []

        async def connect():
            buses.append(Bus())
            return buses[-1]

        task = asyncio.create_task(mdns_block.watch(connect, again=lambda: done.append(1), retry_s=0))
        await settle()
        assert len(done) == 1                      # on connecting: reloads missed
        assert buses[0].rules == [mdns_block.RELOADING_RULE]
        buses[0].say(reloading(True))
        await settle()
        assert len(done) == 1                      # a reload under way: not yet
        buses[0].say(reloading(False))
        await settle()
        assert len(done) == 2                      # it has finished
        buses[0].gone.set()                        # the bus lost
        await settle()
        assert len(buses) == 2 and len(done) == 3  # connected again, set again
        task.cancel()
    asyncio.run(go())


def test_a_failure_is_logged_and_the_watch_goes_on(caplog):
    async def go():
        bus = Bus()

        async def connect():
            return bus

        def again():
            raise OSError("systemctl missing")

        task = asyncio.create_task(mdns_block.watch(connect, again=again, retry_s=0))
        await settle()
        bus.say(reloading(False))
        await settle()
        assert not task.done()
        task.cancel()
    asyncio.run(go())
    assert caplog.text.count("port 5353 not denied again") == 2
