"""ADR-0115: the Lyrion server's network shares."""
from __future__ import annotations

import subprocess

import pytest

from gexis_core import lyrion_shares as ls


class Store:
    def __init__(self):
        self.values = {}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


def shares(tmp_path, *, fail=None, mounted=None):
    calls = []
    mounted = set() if mounted is None else mounted

    def run(command, **kw):
        calls.append(command)
        if command[0] == "mount":
            if fail and fail in command[3]:
                return subprocess.CompletedProcess(command, 32, "", "mount error(13): Permission denied")
            mounted.add(command[4])
        if command[0] == "umount":
            mounted.discard(command[-1])
        return subprocess.CompletedProcess(command, 0, "", "")

    s = ls.Shares(Store(), root=tmp_path / "mnt", credentials=tmp_path / "cred", run=run,
                  is_mount=lambda p: p in mounted)
    return s, calls, mounted


def test_smb_and_nfs_addresses_and_nothing_else():
    assert ls.kind("//nas/music") == "smb"
    assert ls.kind("nas.local:/volume1/music") == "nfs"
    for bad in ("nas/music", "//nas", "http://nas/music", ""):
        assert ls.kind(bad) is None


def test_an_smb_share_needs_a_user_and_an_nfs_one_keeps_no_secret(tmp_path):
    s, _, _ = shares(tmp_path)
    with pytest.raises(ValueError):
        s.add("//nas/music", None, "pw")
    with pytest.raises(ValueError):
        s.add("not an address", "me", "pw")
    s.add("nas:/music", "ignored", "ignored")
    assert s.all() == [{"address": "nas:/music", "user": None, "password": None}]


def test_mounting_reads_the_password_from_a_root_only_file(tmp_path):
    """Never on a command line, where any process can read it."""
    s, calls, _ = shares(tmp_path)
    s.add("//nas/music", "george", "s3cret")
    s.mount_all(s.all())
    mount = next(c for c in calls if c[0] == "mount")
    assert mount[:3] == ["mount", "-t", "cifs"] and "ro," in mount[-1]
    assert not any("s3cret" in part for part in mount)
    cred = next((tmp_path / "cred").iterdir())
    assert cred.read_text() == "username=george\npassword=s3cret\n"
    assert cred.stat().st_mode & 0o777 == 0o600


def test_rows_say_mounted_or_why_not(tmp_path):
    s, _, _ = shares(tmp_path, fail="//nas/locked")
    s.add("//nas/music", "me", "pw")
    s.add("//nas/locked", "me", "wrong")
    assert {i["meta"] for i in s.items()} == {"Waiting for the server to be on"}
    s.mount_all(s.all())
    by = {i["name"]: i["meta"] for i in s.items()}
    assert by["//nas/music"] == "Mounted, read-only"
    assert by["//nas/locked"].startswith("Not mounted: mount error(13)")
    assert {i["state"] for i in s.items()} == {"saved"}, "each with its Forget"


def test_forgetting_unmounts_and_removes_its_credentials(tmp_path):
    s, calls, mounted = shares(tmp_path)
    s.add("//nas/music", "me", "pw")
    s.mount_all(s.all())
    s.forget("//nas/music")
    s.release("//nas/music")
    assert s.all() == [] and not mounted
    assert ["umount", "-l", str(tmp_path / "mnt" / ls.slug("//nas/music"))] in calls
    assert list((tmp_path / "cred").iterdir()) == []


def test_switching_the_server_off_unmounts_every_share(tmp_path):
    s, _, mounted = shares(tmp_path)
    s.add("//nas/a", "me", "pw")
    s.add("nas:/b", None, None)
    s.mount_all(s.all())
    assert len(mounted) == 2
    s.unmount_all()
    assert not mounted


def test_the_store_is_only_touched_on_the_thread_that_opened_it(tmp_path):
    """Found on George's player, 2026-10-03: the real store is SQLite, which
    refuses another thread; mounting runs in one."""
    import asyncio

    from gexis_core.settings import SettingsStore

    store = SettingsStore(tmp_path / "s.db")
    s = ls.Shares(store, root=tmp_path / "mnt", credentials=tmp_path / "cred",
                  run=lambda c, **k: subprocess.CompletedProcess(c, 0, "", ""), is_mount=lambda p: False)
    s.add("nas:/music", None, None)

    async def loop_once():
        await asyncio.to_thread(s.mount_all, s.all())
        await asyncio.to_thread(s.unmount_all)
        s.forget("nas:/music")
        await asyncio.to_thread(s.release, "nas:/music")

    asyncio.run(loop_once())
    assert s.all() == []
