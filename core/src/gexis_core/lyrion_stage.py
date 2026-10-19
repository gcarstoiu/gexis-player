# SPDX-License-Identifier: GPL-3.0-or-later
"""**What the Lyrion server is doing after its download** (ADR-0115
decision 28; George, 2026-10-18: "If it takes long then it should be
transparent to the user that it will take some time before any library scan
is even started", and *Done* above a line saying it is still installing was
misleading).

Measured on sofapi the same evening, part 2 finished at 21:47:06: Lyrion
downloaded and started by 21:47:43, the core put the shares in its list at
21:48:12, asked for its add-ons at 21:48:19, restarted it to load them at
21:49:59, and the scan of the shares began at 21:50:08 - three minutes in
which the page said *Done*. These are those steps, as the page and the
server's row say them.

Pure: the core's loop reads Lyrion (`serverstatus`), and `stage` turns what
it read into the words.
"""
from __future__ import annotations

from gexis_core.lyrion_addons import NAMES, WANTED

#: The stage last worked out, for the server's row in Settings (read on the
#: loop's thread, written by the core's Lyrion loop).
CURRENT: dict = {}


def stage(answering: bool, addons, status: dict | None, has_locations: bool) -> dict:
    """`{"phase", "label", "line", "share", "done", "first"}`: `done` is true
    once Lyrion is reading the music or has read it - the player is usable
    then, however long a large library takes. `first`: the library has never
    been read yet - Lyrion keeps the old one through a rescan (Finding 127),
    so only a first read leaves it empty, and the panel says so in large
    (George, 2026-10-18, option A)."""
    # `addons`: each add-on's folder present, by Lyrion's name, or a bool
    # for all of them. The step counts as done once Material Skin - the one a
    # person sees - is in; one whose download fails (Radio Now Playing's did,
    # sofapi 2026-10-19) is asked again without holding the rest back.
    if isinstance(addons, bool):
        addons = {name: addons for name in WANTED}
    addons_done = bool(addons.get("MaterialSkin")) or all(addons.values())
    got = _stage(answering, addons_done, status or {}, has_locations)
    got["addons"] = [{"name": NAMES.get(name, name), "in": bool(addons.get(name))} for name in WANTED]
    songs = _int((status or {}).get("info total songs"))
    if got["phase"] in ("starting", "addons"):
        got["first"] = not addons_done
    elif got["phase"] in ("waiting", "scanning"):
        got["first"] = not songs
    else:
        got["first"] = False
    return got


def _stage(answering: bool, addons_done: bool, status: dict, has_locations: bool) -> dict:
    if not answering:
        return {"phase": "starting", "label": "Starting", "share": None, "done": False,
                "line": "Lyrion's first start. Its add-ons come next, then it reads your music." if not addons_done
                else "Lyrion is starting; it answers in a few seconds."}
    if not addons_done:
        return {"phase": "addons", "label": "Adding its add-ons", "share": None, "done": False,
                "line": ("Lyrion fetches Material Skin, Music & Artist Information and Radio Now Playing, "
                         "then restarts once: about 3 minutes.")}
    if status.get("rescan"):
        # Lyrion names its step itself, readably ("Scanning new music files",
        # "Discovering files/directories", "Building full text index" -
        # measured on sofapi, 2026-10-18); its count is that step's, and a
        # step with no total gives none.
        step = str(status.get("progressname") or "").strip()
        done, total = _int(status.get("progressdone")), _int(status.get("progresstotal"))
        counted = done is not None and bool(total)
        line = (f"{step}: {done:,} of {total:,}. " if step and counted else f"{step}. " if step else "") + \
            "Music shows up as Lyrion finds it; a large library takes hours. The player is ready to use meanwhile."
        return {"phase": "scanning", "label": "Reading your music", "done": True, "line": line,
                "share": min(0.99, done / total) if counted else None}
    songs = _int(status.get("info total songs"))
    if songs:
        albums = _int(status.get("info total albums"))
        return {"phase": "ready", "label": "Ready", "share": 1.0, "done": True,
                "line": f"{songs:,} songs" + (f" on {albums:,} albums" if albums else "") + " in the library."}
    if has_locations:
        return {"phase": "waiting", "label": "About to read your music", "share": None, "done": False,
                "line": "Lyrion starts reading your folders in a moment."}
    return {"phase": "ready", "label": "Ready, no music yet", "share": 1.0, "done": True,
            "line": "Add where your music is in Settings → Library → Lyrion Server."}


def _int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
