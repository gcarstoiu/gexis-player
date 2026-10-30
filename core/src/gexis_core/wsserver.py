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
import concurrent.futures
import datetime
import hmac
import json
import logging
import os
import random
import subprocess
import tarfile
import threading
import time
import uuid
import zlib
from collections.abc import Callable
from urllib.parse import quote, unquote
from pathlib import Path

import aiohttp
from aiohttp import web
from dbus_next import BusType
from dbus_next.aio import MessageBus

from gexis_core import memo, own_wallpapers, panel_token, screen_apply, settling, updates
from gexis_core.players import Players, own_id, status_line
from gexis_core.group import GroupError
from gexis_core.wallpapers import SEARCH as PIXABAY_SEARCH
from gexis_core import backups, bluetooth_devices, skin_packs, device_name, discovery, hardware_report, lyrion_folders, lyrion_stage, music_floor, lyrion_scan, lyrion_shares, lyrion_usb, problem_report, skin_previews, skins, wifi
from gexis_core.adapters.base import TRANSPORT_COMMANDS
from gexis_core.artistinfo import PHOTO_BACKGROUND, PHOTO_LARGE, PHOTO_THUMB
from gexis_core.artwork_sweep import ARTIST_NAMESPACE, remembered

#: How many artists the idle screen draws from, and how many of those it
#: asks the photo plugin about at once (ADR-0047 §1).
ARTIST_POOL = 1000
ARTIST_BATCH = 12
#: How many of them fanart is asked about before falling back to LMS. Each
#: unknown name costs a MusicBrainz resolution at one a second, so this is
#: the number that decides how long a refresh can take: three, measured at
#: 9 of 12 of George's artists resolving at all.
ARTIST_FANART_TRIES = 3
from dataclasses import replace

from gexis_core.enrichment import ARTWORK_PROVIDERS, Enrichment, TrackKey, fold
from gexis_core.library import LibraryUnavailable, NoPlayer, NotFound
from gexis_core.menus import MenusUnavailable
from gexis_core.radio import RadioUnavailable, UnknownHandle
from gexis_core.model import PlaybackState
from gexis_core.settings_registry import (
    InvalidValue,
    Locked,
    NotSettable,
    NotWired,
    UnknownSetting,
)
from gexis_core.state import StateStore

#: The most artists one request may ask photos for. A screen of
#: cards is about 40; this is a bound on what a caller can make the
#: daemon do in one go, not a page size.
PHOTO_BATCH = 80

#: How many Popular rows the artist page draws (the design's five).
POPULAR_ROWS = 5

logger = logging.getLogger("gexis_core.wsserver")

#: ADR-0102 (a test): the web-app manifest and its icons, at the site root
#: where browsers look for them, with the types they expect.
#: ADR-0152: the API's description and Swagger UI's files, shipped with the core.
API_DIR = Path(__file__).with_name("api")
API_ASSETS = {
    "swagger-ui-bundle.js": "text/javascript",
    "swagger-ui.css": "text/css",
    "start.js": "text/javascript",
    "favicon-32x32.png": "image/png",
}
APP_FILES = {
    "manifest.webmanifest": "application/manifest+json",
    "app-icon.svg": "image/svg+xml",
    "app-icon-192.png": "image/png",
    "app-icon-512.png": "image/png",
    "apple-touch-icon.png": "image/png",
}

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8090


def _screen_size(request: web.Request) -> tuple[int, int] | None:
    """The asking panel's size, when it says it and it is a screen's."""
    try:
        w, h = int(request.query.get("w", "")), int(request.query.get("h", ""))
    except ValueError:
        return None
    return (w, h) if 100 <= w <= 8000 and 100 <= h <= 8000 else None


def _lowest_priority() -> None:
    """The placement thread runs at nice 19: it is never what a person waits
    for, and the player has music to play (ADR-0120)."""
    try:
        os.setpriority(os.PRIO_PROCESS, threading.get_native_id(), 19)
    except (AttributeError, OSError):
        pass


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
        standby=None,
        dashboard=None,
        dashboard_page=None,
        panel_input=None,
        equaliser=None,
        library=None,
        artistinfo=None,
        notes=None,
        enrichment=None,
        radio=None,
        menus=None,
        pairing_answer=None,
        restore=None,
        restart_device=None,
        placer=None,
        lyrion_shares=None,
        lyrion_usb=None,
        lyrion_shares_changed=None,
        own_server=None,
        plugins=(),
        splash=None,
        setup=None,
        setup_flow=None,
        cable=None,
        wifi_address=None,
        screen_seen=None,
        park=None,
        screen_answer=None,
        screen_new_answer=None,
        settling_done=None,
        settling_hide=None,
        on_painted=None,
        upload_plugin=None,
        uninstall_plugin=None,
        weather=None,
        wallpapers=None,
        own=None,
        skins_at: Callable[[], tuple[Path, str] | None] | None = None,
        ui_dir: Path | None = None,
        lyrion_known: "discovery.Known | None" = None,
        multiroom=None,
        plugin_artwork=None,
        panel_token: str | None = None,
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
        #: The Lyrion servers the core keeps (discovery.Known); without it,
        #: each ask searches.
        self._lyrion_found = lyrion_known.current if lyrion_known is not None else (lambda: discovery.find_servers())
        self._store = store
        #: ADR-0170: this boot's token the panel's page sends (`panel_token`).
        self._panel_token = panel_token
        #: ADR-0059's sweep leaves fanart URLs here. Not `_store`,
        #: which is the *state* store - two different things that
        #: would otherwise share a name in this file.
        self._notes = notes
        self._host = host
        self._port = port
        self._activate = activate
        self._transport = transport
        self._set_volume = set_volume
        self._set_mute = set_mute
        self._idle_page = idle_page
        self._settings = settings
        self._peppy = peppy
        #: ADR-0135: the screen's standby, which a touch and the phone wake.
        self._standby = standby
        #: ADR-0156: the Home Assistant dashboard, and the check of its address.
        self._dashboard = dashboard
        self._dashboard_page = dashboard_page
        #: ADR-0157: real taps and typing on the panel, over a framed page.
        self._panel_input = panel_input
        #: ADR-0162: the equaliser (`eq_control.EqualiserControl`).
        self._equaliser = equaliser
        #: ADR-0166: multiroom (`multiroom.Multiroom`).
        self._multiroom = multiroom
        #: ADR-0136: the other players on the network, for the phone's switcher.
        #: This core, as the others see it in its status: a player whose mDNS
        #: name was changed by a conflict (`guestpi-2.local`, 2026-10-12) is
        #: not its hostname, and listed itself as another player.
        self._instance = uuid.uuid4().hex
        self._players = Players(lambda: device_name.hostname(), own_instance=self._instance)
        self._library = library
        self._artistinfo = artistinfo
        self._enrichment = enrichment
        self._radio = radio
        #: ADR-0118: Lyrion's own menus, behind Extended navigation.
        self._menus = menus
        self._pairing_answer = pairing_answer
        #: **ADR-0086.** The installed manifests, so `/plugins/{id}/mark` can
        #: find a file. Held by id rather than searched per request: the set is
        #: fixed for the process and a request must not walk a directory a
        #: URL named.
        self._plugins = {p.id: p for p in plugins}
        #: ADR-0167 T9: the covers plugins handed over as bytes.
        self._plugin_artwork = plugin_artwork
        #: **ADR-0083.** Called after an archive has been written back, to
        #: reboot. Injected rather than imported so the route stays a route:
        #: the daemon owns what "restart the device" means, and a test can
        #: watch it without one.
        self._restore = restore
        #: The updater's backups under way, held so none is collected half-run.
        self._backup_tasks: set[asyncio.Task] = set()
        #: One upload at a time: each is up to a gigabyte on a small card.
        self._uploading = False
        #: **A row that takes effect at a restart, restarts** (ADR-0048,
        #: amended 2026-10-05): saving the device name from Settings reboots,
        #: after the answer. Here, in the route, and not in the row's own
        #: callback - first-time setup writes the same row and must not
        #: reboot halfway through.
        self._restart_device = restart_device
        #: **ADR-0120: where each background sits, by what it shows.** None
        #: places every picture as before, 35 % from the top. Asked on one
        #: low-priority thread, once per picture and screen size.
        self._placer = placer
        self._placements: dict[tuple, dict | None] = {}
        self._placing = None
        #: The visualiser's restart under way, if one is (`_peppy_again`).
        self._peppy_restarting: asyncio.Future | None = None
        #: ADR-0115: the Lyrion server's network shares.
        self._lyrion_shares = lyrion_shares
        self._lyrion_shares_changed = lyrion_shares_changed
        #: ADR-0115 decision 23: the folders Lyrion reads from USB drives.
        self._lyrion_usb = lyrion_usb
        #: The servers the last share scan found, and when (`SHARE_SERVERS_S`).
        self._share_servers: tuple[float, list] | None = None
        #: ADR-0115 decision 2: this device's own Lyrion server, offered among
        #: the servers while it is on - never chosen for the user.
        self._own_server = own_server
        self._splash = splash
        #: ADR-0104: the setup network's status, for the panel and the phone.
        self._setup = setup
        self._setup_flow = setup_flow
        #: ADR-0123: the cable's address (gexis_core.wired.Cable).
        self._cable = cable
        #: ADR-0123 decision 2: the connected Wi-Fi network's address, the
        #: same mechanism on the Wi-Fi port.
        self._wifi_address = wifi_address
        #: ADR-0109: `() -> screen_detect.Seen`, what the attached screen
        #: reports, for setup's Screen step. Injected so a test needs no sysfs.
        self._screen_seen = screen_seen
        #: George, 2026-09-29: "Why don't we disconnect all renderers upon
        #: reboot? It's a fresh start." Called by gexis-park.service as the
        #: device shuts down.
        self._park = park
        #: ADR-0109 decision 5: *Keep this screen?* - `keep` or `revert`,
        #: from the panel only.
        self._screen_answer = screen_answer
        self._screen_new_answer = screen_new_answer
        self._settling_done = settling_done
        self._settling_hide = settling_hide
        #: The panel's first frame starts that question's countdown.
        self._on_painted = on_painted
        #: ADR-0106: a package from a phone or computer, and taking one away.
        self._upload_plugin = upload_plugin
        self._uninstall_plugin = uninstall_plugin
        self._weather = weather
        self._wallpapers = wallpapers
        #: ADR-0133: the player's own pictures, for Gexis wallpapers and Space
        #: pictures - and for artist pictures while there is no library.
        self._own = own if own is not None else own_wallpapers.OwnWallpapers()
        #: Where the skin packs live (ADR-0050). Read per request rather
        #: than at start: a pack could be added under a running daemon, and
        #: parsing 99 sections costs less than the request that asked.
        #: ADR-0111: where the skins are now (root, resolution), asked each
        #: time - a pack arrives or goes while the core runs.
        self._skins_at = skins_at
        self._skins_memo: tuple | None = None
        #: What the idle screen is showing, so the next change is a change.
        #: One value for three sources, because only one of them is on
        #: screen at a time: a file name, a Pixabay id, or an artist.
        #: Each screen's last picture (ADR-0133 amended 2026-10-11, second):
        #: the home and the idle screen pick theirs apart.
        self._last_background: dict[str, str | None] = {"idle": None, "home": None}
        self._ui_dir = ui_dir
        self._clients: set[web.WebSocketResponse] = set()
        store.subscribe(self._broadcast)
        #: ADR-0121: the touchpad's own socket, the panel's (loopback) and the
        #: phones' apart. `/state` stays publish-only (ADR-0028).
        self._pad_panels: set[web.WebSocketResponse] = set()
        self._pad_phones: set[web.WebSocketResponse] = set()

    @property
    def players(self) -> Players:
        """ADR-0136's other players, which a group's members are found by."""
        return self._players

    @property
    def multiroom(self):
        return self._multiroom

    @multiroom.setter
    def multiroom(self, value) -> None:
        self._multiroom = value

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

    #: What each side may say on the touchpad's socket (ADR-0121 §5). Anything
    #: else is dropped: the core relays these, it does not interpret them.
    PAD_FROM_PHONE = frozenset({"move", "tap", "text", "key", "scroll", "zoom"})
    #: `ring`: the D-pad's ring is on a text field (ADR-0164 C5); `untyped`:
    #: a character Home Assistant's page could not be given (ADR-0157).
    PAD_FROM_PANEL = frozenset({"over", "focus", "ring", "untyped"})
    PAD_MAX = 2048

    async def _handle_touchpad(self, request: web.Request) -> web.WebSocketResponse:
        """**The phone as the panel's touchpad and keyboard** (ADR-0121).

        A phone's moves, taps, typing, scrolling and zooming go to the panel; the panel's "the
        pointer is over a text field" and "a text field has focus" go to the
        phones. Relayed, never turned into a command; dropped while the
        *Phone touchpad* row is off. Its own socket rather than `/state`,
        which stays publish-only (ADR-0028)."""
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        panel = self._from_panel(request)
        mine, theirs, allowed = ((self._pad_panels, self._pad_phones, self.PAD_FROM_PANEL) if panel
                                 else (self._pad_phones, self._pad_panels, self.PAD_FROM_PHONE))
        mine.add(ws)
        try:
            async for msg in ws:
                if msg.type != aiohttp.WSMsgType.TEXT or len(msg.data) > self.PAD_MAX:
                    continue
                try:
                    kind = json.loads(msg.data).get("t")
                except (ValueError, AttributeError):
                    continue
                if kind == "ping":
                    # **Answered to the sender alone** (George, 2026-10-14: the
                    # touchpad "loses connection when inactive"): a phone's
                    # socket can die with no close it ever hears, and only an
                    # answer that stops coming tells it so.
                    asyncio.create_task(self._send(ws, '{"t":"pong"}'))
                    continue
                if not self._touchpad_on():
                    continue
                if kind not in allowed:
                    continue
                for other in list(theirs):
                    asyncio.create_task(self._send(other, msg.data))
        finally:
            mine.discard(ws)
            # A phone gone - its sheet closed, its screen locked, its Wi-Fi
            # lost - is said to the panels, which zoom back out (ADR-0121 §2).
            if not panel:
                left = json.dumps({"t": "gone", "phones": len(self._pad_phones)})
                for other in list(self._pad_panels):
                    asyncio.create_task(self._send(other, left))
        return ws

    def _from_panel(self, request: web.Request) -> bool:
        """The panel arrives on loopback, a phone from the LAN (ADR-0035 §6) -
        and, since a plugin calls from loopback too, with this boot's token
        (ADR-0170): a header, or `?panel=` on a socket, which sends none. A
        server built without a token (the tests, a development run) goes by
        loopback alone, as before."""
        if request.remote not in ("127.0.0.1", "::1"):
            return False
        if self._panel_token is None:
            return True
        sent = request.headers.get(panel_token.HEADER) or request.query.get(panel_token.QUERY) or ""
        return hmac.compare_digest(sent.encode(), self._panel_token.encode())

    def _touchpad_on(self) -> bool:
        try:
            return self._settings is None or self._settings.value("phone_touchpad") is not False
        except Exception:  # noqa: BLE001 - a registry without the row keeps it on
            return True

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
        # A source with no capabilities declared declares nothing (found
        # writing ADR-0152's description: indexing it was a plain 500).
        caps = state.capabilities.get(state.active)
        if caps is None or command not in caps.controls:
            return web.json_response(
                {"error": f"{state.active} does not declare {command}"}, status=409
            )
        if command not in state.controls["available"]:
            return web.json_response(
                {"error": f"{command} cannot work on {state.active} right now"}, status=409
            )
        argument = None
        if command == "seek":
            try:
                body = await request.json()
            except ValueError:
                body = None
            position = body.get("position") if isinstance(body, dict) else None
            if isinstance(position, bool) or not isinstance(position, (int, float)) or position < 0:
                return web.json_response({"error": 'body must be {"position": <seconds, 0 or more>}'}, status=400)
            # Past the end is the end: a drag released beyond the bar.
            argument = float(min(position, state.metadata.duration or position))
        elif command in ("shuffle", "repeat"):
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
        state = self._store.state
        if state.fixed_output and state.fixed_mute is None:
            # ADR-0165 §2: Fixed on an output with no control of its own.
            return web.json_response(
                {"error": "this output has no volume control of its own to mute"}, status=409)
        if not await self._set_mute(muted):
            return web.json_response({"error": "volume level not known yet"}, status=409)
        return web.json_response({"muted": muted})

    async def _handle_idle(self, request: web.Request) -> web.Response:
        """`idle_page() -> {url, embeddable, reason}`, asked each time the
        idle screen opens: reachability changes while the device runs."""
        if self._idle_page is None:
            return web.json_response({"error": "idle page is not wired up"}, status=503)
        return web.json_response(await self._idle_page())

    async def _handle_idle_weather(self, request: web.Request) -> web.Response:
        """The forecast the idle screen draws (ADR-0047 §2).

        Asked by the panel rather than pushed: the idle screen is the only
        thing that wants it, it is up for hours, and `Weather` decides how
        often that becomes a call (fifteen minutes) - so a redraw costs
        nothing and a setting change is picked up on the next one.

        **A refusal is a 200 with a reason.** "That place could not be
        found" is an answer the user can act on; a 502 is a blank region and
        a journal line nobody reads.
        """
        if self._settings is None or self._weather is None:
            return web.json_response({"error": "weather is not wired up"}, status=503)
        if not self._settings.value("idle_weather"):
            return web.json_response({"error": None, "off": True})
        place = str(self._settings.value("weather_location") or "").strip()
        if not place:
            return web.json_response({"error": "No location set yet."})
        # `idle_forecast` is two layouts, not a count (design, 2026-09-22).
        # **Both need today**: the Today only layout still draws the current
        # conditions with today's high and low, so the fetch is one day
        # rather than none.
        forecast = str(self._settings.value("idle_forecast") or "3 days")
        days = 3 if forecast == "3 days" else 1
        answer = await self._weather.forecast(place, days)
        return web.json_response({**answer, "forecast": forecast})

    #: How many pictures a route call may pass over as too big for the screen
    #: before it shows one placed as before (ADR-0120 §2).
    PLACE_TRIES = 4
    #: Placements remembered, by picture and screen size.
    PLACE_MEMORY = 400

    async def _handle_idle_wallpaper(self, request: web.Request) -> web.Response:
        """The next background, placed for the panel that asks (ADR-0120).

        The panel says its size (`w`, `h`); each picture is placed once by
        what it shows - `place: {y, width}` beside its URL - and one too big
        for the screen is passed over for the next. Without a size, or
        without the models, the answer is what it always was.
        """
        if self._settings is None:
            return web.json_response({"error": "wallpapers are not wired up"}, status=503)
        # The player's own pictures need nothing wired; the downloaded and
        # the on-device ones need the wallpaper source.
        keys = self.HOME_KEYS if request.query.get("for") == "home" else self.IDLE_KEYS
        if self._wallpapers is None and self._settings.value(keys["background"]) in (
                "Wallpapers online", "Wallpapers on device"):
            return web.json_response({"error": "wallpapers are not wired up"}, status=503)
        screen = _screen_size(request)
        answer = await self._next_background(keys)
        if self._placer is None or screen is None:
            return web.json_response(answer)
        for _ in range(self.PLACE_TRIES):
            if not answer.get("url"):
                return web.json_response(answer)
            place = await self._place(answer["url"], screen)
            if place is None:
                return web.json_response(answer)
            if not place.get("skip"):
                return web.json_response({**answer, "place": place})
            logger.info("idle: %s passed over (%s)", answer["url"], place.get("how"))
            answer = await self._next_background(keys)
        return web.json_response(answer)

    async def _place(self, url: str, screen: tuple[int, int]) -> dict | None:
        """Where this picture sits on this screen, remembered; None when it
        cannot be read, so the panel places it as before."""
        key = (url, screen)
        if key in self._placements:
            return self._placements[key]
        data = await self._picture_bytes(url)
        place = None
        if data:
            loop = asyncio.get_running_loop()
            if self._placing is None:
                self._placing = concurrent.futures.ThreadPoolExecutor(
                    max_workers=1, thread_name_prefix="placement", initializer=_lowest_priority)
            try:
                found = await loop.run_in_executor(self._placing, self._placer.place, data, screen)
                place = {**found.to_json(), "skip": found.skip} if found.skip else found.to_json()
                logger.info("idle: %s placed by %s", url.rsplit("/", 1)[-1][:60], found.how)
            except Exception as exc:  # noqa: BLE001 - a picture placed as before beats none
                logger.warning("idle: could not place %s: %s", url, exc)
        if len(self._placements) >= self.PLACE_MEMORY:
            self._placements.pop(next(iter(self._placements)))
        self._placements[key] = place
        return place

    async def _picture_bytes(self, url: str) -> bytes | None:
        """The picture a background URL names: a file of ours, or the owner's
        server's (an artist picture through LMS's image proxy)."""
        if url.startswith("/idle/wallpaper/own/"):
            path = self._own.path_of(unquote(url[len("/idle/wallpaper/own/"):]))
        elif url.startswith("/idle/wallpaper/local/"):
            path = self._wallpapers.local_path(unquote(url[len("/idle/wallpaper/local/"):]))
        elif url.startswith("/idle/wallpaper/"):
            path = self._wallpapers.path_of(url[len("/idle/wallpaper/"):])
        else:
            try:
                async with aiohttp.ClientSession() as http:
                    async with http.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
                        return await response.read() if response.status == 200 else None
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                logger.info("idle: %s could not be read to place it: %s", url, exc)
                return None
        if path is None:
            return None
        try:
            return await asyncio.to_thread(path.read_bytes)
        except OSError:
            return None

    #: **Which rows each screen reads** (ADR-0133 amended 2026-10-11, second).
    #: The idle screen keeps the keys it always had; the home screen's are
    #: the waiting screen's own.
    IDLE_KEYS = {"screen": "idle", "background": "idle_background", "topics": "wallpaper_topics",
                 "styles": "wallpaper_styles", "time_of_day": "wallpaper_time_of_day",
                 "seasons": "wallpaper_seasons", "holidays": "wallpaper_holidays"}
    HOME_KEYS = {"screen": "home", "background": "waiting_background", "topics": "waiting_wallpaper_topics",
                 "styles": "waiting_wallpaper_styles", "time_of_day": "waiting_wallpaper_time_of_day",
                 "seasons": "waiting_wallpaper_seasons", "holidays": "waiting_wallpaper_holidays"}

    async def _next_background(self, keys: dict | None = None) -> dict:
        """The next background, whatever `idle_background` says it is.

        **One route for four sources**, so the panel asks for "the next
        picture" and does not carry a branch per setting: the setting is the
        daemon's to read, and three of the four answers are things only the
        daemon can reach anyway. *When* the picture changes is the panel
        counting `background_interval`; nothing here holds a timer.
        """
        keys = keys or self.IDLE_KEYS
        last = keys["screen"]
        background = self._settings.value(keys["background"]) or "Gexis wallpapers"
        if background == "Black":
            return {"off": True, "error": None}
        # ADR-0133 §2: artist pictures come from the library, which is not
        # there while the LMS client is off; the player's own show instead.
        if background == "Artist pictures" and self._settings.value("lms_enabled") is False:
            background = "Gexis wallpapers"
        if background == "Artist pictures":
            return await self._artist_picture()
        if background == "Gexis wallpapers":
            return await self._own_picture(background, keys)
        if background == "Wallpapers on device":
            # None twice until every one has been shown, and never the one
            # already on screen when there is another (ADR-0047 §2e).
            name = self._wallpapers.next_local(avoid=self._last_background[last])
            if name is None:
                return {"error": "No pictures on this device yet."}
            self._last_background[last] = name
            # **Quoted**: a name can now carry folders, spaces and anything
            # else a person types, and it travels as a URL.
            return {"url": f"/idle/wallpaper/local/{quote(name)}", "by": "", "page": "",
                    "credit": None, "error": None}
        key = str(self._settings.value("wallpaper_key") or "").strip()
        topics = await self._pixabay_topics(self._settings.value(keys["topics"]) or [], keys)
        # A bar asks for wide pictures (George, 2026-10-04).
        bar = skin_packs.family(*skin_packs.screen_size()) == "bar"
        answer = await self._wallpapers.next(key, list(topics), avoid=self._last_background[last], wide=bar)
        if answer.get("file"):
            self._last_background[last] = answer["file"]
            answer = {**answer, "url": f"/idle/wallpaper/{answer['file']}"}
        return answer

    #: ADR-0133 amended 2026-10-11: the topic that is a search, and what each
    #: holiday asks Pixabay for when it supersedes the topics.
    #:
    #: **Space is outer space, not the word** (George, 2026-10-11: "Space
    #: should be looked at as universe, galaxy, outer space"). Measured the
    #: same day on 200 editors' choice pictures: *space* alone had 112 with no
    #: astronomy tag - rooms, "copy space", the Space Needle. `|` is Pixabay's
    #: OR; single words only, since a space inside it reads as AND. This set
    #: had 6 of 144 off the subject, northern lights and rocket launches;
    #: *universe* was left out because it brought in cosmos flowers.
    PIXABAY_SEARCHES = {"Space": "galaxy|nebula|astronomy|astronaut|astrophotography", "Calm": "calm"}
    PIXABAY_HOLIDAYS = {"newyear": "new year", "christmas": "christmas", "easter": "easter"}

    async def _pixabay_topics(self, chosen: list, keys: dict | None = None) -> list[str]:
        """What `Wallpapers.next` is asked for: on a holiday, with *Holidays*
        on, that holiday alone (George: *"holidays are a toggle that
        supersede the choice of wallpaper"*); otherwise each chosen topic - a
        category as it is, Space and Calm as searches. *Seasons* is the Gexis
        wallpapers' alone (George, 2026-10-11: "Seasons only for Gexis
        wallpapers" - a season beside Science only took turns with it)."""
        keys = keys or self.IDLE_KEYS
        value = self._settings.value
        holidays_on = value(keys["holidays"]) is not False
        country, _ = await self._where() if holidays_on else (None, None)
        today = datetime.datetime.now().date()
        if holidays_on:
            holiday = own_wallpapers.holiday(today, country)
            if holiday in self.PIXABAY_HOLIDAYS:
                return [PIXABAY_SEARCH + self.PIXABAY_HOLIDAYS[holiday]]
        topics = [PIXABAY_SEARCH + self.PIXABAY_SEARCHES[t] if t in self.PIXABAY_SEARCHES else t
                  for t in (str(t) for t in chosen)]
        return topics

    async def _own_picture(self, background: str, keys: dict | None = None) -> dict:
        """**ADR-0133.** The next of the player's own pictures, chosen by the
        style, hour, season and holiday rows (`own_wallpapers.active_sets`)."""
        keys = keys or self.IDLE_KEYS
        last = keys["screen"]
        country, latitude = await self._where()
        value = self._settings.value
        styles = value(keys["styles"])
        sets = own_wallpapers.active_sets(
            datetime.datetime.now(),
            styles=list(styles) if isinstance(styles, list) else ["Calm"],
            time_of_day_on=value(keys["time_of_day"]) is not False,
            seasons_on=value(keys["seasons"]) is not False,
            holidays_on=value(keys["holidays"]) is not False,
            country=country, latitude=latitude)
        answer = self._own.next(sets, avoid=self._last_background[last])
        if answer is None:
            return {"error": "The player's own pictures are not installed."}
        self._last_background[last] = answer["file"]
        return answer

    async def _where(self) -> tuple[str | None, float | None]:
        """**The player's country and latitude** (ADR-0133 §4): the weather
        location's once one is set, the time zone's before that."""
        place = str(self._settings.value("weather_location") or "").strip()
        if place and self._weather is not None:
            try:
                found = await self._weather.geocode(place)
            except Exception:  # noqa: BLE001 - a holiday is not worth a failed picture
                found = None
            if isinstance(found, dict) and found.get("country"):
                return str(found["country"]).upper(), found.get("latitude")
        zone = self._settings.value("timezone") or own_wallpapers.system_zone()
        return own_wallpapers.from_time_zone(zone)

    async def _home_strip(self, limit: int) -> dict:
        """What the library root draws under its cards.

        One shape at a time, named by `home_strip`, `home_strip_count` long.
        **The two artist shapes are one LMS order and one count per artist**
        (Finding 044); the pictures the panel puts on them come from the
        route it already uses for the artist grid.
        """
        shape = str(self._setting_or_none("home_strip") or "New music")
        count = int(self._setting_or_none("home_strip_count") or limit or 10)
        count = max(4, min(count, 20))
        if shape == "Most played artists":
            return {"shape": shape, "artists": await self._library.played_artists("popular", count)}
        if shape == "Recently played artists":
            return {"shape": shape, "artists": await self._library.played_artists("recent", count)}
        return {"shape": "New music", "albums": await self._library.new_music(count)}

    async def _artist_picture(self) -> dict:
        """One artist picture from the library, at random.

        **fanart first, LMS second** (George, 2026-09-21: *"would be good to
        have Lms as a fallback and use fanart as their pictures are of
        better quality"*), which is the same order the artist page has had
        since 2026-09-18. fanart publishes `artistbackground` at 1920x1080
        for exactly this use; LMS's plugin returns whatever it found online,
        which is sometimes a soundtrack cover rather than a photograph.

        **Asked for in a batch and filtered here**, because neither source
        has a picture for every artist and there is no way to ask for "one
        that has one". A handful of ids costs one request (Finding 035: 40
        took 212 ms) and the whole library would be neither necessary nor
        kind.
        """
        if self._library is None or self._artistinfo is None:
            return {"error": "The library is not available."}
        try:
            listing = await self._library.artists(limit=ARTIST_POOL)
        except Exception as exc:  # the library has its own failure modes
            logger.info("idle: artists unavailable: %s", exc)
            return {"error": "The library is not available."}
        items = [a for a in listing.get("items") or [] if a.get("id")]
        if not items:
            return {"error": "No artists in the library yet."}
        # Not the artist already on screen, when there is another.
        items = [a for a in items if a.get("name") != self._last_background["idle"]] or items
        picked = random.sample(items, min(ARTIST_BATCH, len(items)))

        # **fanart is asked about one artist, not the batch.** Each name
        # costs a MusicBrainz resolution the first time (rate-limited to one
        # a second, then remembered on disk), so asking about twelve to
        # throw eleven away would spend eleven seconds to no purpose. The
        # batch stays for LMS, whose answers are cheap and concurrent.
        shuffled = list(picked)
        random.shuffle(shuffled)
        for artist in shuffled[:ARTIST_FANART_TRIES]:
            url, source = await self._fanart_background(artist.get("name") or "")
            if url:
                self._last_background["idle"] = artist.get("name") or ""
                return {"url": url, "by": artist.get("name") or "", "page": "",
                        "credit": None, "source": source, "error": None}

        photos = await self._artistinfo.photos([a["id"] for a in picked], PHOTO_BACKGROUND)
        with_photos = [(a, photos.get(a["id"])) for a in picked if photos.get(a["id"])]
        if not with_photos:
            return {"error": "No artist pictures for these artists."}
        artist, url = random.choice(with_photos)
        self._last_background["idle"] = artist.get("name") or ""
        # The credit is the artist's name rather than a licence line: both
        # sources come through the owner's own server.
        return {"url": url, "by": artist.get("name") or "", "page": "",
                "credit": None, "source": "lms", "error": None}

    async def _fanart_background(self, name: str) -> tuple[str | None, str | None]:
        """fanart.tv's wide picture for this artist - or TheAudioDB's - and
        which one answered; (None, None) when neither has one.

        None covers every way this can come to nothing - no key, no
        MusicBrainz id, no image for that id - because the caller does the
        same thing in all of them: try another artist, then fall back.
        """
        if not name or self._enrichment is None:
            return None, None
        try:
            found = await self._enrichment.for_track(
                TrackKey(artist=fold(name)), only=("fanart-bgs", "tadb-bg")
            )
        except Exception as exc:
            logger.info("idle: fanart unavailable for %r: %s", name, exc)
            return None, None
        if not found.artist_image:
            return None, None
        # Which one answered: fanart.tv's, or TheAudioDB's (ADR-0120 §3) -
        # and any of its pictures, not always the first (ADR-0047 §2e, W3).
        url = random.choice(found.artist_images or (found.artist_image,))
        return url, ("theaudiodb" if found.sources[:1] == ("tadb-bg",) else "fanart")

    async def _handle_local_wallpaper(self, request: web.Request) -> web.StreamResponse:
        """One picture somebody put on this device. Same rule as below: a
        name, never a path."""
        if self._wallpapers is None:
            return web.json_response({"error": "wallpapers are not wired up"}, status=503)
        name = request.match_info["name"]
        path = self._wallpapers.local_path(name)
        if path is None:
            return web.json_response({"error": "no such picture"}, status=404)
        return web.FileResponse(path)

    async def _handle_own_wallpaper(self, request: web.Request) -> web.StreamResponse:
        """One of the player's own pictures (ADR-0133): only a name the
        credits list holds, so nothing else on the disk is reachable."""
        path = self._own.path_of(request.match_info["name"])
        if path is None or not path.is_file():
            return web.json_response({"error": "no such picture"}, status=404)
        return web.FileResponse(path, headers={"Cache-Control": "max-age=86400"})

    async def _handle_wallpaper_file(self, request: web.Request) -> web.StreamResponse:
        """One downloaded picture. **Name only, never a path**: this route
        is reachable from the LAN (ADR-0028) and a file name that can climb
        out of its directory would serve the disk."""
        if self._wallpapers is None:
            return web.json_response({"error": "wallpapers are not wired up"}, status=503)
        name = request.match_info["name"]
        if name != Path(name).name or not name.endswith(".jpg"):
            return web.json_response({"error": "no such picture"}, status=404)
        path = self._wallpapers.path_of(name)
        if path is None:
            return web.json_response({"error": "no such picture"}, status=404)
        return web.FileResponse(path)

    def _skins(self) -> list[tuple]:
        """The installed pack's skins, read again only when the pack changes:
        reading all 287 of the 1920 x 1080 pack takes about 70 ms on a Pi 4,
        and it ran for every picture the picker showed (George, 2026-10-03:
        skimming "can get slow")."""
        at = self._skins_at() if self._skins_at else None
        if not at:
            return []
        try:
            key = (at, at[0].stat().st_mtime_ns)
        except OSError:
            key = (at, None)
        if self._skins_memo is None or self._skins_memo[0] != key:
            self._skins_memo = (key, skins.installed(at[0], resolution=at[1]))
        return self._skins_memo[1]

    async def _handle_skins(self, request: web.Request) -> web.Response:
        """Every skin the device has, with what it shows (ADR-0050).

        **What it shows, not where it lives** (ADR-0019 as amended): a skin
        declares `meter.visible` and `spectrum.visible`, and 77 of the 99 on
        this device declare neither - which means a meter.
        """
        if self._skins_at is None:
            return web.json_response({"error": "skins are not wired up"}, status=503)
        chosen = str(self._setting_or_none("skin_corpus") or skins.ALL)
        every = [skin for skin, _ in self._skins()]
        # The visualiser's own choice (`skins.in_corpus`): Fanart is a skin's
        # option, not its kind - by kind, every skin read as outside it
        # (found writing ADR-0152's description).
        chosen_names = {skin.name for skin in skins.in_corpus(every, chosen)}
        items = [
            {
                "name": skin.name,
                "kind": skin.kind,
                "in_corpus": skin.name in chosen_names,
                "preview": f"/skins/{quote(skin.name)}/preview",
            }
            for skin in every
        ]
        return web.json_response({"skins": items, "corpus": chosen})

    async def _handle_skin_preview(self, request: web.Request) -> web.StreamResponse:
        """A skin's own picture - its `screen.bgr` - and nothing generated.

        **The name in the URL never reaches the filesystem.** It is matched
        against the parsed corpus, and the file served is the one that skin
        declares, beside that skin's own `meters.txt`. A name that is a path
        is simply not a skin.
        """
        if self._skins_at is None:
            return web.json_response({"error": "skins are not wired up"}, status=503)
        wanted = request.match_info["name"]
        for skin, directory in self._skins():
            if skin.name != wanted:
                continue
            picture = skins.preview_of(skin, directory)
            if picture is None:
                return web.json_response({"error": "that skin has no picture"}, status=404)
            # ADR-0050, amended 2026-10-03: at the width the picker shows it.
            width = request.query.get("w", "")
            if width.isdigit():
                small = await skin_previews.scaled(picture, int(width))
                if small is not None:
                    return web.FileResponse(small, headers={"Cache-Control": "max-age=86400"})
            return web.FileResponse(picture)
        return web.json_response({"error": "no such skin"}, status=404)

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
            # The home strip, whichever shape `home_strip` names (9h). The
            # panel asks for the one it is about to draw rather than for all
            # three: two of them cost a browselibrary call plus one count
            # per artist, and nobody sees the other two.
            ("strip", False, None): lambda: self._home_strip(limit),
            ("new", False, None): lambda: library.new_music(),
            ("artists", False, None): lambda: library.artists(offset, limit),
            ("artists", True, "albums"): lambda: library.artist_albums(item_id),
            ("artists", True, "genres"): lambda: library.artist_genres(item_id),
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
            return web.json_response({"error": f"Lyrion unreachable: {exc}"}, status=502)

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
        # OverflowError: an id of Infinity, which `json` reads as a float.
        except (ValueError, KeyError, TypeError, OverflowError, json.JSONDecodeError):
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
            return web.json_response({"error": f"Lyrion unreachable: {exc}"}, status=502)

    # --- ADR-0118: Lyrion's own menus -------------------------------------

    def _menus_off(self) -> web.Response | None:
        """Behind Extended navigation, off by default (ADR-0118 B)."""
        if self._menus is None:
            return web.json_response({"error": "menus are not wired up"}, status=503)
        try:
            on = self._settings is not None and self._settings.value("lms_extended_nav") is True \
                and self._settings.value("lms_enabled") is not False
        except Exception:  # noqa: BLE001 - a registry without the row keeps it off
            on = False
        return None if on else web.json_response({"error": "Extended navigation is off"}, status=409)

    async def _menus_answer(self, call) -> web.Response:
        try:
            return web.json_response(await call)
        except UnknownHandle as exc:
            return web.json_response({"error": f"unknown handle: {exc}"}, status=404)
        except MenusUnavailable as exc:
            return web.json_response({"error": f"Lyrion unreachable: {exc}"}, status=502)

    async def _handle_menus(self, request: web.Request) -> web.Response:
        """The tiles Extended navigation adds to the home screen; none, and
        `on: false`, while it is off - so the panel asks once and knows."""
        if self._menus is None:
            return web.json_response({"on": False, "tiles": []})
        if self._menus_off() is not None:
            return web.json_response({"on": False, "tiles": []})
        try:
            return web.json_response({"on": True, "tiles": await self._menus.tiles()})
        except MenusUnavailable as exc:
            return web.json_response({"on": True, "tiles": [], "error": f"Lyrion unreachable: {exc}"})

    async def _handle_menus_browse(self, request: web.Request) -> web.Response:
        """`?at=<handle>&start=&count=`: one page of a list, by handle."""
        off = self._menus_off()
        if off is not None:
            return off
        try:
            start = int(request.query.get("start", 0))
            count = int(request.query.get("count", 100))
        except ValueError:
            return web.json_response({"error": "start and count are numbers"}, status=400)
        return await self._menus_answer(self._menus.browse(request.query.get("at", ""), start, count))

    async def _handle_menus_letters(self, request: web.Request) -> web.Response:
        """`?at=<handle>`: where each letter starts in that list (the rail)."""
        off = self._menus_off()
        if off is not None:
            return off
        return await self._menus_answer(self._menus.letters(request.query.get("at", "")))

    async def _handle_menus_act(self, request: web.Request) -> web.Response:
        """`{"handle", "action": "play"|"add"|"next"}` - what Lyrion itself
        offers for an item this core issued (ADR-0118 D)."""
        off = self._menus_off()
        if off is not None:
            return off
        try:
            body = await request.json()
            handle, action = str(body["handle"]), str(body.get("action", "play"))
        except (ValueError, KeyError, TypeError):
            return web.json_response({"error": 'expected {"handle": ..., "action": ...}'}, status=400)
        if action not in ("play", "add", "next"):
            return web.json_response({"error": f"unknown action {action}"}, status=404)
        return await self._menus_answer(self._menus.act(handle, action))

    async def _handle_menus_search(self, request: web.Request) -> web.Response:
        """`{"handle", "text"}`: a search item, answered (ADR-0118 E)."""
        off = self._menus_off()
        if off is not None:
            return off
        try:
            body = await request.json()
            handle, text = str(body["handle"]), str(body["text"])
        except (ValueError, KeyError, TypeError):
            return web.json_response({"error": 'expected {"handle": ..., "text": ...}'}, status=400)
        return await self._menus_answer(self._menus.search(handle, text))

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
            return web.json_response({"error": f"Lyrion unreachable: {exc}"}, status=502)

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
            return web.json_response({"error": f"Lyrion unreachable: {exc}"}, status=502)

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
        # **The sweep first, LMS for the rest** (ADR-0068). ADR-0059 settled
        # that order and this asked in the other one: every id went to the
        # LMS plugin and 68 % of the answers were then thrown away for a
        # fanart portrait already on the device. An artist the plugin has
        # not looked up costs it 500-900 ms upstream, so a batch of twenty
        # nobody had opened took 353 ms against 5 ms for one already known.
        swept = {artist_id: await self._swept_portrait(artist_id, size) for artist_id in ids}
        rest = [artist_id for artist_id, url in swept.items() if url is None]
        photos = await self._artistinfo.photos(rest, size) if rest else {}
        return web.json_response(
            {str(artist_id): swept[artist_id] or photos.get(artist_id) for artist_id in swept}
        )

    def swept_portrait_of(self, name: str | None, size: int) -> str | None:
        """**The portrait ADR-0059's sweep found for a name** (ADR-0075).

        The sweep stores by folded artist name, not by LMS id, because a
        rescan renumbers the ids (Finding 029) - and a name is something
        *every* renderer has. So this answers for a Spotify or Bluetooth
        track as readily as for the library's own grid, whenever the artist
        is one the sweep has been over.

        It goes through LMS's image proxy, so the caller gets the size it
        asked for and LMS does the fetching and the caching.
        """
        if self._library is None or not name:
            return None
        found = remembered(self._notes, ARTIST_NAMESPACE, fold(name))
        if not found or found is True:
            return None
        return f"{self._library.base}/imageproxy/{found}/image_{size}x{size}_o.jpg"

    async def _swept_portrait(self, artist_id: int, size: int) -> str | None:
        """The same, for a caller that has an LMS id rather than a name.

        The name comes from the library, which already holds it and answers
        from one map built per scan.
        """
        if self._library is None:
            return None
        try:
            name = await self._library.artist_name(artist_id)
        except Exception:
            return None
        return self.swept_portrait_of(name, size)

    async def _portrait(self, artist_id: int, lms_url, size: int):
        """**fanart's portrait if ADR-0059's sweep found one, LMS's otherwise.**

        For a single artist, where asking LMS first costs nothing because it
        is being asked anyway. The list route resolves the sweep first and
        asks LMS only for what is left (ADR-0068).
        """
        return await self._swept_portrait(artist_id, size) or lms_url

    async def _handle_artist_info(self, request: web.Request) -> web.Response:
        """`?id=<lms artist id>&name=<artist>` -> what the artist page draws
        below its discography (ADR-0038 §2, now that Phase 8 can fill it).

        **The same order as everywhere else** (ADR-0040 §1): LMS's own plugin
        answers first, from the id the library already has, and the key-free
        providers fill what it leaves. They are keyed on the *name*, since
        they know nothing about LMS ids.
        """
        if self._enrichment is None:
            return web.json_response({"error": "enrichment is not wired up"}, status=503)
        name = (request.query.get("name") or "").strip()
        try:
            artist_id = int(request.query["id"]) if request.query.get("id") else None
        except ValueError:
            return web.json_response({"error": "id is an integer"}, status=400)
        if not name:
            return web.json_response({"error": "name is required"}, status=400)

        found = Enrichment()
        if artist_id is not None and self._artistinfo is not None:
            photos = await self._artistinfo.photos([artist_id], PHOTO_LARGE)
            biography = await self._artistinfo.biography(artist_id)
            found = Enrichment(
                biography=biography,
                biography_source="Lyrion" if biography else None,
                artist_image=photos.get(artist_id),
                sources=("lms",) if (biography or photos.get(artist_id)) else (),
            )
        # **The sweep answers for fanart, so fanart is not asked** (ADR-0075).
        swept = self.swept_portrait_of(name, PHOTO_LARGE)
        rest = await self._enrichment.for_track(
            TrackKey(artist=fold(name)),
            only=("fanart", "wikipedia", "listenbrainz", "popular"),
            omit=("fanart",) if swept else (),
        )
        found = found.merged_with(rest)
        if rest.artist_image:
            # **Pictures come from fanart first** (George, 2026-09-18): it
            # has a portrait for artists LMS's plugin has nothing for. The
            # text above is still LMS's where it has any - only the picture
            # changes hands.
            found = replace(found, artist_image=rest.artist_image)
        # **And the sweep comes before fanart** (ADR-0075). It is the same
        # picture, from the same place, already on this device.
        if swept:
            found = replace(found, artist_image=swept)
        return web.json_response({
            "artist": name,
            "enrichment": found.to_json(),
            # Only what this device can actually play, in the order the
            # wider world plays them (the design's own note on Popular).
            "popular": await self._playable(artist_id, found.popular),
        })

    async def _playable(self, artist_id: int | None, popular) -> list[dict]:
        """The popular recordings this library holds, as rows the page can
        press. Matched on a folded title, because a chart and a tag rarely
        agree on capitals or punctuation."""
        if not popular or artist_id is None or self._library is None:
            return []
        try:
            tracks = await self._library.artist_tracks(artist_id)
        except Exception as exc:
            logger.info("artist-info: could not read the artist's tracks (%s)", exc)
            return []
        here = {}
        for track in tracks:
            here.setdefault(fold(track.get("title")), track)
        rows = []
        for title in popular:
            track = here.get(fold(title))
            if track and not any(r["id"] == track["id"] for r in rows):
                rows.append({"id": track["id"], "title": track["title"],
                             "duration": track.get("duration")})
            if len(rows) == POPULAR_ROWS:
                break
        return rows

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
        pending: list[str] = []
        # **The sweep's portrait, for whatever is playing** (ADR-0075). It is
        # keyed on the folded artist name, so a Spotify or Bluetooth track by
        # an artist the sweep has been over gets its picture from this device
        # rather than from a lookup - and fanart is not asked for a picture
        # we are already holding.
        swept = self.swept_portrait_of(state.metadata.artist, PHOTO_LARGE)
        omit = ("fanart",) if swept else ()
        # A cover is looked for only when the renderer sent none (2026-10-06):
        # LMS's own artwork made every LMS track spend MusicBrainz's allowance
        # on a cover nobody would draw.
        if state.metadata.artwork:
            omit += ARTWORK_PROVIDERS
        found = await self._enrichment.for_track(
            key, renderer=state.active, pending=pending, omit=omit,
        )
        if swept:
            found = replace(found, artist_image=swept)
        return web.json_response({
            # True when a provider had not finished: the panel asks again
            # rather than treating this as the final word.
            "pending": bool(pending),
            # The panel checks this before drawing: by the time a lookup
            # returns, the track may have changed.
            "track": {"artist": key.artist, "title": key.title},
            "enrichment": found.to_json(),
        })

    async def _handle_plugin_mark(self, request: web.Request) -> web.Response:
        """A source's glyph, by id (ADR-0086).

        **The id is looked up, never joined onto a path.** It arrives from a
        URL, and a manifest directory is not somewhere a request gets to point
        at - the set of plugins is fixed at startup and anything not in it is
        a 404.
        """
        plugin = self._plugins.get(request.match_info["id"])
        if plugin is None or plugin.mark is None:
            return web.json_response({"error": "no mark for that source"}, status=404)
        # Cached for a day, which is safe only because the URL the panel is
        # given carries the file's hash (`Plugin.mark_url`): a replaced mark is
        # a different URL. The query string is not read here.
        return web.FileResponse(
            plugin.mark, headers={"Cache-Control": "public, max-age=86400"}
        )

    async def _handle_plugin_artwork(self, request: web.Request) -> web.Response:
        """A cover a plugin handed over (ADR-0167 T9), by its key. Looked up
        in memory, never a path; the key names the bytes, so it is cached as
        long as a browser likes."""
        found = None
        if self._plugin_artwork is not None:
            found = self._plugin_artwork.get(request.match_info["id"], request.match_info["key"])
        if found is None:
            return web.json_response({"error": "no such cover"}, status=404)
        kind, data = found
        return web.Response(body=data, content_type=kind,
                            headers={"Cache-Control": "public, max-age=31536000, immutable"})

    async def _handle_surface(self, request: web.Request) -> web.Response:
        """ADR-0035 §6: the panel always arrives on loopback, a phone from the LAN."""
        panel = self._from_panel(request)
        return web.json_response({"surface": "panel" if panel else "remote"})

    async def _handle_touch(self, request: web.Request) -> web.Response:
        """The panel telling the daemon somebody touched it. The daemon cannot
        see touches itself: they land in whichever window has the screen.
        **The panel only** (review, 2026-10-12): a phone's request would wake a
        screen in standby and count as attention it never paid."""
        if not self._from_panel(request):
            return web.json_response({"error": "only the panel reports touches"}, status=403)
        if self._peppy is not None:
            self._peppy.on_touch()
        # ADR-0135: a touch wakes a screen in standby - measured to reach the
        # page with the output off.
        if self._standby is not None:
            self._standby.used()
            if self._standby.may_be_dark:
                await self._standby.wake("touch")
        return web.json_response({"touched": True})

    def _player_status(self) -> dict:
        """**ADR-0136: what this player says of itself** to the others, and
        to Home Assistant (ADR-0160 D5: `id`, `screen`)."""
        state = self._store.state
        return {"name": self._setting_or_none("device_name") or device_name.hostname(),
                "host": f"{device_name.hostname()}.local",
                "instance": self._instance,
                "id": own_id(),
                "screen": self._setting_or_none("headless") is not True,
                # Home Assistant offers the idle screen only where the phone
                # does: while it is switched on (ADR-0163).
                "idle_screen": self._setting_or_none("idle_enabled") is True,
                **status_line(state, state.sources),
                # ADR-0166: its group API, group, Lyrion and level.
                **(self._multiroom.status() if self._multiroom is not None else {})}

    async def watch_players(self) -> None:
        """ADR-0136: the other players kept warm, so the phone's list is ready."""
        await self._players.watch()

    async def _handle_player_status(self, request: web.Request) -> web.Response:
        return web.json_response(self._player_status())

    async def _handle_players(self, request: web.Request) -> web.Response:
        """ADR-0136: this player and the others found, each with its status;
        the phone moves its tab to the one chosen."""
        async with aiohttp.ClientSession() as session:
            others = await self._players.others(session)
        return web.json_response({"self": self._player_status(), "others": others})

    # -- ADR-0166: the group ----------------------------------------------------

    def _no_multiroom(self) -> web.Response | None:
        if self._multiroom is None:
            return web.json_response({"error": "multiroom is not wired up"}, status=503)
        return None

    async def _handle_group(self, request: web.Request) -> web.Response:
        """This player's group: the record it keeps and the view `/state`
        publishes; both null when it is in none."""
        if (refusal := self._no_multiroom()) is not None:
            return refusal
        record = self._multiroom.record
        return web.json_response({"record": record.to_json() if record else None,
                                  "view": self._multiroom.view()})

    async def _handle_group_record(self, request: web.Request) -> web.Response:
        """**Another player's change to a group** (ADR-0166 D3): taken if it
        is later than what this player has. `taken` says whether it was."""
        if (refusal := self._no_multiroom()) is not None:
            return refusal
        try:
            body = await request.json()
            record = body["record"]
        except (ValueError, KeyError, TypeError):
            return web.json_response({"error": 'body must be {"record": {...}}'}, status=400)
        try:
            taken = await self._multiroom.receive(record)
        except GroupError as exc:
            return web.json_response({"error": str(exc)}, status=400)
        return web.json_response({"taken": taken})

    async def _handle_group_change(self, request: web.Request) -> web.Response:
        """Join a player to this one's group, take one out, leave it, or undo
        it (the design's Join, Remove, Leave group, Undo group)."""
        if (refusal := self._no_multiroom()) is not None:
            return refusal
        action = request.path.rsplit("/", 1)[-1]
        player = None
        if action in ("join", "remove"):
            try:
                player = (await request.json())["player"]
            except (ValueError, KeyError, TypeError):
                player = None
            if not isinstance(player, str) or not player:
                return web.json_response({"error": 'body must be {"player": "<id>"}'}, status=400)
        try:
            if action == "join":
                record = await self._multiroom.join(player)
            elif action == "remove":
                record = await self._multiroom.remove(player)
            elif action == "leave":
                record = await self._multiroom.leave()
            else:
                record = await self._multiroom.undo()
        except GroupError as exc:
            return web.json_response({"error": str(exc)}, status=409)
        return web.json_response({"record": record.to_json() if record else None})

    async def _handle_group_enter(self, request: web.Request) -> web.Response:
        """**Join another group, as a whole** (ADR-0166 decision 11): this
        player, not grouped, asks the leader of `{"leader": "<id>"}` to add
        it. The group's view follows on `/state` once the leader has."""
        if (refusal := self._no_multiroom()) is not None:
            return refusal
        try:
            leader = (await request.json())["leader"]
        except (ValueError, KeyError, TypeError):
            leader = None
        if not isinstance(leader, str) or not leader:
            return web.json_response({"error": 'body must be {"leader": "<id>"}'}, status=400)
        try:
            await self._multiroom.enter(leader)
        except GroupError as exc:
            return web.json_response({"error": str(exc)}, status=409)
        return web.json_response({"ok": True})

    async def _handle_group_volume(self, request: web.Request) -> web.Response:
        """**The *All* slider** (ADR-0166 D6): `percent`, and the members'
        levels when the drag began as `from` (optional)."""
        if (refusal := self._no_multiroom()) is not None:
            return refusal
        try:
            body = await request.json()
            percent = float(body["percent"])
        except (ValueError, KeyError, TypeError):
            return web.json_response({"error": 'body must be {"percent": <0-100>, "from": {...}}'},
                                     status=400)
        if not 0 <= percent <= 100:
            return web.json_response({"error": "percent must be 0-100"}, status=400)
        if self._multiroom.record is None:
            return web.json_response({"error": "this player is in no group"}, status=409)
        moved = await self._multiroom.group_volume(percent, body.get("from"))
        return web.json_response({"levels": moved})

    async def _handle_group_mute(self, request: web.Request) -> web.Response:
        if (refusal := self._no_multiroom()) is not None:
            return refusal
        try:
            muted = (await request.json())["muted"]
        except (ValueError, KeyError, TypeError):
            muted = None
        if not isinstance(muted, bool):
            return web.json_response({"error": 'body must be {"muted": true|false}'}, status=400)
        if self._multiroom.record is None:
            return web.json_response({"error": "this player is in no group"}, status=409)
        await self._multiroom.group_mute(muted)
        return web.json_response({"muted": muted})

    async def _handle_group_member_volume(self, request: web.Request) -> web.Response:
        """One member's own level, from any player of the group."""
        if (refusal := self._no_multiroom()) is not None:
            return refusal
        try:
            percent = float((await request.json())["percent"])
        except (ValueError, KeyError, TypeError):
            return web.json_response({"error": 'body must be {"percent": <0-100>}'}, status=400)
        if not 0 <= percent <= 100:
            return web.json_response({"error": "percent must be 0-100"}, status=400)
        if not await self._multiroom.member_volume(request.match_info["id"], percent):
            return web.json_response({"error": "that member did not take it"}, status=502)
        return web.json_response({"percent": percent})

    async def _handle_group_member_mute(self, request: web.Request) -> web.Response:
        if (refusal := self._no_multiroom()) is not None:
            return refusal
        try:
            muted = (await request.json())["muted"]
        except (ValueError, KeyError, TypeError):
            muted = None
        if not isinstance(muted, bool):
            return web.json_response({"error": 'body must be {"muted": true|false}'}, status=400)
        if not await self._multiroom.member_mute(request.match_info["id"], muted):
            return web.json_response({"error": "that member did not take it"}, status=502)
        return web.json_response({"muted": muted})

    async def _handle_standby(self, request: web.Request) -> web.Response:
        """**ADR-0135: the screen off or on from a phone, or the Settings
        action.** `on` is standby on - the screen off."""
        action = request.match_info["action"]
        if self._standby is None:
            return web.json_response({"error": "standby is not wired up"}, status=503)
        if action == "on":
            await self._standby.sleep("asked")
        elif action == "off":
            await self._standby.wake("phone")
        else:
            return web.json_response({"error": f"unknown action {action}"}, status=404)
        return web.json_response({"standby": self._standby.off})

    async def _handle_dashboard(self, request: web.Request) -> web.Response:
        """**ADR-0156: whether the dashboard is up, and whether it can be.**
        The panel asks each time it puts the dashboard up, as it does for the
        idle page: a frame cannot say why it is blank, so the core checks the
        address and answers with the sentence to show."""
        if self._dashboard is None or self._dashboard_page is None:
            return web.json_response({"error": "the dashboard is not wired up"}, status=503)
        page = await self._dashboard_page()
        return web.json_response({"shown": self._dashboard.shown, "by": self._dashboard.by, **page})

    async def _handle_dashboard_request(self, request: web.Request) -> web.Response:
        """**ADR-0156: the dashboard up or down** - from the panel's button
        and edge tab, a phone, or Home Assistant itself. `?by=schedule` is the
        panel putting it up in place of the idle screen, which the schedule's
        end takes down again; anything else is a person's."""
        action = request.match_info["action"]
        if self._dashboard is None:
            return web.json_response({"error": "the dashboard is not wired up"}, status=503)
        by = "schedule" if request.query.get("by") == "schedule" else "asked"
        if action == "show":
            if by == "asked" and self._peppy is not None:
                self._peppy.on_touch()
            self._dashboard.show(by)
        elif action == "hide":
            self._dashboard.hide(by)
        else:
            return web.json_response({"error": f"unknown action {action}"}, status=404)
        return web.json_response({"shown": self._dashboard.shown, "by": self._dashboard.by})

    async def _handle_panel_input(self, request: web.Request) -> web.Response:
        """**ADR-0157: the phone's tap or typing, made real.** The panel asks
        when the phone's pointer is over a page from another site in a frame
        (the Home Assistant dashboard), which its own made-up events cannot
        reach. `{kind: "tap", x, y}` with `x`, `y` fractions of the screen;
        `{kind: "text", text}`; `{kind: "key", key}` - Backspace, Enter or Tab."""
        if self._panel_input is None:
            return web.json_response({"error": "panel input is not wired up"}, status=503)
        try:
            body = await request.json()
        except (ValueError, UnicodeDecodeError):
            return web.json_response({"error": "expected a JSON object"}, status=400)
        kind = body.get("kind") if isinstance(body, dict) else None
        try:
            if kind == "tap":
                x, y = float(body["x"]), float(body["y"])
                if not (0 <= x <= 1 and 0 <= y <= 1):
                    raise ValueError("x and y are fractions of the screen")
                await self._panel_input.tap(x, y)
                return web.json_response({"done": True})
            if kind == "text":
                text = body["text"]
                if not isinstance(text, str) or not text or len(text) > 500:
                    raise ValueError("text is 1 to 500 characters")
                return web.json_response({"done": await self._panel_input.type(text)})
            if kind == "key":
                done = await self._panel_input.key(str(body["key"]))
                if not done:
                    raise ValueError("key is Backspace, Enter or Tab")
                return web.json_response({"done": True})
        except (KeyError, TypeError, ValueError) as exc:
            return web.json_response({"error": str(exc) or "bad input"}, status=400)
        except OSError as exc:
            logger.warning("panel input: %s", exc)
            return web.json_response({"error": f"the panel's input could not be made: {exc}"}, status=503)
        return web.json_response({"error": "kind is tap, text or key"}, status=400)

    #: ADR-0161 D2: the D-pad's keys.
    DPAD_KEYS = ("up", "down", "left", "right", "ok", "back")

    async def _handle_panel_key(self, request: web.Request) -> web.Response:
        """**ADR-0161 D6: a D-pad press on the panel** - from Home Assistant's
        remote, or anything with the API. It becomes a key press on the
        core's virtual keyboard (D1), which the page answers as a keyboard's.
        Attention first, as `/panel/go` is. While the screen is in standby or
        the visualiser is up, a press only wakes the panel, as a first touch
        does (D4); Back over the dashboard takes the dashboard down (D2),
        since the keys would otherwise go to Home Assistant's own page."""
        try:
            body = await request.json()
        except (ValueError, UnicodeDecodeError):
            return web.json_response({"error": "expected a JSON object"}, status=400)
        key = body.get("key") if isinstance(body, dict) else None
        if key not in self.DPAD_KEYS:
            return web.json_response({"error": "key is up, down, left, right, ok or back"}, status=400)
        if self._setting_or_none("headless") is True:
            return web.json_response({"error": "this player has no screen"}, status=409)
        if self._panel_input is None:
            return web.json_response({"error": "panel input is not wired up"}, status=503)
        woke = False
        if self._standby is not None:
            self._standby.used()
            if self._standby.may_be_dark:
                # Only a screen known to be off swallows the press: after a
                # restart its state is unknown, and a lit one must not lose it.
                woke = self._standby.off
                await self._standby.wake("key")
        if self._peppy is not None:
            woke = woke or self._peppy.up
            self._peppy.on_touch()
        if woke:
            return web.json_response({"key": key, "woke": True})
        if key == "back" and self._dashboard is not None and self._dashboard.shown:
            self._dashboard.hide("asked")
            return web.json_response({"key": key, "dashboard": "hidden"})
        try:
            await self._panel_input.dpad(key)
        except OSError as exc:
            logger.warning("panel key: %s", exc)
            return web.json_response({"error": f"the key could not be pressed: {exc}"}, status=503)
        return web.json_response({"key": key})

    # ---- ADR-0162: the equaliser -------------------------------------------------

    async def _equaliser_call(self, call) -> web.Response:
        """One of the equaliser's operations, answered with what it gives back;
        a refusal is a 400 with the sentence for the person."""
        from gexis_core.equaliser import EqualiserError
        if self._equaliser is None:
            return web.json_response({"error": "the equaliser is not wired up"}, status=503)
        try:
            return web.json_response(await call())
        except EqualiserError as exc:
            return web.json_response({"error": str(exc)}, status=400)

    async def _json_body(self, request: web.Request):
        try:
            body = await request.json()
        except (ValueError, UnicodeDecodeError):
            return None
        return body if isinstance(body, dict) else None

    async def _handle_equaliser(self, request: web.Request) -> web.Response:
        """ADR-0162 D9: the equaliser for the output in use."""
        if self._equaliser is None:
            return web.json_response({"error": "the equaliser is not wired up"}, status=503)
        snapshot = self._equaliser.snapshot()
        if snapshot is None:
            return web.json_response({"error": "there is no output"}, status=409)
        return web.json_response(snapshot)

    async def _handle_equaliser_set(self, request: web.Request) -> web.Response:
        """On or off, a setting chosen, the bands or one band, for the output
        in use. A band or a setting is heard at once; on or off reopens the
        output (a moment of silence)."""
        body = await self._json_body(request)
        if body is None:
            return web.json_response({"error": "expected a JSON object"}, status=400)
        return await self._equaliser_call(lambda: self._equaliser.update(body))

    async def _handle_equaliser_save(self, request: web.Request) -> web.Response:
        """The bands as set, saved as one of the owner's (*Save as...*)."""
        body = await self._json_body(request)
        if body is None or "name" not in body:
            return web.json_response({"error": 'body must be {"name": ...}'}, status=400)
        return await self._equaliser_call(lambda: self._equaliser.save_as(body["name"]))

    async def _handle_equaliser_rename(self, request: web.Request) -> web.Response:
        body = await self._json_body(request)
        if body is None or "name" not in body:
            return web.json_response({"error": 'body must be {"name": ...}'}, status=400)
        key = request.match_info["key"]
        return await self._equaliser_call(lambda: self._equaliser.rename(key, body["name"]))

    async def _handle_equaliser_delete(self, request: web.Request) -> web.Response:
        key = request.match_info["key"]
        return await self._equaliser_call(lambda: self._equaliser.delete(key))

    async def _handle_idle_request(self, request: web.Request) -> web.Response:
        """**ADR-0101: the phone's idle-screen toggle.** Attention first, as a
        touch on the panel is (George: "Timers would restart from that
        point") - which also takes the visualiser down, because the panel has
        one screen. Then the request goes to the panel in the state it
        already listens to."""
        action = request.match_info["action"]
        if action not in ("show", "hide"):
            return web.json_response({"error": f"unknown action {action}"}, status=404)
        if self._peppy is not None:
            self._peppy.on_touch()
        self._store.request_idle(action == "show")
        return web.json_response({"idle": action})

    #: ADR-0101 as amended: where a phone may send the panel.
    VIEWS = ("home", "now", "lyrics", "track", "minimise")

    async def _handle_view_request(self, request: web.Request) -> web.Response:
        """**ADR-0101 as amended 2026-10-05: Home, Now playing and Lyrics from
        the phone's sheet.** Attention first, as the idle toggle is; then the
        ask goes to the panel in the state it listens to. Now Playing exists
        only while a source is active, so the three that lead there are
        refused without one."""
        to = request.match_info["to"]
        if to not in self.VIEWS:
            return web.json_response({"error": f"unknown view {to}"}, status=404)
        if to != "home" and self._store.state.active is None:
            return web.json_response({"error": "nothing is playing"}, status=409)
        if self._peppy is not None:
            self._peppy.on_touch()
        self._store.request_view(to)
        return web.json_response({"view": to})

    async def _handle_wifi_details(self, request: web.Request) -> web.Response:
        """ADR-0123: the connected Wi-Fi network's signal, speed, band,
        channel and address - no rescan, so the open sheet can ask every
        few seconds. `{"connected": false}` when there is none."""
        details = await wifi.connected_details()
        if not details:
            return web.json_response({"connected": False})
        return web.json_response({"connected": True, **details})

    #: One report at a time: building one reads and rewrites the whole
    #: journal, half a minute on a Pi 4.
    _report_lock = asyncio.Lock()

    def _address(self, request: web.Request):
        """The cable's or the Wi-Fi's address, by the route."""
        # `/network/wifi` itself is the connected network's details (0.9.3).
        return self._wifi_address if request.path.startswith("/network/wifi/") else self._cable

    async def _handle_cable(self, request: web.Request) -> web.Response:
        """ADR-0123: what the Cable sheet - or the connected Wi-Fi network's
        details - show."""
        port = self._address(request)
        if port is None:
            return web.json_response({"error": "not wired up"}, status=503)
        from gexis_core import wired

        state = await port.status()
        return web.json_response({**state, "summary": wired.summary(state)})

    async def _handle_cable_change(self, request: web.Request) -> web.Response:
        """ADR-0123: an address, Automatic or Manual, applied and waiting for
        *Keep* - or a sentence saying why not."""
        port = self._address(request)
        if port is None:
            return web.json_response({"error": "not wired up"}, status=503)
        other = self._cable if port is self._wifi_address else self._wifi_address
        # Applying counts as waiting: `pending` is set only once the address
        # has come, up to 20 s after the change began.
        if other is not None and (other.pending is not None or other.changing):
            return web.json_response({"error": "Another address change is waiting to be kept. Keep it, or wait for "
                                               "it to go back."}, status=409)
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError('expected {"method": ..., "address": ...}')
            told = await port.change(body.get("method"), body.get("address") or "",
                                     body.get("gateway") or "", body.get("dns") or [])
        except ValueError as exc:
            return web.json_response({"error": str(exc)}, status=400)
        return web.json_response(told)

    async def _handle_cable_keep(self, request: web.Request) -> web.Response:
        """ADR-0123: *Keep* - counted from the new address, which proves it
        works, or from the panel. Whichever port is waiting."""
        ports = [p for p in (self._cable, self._wifi_address) if p is not None]
        if not ports:
            return web.json_response({"error": "not wired up"}, status=503)
        sockname = request.transport.get_extra_info("sockname") if request.transport else None
        arrived_at = sockname[0] if sockname else None
        loopback = self._from_panel(request)
        waiting = [p for p in ports if p.pending is not None]
        if not waiting:
            return web.json_response({"error": "Nothing is waiting to be kept."}, status=409)
        if any(p.keep(arrived_at, loopback) for p in waiting):
            return web.json_response({"kept": True})
        address = waiting[0].pending.address
        return web.json_response({"error": f"Open the player at http://{address}:8090 and keep it there - "
                                           "that is what shows the new address works."}, status=409)

    async def _handle_backup_download(self, request: web.Request) -> web.StreamResponse:
        """**A backup, saved on a phone or computer** (ADR-0083 as amended
        2026-10-08; George: *"the option in system backup to also download
        one of the backups locally"*) - ready for a newly flashed card's
        setup (ADR-0131). What the Backups share already offers the same
        network, by the same names."""
        # **Sent from the file opened without following a link** (Finding
        # 125 #2, 2026-10-14): `FileResponse` opened the name again, and a link
        # `pi` left in the share under a backup's name sent root's
        # `/etc/shadow` to whoever asked.
        name = request.match_info["name"]
        try:
            source = await asyncio.to_thread(backups.open_archive, name)
        except ValueError:
            return web.json_response({"error": "not a backup"}, status=400)
        except FileNotFoundError:
            return web.json_response({"error": "That backup is not on the player any more."}, status=404)
        with source:
            response = web.StreamResponse(headers={
                "Content-Disposition": f'attachment; filename="{name}"',
                # A plain file, not `application/gzip`: browsers added `.gz`
                # to a name already ending `.tgz` (2026-10-16), and Restore
                # did not list what was copied back.
                "Content-Type": "application/octet-stream",
                "Cache-Control": "no-store",
            })
            response.content_length = os.fstat(source.fileno()).st_size
            await response.prepare(request)
            while chunk := await asyncio.to_thread(source.read, 1 << 16):
                await response.write(chunk)
            await response.write_eof()
        return response

    async def _handle_backup_upload(self, request: web.Request) -> web.Response:
        """**A backup added from a phone or computer** (ADR-0083 as amended
        2026-10-17; George: *"It should stay in the restore list"*). The body
        is the file, streamed into the share under setup's cap, checked as
        setup checks one, and added to the list; nothing is restored.
        `?name=` is the file's name."""
        from gexis_core import settings_migrations, setup_flow

        if self._uploading:
            return web.json_response({"ok": False, "error": "Another backup is being added. Wait for it to finish."}, status=409)
        self._uploading = True
        part = None
        size = 0
        try:
            fd, part = await asyncio.to_thread(backups.upload_part)
            try:
                with os.fdopen(fd, "wb") as out:
                    async for chunk in request.content.iter_chunked(1 << 16):
                        size += len(chunk)
                        if size > setup_flow.BACKUP_MAX_BYTES:
                            raise OverflowError
                        await asyncio.to_thread(out.write, chunk)
            except OverflowError:
                part.unlink(missing_ok=True)
                return web.json_response({"ok": False, "error": "That file is larger than any gexis backup."}, status=413)
            except (OSError, ConnectionError) as exc:
                part.unlink(missing_ok=True)
                logger.warning("backup upload failed after %d bytes: %s", size, exc)
                # A full card is the likely OSError: said, not a stack trace.
                return web.json_response({"ok": False, "error": "The file did not arrive whole. Try again."}, status=400)
            try:
                added = await asyncio.to_thread(backups.add_upload, part, request.query.get("name"),
                                                len(settings_migrations.MIGRATIONS))
            except backups.Refused as exc:
                return web.json_response({"ok": False, "error": str(exc)}, status=400)
            except OSError as exc:
                logger.warning("backup upload not added: %s", exc)
                return web.json_response({"ok": False, "error": "The player could not keep that file. Is its card full?"}, status=500)
            self._store.bump_settings_revision()
            return web.json_response({"ok": True, "error": None, **added})
        finally:
            self._uploading = False

    async def _handle_report(self, request: web.Request) -> web.Response:
        """ADR-0125: the problem report, downloaded. The body may carry the
        user's own line, `{"note": "..."}`. Every value is read here, on the
        loop - the settings store is SQLite, bound to this thread - and the
        journal is read and scrubbed in a worker."""
        if self._settings is None:
            return web.json_response({"error": "settings are not wired up"}, status=503)
        try:
            body = await request.json() if request.can_read_body else {}
        except ValueError:
            body = {}
        note = str((body if isinstance(body, dict) else {}).get("note") or "")[:4000]
        rows = self._settings.all_rows()
        values = {}
        for row in rows:
            try:
                values[row["key"]] = self._settings.value(row["key"])
            except Exception:  # noqa: BLE001 - a row that cannot be read is left out
                values[row["key"]] = None
        shares = self._lyrion_shares.all() if self._lyrion_shares is not None else []
        state = self._store.state
        playing = []
        for item in ((state.metadata,) if state.metadata else ()) + (tuple(state.queue.items) if state.queue else ()):
            playing += [item.title, item.artist, item.album]
        if self._report_lock.locked():
            return web.json_response({"error": "a report is already being prepared"}, status=409)
        async with self._report_lock:
            report = await asyncio.get_running_loop().run_in_executor(
                None, lambda: problem_report.build(note, rows, values.get, shares=shares,
                                                   now_playing=[p for p in playing if p]))
        logger.info("report: %s, %d bytes; taken out: %s", report.name, len(report.data), report.summary)
        return web.Response(body=report.data, content_type="application/zip", headers={
            "Content-Disposition": f'attachment; filename="{report.name}"',
            "X-Report-Summary": report.summary,
            "Cache-Control": "no-store",
        })

    #: ADR-0138 decision 4: a prepared report is kept this long, then dropped.
    REPORT_KEEP_S = 3600
    _report_job: dict | None = None

    def _report_inputs(self):
        """What the report is built from, read on the loop (the settings store
        is SQLite, bound to this thread)."""
        rows = self._settings.all_rows()
        values = {}
        for row in rows:
            try:
                values[row["key"]] = self._settings.value(row["key"])
            except Exception:  # noqa: BLE001 - a row that cannot be read is left out
                values[row["key"]] = None
        shares = self._lyrion_shares.all() if self._lyrion_shares is not None else []
        state = self._store.state
        playing = []
        for item in ((state.metadata,) if state.metadata else ()) + (tuple(state.queue.items) if state.queue else ()):
            playing += [item.title, item.artist, item.album]
        return rows, values, shares, [p for p in playing if p]

    def _report_now(self) -> dict | None:
        job = self._report_job
        if job and job.get("at") and time.monotonic() - job["at"] > self.REPORT_KEEP_S:
            self._report_job = job = None
        return job

    async def _handle_report_prepare(self, request: web.Request) -> web.Response:
        """ADR-0138 §1: the report prepared in the background, its checklist
        ticked as it goes (`/report/status`)."""
        if self._settings is None:
            return web.json_response({"error": "settings are not wired up"}, status=503)
        try:
            body = await request.json() if request.can_read_body else {}
        except ValueError:
            body = {}
        if not isinstance(body, dict):
            body = {}
        job = self._report_now()
        if job and job["state"] == "preparing":
            return web.json_response({"error": "a report is already being prepared"}, status=409)
        what = str(body.get("what") or "")[:4000]
        often = body.get("often") if body.get("often") in problem_report.OFTEN else None
        rows, values, shares, playing = self._report_inputs()
        job = {"state": "preparing", "what": what, "often": often, "done": {}, "at": None,
               "report": None, "error": None, "version": ""}
        self._report_job = job

        def tell(step: str, detail: str) -> None:
            job["done"][step] = detail          # read by /report/status; plain assignment

        def work():
            report = problem_report.build(what, rows, values.get, shares=shares, now_playing=playing,
                                          progress=tell)
            version = problem_report._run("dpkg-query", "-W", "-f", "${Version}", "gexis-player").strip()
            return report, version

        async def run() -> None:
            async with self._report_lock:
                try:
                    report, version = await asyncio.get_running_loop().run_in_executor(None, work)
                except Exception as exc:  # noqa: BLE001 - said on the sheet, not lost
                    logger.exception("report: preparing failed")
                    job.update(state="failed", error=str(exc) or type(exc).__name__)
                    return
            logger.info("report: %s, %d bytes; taken out: %s", report.name, len(report.data), report.summary)
            job.update(state="ready", report=report, version=version.split("+")[0], at=time.monotonic())

        asyncio.ensure_future(run())
        return web.json_response({"ok": True})

    async def _handle_report_status(self, request: web.Request) -> web.Response:
        job = self._report_now()
        if job is None:
            return web.json_response({"state": "idle"})
        report = job["report"]
        return web.json_response({
            "state": job["state"],
            "steps": [{"id": sid, "label": label, "done": sid in job["done"], "detail": job["done"].get(sid, "")}
                      for sid, label in problem_report.STEPS],
            "error": job["error"],
            "name": report.name if report else None,
            "size": len(report.data) if report else None,
            "files": [{"name": n, "size": b} for n, b in report.files] if report else [],
            "summary": report.summary if report else None,
        })

    async def _handle_report_file(self, request: web.Request) -> web.Response:
        job = self._report_now()
        if not job or job["state"] != "ready":
            return web.json_response({"error": "No report is ready. Prepare it again."}, status=404)
        report = job["report"]
        return web.Response(body=report.data, content_type="application/zip", headers={
            "Content-Disposition": f'attachment; filename="{report.name}"', "Cache-Control": "no-store"})

    async def _handle_report_issue(self, request: web.Request) -> web.Response:
        job = self._report_now()
        if not job or job["state"] != "ready":
            return web.json_response({"error": "No report is ready. Prepare it again."}, status=404)
        return web.json_response({"url": problem_report.issue_url(job["what"], job["often"], job["version"],
                                                                  job["report"])})

    async def _hardware_facts(self):
        """ADR-0126: what the device reads of its sound card and screen. The
        settings are read here, on the loop (SQLite is bound to this thread);
        the rest, which opens files and runs commands, in a worker."""
        from gexis_core import board_apply, outputs
        stored = self._settings.value("output_device") if self._settings else None
        screen = self._settings.value("screen") if self._settings else None

        def gather():
            output = outputs.resolve(stored)
            written = board_apply.written()
            builtin = output is not None and output.card in outputs.BUILT_IN_CARDS
            return hardware_report.collect(
                output.card if output and not builtin else None,
                chosen_board=written.id if written else None,
                screen_chosen=screen,
                builtin=output.label if builtin else None,
            )

        return await asyncio.get_running_loop().run_in_executor(None, gather)

    async def _handle_hardware_report(self, request: web.Request) -> web.Response:
        """ADR-0126: the facts a hardware report carries, for the sheet to show
        before anything is sent."""
        facts = await self._hardware_facts()
        display = self._display(facts)
        board, screen = hardware_report.names(facts, display)
        return web.json_response({
            # George, 2026-10-07: the screen step only when there is a screen
            # to look at - not headless, and one connected.
            "display": display,
            "board": board if (facts.card or facts.builtin) else None,
            "state": facts.state,
            "screen": screen or None,
            "touch": display and bool(facts.touch),
            "text": facts.text(),
        })

    def _display(self, facts) -> bool:
        """A screen to look at: connected, and the player not Headless."""
        headless = bool(self._settings.value("headless")) if self._settings else False
        return bool(facts.screen_connected) and not headless

    #: One set of tones at a time: two phones at once shared the files and
    #: each took the card from the other (review, 2026-10-11).
    _tones_lock = None

    async def _handle_hardware_tones(self, request: web.Request) -> web.Response:
        """ADR-0126: a tone at 44.1, 96 and 192 kHz through the player's own
        output, and what the card ran at - **only when nothing is playing**:
        a test never cuts into music."""
        from gexis_core import outputs
        if self._tones_lock is None:
            self._tones_lock = asyncio.Lock()
        if self._tones_lock.locked():
            return web.json_response({"error": "The tones are already playing."}, status=409)
        output = outputs.resolve(self._settings.value("output_device")) if self._settings else None
        if output is None:
            return web.json_response({"error": "No output to play to."}, status=409)
        async with self._tones_lock:
            why = hardware_report.busy(output.card)
            if why == "playing":
                return web.json_response({"error": "Something is playing. Stop it first, then play the tones."},
                                         status=409)
            if why == "held":
                return web.json_response({"error": "A source still holds the sound card, paused. Stop it, "
                                                   "then play the tones."}, status=409)
            try:
                results = await asyncio.get_running_loop().run_in_executor(
                    None, lambda: hardware_report.play_tones(output.card))
            except hardware_report.CardBusy:
                return web.json_response({"error": "A source took the sound card while the tones played. "
                                                   "Stop it, then play them again."}, status=409)
        return web.json_response({"tones": results})

    async def _handle_hardware_issue(self, request: web.Request) -> web.Response:
        """ADR-0126: the issue form's address, pre-filled with the facts and
        the owner's answers `{"answers": {...}, "notes": "..."}`."""
        try:
            body = await request.json() if request.can_read_body else {}
        except ValueError:
            body = {}
        if not isinstance(body, dict):
            return web.json_response({"error": "expected an object"}, status=400)
        raw = body.get("answers") if isinstance(body.get("answers"), dict) else {}
        answers = {k: str(v) for k, v in raw.items() if isinstance(v, str) and v}
        notes = str(body.get("notes") or "")[:2000]
        tones = [str(t) for t in (body.get("tones") if isinstance(body.get("tones"), list) else [])][:6]
        # Only the check this feedback ran: one left from another phone or an
        # earlier opening said "not all within" in feedback that had no
        # screen step at all (review, 2026-10-11).
        check = self._store.state.screen_check or {}
        ran = body.get("check_seq")
        screen = (hardware_report.screen_lines(check["result"])
                  if check.get("result") and ran is not None and ran == check.get("seq") else None)
        facts = await self._hardware_facts()
        display = self._display(facts)
        url = hardware_report.issue_url(facts, answers, notes, tones, screen, display)
        # A report prepared is the prompt answered: it is not asked again.
        if self._settings is not None:
            await self._dismiss_hardware_prompt()
            # And kept, to be sent again (ADR-0126 amended 2026-10-11).
            board, screen_name = hardware_report.names(facts, display)
            self._settings.keep(hardware_report.KEPT_KEY, {
                "identity": await self._hardware_identity(), "at": time.time(),
                "board": board, "screen": screen_name or None, "url": url})
        return web.json_response({"url": url})

    async def _hardware_identity(self) -> str:
        """ADR-0126 amended 2026-10-11: the sound card and screen in use, as
        the key what is kept was made on."""
        from gexis_core import board_apply, boards, outputs
        stored = self._settings.value("output_device") if self._settings else None
        screen = self._settings.value("screen") if self._settings else None

        def gather():
            output = outputs.resolve(stored)
            card = output.card if output and output.card not in outputs.BUILT_IN_CARDS else None
            board = None
            if card:
                written = board_apply.written()
                board, _ = boards.identify(card, chosen=written.id if written else None,
                                           product=hardware_report._read(hardware_report.HAT / "product") or None)
            from gexis_core import screen_detect
            try:
                seen = screen_detect.seen()
                shown = f"{seen.edid_maker or ''}/{seen.edid_name or ''}" if seen.connected and not headless else None
            except Exception:  # noqa: BLE001 - unread is no screen
                shown = None
            return hardware_report.identity(card, board.id if board else None, screen, shown)

        headless = bool(self._settings.value("headless")) if self._settings else False
        return await asyncio.get_running_loop().run_in_executor(None, gather)

    async def _handle_hardware_kept(self, request: web.Request) -> web.Response:
        """The last feedback, for the System row: when, what, and the link to
        send it again. Forgotten here when the hardware has changed."""
        if self._settings is None:
            return web.json_response({"kept": None})
        stored = self._settings.kept(hardware_report.KEPT_KEY)
        kept = hardware_report.kept_for(stored, await self._hardware_identity())
        if stored and kept is None:
            self._settings.keep(hardware_report.KEPT_KEY, None)
        if kept is None:
            return web.json_response({"kept": None})
        return web.json_response({"kept": {k: kept.get(k) for k in ("at", "board", "screen", "url")}})

    async def _handle_hardware_file(self, request: web.Request) -> web.Response:
        """ADR-0138 decision 3: the prepared feedback as a text file, to send
        by e-mail."""
        stored = self._settings.kept(hardware_report.KEPT_KEY) if self._settings is not None else None
        kept = hardware_report.kept_for(stored, await self._hardware_identity())
        if kept is None:
            return web.json_response({"error": "No feedback is prepared."}, status=404)
        stamp = time.strftime("%Y-%m-%d", time.localtime(kept.get("at") or time.time()))
        return web.Response(text=hardware_report.feedback_text(kept["url"]), content_type="text/plain",
                            charset="utf-8", headers={
                                "Content-Disposition": f'attachment; filename="gexis-hardware-{stamp}.txt"',
                                "Cache-Control": "no-store"})

    async def _handle_hardware_kept_clear(self, request: web.Request) -> web.Response:
        """*Start over*: the kept feedback forgotten."""
        if self._settings is not None:
            self._settings.keep(hardware_report.KEPT_KEY, None)
        return web.json_response({"ok": True})

    async def _hardware_pieces(self) -> dict[str, str]:
        """ADR-0126 decision 1: what on this device is not Tested. Settings
        on the loop; the board's EEPROM and the list in a worker."""
        from gexis_core import board_apply, boards, outputs, screens
        stored = self._settings.value("output_device") if self._settings else None
        screen = self._settings.value("screen") if self._settings else None

        def gather():
            output = outputs.resolve(stored)
            card = output.card if output and output.card not in outputs.BUILT_IN_CARDS else None
            board = state = None
            if card:
                written = board_apply.written()
                board, state = boards.identify(card, chosen=written.id if written else None,
                                               product=hardware_report._read(hardware_report.HAT / "product") or None)
            model = screens.by_label(screen) if screen else None
            return hardware_report.untested(card, board.id if board else None, state,
                                            screen if model else None, model.tested if model else None)

        return await asyncio.get_running_loop().run_in_executor(None, gather)

    async def _handle_hardware_prompt(self, request: web.Request) -> web.Response:
        """ADR-0126 decision 1: the System page's one line, after a week on
        hardware that is not Tested; null when there is nothing to ask."""
        if self._settings is None:
            return web.json_response({"text": None})
        pieces = await self._hardware_pieces()
        text, record = hardware_report.prompt(self._settings.kept(hardware_report.PROMPT_KEY), pieces, time.time())
        self._settings.keep(hardware_report.PROMPT_KEY, record)
        return web.json_response({"text": text})

    async def _handle_hardware_prompt_dismiss(self, request: web.Request) -> web.Response:
        """*"dismissed for good with one tap"* - for this hardware; another
        board or screen later is asked about in its own time."""
        if self._settings is not None:
            await self._dismiss_hardware_prompt()
        return web.json_response({"ok": True})

    async def _dismiss_hardware_prompt(self) -> None:
        pieces = await self._hardware_pieces()
        self._settings.keep(hardware_report.PROMPT_KEY,
                            hardware_report.dismissed(self._settings.kept(hardware_report.PROMPT_KEY), pieces))

    #: ADR-0126: the pattern goes away by itself if nobody finishes it.
    SCREEN_CHECK_S = 120

    async def _handle_hardware_screen(self, request: web.Request) -> web.Response:
        """ADR-0126: the test pattern on the panel, asked for from a phone
        (`{"show": true}`) and taken down from it (`{"show": false}`)."""
        try:
            body = await request.json() if request.can_read_body else {}
        except ValueError:
            body = {}
        if not isinstance(body, dict):
            body = {}
        check = dict(self._store.state.screen_check or {})
        if not body.get("show"):
            if check:
                self._store.set_screen_check({**check, "showing": False})
            return web.json_response({"ok": True})
        touch = bool(await asyncio.get_running_loop().run_in_executor(None, hardware_report._touch))
        # The pattern is the browser's; the visualiser is a window over it, and
        # a screen in standby is dark (review, 2026-10-11): both would hide it
        # while the phone said it was up.
        if self._peppy is not None:
            # Lowered off the loop, its change published back on it.
            await self._peppy.request_async("hide")
        if self._standby is not None:
            self._standby.used()
            if self._standby.may_be_dark:
                await self._standby.wake("screen check")
        seq = int(check.get("seq", 0)) + 1
        self._store.set_screen_check({"showing": True, "touch": touch, "seq": seq, "result": None})

        def expire():
            now = self._store.state.screen_check or {}
            if now.get("seq") == seq and now.get("showing"):
                self._store.set_screen_check({**now, "showing": False})

        asyncio.get_running_loop().call_later(self.SCREEN_CHECK_S, expire)
        return web.json_response({"seq": seq, "touch": touch})

    async def _handle_hardware_screen_result(self, request: web.Request) -> web.Response:
        """ADR-0126: the panel's four corner taps `{"seq", "width", "height",
        "taps"}`, in the screen's own pixels - measured here, shown on the phone."""
        try:
            body = await request.json()
            check = dict(self._store.state.screen_check or {})
            if not check.get("showing") or body.get("seq") != check.get("seq"):
                return web.json_response({"error": "No test pattern is being shown."}, status=409)
            result = hardware_report.measure_taps(int(body["width"]), int(body["height"]), list(body["taps"]))
        except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
            return web.json_response({"error": "bad taps"}, status=400)
        self._store.set_screen_check({**check, "showing": False, "result": result})
        return web.json_response(result)

    async def _handle_panel_shown(self, request: web.Request) -> web.Response:
        """ADR-0101: the panel reporting whether its idle screen is up - and,
        as amended, whether its lyrics are - so the phone's toggles say what
        the panel shows, whatever changed it. **The panel only** (review,
        2026-10-12): a phone saying so would set the toggles to a lie."""
        if not self._from_panel(request):
            return web.json_response({"error": "only the panel reports what it shows"}, status=403)
        try:
            body = await request.json()
            shown = {key: bool(body[key]) for key in ("idle", "lyrics", "now") if key in body}
        except (ValueError, TypeError, AttributeError):
            shown = {}
        if not shown:
            return web.json_response({"error": 'body must hold "idle", "lyrics" or "now", each a bool'}, status=400)
        self._store.set_panel(**shown)
        return web.json_response(shown)

    async def _handle_setup_status(self, request: web.Request) -> web.Response:
        """ADR-0104 §5: whether setup is needed and the setup network's state.
        **The password goes to the panel only** - it arrives on loopback
        (ADR-0035 §6) - because it is on the glass for anyone in the room and
        nowhere else."""
        if self._setup is None:
            return web.json_response({"needed": False, "network": "unmanaged"})
        panel = self._from_panel(request)
        return web.json_response(self._setup.status() if panel else self._setup.public_status())

    @staticmethod
    def _setup_error(raw: str, status: int) -> web.Response:
        """A setup error as the phone shows it - a sentence - with the
        core's own text in the log (setup_flow.said)."""
        from gexis_core import setup_flow

        logger.info("setup: answered %s: %s", status, raw)
        return web.json_response({"error": setup_flow.said(raw)}, status=status)

    @web.middleware
    async def _note_setup_use(self, request: web.Request, handler):
        """**Somebody is using the setup page** (George, 2026-10-12): the
        page itself or any `/setup/...` route, from a phone - the panel is on
        loopback and asks `/setup/status` for itself. A phone on the setup
        network holds a configured player off its saved Wi-Fi only while
        this was recent (`setup_network.SETUP_ACTIVE_S`)."""
        if (self._setup is not None and (request.path == "/" or request.path.startswith("/setup/"))
                and not self._from_panel(request)):
            self._setup.page_used()
        return await handler(request)

    def _setup_closed(self) -> web.Response | None:
        """ADR-0104: the setup routes answer only while setup is on - the
        setup network is up, or a new device waits to be set up. A configured
        device on its Wi-Fi has Settings for all of this."""
        if self._setup is None or self._setup_flow is None:
            return self._setup_error("setup is not wired up", 503)
        status = self._setup.status()
        if status["network"] in ("open", "failed", "joining") or status["needed"]:
            return None
        return self._setup_error("setup is not running", 409)

    async def _handle_plugin_upload(self, request: web.Request) -> web.Response:
        """ADR-0106: the package as the request body. Read here with its own
        cap rather than aiohttp's 1 MB `client_max_size`, which is for forms."""
        if self._upload_plugin is None:
            return web.json_response({"error": "uploads are not wired up"}, status=503)
        from gexis_core import uploads
        chunks, size = [], 0
        async for chunk in request.content.iter_chunked(1 << 16):
            size += len(chunk)
            if size > uploads.MAX_BYTES:
                return web.json_response({"error": "It is larger than 200 MB."}, status=413)
            chunks.append(chunk)
        try:
            return web.json_response(await self._upload_plugin(b"".join(chunks)))
        except uploads.Refused as exc:
            return web.json_response({"error": f"Not installed: {exc}."}, status=400)

    async def _handle_plugin_uninstall(self, request: web.Request) -> web.Response:
        if self._uninstall_plugin is None:
            return web.json_response({"error": "uploads are not wired up"}, status=503)
        plugin_id = request.match_info["id"]
        if not await self._uninstall_plugin(plugin_id):
            return web.json_response({"error": f"{plugin_id} is not an uploaded plugin"}, status=404)
        return web.json_response({"uninstalled": plugin_id})

    async def _handle_park(self, request: web.Request) -> web.Response:
        """**The device is going down: leave nothing to resume.** Loopback
        only - it is the shutdown's, not a phone's."""
        if not self._from_panel(request):
            return web.json_response({"error": "loopback only"}, status=403)
        if self._park is None:
            return web.json_response({"parked": False})
        # `?stop=all`: an update's, which stops whoever is playing too.
        if request.query.get("stop") == "all":
            return web.json_response({"parked": bool(await self._park(stop_all=True))})
        return web.json_response({"parked": bool(await self._park())})

    async def _handle_setup_answers(self, request: web.Request) -> web.Response:
        closed = self._setup_closed()
        if closed is not None:
            return closed
        # The page loading is how the panel knows a phone reached it.
        self._setup.page_opened()
        return web.json_response(self._setup_flow.answers())

    async def _handle_setup_save(self, request: web.Request) -> web.Response:
        closed = self._setup_closed()
        if closed is not None:
            return closed
        try:
            body = await request.json()
            return web.json_response(self._setup_flow.save(body))
        except ValueError as exc:
            return self._setup_error(str(exc), 400)

    async def _handle_music_space(self, request: web.Request) -> web.Response:
        """The Music folder's free and total space, for part 2's *Where is
        your music?* (George, 2026-10-18). Read only."""
        space = await asyncio.to_thread(lyrion_folders.music_space)
        closed = await asyncio.to_thread(music_floor.is_closed)
        return web.json_response({**(space or {"free": None, "total": None, "text": None}), "closed": closed})

    async def _handle_setup_backup(self, request: web.Request) -> web.Response:
        """**ADR-0131: a backup, uploaded from the phone in setup.** The body
        is the file, streamed to disk under its own cap (a backup can be far
        larger than a form), then checked; the page gets the review or the
        reason in a sentence. `?name=` carries the file's name for the
        review, nothing more."""
        closed = self._setup_closed()
        if closed is not None:
            return closed
        from gexis_core import backups, setup_flow

        part = self._setup_flow.upload_path()
        part.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        try:
            fd = os.open(part, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "wb") as out:
                async for chunk in request.content.iter_chunked(1 << 16):
                    size += len(chunk)
                    if size > setup_flow.BACKUP_MAX_BYTES:
                        raise OverflowError
                    out.write(chunk)
        except OverflowError:
            part.unlink(missing_ok=True)
            return web.json_response({"error": "That file is larger than any gexis backup."}, status=413)
        except (OSError, ConnectionError) as exc:
            part.unlink(missing_ok=True)
            logger.warning("setup: backup upload failed after %d bytes: %s", size, exc)
            return web.json_response({"error": "The file did not arrive whole. Try again."}, status=400)
        try:
            answers = await asyncio.to_thread(self._setup_flow.take_backup, part, request.query.get("name"))
        except backups.Refused as exc:
            return web.json_response({"error": str(exc)}, status=400)
        return web.json_response(answers)

    async def _handle_setup_backup_forget(self, request: web.Request) -> web.Response:
        closed = self._setup_closed()
        if closed is not None:
            return closed
        return web.json_response(await asyncio.to_thread(self._setup_flow.forget_backup))

    async def _handle_setup_networks(self, request: web.Request) -> web.Response:
        """A scan, read while hosting (Finding 099: the phone stays on), less
        the setup network itself, which sees itself."""
        closed = self._setup_closed()
        if closed is not None:
            return closed
        from gexis_core import setup_network, wifi

        items = [i for i in await wifi.scan() if i["name"] != setup_network.SSID]
        return web.json_response({"items": items})

    async def _handle_setup_screen(self, request: web.Request) -> web.Response:
        """ADR-0109: the Screen step - what the screen reports, the tested
        model that suggests, and every model gexis knows."""
        closed = self._setup_closed()
        if closed is not None:
            return closed
        if self._screen_seen is None:
            return self._setup_error("screen detection is not wired up", 503)
        from gexis_core import setup_flow

        report = await asyncio.to_thread(self._screen_seen)
        try:
            turn = screen_apply.parse_rotation(self._settings.value("rotation")) if self._settings else 0
        except Exception:  # noqa: BLE001 - unturned is the safe guess for wording
            turn = 0
        return web.json_response(await asyncio.to_thread(setup_flow.screen_choices, report, turn))

    async def _handle_setup_outputs(self, request: web.Request) -> web.Response:
        """**The Volume choice under the Output step** (George, 2026-10-18):
        each output as Settings lists it, and whether it has a volume
        control of its own - without one, Hardware cannot be had, as in
        Settings (ADR-0127 §2)."""
        closed = self._setup_closed()
        if closed is not None:
            return closed
        from gexis_core import outputs

        found = await asyncio.to_thread(outputs.discover)
        return web.json_response([{"option": o.option, "hardware": o.control is not None} for o in found])

    async def _handle_setup_plugins(self, request: web.Request) -> web.Response:
        """ADR-0128: the Plugins step - every plugin the release ships, with
        what it is, where it downloads from, and its notice."""
        closed = self._setup_closed()
        if closed is not None:
            return closed
        offered = self._setup_flow.offered()
        return web.json_response([{k: p.get(k) for k in ("id", "name", "summary", "notice", "from", "component")}
                                  for p in offered])

    # -- ADR-0149: first use, part 2 ------------------------------------------

    def _personalise_offered(self) -> list[dict]:
        return self._setup_flow.offered() if self._setup_flow is not None else []

    async def _handle_personalise(self, request: web.Request) -> web.Response:
        """What the page needs beyond `/settings`: whether part 2 is owed, and
        the plugins it can switch on, by their switches."""
        from gexis_core import personalise
        return web.json_response({
            "state": personalise.state(),
            "first": personalise.first(),
            "plugins": [{"row": p["row"], "name": p["name"], "component": p.get("component")}
                        for p in self._personalise_offered() if p["row"] in personalise.PLUGIN_ROWS],
        })

    async def _handle_personalise_finish(self, request: web.Request) -> web.Response:
        """**The answers, written in one go** (ADR-0149): `{"settings": {key:
        value}}`, only keys part 2 may write; then what they install is
        followed (ADR-0128) and part 2 is done."""
        from gexis_core import personalise
        if self._settings is None:
            return web.json_response({"error": "settings are not wired up"}, status=503)
        try:
            body = await request.json()
            values = personalise.checked(body.get("settings"))
        except (ValueError, AttributeError) as exc:
            return web.json_response({"error": str(exc)}, status=400)
        result = personalise.apply(values, self._settings, self._personalise_offered(), settling.begin,
                                   self._store.state.components)
        personalise.end(personalise.DONE)
        self._store.set_personalise(None)
        if "lms_server" in result["written"]:
            asyncio.ensure_future(self._restart_when_settled())
        return web.json_response({"ok": True, **result})

    async def _restart_when_settled(self, every_s: float = 3.0, give_up_s: float = 3600.0) -> None:
        """**A Lyrion server set by part 2 is used from the core's next start**
        (the rule Settings follows, `_chosen_server`): George, 2026-10-18 -
        after part 2 the library's tiles had nothing behind them. The core
        restarts, but only once the downloads part 2 began are in: the skins
        install as the core's own child and would be cut off. Settled is the
        settling record gone, or every download in it done or failed - not
        Lyrion's read of the music, which the plate follows too (ADR-0149
        decision 43) and which takes hours on a large library."""
        waited = 0.0
        while waited < give_up_s:
            view = self._store.state.settling
            if settling.read() is None or settling.downloads_in(view):
                break
            await asyncio.sleep(every_s)
            waited += every_s
        await asyncio.sleep(2.0)
        logger.info("personalise: restarting the core to use the Lyrion server part 2 chose")
        await asyncio.create_subprocess_exec("systemctl", "restart", "gexis-core")

    async def _handle_personalise_later(self, request: web.Request) -> web.Response:
        """*Do it later* (`personalise.put_off`)."""
        from gexis_core import personalise
        personalise.put_off(self._settings, personalise.first())
        self._store.set_personalise(None)
        return web.json_response({"ok": True})

    async def _handle_settling_done(self, request: web.Request) -> web.Response:
        """ADR-0128: the owner's OK on a settling screen that names a
        download that did not finish."""
        if self._settling_done is None:
            return web.json_response({"error": "not wired up"}, status=503)
        self._settling_done()
        return web.json_response({"ok": True})

    async def _handle_settling_hide(self, request: web.Request) -> web.Response:
        """ADR-0128 amended 2026-10-10: the owner put the settling screen away
        while the downloads go on."""
        if self._settling_hide is None:
            return web.json_response({"error": "not wired up"}, status=503)
        self._settling_hide()
        return web.json_response({"ok": True})

    async def _handle_setup_finish(self, request: web.Request) -> web.Response:
        closed = self._setup_closed()
        if closed is not None:
            return closed
        try:
            told = self._setup_flow.finish() or {}
        except ValueError as exc:
            return self._setup_error(str(exc), 400)
        return web.json_response({"finishing": True, **told}, status=202)

    async def _handle_painted(self, request: web.Request) -> web.Response:
        """The panel reporting its first painted frame, which is what ends
        the boot animation (ADR-0043 §3).

        Deliberately not tied to `gexis-kiosk.service` going active: that
        happens at 18.26s (Finding 038) and the panel is still a second or
        two from drawing anything. The gap between the two is where a flash
        of black would show.

        Answers 200 whether or not there was a splash to drop - a panel that
        reloads reports a first frame again, and a development machine has
        no plymouth at all. Neither is the panel's problem."""
        dropped = self._splash.drop() if self._splash is not None else False
        if self._on_painted is not None and self._from_panel(request):
            self._on_painted()
        return web.json_response({"painted": True, "splash_dropped": dropped})

    async def _handle_screen_new(self, request: web.Request) -> web.Response:
        """ADR-0109, amended 2026-10-03: the answer to "a different screen is
        attached" - from the panel or a phone, unlike Keep: choosing is not
        proving that the picture and the touch work, and Keep still asks
        that on the panel after the restart."""
        action = request.match_info["action"]
        if action not in ("use", "later", "choose") or self._screen_new_answer is None:
            return web.json_response({"error": f"unknown answer {action}"}, status=404)
        return web.json_response(await self._screen_new_answer(action))

    async def _handle_screen_answer(self, request: web.Request) -> web.Response:
        """**ADR-0109 decision 2: Keep is pressed on the panel only** - a touch
        there proves both the picture and the touch input. Loopback: the
        panel's Chromium is on this device; a phone is not. **Except on a
        screen without touch** (ADR-0147 D3, a TV): nothing there can be
        pressed, so the phone answers - the question says so (`phone`); and
        on a listed panel whose touch the player does not recognise, which
        may need a driver it never installs (Finding 125, 2026-10-14)."""
        confirm = self._store.state.screen_confirm or {}
        action = request.match_info["action"]
        local = self._from_panel(request)
        # **`shown`: the panel has drawn the question** (George, 2026-10-14:
        # "The countdown should start with the keep screen displayed") - its
        # countdown starts then. Only the panel says what is on its glass.
        if action == "shown" and not local:
            return web.json_response({"error": "only the panel reports this"}, status=403)
        if not local and not confirm.get("phone"):
            return web.json_response({"error": "only the panel answers this"}, status=403)
        if action not in ("keep", "revert", "shown") or self._screen_answer is None:
            return web.json_response({"error": f"unknown answer {action}"}, status=404)
        return web.json_response(await self._screen_answer(action))

    async def _handle_peppy(self, request: web.Request) -> web.Response:
        action = request.match_info["action"]
        if self._peppy is None:
            return web.json_response({"error": "the Peppy screen is not wired up"}, status=503)
        if action not in ("show", "hide"):
            return web.json_response({"error": f"unknown action {action}"}, status=404)
        # Off the loop: raising or lowering waits on wlrctl (review, 2026-10-12).
        shown = await self._peppy.request_async(action)
        # **Only when it was tried and found no window** (ShelvesPi,
        # 2026-10-21): a show refused for standby started the driver again
        # with the only output off, and it could not start - *the video
        # driver did not add any displays* - so the visualiser stayed gone.
        if (not shown and action == "show" and self._peppy._has_levels()
                and not getattr(self._peppy, "refused", False)):
            # **One restart at a time** (review, 2026-10-12): a second tap
            # while the skins load (~9 s) restarted the unit again and killed
            # the half-loaded one. A later ask waits for the restart under way;
            # shielded, so a phone that gives up does not cancel it for all.
            if self._peppy_restarting is None or self._peppy_restarting.done():
                self._peppy_restarting = asyncio.ensure_future(self._peppy_again())
            shown = await asyncio.shield(self._peppy_restarting)
        if not shown:
            return web.json_response({"error": "no Peppy screen window to act on"}, status=409)
        return web.json_response({"peppy": action})

    #: How long a restarted visualiser has to put its window up (its skins
    #: load in about 9 s on a Pi 4 with the 1920x1080 packs, guestpi).
    PEPPY_AGAIN_S = 25

    async def _peppy_again(self) -> bool:
        """**Asked to show, and there is no window: start it again.** Its
        loop can end (a skin that would not build ended it on guestpi,
        2026-10-07, and the panel then said only *no Peppy screen window to
        act on* for hours). The unit is `Restart=no` so a crash loop stays
        visible; a listener asking for it is a reason to try once."""
        logger.warning("peppy: no window to show; starting gexis-peppy again")
        proc = await asyncio.create_subprocess_exec("systemctl", "restart", "gexis-peppy.service")
        await proc.wait()
        deadline = asyncio.get_running_loop().time() + self.PEPPY_AGAIN_S
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(1.5)
            # On the loop, as the first ask is: showing publishes the panel's
            # change to the phones, and that needs the loop (a worker thread
            # here answered the first visualiser of an evening with a 500,
            # sofapi 2026-10-11, though it came up).
            if await self._peppy.request_async("show"):
                return True
        return False

    async def _handle_notice(self, request: web.Request) -> web.Response:
        """ADR-0099: the Legal and Credits pages, from `notices.json`."""
        from gexis_core import changelog, notices

        name = request.match_info["name"]
        # ADR-0116: the release notes, drawn as a document.
        page = changelog.page() if name == "changelog" else notices.document(name)
        if page is None:
            return web.json_response({"error": "no such document"}, status=404)
        return web.json_response(page)

    async def _handle_settings(self, request: web.Request) -> web.Response:
        if self._settings is None:
            return web.json_response({"error": "settings are not wired up"}, status=503)
        # Each callback's reads (ports, skins) once for this answer.
        with memo.scope():
            groups = self._settings.to_json()
            await self._seed_lists(groups)
        # ADR-0048 §5: the header reads name - hostname - address, and the
        # last two are the system's own. After a rename the stored name and
        # the live hostname disagree, and that disagreement is exactly what
        # the user needs to see.
        return web.json_response(
            {
                "groups": groups,
                "device": {
                    # A registry without the row is not a broken request: the
                    # header simply has one fewer fact to show.
                    "name": self._setting_or_none("device_name"),
                    "hostname": device_name.hostname(),
                    "address": device_name.address(),
                },
            }
        )

    #: A `list` whose items are one cheap local read arrives **with the
    #: row** (ADR-0044 §1, amended 2026-09-21). The others carry
    #: `discover: true` and go looking when their sheet opens, which is
    #: what the sheet's searching state is for: LMS discovery listens for
    #: 2.5 s and a Wi-Fi scan takes seconds, where BlueZ answers in 22-29 ms.
    #: Module and attribute rather than the function itself, so the name is
    #: resolved when it is called - the same late binding every other call
    #: here has, and what lets a test stand in for BlueZ.
    #: Lists whose items arrive with `/settings` rather than being fetched
    #: when the sheet opens. `bt_trusted` reads BlueZ; `restore` reads a
    #: directory (ADR-0083), which is local and instant, so making somebody
    #: open the sheet to learn there are no backups would be a spinner over
    #: a `stat` call.
    SEEDED_LISTS = {"bt_trusted": (bluetooth_devices, "known")}

    async def _seed_lists(self, groups: list[dict]) -> None:
        """Give the rows that do not have to go looking their items.

        **Two things need them, and the row needs them first.** A device
        list's value is a count of its items, so a row counting only what
        the *sheet* fetches reads "None" until someone opens it - which is
        what it did on the device with a phone paired (George,
        2026-09-21). And a sheet whose items are already in the panel's
        hands opens drawn, instead of showing a searching state for the
        three frames a 25 ms read takes.

        Read per request rather than cached: `/settings` is fetched when
        the screen mounts and when a write moves the revision, which is
        exactly when the row is drawn. A list that is a bus round-trip old
        is wrong in the direction that matters - a device forgotten
        elsewhere still listed here.
        """
        for group in groups:
            for row in group["rows"]:
                key = row.get("key")
                if key == "lyrion-server.more":
                    # ADR-0150: the server's own page first, by this player's
                    # name; the apps' links come from the manifest.
                    host = device_name.hostname() or "gexis"
                    row["links"] = [{"label": "Lyrion's own page", "url": f"http://{host}.local:9000"},
                                    *(row.get("links") or [])]
                    continue
                if key == "lyrion-server.library":
                    # ADR-0115 decision 28 (George, 2026-10-18): the stage, its
                    # line and, while Lyrion reads, how far - kept after Ready.
                    stage = dict(lyrion_stage.CURRENT)
                    if stage:
                        row["value"] = stage["label"]
                        row["note"] = stage["line"]
                        row["progress"] = stage.get("share") if stage["phase"] == "scanning" else None
                        row["busy"] = stage["phase"] in ("starting", "addons", "waiting") or (
                            stage["phase"] == "scanning" and stage.get("share") is None)
                    continue
                if key == "lyrion-server.music_folder":
                    # George, 2026-10-18: the Music folder's free and total space.
                    space = await asyncio.to_thread(lyrion_folders.music_space)
                    if space:
                        row["note"] = f"{row.get('note') or ''} {space['text']}.".strip()
                    # ADR-0115 decision 27: closed below 4 GB free.
                    if await asyncio.to_thread(music_floor.is_closed):
                        row["note"] += (" The card is nearly full: the Music share takes no new files"
                                        " until 4.5 GB is free.")
                    continue
                if row["type"] != "list":
                    continue
                if key == "restore":
                    row["items"] = [a.to_item() for a in backups.available()]
                    continue
                if key == "lyrion-server.shares":
                    # ADR-0115: the shares added, each with its Forget, on the
                    # row itself; the stored list - logins included - is not
                    # what the row shows (George, 2026-10-03: "look like just
                    # code"), so it is not sent.
                    row["value"] = None
                    row["items"] = await self._share_items() if self._lyrion_shares else []
                    continue
                if key == "lyrion-server.usb_folders":
                    # ADR-0115 decision 23: each folder chosen, with its
                    # Remove, and each drive plugged in with nothing chosen.
                    row["value"] = None
                    row["items"] = await self._usb_items(sheet=False) if self._lyrion_usb else []
                    continue
                source = self.SEEDED_LISTS.get(key)
                if source is None:
                    continue
                module, name = source
                # `_bluetooth` answers [] for an adapter that is not there,
                # so an unavailable BlueZ reads as the row's own empty state
                # rather than failing the whole settings payload.
                row["items"] = await self._bluetooth(getattr(module, name))

    async def _usb_items(self, sheet: bool) -> list[dict]:
        """The USB folders' rows (`sheet=False`) or the drives to browse.
        The store on this thread; the drives, which read the disk, in a
        worker."""
        usb = self._lyrion_usb
        chosen = usb.all()

        def look() -> tuple[list[str], dict]:
            plugged = usb.plugged()
            return plugged, {d: usb.label_of(d) for d in {*plugged, *(e["drive"] for e in chosen)}}
        plugged, labels = await asyncio.to_thread(look)
        return (usb.sheet_items if sheet else usb.items)(chosen, plugged, labels)

    async def _usb_action(self, body: dict, name: str, action: str) -> web.Response:
        """ADR-0115 decision 23: browse a drive's folders, add one, remove
        one. `name` is the drive (browse, add) or the item's address
        (forget)."""
        usb = self._lyrion_usb
        if usb is None:
            return web.json_response({"ok": False, "error": "USB folders are not wired up"})
        folder = str(body.get("folder") or "")
        try:
            if action == "browse":
                found = await asyncio.to_thread(usb.browse, name, folder)
                label = usb.name_of(name, await asyncio.to_thread(usb.label_of, name))
                clean = lyrion_usb.clean(folder)
                # George, 2026-10-18 ("Tick several"): folders only, each
                # ticked or opened by the page; the path above them, a
                # step each, is how it goes back up.
                items = [{"name": f["name"], "meta": "Has folders inside" if f["deeper"] else "",
                          "bars": None, "state": "found", "open": True, "drive": name, "folder": f["folder"]}
                         for f in found]
                parts = clean.split("/") if clean else []
                crumbs = [{"name": label, "drive": name, "folder": ""}] + [
                    {"name": part, "drive": name, "folder": "/".join(parts[:i + 1])} for i, part in enumerate(parts)]
                return web.json_response({"ok": True, "error": None, "items": items, "crumbs": crumbs,
                                          "title": f"{label} / {clean}" if clean else label})
            if action == "add":
                label = await asyncio.to_thread(usb.label_of, name)
                usb.add(name, folder, label)
            elif action == "forget":
                usb.remove(name)
            else:
                return web.json_response({"error": f"unknown action {action}"}, status=400)
        except ValueError as exc:
            return web.json_response({"ok": False, "error": f"Needs {exc}"})
        if self._lyrion_shares_changed is not None:
            self._lyrion_shares_changed()
        return web.json_response({"ok": True, "error": None})

    async def _share_items(self) -> list[dict]:
        """The Lyrion shares' rows. The list is read on this thread - the
        settings store is SQLite, which answers only the thread that opened
        it - and the mount checks in a worker: a share whose NAS is off
        holds a stat for the whole NFS timeout (review, 2026-10-12)."""
        shares = self._lyrion_shares.all()
        mounted = await asyncio.to_thread(self._lyrion_shares.mounted, shares)
        return self._lyrion_shares.items(mounted)

    async def _handle_pairing_answer(self, request: web.Request) -> web.Response:
        """Accept or reject the open pairing request (ADR-0045).

        409 when nothing is being asked, which is the answer to a tap that
        arrived after the agent's window closed - **it must not land on the
        next request**, and the panel needs to hear that rather than assume
        it worked.
        """
        if self._pairing_answer is None:
            return web.json_response({"error": "no pairing agent"}, status=503)
        answer = request.match_info["answer"]
        if answer not in ("accept", "reject"):
            return web.json_response({"error": f"unknown answer {answer}"}, status=400)
        if not self._pairing_answer(answer == "accept"):
            return web.json_response({"error": "nothing is being asked"}, status=409)
        return web.json_response({"answer": answer})

    @staticmethod
    async def _bluetooth(call, *args):
        """Run one BlueZ call on a connection of its own.

        A short-lived bus rather than the daemon's: the adapter's own
        connection is driving A2DP and the agent, and a settings sheet
        reaching into it to enumerate devices would couple the two for no
        gain. Opening a system bus is cheap and a sheet is rare.
        """
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        try:
            return await call(bus, *args)
        except Exception as exc:
            logger.warning("bluetooth: %s failed: %s", getattr(call, "__name__", call), exc)
            return [] if not args else (False, "Bluetooth is unavailable.")
        finally:
            bus.disconnect()

    def _setting_or_none(self, key: str):
        try:
            return self._settings.value(key)
        except UnknownSetting:
            return None

    async def _handle_setting_write(self, request: web.Request) -> web.Response:
        if self._settings is None:
            return web.json_response({"error": "settings are not wired up"}, status=503)
        key = request.match_info["key"]
        try:
            body = await request.json()
            value = body["value"]
        except (ValueError, KeyError, TypeError):
            return web.json_response({"error": 'body must be {"value": ...}'}, status=400)
        before = self._settings_value(key)
        # The answer carries the revision the save made, so the page that
        # saved reloads the settings once, whichever of this answer and the
        # revision's broadcast reaches it first (George, 2026-10-16: two
        # full reloads followed every tap on the phone).
        response = self._settings_call(lambda: {"key": key, "value": self._settings.set(key, value),
                                                "revision": self._store.settings_revision})
        if response.status == 200 and self._settings_value(key) != before:
            restarts = self._settings_restarts(key)
            if restarts == "core":
                asyncio.ensure_future(self._restart_core_for(key))
            elif restarts and self._restart_device is not None:
                asyncio.ensure_future(self._restart_device(key))
        return response

    async def _restart_core_for(self, key: str) -> None:
        """**A Lyrion server chosen in Settings is used at once** (George,
        2026-10-23: *"Yes"*, ADR-0048 amended). The server is read at the
        core's start; before, a choice waited for the next one, and the
        player went on asking the old address while Settings showed the new.
        The core restarts as part 2's does (`_restart_when_settled`), after
        the answer, which the toast needs."""
        logger.info("settings: %s changed; restarting the core to use it", key)
        await asyncio.sleep(1.5)
        await asyncio.create_subprocess_exec("systemctl", "restart", "gexis-core")

    def _settings_value(self, key: str):
        try:
            return self._settings.value(key)
        except Exception:  # noqa: BLE001 - the write below says what is wrong
            return None

    def _settings_restarts(self, key: str) -> bool | str:
        """The row's `restart`: true restarts the device, `"core"` the core."""
        try:
            return self._settings.row(key).get("restart") or False
        except Exception:  # noqa: BLE001
            return False

    async def _handle_setting_action(self, request: web.Request) -> web.Response:
        if self._settings is None:
            return web.json_response({"error": "settings are not wired up"}, status=503)
        key = request.match_info["key"]
        if key == "backup" and request.query.get("before") == "update":
            return self._backup_before_update()

        def run():
            self._settings.run(key)
            return {"key": key}

        return self._settings_call(run)

    def _backup_before_update(self) -> web.Response:
        """**The updater's backup, kept three deep** (George, 2026-10-12,
        answer 3). `POST /settings/backup?before=update`: named as the
        updater's own, and the updater's older ones beyond
        `backups.KEEP_AUTOMATIC` deleted once it is written - never one
        taken by hand. A core before this ignores the query and takes an
        ordinary one, as it always did.

        Answered at once, as the row's own action is: the updater watches
        the share for the file, and a backup can outlast the request.
        """
        # Read here, on the loop: the settings store is bound to this thread.
        name = str(self._setting_or_none("device_name") or "gexis")
        directory = backups.DEFAULT_DIR

        def make() -> str:
            backups.update_backup_failed(None, directory)
            made = backups.create(name, directory, automatic=True)
            backups.prune_automatic(made, directory)
            return made

        async def run() -> None:
            try:
                made = await asyncio.to_thread(make)
            except Exception as exc:  # noqa: BLE001 - the updater stops without one
                logger.warning("backup before update: failed: %s", exc)
                # **Said, not waited out** (sofapi, 2026-10-13): the updater
                # watched for a file for two minutes after this had failed.
                await asyncio.to_thread(backups.update_backup_failed, str(exc), directory)
                return
            logger.info("backup before update: %s", made)
            # The Restore row lists the share, as after the row's own backup.
            self._store.bump_settings_revision()

        task = asyncio.ensure_future(run())
        self._backup_tasks.add(task)
        task.add_done_callback(self._backup_tasks.discard)
        return web.json_response({"key": "backup", "before": "update"})

    #: Where a `list` row's items come from - ADR-0044 §1's first open
    #: question, now answered for all three.
    #: How long a scan for share servers is reused (2026-10-18).
    SHARE_SERVERS_S = 60.0
    LIST_SOURCES = ("wifi", "lms_server", "bt_trusted", "restore", "lyrion-server.shares",
                    "lyrion-server.usb_folders")

    async def _list_row(self, request: web.Request):
        """The `list` row named in the path, or a response explaining why
        there is none."""
        if self._settings is None:
            return None, web.json_response({"error": "settings are not wired up"}, status=503)
        key = request.match_info["key"]
        try:
            row = self._settings.row(key)
        except UnknownSetting:
            return None, web.json_response({"error": f"unknown setting {key}"}, status=404)
        if row["type"] != "list":
            return None, web.json_response({"error": f"{key} is not a list"}, status=405)
        if key not in self.LIST_SOURCES:
            # A real list with nothing behind it yet. Empty, not broken.
            return None, web.json_response({"items": []})
        return key, None

    async def _handle_list_items(self, request: web.Request) -> web.Response:
        key, refusal = await self._list_row(request)
        if refusal is not None:
            return refusal
        if key == "wifi":
            if not wifi.available():
                return web.json_response({"items": [], "error": "NetworkManager is not available"})
            return web.json_response({"items": await wifi.scan()})
        if key == "bt_trusted":
            return web.json_response({"items": await self._bluetooth(bluetooth_devices.known)})
        if key == "lyrion-server.usb_folders":
            return web.json_response({"items": await self._usb_items(sheet=True) if self._lyrion_usb else []})
        if key == "lyrion-server.shares":
            if self._lyrion_shares is None:
                return web.json_response({"items": []})
            saved = await self._share_items()
            # `?saved=1`: the shares added, without looking for servers - what
            # a page re-reads after an add or a Forget (sofapi, 2026-10-18:
            # every add waited for a two-second scan).
            if request.query.get("saved") == "1":
                return web.json_response({"items": saved})
            # ADR-0115's scan: the servers announcing themselves, after the
            # shares already added; this device's own left out. **Kept for a
            # minute**: the sheet and the page list them again and again
            # while shares are added; `?fresh=1` looks again now.
            own = {device_name.hostname(), f"{device_name.hostname()}.local", device_name.address() or ""}
            now = time.monotonic()
            cached = self._share_servers
            if cached is not None and now - cached[0] < self.SHARE_SERVERS_S and request.query.get("fresh") != "1":
                found = cached[1]
            else:
                found = await asyncio.to_thread(lyrion_scan.servers, own)
                self._share_servers = (time.monotonic(), found)
            # George, 2026-10-18: the search shows what can be added, not
            # what is: the shares added are on their own tile.
            servers = [{"name": server.name, "bars": None, "state": "found",
                        "meta": f"{server.kind.upper()} · {server.host} · tap to see its shares",
                        "server": {"host": server.host, "kind": server.kind}} for server in found]
            return web.json_response({"items": servers})
        if key == "restore":
            # ADR-0083. Read from the share every time: somebody may have
            # copied one in from another machine since the sheet last opened,
            # which is the whole point of it being a share.
            return web.json_response(
                {"items": [a.to_item() for a in backups.available()]}
            )
        # A found server is shown by its name and carries its address, which
        # is what the setting stores and what choosing it writes (George,
        # 2026-10-16: host names rather than addresses).
        current = str(self._settings.value("lms_server") or "")
        items = []
        own = self._own_server() if self._own_server else None
        if own:
            items.append({"name": device_name.hostname() or own, "address": own,
                          "meta": f"This player's own server · {own}", "bars": None,
                          "state": "current" if own == current else "found"})
        for server in await self._lyrion_found():
            if own and server["address"] == own:
                continue
            name = discovery.label(server)
            meta = " · ".join(part for part in (server["name"] or "Lyrion server", server["version"],
                                                server["address"] if name != server["address"] else "") if part)
            items.append(
                {
                    "name": name,
                    "address": server["address"],
                    "meta": meta,
                    "bars": None,
                    "state": "current" if server["address"] == current else "found",
                }
            )
        return web.json_response({"items": items})

    async def _handle_list_action(self, request: web.Request) -> web.Response:
        key, refusal = await self._list_row(request)
        if refusal is not None:
            return refusal
        try:
            body = await request.json()
            name = body["name"]
            action = body.get("action", "join")
        except (ValueError, KeyError, TypeError):
            return web.json_response({"error": 'body must be {"name": ..., "action": ...}'}, status=400)
        if key == "lyrion-server.usb_folders":
            return await self._usb_action(body, name, action)
        if key == "lyrion-server.shares":
            # ADR-0115: added, or forgotten; the mount follows in the core's
            # loop while the server is on.
            if self._lyrion_shares is None:
                return web.json_response({"ok": False, "error": "shares are not wired up"})
            try:
                # The store on this thread (SQLite, one thread); the unmount,
                # which can take seconds, in a worker.
                if action == "browse":
                    # One server's shares, or a request for a login.
                    target = body.get("server")
                    target = target if isinstance(target, dict) else {}
                    server = lyrion_scan.Server(name=name, host=str(target.get("host") or name),
                                                kind="nfs" if target.get("kind") == "nfs" else "smb")
                    try:
                        found = await asyncio.to_thread(lyrion_scan.shares, server, body.get("user") or None,
                                                        body.get("password") or None)
                    except lyrion_scan.NeedsLogin:
                        return web.json_response({"ok": False, "login": True,
                                                  "error": f"{name} needs a user and password to show its shares"})
                    # A NAS asleep past smbclient's 15 s, or the tool missing:
                    # a sentence on the sheet rather than a 500 (review,
                    # 2026-10-12).
                    except subprocess.TimeoutExpired:
                        return web.json_response({"ok": False, "error": f"{name} did not answer. Is it switched on?"})
                    except (subprocess.SubprocessError, OSError) as exc:
                        logger.warning("lyrion: %s's shares not listed: %s", name, exc)
                        return web.json_response({"ok": False, "error": f"{name}'s shares could not be listed."})
                    # Shares already added are not offered again (George,
                    # 2026-10-18): they took up the list for nothing.
                    added = {a["address"].lower() for a in self._lyrion_shares.all()}
                    return web.json_response({"ok": True, "error": None, "items": [
                        {"name": lyrion_shares.label(s["address"])[0], "meta": s["comment"] or None,
                         "bars": None, "state": "found", "share": True, "address": s["address"]}
                        for s in found if s["address"].lower() not in added]})
                if action == "folders":
                    # George, 2026-10-18: a share opens into its folders, at
                    # any depth, as a USB drive does. SMB only: listing an
                    # NFS export would mean mounting it.
                    address = name.rstrip("/")
                    shown, server = lyrion_shares.label(address)
                    items, crumbs = [], [{"name": server, "server": True}]
                    if address.startswith("//"):
                        host, share, *path = address[2:].split("/")
                        crumbs += [{"name": share, "address": f"//{host}/{share}"}] + [
                            {"name": part, "address": f"//{host}/{share}/" + "/".join(path[:i + 1])}
                            for i, part in enumerate(path)]
                        try:
                            found = await asyncio.to_thread(lyrion_scan.folders, address, body.get("user") or None,
                                                            body.get("password") or None)
                        except lyrion_scan.NeedsLogin:
                            return web.json_response({"ok": False, "login": True,
                                                      "error": f"{server} needs a user and password to show its folders"})
                        except (lyrion_scan.NoAnswer, subprocess.TimeoutExpired):
                            return web.json_response({"ok": False, "error": f"{server} did not answer. Is it switched on?"})
                        items = [{"name": f, "meta": "", "bars": None, "state": "found", "share": True,
                                  "open": True, "address": f"{address}/{f}"} for f in found]
                    else:
                        crumbs.append({"name": shown, "address": address})
                    return web.json_response({"ok": True, "error": None, "items": items, "crumbs": crumbs,
                                              "title": " / ".join(c["name"] for c in crumbs)})
                if action == "add":
                    self._lyrion_shares.add(name, body.get("user"), body.get("password"))
                elif action == "forget":
                    self._lyrion_shares.forget(name)
                    await asyncio.to_thread(self._lyrion_shares.release, name)
                else:
                    return web.json_response({"error": f"unknown action {action}"}, status=400)
            except ValueError as exc:
                return web.json_response({"ok": False, "error": f"Needs {exc}"})
            if self._lyrion_shares_changed is not None:
                self._lyrion_shares_changed()
            return web.json_response({"ok": True, "error": None})
        if key == "bt_trusted":
            if action != "forget":
                return web.json_response({"error": f"unknown action {action}"}, status=400)
            ok, error = await self._bluetooth(bluetooth_devices.forget, name)
            return web.json_response({"ok": ok, "error": error})
        if key == "restore":
            # **ADR-0083: this one reboots.** The answer goes out first and
            # the reboot is scheduled behind it, or the panel would be told
            # nothing and left looking stuck through the restart.
            if action == "forget":
                try:
                    await asyncio.to_thread(backups.forget, name)
                except (OSError, ValueError) as exc:
                    return web.json_response({"ok": False, "error": str(exc)})
                return web.json_response({"ok": True, "error": None})
            if action != "join":
                return web.json_response({"error": f"unknown action {action}"}, status=400)
            if self._restore is None:
                return web.json_response({"ok": False, "error": "restoring is not wired up"})
            try:
                await asyncio.to_thread(backups.restore, name)
            # EOFError and zlib.error: a backup cut short - half-copied into
            # the Backups share - which tarfile reads that far and no further.
            except (OSError, ValueError, tarfile.TarError, EOFError, zlib.error) as exc:
                logger.warning("restore: %s failed: %s", name, exc)
                return web.json_response({"ok": False, "error": str(exc)})
            # The backup's name, in all four places, before the reboot reads
            # them (device_name.apply_restored).
            written = await asyncio.to_thread(device_name.apply_restored)
            if written is not None:
                logger.info("restore: device name applied everywhere (%s)", written.hostname)
            asyncio.ensure_future(self._restore())
            return web.json_response({"ok": True, "error": None})
        if key != "wifi":
            return web.json_response({"error": f"{key} has no per-item action"}, status=405)
        if not wifi.available():
            return web.json_response({"error": "NetworkManager is not available"}, status=503)
        if action == "forget":
            ok, error = await wifi.forget(name)
        elif action == "join":
            ok, error = await wifi.join(name, body.get("password") or None)
        else:
            return web.json_response({"error": f"unknown action {action}"}, status=400)
        # A refused password is not a broken request: the answer is 200 with
        # the reason, because the sheet shows it and offers to try again.
        answer = {"ok": ok, "error": error}
        if ok and action == "join":
            from gexis_core import wired

            if wired.has_port() and wired.link()[0]:
                # ADR-0123 as amended: the cable wins - the join proved the
                # password, and the network waits for the cable to go.
                answer["notice"] = wired.CABLE_IN_USE
        return web.json_response(answer)

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
        except Locked as exc:
            # 409 as well: the row exists and is settable in general, but
            # not while the hardware has taken the choice away (ADR-0055).
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
        app = web.Application(middlewares=[self._note_setup_use])
        app.router.add_get("/state", self._handle)
        app.router.add_post("/renderer/{renderer_id}/activate", self._handle_activate)
        app.router.add_post("/transport/{command}", self._handle_transport)
        app.router.add_post("/volume", self._handle_set_volume)
        app.router.add_post("/volume/mute", self._handle_set_mute)
        app.router.add_get("/idle", self._handle_idle)
        app.router.add_get("/idle/weather", self._handle_idle_weather)
        app.router.add_get("/idle/wallpaper", self._handle_idle_wallpaper)
        # `{name:.*}` because a picture may be in a folder; `local_path`
        # is what refuses anything that resolves outside the directory.
        app.router.add_get("/idle/wallpaper/local/{name:.*}", self._handle_local_wallpaper)
        app.router.add_get("/idle/wallpaper/own/{name:.*}", self._handle_own_wallpaper)
        app.router.add_get("/idle/wallpaper/{name}", self._handle_wallpaper_file)
        app.router.add_get("/surface", self._handle_surface)
        app.router.add_get("/touchpad", self._handle_touchpad)
        app.router.add_post("/touch", self._handle_touch)
        app.router.add_post("/panel/painted", self._handle_painted)
        app.router.add_post("/screen/{action}", self._handle_screen_answer)
        app.router.add_post("/screen-new/{action}", self._handle_screen_new)
        app.router.add_get("/setup/status", self._handle_setup_status)
        app.router.add_post("/renderers/park", self._handle_park)
        app.router.add_post("/plugins/upload", self._handle_plugin_upload)
        app.router.add_post("/plugins/{id}/uninstall", self._handle_plugin_uninstall)
        app.router.add_get("/setup/answers", self._handle_setup_answers)
        app.router.add_post("/setup/answers", self._handle_setup_save)
        app.router.add_get("/setup/networks", self._handle_setup_networks)
        app.router.add_get("/setup/screen", self._handle_setup_screen)
        app.router.add_post("/setup/finish", self._handle_setup_finish)
        app.router.add_get("/storage/music", self._handle_music_space)
        app.router.add_post("/setup/backup", self._handle_setup_backup)
        app.router.add_delete("/setup/backup", self._handle_setup_backup_forget)
        app.router.add_get("/setup/plugins", self._handle_setup_plugins)
        app.router.add_get("/setup/outputs", self._handle_setup_outputs)
        app.router.add_get("/personalise", self._handle_personalise)
        app.router.add_post("/personalise/finish", self._handle_personalise_finish)
        app.router.add_post("/personalise/later", self._handle_personalise_later)
        app.router.add_post("/settling/done", self._handle_settling_done)
        app.router.add_post("/settling/hide", self._handle_settling_hide)
        # ADR-0101: the phone's idle toggle, and the panel saying what it shows.
        app.router.add_post("/panel/idle/{action}", self._handle_idle_request)
        app.router.add_post("/panel/standby/{action}", self._handle_standby)
        app.router.add_get("/panel/dashboard", self._handle_dashboard)
        app.router.add_post("/panel/dashboard/{action}", self._handle_dashboard_request)
        app.router.add_post("/panel/input", self._handle_panel_input)
        app.router.add_get("/player/status", self._handle_player_status)
        app.router.add_get("/players", self._handle_players)
        app.router.add_get("/group", self._handle_group)
        app.router.add_post("/group/record", self._handle_group_record)
        app.router.add_post("/group/join", self._handle_group_change)
        app.router.add_post("/group/remove", self._handle_group_change)
        app.router.add_post("/group/leave", self._handle_group_change)
        app.router.add_post("/group/undo", self._handle_group_change)
        app.router.add_post("/group/enter", self._handle_group_enter)
        app.router.add_post("/group/volume", self._handle_group_volume)
        app.router.add_post("/group/mute", self._handle_group_mute)
        app.router.add_post("/group/members/{id}/volume", self._handle_group_member_volume)
        app.router.add_post("/group/members/{id}/mute", self._handle_group_member_mute)
        app.router.add_post("/panel/shown", self._handle_panel_shown)
        app.router.add_post("/panel/go/{to}", self._handle_view_request)
        app.router.add_post("/panel/key", self._handle_panel_key)
        app.router.add_get("/equaliser", self._handle_equaliser)
        app.router.add_put("/equaliser", self._handle_equaliser_set)
        app.router.add_post("/equaliser/settings", self._handle_equaliser_save)
        app.router.add_put("/equaliser/settings/{key}", self._handle_equaliser_rename)
        app.router.add_delete("/equaliser/settings/{key}", self._handle_equaliser_delete)
        app.router.add_post("/peppy/{action}", self._handle_peppy)
        app.router.add_get("/settings", self._handle_settings)
        app.router.add_get("/notices/{name}", self._handle_notice)
        app.router.add_put("/settings/{key}", self._handle_setting_write)
        app.router.add_post("/settings/{key}", self._handle_setting_action)
        app.router.add_get("/settings/{key}/items", self._handle_list_items)
        app.router.add_get("/network/wifi", self._handle_wifi_details)
        app.router.add_post("/report", self._handle_report)
        app.router.add_post("/report/prepare", self._handle_report_prepare)
        app.router.add_get("/report/status", self._handle_report_status)
        app.router.add_get("/report/file", self._handle_report_file)
        app.router.add_get("/report/issue", self._handle_report_issue)
        app.router.add_get("/backups/{name}", self._handle_backup_download)
        app.router.add_post("/backups", self._handle_backup_upload)
        app.router.add_get("/network/cable", self._handle_cable)
        app.router.add_post("/network/cable", self._handle_cable_change)
        app.router.add_get("/network/wifi/address", self._handle_cable)
        app.router.add_post("/network/wifi/address", self._handle_cable_change)
        app.router.add_post("/network/keep", self._handle_cable_keep)
        app.router.add_get("/hardware-report", self._handle_hardware_report)
        app.router.add_post("/hardware-report/issue", self._handle_hardware_issue)
        app.router.add_post("/hardware-report/tones", self._handle_hardware_tones)
        app.router.add_get("/hardware-report/prompt", self._handle_hardware_prompt)
        app.router.add_get("/hardware-report/kept", self._handle_hardware_kept)
        app.router.add_post("/hardware-report/kept/clear", self._handle_hardware_kept_clear)
        app.router.add_get("/hardware-report/file", self._handle_hardware_file)
        app.router.add_post("/hardware-report/prompt/dismiss", self._handle_hardware_prompt_dismiss)
        app.router.add_post("/hardware-report/screen", self._handle_hardware_screen)
        app.router.add_post("/hardware-report/screen/result", self._handle_hardware_screen_result)
        app.router.add_post("/settings/{key}/items", self._handle_list_action)
        app.router.add_post("/bluetooth/pairing/{answer}", self._handle_pairing_answer)
        # ADR-0050. `{name:.*}` because a skin's name is a section heading
        # somebody typed, spaces and punctuation included.
        app.router.add_get("/skins", self._handle_skins)
        app.router.add_get("/skins/{name:.*}/preview", self._handle_skin_preview)
        app.router.add_get("/plugins/{id}/mark", self._handle_plugin_mark)
        app.router.add_get("/plugins/{id}/artwork/{key}", self._handle_plugin_artwork)
        app.router.add_get("/menus", self._handle_menus)
        app.router.add_get("/menus/browse", self._handle_menus_browse)
        app.router.add_get("/menus/letters", self._handle_menus_letters)
        app.router.add_post("/menus/act", self._handle_menus_act)
        app.router.add_post("/menus/search", self._handle_menus_search)
        app.router.add_get("/radio", self._handle_radio)
        app.router.add_post("/radio/play", self._handle_radio_play)
        app.router.add_get("/library/artist-photos", self._handle_artist_photos)
        app.router.add_get("/library/artist-info", self._handle_artist_info)
        app.router.add_get("/enrichment", self._handle_enrichment)
        app.router.add_post("/library/action", self._handle_library_action)
        app.router.add_get("/library/{what}", self._handle_library)
        app.router.add_get("/library/{what}/{id}", self._handle_library)
        app.router.add_get("/library/{what}/{id}/{sub}", self._handle_library)
        # ADR-0152: the API's own page, while API explorer is on.
        app.router.add_get("/api", self._handle_api_page)
        app.router.add_get("/api/", self._handle_api_page)
        app.router.add_get("/api/openapi.json", self._handle_api_description)
        app.router.add_get("/api/swagger-ui/{file}", self._handle_api_asset)
        # The UI is registered *after* the API, so nothing it serves can
        # shadow `/state` or a command route - aiohttp resolves in
        # registration order. Two routes only, which is why vite is
        # configured to emit everything under assets/: a greedy catch-all
        # would put that ordering guarantee back in play every time a
        # route is added.
        if self._ui_dir is not None:
            app.router.add_get("/", self._handle_index)
            app.router.add_static("/assets", self._ui_dir / "assets")
            # ADR-0102 (a test): what a phone reads to install Settings as an
            # app. Named one by one, for the reason above.
            for name in APP_FILES:
                app.router.add_get(f"/{name}", self._handle_app_file)
        return app

    # --- ADR-0152: the API, described and tried -------------------------

    def _api_shown(self) -> bool:
        """*API explorer* (System, after Debug logs), read at each request;
        off, the page and its files are not there - the API itself is the
        same either way."""
        return self._setting_or_none("api_explorer") is True

    async def _handle_api_page(self, request: web.Request) -> web.StreamResponse:
        if not self._api_shown():
            return web.json_response({"error": "the API explorer is off (Settings -> System)"}, status=404)
        if request.path == "/api":
            # The page's links are relative to /api/.
            raise web.HTTPFound("/api/")
        return web.FileResponse(API_DIR / "index.html", headers={"Cache-Control": "no-cache"})

    async def _handle_api_description(self, request: web.Request) -> web.Response:
        """The file as it ships, naming the release this player runs."""
        if not self._api_shown():
            return web.json_response({"error": "the API explorer is off (Settings -> System)"}, status=404)
        spec = json.loads(await asyncio.to_thread((API_DIR / "openapi.json").read_text))
        release = await asyncio.to_thread(updates.installed_release)
        if release:
            spec["info"]["version"] = release
        return web.json_response(spec, headers={"Cache-Control": "no-cache"})

    async def _handle_api_asset(self, request: web.Request) -> web.StreamResponse:
        """Swagger UI's files, by name from its own folder only."""
        if not self._api_shown():
            return web.json_response({"error": "the API explorer is off (Settings -> System)"}, status=404)
        name = request.match_info["file"]
        if name not in API_ASSETS:
            return web.json_response({"error": "no such file"}, status=404)
        return web.FileResponse(API_DIR / "swagger-ui" / name, headers={"Content-Type": API_ASSETS[name]})

    async def _handle_app_file(self, request: web.Request) -> web.FileResponse:
        name = request.path.lstrip("/")
        return web.FileResponse(self._ui_dir / name, headers={"Content-Type": APP_FILES[name]})

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
