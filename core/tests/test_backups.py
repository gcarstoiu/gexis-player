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
    (root / "var/lib/go-librespot").mkdir(parents=True)
    (root / "var/lib/go-librespot/state.json").write_text('{"credentials": {}}')
    (root / "var/lib/gexis-core/settings.db").write_text("settings")
    (root / "var/lib/gexis-core/enrichment.db").write_text("enrichment")
    (root / "etc/gexis/core.toml").write_text('idle_url = "secret"')
    (root / "etc/gexis/device-name.env").write_text("NAME=gexis")
    (root / "var/lib/bluetooth/11:22/info").write_text("paired")
    (root / "var/lib/beszel-agent").mkdir(parents=True)
    (root / "var/lib/beszel-agent/fingerprint").write_text("ec4c41e0")
    # ADR-0114: the hub's history, systems and account.
    (root / "var/lib/beszel-hub").mkdir(parents=True)
    (root / "var/lib/beszel-hub/data.db").write_bytes(b"hub")
    # ADR-0115: the Lyrion server's settings and saved playlists.
    (root / "var/lib/squeezeboxserver/prefs").mkdir(parents=True)
    (root / "var/lib/squeezeboxserver/prefs/server.prefs").write_text("---\n")
    (root / "var/lib/gexis-music/Playlists").mkdir(parents=True)
    (root / "var/lib/gexis-music/Playlists/Evening.m3u").write_text("#EXTM3U\n")
    (root / "home/pi/.local/share/Plexamp/Settings").mkdir(parents=True)
    (root / "home/pi/.local/share/Plexamp/Settings/%40Plexamp%3Auser%3Atoken").write_text("Stoken")
    # ADR-0106: an uploaded plugin's data and the list of them.
    (root / "var/lib/private/gexis-uploaded/radiofoo").mkdir(parents=True)
    (root / "var/lib/private/gexis-uploaded/radiofoo/state").write_text("learned")
    (root / "var/lib/gexis").mkdir(parents=True, exist_ok=True)
    (root / "var/lib/gexis/plugins-known.json").write_text('{"radiofoo": {"version": "1.0.0"}}')
    return root


def test_it_holds_what_a_flash_destroys(tmp_path):
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    name = backups.create("gexis", out, root)

    with tarfile.open(out / name) as archive:
        held = set(archive.getnames())
    for member in backups.MEMBERS:
        assert any(n == member or n.startswith(member + "/") for n in held), member


def test_it_holds_the_spotify_pairing(tmp_path):
    """**The one the first backup missed.** George reflashed, the restore put
    everything else back, and the device came up as a brand-new never-paired
    Spotify player - `credentials: {username: "", data: null}`."""
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    name = backups.create("gexis", out, root)

    with tarfile.open(out / name) as archive:
        held = set(archive.getnames())
    assert "var/lib/go-librespot/state.json" in held


def test_it_leaves_go_librespots_config_to_the_image(tmp_path):
    """**ADR-0095.** `config.yml` is the image's; restored over a newer image it
    would name the device the renderer used to use."""
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    (root / "var/lib/go-librespot/config.yml").write_text("audio_device: output")
    name = backups.create("gexis", out, root)

    with tarfile.open(out / name) as archive:
        held = set(archive.getnames())
    assert "var/lib/go-librespot/config.yml" not in held


def test_an_old_archive_restores_the_pairing_and_not_the_config(tmp_path):
    """Every backup made before this change holds the whole directory. It must
    still restore - the pairing is why it exists - without the config."""
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    (root / "var/lib/go-librespot/config.yml").write_text("audio_device: output")
    out.mkdir()
    old = out / "gexis-gexis-20260925-120000.tgz"
    with tarfile.open(old, "w:gz") as archive:
        archive.add(root / "var/lib/go-librespot", arcname="var/lib/go-librespot")
        archive.add(root / "var/lib/gexis-core/settings.db", arcname="var/lib/gexis-core/settings.db")
    fresh = tmp_path / "fresh"
    backups.restore(old.name, out, fresh)
    assert (fresh / "var/lib/go-librespot/state.json").exists()
    assert not (fresh / "var/lib/go-librespot/config.yml").exists()
    assert (fresh / "var/lib/gexis-core/settings.db").exists()


def test_anything_else_outside_the_list_is_still_refused(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (tmp_path / "evil").write_text("x")
    bad = out / "gexis-gexis-20260925-120001.tgz"
    with tarfile.open(bad, "w:gz") as archive:
        archive.add(tmp_path / "evil", arcname="etc/sudoers.d/evil")
    with pytest.raises(ValueError):
        backups.restore(bad.name, out, tmp_path / "fresh")


def test_it_holds_the_beszel_fingerprint(tmp_path):
    """**The same lesson, applied before it could be learned twice** (ADR-0087).
    The agent's fingerprint is the identity the hub binds this system to, so a
    reflash that loses it is a device the hub no longer recognises - which is
    exactly what happened to the Spotify pairing above."""
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    name = backups.create("gexis", out, root)

    with tarfile.open(out / name) as archive:
        held = set(archive.getnames())
    assert "var/lib/beszel-agent/fingerprint" in held


def test_it_holds_the_plexamp_claim_and_puts_it_back(tmp_path):
    """**The third of these, and the one that was not caught in time.** George
    reflashed, restored, and Plexamp came up unclaimed and missing from the
    Plex player list; the claim token that made it is single-use. This one
    goes round the whole loop, because it is the first member under a home
    directory rather than /var/lib."""
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    name = backups.create("gexis", out, root)
    token = "home/pi/.local/share/Plexamp/Settings/%40Plexamp%3Auser%3Atoken"

    with tarfile.open(out / name) as archive:
        assert token in set(archive.getnames())

    fresh = tmp_path / "fresh"
    fresh.mkdir()
    backups.restore(name, out, fresh)
    assert (fresh / token).read_text() == "Stoken"


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


# -- ADR-0131: a backup uploaded in setup ------------------------------------

import json
import sqlite3


def _store(path, values):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.executemany("INSERT INTO settings VALUES (?, ?)", [(k, json.dumps(v)) for k, v in values.items()])
    conn.commit()
    conn.close()


def _real_device(root, values):
    _device(root)
    (root / "var/lib/gexis-core/settings.db").unlink()
    _store(root / "var/lib/gexis-core/settings.db", values)
    (root / "var/lib/bluetooth/DC:A6:32:00:00:01/9C:5A:44:11:22:33").mkdir(parents=True)
    (root / "var/lib/bluetooth/DC:A6:32:00:00:01/9C:5A:44:11:22:33/info").write_text("[LinkKey]")
    return root


VALUES = {"device_name": "Living Room", "timezone": "Europe/Berlin", "screen": 'Waveshare/13.3" HDMI LCD (H) (1920x1080)',
          "headless": False, "visualiser_skins": True, "plexamp.enabled": True, "beszel.enabled": False,
          "_settings_schema": 5, "volume_max": 80}


def test_inspect_says_what_a_backup_brings_without_putting_anything_back(tmp_path):
    root, out = _real_device(tmp_path / "root", VALUES), tmp_path / "out"
    name = backups.create("Living Room", out, root)
    seen = backups.inspect(out / name, known_migrations=5)
    assert seen["name"] == "Living Room"
    assert seen["settings"]["timezone"] == "Europe/Berlin"
    assert "volume_max" not in seen["settings"], "only what setup applies as its answers"
    assert seen["enabled"] == ["plexamp"]
    assert seen["newer"] is False
    assert "1 paired Bluetooth device" in seen["brings"]
    assert {"Spotify sign-in", "Plexamp's claim", "1 playlist"} <= set(seen["brings"])


def test_a_backup_from_a_newer_release_is_said(tmp_path):
    root, out = _real_device(tmp_path / "root", VALUES), tmp_path / "out"
    name = backups.create("x", out, root)
    assert backups.inspect(out / name, known_migrations=4)["newer"] is True


@pytest.mark.parametrize("make, sentence", [
    (lambda p: p.write_bytes(b"not an archive"), backups.NOT_A_BACKUP),
    (lambda p: p.write_bytes(b"\x1f\x8b\x08\x00truncated"), backups.NOT_A_BACKUP),
])
def test_what_is_not_a_backup_is_refused_in_words(tmp_path, make, sentence):
    path = tmp_path / "upload.tgz"
    make(path)
    with pytest.raises(backups.Refused) as refused:
        backups.inspect(path, known_migrations=5)
    assert str(refused.value) == sentence


def test_an_archive_with_foreign_paths_or_no_settings_is_refused(tmp_path):
    (tmp_path / "etc").mkdir()
    (tmp_path / "etc/passwd").write_text("root")
    foreign = tmp_path / "foreign.tgz"
    with tarfile.open(foreign, "w:gz") as archive:
        archive.add(tmp_path / "etc/passwd", arcname="etc/passwd")
    with pytest.raises(backups.Refused, match="holds more than"):
        backups.inspect(foreign, known_migrations=5)
    empty = tmp_path / "empty.tgz"
    (tmp_path / "etc/gexis").mkdir()
    (tmp_path / "etc/gexis/core.toml").write_text("")
    with tarfile.open(empty, "w:gz") as archive:
        archive.add(tmp_path / "etc/gexis/core.toml", arcname="etc/gexis/core.toml")
    with pytest.raises(backups.Refused, match="no settings"):
        backups.inspect(empty, known_migrations=5)


def test_settings_the_store_cannot_open_are_refused(tmp_path):
    """George: refused when *"a change in the sqlite schema ... would break
    the import completely"* - a store without its table, or not a database."""
    for content in (None, b"not sqlite at all"):
        root = _device(tmp_path / f"r{content is None}")
        db = root / "var/lib/gexis-core/settings.db"
        db.unlink()
        if content is None:
            sqlite3.connect(db).execute("CREATE TABLE other (x)").connection.commit()
        else:
            db.write_bytes(content * 100)
        name = backups.create("x", tmp_path / f"o{content is None}", root)
        with pytest.raises(backups.Refused, match="cannot be read"):
            backups.inspect(tmp_path / f"o{content is None}" / name, known_migrations=5)


def test_the_databases_are_renamed_into_place_not_overwritten(tmp_path):
    """ADR-0131 §5.4: the core holds the store open while setup restores; an
    open connection keeps the file it had."""
    root, out = _real_device(tmp_path / "root", VALUES), tmp_path / "out"
    name = backups.create("x", out, root)
    target = tmp_path / "new"
    (target / "var/lib/gexis-core").mkdir(parents=True)
    _store(target / "var/lib/gexis-core/settings.db", {"device_name": "gexis"})
    held = sqlite3.connect(target / "var/lib/gexis-core/settings.db")
    before = (target / "var/lib/gexis-core/settings.db").stat().st_ino
    backups.restore_file(out / name, target)
    assert (target / "var/lib/gexis-core/settings.db").stat().st_ino != before
    assert held.execute("SELECT value FROM settings WHERE key='device_name'").fetchone()[0] == '"gexis"'
    fresh = sqlite3.connect(target / "var/lib/gexis-core/settings.db")
    assert fresh.execute("SELECT value FROM settings WHERE key='device_name'").fetchone()[0] == '"Living Room"'
    assert (target / "var/lib/bluetooth/DC:A6:32:00:00:01/9C:5A:44:11:22:33/info").read_text() == "[LinkKey]"
    assert not list((target / "var/lib/gexis-core").glob(".*restoring"))


def test_made_is_the_time_in_the_name_or_the_newest_file(tmp_path):
    root, out = _real_device(tmp_path / "root", VALUES), tmp_path / "out"
    name = backups.create("x", out, root)
    stamp = time.mktime(time.strptime(name[-19:-4], "%Y%m%d-%H%M%S"))
    assert backups.inspect(out / name, 5)["made"] == stamp
    renamed = out / "my-backup.tgz"
    (out / name).rename(renamed)
    assert backups.inspect(renamed, 5)["made"] == max(m.mtime for m in tarfile.open(renamed).getmembers())
