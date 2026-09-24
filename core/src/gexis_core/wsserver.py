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
import random
from urllib.parse import quote
from pathlib import Path

from aiohttp import web
from dbus_next import BusType
from dbus_next.aio import MessageBus

from gexis_core import bluetooth_devices, device_name, discovery, skins, wifi
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

from gexis_core.enrichment import Enrichment, TrackKey, fold
from gexis_core.library import LibraryUnavailable, NoPlayer, NotFound
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
        notes=None,
        enrichment=None,
        radio=None,
        pairing_answer=None,
        splash=None,
        weather=None,
        wallpapers=None,
        skins_dir: Path | None = None,
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
        self._pairing_answer = pairing_answer
        self._splash = splash
        self._weather = weather
        self._wallpapers = wallpapers
        #: Where the skin packs live (ADR-0050). Read per request rather
        #: than at start: a pack could be added under a running daemon, and
        #: parsing 99 sections costs less than the request that asked.
        self._skins_dir = Path(skins_dir) if skins_dir else None
        #: What the idle screen is showing, so the next change is a change.
        #: One value for three sources, because only one of them is on
        #: screen at a time: a file name, a Pixabay id, or an artist.
        self._last_background: str | None = None
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
        # **Both need today**: the None layout still draws the current
        # conditions with today's high and low, so the fetch is one day
        # rather than none.
        forecast = str(self._settings.value("idle_forecast") or "3 days")
        days = 3 if forecast == "3 days" else 1
        answer = await self._weather.forecast(place, days)
        return web.json_response({**answer, "forecast": forecast})

    async def _handle_idle_wallpaper(self, request: web.Request) -> web.Response:
        """The next background, whatever `idle_background` says it is.

        **One route for four sources**, so the panel asks for "the next
        picture" and does not carry a branch per setting: the setting is the
        daemon's to read, and three of the four answers are things only the
        daemon can reach anyway. *When* the picture changes is the panel
        counting `background_interval`; nothing here holds a timer.
        """
        if self._settings is None or self._wallpapers is None:
            return web.json_response({"error": "wallpapers are not wired up"}, status=503)
        background = self._settings.value("idle_background") or "Artist pictures"
        if background == "Black":
            return web.json_response({"off": True, "error": None})
        if background == "Artist pictures":
            return web.json_response(await self._artist_picture())
        if background == "Wallpapers on device":
            names = self._wallpapers.local_names()
            if not names:
                return web.json_response({"error": "No pictures on this device yet."})
            # Not the one already on screen, when there is another. A folder
            # of four and a fifteen-minute rotation would otherwise repeat
            # about one change in four, which reads as the screen being stuck.
            choices = [n for n in names if n != self._last_background] or names
            name = random.choice(choices)
            self._last_background = name
            # **Quoted**: a name can now carry folders, spaces and anything
            # else a person types, and it travels as a URL.
            return web.json_response(
                {"url": f"/idle/wallpaper/local/{quote(name)}", "by": "", "page": "",
                 "credit": None, "error": None}
            )
        key = str(self._settings.value("wallpaper_key") or "").strip()
        topics = self._settings.value("wallpaper_topics") or []
        answer = await self._wallpapers.next(key, list(topics), avoid=self._last_background)
        if answer.get("file"):
            self._last_background = answer["file"]
            answer = {**answer, "url": f"/idle/wallpaper/{answer['file']}"}
        return web.json_response(answer)

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
            url = await self._fanart_background(artist.get("name") or "")
            if url:
                self._last_background = artist.get("name") or ""
                return {"url": url, "by": artist.get("name") or "", "page": "",
                        "credit": None, "source": "fanart", "error": None}

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

    async def _fanart_background(self, name: str) -> str | None:
        """fanart's wide picture for this artist, or None.

        None covers every way this can come to nothing - no key, no
        MusicBrainz id, no image for that id - because the caller does the
        same thing in all of them: try another artist, then fall back.
        """
        if not name or self._enrichment is None:
            return None
        try:
            found = await self._enrichment.for_track(
                TrackKey(artist=fold(name)), only=("fanart-bg",)
            )
        except Exception as exc:
            logger.info("idle: fanart unavailable for %r: %s", name, exc)
            return None
        return found.artist_image or None

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
        return skins.installed(self._skins_dir) if self._skins_dir else []

    async def _handle_skins(self, request: web.Request) -> web.Response:
        """Every skin the device has, with what it shows (ADR-0050).

        **What it shows, not where it lives** (ADR-0019 as amended): a skin
        declares `meter.visible` and `spectrum.visible`, and 77 of the 99 on
        this device declare neither - which means a meter.
        """
        if self._skins_dir is None:
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
        if self._skins_dir is None:
            return web.json_response({"error": "skins are not wired up"}, status=503)
        wanted = request.match_info["name"]
        for skin, directory in self._skins():
            if skin.name != wanted:
                continue
            picture = skins.preview_of(skin, directory)
            if picture is None:
                return web.json_response({"error": "that skin has no picture"}, status=404)
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
        return web.json_response(
            {str(k): await self._portrait(k, v, size) for k, v in photos.items()}
        )

    async def _portrait(self, artist_id: int, lms_url, size: int):
        """**fanart's portrait if ADR-0059's sweep found one, LMS's otherwise.**

        The panel asks by LMS id and the sweep stores by folded name, because
        a rescan renumbers the ids (Finding 029) - so the name comes from the
        library, which already holds it.

        Both go through LMS's image proxy, so the grid gets the size it asked
        for and LMS does the fetching and caching either way.
        """
        if self._library is None:
            return lms_url
        try:
            name = await self._library.artist_name(artist_id)
        except Exception:
            return lms_url
        if not name:
            return lms_url
        found = remembered(self._notes, ARTIST_NAMESPACE, fold(name))
        if not found or found is True:
            return lms_url
        return f"{self._library.base}/imageproxy/{found}/image_{size}x{size}_o.jpg"

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
                biography_source="LMS" if biography else None,
                artist_image=photos.get(artist_id),
                sources=("lms",) if (biography or photos.get(artist_id)) else (),
            )
        rest = await self._enrichment.for_track(
            TrackKey(artist=fold(name)),
            only=("fanart", "wikipedia", "listenbrainz", "popular"),
        )
        found = found.merged_with(rest)
        if rest.artist_image:
            # **Pictures come from fanart first** (George, 2026-09-18): it
            # has a portrait for artists LMS's plugin has nothing for. The
            # text above is still LMS's where it has any - only the picture
            # changes hands.
            found = replace(found, artist_image=rest.artist_image)
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
        found = await self._enrichment.for_track(key, renderer=state.active, pending=pending)
        return web.json_response({
            # True when a provider had not finished: the panel asks again
            # rather than treating this as the final word.
            "pending": bool(pending),
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
        return web.json_response({"painted": True, "splash_dropped": dropped})

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
                source = self.SEEDED_LISTS.get(row.get("key"))
                if source is None or row["type"] != "list":
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
        return self._settings_call(lambda: {"key": key, "value": self._settings.set(key, value)})

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
    LIST_SOURCES = ("wifi", "lms_server", "bt_trusted")

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
        # A discovered server is named by its address, because that is what
        # the setting stores; the human name is the line underneath.
        current = str(self._settings.value("lms_server") or "")
        items = []
        for server in await discovery.find_servers():
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
        if key == "bt_trusted":
            if action != "forget":
                return web.json_response({"error": f"unknown action {action}"}, status=400)
            ok, error = await self._bluetooth(bluetooth_devices.forget, name)
            return web.json_response({"ok": ok, "error": error})
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
        return web.json_response({"ok": ok, "error": error})

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
        app.router.add_get("/idle/wallpaper/{name}", self._handle_wallpaper_file)
        app.router.add_get("/surface", self._handle_surface)
        app.router.add_post("/touch", self._handle_touch)
        app.router.add_post("/panel/painted", self._handle_painted)
        app.router.add_post("/peppy/{action}", self._handle_peppy)
        app.router.add_get("/settings", self._handle_settings)
        app.router.add_put("/settings/{key}", self._handle_setting_write)
        app.router.add_post("/settings/{key}", self._handle_setting_action)
        app.router.add_get("/settings/{key}/items", self._handle_list_items)
        app.router.add_post("/settings/{key}/items", self._handle_list_action)
        app.router.add_post("/bluetooth/pairing/{answer}", self._handle_pairing_answer)
        # ADR-0050. `{name:.*}` because a skin's name is a section heading
        # somebody typed, spaces and punctuation included.
        app.router.add_get("/skins", self._handle_skins)
        app.router.add_get("/skins/{name:.*}/preview", self._handle_skin_preview)
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
