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
from gexis_core.artistinfo import PHOTO_LARGE, PHOTO_THUMB
from gexis_core.enrichment import Enrichment, TrackKey
from gexis_core.library import LibraryUnavailable, NoPlayer, NotFound
from gexis_core.radio import RadioUnavailable, UnknownHandle
from gexis_core.model import PlaybackState
from gexis_core.settings_registry import InvalidValue, NotSettable, NotWired, UnknownSetting
from gexis_core.state import StateStore

#: The most artists one request may ask photos for. A screen of
#: cards is about 40; this is a bound on what a caller can make the
#: daemon do in one go, not a page size.
PHOTO_BATCH = 80

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
        library=None,
        artistinfo=None,
        enrichment=None,
        radio=None,
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
        self._library = library
        self._artistinfo = artistinfo
        self._enrichment = enrichment
        self._radio = radio
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
        if command not in state.controls["available"]:
            return web.json_response(
                {"error": f"{command} cannot work on {state.active} right now"}, status=409
            )
        argument = None
        if command in ("shuffle", "repeat"):
            try:
                body = await request.json()
            except ValueError:
                body = None
            if command == "shuffle":
                argument = body.get("on") if isinstance(body, dict) else None
                if not isinstance(argument, bool):
                    return web.json_response({"error": 'body must be {"on": true|false}'}, status=400)
            else:
                argument = body.get("mode") if isinstance(body, dict) else None
                if argument not in ("off", "all", "one"):
                    return web.json_response(
                        {"error": 'body must be {"mode": "off"|"all"|"one"}'}, status=400
                    )
        if not await self._transport(state.active, command, argument):
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

    async def _handle_library(self, request: web.Request) -> web.Response:
        """ADR-0038 §5: reads only, for the designed screens. The panel asks
        for what a screen shows and gets the fields it draws; it never sends
        an LMS command. 502 when LMS cannot be reached (the renderer
        routes' convention), 404 for an id that does not exist - which a
        rescan makes of every id (Finding 029 §4)."""
        if self._library is None:
            return web.json_response({"error": "the library is not wired up"}, status=503)
        what = request.match_info["what"]
        item = request.match_info.get("id")
        sub = request.match_info.get("sub")
        try:
            offset = max(0, int(request.query.get("offset", 0)))
            limit = min(1000, max(1, int(request.query.get("limit", 1000))))
            item_id = int(item) if item is not None else None
        except ValueError:
            return web.json_response({"error": "offset, limit and ids are integers"}, status=400)
        library = self._library
        reads = {
            ("counts", False, None): lambda: library.counts(),
            ("new", False, None): lambda: library.new_music(),
            ("artists", False, None): lambda: library.artists(offset, limit),
            ("artists", True, "albums"): lambda: library.artist_albums(item_id),
            ("albums", True, None): lambda: library.album(item_id),
            ("playlists", False, None): lambda: library.playlists(),
            ("playlists", True, None): lambda: library.playlist(item_id, offset, limit),
        }
        read = reads.get((what, item_id is not None, sub))
        if read is None:
            return web.json_response({"error": f"no library read {request.path}"}, status=404)
        try:
            return web.json_response(await read())
        except NotFound as exc:
            return web.json_response({"error": f"{exc} not found"}, status=404)
        except LibraryUnavailable as exc:
            return web.json_response({"error": f"LMS unreachable: {exc}"}, status=502)

    async def _handle_library_action(self, request: web.Request) -> web.Response:
        """ADR-0038 §5: one route for what the panel does to the library.
        `{"kind": "album"|"artist"|"track"|"playlist", "id": <int>,
        "action": "play"|"add"|"playlist"}`, with `playlist_id` when adding
        to one. A `200` means the command was sent; what happened is read
        from `/state`, as for transport (ADR-0037 §1)."""
        if self._library is None:
            return web.json_response({"error": "the library is not wired up"}, status=503)
        try:
            body = await request.json()
            kind = str(body["kind"])
            action = str(body.get("action", "play"))
            item_id = int(body["id"])
            target = body.get("playlist_id")
            playlist_id = None if target is None else int(target)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            return web.json_response(
                {"error": 'expected {"kind": ..., "id": <int>, "action": ...}'}, status=400
            )
        try:
            return web.json_response(
                await self._library.act(kind, item_id, action, playlist_id)
            )
        except NotFound as exc:
            return web.json_response({"error": f"{exc} not found"}, status=404)
        except NoPlayer as exc:
            return web.json_response({"error": str(exc)}, status=409)
        except LibraryUnavailable as exc:
            return web.json_response({"error": f"LMS unreachable: {exc}"}, status=502)

    async def _handle_radio(self, request: web.Request) -> web.Response:
        """ADR-0038 §5: the panel browses by handle, never by command. No
        handle is the root, `["radios","menu:radio"]`."""
        if self._radio is None:
            return web.json_response({"error": "radio is not wired up"}, status=503)
        try:
            return web.json_response(await self._radio.browse(request.query.get("at")))
        except UnknownHandle as exc:
            return web.json_response({"error": f"unknown handle: {exc}"}, status=404)
        except RadioUnavailable as exc:
            return web.json_response({"error": f"LMS unreachable: {exc}"}, status=502)

    async def _handle_radio_play(self, request: web.Request) -> web.Response:
        """`{"handle": ..., "action": "play"|"add"}` - and only a handle
        this core issued for a station does anything (ADR-0038 §5)."""
        if self._radio is None:
            return web.json_response({"error": "radio is not wired up"}, status=503)
        try:
            body = await request.json()
            handle = str(body["handle"])
            action = str(body.get("action", "play"))
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            return web.json_response({"error": 'expected {"handle": ..., "action": ...}'}, status=400)
        if action not in ("play", "add"):
            return web.json_response({"error": f"unknown action {action}"}, status=404)
        try:
            return web.json_response(await self._radio.play(handle, action))
        except UnknownHandle as exc:
            return web.json_response({"error": f"unknown handle: {exc}"}, status=404)
        except RadioUnavailable as exc:
            return web.json_response({"error": f"LMS unreachable: {exc}"}, status=502)

    async def _handle_artist_photos(self, request: web.Request) -> web.Response:
        """`?ids=1,2,3[&size=200]` -> `{"<id>": url|null}`.

        LMS's own plugin, when the server has it (ADR-0040 §1). Asked for the
        artists the panel is about to draw rather than for the library: 40
        took 212 ms against George's server, 917 would be neither necessary
        nor kind (Finding 035).
        """
        if self._artistinfo is None:
            return web.json_response({"error": "artist info is not wired up"}, status=503)
        raw = request.query.get("ids", "")
        try:
            ids = [int(part) for part in raw.split(",") if part.strip()][:PHOTO_BATCH]
            size = int(request.query.get("size", PHOTO_THUMB))
        except ValueError:
            return web.json_response({"error": "ids must be integers"}, status=400)
        if not ids:
            return web.json_response({})
        if size not in (PHOTO_THUMB, PHOTO_LARGE):
            return web.json_response({"error": f"unknown size {size}"}, status=400)
        photos = await self._artistinfo.photos(ids, size)
        return web.json_response({str(k): v for k, v in photos.items()})

    async def _handle_enrichment(self, request: web.Request) -> web.Response:
        """What is known about what is playing, beyond what the renderer said
        (ADR-0012, ADR-0040).

        **A route rather than part of `/state`.** Enrichment is wanted only
        while a tab is open, it takes seconds, and now playing must render
        without it. Putting it in the state payload would also push a new
        payload at every panel on every lookup, on a panel that already drops
        frames while music plays (Finding 034).
        """
        if self._enrichment is None:
            return web.json_response({"error": "enrichment is not wired up"}, status=503)
        state = self._store.state
        key = TrackKey.of(state.metadata)
        if key.is_empty():
            return web.json_response({"track": None, "enrichment": Enrichment().to_json()})
        found = await self._enrichment.for_track(key, renderer=state.active)
        return web.json_response({
            # The panel checks this before drawing: by the time a lookup
            # returns, the track may have changed.
            "track": {"artist": key.artist, "title": key.title},
            "enrichment": found.to_json(),
        })

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
        app.router.add_get("/radio", self._handle_radio)
        app.router.add_post("/radio/play", self._handle_radio_play)
        app.router.add_get("/library/artist-photos", self._handle_artist_photos)
        app.router.add_get("/enrichment", self._handle_enrichment)
        app.router.add_post("/library/action", self._handle_library_action)
        app.router.add_get("/library/{what}", self._handle_library)
        app.router.add_get("/library/{what}/{id}", self._handle_library)
        app.router.add_get("/library/{what}/{id}/{sub}", self._handle_library)
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
        # Never cached. Everything it references is content-hashed, so the
        # assets can be; this file is the only thing that names them, and a
        # cached copy pins the panel to a build that no longer exists on
        # disk - which is exactly what happened on 2026-09-18: the kiosk
        # restarted onto the previous bundle and 404'd the assets it asked
        # for, so a deployed change simply was not there.
        return web.FileResponse(
            self._ui_dir / "index.html", headers={"Cache-Control": "no-store"}
        )

    async def run(self) -> None:
        runner = web.AppRunner(self.make_app())
        await runner.setup()
        site = web.TCPSite(runner, self._host, self._port)
        await site.start()
        logger.info("wsserver: listening on ws://%s:%d/state", self._host, self._port)
        await asyncio.Event().wait()
