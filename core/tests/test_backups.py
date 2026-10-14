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


def test_a_link_is_never_made(tmp_path):
    """A symlink member is how an archive writes somewhere its names do not
    mention. Under our paths it is left out (Finding 125 #5: refusing the
    archive for it made backups unrestorable); anywhere else the archive is
    still refused."""
    import os
    out = tmp_path / "out"
    out.mkdir()
    name = "gexis-gexis-20260925-120000.tgz"
    _hostile(out / name, "var/lib/gexis-core/settings.db", link_to="/etc/shadow")

    backups.restore(name, out, tmp_path / "root")
    assert not os.path.lexists(tmp_path / "root/var/lib/gexis-core/settings.db")

    _hostile(out / name, "etc/shadow", link_to="/tmp/x")
    with pytest.raises(ValueError, match="refuses to write"):
        backups.restore(name, out, tmp_path / "elsewhere")
    assert not (tmp_path / "elsewhere").exists()


@pytest.mark.parametrize("member", [
    # Under an allowed path by its first characters, then back out.
    "var/lib/bluetooth/../../../etc/cron.d/evil",
    "var/lib/bluetooth/11:22/../../../../etc/cron.d/evil",
    # A sibling that only starts like one of ours.
    "var/lib/bluetoothX/evil",
    "var/lib/gexis-core/settings.db.evil",
    # Absolute, and spelled so a prefix match would not see it.
    "/var/lib/bluetooth/evil",
    "./var/lib/bluetooth/evil",
    "var/lib/bluetooth//evil",
])
def test_a_member_that_climbs_out_of_our_paths_is_refused(tmp_path, member):
    """**The review of 2026-10-12.** The check matched names by their first
    characters, so `var/lib/bluetooth/../../../etc/cron.d/evil` passed it;
    on the device's Python 3.13 `extractall` follows the `..`, as root, and
    the reboot after a restore runs what it planted. Here the root is a
    folder, so the escape lands inside it - which is where we look."""
    out = tmp_path / "out"
    out.mkdir()
    name = "gexis-gexis-20260925-120000.tgz"
    _hostile(out / name, member)
    root = tmp_path / "root"

    with pytest.raises(ValueError, match="refuses"):
        backups.restore(name, out, root)
    assert not (root / "etc/cron.d/evil").exists()
    assert not list(tmp_path.rglob("evil"))


@pytest.mark.parametrize("kind", [tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE])
def test_a_hard_link_or_a_device_is_never_made(tmp_path, kind):
    """Left out under our paths (Finding 125 #5), refused anywhere else."""
    import os
    out = tmp_path / "out"
    out.mkdir()
    for where, root in (("var/lib/bluetooth/evil", tmp_path / "root"), ("etc/evil", tmp_path / "elsewhere")):
        name = "gexis-gexis-20260925-120000.tgz"
        with tarfile.open(out / name, "w:gz") as archive:
            info = tarfile.TarInfo(where)
            info.type = kind
            info.linkname = "/etc/shadow" if kind == tarfile.LNKTYPE else ""
            archive.addfile(info)
        if where.startswith("etc/"):
            with pytest.raises(ValueError, match="refuses"):
                backups.restore(name, out, root)
            assert not root.exists()
        else:
            assert backups.restore_file(out / name, root) == 0
            assert not os.path.lexists(root / where)


def test_a_setuid_bit_is_not_put_back(tmp_path):
    """A file under one of our paths, but marked to run as its owner."""
    import io
    out = tmp_path / "out"
    out.mkdir()
    name = "gexis-gexis-20260925-120000.tgz"
    with tarfile.open(out / name, "w:gz") as archive:
        info = tarfile.TarInfo("home/pi/.local/share/Plexamp/run")
        info.mode = 0o4755
        info.size = 5
        archive.addfile(info, io.BytesIO(b"pwned"))

    backups.restore(name, out, tmp_path / "root")
    assert (tmp_path / "root/home/pi/.local/share/Plexamp/run").stat().st_mode & 0o7000 == 0


def test_the_extraction_keeps_owners_and_refuses_what_escapes(tmp_path, monkeypatch):
    """**Not the default filter**: Python 3.13, on the device, has none (every
    file as the archive says, links and all), and 3.14's `data` would put
    Plexamp's claim back owned by root, where `pi` cannot write it. `tar`
    keeps owners and still refuses a path that leaves the root - decided
    for every member, now that the extraction is the module's own (Finding
    125 #1)."""
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    name = backups.create("gexis", out, root)
    seen = []
    real = tarfile.tar_filter

    def spy(member, dest_path):
        seen.append(member.name)
        return real(member, dest_path)

    monkeypatch.setattr(tarfile, "tar_filter", spy)
    count = backups.restore_file(out / name, tmp_path / "fresh")
    assert len(seen) == count and "var/lib/gexis-core/settings.db" in seen


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


# -- ADR-0083 as amended 2026-10-08: a backup downloaded ------------------------

def test_a_download_is_one_of_ours_by_name(tmp_path):
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    name = backups.create("gexis", out, root)
    assert backups.path_of(name, out) == out / name
    with pytest.raises(ValueError):
        backups.path_of("../settings.db", out)
    with pytest.raises(ValueError):
        backups.path_of("notes.txt", out)
    with pytest.raises(FileNotFoundError):
        backups.path_of("gexis-gone-20260101-000000.tgz", out)


@pytest.mark.asyncio
async def test_the_route_sends_it_as_a_file_to_save(tmp_path, monkeypatch):
    from aiohttp.test_utils import TestClient, TestServer
    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer

    root, out = _device(tmp_path / "root"), tmp_path / "out"
    name = backups.create("gexis", out, root)
    monkeypatch.setattr(backups, "DEFAULT_DIR", out)
    monkeypatch.setattr(backups.path_of, "__defaults__", (out,))
    async with TestClient(TestServer(StateServer(StateStore({})).make_app())) as client:
        r = await client.get(f"/backups/{name}")
        assert r.status == 200
        assert r.headers["Content-Disposition"] == f'attachment; filename="{name}"'
        assert await r.read() == (out / name).read_bytes()
        assert (await client.get("/backups/..%2Fsettings.db")).status in (400, 404)
        assert (await client.get("/backups/gexis-gone-20260101-000000.tgz")).status == 404


# -- the review of 2026-10-12: the Beszel hub's live database ------------------

def _live_hub(root):
    """The hub's PocketBase store as the hub leaves it while it runs: WAL
    mode, the newest rows still in `data.db-wal`. The connection returned
    is the hub, holding it open."""
    hub = root / "var/lib/beszel-hub"
    (hub / "data.db").unlink()
    conn = sqlite3.connect(hub / "data.db")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA wal_autocheckpoint=0")
    conn.execute("CREATE TABLE history (n INTEGER)")
    conn.executemany("INSERT INTO history VALUES (?)", [(n,) for n in range(3000)])
    conn.commit()
    assert (hub / "data.db-wal").stat().st_size > 0
    return conn


def test_a_live_database_is_backed_up_as_one_consistent_file(tmp_path):
    """The hub was tarred while it wrote: `data.db` and `data.db-wal` read at
    different moments restored to a state that never existed. Now a store
    with a WAL beside it goes in as SQLite's own copy of it, whole, and its
    WAL and index stay out."""
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    hub = _live_hub(root)
    name = backups.create("gexis", out, root)
    hub.close()

    with tarfile.open(out / name) as archive:
        held = set(archive.getnames())
        assert "var/lib/beszel-hub/data.db" in held
        assert not {"var/lib/beszel-hub/data.db-wal", "var/lib/beszel-hub/data.db-shm"} & held
        archive.extract("var/lib/beszel-hub/data.db", tmp_path / "x", filter="tar")
    copy = sqlite3.connect(tmp_path / "x/var/lib/beszel-hub/data.db")
    assert copy.execute("SELECT count(*) FROM history").fetchone()[0] == 3000
    assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_the_hub_is_stopped_before_its_files_are_put_back(tmp_path):
    """Restored under a running hub, its own WAL was checkpointed into the
    restored file at the reboot - "database disk image is malformed", both
    histories lost. The hub stops first; a WAL the archive does not bring is
    not left beside the file it brings."""
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    name = backups.create("gexis", out, root)
    target = _device(tmp_path / "target")
    (target / "var/lib/beszel-hub/data.db-wal").write_bytes(b"the running hub's")
    (target / "var/lib/beszel-hub/data.db-shm").write_bytes(b"its index")
    calls = []

    def run(argv, **kw):
        calls.append((argv, (target / "var/lib/beszel-hub/data.db-wal").exists()))
        import subprocess
        return subprocess.CompletedProcess(argv, 0, "", "")

    backups.restore_file(out / name, target, run=run)
    stops = [argv for argv, _ in calls if argv[:2] == ["systemctl", "stop"]]
    assert ["systemctl", "stop", "beszel-hub.service"] in stops
    assert not (target / "var/lib/beszel-hub/data.db-wal").exists()
    assert not (target / "var/lib/beszel-hub/data.db-shm").exists()
    assert (target / "var/lib/beszel-hub/data.db").read_bytes() == b"hub"


def test_an_archive_without_the_hub_leaves_it_running(tmp_path):
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    import shutil
    shutil.rmtree(root / "var/lib/beszel-hub")
    name = backups.create("gexis", out, root)
    calls = []
    backups.restore_file(out / name, _device(tmp_path / "target"), run=lambda argv, **kw: calls.append(argv))
    assert not any("beszel-hub" in " ".join(argv) for argv in calls)


def test_a_restore_that_fails_starts_the_hub_it_stopped(tmp_path, monkeypatch):
    import subprocess
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    name = backups.create("gexis", out, root)
    calls = []

    def run(argv, **kw):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")   # is-active: it was running

    def full(*a, **k):
        raise OSError("no space left on device")

    monkeypatch.setattr(backups, "_write_beside", full)
    with pytest.raises(OSError):
        backups.restore_file(out / name, _device(tmp_path / "target"), run=run)
    assert calls[-1] == ["systemctl", "start", "beszel-hub.service"]


# --- the updater's backups, kept three deep (George, 2026-10-12, answer 3) ---


def _archive(directory, name):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_bytes(b"x")
    return name


def test_an_updates_backup_is_named_as_one_and_still_restorable_by_an_older_core(tmp_path):
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    name = backups.create("Living Room", out, root, automatic=True)
    assert backups.AUTOMATIC.match(name), name
    assert name.startswith("gexis-living-room.before-update-")
    # Still a backup to the release an update goes back to.
    assert backups.NAME.match(name) and backups.SAFE.match(name)
    assert [a.name for a in backups.available(out)] == [name]


def test_a_backup_taken_by_hand_is_not_an_updates(tmp_path):
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    name = backups.create("Living Room", out, root)
    assert not backups.AUTOMATIC.match(name)


def test_no_device_name_makes_a_hand_backup_look_like_an_updates():
    """The mark is a `.`, which a device's name never becomes."""
    for device in ("before update", "x.before-update", "gexis.before-update", "Kitchen .before-update"):
        name = f"gexis-{backups._slug(device)}-20261012-101500.tgz"
        assert not backups.AUTOMATIC.match(name), name


def test_the_newest_three_updates_backups_are_kept_and_no_other_kind_is_touched(tmp_path):
    out = tmp_path / "out"
    autos = [_archive(out, f"gexis-den.before-update-2026100{d}-101500.tgz") for d in range(1, 7)]
    by_hand = [_archive(out, "gexis-den-20261001-090000.tgz"),
               _archive(out, "gexis-den-20261009-090000.tgz"),
               # From before the mark: kept, whatever its age.
               _archive(out, "gexis-den-20250101-000000.tgz"),
               _archive(out, "something-else.tgz")]
    gone = backups.prune_automatic(autos[-1], out)
    assert backups.KEEP_AUTOMATIC == 3
    assert sorted(gone) == autos[:3]
    left = {p.name for p in out.iterdir()}
    assert left == set(autos[3:]) | set(by_hand)


def test_the_one_just_made_is_kept_when_the_clock_came_up_behind(tmp_path):
    """No clock of its own: a Pi that has not reached a time server yet
    stamps a new backup older than the ones before it."""
    out = tmp_path / "out"
    older_clock = _archive(out, "gexis-den.before-update-20240101-000000.tgz")
    later = [_archive(out, f"gexis-den.before-update-2026100{d}-101500.tgz") for d in range(1, 5)]
    backups.prune_automatic(older_clock, out)
    left = sorted(p.name for p in out.iterdir())
    assert older_clock in left and len(left) == backups.KEEP_AUTOMATIC
    assert later[-2:] == left[-2:]


def test_three_or_fewer_are_all_kept(tmp_path):
    out = tmp_path / "out"
    autos = [_archive(out, f"gexis-den.before-update-2026100{d}-101500.tgz") for d in range(1, 4)]
    assert backups.prune_automatic(autos[-1], out) == []
    assert {p.name for p in out.iterdir()} == set(autos)


def test_settings_says_which_backups_an_update_made(tmp_path):
    out = tmp_path / "out"
    _archive(out, "gexis-den.before-update-20261001-101500.tgz")
    _archive(out, "gexis-den-20261002-101500.tgz")
    metas = {a.name: a.to_item()["meta"] for a in backups.available(out)}
    assert metas["gexis-den.before-update-20261001-101500.tgz"].endswith("· before an update")
    assert "update" not in metas["gexis-den-20261002-101500.tgz"]


def test_a_file_that_goes_while_the_backup_runs_is_left_out_not_the_backup(tmp_path, monkeypatch):
    """sofapi, 2026-10-13: an uploaded plugin's SQLite `-shm` file was listed,
    then deleted by its program before it was read, and the whole update
    backup failed with "No such file or directory"."""
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    data = root / "var/lib/private/gexis-uploaded/radiofoo/data"
    data.mkdir()
    (data / "settings.db-shm").write_bytes(b"shm")
    (data / "prefs.json").write_text("{}")
    real = tarfile.TarFile.gettarinfo

    def gone(self, name=None, arcname=None, fileobj=None):
        if str(name).endswith("settings.db-shm"):
            raise FileNotFoundError(2, "No such file or directory", str(name))
        return real(self, name, arcname, fileobj)

    monkeypatch.setattr(tarfile.TarFile, "gettarinfo", gone)
    name = backups.create("gexis", out, root)
    with tarfile.open(out / name) as archive:
        held = set(archive.getnames())
    assert "var/lib/private/gexis-uploaded/radiofoo/data/prefs.json" in held
    assert not any(n.endswith("settings.db-shm") for n in held)
    assert "var/lib/gexis-core/settings.db" in held, "the rest is all there"


def test_an_update_backup_that_failed_leaves_its_reason_and_a_new_one_clears_it(tmp_path):
    backups.update_backup_failed("disk full", tmp_path)
    assert (tmp_path / backups.FAILED_MARK).read_text() == "disk full\n"
    assert backups.available(tmp_path) == [], "never listed as a backup"
    backups.update_backup_failed(None, tmp_path)
    assert not (tmp_path / backups.FAILED_MARK).exists()


# --- Finding 125 (2026-10-14): the review of everything since 0.10.1 ---------

import os
import subprocess


@pytest.mark.parametrize("member, plant", [
    # A folder the archive writes into, already a link on the disk.
    ("var/lib/private/gexis-uploaded/radiofoo/link/evil", "link"),
    # The file itself, already a link on the disk.
    ("var/lib/private/gexis-uploaded/radiofoo/state", "state"),
])
def test_a_restore_never_writes_through_a_link_already_on_the_disk(tmp_path, member, plant):
    """**Finding 125 #1.** An uploaded plugin owns its data folder and can put
    a link in it; `extractall` as root followed it, and on the device, whose
    root is `/`, the `tar` filter's "outside the root" never fires. Here
    the link points inside the test's root, as everything does on `/`."""
    out = tmp_path / "out"
    out.mkdir()
    root = tmp_path / "root"
    plugin = root / "var/lib/private/gexis-uploaded/radiofoo"
    plugin.mkdir(parents=True)
    cron = root / "etc/cron.d"
    cron.mkdir(parents=True)
    victim = cron / "evil"
    if plant == "link":
        (plugin / "link").symlink_to(cron)
    else:
        victim.write_text("root's")
        (plugin / "state").symlink_to(victim)
    name = "gexis-gexis-20260925-120000.tgz"
    _hostile(out / name, member)

    with pytest.raises(ValueError, match="link already on the disk"):
        backups.restore(name, out, root)
    assert not victim.exists() or victim.read_text() == "root's"


def test_a_link_planted_after_the_check_is_still_not_followed(tmp_path, monkeypatch):
    """**Finding 125 #1**, the race: the plugin runs while the restore does.
    Each folder is opened without following a link, so one that appears
    between the look and the write is refused, not written through."""
    out = tmp_path / "out"
    out.mkdir()
    root = tmp_path / "root"
    plugin = root / "var/lib/private/gexis-uploaded/radiofoo"
    plugin.mkdir(parents=True)
    cron = root / "etc/cron.d"
    cron.mkdir(parents=True)
    name = "gexis-gexis-20260925-120000.tgz"
    _hostile(out / name, "var/lib/private/gexis-uploaded/radiofoo/link/evil")

    def plant(members, run):
        (plugin / "link").symlink_to(cron)
        return []

    monkeypatch.setattr(backups, "_stop_for_restore", plant)
    with pytest.raises((ValueError, OSError)):
        backups.restore(name, out, root)
    assert not (cron / "evil").exists()


def test_a_restore_still_puts_back_owners_modes_and_times(tmp_path):
    """**Finding 125 #1**: the extraction is the module's own now; what the
    `tar` filter decided still holds - modes kept less any setuid bit or
    write bit for others, times kept, folders made."""
    import io
    out = tmp_path / "out"
    out.mkdir()
    name = "gexis-gexis-20260925-120000.tgz"
    with tarfile.open(out / name, "w:gz") as archive:
        folder = tarfile.TarInfo("home/pi/.local/share/Plexamp/Settings")
        folder.type = tarfile.DIRTYPE
        folder.mode = 0o750
        folder.mtime = 1_700_000_000
        archive.addfile(folder)
        info = tarfile.TarInfo("home/pi/.local/share/Plexamp/Settings/token")
        info.mode = 0o6646
        info.mtime = 1_600_000_000
        info.size = 5
        archive.addfile(info, io.BytesIO(b"token"))

    root = tmp_path / "root"
    backups.restore(name, out, root)
    token = root / "home/pi/.local/share/Plexamp/Settings/token"
    assert token.read_bytes() == b"token"
    assert token.stat().st_mode & 0o7777 == 0o644
    assert token.stat().st_mtime == 1_600_000_000
    assert token.parent.stat().st_mode & 0o7777 == 0o750
    assert token.parent.stat().st_mtime == 1_700_000_000
    assert not [p for p in token.parent.iterdir() if p.name != "token"], "nothing left beside it"


def test_the_part_file_root_writes_is_never_a_link_someone_left(tmp_path, monkeypatch):
    """**Finding 125 #2.** The share belongs to `pi`, setgid but not sticky,
    so the kernel's protection for links does not apply there: a link at
    the name the next backup's partial file would have was written through
    by root - a gzip stream into `cmdline.txt`."""
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(backups.time, "strftime", lambda fmt, *a: "20261015-030001")
    victim = tmp_path / "cmdline.txt"
    victim.write_text("console=tty1")
    name = "gexis-den.before-update-20261015-030001.tgz"
    (out / f".{name}.part").symlink_to(victim)
    (out / name).symlink_to(victim)

    assert backups.create("Den", out, root, automatic=True) == name
    assert victim.read_text() == "console=tty1"
    assert not (out / name).is_symlink()
    with tarfile.open(out / name) as archive:
        assert "var/lib/gexis-core/settings.db" in archive.getnames()


def test_the_failure_mark_is_never_written_through_a_link(tmp_path):
    """**Finding 125 #2**: the same, for the word an update's failed backup
    leaves - its text went into whatever the link named."""
    victim = tmp_path / "shadow"
    victim.write_text("root:x:0:0")
    share = tmp_path / "share"
    share.mkdir()
    (share / backups.FAILED_MARK).symlink_to(victim)

    backups.update_backup_failed("disk full", share)
    assert victim.read_text() == "root:x:0:0"
    assert not (share / backups.FAILED_MARK).is_symlink()
    assert (share / backups.FAILED_MARK).read_text() == "disk full\n"


def test_the_uploaded_plugins_are_stopped_before_their_data_is_put_back(tmp_path):
    """**Finding 125 #4.** A running uploaded plugin's own SQLite WAL was
    checkpointed into its restored database at the reboot: the restore
    undone, or the file corrupted. Its units stop first, as the hub's do."""
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    name = backups.create("gexis", out, root)
    target = _device(tmp_path / "target")
    state = target / "var/lib/private/gexis-uploaded/radiofoo/state"
    state.write_text("newer")
    seen = []

    def run(argv, **kw):
        seen.append((argv, state.read_text()))
        out_ = ""
        if argv[1:2] == ["list-units"]:
            out_ = ("gexis-uploaded-service@radiofoo.service loaded active running x\n"
                    "gexis-uploaded-renderer@other.service loaded active running y\n")
        return subprocess.CompletedProcess(argv, 0, out_, "")

    backups.restore_file(out / name, target, run=run)
    stops = [(argv, text) for argv, text in seen if argv[:2] == ["systemctl", "stop"]]
    # By the pattern: one restarting after a failure stops as well.
    assert ["systemctl", "stop", "gexis-uploaded-*@*.service"] in [a for a, _ in stops]
    assert all(text == "newer" for _, text in stops), "stopped before anything was put back"
    assert state.read_text() == "learned"


def test_a_restore_that_fails_starts_the_plugins_it_stopped(tmp_path, monkeypatch):
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    name = backups.create("gexis", out, root)
    calls = []

    def run(argv, **kw):
        calls.append(argv)
        out_ = "gexis-uploaded-service@radiofoo.service loaded active running x\n" \
            if argv[1:2] == ["list-units"] else ""
        return subprocess.CompletedProcess(argv, 0, out_, "")

    def full(*a, **k):
        raise OSError("no space left on device")

    monkeypatch.setattr(backups, "_put_back", full)
    with pytest.raises(OSError):
        backups.restore_file(out / name, _device(tmp_path / "target"), run=run)
    assert ["systemctl", "start", "gexis-uploaded-service@radiofoo.service"] in calls


def test_an_archive_without_uploaded_data_leaves_the_plugins_running(tmp_path):
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    import shutil
    shutil.rmtree(root / "var/lib/private/gexis-uploaded")
    name = backups.create("gexis", out, root)
    calls = []
    backups.restore_file(out / name, _device(tmp_path / "target"),
                         run=lambda argv, **kw: calls.append(argv) or subprocess.CompletedProcess(argv, 0, "", ""))
    assert not any("gexis-uploaded" in " ".join(argv) for argv in calls)


def test_a_pipe_or_a_link_in_a_plugins_folder_does_not_make_the_backup_unrestorable(tmp_path):
    """**Finding 125 #5.** A renderer's pipe, or a venv's `lib64 -> lib`,
    went into every backup, and restore refused the whole archive for it."""
    root, out = _device(tmp_path / "root"), tmp_path / "out"
    plugin = root / "var/lib/private/gexis-uploaded/radiofoo"
    os.mkfifo(plugin / "pipe")
    (plugin / "lib").mkdir()
    (plugin / "lib/site.py").write_text("x = 1")
    (plugin / "lib64").symlink_to("lib")
    name = backups.create("gexis", out, root)
    with tarfile.open(out / name) as archive:
        held = {m.name: m for m in archive.getmembers()}
    assert "var/lib/private/gexis-uploaded/radiofoo/lib/site.py" in held
    assert all(m.isfile() or m.isdir() for m in held.values())

    target = tmp_path / "target"
    backups.restore_file(out / name, target)
    assert (target / "var/lib/private/gexis-uploaded/radiofoo/lib/site.py").read_text() == "x = 1"
    assert (target / "var/lib/private/gexis-uploaded/radiofoo/state").read_text() == "learned"


@pytest.mark.parametrize("kind", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE])
def test_an_older_backup_with_a_link_or_a_pipe_restores_everything_else(tmp_path, kind):
    """**Finding 125 #5**, for the backups 0.15.0 already wrote - among them
    the ones an update keeps to go back to: the entry is left out, the
    archive is not."""
    import io
    out = tmp_path / "out"
    out.mkdir()
    name = "gexis-gexis-20260925-120000.tgz"
    with tarfile.open(out / name, "w:gz") as archive:
        odd = tarfile.TarInfo("var/lib/private/gexis-uploaded/radiofoo/odd")
        odd.type = kind
        odd.linkname = "/etc/shadow" if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE) else ""
        archive.addfile(odd)
        info = tarfile.TarInfo("var/lib/private/gexis-uploaded/radiofoo/state")
        info.size = 7
        archive.addfile(info, io.BytesIO(b"learned"))

    root = tmp_path / "root"
    assert backups.restore_file(out / name, root) == 1
    assert (root / "var/lib/private/gexis-uploaded/radiofoo/state").read_text() == "learned"
    assert not os.path.lexists(root / "var/lib/private/gexis-uploaded/radiofoo/odd")
