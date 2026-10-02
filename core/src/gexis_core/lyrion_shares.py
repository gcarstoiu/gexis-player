# SPDX-License-Identifier: GPL-3.0-or-later
"""**The Lyrion server's network shares** (ADR-0115 decisions 7 and 9): the
folders on a NAS or a computer that it plays from, each mounted read-only
under `/mnt/gexis-shares` and offered to the server by `lyrion_folders`.

A share is SMB (`//nas/music`, with a user and a password) or NFS
(`nas:/music`, with neither). They are kept in the settings store under
`lyrion-server.shares`; an SMB password reaches `mount` only through a
credentials file readable by root, never on a command line.
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
        shares = [s for s in self.all() if s["address"] != address]
        shares.append({"address": address, "user": user if which == "smb" else None,
                       "password": password if which == "smb" else None})
        self._save(shares)

    def forget(self, address: str) -> None:
        self._unmount(self._root / slug(address))
        (self._credentials / f"{slug(address)}.cred").unlink(missing_ok=True)
        self._save([s for s in self.all() if s["address"] != address])
        self.errors.pop(address, None)

    def items(self) -> list[dict]:
        """The list's rows: each share and whether it is mounted."""
        out = []
        for share in self.all():
            address = share["address"]
            if self._is_mount(str(self._root / slug(address))):
                meta = "Mounted, read-only"
            elif address in self.errors:
                meta = f"Not mounted: {self.errors[address]}"
            else:
                meta = "Waiting for the server to be on"
            out.append({"name": address, "meta": meta, "bars": None, "state": "saved"})
        return out

    def mount_all(self) -> None:
        """Every share mounted; any folder here that is no longer one, gone."""
        wanted = {slug(s["address"]): s for s in self.all()}
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
            self._credentials.mkdir(parents=True, exist_ok=True, mode=0o700)
            cred = self._credentials / f"{slug(address)}.cred"
            cred.touch(mode=0o600)
            cred.write_text(f"username={share.get('user') or ''}\npassword={share.get('password') or ''}\n")
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
