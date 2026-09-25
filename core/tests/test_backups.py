# SPDX-License-Identifier: GPL-3.0-or-later
"""**ADR-0083: a backup leaves the device.**

The share is guest-writable, so an archive in it is not necessarily one we
made. Most of what is tested here is that.
"""
from __future__ import annotations

import tarfile
import time

import pytest

from gexis_core import backups


def _device(root):
    """A device tree with the things a flash destroys."""
    (root / "var/lib/gexis-core").mkdir(parents=True)
    (root / "etc/gexis").mkdir(parents=True)
    (root / "var/lib/bluetooth/11:22").mkdir(parents=True)
    (root / "var/lib/gexis-core/settings.db").write_text("settings")
    (root / "var/lib/gexis-core/enrichment.db").write_text("enrichment")
    (root / "etc/gexis/core.toml").write_text('idle_url = "secret"')
    (root / "etc/gexis/device-name.env").write_text("NAME=gexis")
    (root / "var/lib/bluetooth/11:22/info").write_text("paired")
    return root


def test_it_holds_what_a_flash_destroys(tmp_path):
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    name = backups.create("gexis", out, root)

    with tarfile.open(out / name) as archive:
        held = set(archive.getnames())
    for member in backups.MEMBERS:
        assert any(n == member or n.startswith(member + "/") for n in held), member


def test_a_missing_member_is_skipped_not_fatal(tmp_path):
    """A device that has never paired anything has no /var/lib/bluetooth, and
    that is not an error."""
    root = _device(tmp_path / "root")
    for path in (root / "var/lib/bluetooth/11:22/info", root / "var/lib/bluetooth/11:22",
                 root / "var/lib/bluetooth"):
        path.rmdir() if path.is_dir() else path.unlink()

    name = backups.create("gexis", tmp_path / "out", root)
    assert (tmp_path / "out" / name).is_file()


def test_the_name_carries_the_device_and_the_time(tmp_path):
    name = backups.create("Living Room!", tmp_path / "out", _device(tmp_path / "root"))
    assert name.startswith("gexis-living-room-")
    assert backups.NAME.match(name)


def test_a_half_written_archive_is_never_listed(tmp_path, monkeypatch):
    """The share is read by a person who cannot tell a partial file from a
    whole one, so it is written aside and renamed."""
    root, out = _device(tmp_path / "root"), tmp_path / "out"

    real = tarfile.open

    def explode(*args, **kwargs):
        handle = real(*args, **kwargs)
        original = handle.add

        def boom(*a, **k):
            original(*a, **k)
            raise OSError("no space left on device")

        handle.add = boom
        return handle

    monkeypatch.setattr(tarfile, "open", explode)
    with pytest.raises(OSError):
        backups.create("gexis", out, root)

    assert backups.available(out) == []
    assert not list(out.glob("*.tgz"))


def test_only_our_own_archives_are_listed(tmp_path):
    """Anyone on the LAN can drop anything in there."""
    out = tmp_path / "out"
    backups.create("gexis", out, _device(tmp_path / "root"))
    (out / "holiday-photos.tgz").write_text("not ours")
    (out / "notes.txt").write_text("not ours either")
    (out / "sub").mkdir()

    listed = backups.available(out)
    assert len(listed) == 1
    assert backups.NAME.match(listed[0].name)


def test_newest_first(tmp_path):
    out = tmp_path / "out"
    root = _device(tmp_path / "root")
    first = backups.create("gexis", out, root)
    time.sleep(0.01)
    (out / first).touch()
    second = out / "gexis-gexis-20200101-000000.tgz"
    second.write_bytes((out / first).read_bytes())
    import os
    os.utime(second, (0, 0))

    assert [a.name for a in backups.available(out)] == [first, second.name]


def test_a_missing_directory_is_no_backups_not_a_crash(tmp_path):
    assert backups.available(tmp_path / "never-made") == []


# ---------------------------------------------------------------------------
# Restore, where the share being writable by anyone starts to matter.
# ---------------------------------------------------------------------------


def _hostile(path, member_name, *, link_to=None):
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo(member_name)
        if link_to:
            info.type = tarfile.SYMTYPE
            info.linkname = link_to
            archive.addfile(info)
        else:
            payload = b"pwned"
            info.size = len(payload)
            import io
            archive.addfile(info, io.BytesIO(payload))


def test_restore_puts_it_back(tmp_path):
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    name = backups.create("gexis", out, root)
    (root / "var/lib/gexis-core/settings.db").write_text("clobbered")

    backups.restore(name, out, root)
    assert (root / "var/lib/gexis-core/settings.db").read_text() == "settings"


def test_a_name_that_is_not_ours_is_refused(tmp_path):
    for name in ("../../etc/passwd", "holiday.tgz", "gexis-x-1.tgz", "a/b.tgz"):
        with pytest.raises(ValueError):
            backups.restore(name, tmp_path, tmp_path)


def test_an_archive_that_writes_outside_our_paths_is_refused(tmp_path):
    """**The one that matters.** Anyone on the LAN can put a file in that
    share, and `extractall` would happily write `etc/shadow`."""
    out = tmp_path / "out"
    out.mkdir()
    name = "gexis-gexis-20260925-120000.tgz"
    _hostile(out / name, "etc/shadow")

    with pytest.raises(ValueError, match="refuses to write"):
        backups.restore(name, out, tmp_path / "root")
    assert not (tmp_path / "root").exists()


def test_a_link_is_refused(tmp_path):
    """A symlink member is how an archive writes somewhere its names do not
    mention."""
    out = tmp_path / "out"
    out.mkdir()
    name = "gexis-gexis-20260925-120000.tgz"
    _hostile(out / name, "var/lib/gexis-core/settings.db", link_to="/etc/shadow")

    with pytest.raises(ValueError, match="refuses a link"):
        backups.restore(name, out, tmp_path / "root")


def test_restoring_something_that_is_not_there(tmp_path):
    with pytest.raises(FileNotFoundError):
        backups.restore("gexis-gexis-20260925-120000.tgz", tmp_path, tmp_path)


def test_forget_removes_only_ours(tmp_path):
    out = tmp_path / "out"
    name = backups.create("gexis", out, _device(tmp_path / "root"))
    backups.forget(name, out)
    assert backups.available(out) == []
    with pytest.raises(ValueError):
        backups.forget("../settings.db", out)
