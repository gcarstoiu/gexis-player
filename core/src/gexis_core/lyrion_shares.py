# SPDX-License-Identifier: GPL-3.0-or-later
"""**The Lyrion server's network shares** (ADR-0115 decisions 7 and 9): the
folders on a NAS or a computer that it plays from, each mounted read-only
under `/mnt/gexis-shares` and offered to the server by `lyrion_folders`.

A share is SMB (`//nas/music`, with a user and a password) or NFS
(`nas:/music`, with neither). They are kept in the settings store under
`lyrion-server.shares` - the address and the user. **The password is not**
(ADR-0115 decision 15, George, 2026-10-03: *"B"*): it is written once, when
the share is added, to a credentials file readable by root - the one `mount`
reads, never a command line - so neither `GET /settings` nor a backup
carries it. A share restored without its file asks for the password again.

**The store is read on the core's own thread, mounting is done in another**
(found on George's player, 2026-10-03: SQLite refuses a connection from a
thread that did not open it, and every Add and every loop failed with it).
So `mount_all`, `unmount_all` and `release` take what they need as
arguments and never touch the store; everything that does is cheap.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

KEY = "lyrion-server.shares"
ROOT = Path("/mnt/gexis-shares")
CREDENTIALS = Path("/etc/gexis/shares")
SMB = re.compile(r"^//[^/\s]+/[^\s].*$")
NFS = re.compile(r"^[^/:\s]+:/(?!/).*$")  # not a URL: "http://..." has two slashes


def kind(address: str) -> str | None:
    if SMB.match(address):
        return "smb"
    if NFS.match(address):
        return "nfs"
    return None


def slug(address: str) -> str:
    """The mount point's name: readable, and unique by a short hash."""
    readable = re.sub(r"[^A-Za-z0-9]+", "-", address).strip("-")[:40] or "share"
    return f"{readable}-{hashlib.sha256(address.encode()).hexdigest()[:6]}"


def label(address: str) -> tuple[str, str]:
    """(the share's own name, its server's) as a person says them: "Music"
    and "Tower" for `//Tower.local/Music`, "music" and "nas" for
    `nas.local:/volume1/music` (George, 2026-10-03: the row read "just
    code")."""
    if address.startswith("//"):
        host, _, path = address[2:].partition("/")
    else:
        host, _, path = address.partition(":")
    name = path.rstrip("/").rsplit("/", 1)[-1] or path or address
    server = host.removesuffix(".local") or host
    return name, server


class Shares:
    def __init__(self, store, root: Path = ROOT, credentials: Path = CREDENTIALS, run=subprocess.run,
                 is_mount=os.path.ismount) -> None:
        self._store = store
        self._root = root
        self._credentials = credentials
        self._run = run
        self._is_mount = is_mount
        #: The last mount error per share, said in its row.
        self.errors: dict[str, str] = {}

    def all(self) -> list[dict]:
        value = self._store.get(KEY)
        try:
            shares = json.loads(value) if isinstance(value, str) else (value or [])
        except ValueError:
            shares = []
        return [s for s in shares if isinstance(s, dict) and s.get("address")]

    def _save(self, shares: list[dict]) -> None:
        self._store.set(KEY, json.dumps(shares))

    def add(self, address: str, user: str | None, password: str | None) -> None:
        address = (address or "").strip()
        which = kind(address)
        if which is None:
            raise ValueError("an address like //nas/music (SMB) or nas:/music (NFS)")
        if which == "smb" and not user:
            raise ValueError("an SMB share needs a user")
        if which == "smb":
            self._write_login(address, user, password)
        shares = [s for s in self.all() if s["address"] != address]
        shares.append({"address": address, "user": user if which == "smb" else None})
        self._save(shares)
        # Mounted again with the new login, not left on the old one.
        self.errors.pop(address, None)

    def migrate(self) -> None:
        """Stores written before decision 15 held the password: each moves to
        its file and out of the store. Once, at start."""
        shares = self.all()
        if not any("password" in s for s in shares):
            return
        for share in shares:
            password = share.pop("password", None)
            if kind(share["address"]) == "smb" and not self._login(share["address"]).exists():
                self._write_login(share["address"], share.get("user"), password)
        self._save(shares)
        logger.info("lyrion: share passwords moved out of the settings store")

    def forget_all(self) -> list[str]:
        """Every share out of the list (ADR-0115 decision 14: Remove); the
        caller `release`s each address returned, in a worker."""
        addresses = [s["address"] for s in self.all()]
        self._save([])
        self.errors.clear()
        return addresses

    def _login(self, address: str) -> Path:
        return self._credentials / f"{slug(address)}.cred"

    def _write_login(self, address: str, user: str | None, password: str | None) -> None:
        self._credentials.mkdir(parents=True, exist_ok=True, mode=0o700)
        cred = self._login(address)
        cred.touch(mode=0o600)
        cred.chmod(0o600)
        cred.write_text(f"username={user or ''}\npassword={password or ''}\n")

    def _needs_login(self, share: dict) -> bool:
        """An SMB share whose password is not on this device (restored from a
        backup, which does not carry it). A guest has none to lose."""
        return (kind(share["address"]) == "smb" and not self._login(share["address"]).exists()
                and (share.get("user") or "").lower() != "guest")

    def forget(self, address: str) -> None:
        """Out of the list; `release` (in a worker) unmounts it."""
        self._save([s for s in self.all() if s["address"] != address])
        self.errors.pop(address, None)

    def release(self, address: str) -> None:
        """Unmount a forgotten share and remove its credentials. No store."""
        self._unmount(self._root / slug(address))
        self._login(address).unlink(missing_ok=True)

    def items(self) -> list[dict]:
        """The list's rows: each share and whether it is mounted."""
        out = []
        for share in self.all():
            address = share["address"]
            name, server = label(address)
            if self._needs_login(share):
                out.append({"name": name, "meta": f"On {server} · Needs its password again - tap to enter it",
                            "bars": None, "state": "saved", "address": address, "login": True,
                            "user": share.get("user")})
                continue
            if self._is_mount(str(self._root / slug(address))):
                meta = "Mounted, read-only"
            elif address in self.errors:
                meta = f"Not mounted: {self.errors[address]}"
            else:
                meta = "Waiting for the server to be on"
            out.append({"name": name, "meta": f"On {server} · {meta}", "bars": None, "state": "saved",
                        "address": address})
        return out

    def mount_all(self, shares: list[dict]) -> None:
        """Every share in `shares` (as `all()` read them) mounted; any folder
        here that is no longer one, gone. No store: runs in a worker."""
        wanted = {slug(s["address"]): s for s in shares}
        self._root.mkdir(parents=True, exist_ok=True)
        for folder in self._root.iterdir():
            if folder.is_dir() and folder.name not in wanted:
                self._unmount(folder)
        for name, share in wanted.items():
            point = self._root / name
            if self._is_mount(str(point)):
                continue
            point.mkdir(exist_ok=True)
            error = self._mount(share, point)
            if error:
                self.errors[share["address"]] = error
            else:
                self.errors.pop(share["address"], None)

    def unmount_all(self) -> None:
        if not self._root.is_dir():
            return
        for folder in self._root.iterdir():
            if folder.is_dir():
                self._unmount(folder)

    def _mount(self, share: dict, point: Path) -> str | None:
        address = share["address"]
        if kind(address) == "smb":
            cred = self._login(address)
            if not cred.exists():
                if self._needs_login(share):
                    return "Needs its password again"
                self._write_login(address, share.get("user"), None)  # a guest, restored
            command = ["mount", "-t", "cifs", address, str(point), "-o",
                       f"ro,credentials={cred},uid=squeezeboxserver,gid=nogroup,iocharset=utf8,nosuid,nodev,noexec"]
        else:
            command = ["mount", "-t", "nfs", address, str(point), "-o", "ro,soft,timeo=100,nosuid,nodev,noexec"]
        result = self._run(command, capture_output=True, text=True, timeout=30, check=False)
        if result.returncode:
            error = (result.stderr or result.stdout or f"mount exited {result.returncode}").strip().splitlines()[-1]
            logger.warning("lyrion: %s not mounted: %s", address, error)
            return error[:120]
        logger.info("lyrion: %s mounted read-only at %s", address, point)
        return None

    def _unmount(self, point: Path) -> None:
        if self._is_mount(str(point)):
            self._run(["umount", "-l", str(point)], capture_output=True, text=True, timeout=30, check=False)
        try:
            point.rmdir()
        except OSError:
            pass
