# SPDX-License-Identifier: GPL-3.0-or-later
"""**The Lyrion server's music folders** (ADR-0115 decisions 3 and 9): the
device's own Music folder, every USB disk that is mounted, and every network
share that is mounted, offered to the server on this device as its
`mediadirs`.

Lyrion keeps the list itself, in its own preferences, and a user may add
folders on Lyrion's own page (decision 4). So this never replaces the list:
it adds the folders it manages that are there, takes away the ones it
manages that are gone, and leaves every other folder as the user set it.
A change is followed by a rescan, at the server's own low priority.
"""
from __future__ import annotations

import logging
import os
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


def mounted(root: Path, is_mount: Callable[[str], bool] = os.path.ismount) -> list[str]:
    """Each folder under `root` that has something mounted on it."""
    try:
        return sorted(str(p) for p in root.iterdir() if p.is_dir() and is_mount(str(p)))
    except OSError:
        return []


def wanted(current: list[str], present: list[str], music: Path = MUSIC,
           managed: tuple[Path, ...] = MANAGED) -> list[str]:
    """`current` with the Music folder and the mounted folders in, the managed
    folders that are gone out, and the user's own untouched, in their order."""
    def ours(path: str) -> bool:
        return any(path == str(m) or path.startswith(str(m) + "/") for m in managed)

    kept = [p for p in current if not ours(p) or p in present]
    for path in [str(music), *present]:
        if path not in kept:
            kept.append(path)
    return kept


async def sync(rpc: Callable[[list], Awaitable[dict]], is_mount=os.path.ismount) -> bool:
    """Bring the server's folders up to date; True if they changed (and a
    rescan was asked for). A server that does not answer changes nothing."""
    result = await rpc(["pref", "mediadirs", "?"])
    current = result.get("_p2") or []
    if isinstance(current, str):
        current = [current]
    present = [d for root in MANAGED for d in mounted(root, is_mount)]
    want = wanted(list(current), present)
    if want == list(current):
        return False
    await rpc(["pref", "mediadirs", want])
    await rpc(["rescan"])
    logger.info("lyrion: music folders %s (were %s); rescanning", want, current)
    return True
