# SPDX-License-Identifier: GPL-3.0-or-later
"""**mpv's JSON socket, as the radio renderer uses it** (ADR-0180 item 3).

mpv's own protocol (its manual, *JSON IPC*): one JSON object per line each
way. A command is `{"command": [...], "request_id": n}` and is answered by a
line carrying the same `request_id` and `"error": "success"` or the reason.
Everything else that arrives is an event, `{"event": "..."}` - among them
`property-change` for each property asked for with `observe_property`.

Nothing here knows about radio: it connects, sends, answers, and hands the
events on. The renderer (`adapters/radio.py`) decides what they mean.
"""
from __future__ import annotations

import asyncio
import itertools
import json
import logging
from typing import Callable

logger = logging.getLogger("gexis_core.mpv_ipc")

#: A command mpv does not answer in this long is taken as failed.
REPLY_TIMEOUT_S = 3.0
#: One line from mpv can carry a whole metadata block; a stream's tags are
#: small, but nothing caps them but this.
LINE_LIMIT = 1 << 20


class MpvError(Exception):
    """mpv answered a command with something other than success, or did not
    answer at all."""


class Mpv:
    """One connection to one mpv. `on_event` is called with each event's
    dict, in the order they arrive; `on_close` once, when the connection
    ends for any reason."""

    def __init__(self, on_event: Callable[[dict], None],
                 on_close: Callable[[], None] | None = None) -> None:
        self._on_event = on_event
        self._on_close = on_close
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._ids = itertools.count(1)
        self._waiting: dict[int, asyncio.Future] = {}
        self._task: asyncio.Task | None = None

    @property
    def connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def connect(self, path: str) -> None:
        self._reader, self._writer = await asyncio.open_unix_connection(path, limit=LINE_LIMIT)
        self._task = asyncio.create_task(self._read(), name="mpv-ipc")

    async def command(self, *args, timeout: float = REPLY_TIMEOUT_S):
        """Send one command; its `data` when mpv says success, else
        `MpvError`."""
        if not self.connected:
            raise MpvError("not connected")
        request_id = next(self._ids)
        future = asyncio.get_running_loop().create_future()
        self._waiting[request_id] = future
        line = json.dumps({"command": list(args), "request_id": request_id}) + "\n"
        try:
            self._writer.write(line.encode())
            await self._writer.drain()
            reply = await asyncio.wait_for(future, timeout)
        except (OSError, asyncio.TimeoutError) as exc:
            raise MpvError(f"{args[0]}: {exc or type(exc).__name__}") from exc
        finally:
            self._waiting.pop(request_id, None)
        if reply.get("error") != "success":
            raise MpvError(f"{args[0]}: {reply.get('error')}")
        return reply.get("data")

    async def close(self) -> None:
        if self._writer is not None:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except OSError:
                pass
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001 - closing
                pass

    async def _read(self) -> None:
        try:
            while True:
                try:
                    raw = await self._reader.readline()
                except (OSError, ValueError) as exc:
                    # ValueError: a line over the limit - the stream cannot be
                    # read in step after it, so the connection ends.
                    logger.warning("mpv: connection read failed: %s", exc)
                    break
                if not raw:
                    break
                try:
                    message = json.loads(raw)
                except ValueError:
                    logger.warning("mpv: a line that is not JSON: %r", raw[:200])
                    continue
                if not isinstance(message, dict):
                    continue
                request_id = message.get("request_id")
                if "event" not in message and isinstance(request_id, int):
                    future = self._waiting.get(request_id)
                    if future is not None and not future.done():
                        future.set_result(message)
                    continue
                if "event" in message:
                    try:
                        self._on_event(message)
                    except Exception:  # noqa: BLE001 - one bad event is not the end
                        logger.exception("mpv: handling %s failed", message.get("event"))
        finally:
            for future in self._waiting.values():
                if not future.done():
                    future.set_exception(MpvError("connection closed"))
            if self._writer is not None:
                self._writer.close()
            if self._on_close is not None:
                try:
                    self._on_close()
                except Exception:  # noqa: BLE001
                    logger.exception("mpv: on_close failed")
