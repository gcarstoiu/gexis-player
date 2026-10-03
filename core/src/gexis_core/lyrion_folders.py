# SPDX-License-Identifier: GPL-3.0-or-later
"""**The Lyrion server's music folders** (ADR-0115 decisions 3 and 9): the
device's own Music folder, every USB disk that is mounted, and every network
share that is mounted, offered to the server on this device as its
`mediadirs`.

Lyrion keeps the list itself, in its own preferences, and a user may add
folders on Lyrion's own page (decision 4). So this never replaces the list:
it adds the folders it manages that are there, takes away the ones it
manages that are gone, and leaves every other folder as the user set it.
**A saved share stays in the list while it is not mounted** (ADR-0115
decision 16; George, 2026-10-03: *"clearly A"*). Lyrion answers a folder
taken out of its list by wiping the whole library and scanning everything
again - two hours for George's 61,362 files - so a NAS that is off when the
player starts must not take its folder out. Only Forget does. **A USB disk
stays for 7 days after it is unplugged** (decision 17; George: *"decision A,
but 7 days not more"*), remembered by when it was last seen mounted.

**Lyrion scans on the change itself** (its `Slim/Utils/Prefs.pm`, read
2026-10-03): a folder added is scanned on its own; a folder taken away wipes
the library and scans everything again. So nothing here asks for a rescan.
It did until 2026-10-03, and adding George's NAS share scanned its 61,362
files and then queued a second walk of them all.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

#: The device's own Music folder, always offered (decision 3).
MUSIC = Path("/var/lib/gexis-music")
#: Where a USB disk is mounted, read-only, by the package's udev rule.
USB = Path("/media/gexis-usb")
#: Where a network share is mounted, read-only.
SHARES = Path("/mnt/gexis-shares")
#: The folders this module manages: everything under these is ours to add
#: and to take away.
MANAGED = (USB, SHARES)
#: When each USB disk was last seen mounted (decision 17).
USB_SEEN = Path("/var/lib/gexis/lyrion-usb-seen.json")
USB_KEEP_S = 7 * 24 * 3600


def usb_recent(mounted_now: list[str], path: Path = USB_SEEN, now: float | None = None,
               keep_s: float = USB_KEEP_S) -> list[str]:
    """The USB folders seen mounted in the last 7 days, mounted now or not;
    what is mounted now is remembered as seen now, and older ones forgotten."""
    now = time.time() if now is None else now
    try:
        seen = json.loads(path.read_text())
        seen = seen if isinstance(seen, dict) else {}
    except (OSError, ValueError):
        seen = {}
    for folder in mounted_now:
        if folder.startswith(str(USB) + "/"):
            seen[folder] = now
    seen = {folder: at for folder, at in seen.items()
            if isinstance(at, (int, float)) and now - at <= keep_s}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(seen, indent=1))
    except OSError:
        pass
    return sorted(seen)


def mounted(root: Path, is_mount: Callable[[str], bool] = os.path.ismount) -> list[str]:
    """Each folder under `root` that has something mounted on it."""
    try:
        return sorted(str(p) for p in root.iterdir() if p.is_dir() and is_mount(str(p)))
    except OSError:
        return []


def wanted(current: list[str], present: list[str], music: Path = MUSIC,
           managed: tuple[Path, ...] = MANAGED, saved: list[str] = ()) -> list[str]:
    """`current` with the Music folder and the mounted folders in, the managed
    folders that are gone out - except a saved share's, mounted or not - and
    the user's own untouched, in their order."""
    def ours(path: str) -> bool:
        return any(path == str(m) or path.startswith(str(m) + "/") for m in managed)

    kept = [p for p in current if not ours(p) or p in present or p in saved]
    for path in [str(music), *present]:
        if path not in kept:
            kept.append(path)
    return kept


async def sync(rpc: Callable[[list], Awaitable[dict]], is_mount=os.path.ismount,
               saved: list[str] = (), usb_seen: Path = USB_SEEN) -> bool:
    """Bring the server's folders up to date; True if they changed - Lyrion
    then scans what the change needs. A server that does not answer changes
    nothing."""
    result = await rpc(["pref", "mediadirs", "?"])
    current = result.get("_p2") or []
    if isinstance(current, str):
        current = [current]
    present = [d for root in MANAGED for d in mounted(root, is_mount)]
    keep = [*saved, *usb_recent(present, usb_seen)]
    want = wanted(list(current), present, saved=keep)
    if want == list(current):
        return False
    await rpc(["pref", "mediadirs", want])
    logger.info("lyrion: music folders %s (were %s); Lyrion scans the change", want, current)
    return True
