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
#: From My Music: what our own screens already are (C).
LEFT_OUT_IDS = {"myMusicArtistsAlbumArtists", "myMusicPlaylists"}
#: Entries left out by their icon (see the module's docstring).
LEFT_OUT_ICONS = {"plugins/Spotty/html/images/transfer.png"}

#: What an entry is, from the parameter Lyrion names it by - not its words -
#: so the panel can give it the shape and tint of its kind (design/screens.md
#: §8: categories are read by colour and silhouette).
#: Most specific first: an album in a genre carries both ids.
HINTS = (("album_id", "album"), ("work_id", "work"), ("artist_id", "artist"), ("role_id", "artist"),
         ("folder_id", "folder"), ("year", "year"), ("genre_id", "genre"))

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
            tiles.append({
                "key": KNOWN_TILES.get(ident, "other"),
                "id": ident,
                "label": _text(item)[0],
                "handle": self._issue(spec),
            })
        return tiles

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
        rows = [r for r in (self._row(i, base) for i in result.get("item_loop") or []) if r]
        return {
            "title": spec.get("title") or result.get("title"),
            "count": int(result.get("count") or 0),
            "start": start,
            "items": rows,
        }

    async def _node(self, spec: dict, start: int, count: int) -> dict:
        menu = await self._home()
        children = [m for m in sorted(menu, key=_weight) if m.get("node") == spec["node"]
                    and str(m.get("id") or "") not in LEFT_OUT_IDS]
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
        if plays:
            spec = {"kind": "play", "actions": self._actions(item, base, go_plays=(cmd, params))}
            return self._shape(item, spec) if spec["actions"] else None
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
        return {
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
    params = {**(item.get("commonParams") or {}), **(item.get("params") or {}), **(spec.get("params") or {})}
    return next((word for key, word in HINTS if key in params), None)


def _is_browse(cmd) -> bool:
    return bool(cmd) and str(cmd[-1]) in BROWSE_TAIL


def _weight(item: dict) -> float:
    try:
        return float(item.get("weight") or 0)
    except (TypeError, ValueError):
        return 0.0


def _text(item: dict) -> tuple[str, str | None]:
    lines = str(item.get("text") or "").split("\n")
    return lines[0].strip(), (lines[1].strip() or None) if len(lines) > 1 else None
