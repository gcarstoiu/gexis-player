# SPDX-License-Identifier: GPL-3.0-or-later
"""The state WebSocket (Phase 3 criterion 1, ARCHITECTURE.md's "state
WebSocket already exists" - this is where it comes from) and the REST
command surface (Phase 4, [ADR-0028]). aiohttp, not a new dependency -
already pinned for the LMS/Spotify adapters' HTTP clients.

Push, not poll (ADR-0018's "subscribed, not polled" principle, restated
here for the same reason): a client gets the current state immediately on
connect, then a fresh payload only when `StateStore` actually changes -
never a fixed tick. This is what makes criterion 6's bounded latency
measurement meaningful: the number characterises how fast a change
propagates, not a polling interval it happens to beat.

**The socket stays publish-only; commands are POSTs** (ADR-0028). The
deciding reason was error reporting: an activation can fail in ways the
user must be told about (LMS unreachable), and a broadcast-only socket has
nowhere to put that without correlation IDs or a "last command result"
field grafted onto the published state. An HTTP status says it to the
caller that asked. This module holds no policy - the handlers are
callables injected by `__main__.py`, so what a command *does* stays with
the wiring that knows about adapters.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from aiohttp import web

from gexis_core.adapters.base import TRANSPORT_COMMANDS
from gexis_core.model import PlaybackState
from gexis_core.settings_registry import InvalidValue, NotSettable, NotWired, UnknownSetting
from gexis_core.state import StateStore

logger = logging.getLogger("gexis_core.wsserver")

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8090


class StateServer:
    def __init__(
        self,
        store: StateStore,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        *,
        activate=None,
        transport=None,
        set_volume=None,
        set_mute=None,
        idle_page=None,
        settings=None,
        peppy=None,
        ui_dir: Path | None = None,
    ) -> None:
        """`activate(renderer_id) -> bool` and `set_volume(percent) -> bool`
        are injected by `__main__.py` (ADR-0028's command surface). Both are
        optional: without them the routes still exist and answer 503, which
        is a truer answer than a 404 for a server that has the concept but
        no wiring behind it.

        `ui_dir` is the built Svelte output (ADR-0028: this daemon serves
        the UI, in the same process and on the same origin as `/state`).
        Optional because the daemon must run perfectly well without it -
        which is every deployment before Phase 4b, and any development run
        where only the core is installed.
        """
        self._store = store
        self._host = host
        self._port = port
        self._activate = activate
        self._transport = transport
        self._set_volume = set_volume
        self._set_mute = set_mute
        self._idle_page = idle_page
        self._settings = settings
        self._peppy = peppy
        self._ui_dir = ui_dir
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
                # The socket is publish-only by decision, not by omission
                # (ADR-0028) - commands are POSTs. Drain and ignore so a
                # client that sends anything doesn't desync the connection.
                pass
        finally:
            self._clients.discard(ws)
            logger.info("wsserver: client disconnected (%d remaining)", len(self._clients))
        return ws

    async def _handle_activate(self, request: web.Request) -> web.Response:
        renderer_id = request.match_info["renderer_id"]
        if self._activate is None:
            return web.json_response({"error": "activation is not wired up"}, status=503)
        known = self._store.state.capabilities
        if renderer_id not in known:
            return web.json_response({"error": f"unknown renderer {renderer_id}"}, status=404)
        # ADR-0020's rule, applied to a command rather than a control: a
        # renderer that cannot be activated says so, rather than accepting
        # the request and silently doing nothing. `controls` is the
        # declaration criterion 2 built for exactly this (Phase 3 left it
        # empty because nothing could act on a command yet).
        if "activate" not in known[renderer_id].controls:
            return web.json_response(
                {"error": f"{renderer_id} does not declare an activate control"}, status=409
            )
        if not await self._activate(renderer_id):
            # The adapter's own API refused or was unreachable. 502 rather
            # than 500: the failure is upstream of us, and the UI needs to
            # tell the user where rather than blame the panel.
            return web.json_response({"error": f"{renderer_id} did not activate"}, status=502)
        return web.json_response({"activated": renderer_id})

    async def _handle_transport(self, request: web.Request) -> web.Response:
        """ADR-0037 §1: to whoever is active, never to a renderer by name - a
        command to one that is not active would be an acquisition, and that
        has its own path. `200` means sent; what happened arrives on /state."""
        command = request.match_info["command"]
        if command not in TRANSPORT_COMMANDS:
            return web.json_response({"error": f"unknown transport command {command}"}, status=404)
        if self._transport is None:
            return web.json_response({"error": "transport is not wired up"}, status=503)
        state = self._store.state
        if state.active is None:
            return web.json_response({"error": "nothing is active"}, status=409)
        if command not in state.capabilities[state.active].controls:
            return web.json_response(
                {"error": f"{state.active} does not declare {command}"}, status=409
            )
        if not await self._transport(state.active, command):
            return web.json_response({"error": f"{state.active} did not take {command}"}, status=502)
        return web.json_response({"sent": command, "renderer": state.active})

    async def _handle_set_volume(self, request: web.Request) -> web.Response:
        if self._set_volume is None:
            return web.json_response({"error": "volume control is not wired up"}, status=503)
        try:
            body = await request.json()
            percent = float(body["percent"])
        except (ValueError, KeyError, TypeError):
            return web.json_response(
                {"error": 'body must be {"percent": <number 0-100>}'}, status=400
            )
        if not 0 <= percent <= 100:
            return web.json_response({"error": "percent must be 0-100"}, status=400)
        if not await self._set_volume(percent):
            return web.json_response({"error": "volume write failed"}, status=502)
        return web.json_response({"percent": percent})

    async def _handle_set_mute(self, request: web.Request) -> web.Response:
        if self._set_mute is None:
            return web.json_response({"error": "mute is not wired up"}, status=503)
        try:
            muted = (await request.json())["muted"]
        except (ValueError, KeyError, TypeError):
            muted = None
        if not isinstance(muted, bool):
            return web.json_response({"error": 'body must be {"muted": true|false}'}, status=400)
        if not await self._set_mute(muted):
            return web.json_response({"error": "volume level not known yet"}, status=409)
        return web.json_response({"muted": muted})

    async def _handle_idle(self, request: web.Request) -> web.Response:
        """`idle_page() -> {url, embeddable, reason}`, asked each time the
        idle screen opens: reachability changes while the device runs."""
        if self._idle_page is None:
            return web.json_response({"error": "idle page is not wired up"}, status=503)
        return web.json_response(await self._idle_page())

    async def _handle_surface(self, request: web.Request) -> web.Response:
        """ADR-0035 §6: the panel always arrives on loopback, a phone from the LAN."""
        panel = request.remote in ("127.0.0.1", "::1")
        return web.json_response({"surface": "panel" if panel else "remote"})

    async def _handle_touch(self, request: web.Request) -> web.Response:
        """The panel telling the daemon somebody touched it. The daemon cannot
        see touches itself: they land in whichever window has the screen."""
        if self._peppy is not None:
            self._peppy.on_touch()
        return web.json_response({"touched": True})

    async def _handle_peppy(self, request: web.Request) -> web.Response:
        action = request.match_info["action"]
        if self._peppy is None:
            return web.json_response({"error": "the Peppy screen is not wired up"}, status=503)
        if action not in ("show", "hide"):
            return web.json_response({"error": f"unknown action {action}"}, status=404)
        shown = self._peppy.request(action)
        if not shown:
            return web.json_response({"error": "no Peppy screen window to act on"}, status=409)
        return web.json_response({"peppy": action})

    async def _handle_settings(self, request: web.Request) -> web.Response:
        if self._settings is None:
            return web.json_response({"error": "settings are not wired up"}, status=503)
        return web.json_response({"groups": self._settings.to_json()})

    async def _handle_setting_write(self, request: web.Request) -> web.Response:
        if self._settings is None:
            return web.json_response({"error": "settings are not wired up"}, status=503)
        key = request.match_info["key"]
        try:
            body = await request.json()
            value = body["value"]
        except (ValueError, KeyError, TypeError):
            return web.json_response({"error": 'body must be {"value": ...}'}, status=400)
        return self._settings_call(lambda: {"key": key, "value": self._settings.set(key, value)})

    async def _handle_setting_action(self, request: web.Request) -> web.Response:
        if self._settings is None:
            return web.json_response({"error": "settings are not wired up"}, status=503)
        key = request.match_info["key"]

        def run():
            self._settings.run(key)
            return {"key": key}

        return self._settings_call(run)

    @staticmethod
    def _settings_call(call) -> web.Response:
        try:
            return web.json_response(call())
        except UnknownSetting as exc:
            return web.json_response({"error": f"unknown setting {exc.args[0]}"}, status=404)
        except NotSettable as exc:
            return web.json_response({"error": str(exc)}, status=405)
        except NotWired as exc:
            return web.json_response({"error": str(exc)}, status=409)
        except InvalidValue as exc:
            return web.json_response({"error": str(exc)}, status=400)

    def make_app(self) -> web.Application:
        """Split out from `run()` so tests can drive the routes with
        aiohttp's own `test_utils.TestServer`/`TestClient` - a real
        WebSocket client and real HTTP requests against a real
        (ephemeral-port) server, matching Phase 3's own testing approach
        (DEVELOPMENT.md: "tested with a WebSocket client") - rather than
        binding a fixed port or reaching into `run()`'s internals.
        """
        app = web.Application()
        app.router.add_get("/state", self._handle)
        app.router.add_post("/renderer/{renderer_id}/activate", self._handle_activate)
        app.router.add_post("/transport/{command}", self._handle_transport)
        app.router.add_post("/volume", self._handle_set_volume)
        app.router.add_post("/volume/mute", self._handle_set_mute)
        app.router.add_get("/idle", self._handle_idle)
        app.router.add_get("/surface", self._handle_surface)
        app.router.add_post("/touch", self._handle_touch)
        app.router.add_post("/peppy/{action}", self._handle_peppy)
        app.router.add_get("/settings", self._handle_settings)
        app.router.add_put("/settings/{key}", self._handle_setting_write)
        app.router.add_post("/settings/{key}", self._handle_setting_action)
        # The UI is registered *after* the API, so nothing it serves can
        # shadow `/state` or a command route - aiohttp resolves in
        # registration order. Two routes only, which is why vite is
        # configured to emit everything under assets/: a greedy catch-all
        # would put that ordering guarantee back in play every time a
        # route is added.
        if self._ui_dir is not None:
            app.router.add_get("/", self._handle_index)
            app.router.add_static("/assets", self._ui_dir / "assets")
        return app

    async def _handle_index(self, request: web.Request) -> web.FileResponse:
        return web.FileResponse(self._ui_dir / "index.html")

    async def run(self) -> None:
        runner = web.AppRunner(self.make_app())
        await runner.setup()
        site = web.TCPSite(runner, self._host, self._port)
        await site.start()
        logger.info("wsserver: listening on ws://%s:%d/state", self._host, self._port)
        await asyncio.Event().wait()
