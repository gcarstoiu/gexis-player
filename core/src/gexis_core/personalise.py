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
*Finish* both end it; Settings -> Display -> Personalise opens it again.

**Only until the first boot after setup** (George, 2026-10-18: *"automatic
trigger of personalise flow should only be triggered on the first boot after
setup has ran"*): owed part 2 lasts through the boot setup ran in and the
next one, then is put off, as *Do it later* would. Opened from Settings, it
lasts the boot it was opened in. `at_start` decides, from the kernel's boot id.
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
BOOT_ID = Path("/proc/sys/kernel/random/boot_id")
PENDING, DONE, LATER = "pending", "done", "later"

#: **What part 2 may write, and nothing else**: the page sends settings by
#: their keys, and a key not here is refused rather than written. In the
#: order they are applied - the sources before the screen, and the plugins'
#: switches last (below), since switching one on starts its download.
KEYS = (
    "lms_enabled", "lms_server", "lms_extended_nav", "lms_library",
    "spotify_enabled", "bt_enabled",
    "phone_touchpad",
    "visualiser_skins", "viz_timeout", "skin_corpus", "skin_motion", "record_speed",
    "waiting_clock", "waiting_background", "waiting_wallpaper_styles",
    "idle_enabled", "idle_background", "wallpaper_styles", "idle_clock", "idle_weather",
    "weather_location",
    "standby_schedule", "standby_times",
)
#: The plugins part 2 can switch, by their switch. The Lyrion server and
#: Plexamp download; AirPlay is in the image (ADR-0167) and is written
#: either way, as Spotify is.
PLUGIN_ROWS = ("lyrion-server.enabled", "plexamp.enabled", "airplay.enabled")
#: ADR-0115 decision 20: where the Lyrion server on this player reads music,
#: written before its switch so it starts with them. The USB folders
#: themselves are added on *Where is your music?* as they are chosen.
LOCATION_ROWS = ("lyrion-server.music_folder", "lyrion-server.usb")


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


def boot_id(path: Path = BOOT_ID) -> str | None:
    try:
        return path.read_text().strip() or None
    except OSError:
        return None


def mark_pending(path: Path = PATH, first: bool = True, boot: str | None = None) -> None:
    """Owed: `first` when part 1 of a new player has just finished - the page
    then starts from part 2's own defaults - else asked again from Settings,
    starting from what the player has now. `boot` is the boot it was owed in."""
    _write({"state": PENDING, "first": first, "since": time.time(), "boot": boot or boot_id()}, path)
    logger.info("personalise: owed (%s)", "a new player" if first else "asked again from Settings")


def at_start(path: Path = PATH, boot: str | None = None) -> bool | None:
    """At the core's start: True while part 2 is still owed, False when it was
    owed and its time is over (the caller puts it off), None when it is not
    owed. A restart of the core within one boot changes nothing."""
    record = read(path)
    if record.get("state") != PENDING:
        return None
    now = boot or boot_id()
    made = record.get("boot")
    if now is None or made == now:
        return True
    # A new player's first boot after setup: kept, and that boot noted.
    if record.get("first") and record.get("shown", now) == now:
        if "shown" not in record:
            record["shown"] = now
            _write(record, path)
        return True
    logger.info("personalise: owed in an earlier boot; put off")
    return False


def put_off(settings, first: bool) -> None:
    """*Do it later*. **A new player put off plays what needs nothing set up**
    (George, 2026-10-18: skipped on a fresh install, the panel showed the
    library's tiles with nothing behind them; it should be the waiting screen
    with Spotify and Bluetooth): the Lyrion client goes off, as part 2's own
    page says - "Spotify and Bluetooth are on, and nothing else is installed".
    Asked again from Settings and put off, nothing changes ("Nothing was
    changed")."""
    if first and settings is not None:
        try:
            if settings.value("lms_enabled"):
                settings.set("lms_enabled", False)
                logger.info("personalise: put off on a new player; the Lyrion client is off")
        except Exception as exc:  # noqa: BLE001 - putting off must still end it
            logger.warning("personalise: Lyrion client not switched off: %s", exc)
    end(LATER)


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
    unknown = sorted(k for k in values if k not in KEYS and k not in PLUGIN_ROWS and k not in LOCATION_ROWS)
    if unknown:
        raise ValueError(f"not part 2's to set: {', '.join(unknown)}")
    return values


def apply(values: dict, settings, offered: list[dict], begin: Callable[[list[dict]], None],
          status: dict | None = None) -> dict:
    """**Write the answers, then switch on what downloads, then follow the
    downloads** (ADR-0128). Each setting goes through `Settings.set`, so it
    does what it does from Settings; one that refuses is reported and the
    rest go on - as setup does - and is named in the result. Returns
    `{"failed": [keys], "waiting": [component ids], "written": [keys]}`.

    `status`, each download's live state: **what is already in is not
    waited for** (ADR-0149 decision 42; George, 2026-10-19: the skins and
    Plexamp download during part 2, which "leaves only lyrion topics at the
    end"). The Lyrion server is followed past its download, through its own
    steps (`follow`, decision 43), unless it has already read the music."""
    status = status or {}
    values = checked(values)
    failed, written = [], []

    def put(key: str, value) -> None:
        try:
            if settings.value(key) != value:
                settings.set(key, value)
                written.append(key)
        except Exception as exc:  # noqa: BLE001 - one refusal must not stop the rest
            logger.warning("personalise: %s not set: %s", key, exc)
            failed.append(key)

    for key in KEYS:
        if key in values:
            put(key, values[key])
    for key in LOCATION_ROWS:
        if key in values:
            put(key, bool(values[key]))
    by_row = {p["row"]: p for p in offered}
    wait = []
    for row in PLUGIN_ROWS:
        if row not in values:
            continue
        put(row, bool(values[row]))
        plugin = by_row.get(row)
        if values[row] and plugin and plugin.get("component") and row not in failed:
            item = {"id": plugin["component"], "name": plugin["name"]}
            if row == "lyrion-server.enabled":
                item["follow"] = True
            wait.append(item)
    if values.get("visualiser_skins") and "visualiser_skins" not in failed:
        wait.insert(0, {"id": "skins", "name": "The visualiser's skins"})
    wait = [w for w in wait if not _in(status.get(w["id"]) or {}, w.get("follow"))]
    try:
        begin(wait)
    except OSError as exc:
        logger.warning("personalise: cannot record what to wait for: %s", exc)
    logger.info("personalise: %d setting(s) written%s; waiting for %s", len(values) - len(failed),
                f", {len(failed)} refused" if failed else "", ", ".join(w["name"] for w in wait) or "nothing")
    return {"failed": failed, "waiting": [w["id"] for w in wait], "written": written}


def _in(live: dict, follow: bool | None) -> bool:
    """Installed - and, for a download followed past it, finished with that
    too (Lyrion's library read)."""
    if live.get("state") != "installed":
        return False
    return not follow or (live.get("after") or {}).get("phase") == "ready"
