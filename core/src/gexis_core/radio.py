# SPDX-License-Identifier: GPL-3.0-or-later
"""Radio: the one SlimBrowse subtree (ADR-0030, ADR-0038 §5 and §8).

The panel never sends an LMS command here. The core walks the tree, hands
back an opaque **handle** per item, and only ever acts on a handle it
issued from `["radios", "menu:radio"]` - so the network-facing API
(ADR-0028 binds 0.0.0.0 and is unauthenticated by decision) cannot become a
way to run arbitrary LMS commands.

**Why an item's own action is resolved rather than followed.** Measured
2026-09-17 (Finding 029 §6): station items carry no `actions` of their own.
They have a `goAction` naming one of the list's `base.actions`, and in a
station list that inherited action is `… playlist play` with
`nextWindow: nowPlaying` - not a browse. A walker that treated
`base.actions.go` as "open this" started playing a station on George's
system. So the resolved command decides what an item *is*: one that ends in
`play` is a station, one that ends in `items` is a folder.

Two exclusions, both from ADR-0030 and re-measured in Finding 029:

- **Podcasts**, by its command `["podcast", "items"]`. The reply carries no
  `id`, so the `opmlpodcast` id that record named cannot be matched.
- **Anything asking for typed text** - an `input` block, or
  `__TAGGEDINPUT__` / `__INPUT__` in an action's params. Today that is
  Search TuneIn; the rule is mechanical so it keeps working as plugins
  change.
"""
from __future__ import annotations

import itertools
import logging
import secrets

logger = logging.getLogger("gexis_core.radio")

#: Where the tree is entered. Never `home`: everything unwanted - LMS's own
#: settings, My Apps, Radio Paradise - is unreachable by construction rather
#: than filtered (ADR-0030).
ROOT_CMD = ["radios"]
ROOT_PARAMS = {"menu": "radio"}

#: Asked for on every request below the root, which is how the walk in
#: Finding 029 saw the tree; the reply's shape depends on it.
MENU_PARAM = {"menu": "1"}

#: How many items one request asks for. The biggest list measured is Radio
#: Now Playing's 950.
PAGE = 200

#: Commands that are not a browse, whatever the key they arrive under.
PLAY_TAIL = ("play", "add", "insert", "load")

#: Excluded by command, because the reply has no id to exclude by.
EXCLUDED_CMD = ("podcast",)

_id_counter = itertools.count(1)


class RadioUnavailable(Exception):
    """LMS could not be reached, or answered with an error."""


class UnknownHandle(Exception):
    """A handle this core did not issue, or issued too long ago."""


def _wants_text(item: dict, params: dict) -> bool:
    if item.get("input"):
        return True
    return any("__TAGGEDINPUT__" in str(v) or "__INPUT__" in str(v) for v in params.values())


class RadioBrowser:
    """One per daemon. Holds the handles it has issued, newest first."""

    def __init__(self, rpc, player_id, *, limit: int = 4000) -> None:
        #: `rpc(command, player)` - the library's, so there is one HTTP
        #: session for the daemon.
        self._rpc = rpc
        self._player_id = player_id
        self._handles: dict[str, dict] = {}
        self._limit = limit

    # --- handles -----------------------------------------------------------

    def _issue(self, spec: dict) -> str:
        handle = secrets.token_urlsafe(9)
        self._handles[handle] = spec
        # Bounded: a walk of the whole tree would otherwise grow without
        # end. Oldest out first; a handle that falls off is re-issued by
        # browsing to it again.
        while len(self._handles) > self._limit:
            self._handles.pop(next(iter(self._handles)))
        return handle

    def _spec(self, handle: str | None) -> dict:
        if handle is None:
            return {"cmd": list(ROOT_CMD), "params": dict(ROOT_PARAMS), "kind": "folder"}
        spec = self._handles.get(handle)
        if spec is None:
            raise UnknownHandle(handle)
        return spec

    # --- the tree ----------------------------------------------------------

    async def browse(self, handle: str | None = None) -> dict:
        """One level of the tree, as rows the panel can draw."""
        spec = self._spec(handle)
        if spec["kind"] != "folder":
            raise UnknownHandle(f"{handle} is not a folder")
        result = await self._request(spec)
        base = (result.get("base") or {}).get("actions") or {}
        rows = []
        for item in result.get("item_loop", []):
            row = self._row(item, base)
            if row is not None:
                rows.append(row)
        return {
            "title": result.get("title"),
            "count": len(rows),
            "items": rows,
        }

    async def _request(self, spec: dict) -> dict:
        command = list(spec["cmd"]) + [0, PAGE]
        command += [f"{k}:{v}" for k, v in spec["params"].items()]
        if spec["cmd"] != ROOT_CMD:
            # Added *beside* the action's own `menu`, not over it: replacing
            # it changes the reply's shape, and a station list then comes
            # back with a context-menu action instead of its play (measured
            # against the live tree, 2026-09-18).
            command += [f"{k}:{v}" for k, v in MENU_PARAM.items()]
        return await self._rpc(command, self._player_id() or "")

    def _row(self, item: dict, base: dict) -> dict | None:
        """One item, or None if it is excluded."""
        action, params = self._resolve(item, base)
        if action is None:
            return None
        if _wants_text(item, params):
            return None
        cmd = list(action.get("cmd") or [])
        if not cmd or cmd[0] in EXCLUDED_CMD:
            return None
        # What LMS itself calls the item is the surer signal: a station is
        # `type: audio`, whatever key its action arrived under. The
        # resolved command is the second test, for items with no type.
        plays = str(item.get("type")) == "audio" or cmd[-1] in PLAY_TAIL
        spec = {"cmd": cmd, "params": params, "kind": "station" if plays else "folder"}
        # A station's own stream URL, where the item carries one: playing it
        # directly is one command and needs no menu session (Finding 029 §6).
        url = (item.get("presetParams") or {}).get("favorites_url")
        if plays and url:
            spec["url"] = url
        text = str(item.get("text") or "").split("\n")
        return {
            "handle": self._issue(spec),
            "kind": spec["kind"],
            "label": text[0].strip(),
            # A station's second line is what it is playing right now.
            "subtitle": text[1].strip() if len(text) > 1 else None,
        }

    def _resolve(self, item: dict, base: dict) -> tuple[dict | None, dict]:
        """The action an item actually carries, and the params to send with
        it: its own `actions`, else the one its `goAction` names in the
        list's `base.actions` (see this module's docstring)."""
        actions = item.get("actions") or {}
        name = item.get("goAction") or "go"
        action = actions.get("go") or actions.get(name) or base.get(name) or base.get("go")
        if action is None:
            return None, {}
        params = dict(action.get("params") or {})
        # `itemsParams` names which of the item's own bags of parameters the
        # inherited action wants.
        bag = action.get("itemsParams")
        params.update(item.get(bag) or {} if bag else item.get("params") or {})
        return action, params

    # --- playing -----------------------------------------------------------

    async def play(self, handle: str, action: str = "play") -> dict:
        """Play a station, or add it to the queue. Only a handle this core
        issued for a station will do anything."""
        spec = self._spec(handle)
        if spec["kind"] != "station":
            raise UnknownHandle(f"{handle} is not a station")
        player = self._player_id()
        if not player:
            raise UnknownHandle("the LMS player has not been resolved yet")
        if spec.get("url"):
            command = ["playlist", "play" if action == "play" else "add", spec["url"]]
        else:
            command = list(spec["cmd"]) + [f"{k}:{v}" for k, v in spec["params"].items()]
        await self._rpc(command, player)
        logger.info("radio: %s %s", action, spec.get("url") or spec["cmd"])
        return {"played": action == "play"}
