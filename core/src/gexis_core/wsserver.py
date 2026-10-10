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
import json
import logging
import os
import random
import tarfile
import threading
import time
from collections.abc import Callable
from urllib.parse import quote, unquote
from pathlib import Path

import aiohttp
from aiohttp import web
from dbus_next import BusType
from dbus_next.aio import MessageBus

from gexis_core import own_wallpapers
from gexis_core import backups, bluetooth_devices, skin_packs, device_name, discovery, hardware_report, lyrion_scan, lyrion_shares, problem_report, skin_previews, skins, wifi
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
        on_painted=None,
        upload_plugin=None,
        uninstall_plugin=None,
        weather=None,
        wallpapers=None,
        own=None,
        space=None,
        skins_at: Callable[[], tuple[Path, str] | None] | None = None,
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
        #: **ADR-0083.** Called after an archive has been written back, to
        #: reboot. Injected rather than imported so the route stays a route:
        #: the daemon owns what "restart the device" means, and a test can
        #: watch it without one.
        self._restore = restore
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
        #: ADR-0115: the Lyrion server's network shares.
        self._lyrion_shares = lyrion_shares
        self._lyrion_shares_changed = lyrion_shares_changed
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
        #: ADR-0133: Space pictures downloaded from NASA and ESA.
        self._space = space
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
        self._last_background: str | None = None
        self._ui_dir = ui_dir
        self._clients: set[web.WebSocketResponse] = set()
        store.subscribe(self._broadcast)
        #: ADR-0121: the touchpad's own socket, the panel's (loopback) and the
        #: phones' apart. `/state` stays publish-only (ADR-0028).
        self._pad_panels: set[web.WebSocketResponse] = set()
        self._pad_phones: set[web.WebSocketResponse] = set()

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
    PAD_FROM_PANEL = frozenset({"over", "focus"})
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
                if not self._touchpad_on():
                    continue
                try:
                    kind = json.loads(msg.data).get("t")
                except (ValueError, AttributeError):
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

    @staticmethod
    def _from_panel(request: web.Request) -> bool:
        """The panel arrives on loopback, a phone from the LAN (ADR-0035 §6)."""
        return request.remote in ("127.0.0.1", "::1")

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
        if self._wallpapers is None and self._settings.value("idle_background") in (
                "Wallpapers online", "Wallpapers on device"):
            return web.json_response({"error": "wallpapers are not wired up"}, status=503)
        screen = _screen_size(request)
        answer = await self._next_background()
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
            answer = await self._next_background()
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
        if url.startswith("/idle/wallpaper/space/"):
            path = self._space.path_of(url[len("/idle/wallpaper/space/"):]) if self._space else None
        elif url.startswith("/idle/wallpaper/own/"):
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

    async def _next_background(self) -> dict:
        """The next background, whatever `idle_background` says it is.

        **One route for four sources**, so the panel asks for "the next
        picture" and does not carry a branch per setting: the setting is the
        daemon's to read, and three of the four answers are things only the
        daemon can reach anyway. *When* the picture changes is the panel
        counting `background_interval`; nothing here holds a timer.
        """
        background = self._settings.value("idle_background") or "Gexis wallpapers"
        if background == "Black":
            return {"off": True, "error": None}
        # ADR-0133 §2: artist pictures come from the library, which is not
        # there while the LMS client is off; the player's own show instead.
        if background == "Artist pictures" and self._settings.value("lms_enabled") is False:
            background = "Gexis wallpapers"
        if background == "Artist pictures":
            return await self._artist_picture()
        if background in ("Gexis wallpapers", "Space pictures"):
            return await self._own_picture(background)
        if background == "Wallpapers on device":
            # None twice until every one has been shown, and never the one
            # already on screen when there is another (ADR-0047 §2e).
            name = self._wallpapers.next_local(avoid=self._last_background)
            if name is None:
                return {"error": "No pictures on this device yet."}
            self._last_background = name
            # **Quoted**: a name can now carry folders, spaces and anything
            # else a person types, and it travels as a URL.
            return {"url": f"/idle/wallpaper/local/{quote(name)}", "by": "", "page": "",
                    "credit": None, "error": None}
        key = str(self._settings.value("wallpaper_key") or "").strip()
        topics = self._settings.value("wallpaper_topics") or []
        # A bar asks for wide pictures (George, 2026-10-04).
        bar = skin_packs.family(*skin_packs.screen_size()) == "bar"
        answer = await self._wallpapers.next(key, list(topics), avoid=self._last_background, wide=bar)
        if answer.get("file"):
            self._last_background = answer["file"]
            answer = {**answer, "url": f"/idle/wallpaper/{answer['file']}"}
        return answer

    async def _own_picture(self, background: str) -> dict:
        """**ADR-0133.** The next of the player's own pictures. Space
        pictures are their built-in set; Gexis wallpapers are chosen by the
        style, hour, season and holiday rows (`own_wallpapers.active_sets`)."""
        if background == "Space pictures":
            # Downloaded ones first; the built-in set until one has arrived.
            if self._space is not None:
                answer = await self._space.next(avoid=self._last_background)
                if answer is not None:
                    self._last_background = answer["file"]
                    return answer
            sets = [own_wallpapers.SPACE]
        else:
            country, latitude = await self._where()
            value = self._settings.value
            styles = value("wallpaper_styles")
            sets = own_wallpapers.active_sets(
                datetime.datetime.now(),
                styles=list(styles) if isinstance(styles, list) else ["Calm"],
                time_of_day_on=value("wallpaper_time_of_day") is not False,
                seasons_on=value("wallpaper_seasons") is not False,
                holidays_on=value("wallpaper_holidays") is not False,
                country=country, latitude=latitude)
        answer = self._own.next(sets, avoid=self._last_background)
        if answer is None:
            return {"error": "The player's own pictures are not installed."}
        self._last_background = answer["file"]
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
        items = [a for a in items if a.get("name") != self._last_background] or items
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
                self._last_background = artist.get("name") or ""
                return {"url": url, "by": artist.get("name") or "", "page": "",
                        "credit": None, "source": source, "error": None}

        photos = await self._artistinfo.photos([a["id"] for a in picked], PHOTO_BACKGROUND)
        with_photos = [(a, photos.get(a["id"])) for a in picked if photos.get(a["id"])]
        if not with_photos:
            return {"error": "No artist pictures for these artists."}
        artist, url = random.choice(with_photos)
        self._last_background = artist.get("name") or ""
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

    async def _handle_space_wallpaper(self, request: web.Request) -> web.StreamResponse:
        """One downloaded Space picture (ADR-0133): a name it handed out."""
        path = self._space.path_of(request.match_info["name"]) if self._space else None
        if path is None:
            return web.json_response({"error": "no such picture"}, status=404)
        return web.FileResponse(path)

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
        wanted = skins.CORPUS.get(chosen) or skins.CORPUS[skins.ALL]
        items = [
            {
                "name": skin.name,
                "kind": skin.kind,
                "in_corpus": skin.kind in wanted,
                "preview": f"/skins/{quote(skin.name)}/preview",
            }
            for skin, _ in self._skins()
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
        if other is not None and other.pending is not None:
            return web.json_response({"error": "Another address change is waiting to be kept. Keep it, or wait for "
                                               "it to go back."}, status=409)
        try:
            body = await request.json()
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
        loopback = request.remote in ("127.0.0.1", "::1")
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
        try:
            path = backups.path_of(request.match_info["name"])
        except ValueError:
            return web.json_response({"error": "not a backup"}, status=400)
        except FileNotFoundError:
            return web.json_response({"error": "That backup is not on the player any more."}, status=404)
        return web.FileResponse(path, headers={
            "Content-Disposition": f'attachment; filename="{path.name}"',
            "Content-Type": "application/gzip",
            "Cache-Control": "no-store",
        })

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
        note = str((body or {}).get("note") or "")[:4000]
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
            return hardware_report.collect(
                output.card if output and output.card not in outputs.BUILT_IN_CARDS else None,
                chosen_board=written.id if written else None,
                screen_chosen=screen,
            )

        return await asyncio.get_running_loop().run_in_executor(None, gather)

    async def _handle_hardware_report(self, request: web.Request) -> web.Response:
        """ADR-0126: the facts a hardware report carries, for the sheet to show
        before anything is sent."""
        facts = await self._hardware_facts()
        headless = bool(self._settings.value("headless")) if self._settings else False
        return web.json_response({
            # George, 2026-10-07: the screen step only when there is a screen
            # to look at - not headless, and one connected.
            "display": facts.screen_connected and not headless,
            "board": facts.board or facts.card or None,
            "state": facts.state,
            "screen": facts.screen_chosen or (f"{facts.edid_maker or ''} {facts.edid_name or ''}".strip() or None),
            "touch": bool(facts.touch),
            "text": facts.text(),
        })

    async def _handle_hardware_tones(self, request: web.Request) -> web.Response:
        """ADR-0126: a tone at 44.1, 96 and 192 kHz through the player's own
        output, and what the card ran at - **only when nothing is playing**:
        a test never cuts into music."""
        from gexis_core import outputs
        if hardware_report.playing():
            return web.json_response({"error": "Something is playing. Pause it first, then play the tones."},
                                     status=409)
        output = outputs.resolve(self._settings.value("output_device")) if self._settings else None
        if output is None:
            return web.json_response({"error": "No output to play to."}, status=409)
        results = await asyncio.get_running_loop().run_in_executor(
            None, lambda: hardware_report.play_tones(output.card))
        return web.json_response({"tones": results})

    async def _handle_hardware_issue(self, request: web.Request) -> web.Response:
        """ADR-0126: the issue form's address, pre-filled with the facts and
        the owner's answers `{"answers": {...}, "notes": "..."}`."""
        try:
            body = await request.json() if request.can_read_body else {}
        except ValueError:
            body = {}
        answers = {k: str(v) for k, v in (body.get("answers") or {}).items()}
        notes = str(body.get("notes") or "")[:2000]
        tones = [str(t) for t in (body.get("tones") or [])][:6]
        check = self._store.state.screen_check or {}
        screen = hardware_report.screen_lines(check["result"]) if check.get("result") else None
        facts = await self._hardware_facts()
        url = hardware_report.issue_url(facts, answers, notes, tones, screen)
        # A report prepared is the prompt answered: it is not asked again.
        if self._settings is not None:
            await self._dismiss_hardware_prompt()
        return web.json_response({"url": url})

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
        check = dict(self._store.state.screen_check or {})
        if not body.get("show"):
            if check:
                self._store.set_screen_check({**check, "showing": False})
            return web.json_response({"ok": True})
        touch = bool(await asyncio.get_running_loop().run_in_executor(None, hardware_report._touch))
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
        except (ValueError, KeyError, TypeError):
            return web.json_response({"error": "bad taps"}, status=400)
        self._store.set_screen_check({**check, "showing": False, "result": result})
        return web.json_response(result)

    async def _handle_panel_shown(self, request: web.Request) -> web.Response:
        """ADR-0101: the panel reporting whether its idle screen is up - and,
        as amended, whether its lyrics are - so the phone's toggles say what
        the panel shows, whatever changed it."""
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
        panel = request.remote in ("127.0.0.1", "::1")
        return web.json_response(self._setup.status() if panel else self._setup.public_status())

    @staticmethod
    def _setup_error(raw: str, status: int) -> web.Response:
        """A setup error as the phone shows it - a sentence - with the
        core's own text in the log (setup_flow.said)."""
        from gexis_core import setup_flow

        logger.info("setup: answered %s: %s", status, raw)
        return web.json_response({"error": setup_flow.said(raw)}, status=status)

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
        if request.remote not in ("127.0.0.1", "::1"):
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
        return web.json_response(setup_flow.screen_choices(report))

    async def _handle_setup_plugins(self, request: web.Request) -> web.Response:
        """ADR-0128: the Plugins step - every plugin the release ships, with
        what it is, where it downloads from, and its notice."""
        closed = self._setup_closed()
        if closed is not None:
            return closed
        offered = self._setup_flow.offered()
        return web.json_response([{k: p.get(k) for k in ("id", "name", "summary", "notice", "from", "component")}
                                  for p in offered])

    async def _handle_settling_done(self, request: web.Request) -> web.Response:
        """ADR-0128: the owner's OK on a settling screen that names a
        download that did not finish."""
        if self._settling_done is None:
            return web.json_response({"error": "not wired up"}, status=503)
        self._settling_done()
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
        if self._on_painted is not None and request.remote in ("127.0.0.1", "::1"):
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
        panel's Chromium is on this device; a phone is not."""
        if request.remote not in ("127.0.0.1", "::1"):
            return web.json_response({"error": "only the panel answers this"}, status=403)
        action = request.match_info["action"]
        if action not in ("keep", "revert") or self._screen_answer is None:
            return web.json_response({"error": f"unknown answer {action}"}, status=404)
        return web.json_response(await self._screen_answer(action))

    async def _handle_peppy(self, request: web.Request) -> web.Response:
        action = request.match_info["action"]
        if self._peppy is None:
            return web.json_response({"error": "the Peppy screen is not wired up"}, status=503)
        if action not in ("show", "hide"):
            return web.json_response({"error": f"unknown action {action}"}, status=404)
        shown = self._peppy.request(action)
        if not shown and action == "show" and self._peppy._has_levels():
            shown = await self._peppy_again()
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
            if await asyncio.to_thread(self._peppy.request, "show"):
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
                    row["items"] = self._lyrion_shares.items() if self._lyrion_shares else []
                    continue
                source = self.SEEDED_LISTS.get(key)
                if source is None:
                    continue
                module, name = source
                # `_bluetooth` answers [] for an adapter that is not there,
                # so an unavailable BlueZ reads as the row's own empty state
                # rather than failing the whole settings payload.
                row["items"] = await self._bluetooth(getattr(module, name))

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
        response = self._settings_call(lambda: {"key": key, "value": self._settings.set(key, value)})
        if (response.status == 200 and self._restart_device is not None
                and self._settings_restarts(key) and self._settings_value(key) != before):
            asyncio.ensure_future(self._restart_device(key))
        return response

    def _settings_value(self, key: str):
        try:
            return self._settings.value(key)
        except Exception:  # noqa: BLE001 - the write below says what is wrong
            return None

    def _settings_restarts(self, key: str) -> bool:
        try:
            return bool(self._settings.row(key).get("restart"))
        except Exception:  # noqa: BLE001
            return False

    async def _handle_setting_action(self, request: web.Request) -> web.Response:
        if self._settings is None:
            return web.json_response({"error": "settings are not wired up"}, status=503)
        key = request.match_info["key"]

        def run():
            self._settings.run(key)
            return {"key": key}

        return self._settings_call(run)

    #: Where a `list` row's items come from - ADR-0044 §1's first open
    #: question, now answered for all three.
    LIST_SOURCES = ("wifi", "lms_server", "bt_trusted", "restore", "lyrion-server.shares")

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
        if key == "lyrion-server.shares":
            if self._lyrion_shares is None:
                return web.json_response({"items": []})
            # On this thread: it reads the settings store (SQLite, one thread).
            saved = self._lyrion_shares.items()
            # ADR-0115's scan: the servers announcing themselves, after the
            # shares already added; this device's own left out.
            own = {device_name.hostname(), f"{device_name.hostname()}.local", device_name.address() or ""}
            found = await asyncio.to_thread(lyrion_scan.servers, own)
            for server in found:
                saved.append({"name": server.name, "bars": None, "state": "found",
                              "meta": f"{server.kind.upper()} · {server.host} · tap to see its shares",
                              "server": {"host": server.host, "kind": server.kind}})
            return web.json_response({"items": saved})
        if key == "restore":
            # ADR-0083. Read from the share every time: somebody may have
            # copied one in from another machine since the sheet last opened,
            # which is the whole point of it being a share.
            return web.json_response(
                {"items": [a.to_item() for a in backups.available()]}
            )
        # A discovered server is named by its address, because that is what
        # the setting stores; the human name is the line underneath.
        current = str(self._settings.value("lms_server") or "")
        items = []
        own = self._own_server() if self._own_server else None
        if own:
            items.append({"name": own, "meta": "This player's own server", "bars": None,
                          "state": "current" if own == current else "found"})
        for server in await discovery.find_servers():
            if own and server["address"] == own:
                continue
            meta = " · ".join(part for part in (server["name"], server["version"]) if part)
            items.append(
                {
                    "name": server["address"],
                    "meta": meta or "Lyrion server",
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
                    target = body.get("server") or {}
                    server = lyrion_scan.Server(name=name, host=str(target.get("host") or name),
                                                kind="nfs" if target.get("kind") == "nfs" else "smb")
                    try:
                        found = await asyncio.to_thread(lyrion_scan.shares, server, body.get("user") or None,
                                                        body.get("password") or None)
                    except lyrion_scan.NeedsLogin:
                        return web.json_response({"ok": False, "login": True,
                                                  "error": f"{name} needs a user and password to show its shares"})
                    return web.json_response({"ok": True, "error": None, "items": [
                        {"name": lyrion_shares.label(s["address"])[0], "meta": s["comment"] or None,
                         "bars": None, "state": "found", "share": True, "address": s["address"]}
                        for s in found]})
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
            except (OSError, ValueError, tarfile.TarError) as exc:
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
        app = web.Application()
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
        app.router.add_get("/idle/wallpaper/space/{name}", self._handle_space_wallpaper)
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
        app.router.add_post("/setup/backup", self._handle_setup_backup)
        app.router.add_delete("/setup/backup", self._handle_setup_backup_forget)
        app.router.add_get("/setup/plugins", self._handle_setup_plugins)
        app.router.add_post("/settling/done", self._handle_settling_done)
        # ADR-0101: the phone's idle toggle, and the panel saying what it shows.
        app.router.add_post("/panel/idle/{action}", self._handle_idle_request)
        app.router.add_post("/panel/shown", self._handle_panel_shown)
        app.router.add_post("/panel/go/{to}", self._handle_view_request)
        app.router.add_post("/peppy/{action}", self._handle_peppy)
        app.router.add_get("/settings", self._handle_settings)
        app.router.add_get("/notices/{name}", self._handle_notice)
        app.router.add_put("/settings/{key}", self._handle_setting_write)
        app.router.add_post("/settings/{key}", self._handle_setting_action)
        app.router.add_get("/settings/{key}/items", self._handle_list_items)
        app.router.add_get("/network/wifi", self._handle_wifi_details)
        app.router.add_post("/report", self._handle_report)
        app.router.add_get("/backups/{name}", self._handle_backup_download)
        app.router.add_get("/network/cable", self._handle_cable)
        app.router.add_post("/network/cable", self._handle_cable_change)
        app.router.add_get("/network/wifi/address", self._handle_cable)
        app.router.add_post("/network/wifi/address", self._handle_cable_change)
        app.router.add_post("/network/keep", self._handle_cable_keep)
        app.router.add_get("/hardware-report", self._handle_hardware_report)
        app.router.add_post("/hardware-report/issue", self._handle_hardware_issue)
        app.router.add_post("/hardware-report/tones", self._handle_hardware_tones)
        app.router.add_get("/hardware-report/prompt", self._handle_hardware_prompt)
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
