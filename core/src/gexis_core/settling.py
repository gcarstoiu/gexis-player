# SPDX-License-Identifier: GPL-3.0-or-later
"""**The first start after setup, until the player has settled** (ADR-0128).

Setup chooses a skin pack and plugins; each downloads once the player is on
the home network - after setup's restart, more often than not. Until then the
panel says what it is waiting for, each download with its progress, then
*Ready*. George, 2026-10-07: it **cannot be skipped**, and **a download that
fails is left for Settings, and the owner is told**: the screen names what did
not finish and where to try again, and waits for OK.

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


def end(path: Path = PATH) -> None:
    path.unlink(missing_ok=True)


def view(record: dict | None, status: dict, now: float | None = None) -> dict | None:
    """What the screen shows: each item's state - `waiting`, `busy` (with
    `received`/`total`), `done` or `failed` (with `error`) - and the phase,
    `settling` while any is waiting or busy, then `ready` or `failed`."""
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
        if state == "installed":
            entry["state"] = "done"
        elif state == "failed":
            entry["state"] = "failed"
            entry["error"] = live.get("error")
        elif state in BUSY:
            entry["state"] = "busy"
        elif now - float(record.get("started") or now) > WAIT_S:
            entry["state"] = "failed"
            entry["error"] = "The download did not start"
        else:
            entry["state"] = "waiting"
        items.append(entry)
    states = {i["state"] for i in items}
    phase = "settling" if states & {"waiting", "busy"} else ("failed" if "failed" in states else "ready")
    return {"phase": phase, "items": items}
