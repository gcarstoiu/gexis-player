# SPDX-License-Identifier: GPL-3.0-or-later
"""Library reads for the panel's designed screens (Phase 7 step 3,
ADR-0038 §1, §5-7): typed LMS queries, not SlimBrowse (ADR-0030).

The core runs the queries and returns the fields the screens need, never
LMS's reply as such, so the panel sends no LMS command (ADR-0038 §5).

What the queries return, and what they cost, was measured against George's
server on 2026-09-17 (Finding 029): every read 5-26 ms; all 916 album
artists in one 98 KB reply. So lists are paged only where the panel asks
for a page, and nothing here batches or pre-fetches.

**Cache.** Lists are kept in memory (ADR-0020) until LMS's `lastscan`
changes: a full rescan renumbers every album and artist id (Finding 029
§4), so nothing cached before one is valid after it. `lastscan` is read at
most once per `LASTSCAN_CHECK_S`. Playlists are not cached: they change
from any LMS app without a scan.
"""
from __future__ import annotations

import itertools
import logging
import time
import unicodedata

import aiohttp

logger = logging.getLogger("gexis_core.library")

#: ADR-0022 inventory, "Albums in the New Music strip" [H]: the design's ten.
NEW_MUSIC_COUNT = 10

#: ADR-0022 inventory, "Artwork size requested from LMS" [H]. `_o.jpg` is
#: always a JPEG; the bare resize was a PNG for 5 of 20 albums (Finding 029
#: §5). Ten 500px covers in 176px cards were part of what made the New Music
#: strip scroll unevenly on the panel (George, 2026-09-17).
#:
#: **A ladder, not one size per element** (Phase 7a step 1, 2026-09-18).
#: Each request is the smallest step at or above what the panel actually
#: draws, so no cover is bigger than the box it fills and LMS still keeps a
#: bounded number of resized variants to cache. What the panel draws:
#: now playing's well 500, the album page 264, a New Music card 176, a
#: discography card 132, a queue row 42.
ARTWORK_COVER = 300
ARTWORK_THUMB = 200
#: Rows: the queue rail's 42px thumbnails, and track rows if one ever draws
#: artwork (none does today).
ARTWORK_ROW = 100

#: ADR-0022 inventory, "How long cached library lists are kept" [N]: until
#: a rescan, noticed within this many seconds.
LASTSCAN_CHECK_S = 60.0

#: Album fields: l=album, j=artwork_track_id, y=year, a=artist, S=artist_id,
#: W=release_type (Finding 029 §2).
ALBUM_TAGS = "ljyaSW"
#: Track fields: t=tracknum, d=duration, a=artist, c=coverid, i=disc.
TRACK_TAGS = "tdaci"

_id_counter = itertools.count(1)


class LibraryUnavailable(Exception):
    """LMS could not be reached, or answered with an error."""


class NotFound(Exception):
    """No such album, artist or playlist - including one a rescan
    renumbered away."""


class NoPlayer(Exception):
    """The player has not been found on the server yet, so there is
    nothing to play on."""


#: What the panel asks for, and the LMS command it becomes. Measured against
#: George's server in Finding 029: every kind loads and adds, and a load on a
#: powered-off player makes LMS power it on itself (ADR-0038 §4).
TARGETS = {"album": "album_id", "artist": "artist_id", "track": "track_id",
           "playlist": "playlist_id"}
#: `shuffle` is `play` with LMS's shuffle turned on instead of off - the
#: design's Shuffle all beside Play all (George, 2026-09-18).
ACTIONS = {"play": "cmd:load", "add": "cmd:add", "shuffle": "cmd:load"}
#: Adding to a saved playlist is not a `playlistcontrol` at all: LMS takes
#: one track URL at a time, and ignores `album_id`/`track_id` there without
#: an error (Finding 029 §3). So the tracks are resolved first.
PLAYLIST_ACTION = "playlist"

#: The queue rail acts on a position in the queue, not on a library id:
#: jump to it, or drop it (design/data-contract.md's queue rail).
#: `clear` takes no position, unlike the other two - the rail's Clear
#: button empties the queue where the rows address one track each.
QUEUE_ACTIONS = {"play": ["playlist", "index"], "remove": ["playlist", "delete"], "clear": ["playlist", "clear"]}


def _int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _letter(textkey) -> str:
    """The jump rail's letter for an artist (George, 2026-09-18).

    LMS's own key is kept for the order (ADR-0038 §1a) but not for the rail:
    it hands back `Ç` and `Í` for two artists on George's server and a digit
    for each numeric name, where the design's rail is `#` then A-Z. Accents
    fold onto their base letter - `Ç` into C, `Í` into I - and anything that
    is not a letter files under `#`.
    """
    if not textkey:
        return "#"
    first = unicodedata.normalize("NFKD", str(textkey))[:1].upper()
    return first if first.isalpha() and first.isascii() else "#"


def _float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class LmsLibrary:
    def __init__(self, host: str, port: int, *, player_id=None, clock=time.monotonic) -> None:
        self._base = f"http://{host}:{port}"
        #: Reads the renderer adapter's own resolved player id: the library
        #: plays on the same player the adapter arbitrates for, and never
        #: hardcodes one (the project's rule for anything that differs per
        #: machine).
        self._player_id = player_id or (lambda: None)
        self._clock = clock
        self._cache: dict[tuple, dict] = {}
        self._http: aiohttp.ClientSession | None = None
        self._lastscan: str | None = None
        self._lastscan_checked: float | None = None

    # --- LMS ---------------------------------------------------------------

    async def _session(self) -> aiohttp.ClientSession:
        """One session for the life of the daemon, so a connection is kept
        open. Adding an artist to a playlist is one request per track (LMS
        takes no bulk form, Finding 029 §3), and a session per request meant
        a new connection per track - slow enough for George to notice,
        2026-09-18."""
        if self._http is None or self._http.closed:
            self._http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self._http

    async def _rpc(self, command: list, player: str = "", timeout: float | None = None) -> dict:
        body = {"id": next(_id_counter), "method": "slim.request", "params": [player, command]}
        # `timeout` overrides the session's own for one call. The artist
        # information plugin needs it: an artist it has not looked up before
        # costs it 500-900 ms and sometimes more, because it goes to the
        # network, and the session's 10 s was cutting those off (2026-09-18).
        kwargs = {"timeout": aiohttp.ClientTimeout(total=timeout)} if timeout else {}
        try:
            session = await self._session()
            async with session.post(f"{self._base}/jsonrpc.js", json=body, **kwargs) as resp:
                resp.raise_for_status()
                return (await resp.json()).get("result") or {}
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise LibraryUnavailable(str(exc)) from exc

    async def rpc(self, command: list, player: str = "", timeout: float | None = None) -> dict:
        """One JSON-RPC call on this library's session. Public because the
        radio browser (radio.py) and the artist-information plugin
        (artistinfo.py) send their own commands and there is no reason for a
        second HTTP session to LMS."""
        return await self._rpc(command, player, timeout)

    async def _check_lastscan(self) -> None:
        now = self._clock()
        if self._lastscan_checked is not None and now - self._lastscan_checked < LASTSCAN_CHECK_S:
            return
        status = await self._rpc(["serverstatus", 0, 0])
        self._lastscan_checked = now
        lastscan = status.get("lastscan")
        # While a scan runs LMS reports `rescan` and no `lastscan` (seen
        # 2026-09-17); ids are in flux, so nothing is kept until it settles.
        if status.get("rescan") or lastscan != self._lastscan:
            if self._cache:
                logger.info("library: LMS rescanned (lastscan %s -> %s), dropping the cache",
                            self._lastscan, lastscan)
            self._cache.clear()
            self._lastscan = None if status.get("rescan") else lastscan

    async def _cached(self, command: list) -> dict:
        await self._check_lastscan()
        key = tuple(command)
        if key not in self._cache:
            result = await self._rpc(command)
            if self._lastscan is not None:
                self._cache[key] = result
            return result
        return self._cache[key]

    def _artwork(self, track_id, size: int) -> str | None:
        if not track_id:
            return None
        return f"{self._base}/music/{track_id}/cover_{size}x{size}_o.jpg"

    # --- shapes ------------------------------------------------------------

    def _album(self, raw: dict, size: int = ARTWORK_COVER) -> dict:
        return {
            "id": _int(raw.get("id")),
            "title": raw.get("album"),
            "artist": raw.get("artist"),
            "artist_id": _int(raw.get("artist_id")),
            "year": _int(raw.get("year")) or None,
            "release_type": raw.get("release_type"),
            "artwork": self._artwork(raw.get("artwork_track_id"), size),
        }

    def _track(self, raw: dict, size: int = ARTWORK_ROW) -> dict:
        return {
            "id": _int(raw.get("id")),
            "title": raw.get("title"),
            "artist": raw.get("artist"),
            "tracknum": _int(raw.get("tracknum")),
            "disc": _int(raw.get("disc")),
            "duration": _float(raw.get("duration")),
            "artwork": self._artwork(raw.get("coverid"), size),
        }

    # --- reads -------------------------------------------------------------

    async def counts(self) -> dict:
        """The library root's cards. "stations" has no source in the radio
        tree (ADR-0038, still open), so it is not reported."""
        albums = await self._cached(["albums", 0, 1])
        artists = await self._cached(["artists", 0, 1, "role_id:ALBUMARTIST"])
        playlists = await self._library_playlists()
        return {
            "albums": _int(albums.get("count")) or 0,
            "artists": _int(artists.get("count")) or 0,
            "playlists": len(playlists),
        }

    async def new_music(self) -> list[dict]:
        result = await self._cached(["albums", 0, NEW_MUSIC_COUNT, "sort:new", f"tags:{ALBUM_TAGS}"])
        return [self._album(a, ARTWORK_THUMB) for a in result.get("albums_loop", [])]

    async def artists(self, offset: int = 0, limit: int = 1000) -> dict:
        """Album artists (George, 2026-09-17), in LMS's order, each with
        LMS's own letter (`textkey`) - ADR-0038 §1a: however LMS files, so do
        we."""
        result = await self._cached(["artists", offset, limit, "role_id:ALBUMARTIST", "tags:s"])
        return {
            "count": _int(result.get("count")) or 0,
            "offset": offset,
            "items": [
                {
                    "id": _int(a.get("id")),
                    "name": a.get("artist"),
                    "letter": _letter(a.get("textkey")),
                }
                for a in result.get("artists_loop", [])
            ],
        }

    async def artist_albums(self, artist_id: int) -> list[dict]:
        """The discography, newest first (George, 2026-09-18), each album
        with LMS's own `release_type` for grouping (ADR-0038 §1a).

        LMS returns these alphabetically. Its `release_type` is still taken
        exactly as given; only the order is ours, because a discography
        reads by year.
        """
        result = await self._cached(
            ["albums", 0, 1000, f"artist_id:{artist_id}", "role_id:ALBUMARTIST", f"tags:{ALBUM_TAGS}"]
        )
        # An unknown id and an artist with no albums both come back empty;
        # LMS gives no way to tell them apart in this query.
        # The discography draws 132px cards, on the artist page and in
        # Browse's middle pane.
        albums = [self._album(a, ARTWORK_THUMB) for a in result.get("albums_loop", [])]
        # Undated albums last rather than first, and same-year albums by
        # title, so the order is stable between reads.
        albums.sort(key=lambda a: (-(a["year"] or 0), (a["title"] or "").casefold()))
        return albums

    async def album(self, album_id: int) -> dict:
        found = await self._cached(["albums", 0, 1, f"album_id:{album_id}", f"tags:{ALBUM_TAGS}"])
        loop = found.get("albums_loop", [])
        if not loop:
            raise NotFound(f"album {album_id}")
        tracks = await self._cached(
            ["titles", 0, 1000, f"album_id:{album_id}", "sort:tracknum", f"tags:{TRACK_TAGS}"]
        )
        album = self._album(loop[0])
        album["tracks"] = [self._track(t) for t in tracks.get("titles_loop", [])]
        return album

    # --- actions -----------------------------------------------------------

    async def act(
        self, kind: str, item_id: int, action: str, playlist_id: int | None = None
    ) -> dict:
        """Play something, or add it to the queue (ADR-0038 §3, §5).

        One `playlistcontrol` per action, as measured: a load replaces the
        queue and starts playing, an add appends without interrupting
        (Finding 029 §7). Nothing here powers the player on - LMS does that
        itself, which is what makes the library able to start playback at
        all (ADR-0038 §4, ADR-0027).

        **Play means in order** (George, 2026-09-18): LMS's own shuffle is
        turned off first. With it on, a freshly loaded album starts at a
        random track and an artist starts mid-album, which is what George
        saw. The design gives shuffle its own button, so Play is the
        in-order one; the panel is knowingly changing a player setting that
        LMS's own apps show.

        Returns what LMS reported, which is the number of tracks it acted
        on; a `200` means the command was sent, and what happened is read
        from `/state` (ADR-0037 §1).
        """
        if kind == "queue":
            return await self._queue_action(item_id, action)
        if kind not in TARGETS or action not in {**ACTIONS, PLAYLIST_ACTION: ""}:
            raise NotFound(f"{action} {kind}")
        if action == PLAYLIST_ACTION:
            return await self._add_to_playlist(kind, item_id, playlist_id)
        player = self._player_id()
        if not player:
            raise NoPlayer("the LMS player has not been resolved yet")
        if action in ("play", "shuffle"):
            await self._rpc(["playlist", "shuffle", 1 if action == "shuffle" else 0], player)
        result = await self._rpc(
            ["playlistcontrol", ACTIONS[action], f"{TARGETS[kind]}:{item_id}"], player
        )
        count = _int(result.get("count"))
        if not count:
            # LMS answers an unknown id with no count rather than an error.
            raise NotFound(f"{kind} {item_id}")
        logger.info("library: %s %s %s -> %s tracks", action, kind, item_id, count)
        return {"tracks": count}

    async def _queue_action(self, index: int, action: str) -> dict:
        """Jump to a position in the queue, or drop it. The rail addresses
        the queue by position because that is what LMS's own commands take
        and what the rail shows."""
        command = QUEUE_ACTIONS.get(action)
        if command is None:
            raise NotFound(f"{action} on the queue")
        player = self._player_id()
        if not player:
            raise NoPlayer("the LMS player has not been resolved yet")
        await self._rpc(command if action == "clear" else [*command, index], player)
        logger.info("library: queue %s %s", action, "" if action == "clear" else index)
        return {"index": index}

    async def _add_to_playlist(self, kind: str, item_id: int, playlist_id: int | None) -> dict:
        """Add an album, artist, track or playlist's tracks to a library
        playlist (ADR-0038 §3).

        LMS has no command that adds a whole album: `playlists edit cmd:add`
        takes one `url:` at a time, and silently ignores an `album_id` or
        `track_id` given to it (Finding 029 §3). The tracks are resolved
        first, then added in order.
        """
        if playlist_id is None:
            raise NotFound("a playlist to add to")
        if playlist_id not in {p["id"] for p in await self._library_playlists()}:
            # A plugin's playlist is not ours to write to, and an unknown id
            # is not a playlist at all (ADR-0038 §1).
            raise NotFound(f"library playlist {playlist_id}")
        if kind == "playlist":
            tracks = await self._rpc(
                ["playlists", "tracks", 0, 1000, f"playlist_id:{item_id}", "tags:u"]
            )
            urls = [t.get("url") for t in tracks.get("playlisttracks_loop", [])]
        else:
            query = ["titles", 0, 1000, f"{TARGETS[kind]}:{item_id}", "tags:u"]
            if kind == "album":
                query.append("sort:tracknum")
            found = await self._rpc(query)
            urls = [t.get("url") for t in found.get("titles_loop", [])]
        urls = [u for u in urls if u]
        if not urls:
            raise NotFound(f"{kind} {item_id}")
        for url in urls:
            await self._rpc(["playlists", "edit", "cmd:add", f"playlist_id:{playlist_id}", f"url:{url}"])
        logger.info(
            "library: added %s tracks from %s %s to playlist %s",
            len(urls), kind, item_id, playlist_id,
        )
        return {"tracks": len(urls)}

    # --- playlists ---------------------------------------------------------

    async def _library_playlists(self) -> list[dict]:
        """LMS library playlists only, never a plugin's (George,
        2026-09-17). They are `file:` URLs; Qobuz's are `qobuz:`. LMS's own
        `search:` does not filter playlists and `0 0` returns no count
        (Finding 029 §3), so the whole list is read and filtered here."""
        result = await self._rpc(["playlists", 0, 10000, "tags:su"])
        return [
            {"id": _int(p.get("id")), "name": p.get("playlist")}
            for p in result.get("playlists_loop", [])
            if str(p.get("url", "")).startswith("file:")
        ]

    async def playlists(self) -> list[dict]:
        playlists = await self._library_playlists()
        for playlist in playlists:
            tracks = await self._rpc(["playlists", "tracks", 0, 1, f"playlist_id:{playlist['id']}"])
            playlist["tracks"] = _int(tracks.get("count")) or 0
        return playlists

    async def playlist(self, playlist_id: int, offset: int = 0, limit: int = 1000) -> dict:
        playlists = await self._library_playlists()
        match = next((p for p in playlists if p["id"] == playlist_id), None)
        if match is None:
            raise NotFound(f"playlist {playlist_id}")
        result = await self._rpc(
            ["playlists", "tracks", offset, limit, f"playlist_id:{playlist_id}", f"tags:{TRACK_TAGS}"]
        )
        return {
            "id": playlist_id,
            "name": match["name"],
            "count": _int(result.get("count")) or 0,
            "offset": offset,
            "items": [self._track(t) for t in result.get("playlisttracks_loop", [])],
        }
