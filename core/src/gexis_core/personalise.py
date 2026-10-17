# SPDX-License-Identifier: GPL-3.0-or-later
"""**First use, part 2: make it yours** (ADR-0149; Phase 14, `ph-first-use`).

Part 1 (setup, over the setup network) gets the player working. Part 2 runs
on the phone from the home network, at the player's own address, and asks
how the player is used: what it plays, what its screen shows. Its answers
are ordinary settings, written here in one go when the page finishes, and
what they install (the Lyrion Server, Plexamp, the visualiser's skins) is
followed by ADR-0128's settling, on the panel and on the phone.

**Owed, done or put off** is the one thing kept here: a new player is owed
part 2 once part 1 has finished (not a restored one, whose backup answers it,
and not one updated from an earlier release). While it is owed, the phone's
page opens on it and the panel shows a code to it. *Do it later* and
*Finish* both end it; Settings -> System -> Personalise opens it again at
any time without making it owed.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("gexis_core.personalise")

PATH = Path("/var/lib/gexis/personalise.json")
PENDING, DONE, LATER = "pending", "done", "later"

#: **What part 2 may write, and nothing else**: the page sends settings by
#: their keys, and a key not here is refused rather than written. In the
#: order they are applied - the sources before the screen, and the plugins'
#: switches last (below), since switching one on starts its download.
KEYS = (
    "lms_enabled", "lms_server", "lms_extended_nav", "lms_library",
    "spotify_enabled", "bt_enabled",
    "visualiser_skins", "viz_timeout", "skin_corpus", "skin_motion", "record_speed",
    "waiting_clock", "waiting_background", "waiting_wallpaper_styles",
    "idle_enabled", "idle_background", "wallpaper_styles", "idle_clock", "idle_weather",
    "weather_location",
    "standby_schedule", "standby_times",
)
#: The plugins part 2 can switch on, by their switch: each downloads.
PLUGIN_ROWS = ("lyrion-server.enabled", "plexamp.enabled")


def _write(record: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(record))
    os.replace(tmp, path)


def read(path: Path = PATH) -> dict:
    try:
        record = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return record if isinstance(record, dict) else {}


def state(path: Path = PATH) -> str | None:
    """`pending`, `done`, `later`, or None for a player that was never
    offered it (updated from a release before part 2, or restored)."""
    value = read(path).get("state")
    return value if value in (PENDING, DONE, LATER) else None


def mark_pending(path: Path = PATH, first: bool = True) -> None:
    """Owed: `first` when part 1 of a new player has just finished - the page
    then starts from part 2's own defaults - else asked again from Settings,
    starting from what the player has now."""
    _write({"state": PENDING, "first": first, "since": time.time()}, path)
    logger.info("personalise: owed (%s)", "a new player" if first else "asked again from Settings")


def first(path: Path = PATH) -> bool:
    return bool(read(path).get("first"))


def end(how: str, path: Path = PATH) -> None:
    _write({"state": how, "since": time.time()}, path)
    logger.info("personalise: %s", how)


def checked(values: Any) -> dict:
    """The settings the page sent, refused whole if any key is not part 2's
    to write: a page that sends one more than it should is a page wrong
    about what it is, and half of its answers are worse than none."""
    if not isinstance(values, dict):
        raise ValueError("settings must be an object")
    unknown = sorted(k for k in values if k not in KEYS and k not in PLUGIN_ROWS)
    if unknown:
        raise ValueError(f"not part 2's to set: {', '.join(unknown)}")
    return values


def apply(values: dict, settings, offered: list[dict], begin: Callable[[list[dict]], None]) -> dict:
    """**Write the answers, then switch on what downloads, then follow the
    downloads** (ADR-0128). Each setting goes through `Settings.set`, so it
    does what it does from Settings; one that refuses is reported and the
    rest go on - as setup does - and is named in the result. Returns
    `{"failed": [keys], "waiting": [component ids]}`."""
    values = checked(values)
    failed = []

    def put(key: str, value) -> None:
        try:
            if settings.value(key) != value:
                settings.set(key, value)
        except Exception as exc:  # noqa: BLE001 - one refusal must not stop the rest
            logger.warning("personalise: %s not set: %s", key, exc)
            failed.append(key)

    for key in KEYS:
        if key in values:
            put(key, values[key])
    by_row = {p["row"]: p for p in offered}
    wait = []
    for row in PLUGIN_ROWS:
        if row not in values:
            continue
        put(row, bool(values[row]))
        plugin = by_row.get(row)
        if values[row] and plugin and plugin.get("component") and row not in failed:
            wait.append({"id": plugin["component"], "name": plugin["name"]})
    if values.get("visualiser_skins") and "visualiser_skins" not in failed:
        wait.insert(0, {"id": "skins", "name": "The visualiser's skins"})
    try:
        begin(wait)
    except OSError as exc:
        logger.warning("personalise: cannot record what to wait for: %s", exc)
    logger.info("personalise: %d setting(s) written%s; waiting for %s", len(values) - len(failed),
                f", {len(failed)} refused" if failed else "", ", ".join(w["name"] for w in wait) or "nothing")
    return {"failed": failed, "waiting": [w["id"] for w in wait]}
