# SPDX-License-Identifier: GPL-3.0-or-later
"""**The socket a plugin connects to** (ADR-0084, `docs/PLUGIN-CONTRACT.md`).

A Unix socket at `/run/gexis/plugins.sock`, one JSON object per line. The core
listens and plugins connect: they come and go, and the core is the fixed
point.

**Transport only.** This module knows about lines, ids and the handshake, and
nothing about arbitration, adapters or the state store - the same division
`wsserver.py` keeps for the browser. What arrives is handed to `on_event`;
what the daemon wants said goes out through `send`.

**A plugin must already be installed.** Its id has to match a manifest
(ADR-0086), because a plugin the core cannot draw and has no settings rows for
is one the panel would be unable to show. Connecting is how a plugin says it
is *running*, not how it says it exists.
"""
from __future__ import annotations

import asyncio
import json
import logging
import shutil
from pathlib import Path

logger = logging.getLogger("gexis_core.plugin_server")

DEFAULT_PATH = Path("/run/gexis/plugins.sock")

#: The contract this core serves. A plugin states what it speaks and is
#: refused if that is not this - never downgraded silently, because ADR-0016's
#: own consequence is that plugins in other repositories will lag, and a quiet
#: partial service is worse than a clear refusal.
CONTRACT = 1

#: **The group that may connect** (ADR-0084 as amended). The daemon is root, so
#: `0660` on its own is root-only; a plugin runs as its own unprivileged account
#: and joins this group. Named for what it grants rather than for the project,
#: because that is what an administrator reading `ls -l` needs to know.
GROUP = "gexis-plugins"

#: A line longer than this is not a message, it is a mistake or an attack.
#: The largest thing a plugin legitimately sends is a queue, and LMS's ceiling
#: is a few hundred tracks.
MAX_LINE = 1 << 20

#: What a plugin may send unprompted. Anything else is answered with an error
#: rather than ignored: a plugin author cannot see this log.
EVENTS = frozenset(
    {"acquire", "release", "available", "metadata", "queue", "volume"}
)

#: How long a command waits for its `ok` before the caller is told it failed.
#: Generous: a renderer's own API is on the other side of this.
REPLY_TIMEOUT_S = 10.0


class PluginGone(Exception):
    """The plugin disconnected, or never answered."""


class Session:
    """One connected plugin."""

    def __init__(self, plugin, declaration: dict, writer: asyncio.StreamWriter) -> None:
        self.plugin = plugin
        self.declaration = declaration
        self._writer = writer
        self._next_id = 0
        self._waiting: dict[int, asyncio.Future] = {}

    @property
    def id(self) -> str:
        return self.plugin.id

    @property
    def kind(self) -> str:
        return self.plugin.kind

    def _write(self, message: dict) -> None:
        self._writer.write((json.dumps(message, separators=(",", ":")) + "\n").encode())

    async def send(self, t: str, **fields):
        """A command, and its answer. Raises `PluginGone` if there is none."""
        self._next_id += 1
        ident = self._next_id
        waiter: asyncio.Future = asyncio.get_running_loop().create_future()
        self._waiting[ident] = waiter
        try:
            self._write({"t": t, "id": ident, **fields})
            await self._writer.drain()
            return await asyncio.wait_for(waiter, REPLY_TIMEOUT_S)
        except (ConnectionError, asyncio.TimeoutError) as exc:
            raise PluginGone(f"{self.id}: no answer to {t}") from exc
        finally:
            self._waiting.pop(ident, None)

    def _settle(self, message: dict) -> None:
        """An `ok` or `error` arriving for a command."""
        waiter = self._waiting.get(message.get("id"))
        if waiter is None or waiter.done():
            # A reply to something already timed out, or an id we never sent.
            # Dropped rather than raised: a late answer is not an error, and
            # an invented one is the plugin's bug to see in its own log.
            return
        if message["t"] == "ok":
            waiter.set_result(message.get("result", True))
        else:
            waiter.set_exception(PluginGone(message.get("message") or "refused"))

    def close(self) -> None:
        for waiter in self._waiting.values():
            if not waiter.done():
                waiter.set_exception(PluginGone(f"{self.id}: disconnected"))
        self._waiting.clear()
        self._writer.close()


class PluginServer:
    """Listens; hands every event to `on_event(session, type, message)`.

    `on_connect` and `on_disconnect` bracket a plugin's life, so the daemon
    can register and unregister whatever it wants to - an adapter, a row, a
    nothing.
    """

    def __init__(
        self,
        plugins,
        *,
        path: Path = DEFAULT_PATH,
        on_event=None,
        on_connect=None,
        on_disconnect=None,
        settings_for=None,
        contract: int = CONTRACT,
    ) -> None:
        self._installed = {p.id: p for p in plugins}
        self._path = path
        self._on_event = on_event
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        #: `settings_for(plugin_id) -> dict`. **Handed over in `welcome`**,
        #: because a plugin's rows outlive its process: somebody can change
        #: one while it is stopped, and it has to come up on the answer rather
        #: than on its own default (ADR-0086).
        self._settings_for = settings_for
        self._contract = contract
        self.sessions: dict[str, Session] = {}

    async def run(self) -> None:
        """Serve for the life of the process."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # A socket left by a daemon that died is not a reason to refuse to
        # start; nothing else may bind this path.
        self._path.unlink(missing_ok=True)
        server = await asyncio.start_unix_server(self._serve, path=str(self._path))
        # Nothing on the network can reach a filesystem socket, but anyone on
        # the device could: the permission is the authorisation (ADR-0084).
        self._path.chmod(0o660)
        self._give_the_group_access()
        logger.info("plugins: listening on %s (contract %d)", self._path, self._contract)
        async with server:
            await server.serve_forever()

    def _give_the_group_access(self) -> None:
        """**Who may connect** (ADR-0084 as amended 2026-09-25).

        `0660` alone means *root only*, because this daemon runs as root and so
        the socket is `root:root`. That was found by the first plugin written
        outside this repository: it ran as `pi`, as ADR-0087 says a plugin
        should, and got `Permission denied` - so the access model as built was
        "every plugin runs as root", which is the thing that record refused for
        Beszel.

        So the socket is group-owned by `GROUP`, and a plugin's unit runs as a
        user in it. The same shape `docker.sock` has, for the same reason: the
        permission is the authorisation and a group is how a permission names
        more than one account.

        **A missing group is a warning, not a failure.** A device upgraded from
        an image that predates the group would otherwise lose its daemon over a
        socket only root was using anyway.
        """
        try:
            shutil.chown(self._path, group=GROUP)
        except (LookupError, KeyError):
            logger.warning(
                "plugins: no %r group on this device - the socket stays root-only "
                "and any plugin not running as root will be refused by the "
                "kernel before it can say hello", GROUP,
            )
        except OSError as exc:
            logger.warning("plugins: could not give %r the socket: %s", GROUP, exc)

    async def _serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        session = None
        try:
            session = await self._greet(reader, writer)
            if session is None:
                return
            await self._listen(session, reader)
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        except Exception as exc:  # noqa: BLE001 - one plugin cannot take the rest
            logger.warning("plugins: %s", exc)
        finally:
            if session is not None:
                self.sessions.pop(session.id, None)
                session.close()
                logger.info("plugins: %s disconnected", session.id)
                if self._on_disconnect is not None:
                    self._on_disconnect(session)
            else:
                writer.close()

    async def _refuse(self, writer: asyncio.StreamWriter, reason: str) -> None:
        logger.warning("plugins: refused a connection - %s", reason)
        writer.write((json.dumps({"t": "refused", "reason": reason}) + "\n").encode())
        try:
            await writer.drain()
        except ConnectionError:
            pass
        writer.close()

    async def _greet(self, reader, writer) -> Session | None:
        """The handshake. Every refusal says why, on the wire and in the log."""
        try:
            line = await asyncio.wait_for(reader.readline(), REPLY_TIMEOUT_S)
        except asyncio.TimeoutError:
            await self._refuse(writer, "said nothing")
            return None
        if not line:
            writer.close()
            return None
        try:
            hello = json.loads(line)
        except ValueError:
            await self._refuse(writer, "first line was not JSON")
            return None
        if hello.get("t") != "hello":
            await self._refuse(writer, f"first message was {hello.get('t')!r}, not 'hello'")
            return None
        if hello.get("contract") != self._contract:
            await self._refuse(
                writer, f"contract {hello.get('contract')!r} is not served here "
                        f"(this core speaks {self._contract})")
            return None
        plugin = self._installed.get(hello.get("id"))
        if plugin is None:
            await self._refuse(
                writer, f"{hello.get('id')!r} is not installed - a plugin needs a "
                        f"manifest before it can connect")
            return None
        if plugin.id in self.sessions:
            await self._refuse(writer, f"{plugin.id} is already connected")
            return None
        if hello.get("kind") and hello["kind"] != plugin.kind:
            await self._refuse(
                writer, f"{plugin.id} says it is a {hello['kind']!r} and its manifest "
                        f"says {plugin.kind!r}")
            return None
        if hello.get("unit") and hello["unit"] != plugin.unit:
            # **The manifest owns the unit name** (ADR-0089). The release
            # ladder attributes a still-busy device to it, so a renderer that
            # could name its own at runtime could point process-level
            # escalation at any unit on the device. Refused rather than
            # ignored, because a plugin that believes it named something is
            # a plugin whose author needs to hear otherwise.
            await self._refuse(
                writer, f"{plugin.id} says its unit is {hello['unit']!r} and its "
                        f"manifest says {plugin.unit!r} - the manifest is the one "
                        f"the release ladder uses")
            return None

        session = Session(plugin, hello, writer)
        self.sessions[plugin.id] = session
        if self._on_connect is not None:
            # **Before `welcome`, and allowed to refuse** (ADR-0089). The
            # daemon builds a renderer's adapter here, and a declaration it
            # cannot act on has to cost the plugin its connection rather than
            # its arbitration: a renderer registered with wrong capabilities
            # would be offered on the panel, chosen, and then fail to do what
            # it said. This module still knows nothing about adapters - it
            # calls a callable and reports what came back.
            try:
                self._on_connect(session)
            except Exception as exc:  # noqa: BLE001 - the reason goes on the wire
                self.sessions.pop(plugin.id, None)
                await self._refuse(writer, f"{plugin.id}: {exc}")
                return None
        welcome = {"t": "welcome", "contract": self._contract}
        if self._settings_for is not None:
            welcome["settings"] = self._settings_for(plugin.id)
        session._write(welcome)
        await writer.drain()
        logger.info("plugins: %s connected (%s)", plugin.id, plugin.kind)
        return session

    async def _listen(self, session: Session, reader) -> None:
        while True:
            line = await reader.readline()
            if not line:
                return
            if len(line) > MAX_LINE:
                logger.warning("plugins: %s sent %d bytes on one line, dropping",
                               session.id, len(line))
                continue
            try:
                message = json.loads(line)
            except ValueError:
                logger.warning("plugins: %s sent a line that is not JSON", session.id)
                continue
            t = message.get("t")
            if t in ("ok", "error"):
                session._settle(message)
                continue
            if t not in EVENTS:
                logger.warning("plugins: %s sent %r, which is not an event", session.id, t)
                continue
            if self._on_event is not None:
                try:
                    self._on_event(session, t, message)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("plugins: handling %s from %s: %s", t, session.id, exc)
