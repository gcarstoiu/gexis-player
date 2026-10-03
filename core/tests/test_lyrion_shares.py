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
    assert s.all() == [{"address": "nas:/music", "user": None}]


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
    assert {i["meta"] for i in s.items()} == {"On nas · Waiting for the server to be on"}
    s.mount_all(s.all())
    by = {i["address"]: i["meta"] for i in s.items()}
    assert by["//nas/music"] == "On nas · Mounted, read-only"
    assert by["//nas/locked"].startswith("On nas · Not mounted: mount error(13)")
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


def test_a_share_reads_as_its_name_on_its_server():
    """George, 2026-10-03: the row read "just code"."""
    assert ls.label("//Tower.local/Music") == ("Music", "Tower")
    assert ls.label("//nas/media/Music/") == ("Music", "nas")
    assert ls.label("nas.local:/volume1/music") == ("music", "nas")


def test_a_row_names_the_share_and_keeps_its_address_for_forget(tmp_path):
    s, _, _ = shares(tmp_path)
    s.add("//Tower.local/Music", "guest", None)
    [item] = s.items()
    assert item["name"] == "Music" and item["address"] == "//Tower.local/Music"
    assert item["meta"].startswith("On Tower · ")
    assert "password" not in item and "user" not in item, "a user only where it is asked for again"


def test_the_store_never_holds_a_password(tmp_path):
    """ADR-0115 decision 15: GET /settings and every backup read the store."""
    s, _, _ = shares(tmp_path)
    s.add("//nas/music", "george", "s3cret")
    assert "s3cret" not in str(s._store.values)
    assert s.all() == [{"address": "//nas/music", "user": "george"}]
    assert (tmp_path / "cred" / f"{ls.slug('//nas/music')}.cred").read_text() == \
        "username=george\npassword=s3cret\n"


def test_a_store_from_before_moves_its_passwords_to_their_files(tmp_path):
    s, _, _ = shares(tmp_path)
    s._store.set(ls.KEY, '[{"address": "//nas/music", "user": "me", "password": "pw"}, '
                         '{"address": "nas:/b", "user": null, "password": null}]')
    s.migrate()
    assert s.all() == [{"address": "//nas/music", "user": "me"}, {"address": "nas:/b", "user": None}]
    assert "password=pw" in (tmp_path / "cred" / f"{ls.slug('//nas/music')}.cred").read_text()
    s.migrate()  # nothing left to move, and nothing lost
    assert "password=pw" in (tmp_path / "cred" / f"{ls.slug('//nas/music')}.cred").read_text()


def test_a_share_restored_without_its_password_asks_for_it_and_is_not_mounted(tmp_path):
    """A backup carries the store, not the root-only file."""
    s, calls, mounted = shares(tmp_path)
    s._store.set(ls.KEY, '[{"address": "//nas/music", "user": "me"}, {"address": "//nas/open", "user": "guest"}]')
    s.mount_all(s.all())
    [locked, guest] = s.items()
    assert locked["login"] is True and locked["user"] == "me"
    assert "Needs its password again" in locked["meta"]
    assert not any("//nas/music" in c for c in calls if c[0] == "mount"), "no mount without a login"
    assert "login" not in guest and guest["meta"].endswith("Mounted, read-only"), "a guest has none to lose"
    s.add("//nas/music", "me", "pw")
    s.mount_all(s.all())
    assert s.items()[0]["meta"].endswith("Mounted, read-only")


def test_forgetting_them_all_empties_the_list(tmp_path):
    s, _, _ = shares(tmp_path)
    s.add("//nas/a", "me", "pw")
    s.add("nas:/b", None, None)
    assert s.forget_all() == ["//nas/a", "nas:/b"]
    assert s.all() == []


def test_points_name_every_saved_share_mounted_or_not(tmp_path):
    s, _, _ = shares(tmp_path)
    s.add("//nas/a", "me", "pw")
    s.add("nas:/b", None, None)
    assert s.points() == [str(tmp_path / "mnt" / ls.slug("//nas/a")), str(tmp_path / "mnt" / ls.slug("nas:/b"))]
