# SPDX-License-Identifier: GPL-3.0-or-later
"""The state WebSocket (Phase 3 criterion 1, ARCHITECTURE.md's "state
WebSocket already exists" - this is where it comes from). aiohttp, not a
new dependency - already pinned for the LMS/Spotify adapters' HTTP clients.

Push, not poll (ADR-0018's "subscribed, not polled" principle, restated
here for the same reason): a client gets the current state immediately on
connect, then a fresh payload only when `StateStore` actually changes -
never a fixed tick. This is what makes criterion 6's bounded latency
measurement meaningful: the number characterises how fast a change
propagates, not a polling interval it happens to beat.
"""
from __future__ import annotations

import asyncio
import json
import logging

from aiohttp import web

from gexis_core.model import PlaybackState
from gexis_core.state import StateStore

logger = logging.getLogger("gexis_core.wsserver")

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8090


class StateServer:
    def __init__(self, store: StateStore, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        self._store = store
        self._host = host
        self._port = port
        self._clients: set[web.WebSocketResponse] = set()
        store.subscribe(self._broadcast)

    def _broadcast(self, state: PlaybackState) -> None:
        if not self._clients:
            return
        payload = json.dumps(state.to_json())
        for ws in list(self._clients):
            asyncio.create_task(self._send(ws, payload))

    async def _send(self, ws: web.WebSocketResponse, payload: str) -> None:
        try:
            await ws.send_str(payload)
        except ConnectionResetError:
            # The client's own disconnect handling (below) removes it from
            # `_clients` - a send racing that teardown is expected, not an
            # error worth logging.
            pass

    async def _handle(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._clients.add(ws)
        logger.info("wsserver: client connected (%d total)", len(self._clients))
        try:
            # Sent directly, not via _broadcast - a new client needs the
            # current snapshot exactly once, regardless of whether anything
            # has changed since the last broadcast to everyone else.
            await ws.send_str(json.dumps(self._store.state.to_json()))
            async for _ in ws:
                # No client-to-server messages are defined yet (criterion 1
                # is publish-only) - drain and ignore so a client that sends
                # anything doesn't desync the connection.
                pass
        finally:
            self._clients.discard(ws)
            logger.info("wsserver: client disconnected (%d remaining)", len(self._clients))
        return ws

    def make_app(self) -> web.Application:
        """Split out from `run()` so tests can drive the route with
        aiohttp's own `test_utils.TestServer`/`TestClient` - a real
        WebSocket client against a real (ephemeral-port) server, matching
        Phase 3's own testing approach (DEVELOPMENT.md: "tested with a
        WebSocket client") - rather than binding a fixed port or reaching
        into `run()`'s internals to find one.
        """
        app = web.Application()
        app.router.add_get("/state", self._handle)
        return app

    async def run(self) -> None:
        runner = web.AppRunner(self.make_app())
        await runner.setup()
        site = web.TCPSite(runner, self._host, self._port)
        await site.start()
        logger.info("wsserver: listening on ws://%s:%d/state", self._host, self._port)
        await asyncio.Event().wait()
