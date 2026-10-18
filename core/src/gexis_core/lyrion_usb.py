# SPDX-License-Identifier: GPL-3.0-or-later
"""**The folders Lyrion reads from USB drives** (ADR-0115 decisions 20-24,
George 2026-10-18: *"What we need to add though is a folder selection from
USB"*; *"Nothing should be preselected"*).

`lyrion-server.usb_folders` holds what was chosen, one entry per folder:
the drive, known by its filesystem's UUID - the name it is mounted under,
`/media/gexis-usb/<UUID>`, by the package's udev rule - the folder inside it
(`""` for the whole drive), and the drive's label, kept for the row while it
is unplugged. **A drive plugged in for the first time is not added**
(*"1b"*): it is offered in the sheet until folders are chosen.

A folder is browsed read-only, folders only. Adding a folder that a chosen
one already holds is refused - it is in Lyrion already - and adding one
that holds chosen folders replaces them, since Lyrion would otherwise read
the same files twice.

Lyrion's list itself is `lyrion_folders.sync`'s, from `paths()`.
"""
from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath

from gexis_core.lyrion_folders import USB

KEY = "lyrion-server.usb_folders"
MUSIC_KEY = "lyrion-server.music_folder"
SWITCH_KEY = "lyrion-server.usb"
BY_UUID = Path("/dev/disk/by-uuid")
BY_LABEL = Path("/dev/disk/by-label")
#: What a drive carries for its own system, not music: never offered.
HIDDEN = {"System Volume Information", "$RECYCLE.BIN", "lost+found", "LOST.DIR"}


def _unescape(name: str) -> str:
    """udev writes a label's spaces and slashes as `\\x20`, `\\x2f`."""
    out, i = [], 0
    while i < len(name):
        if name.startswith("\\x", i) and len(name) >= i + 4:
            try:
                out.append(chr(int(name[i + 2:i + 4], 16)))
                i += 4
                continue
            except ValueError:
                pass
        out.append(name[i])
        i += 1
    return "".join(out)


def clean(folder: str) -> str:
    """A folder inside a drive, as stored: relative, no `..`, no slashes at
    the ends. Raises ValueError for one that leaves the drive."""
    parts = [p for p in PurePosixPath(folder or "").parts if p not in ("", ".", "/")]
    if any(p == ".." for p in parts):
        raise ValueError("a folder inside the drive")
    return "/".join(parts)


def holds(outer: str, inner: str) -> bool:
    """Whether folder `outer` holds `inner` (or is it); `""` holds all."""
    return outer == "" or inner == outer or inner.startswith(outer + "/")


class UsbFolders:
    def __init__(self, store, root: Path = USB, is_mount=os.path.ismount,
                 by_uuid: Path = BY_UUID, by_label: Path = BY_LABEL) -> None:
        self._store = store
        self._root = root
        self._is_mount = is_mount
        self._by_uuid = by_uuid
        self._by_label = by_label

    # --- What was chosen: the store, on its own thread --------------------

    def all(self) -> list[dict]:
        value = self._store.get(KEY)
        try:
            chosen = json.loads(value) if isinstance(value, str) else (value or [])
        except ValueError:
            chosen = []
        out = []
        for entry in chosen if isinstance(chosen, list) else []:
            if isinstance(entry, dict) and isinstance(entry.get("drive"), str) and entry["drive"]:
                try:
                    folder = clean(str(entry.get("folder") or ""))
                except ValueError:
                    continue
                out.append({"drive": entry["drive"], "folder": folder, "label": entry.get("label")})
        return out

    def _save(self, chosen: list[dict]) -> None:
        self._store.set(KEY, json.dumps(chosen))

    def add(self, drive: str, folder: str, label: str | None) -> None:
        """Raises ValueError, as a sentence's end, when it cannot be added."""
        folder = clean(folder)
        if not drive or "/" in drive or drive in (".", ".."):
            raise ValueError("a USB drive that is plugged in")
        chosen = self.all()
        for entry in chosen:
            if entry["drive"] == drive and holds(entry["folder"], folder):
                where = entry["folder"] or "the whole drive"
                raise ValueError(f"nothing more: it is in {where}, which Lyrion reads already")
        kept = [e for e in chosen if not (e["drive"] == drive and holds(folder, e["folder"]))]
        kept.append({"drive": drive, "folder": folder, "label": label})
        self._save(kept)

    def remove(self, key: str) -> None:
        """`key` is an item's `address`: `<drive>/<folder>`."""
        drive, _, folder = key.partition("/")
        folder = clean(folder)
        self._save([e for e in self.all() if not (e["drive"] == drive and e["folder"] == folder)])

    def forget_all(self) -> None:
        """ADR-0115 decision 14: Remove takes the server's settings too."""
        for key in (KEY, MUSIC_KEY, SWITCH_KEY):
            self._store.delete(key)

    # --- The drives: the file system, off the loop ------------------------

    def drive_path(self, drive: str) -> Path:
        return self._root / drive

    def plugged(self) -> list[str]:
        """The drives mounted now, by UUID."""
        try:
            return sorted(p.name for p in self._root.iterdir() if p.is_dir() and self._is_mount(str(p)))
        except OSError:
            return []

    def label_of(self, drive: str) -> str | None:
        """The drive's own name, if its file system has one: the by-label
        link that leads to the same device as its by-uuid link."""
        try:
            device = (self._by_uuid / drive).resolve(strict=True)
            for link in self._by_label.iterdir():
                if link.resolve() == device:
                    return _unescape(link.name)
        except OSError:
            pass
        return None

    def browse(self, drive: str, folder: str) -> list[dict]:
        """The folders inside `folder` on a drive that is plugged in, each
        with whether it has folders of its own. Raises ValueError."""
        folder = clean(folder)
        if drive not in self.plugged():
            raise ValueError("the drive to be plugged in")
        top = self.drive_path(drive).resolve()
        here = (top / folder).resolve()
        if here != top and top not in here.parents:
            raise ValueError("a folder inside the drive")
        out = []
        try:
            entries = sorted(os.scandir(here), key=lambda e: e.name.casefold())
        except OSError as exc:
            raise ValueError("a folder that can be read") from exc
        for entry in entries:
            if entry.name.startswith(".") or entry.name in HIDDEN:
                continue
            try:
                if not entry.is_dir(follow_symlinks=False):
                    continue
                with os.scandir(entry.path) as inside:
                    deeper = any(e.is_dir(follow_symlinks=False) and not e.name.startswith(".")
                                 for e in inside)
            except OSError:
                continue
            out.append({"name": entry.name, "folder": f"{folder}/{entry.name}" if folder else entry.name,
                        "deeper": deeper})
        return out

    def paths(self, chosen: list[dict]) -> list[str]:
        """Each chosen folder as Lyrion reads it."""
        return [str(self.drive_path(e["drive"]) / e["folder"]) if e["folder"] else str(self.drive_path(e["drive"]))
                for e in chosen]

    # --- The rows ----------------------------------------------------------

    def name_of(self, drive: str, label: str | None) -> str:
        return label or f"USB drive {drive[:9]}"

    def items(self, chosen: list[dict], plugged: list[str], labels: dict[str, str | None]) -> list[dict]:
        """The row's own list: each chosen folder, on its drive, plugged in
        or not; then each drive plugged in with nothing chosen."""
        out = []
        for e in chosen:
            name = self.name_of(e["drive"], labels.get(e["drive"]) or e.get("label"))
            where = "Plugged in" if e["drive"] in plugged else "Unplugged - kept for 7 days"
            out.append({"name": e["folder"] or "Whole drive", "meta": f"{name} · {where}", "bars": None,
                        "state": "saved", "address": f"{e['drive']}/{e['folder']}"})
        added = {e["drive"] for e in chosen}
        for drive in plugged:
            if drive not in added:
                out.append({"name": self.name_of(drive, labels.get(drive)), "meta": "Not added yet - tap to choose its folders",
                            "bars": None, "state": "found", "drive": drive, "pending": True})
        return out

    def sheet_items(self, chosen: list[dict], plugged: list[str], labels: dict[str, str | None]) -> list[dict]:
        """The sheet's list: each drive plugged in, to browse."""
        out = []
        for drive in plugged:
            folders = [e["folder"] for e in chosen if e["drive"] == drive]
            names = [f.rsplit("/", 1)[-1] for f in folders if f]
            if "" in folders:
                meta = "Whole drive added"
            elif names:
                meta = "Added: " + ", ".join(names[:2]) + (f" and {len(names) - 2} more" if len(names) > 2 else "")
            else:
                meta = "Not added yet"
            meta += " · tap to see its folders"
            out.append({"name": self.name_of(drive, labels.get(drive)), "meta": meta, "bars": None,
                        "state": "found", "drive": drive})
        return out
