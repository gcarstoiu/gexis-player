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
again - two hours for George's tens of thousands of files - so a NAS that is off when the
player starts must not take its folder out. Only Forget does. **A USB disk
stays for 7 days after it is unplugged** (decision 17; George: *"decision A,
but 7 days not more"*), remembered by when it was last seen mounted.

**Lyrion scans on the change itself** (its `Slim/Utils/Prefs.pm`, read
2026-10-03): a folder added is scanned on its own; a folder taken away wipes
the library and scans everything again. So nothing here asks for a rescan.
It did until 2026-10-03, and adding George's NAS share scanned its tens of thousands of files and then queued a second walk of them all.
"""
from __future__ import annotations

import asyncio

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
#: A disk still mounted is seen again no oftener than this: the record is
#: written only when it changes, not on every 20 s pass (review,
#: 2026-10-12), and an hour is nothing against 7 days.
USB_SEEN_EVERY_S = 3600


def size_text(n: int) -> str:
    """Bytes as a phone shows them: decimal units, one decimal under 100."""
    for unit, size in (("TB", 10**12), ("GB", 10**9), ("MB", 10**6)):
        if n >= size:
            value = n / size
            return f"{value:.1f} {unit}" if value < 100 else f"{value:.0f} {unit}"
    return f"{n} bytes"


def music_space(music: Path = MUSIC) -> dict | None:
    """**The Music folder's room** (George, 2026-10-18: "For music folder
    display total available and free space"): the file system it is on,
    free and total, in bytes and as text. None when it cannot be read."""
    import shutil

    try:
        usage = shutil.disk_usage(music if music.exists() else music.parent)
    except OSError:
        return None
    return {"free": usage.free, "total": usage.total,
            "text": f"{size_text(usage.free)} free of {size_text(usage.total)}"}


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
    before = dict(seen)
    for folder in mounted_now:
        at = seen.get(folder)
        if folder.startswith(str(USB) + "/") and not (isinstance(at, (int, float))
                                                      and 0 <= now - at < USB_SEEN_EVERY_S):
            seen[folder] = now
    seen = {folder: at for folder, at in seen.items()
            if isinstance(at, (int, float)) and now - at <= keep_s}
    if seen != before:
        _write(path, json.dumps(seen, indent=1))
    return sorted(seen)


def _write(path: Path, text: str) -> None:
    """Whole or not at all. A record cut short by a power cut reads as no
    disk ever seen, and an unplugged disk's folder then leaves Lyrion's
    list - which Lyrion answers by wiping the library and scanning it all
    again (review, 2026-10-12)."""
    tmp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "w") as out:
            out.write(text)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    except OSError as exc:
        logger.info("lyrion: could not keep when USB disks were seen (%s)", exc)


def mounted(root: Path, is_mount: Callable[[str], bool] = os.path.ismount) -> list[str]:
    """Each folder under `root` that has something mounted on it."""
    try:
        return sorted(str(p) for p in root.iterdir() if p.is_dir() and is_mount(str(p)))
    except OSError:
        return []


def wanted(current: list[str], present: list[str], music: Path = MUSIC,
           managed: tuple[Path, ...] | None = None, saved: list[str] = (), music_on: bool = True) -> list[str]:
    """`current` with the Music folder (while it is switched on) and the
    present folders in, the managed folders that are gone out - except a
    saved one's, present or not - and the user's own untouched, in their
    order. The Music folder is managed only while it is switched off
    (ADR-0115 decision 20): then it goes, and a folder of the user's inside
    it stays."""
    managed = MANAGED if managed is None else managed

    def ours(path: str) -> bool:
        return (any(path == str(m) or path.startswith(str(m) + "/") for m in managed)
                or (not music_on and path == str(music)))

    present = [str(music), *present] if music_on else list(present)
    kept = [p for p in current if not ours(p) or p in present or p in saved]
    for path in present:
        if path not in kept:
            kept.append(path)
    return kept


async def sync(rpc: Callable[[list], Awaitable[dict]], is_mount=os.path.ismount,
               saved: list[str] = (), usb_seen: Path = USB_SEEN, music_on: bool = True,
               usb_chosen: list[str] | None = None) -> bool:
    """Bring the server's folders up to date; True if they changed - Lyrion
    then scans what the change needs. A server that does not answer changes
    nothing.

    `usb_chosen`: the USB folders chosen (ADR-0115 decision 23), as paths;
    `None` is every drive mounted, whole, as before the choice existed. A
    chosen folder is present while its drive is mounted and the folder is
    there, and kept for 7 days after its drive was last seen (decision 17)."""
    result = await rpc(["pref", "mediadirs", "?"])
    current = result.get("_p2") or []
    if isinstance(current, str):
        current = [current]
    # Off the loop: a mount point on a server that is switched off can hold
    # `ismount` for seconds, every 20 s (review, 2026-10-12).
    def look() -> tuple[list[str], list[str]]:
        usb, shares_root = MANAGED
        drives = mounted(usb, is_mount)
        recent = usb_recent(drives, usb_seen)
        if usb_chosen is None:
            usb_present, usb_keep = drives, recent
        else:
            def drive_of(path: str) -> str:
                return str(usb / Path(path).relative_to(usb).parts[0])
            usb_present = [p for p in usb_chosen if drive_of(p) in drives and os.path.isdir(p)]
            usb_keep = [p for p in usb_chosen if drive_of(p) in recent]
        shares = mounted(shares_root, is_mount)
        return [*usb_present, *shares], [*saved, *usb_keep]
    present, keep = await asyncio.to_thread(look)
    want = wanted(list(current), present, saved=keep, music_on=music_on)
    if want == list(current):
        return False
    await rpc(["pref", "mediadirs", want])
    logger.info("lyrion: music folders %s (were %s); Lyrion scans the change", want, current)
    return True
