# SPDX-License-Identifier: GPL-3.0-or-later
"""**The first start after setup, until the player has settled** (ADR-0128).

Setup chooses a skin pack and plugins; each downloads once the player is on
the home network - after setup's restart, more often than not. Until then the
panel says what it is waiting for, each download with its progress, then
*Ready*. **A download that fails is left for Settings, and the owner is
told**: the screen names what did not finish and where to try again, and
waits for OK (George, 2026-10-07).

**It can be put away at once** (ADR-0128 amended 2026-10-10; George: "the
settling screen should be dismissible much faster and the user should be told
of this. Otherwise it feels like being stuck"). `hide` marks the record; the
downloads go on, Settings shows how far they are, and the screen comes back
only if one of them fails - so the owner is still told.

Setup writes what to wait for (`begin`), by the names `/state`'s `components`
already carries (a plugin's component, `skins` for the pack); the core reads
it every few seconds (`view`) until it is finished with (`end`). The file is
what survives the restart in between.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger("gexis_core.settling")

PATH = Path("/var/lib/gexis/settling.json")
#: A download that has not begun this long after setup did not start - no
#: home network, most likely. Said as failed, so the screen can finish.
WAIT_S = 600.0
#: How long *Ready* stays up when everything finished.
READY_S = 4.0

BUSY = frozenset({"preparing", "downloading", "retrying", "verifying", "installing"})


def begin(items: list[dict], path: Path = PATH, now: float | None = None) -> None:
    """`items`: `{"id": <component name>, "name": <what the screen calls it>}`.
    Nothing to wait for writes nothing."""
    if not items:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps({"started": time.time() if now is None else now, "items": items}))
    tmp.replace(path)
    logger.info("settling: waiting for %s", ", ".join(i["name"] for i in items))


def read(path: Path = PATH) -> dict | None:
    try:
        record = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return record if isinstance(record, dict) and record.get("items") else None


def hide(path: Path = PATH) -> None:
    """The owner put the screen away; what it waits for is still followed."""
    record = read(path)
    if record is None or record.get("hidden"):
        return
    record["hidden"] = True
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(record))
    tmp.replace(path)
    logger.info("settling: put away by the owner; the downloads go on")


def end(path: Path = PATH) -> None:
    path.unlink(missing_ok=True)


def view(record: dict | None, status: dict, now: float | None = None) -> dict | None:
    """What the screen shows: each item's state - `waiting`, `busy` (with
    `received`/`total`), `done` or `failed` (with `error`) - and the phase,
    `settling` while any is waiting or busy, then `ready` or `failed` - and
    `hidden`, put away by the owner: true only while nothing has failed."""
    if not record:
        return None
    now = time.time() if now is None else now
    items = []
    for item in record["items"]:
        live = status.get(item["id"]) or {}
        state = live.get("state")
        # **A share as well as bytes** (George's bar player, 2026-10-09: the
        # skins "showed no progress in downloading and then all of a sudden it
        # was done"). A skin pack reports how far it is as a share - apt gives
        # no byte counts - and only bytes were passed on.
        entry = {"id": item["id"], "name": item.get("name") or live.get("label") or item["id"],
                 "received": live.get("received"), "total": live.get("total"),
                 "share": live.get("share"), "error": None}
        if item.get("follow"):
            # **Lyrion followed through its own steps** (ADR-0149 decision
            # 43; George, 2026-10-19: the plate "was showing something
            # getting ready and then the next minute the library was there in
            # full"): its download is the first of five, as the phone's
            # Getting ready numbers them.
            entry["steps"] = lyrion_steps(live)
        after = live.get("after") if state == "installed" else None
        if state == "installed" and item.get("follow") and (after or {}).get("phase") != "ready":
            # Installed, and Lyrion starting, adding its add-ons or reading -
            # or not yet read at all, a moment after its download.
            after = after or {"phase": "starting", "label": "Starting"}
            entry["state"] = "busy"
            entry["step"] = "after"
            entry["after"] = after.get("phase")
            entry["label"] = after.get("label")
            entry["line"] = after.get("line")
            entry["share"] = after.get("share") if after.get("phase") == "scanning" else None
            entry["received"] = entry["total"] = None
        elif state == "installed":
            entry["state"] = "done"
            if after:
                entry["line"] = after.get("line")
        elif state == "failed":
            entry["state"] = "failed"
            entry["error"] = live.get("error")
        elif state in BUSY:
            entry["state"] = "busy"
            # **Which step** (George, 2026-10-11: the skins sat at 100 % for
            # the 4 min 18 s their install took on the bar, which "might look
            # like a bug"): the screen says Installing once the download is in.
            entry["step"] = state
        elif now - float(record.get("started") or now) > WAIT_S:
            entry["state"] = "failed"
            entry["error"] = "The download did not start"
        else:
            entry["state"] = "waiting"
        items.append(entry)
    states = {i["state"] for i in items}
    phase = "settling" if states & {"waiting", "busy"} else ("failed" if "failed" in states else "ready")
    return {"phase": phase, "items": items, "hidden": bool(record.get("hidden")) and phase != "failed"}


def downloads_in(view_: dict | None) -> bool:
    """Every download done or failed - what follows a download (Lyrion
    reading the music, hours on a large library) not waited for. The core's
    restart for a server part 2 chose waits for this (decision 37), never
    for the read."""
    if not view_:
        return True
    return all(i["state"] in ("done", "failed") or i.get("step") == "after" for i in view_["items"])


#: What Lyrion adds after its first start, until it says which (lyrion_stage).
ADDONS = "Material Skin, Music & Artist Information and Radio Now Playing"


def lyrion_steps(live: dict) -> list[list[str]]:
    """**Lyrion as an ordered checklist**, `[text, "done" | "now" | "next"]`
    for each step - the download, its start, its add-ons, reading the music,
    ready - in the words the phone's Getting ready uses (ADR-0115 decision
    28, ADR-0149 decision 43)."""
    state, after = live.get("state"), live.get("after") or {}
    phase = after.get("phase")
    at = 0 if state != "installed" else {"starting": 1, "addons": 2, "waiting": 3, "scanning": 3, "ready": 4}.get(phase, 1)
    total, received, share = live.get("total"), live.get("received"), live.get("share")
    pct = round(100 * received / total) if total and received is not None else round(100 * share) if share is not None else None
    added = ", ".join(a["name"] + (" ✓" if a.get("in") else " (being retried)" if at > 2 else "")
                      for a in after.get("addons") or [])
    read = after.get("share") if phase == "scanning" else None
    texts = [
        "Download Lyrion · did not finish" if state == "failed"
        else f"Download Lyrion · {pct} %" if at == 0 and pct else "Download Lyrion",
        "Start Lyrion",
        f"Add {added or ADDONS} · one restart, about 3 minutes",
        f"Read your music · {round(read * 100)} %" if read is not None else "Read your music",
        f"Ready · {after.get('line')}" if at == 4 and after.get("line") else "Ready to browse",
    ]
    return [[text, "done" if i < at or (i == 4 and at == 4) else "now" if i == at else "next"]
            for i, text in enumerate(texts)]
