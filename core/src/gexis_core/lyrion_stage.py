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

#: The stage last worked out, for the server's row in Settings (read on the
#: loop's thread, written by the core's Lyrion loop).
CURRENT: dict = {}


def stage(answering: bool, addons_done: bool, status: dict | None, has_locations: bool) -> dict:
    """`{"phase", "label", "line", "share", "done"}`: `done` is true once
    Lyrion is reading the music or has read it - the player is usable then,
    however long a large library takes."""
    status = status or {}
    if not answering:
        return {"phase": "starting", "label": "Starting", "share": None, "done": False,
                "line": "Lyrion's first start. Its add-ons come next, then it reads your music." if not addons_done
                else "Lyrion is starting; it answers in a few seconds."}
    if not addons_done:
        return {"phase": "addons", "label": "Adding its add-ons", "share": None, "done": False,
                "line": ("Lyrion fetches Material Skin, Music & Artist Information and Radio Now Playing, "
                         "then restarts once: about 3 minutes before it reads your music.")}
    if status.get("rescan"):
        done, total = _int(status.get("progressdone")), _int(status.get("progresstotal"))
        unit = counted(str(status.get("progressname") or ""))
        line = (f"{done:,} of {total:,} {unit} so far. " if done is not None and total else "") + \
            "Music shows up as Lyrion finds it; a large library takes hours. The player is ready to use meanwhile."
        return {"phase": "scanning", "label": "Reading your music", "done": True, "line": line,
                "share": min(0.99, done / total) if done is not None and total else None}
    songs = _int(status.get("info total songs"))
    if songs:
        albums = _int(status.get("info total albums"))
        return {"phase": "ready", "label": "Ready", "share": 1.0, "done": True,
                "line": f"{songs:,} songs" + (f" on {albums:,} albums" if albums else "") + " in the library."}
    if has_locations:
        return {"phase": "waiting", "label": "About to read your music", "share": None, "done": False,
                "line": "Lyrion starts reading your folders in a moment."}
    return {"phase": "ready", "label": "Ready, no music yet", "share": 1.0, "done": True,
            "line": "Add where your music is in Settings → Sources → Lyrion Server."}


def counted(progressname: str) -> str:
    """What a scan step counts, by Lyrion's own name for it (its code:
    `<folder>|discovering_files`, `<folder>|audio_new`, `..._changed`,
    `..._deleted`, `precacheArtwork`, `updateStandaloneArtwork`). Measured on
    sofapi, 2026-10-18: after a restart Lyrion pre-loads its albums' artwork,
    46 of them - counted as files, it read "37 of 46 files" over 760 songs."""
    step = progressname.rsplit("|", 1)[-1].lower()
    if "artwork" in step:
        return "albums' artwork"
    if step.startswith("discovering"):
        return "files found"
    if step.endswith("_new"):
        return "new files read"
    if step.endswith("_changed"):
        return "changed files read"
    if step.endswith("_deleted"):
        return "removed files checked"
    return "steps"


def _int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
