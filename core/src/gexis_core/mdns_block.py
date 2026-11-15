# SPDX-License-Identifier: GPL-3.0-or-later
"""**Uploaded plugins kept off the mDNS port after systemd reloads**
(ADR-0142 as amended 2026-11-14, Finding 148).

The uploaded-plugin units deny port 5353 (`SocketBindDeny=`), so a plugin's
own mDNS responder cannot answer for the Pi's name. systemd 257 takes that
block off every running unit at each `daemon-reload` - this core's own at
start, a package's, anyone's - and leaves the units' other filters in place
(bedroompi, 2026-11-14: 13 times in 14). A plugin running then can take the
port: one answered for `bedroompi.local` with an address avahi does not
announce, and avahi renamed the Pi `bedroompi-2`. Setting the property again
puts the block back on the running unit without restarting it, so this does
that after every reload, and once when it starts listening.
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
from typing import Awaitable, Callable

from dbus_next import BusType, Message, MessageType
from dbus_next.aio import MessageBus

logger = logging.getLogger(__name__)

#: As the uploaded-plugin units say it (a test holds the two together).
DENY = ("ipv4:udp:5353", "ipv6:udp:5353")
UNITS = ("gexis-uploaded-renderer@*.service", "gexis-uploaded-service@*.service")
#: systemd sends `Reloading` to every listener, true as a reload starts and
#: false once it is done (seen on bedroompi, 2026-11-14).
RELOADING_RULE = ("type='signal',sender='org.freedesktop.systemd1',path='/org/freedesktop/systemd1',"
                  "interface='org.freedesktop.systemd1.Manager',member='Reloading'")
RETRY_S = 30.0

Run = Callable[..., subprocess.CompletedProcess]


def running(run: Run = subprocess.run) -> list[str]:
    """The uploaded plugins' units running now."""
    out = run(["systemctl", "list-units", "--plain", "--no-legend", "--state=active", *UNITS],
              capture_output=True, text=True, check=False).stdout or ""
    return [line.split()[0] for line in out.splitlines() if line.split()]


def command(unit: str) -> list[str]:
    """The block set again, emptied first so that repeating it does not
    lengthen the list."""
    return ["systemctl", "set-property", "--runtime", unit, "SocketBindDeny=",
            *(f"SocketBindDeny={rule}" for rule in DENY)]


def reapply(run: Run = subprocess.run) -> list[str]:
    """The block put back on every running uploaded plugin; the units done."""
    done = []
    for unit in running(run):
        result = run(command(unit), capture_output=True, text=True, check=False)
        if result.returncode == 0:
            done.append(unit)
        else:
            logger.warning("plugins: port 5353 not denied again for %s: %s",
                           unit, (result.stderr or "").strip())
    if done:
        logger.info("plugins: port 5353 denied again for %s", ", ".join(done))
    return done


def reload_ended(message: Message) -> bool:
    """systemd's `Reloading(false)`: a reload has finished."""
    return (message.message_type == MessageType.SIGNAL
            and message.interface == "org.freedesktop.systemd1.Manager"
            and message.member == "Reloading" and message.body == [False])


async def _system_bus() -> MessageBus:
    return await MessageBus(bus_type=BusType.SYSTEM).connect()


async def watch(connect: Callable[[], Awaitable[MessageBus]] = _system_bus,
                again: Callable[[], object] = reapply, retry_s: float = RETRY_S) -> None:
    """For the life of the core: `again` after each reload systemd finishes,
    and once on connecting, for reloads missed while not listening (this
    core's own at start among them). A lost bus is connected again."""
    lock = asyncio.Lock()
    pending: set[asyncio.Task] = set()

    async def once() -> None:
        async with lock:
            try:
                await asyncio.to_thread(again)
            except Exception:  # noqa: BLE001 - the next reload tries again
                logger.exception("plugins: port 5353 not denied again")

    def handler(message: Message) -> None:
        if reload_ended(message):
            task = asyncio.ensure_future(once())
            pending.add(task)
            task.add_done_callback(pending.discard)

    while True:
        try:
            bus = await connect()
            await bus.call(Message(
                destination="org.freedesktop.DBus", path="/org/freedesktop/DBus",
                interface="org.freedesktop.DBus", member="AddMatch", signature="s", body=[RELOADING_RULE],
            ))
            bus.add_message_handler(handler)
            await once()
            await bus.wait_for_disconnect()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - listened for again below
            logger.exception("plugins: systemd's reloads not followed")
        await asyncio.sleep(retry_s)
