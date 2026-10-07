# SPDX-License-Identifier: GPL-3.0-or-later
"""Lyrion's own menus on the home screen (ADR-0118, Phase 13f).

The Radio screen's walker (radio.py, ADR-0030) widened to Lyrion's home
menu: **My Music, Favourites, Apps**, and any top category an app adds. The
same rules hold - the panel never sends a Lyrion command; the core hands
out an opaque **handle** per item and acts only on handles it issued; an
item is what its *resolved* command says it is (Finding 029).

What is left out, each by something Lyrion says rather than by its words
(Findings 110, 111):

- **The player's settings and power** - Alarm Clock, Synchronise, Turn Off
  and the rest live in the same tree (ADR-0118 C). Lyrion's global Search
  has no tile (G); its Radio branch has none either, since ours stays (F).
- **My Music's Album Artists and Playlists**, which our own Artists and
  Playlists cover (C) - by their ids.
- **Entries that write** (J): a browse command whose action names a
  `nextWindow` other than `nowPlaying` - "go back once done" - is an
  action, not a folder. Qobuz's *Add Release to Qobuz favourites* is one.
- **Spotty's Transfer Playback**, whose devices arrive as play items: by
  its icon, the one thing about it that is not a translated word.
- **Preset buttons** (`set-preset-N`) and one-off actions (`do`): never
  offered (D). Context menus come in a later iteration.
"""
from __future__ import annotations

import logging
import secrets
import time
import unicodedata
from urllib.parse import quote

from gexis_core.radio import PLAY_TAIL, UnknownHandle, _wants_text

logger = logging.getLogger("gexis_core.menus")

#: The home menu, flat, as the jive menu gives it (Finding 111).
HOME_CMD = ["menu", 0, 500, "direct:1"]

#: Top categories with tiles of their own, in the order ADR-0118 A puts
#: them relative to each other; the panel places them among ours.
KNOWN_TILES = {"myMusic": "mymusic", "favorites": "favorites", "opmlmyapps": "apps"}
#: Top items with no tile (ADR-0118 C, F, G).
NO_TILE = {"globalSearch", "playerpower", "radios"}
#: Whole branches that are the player's settings, never walked (C).
SETTINGS_NODES = {"settings", "settingsAudio", "advancedSettings"}
#: From My Music: what our own screens already are (C) - Playlists Folder
#: being the same playlists again.
LEFT_OUT_IDS = {"myMusicArtistsAlbumArtists", "myMusicPlaylists", "myMusicPlaylistFolder"}

#: **Every browse mode the server offers**, not only the player menu's
#: (George, 2026-10-06: "There are entries missing in My music"). The player
#: menu carried 14 of the 23 Lyrion's web interface shows; the rest are the
#: Extended Browse Modes plugin's - Random Albums, Popular Artists, Top
#: Tracks... Material's own list has them all; without Material, the player
#: menu is what there is.
MODES_CMD = ["material-skin", "browsemodes"]
#: Extended Browse Modes' own switches: a mode its owner turned off stays off.
EBM_PREF = ["pref", "plugin.extendedbrowsemodes:additionalMenuItems", "?"]
#: Entries left out by their icon (see the module's docstring).
LEFT_OUT_ICONS = {"plugins/Spotty/html/images/transfer.png"}

#: What an entry is, from the parameter Lyrion names it by - not its words -
#: so the panel can give it the shape and tint of its kind (design/screens.md
#: §8: categories are read by colour and silhouette).
#: Most specific first: an album in a genre carries both ids.
#: (`role_id` is not one: Lyrion sends it beside a genre's id too.)
HINTS = (("album_id", "album"), ("work_id", "work"), ("artist_id", "artist"),
         ("folder_id", "folder"), ("year", "year"), ("genre_id", "genre"))

#: Hidden while they hold nothing to choose (the handover's note 3, George
#: 2026-10-06): the entry, and the most it may hold and still be hidden.
HIDE_WHEN_FEW = {"opmlselectRemoteLibrary": 0, "opmlselectVirtualLibrary": 1}

#: The most of a list read at once for its letter index: All Artists' thousands
#: came back in 221 ms (2.7 MB) on George's server.
LETTERS_MAX = 20000
#: How long a letter index is kept: a rescan moves positions, and a scan
#: takes about two hours (Finding 109), so half an hour is the stale bound.
LETTERS_KEEP_S = 30 * 60

#: One page of a list. Lyrion pages by start and count (Finding 111).
PAGE = 100
#: How big an item's picture is asked for.
IMAGE_SIZE = 300

#: A browse is a command ending in one of these.
BROWSE_TAIL = ("items", "browselibrary")


class MenusUnavailable(Exception):
    """Lyrion could not be reached, or answered with an error."""


class LyrionMenus:
    """One per daemon, like RadioBrowser: the handles it has issued."""

    def __init__(self, rpc, player_id, base_url, *, limit: int = 8000) -> None:
        self._rpc = rpc
        self._player_id = player_id
        #: The Lyrion server's own address, for pictures (a callable: the
        #: server can change under a running core).
        self._base_url = base_url
        self._handles: dict[str, dict] = {}
        self._limit = limit
        #: Letter indexes by the list they index, kept a while: handles are
        #: new on every opening, and reading a list whole is the heaviest
        #: thing the menus do - All Artists is 2.7 MB from Lyrion, and the
        #: core relays nothing else while it parses (the phone's touchpad
        #: stalled ~135 ms in every ~170 for 2 s, measured on gexis
        #: 2026-10-06).
        self._letters: dict[tuple, tuple[float, dict]] = {}
        self._clock = time.monotonic

    # --- handles -----------------------------------------------------------

    def _issue(self, spec: dict) -> str:
        handle = secrets.token_urlsafe(9)
        self._handles[handle] = spec
        while len(self._handles) > self._limit:
            self._handles.pop(next(iter(self._handles)))
        return handle

    def _spec(self, handle: str) -> dict:
        spec = self._handles.get(handle)
        if spec is None:
            raise UnknownHandle(handle)
        return spec

    async def _call(self, command: list) -> dict:
        try:
            return await self._rpc(command, self._player_id() or "")
        except UnknownHandle:
            raise
        except Exception as exc:  # noqa: BLE001 - the library's own failures, worded
            raise MenusUnavailable(str(exc)) from exc

    # --- the home screen's tiles ----------------------------------------

    async def _home(self) -> list[dict]:
        result = await self._call(list(HOME_CMD))
        return result.get("item_loop") or []

    async def tiles(self) -> list[dict]:
        """The tiles ADR-0118 A adds: My Music, Favourites, Apps, and each
        other top category an app has added (`kind: "other"`)."""
        menu = await self._home()
        tiles = []
        for item in sorted(menu, key=_weight):
            if item.get("node") != "home":
                continue
            ident = str(item.get("id") or "")
            if ident in NO_TILE or ident in SETTINGS_NODES:
                continue
            spec = self._top_spec(item, menu)
            if spec is None:
                continue
            handle = self._issue(spec)
            tiles.append({
                "key": KNOWN_TILES.get(ident, "other"),
                "id": ident,
                "label": _text(item)[0],
                "handle": handle,
                # The card's second line: "21 views", "8 items", "6 apps".
                "count": await self._count(handle),
            })
        return tiles

    async def _count(self, handle: str) -> int | None:
        """How many entries a tile opens to - a lone text line (Lyrion's
        "Empty") counting as none; None when it cannot be read."""
        try:
            page = await self.browse(handle, 0, 2)
        except (UnknownHandle, MenusUnavailable):
            return None
        if page["count"] == 1 and page["items"] and page["items"][0]["kind"] == "text":
            return 0
        return page["count"]

    def _top_spec(self, item: dict, menu: list[dict]) -> dict | None:
        ident = str(item.get("id") or "")
        if ident == "opmlmyapps":
            # The apps are reached through `myapps items` (Finding 111).
            return {"kind": "folder", "cmd": ["myapps", "items"], "params": {}, "title": _text(item)[0]}
        if any(m.get("node") == ident for m in menu):
            # A node: its children are menu items of their own.
            return {"kind": "node", "node": ident, "title": _text(item)[0]}
        go = (item.get("actions") or {}).get("go")
        if not go or not _is_browse(go.get("cmd")):
            return None
        return {"kind": "folder", "cmd": list(go["cmd"]), "params": dict(go.get("params") or {}),
                "title": _text(item)[0]}

    # --- a list -------------------------------------------------------

    async def browse(self, handle: str, start: int = 0, count: int = PAGE) -> dict:
        """One page of a list, as rows the panel can draw."""
        spec = self._spec(handle)
        if spec["kind"] == "node":
            return await self._node(spec, start, count)
        if spec["kind"] not in ("folder", "container"):
            raise UnknownHandle(f"{handle} is not a list")
        start, count = max(0, int(start)), max(1, min(int(count), PAGE))
        command = list(spec["cmd"]) + [start, count]
        command += [f"{k}:{v}" for k, v in spec["params"].items()] + ["menu:1"]
        result = await self._call(command)
        base = (result.get("base") or {}).get("actions") or {}
        loop = result.get("item_loop") or []
        rows = [r for r in (self._row(i, base) for i in loop) if r]
        total = int(result.get("count") or 0)
        # Lyrion counts what the panel leaves out (an album page's "Add to
        # favourites", J): on the last page the count is what is shown.
        if start + len(loop) >= total:
            total = start + len(rows)
        facts = await self._album_facts(spec, rows)
        for row in rows:
            row.pop("track", None)
        return {
            "title": spec.get("title") or result.get("title"),
            "count": total,
            "start": start,
            "items": rows,
            **({"facts": facts} if facts else {}),
        }

    async def _album_facts(self, spec: dict, rows: list[dict]) -> list[list[str]] | None:
        """**A library album's release facts and its tracks' lengths**
        (George, 2026-10-06: "the length of the tracks is not shown", "not
        seeing the small release information"). Lyrion's menu gives a track
        its id and nothing else; the library gives the rest, asked once per
        page. A streaming app's album carries its own facts as text lines
        (Qobuz) and no lengths at all - nothing to add there."""
        album = (spec.get("params") or {}).get("album_id")
        tracks = {row["track"]: row for row in rows if row.get("track") is not None}
        if album is None or not tracks:
            return None
        try:
            found = (await self._call(["titles", 0, 1000, f"album_id:{album}", "tags:dgy"])).get("titles_loop") or []
        except Exception:  # noqa: BLE001 - the page stands without them
            return None
        total = 0.0
        genres: list[str] = []
        years: set[str] = set()
        for title in found:
            seconds = float(title.get("duration") or 0)
            total += seconds
            row = tracks.get(int(title.get("id") or -1))
            if row is not None and seconds:
                row["duration"] = round(seconds)
            genre = str(title.get("genre") or "").strip()
            if genre and genre.lower() != "no genre" and genre not in genres:
                genres.append(genre)
            year = str(title.get("year") or "").strip()
            if year and year != "0":
                years.add(year)
        facts = []
        if genres:
            facts.append(["Genre", ", ".join(genres[:3])])
        if years:
            first, last = min(years), max(years)
            facts.append(["Year", first if first == last else f"{first} – {last}"])
        if total:
            facts.append(["Duration", _clock(total)])
        facts.append(["Tracks", str(len(found))])
        return facts

    async def _modes(self) -> list[dict]:
        """My Music's modes beyond the player menu, as menu items, or none
        when the server cannot say (no Material, an older Lyrion)."""
        try:
            modes = (await self._rpc(list(MODES_CMD), self._player_id() or "")).get("modes_loop") or []
        except Exception:  # noqa: BLE001 - optional: the player menu stands alone
            return []
        try:
            prefs = (await self._rpc(list(EBM_PREF), "")).get("_p2") or []
            off = {str(p.get("id")) for p in prefs if isinstance(p, dict) and str(p.get("enabled")) == "0"}
        except Exception:  # noqa: BLE001
            off = set()
        items = []
        for mode in modes:
            ident = str(mode.get("id") or "")
            params = mode.get("params") or {}
            if not ident or ident in off or not params.get("mode"):
                continue
            items.append({"node": "myMusic", "id": ident, "text": mode.get("text") or "",
                          "weight": mode.get("weight"),
                          "actions": {"go": {"cmd": ["browselibrary", "items"], "params": {**params, "menu": 1}}}})
        return items

    async def _node(self, spec: dict, start: int, count: int) -> dict:
        menu = await self._home()
        children = [m for m in menu if m.get("node") == spec["node"]]
        if spec["node"] == "myMusic":
            have = {str(m.get("id") or "") for m in children}
            children += [m for m in await self._modes() if m["id"] not in have]
        children = [m for m in sorted(children, key=_weight) if str(m.get("id") or "") not in LEFT_OUT_IDS]
        children = [m for m in children if not await self._too_few(m)]
        rows = []
        for item in children:
            ident = str(item.get("id") or "")
            if any(m.get("node") == ident for m in menu):
                rows.append(self._shape(item, {"kind": "node", "node": ident, "title": _text(item)[0]}))
                continue
            row = self._row(item, {})
            if row:
                rows.append(row)
        page = rows[start:start + count]
        # `node`: a menu of Lyrion's own, drawn as the panel's grouped cards.
        return {"title": spec.get("title"), "count": len(rows), "start": start, "items": page,
                "node": spec["node"]}

    async def _too_few(self, item: dict) -> bool:
        """An entry that would open to (nearly) nothing (HIDE_WHEN_FEW)."""
        most = HIDE_WHEN_FEW.get(str(item.get("id") or ""))
        go = (item.get("actions") or {}).get("go")
        if most is None or not go:
            return False
        command = list(go.get("cmd") or []) + [0, 2] + [f"{k}:{v}" for k, v in (go.get("params") or {}).items()] + ["menu:1"]
        try:
            return int((await self._call(command)).get("count") or 0) <= most
        except MenusUnavailable:
            return False

    async def letters(self, handle: str) -> dict:
        """**Where each letter starts in a list** (the handover's note 6):
        Lyrion gives no index with a page, but every item of a library list
        carries its first letter (`textkey`), so the list is read once, whole,
        and the first position of each letter kept. Accents fold to their
        letter; digits and signs are `#`. Empty for a list with no letters."""
        spec = self._spec(handle)
        if spec["kind"] not in ("folder", "container") or "letters" in spec:
            return {"letters": spec.get("letters", {})}
        command = list(spec["cmd"]) + [0, LETTERS_MAX]
        command += [f"{k}:{v}" for k, v in spec["params"].items()] + ["menu:1"]
        key = tuple(str(part) for part in command)
        kept = self._letters.get(key)
        if kept and self._clock() - kept[0] < LETTERS_KEEP_S:
            spec["letters"] = kept[1]
            return {"letters": kept[1]}
        items = (await self._call(command)).get("item_loop") or []
        keys = [item.get("textkey") for item in items]
        found: dict[str, int] = {}
        if items and sum(1 for k in keys if k) >= len(items) * 0.9:
            last = None
            for position, textkey in enumerate(keys):
                # Sorted: a letter can only start where the key's first
                # character changes, so the fold runs a few dozen times.
                head = str(textkey or "")[:1]
                if head == last:
                    continue
                last = head
                letter = _letter(textkey)
                if letter and letter not in found:
                    found[letter] = position
        spec["letters"] = found
        self._letters[key] = (self._clock(), found)
        return {"letters": found}

    # --- one item -----------------------------------------------------

    def _row(self, item: dict, base: dict) -> dict | None:
        """One item as the panel draws it, or None when it is left out."""
        if str(item.get("icon") or "") in LEFT_OUT_ICONS:
            return None
        if any(token in str(item.get("text") or "") for token in ("__TAGGEDINPUT__", "__INPUT__")):
            # Lyrion's own placeholder for typed text, shown as a remembered
            # search in Qobuz's Search (seen 2026-10-05): nothing to draw.
            return None
        go, params = _resolve(item, base, item.get("goAction") or "go")
        kind_word = str(item.get("type") or "")
        if go is None or kind_word == "text" or item.get("style") == "itemNoAction":
            text = _text(item)
            if not text[0]:
                return None
            return {"handle": None, "kind": "text", "label": text[0], "subtitle": text[1],
                    "image": None, "can": []}
        cmd = list(go.get("cmd") or [])
        if not cmd:
            return None
        if _wants_text(item, params) or kind_word == "search":
            return self._shape(item, {"kind": "search", "cmd": cmd, "params": params,
                                      "title": _text(item)[0]})
        plays = kind_word == "audio" or item.get("style") == "itemplay" or cmd[-1] in PLAY_TAIL
        # An album asked for as a context menu (Qobuz's Bestsellers carry
        # `isContextMenu`, seen 2026-10-06): its tracks "go" to Play Control,
        # a list of what to do with them - they are leaves, played by the
        # `play`, `add` and `add-hold` the list's base offers.
        control = item.get("goAction") == "playControl"
        if plays or control:
            found = self._actions(item, base, go_plays=None if control else (cmd, params))
            spec = {"kind": "play", "actions": found}
            if not spec["actions"]:
                return None
            row = self._shape(item, spec)
            track = (item.get("commonParams") or {}).get("track_id")
            if track is not None:
                row["track"] = int(track)
            return row
        if not _is_browse(cmd):
            # A `do`, a preset, anything that is not a browse: not offered (D).
            return None
        if go.get("nextWindow") not in (None, "", "nowPlaying"):
            # An entry that writes and then goes back (J).
            return None
        # An album or a playlist - open it, or play it whole - only when Lyrion
        # types it so: a list's `base` offers play to every item in it, apps
        # included (My Apps, read 2026-10-05).
        actions = self._actions(item, base) if kind_word == "playlist" else {}
        kind = "container" if actions else "folder"
        return self._shape(item, {"kind": kind, "cmd": cmd, "params": params,
                                  "title": _text(item)[0], "actions": actions})

    def _actions(self, item: dict, base: dict, go_plays=None) -> dict:
        """Play, add to the end and play next, as Lyrion itself offers them
        for this item (`play`, `add`, `add-hold`)."""
        found = {}
        for ours, theirs in (("play", "play"), ("add", "add"), ("next", "add-hold")):
            action, params = _resolve(item, base, theirs, fallback=False)
            if action and action.get("cmd"):
                found[ours] = {"cmd": list(action["cmd"]), "params": params}
        if go_plays and "play" not in found:
            found["play"] = {"cmd": go_plays[0], "params": go_plays[1]}
        return found

    def _shape(self, item: dict, spec: dict) -> dict:
        text = _text(item)
        # Qobuz marks what it cannot stream - not licensed here, or not yet
        # released - with "* " (its _albumItem and _trackItem): an album then
        # has no `playlist` type and a track nothing to play. Said plainly
        # rather than as a star.
        unavailable = text[0].startswith("* ")
        if unavailable:
            text = (text[0][2:].strip(), text[1])
        return {
            **({"unavailable": True} if unavailable else {}),
            "handle": self._issue(spec),
            "kind": spec["kind"],
            "label": text[0],
            "subtitle": text[1],
            "image": self._image(item),
            "can": sorted((spec.get("actions") or {}).keys()),
            # Lyrion's own id for a menu entry (My Music's), and what an
            # entry in a list is: the panel's looks key on these.
            "id": str(item.get("id") or "") or None,
            "hint": _hint(item, spec),
            # The letter Lyrion sorted it under ("Jon Lord" under L): the
            # list's headers follow it, as the rail does.
            "letter": _letter(item.get("textkey")),
        }

    def _image(self, item: dict) -> str | None:
        base = (self._base_url() or "").rstrip("/")
        if not base:
            return None
        icon = item.get("icon-id") or item.get("icon") or item.get("image") \
            or ((item.get("window") or {}).get("icon-id"))
        if not icon:
            return None
        icon = str(icon)
        size = IMAGE_SIZE
        if icon.startswith(("http://", "https://")):
            return f"{base}/imageproxy/{quote(icon, safe='')}/image_{size}x{size}_o.jpg"
        if icon.lstrip("-").replace("-", "").isalnum() and "/" not in icon and "." not in icon:
            return f"{base}/music/{icon}/cover_{size}x{size}_o.jpg"
        return f"{base}/{icon.lstrip('/')}"

    # --- acting -------------------------------------------------------

    async def act(self, handle: str, action: str) -> dict:
        """Play, add or play next - only for a handle this core issued for
        something Lyrion itself said can do that."""
        spec = self._spec(handle)
        chosen = (spec.get("actions") or {}).get(action)
        if chosen is None:
            raise UnknownHandle(f"{handle} cannot {action}")
        if not self._player_id():
            raise UnknownHandle("the Lyrion player has not been resolved yet")
        command = list(chosen["cmd"]) + [f"{k}:{v}" for k, v in chosen["params"].items()]
        await self._call(command)
        logger.info("menus: %s %s", action, chosen["cmd"])
        return {"done": action}

    async def search(self, handle: str, text: str, count: int = PAGE) -> dict:
        """A search item answered with the phone's typed text (ADR-0118 E):
        its results, as a list with handles of their own."""
        spec = self._spec(handle)
        if spec["kind"] != "search":
            raise UnknownHandle(f"{handle} is not a search")
        words = " ".join(str(text).split())[:200]
        if not words:
            raise UnknownHandle("nothing to search for")
        params = {k: (str(v).replace("__TAGGEDINPUT__", words).replace("__INPUT__", words))
                  for k, v in spec["params"].items()}
        if not any(words in str(v) for v in params.values()):
            params["search"] = words
        results = self._issue({"kind": "folder", "cmd": spec["cmd"], "params": params,
                               "title": f"{spec.get('title') or 'Search'}: {words}"})
        return {"handle": results, **await self.browse(results, 0, count)}


def _resolve(item: dict, base: dict, name: str, fallback: bool = True) -> tuple[dict | None, dict]:
    """The action an item carries under `name`: its own, else the list's
    (`base.actions`), with the parameters it names (radio.py's rule)."""
    actions = item.get("actions") or {}
    action = actions.get(name) or base.get(name)
    if action is None and fallback:
        action = actions.get("go") or base.get("go")
    if not isinstance(action, dict):
        return None, {}
    params = dict(action.get("params") or {})
    bag = action.get("itemsParams")
    params.update((item.get(bag) or {}) if bag else (item.get("params") or {}))
    return action, params


def _hint(item: dict, spec: dict) -> str | None:
    """What an entry is: an app (Lyrion's `redirect` in My Apps), else by the
    entry's own identity - `commonParams`, which for a genre is its genre id
    alone - before what its action carries."""
    if str(item.get("type") or "") == "redirect":
        return "app"
    own = item.get("commonParams") or {}
    for params in (own, {**(item.get("params") or {}), **(spec.get("params") or {})}):
        found = next((word for key, word in HINTS if key in params), None)
        if found:
            return found
    return None


#: Letters Unicode does not decompose to a Latin one (Ł in Łódź).
_UNFOLDED = {"Ł": "L", "Ø": "O", "Đ": "D", "Ð": "D", "Æ": "A", "Œ": "O", "ß": "S", "Þ": "T", "ẞ": "S"}


def _letter(key) -> str | None:
    """A rail letter for a textkey: A-Z with accents folded, `#` otherwise."""
    if not key:
        return None
    first = str(key)[0].upper()
    first = _UNFOLDED.get(first, first)
    base = unicodedata.normalize("NFKD", first).encode("ascii", "ignore").decode().upper()
    return base if len(base) == 1 and "A" <= base <= "Z" else "#"


def _is_browse(cmd) -> bool:
    return bool(cmd) and str(cmd[-1]) in BROWSE_TAIL


def _weight(item: dict) -> float:
    try:
        return float(item.get("weight") or 0)
    except (TypeError, ValueError):
        return 0.0


def _clock(seconds: float) -> str:
    """0:46:05 or 46:05, as Qobuz writes an album's duration."""
    whole = int(round(seconds))
    h, rest = divmod(whole, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _text(item: dict) -> tuple[str, str | None]:
    lines = str(item.get("text") or "").split("\n")
    return lines[0].strip(), (lines[1].strip() or None) if len(lines) > 1 else None
