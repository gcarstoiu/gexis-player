# SPDX-License-Identifier: GPL-3.0-or-later
"""**What a flash destroys, in one file** (ADR-0083).

Assembled by asking what the card holds that nobody can type back in: the
settings store, the enrichment cache the sweeps fill, the two files in
`/etc/gexis` that carry the LMS address and the idle URL, and BlueZ's
pairings. Written into a share of its own, because **a backup that stays on
the device does not survive the event it exists for.**

Everything here is deliberately dumb - `tar`, a directory listing, and a
restore that puts files back and asks for a reboot. A button somebody presses
once a month is the wrong place for a mechanism.
"""
from __future__ import annotations

import errno
import grp
import json
import logging
import os
import pwd
import re
import secrets
import shutil
import sqlite3
import stat
import subprocess
import tarfile
import tempfile
import time
import zlib
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("gexis_core.backups")

#: The share (ADR-0083). A sibling of `pictures`, not a parent of anything.
DEFAULT_DIR = Path("/var/lib/gexis-core/backups")

#: What goes in, relative to `/`. Missing members are skipped rather than
#: failing the archive: a device that has never paired anything has no
#: `/var/lib/bluetooth`, and that is not an error.
MEMBERS = (
    "var/lib/gexis-core/settings.db",
    "var/lib/gexis-core/enrichment.db",
    "etc/gexis/core.toml",
    "etc/gexis/device-name.env",
    "var/lib/bluetooth",
    # **The Spotify pairing** (added 2026-09-25). go-librespot stores the
    # credentials a phone handed it here (`persist_credentials: true`), and
    # the first backup missed it: the card was flashed, the restore put
    # everything else back, and the device came up advertising itself as a
    # brand-new never-paired player. George found it as "I am not seeing the
    # gexis device in Spotify".
    #
    # Deliberately not listed: `/var/lib/gexis-kiosk`, 62 MB of Chromium
    # profile that ADR-0043 keeps off the default path precisely so wiping it
    # is one directory, and samba's own tdb state, which is not anybody's.
    #
    # **The file, not the directory** (narrowed 2026-09-26, ADR-0095). The
    # directory also holds `config.yml`, which the image owns: a restore after
    # an image update put the old one back, and would have undone ADR-0095's
    # `audio_device: output_wait` without a word.
    "var/lib/go-librespot/state.json",
    # **The Beszel agent's fingerprint** (added 2026-09-25, ADR-0087). Same
    # lesson as the line above, applied before it could be learned twice: the
    # agent's `DATA_DIR` holds the identity the hub binds this system to, and a
    # reflash that loses it is a device the hub no longer recognises. Absent
    # until the plugin has run, and `create` skips a member that is not there.
    "var/lib/beszel-agent",
    # ADR-0114: the hub's history, systems and account.
    "var/lib/beszel-hub",
    # ADR-0115: the Lyrion server's own settings and the playlists it saved -
    # not its database or artwork cache (a rescan rebuilds them), and not the
    # music in the Music folder, which can be any size.
    "var/lib/squeezeboxserver/prefs",
    "var/lib/gexis-music/Playlists",
    # **Plexamp's claim** (added 2026-09-26, ADR-0090). The third time for the
    # same lesson, and this one was learned the hard way: the card was
    # flashed, the restore put the settings back with `plexamp.enabled` on,
    # and Plexamp came up unclaimed - not in the Plex player list at all. The
    # player's identity and the token that signs it in live in `Settings/`
    # here, one file per key (Finding 077); the claim token that made them is
    # single-use and minutes-lived, so it cannot stand in. Runs as `pi`,
    # hence under the home directory. ~200 KB.
    "home/pi/.local/share/Plexamp",
    # **Uploaded plugins: their data and the list of them, not their
    # packages** (ADR-0106; George, 13a criterion 4: "Agree with your
    # suggestion"). What an uploaded plugin runs is the user's to bring back;
    # what it learned, and that it was here, is ours to keep. systemd keeps a
    # temporary user's `StateDirectory` under `private/`, and fixes its owner
    # at the next start.
    "var/lib/private/gexis-uploaded",
    "var/lib/gexis/plugins-known.json",
)

#: **Paths older archives hold and this one no longer writes.** Skipped on
#: restore rather than refused: every backup made before 2026-09-26 holds all of
#: `/var/lib/go-librespot`, and refusing them would make them unrestorable for
#: the sake of one image-owned file.
FORMERLY_BACKED_UP = ("var/lib/go-librespot",)

#: **What makes a backup this player and no other** (ADR-0131 as amended;
#: George, 2026-10-08: "Setup could offer to leave these behind when the name
#: is changed" - "yes"). A backup restored onto a second player leaves these
#: behind, so two players do not share one identity: one system in two
#: places on the Beszel hub, one Plex player on two devices. The pairings
#: are bound to the first Pi's adapter and do nothing on another.
IDENTITIES = (
    ("var/lib/beszel-agent", "Beszel connection"),
    ("home/pi/.local/share/Plexamp", "Plexamp's claim"),
    ("var/lib/go-librespot/state.json", "Spotify sign-in"),
    ("var/lib/bluetooth", "Bluetooth pairings"),
)

#: **The settings that go with them** (George, 2026-10-08, on a second player
#: that came up still showing the first one's hub: *"everything goes,
#: including IP"*). A key, or a prefix ending in "." for every key of a
#: plugin. Beszel's connection is all settings - the hub's address, its key,
#: the token - and switched on with them gone it would have nothing to reach,
#: so the whole plugin goes back to its defaults. Plexamp keeps its switch:
#: on a second player it is claimed again.
IDENTITY_SETTINGS = ("beszel.", "plexamp.claim_token")

#: **The databases the core holds open** (ADR-0131 §5). Put back by writing
#: beside them and renaming, so an open connection keeps the file it had and
#: never sees one overwritten underneath it.
REPLACED = ("var/lib/gexis-core/settings.db", "var/lib/gexis-core/enrichment.db")
SETTINGS_DB = "var/lib/gexis-core/settings.db"

#: **Services whose files a restore puts back under them** (the review of
#: 2026-10-12): stopped first, so nothing has them open. The hub's PocketBase
#: store is SQLite in WAL mode: put back under the running hub, its own WAL
#: was checkpointed into the restored file at the reboot - "database disk
#: image is malformed", the history the restore was for and the hub's own
#: both lost. Not started again: the reboot that follows starts it.
#:
#: **Uploaded plugins, every one** (Finding 125 #4, 2026-10-14): the same
#: for a plugin with a SQLite store of its own - its last connection
#: checkpointed what it wrote after the backup into the restored file, and
#: the restore was undone for it, or the file corrupted. A unit with a `*`
#: is a pattern: each one of them that runs is stopped.
STOPPED_FOR_RESTORE = (
    ("var/lib/beszel-hub", "beszel-hub.service"),
    ("var/lib/private/gexis-uploaded", "gexis-uploaded-*@*.service"),
)

#: SQLite's companions of a database in WAL mode.
WAL_FILES = ("-wal", "-shm")

#: `gexis-<name>-<stamp>.tgz`. The name is the device's, so an archive says
#: where it came from - ADR-0083 does not prevent restoring one device's
#: archive onto another, and this is what makes it visible. **`.tgz.gz` too**
#: (found 2026-10-16): the download went out as `application/gzip`, and
#: Firefox and others saved it with `.gz` added - the same archive, which
#: copied back into the share was not listed.
NAME = re.compile(r"^gexis-.*-\d{8}-\d{6}\.tgz(?:\.gz)?$")

#: **The backup the updater asks for before each update** (George,
#: 2026-10-12, answer 3: pruned, the three most recent kept). Named
#: `gexis-<name>.before-update-<stamp>.tgz`: still a `NAME`, so a release
#: before this one - the one an update goes back to - lists and restores it,
#: and marked by a `.`, which `_slug` never writes, so no device's name can
#: make a backup taken by hand look like one of these.
AUTOMATIC_MARK = ".before-update"
AUTOMATIC = re.compile(r"^gexis-[a-z0-9-]+\.before-update-(\d{8}-\d{6})\.tgz$")

#: How many of them are kept (George, 2026-10-12). A backup taken by hand,
#: or one from before the mark existed, is never counted and never deleted.
KEEP_AUTOMATIC = 3

#: Nothing outside the backup directory is ever read or written by name, and a
#: name that tries is refused rather than sanitised.
SAFE = re.compile(r"^[A-Za-z0-9._-]+$")


#: **What is wrong with a file that cannot be one** (the bar, 2026-10-16: a
#: power cut during an update's backup left one of 0 bytes, listed and
#: offered for a restore that would fail). Checked by its first bytes, which
#: costs nothing; the whole archive is read only when it is restored.
EMPTY = "Empty: it cannot be restored"
NOT_GZIP = "Damaged: it cannot be restored"


@dataclass(frozen=True)
class Archive:
    name: str
    made: float
    size: int
    problem: str | None = None

    def to_item(self) -> dict:
        """The shape a `list` row's items take (ADR-0044 §1)."""
        when = time.strftime("%-d %b %Y, %H:%M", time.localtime(self.made))
        item = {
            "name": self.name,
            "meta": f"{when} · {_size(self.size)}"
                    + (" · before an update" if AUTOMATIC.match(self.name) else ""),
            "state": "saved",
            "bars": None,
        }
        if self.problem:
            # Listed so it can be forgotten, never offered for a restore.
            item.update(meta=f"{when} · {self.problem}", broken=True)
        return item


def _size(size: int) -> str:
    """In KB under a megabyte (2026-10-16): a fresh player's 12 KB backup
    read "0.0 MB", beside one that really was empty."""
    if size < 1_048_576:
        return f"{max(1, round(size / 1024))} KB"
    return f"{size / 1_048_576:.1f} MB"


def _problem(path: Path, size: int) -> str | None:
    if size == 0:
        return EMPTY
    try:
        with path.open("rb") as f:
            return None if f.read(2) == b"\x1f\x8b" else NOT_GZIP
    except OSError:
        return NOT_GZIP


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", (text or "gexis").strip()).strip("-")
    return (cleaned or "gexis").lower()


def available(directory: Path = DEFAULT_DIR) -> list[Archive]:
    """Every archive in the share, **newest first**.

    A file that is not one of ours is ignored rather than listed: the share is
    writable by anyone on the LAN, so it can hold anything at all.
    """
    try:
        entries = list(directory.iterdir())
    except OSError:
        return []
    found = []
    for entry in entries:
        if not NAME.match(entry.name):
            continue
        # `lstat`, not `is_file` (Finding 125 #2, 2026-10-14): a link `pi`
        # left under a backup's name is not a backup, and listing it is
        # what offered it for download and restore.
        try:
            info = entry.lstat()
        except OSError:
            continue
        if not stat.S_ISREG(info.st_mode):
            continue
        found.append(Archive(entry.name, info.st_mtime, info.st_size, _problem(entry, info.st_size)))
    return sorted(found, key=lambda a: a.made, reverse=True)


def _snapshot(source: Path, into: Path) -> bool:
    """SQLite's own copy of a database another program has open in WAL
    mode: one consistent file, the WAL's rows in it. False when it is not
    one SQLite can read; the files then go in as they are."""
    try:
        live = sqlite3.connect(source)
        try:
            copy = sqlite3.connect(into)
            try:
                live.backup(copy)
            finally:
                copy.close()
        finally:
            live.close()
        return True
    except sqlite3.Error as exc:
        logger.warning("backup: %s could not be copied as a database (%s); taking its files", source, exc)
        into.unlink(missing_ok=True)
        return False


#: **An update's backup that failed says so** (sofapi, 2026-10-13): the
#: updater watches the share for the new archive, and without this it waited
#: two minutes for one that was never coming. The core writes the reason
#: here; the updater reads it while it waits. Hidden, so never listed.
FAILED_MARK = ".before-update-failed"


def update_backup_failed(reason: str | None, directory: Path = DEFAULT_DIR) -> None:
    """Leave `reason` for the updater, or clear it (None) as a backup starts.

    **Never through a link** (Finding 125 #2, 2026-10-14): the share belongs
    to `pi`, setgid but not sticky, so the kernel's guard against following
    links does not apply in it, and root wrote the reason into whatever a
    link left at this name pointed to. What is there is removed - `unlink`
    removes a link, not what it names - and the mark made new; a link put
    back in between makes the write fail rather than follow it."""
    mark = directory / FAILED_MARK
    try:
        if reason is None:
            mark.unlink(missing_ok=True)
        else:
            directory.mkdir(parents=True, exist_ok=True)
            mark.unlink(missing_ok=True)
            fd = os.open(mark, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o644)
            with os.fdopen(fd, "w") as out:
                out.write(reason + "\n")
    except OSError as exc:
        logger.debug("backup: cannot write %s: %s", mark, exc)


def _give_to_pi(fd: int) -> None:
    """The share is `force user = pi`; an archive root wrote has to be
    replaceable by the next writer. **Through the open file** (Finding 125
    #2): `chown(1)` on the name followed a link `pi` had left there, and
    handed whatever it named to `pi`."""
    try:
        uid = pwd.getpwnam("pi").pw_uid
        gid = grp.getgrnam("pi").gr_gid
        os.fchown(fd, uid, gid)
    except (KeyError, OSError):  # no `pi`, or not root: the tests
        pass


def _add(archive: tarfile.TarFile, path: Path, arcname: str, filter) -> None:
    """`path` and, for a folder, everything in it - one entry at a time, so
    **a file that goes while the backup runs is left out, not the backup**
    (sofapi, 2026-10-13: an uploaded plugin's SQLite `-shm` file was listed,
    then deleted by its program before it was read; `tarfile.add`'s own walk
    failed the whole backup with "No such file or directory", and the update
    waiting for it stopped). A file gone has nothing in it to bring back."""
    try:
        archive.add(path, arcname=arcname, recursive=False, filter=filter)
    except FileNotFoundError:
        logger.info("backup: %s went while it was read, skipping", arcname)
        return
    if path.is_dir() and not path.is_symlink():
        try:
            names = sorted(os.listdir(path))
        except FileNotFoundError:
            return
        for name in names:
            _add(archive, path / name, f"{arcname}/{name}", filter)


#: How old a partial archive is before the next backup takes it for one
#: cut short. A backup being written touches its file all the time.
STALE_PART_S = 10 * 60

#: `create`'s partial names: `.<final name>.<random>.part`.
PART = re.compile(r"^\.gexis-.*\.tgz\..+\.part$")


def _sweep_parts(directory: Path, now: float | None = None) -> None:
    """**A backup cut short leaves nothing behind** (Finding 125 #2,
    2026-10-14): `mkstemp`'s random name is one no later backup reuses, so
    the partial file of one killed or powered off stayed in the share,
    hidden, for good. Removed by name only - `unlink` takes a link away
    without following it, and nothing here is opened - and only once it is
    old enough not to be another backup still being written."""
    now = time.time() if now is None else now
    try:
        names = os.listdir(directory)
    except OSError:
        return
    for name in names:
        if not PART.match(name):
            continue
        path = directory / name
        try:
            if now - os.lstat(path).st_mtime < STALE_PART_S:
                continue
            path.unlink()
        except OSError:
            continue
        logger.info("backup: removed %s, left by a backup cut short", name)


def create(device_name: str, directory: Path = DEFAULT_DIR, root: Path = Path("/"),
           automatic: bool = False) -> str:
    """Write one, and return its name.

    **Written to a temporary name and renamed**, so a half-written archive is
    never listed as a whole one - the share is read by a person who cannot
    tell the difference.

    **A database with a WAL beside it goes in as one file** (the review of
    2026-10-12): the Beszel hub writes its store while this runs, and
    `data.db` and `data.db-wal` read a moment apart restored to a state that
    never existed. SQLite's backup copies it whole; the WAL and its index
    stay out. A database with no WAL - the core's own, and the hub's when it
    is stopped - is one file already, and goes in as it is.

    `automatic`: the updater's, named with `AUTOMATIC_MARK` so that
    `prune_automatic` can find it later.

    **The temporary name is not one anybody can guess** (Finding 125 #2,
    2026-10-14). It was `.<name>.part`, in a share `pi` writes: a link left
    at that name had root write the archive into `cmdline.txt`, or
    `/etc/shadow`. `mkstemp` makes a new file under a random name and never
    opens one already there; the rename puts it in place of whatever holds
    the final name, a link included, without following it.

    **Only files and folders go in** (Finding 125 #5, 2026-10-14): a
    plugin's pipe, or the `lib64 -> lib` of a venv, went into every backup
    as what it was, and restore - which writes nothing but files and
    folders - refused the whole archive for it. Left out, and said.
    """
    directory.mkdir(parents=True, exist_ok=True)
    _sweep_parts(directory)
    mark = AUTOMATIC_MARK if automatic else ""
    name = f"gexis-{_slug(device_name)}{mark}-{time.strftime('%Y%m%d-%H%M%S')}.tgz"
    final = directory / name
    fd, partial_name = tempfile.mkstemp(prefix=f".{name}.", suffix=".part", dir=directory)
    partial = Path(partial_name)
    try:
        with os.fdopen(fd, "wb") as raw:
            with tempfile.TemporaryDirectory() as work, tarfile.open(fileobj=raw, mode="w:gz") as archive:
                _fill(archive, work, root)
            raw.flush()
            os.fchmod(raw.fileno(), 0o644)
            _give_to_pi(raw.fileno())
            size = os.fstat(raw.fileno()).st_size
            # **On the card before it has its name** (the bar, 2026-10-14: a
            # power cut during an update's backup left the name and none of
            # the data - 0 bytes, listed as a backup).
            os.fsync(raw.fileno())
        partial.replace(final)
        _sync_dir(directory)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    logger.info("backup: wrote %s (%d bytes)", name, size)
    return name


def _sync_dir(directory: Path) -> None:
    """The rename itself on the card. Best effort: a filesystem that cannot
    sync a directory still has the file's data, synced above."""
    try:
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _fill(archive: tarfile.TarFile, work: str, root: Path) -> None:
    """Everything in `MEMBERS` into `archive`; `work`, a folder for the
    databases' copies."""
    copied: list[tuple[tarfile.TarInfo, Path]] = []

    def live_databases(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
        path = root / info.name
        if info.isdir():
            return info
        if not info.isfile():
            logger.info("backup: %s is not a file or a folder, leaving it out", info.name)
            return None
        if any(info.name.endswith(s) for s in WAL_FILES) and \
                any(c.name == info.name[:-4] for c, _ in copied):
            return None
        if Path(f"{path}-wal").exists():
            into = Path(work) / str(len(copied))
            if _snapshot(path, into):
                copied.append((info, into))
                return None
        return info

    for member in MEMBERS:
        source = root / member
        if not source.exists():
            logger.info("backup: %s is not here, skipping", member)
            continue
        _add(archive, source, member, live_databases)
    # The copies, under the live files' names, owners and modes.
    for info, into in copied:
        info.size = into.stat().st_size
        with open(into, "rb") as data:
            archive.addfile(info, data)


def prune_automatic(keep_name: str, directory: Path = DEFAULT_DIR, keep: int = KEEP_AUTOMATIC) -> list[str]:
    """**The updater's backups beyond the newest `keep`, deleted** (George,
    2026-10-12), after `keep_name` - the one just made - was written.
    Returns the names deleted.

    Only names `AUTOMATIC` matches are ever looked at: a backup taken by
    hand, one copied in, one from before the mark, are not this function's.
    **Newest by the time in the name, and the one just made always kept**:
    a Pi has no clock of its own, and one that came up behind the time
    stamped a new backup older than the ones before it.
    """
    try:
        entries = [e.name for e in directory.iterdir() if e.is_file()]
    except OSError:
        return []
    theirs = sorted((n for n in entries if AUTOMATIC.match(n) and n != keep_name),
                    key=lambda n: AUTOMATIC.match(n).group(1), reverse=True)
    kept = 1 if AUTOMATIC.match(keep_name) and keep_name in entries else 0
    gone = []
    for name in theirs[max(keep - kept, 0):]:
        try:
            (directory / name).unlink()
        except OSError as exc:
            logger.warning("backup: could not delete %s: %s", name, exc)
            continue
        gone.append(name)
        logger.info("backup: deleted %s, an update's backup beyond the newest %d", name, keep)
    return gone


def _under(name: str, paths) -> bool:
    """Whether `name` is one of `paths` or inside one - **by whole path
    components**: `var/lib/bluetoothX` is not under `var/lib/bluetooth`."""
    return any(name == p or name.startswith(p + "/") for p in paths)


def _checked(archive: tarfile.TarFile, label: str) -> list[tarfile.TarInfo]:
    """The members to put back. Refuses a link and a member that would land
    outside the paths this module writes - the share is guest-writable, so an
    archive in it is not necessarily one we made.

    **Only plain files and folders, by names already in their plain form**
    (the review of 2026-10-12). The first version matched names by their
    first characters, so `var/lib/bluetooth/../../../etc/cron.d/x` passed,
    and on the device's Python 3.13 `extractall` followed the `..` - as
    root, with the reboot after a restore to run what it planted. A name
    with `..`, `.`, an empty part or a leading `/` is refused, not tidied: no
    archive `create` writes has one.

    **A link, a pipe or a device under our paths is left out, not the
    archive** (Finding 125 #5, 2026-10-14). Refused, one plugin's pipe or
    venv link made every backup 0.15.0 wrote unrestorable - the ones an
    update keeps to go back to among them. Left out, nothing is made for
    it, which is all refusing it ever protected; one under any other path
    is still refused with the archive."""
    members = []
    for member in archive.getmembers():
        parts = member.name.split("/")
        if member.name.startswith("/") or any(part in ("", ".", "..") for part in parts):
            raise ValueError(f"{label}: refuses to write {member.name!r}")
        ours = _under(member.name, MEMBERS)
        if not (member.isfile() or member.isdir()):
            if not (ours or _under(member.name, FORMERLY_BACKED_UP)):
                raise ValueError(f"{label}: refuses to write {member.name!r}")
            logger.info("backup: %s: leaving out %s, not a file or a folder", label, member.name)
            continue
        if ours:
            members.append(member)
        elif _under(member.name, FORMERLY_BACKED_UP):
            # An archive from before a member was narrowed: skipped, not
            # refused, so a backup taken the day before is still one.
            logger.info("backup: %s: leaving %s to the image", label, member.name)
        else:
            raise ValueError(f"{label}: refuses to write {member.name!r}")
    return members


def restore(name: str, directory: Path = DEFAULT_DIR, root: Path = Path("/")) -> None:
    """Put one back. **The caller reboots** (ADR-0083)."""
    if not SAFE.match(name) or not NAME.match(name):
        raise ValueError(f"not a backup name: {name!r}")
    # **Opened without following a link** (Finding 125 #2, 2026-10-14): a
    # link `pi` left under a backup's name had root read, and put back,
    # whatever archive it named. Read through the one open file.
    with open_archive(name, directory) as source:
        restore_file(directory / name, root, fileobj=source)


def restore_file(path: Path, root: Path = Path("/"), leave: tuple[str, ...] = (), run=None,
                 fileobj=None) -> int:
    """Put back the archive at `path`, whatever it is called - setup's
    upload is not in the share (ADR-0131). `leave`: paths not put back, the
    identities of a backup restored as another player. Returns how many
    paths. `run`: how services are stopped (`STOPPED_FOR_RESTORE`) - on the
    device's own root, systemctl; elsewhere nothing unless a test passes
    one. `fileobj`: the archive already open, read instead of `path`."""
    if run is None and root == Path("/"):
        run = subprocess.run
    with tarfile.open(path, "r:gz", fileobj=fileobj) as archive:
        members = [m for m in _checked(archive, path.name) if not _under(m.name, leave)]
        _refuse_links_on_disk(members, root, path.name)
        stopped = _stop_for_restore(members, run)
        try:
            _put_back(archive, members, root)
        except BaseException:
            # Nothing reboots after a restore that failed: what was running
            # runs again.
            for unit in stopped:
                run(["systemctl", "start", unit], check=False, capture_output=True)
            raise
    logger.warning("backup: restored %s over %d path(s); a reboot follows", path.name, len(members))
    return len(members)


def _refuse_links_on_disk(members: list[tarfile.TarInfo], root: Path, label: str) -> None:
    """**Nothing is written through a link already on the disk** (Finding
    125 #1, 2026-10-14). An uploaded plugin owns its data folder, and
    Plexamp, as `pi`, its own; a link left in either - `link -> /etc/cron.d`
    - had root write a member named `.../link/evil` into `/etc/cron.d`, and
    the reboot after a restore ran it. `_checked` looks only at names; this
    looks at the disk, before anything is stopped or written, so the
    archive is refused whole. `_put_back` refuses the same again as it
    writes, for a link made in between."""
    for member in members:
        here = root
        for part in member.name.split("/"):
            here = here / part
            try:
                mode = os.lstat(here).st_mode
            except FileNotFoundError:
                break
            if stat.S_ISLNK(mode):
                raise ValueError(f"{label}: refuses to write {member.name!r} through a link already on "
                                 f"the disk, {str(here.relative_to(root))!r}")


def _units_running(pattern: str, run) -> list[str]:
    """The units `pattern` names that are running now."""
    listed = run(["systemctl", "list-units", "--state=active", "--plain", "--no-legend", pattern],
                 check=False, capture_output=True, text=True)
    return [line.split()[0] for line in (getattr(listed, "stdout", "") or "").splitlines() if line.split()]


def _stop_for_restore(members: list[tarfile.TarInfo], run) -> list[str]:
    """Stop each service whose files the archive brings; return those that
    were running."""
    stopped = []
    if run is None:
        return stopped
    for prefix, unit in STOPPED_FOR_RESTORE:
        if not any(_under(m.name, (prefix,)) for m in members):
            continue
        if "*" in unit:
            # Stopped by the pattern, so one restarting after a failure
            # stops as well; started again by name, only those that ran.
            running = _units_running(unit, run)
            run(["systemctl", "stop", unit], check=False, capture_output=True)
            stopped.extend(running)
            logger.info("backup: %s stopped for the restore", ", ".join(running) or unit)
            continue
        active = run(["systemctl", "is-active", "--quiet", unit], check=False, capture_output=True)
        run(["systemctl", "stop", unit], check=False, capture_output=True)
        if getattr(active, "returncode", 1) == 0:
            stopped.append(unit)
        logger.info("backup: %s stopped for the restore", unit)
    return stopped


#: A folder opened to write in: never through a link (Finding 125 #1).
_FOLDER = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def _open_folder(root_fd: int, parts: list[str], label: str, make: bool = True) -> int:
    """The folder `parts` below `root_fd`, made where it is missing, each
    step opened relative to the one before and **never through a link**: a
    link at any step, even one made a moment ago, is refused rather than
    followed. Returns its descriptor, the caller's to close."""
    fd = os.dup(root_fd)
    try:
        for part in parts:
            if make:
                try:
                    os.mkdir(part, 0o777, dir_fd=fd)
                except FileExistsError:
                    pass
            try:
                inner = os.open(part, _FOLDER, dir_fd=fd)
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise ValueError(f"{label}: refuses to write through {'/'.join(parts)!r}: a link "
                                     f"already on the disk, or not a folder") from None
                raise
            os.close(fd)
            fd = inner
        return fd
    except BaseException:
        os.close(fd)
        raise


def _owner(member: tarfile.TarInfo) -> tuple[int, int]:
    """Who a member belongs to, as `tarfile` decides it: by name where this
    system knows the name, by number where it does not."""
    uid, gid = member.uid, member.gid
    try:
        if member.gname:
            gid = grp.getgrnam(member.gname).gr_gid
    except KeyError:
        pass
    try:
        if member.uname:
            uid = pwd.getpwnam(member.uname).pw_uid
    except KeyError:
        pass
    return (-1 if uid is None else uid), (-1 if gid is None else gid)


def _set_attributes(fd: int, member: tarfile.TarInfo) -> None:
    """Owner, then mode - a change of owner clears a setuid bit - then time,
    from `member`, through the open file. As `extractall` had it: one that
    cannot be set is logged, not fatal."""
    try:
        if os.geteuid() == 0:
            os.fchown(fd, *_owner(member))
        if member.mode is not None:
            os.fchmod(fd, member.mode)
        if member.mtime is not None:
            os.utime(fd, (member.mtime, member.mtime))
    except (OSError, OverflowError) as exc:
        logger.debug("backup: %s: %s", member.name, exc)


def _write_beside(archive: tarfile.TarFile, member: tarfile.TarInfo, kept: tarfile.TarInfo,
                  folder: int, leaf: str) -> None:
    """One file, written beside its place under a name nobody can guess and
    renamed over it. The rename replaces a link standing there instead of
    following it, and a program holding the old file open - the core its
    databases (ADR-0131 §5.4) - keeps the one it had."""
    partial = f".{leaf}.{secrets.token_hex(4)}.restoring"
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600,
                 dir_fd=folder)
    try:
        with os.fdopen(fd, "wb") as out:
            source = archive.extractfile(member)
            if source is not None:
                with source:
                    shutil.copyfileobj(source, out)
            out.flush()
            _set_attributes(out.fileno(), kept)
        os.rename(partial, leaf, src_dir_fd=folder, dst_dir_fd=folder)
    except BaseException:
        try:
            os.unlink(partial, dir_fd=folder)
        except FileNotFoundError:
            pass
        raise


def _put_back(archive: tarfile.TarFile, members: list[tarfile.TarInfo], root: Path) -> None:
    """The extraction itself, **the module's own** (Finding 125 #1,
    2026-10-14). It was `extractall` with the `tar` filter, called here a
    second guard behind `_checked`; that filter refuses a path only when
    it leaves `root`, and on the device `root` is `/`, so it refused
    nothing, and every link on the way was followed. Now each folder is
    opened from the one above it without following a link, and every file
    is written beside its place and renamed - the core's databases as
    before, and now the rest the same way.

    **The `tar` filter still decides what is kept** (the review of
    2026-10-12): owners as the archive says - `data` would put Plexamp's
    claim back owned by root, where `pi` cannot write it - and no setuid
    bit, no write bit for others."""
    label = Path(archive.name or "backup").name
    root.mkdir(parents=True, exist_ok=True)
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        brought = {m.name for m in members}
        folders = []
        for member in members:
            kept = tarfile.tar_filter(member, str(root))
            parts = member.name.split("/")
            if member.isdir():
                os.close(_open_folder(root_fd, parts, label))
                folders.append(kept)
                continue
            folder = _open_folder(root_fd, parts[:-1], label)
            try:
                _write_beside(archive, member, kept, folder, parts[-1])
                # A WAL the archive does not bring is not left beside the
                # database it brings: the next open would apply it to the
                # restored file. Not the core's own: it holds those open.
                if member.name not in REPLACED:
                    for suffix in WAL_FILES:
                        if member.name + suffix not in brought:
                            try:
                                os.unlink(parts[-1] + suffix, dir_fd=folder)
                            except FileNotFoundError:
                                pass
            finally:
                os.close(folder)
        # Folders' own modes last, deepest first, as `extractall` had it: one
        # made read-only before its files were in would refuse them.
        for kept in sorted(folders, key=lambda m: m.name, reverse=True):
            fd = _open_folder(root_fd, kept.name.split("/"), label, make=False)
            try:
                _set_attributes(fd, kept)
            finally:
                os.close(fd)
    finally:
        os.close(root_fd)


def write_settings(values: dict, root: Path = Path("/")) -> None:
    """**Setup's own answers over a restored backup** (ADR-0131 as amended):
    written into the settings file just put back, which is the one the next
    start reads. The core's open store still holds the file it had."""
    if not values:
        return
    conn = sqlite3.connect(root / SETTINGS_DB)
    try:
        conn.executemany("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                         [(key, json.dumps(value)) for key, value in values.items()])
        conn.commit()
    finally:
        conn.close()


def forget_settings(keys: tuple = IDENTITY_SETTINGS, root: Path = Path("/")) -> None:
    """**A second player's restored settings without the first one's
    identities** (`IDENTITY_SETTINGS`): removed from the settings file just
    put back, so the next start reads each one's default."""
    conn = sqlite3.connect(root / SETTINGS_DB)
    try:
        for key in keys:
            if key.endswith("."):
                conn.execute("DELETE FROM settings WHERE substr(key, 1, ?) = ?", (len(key), key))
            else:
                conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        conn.commit()
    finally:
        conn.close()


class Refused(ValueError):
    """**A file setup cannot restore, in words for the phone** (ADR-0131 §4)."""


NOT_A_BACKUP = "That file is not a gexis backup. A backup is a .tgz file from the player's Backups share."
FOREIGN = "That file holds more than a gexis backup does, so it is not restored."
NO_SETTINGS = "That backup has no settings in it."
UNREADABLE = "The settings in that backup cannot be read by this version of gexis."

#: What setup applies from a backup as its own answers, in this order
#: (ADR-0131 §5.3): Headless before the screen, as setup's own steps go.
APPLIED = ("device_name", "timezone", "clock_format", "output_device", "lms_enabled", "lms_server",
           "spotify_enabled", "bt_enabled", "headless", "screen", "visualiser_skins")

_PAIRED = re.compile(r"^var/lib/bluetooth/[0-9A-F:]{17}/[0-9A-F:]{17}$")


def _settings_in(archive: tarfile.TarFile, member: tarfile.TarInfo) -> dict:
    source = archive.extractfile(member)
    if source is None:
        raise Refused(NO_SETTINGS)
    with tempfile.TemporaryDirectory() as work:
        copy = Path(work) / "settings.db"
        with source, open(copy, "wb") as out:
            shutil.copyfileobj(source, out)
        try:
            conn = sqlite3.connect(f"file:{copy}?mode=ro", uri=True)
            try:
                rows = conn.execute("SELECT key, value FROM settings").fetchall()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("backup: settings unreadable: %s", exc)
            raise Refused(UNREADABLE) from None
    values = {}
    for key, raw in rows:
        try:
            values[key] = json.loads(raw)
        except (TypeError, ValueError):
            continue
    return values


def inspect(path: Path, known_migrations: int, schema_key: str = "_settings_schema") -> dict:
    """**What a backup would bring, without putting anything back** (ADR-0131
    §3-4): its settings as setup applies them, which plugins it has on, what
    else it carries, when and where it was made, and whether a newer version
    of gexis made it. Raises `Refused` with the sentence for the phone."""
    try:
        archive = tarfile.open(path, "r:gz")
    except (tarfile.TarError, OSError, EOFError, zlib.error):
        raise Refused(NOT_A_BACKUP) from None
    with archive:
        try:
            members = _checked(archive, path.name)
        except ValueError:
            raise Refused(FOREIGN) from None
        except (tarfile.TarError, OSError, EOFError, zlib.error):
            raise Refused(NOT_A_BACKUP) from None
        by_name = {m.name: m for m in members}
        db = by_name.get(SETTINGS_DB)
        if db is None or not db.isfile():
            raise Refused(NO_SETTINGS)
        values = _settings_in(archive, db)
        name = values.get("device_name")
        env = by_name.get("etc/gexis/device-name.env")
        if not name and env is not None and env.isfile():
            source = archive.extractfile(env)
            if source is not None:
                with source:
                    for line in source.read().decode(errors="replace").splitlines():
                        if line.startswith("NAME="):
                            name = line[5:].strip().strip('"') or None
    names = [m.name for m in members]
    schema = values.get(schema_key)
    # When it was made: the time in its name, as `create` writes it, or the
    # newest file in it - a renamed file keeps its contents' times.
    stamp = re.search(r"-(\d{8}-\d{6})\.tgz(?:\.gz)?$", path.name)
    try:
        made = time.mktime(time.strptime(stamp.group(1), "%Y%m%d-%H%M%S")) if stamp else None
    except ValueError:
        made = None
    if made is None:
        made = max((m.mtime for m in members), default=None)
    brings = []
    paired = sum(1 for n in names if _PAIRED.match(n))
    if paired:
        brings.append(f"{paired} paired Bluetooth {'device' if paired == 1 else 'devices'}")
    if "var/lib/go-librespot/state.json" in names:
        brings.append("Spotify sign-in")
    if any(n.startswith("home/pi/.local/share/Plexamp/Settings/") for n in names):
        brings.append("Plexamp's claim")
    if any(n.startswith("var/lib/beszel-agent/") for n in names):
        brings.append("Beszel connection")
    if any(n.startswith("var/lib/beszel-hub/") for n in names):
        brings.append("Beszel hub history")
    if any(n.startswith("var/lib/squeezeboxserver/prefs/") for n in names):
        brings.append("Lyrion server settings")
    playlists = sum(1 for n in names if n.startswith("var/lib/gexis-music/Playlists/") and n.endswith(".m3u"))
    if playlists:
        brings.append(f"{playlists} {'playlist' if playlists == 1 else 'playlists'}")
    if "var/lib/gexis-core/enrichment.db" in names:
        brings.append("Artist and album information")
    if any(n.startswith("var/lib/private/gexis-uploaded/") for n in names):
        brings.append("Uploaded plugins' data")
    held = [label for prefix, label in IDENTITIES
            if any(n == prefix or n.startswith(prefix + "/") for n in names)]
    return {
        "name": name,
        "made": made,
        #: What a second player would leave behind, of what this one holds.
        "identities": held,
        "newer": isinstance(schema, int) and schema > known_migrations,
        "settings": {key: values[key] for key in APPLIED if key in values},
        #: **On only where the backup stores it on.** A plugin switch nobody
        #: touched is not stored, and reads its unit's own state - and every
        #: plugin ships disabled. Taking "not stored" as on (2026-10-10, for an
        #: afternoon) put the Lyrion Server on sofapi's settling screen with
        #: nothing to switch it on, waiting for a download that never started.
        "enabled": sorted(k[:-len(".enabled")] for k, v in values.items()
                          if k.endswith(".enabled") and v is True),
        "brings": brings,
    }


def path_of(name: str, directory: Path = DEFAULT_DIR) -> Path:
    """**One backup, to download** (ADR-0083 as amended 2026-10-08): its file,
    by a name that is ours and nothing else. Raises ValueError for a name
    that is not, FileNotFoundError for one that is not there."""
    if not SAFE.match(name) or not NAME.match(name):
        raise ValueError(f"not a backup name: {name!r}")
    path = directory / name
    # `lstat` (Finding 125 #2, 2026-10-14): a link under a backup's name is
    # not one. The route itself sends through `open_archive`.
    try:
        if not stat.S_ISREG(os.lstat(path).st_mode):
            raise FileNotFoundError(name)
    except OSError:
        raise FileNotFoundError(name) from None
    return path


def open_archive(name: str, directory: Path | None = None):
    """**One backup, open for reading - never through a link** (Finding
    125 #2, 2026-10-14). The share is `pi`'s, setgid but not sticky, so the
    kernel's guard for links does not apply there: a link left under a
    backup's name had root send, or restore, whatever it named -
    `/etc/shadow` to anyone on the network. `O_NOFOLLOW` refuses the link
    when the file is opened, so nothing can be swapped in after a check;
    anything that is not a plain file (a pipe: `O_NONBLOCK`, so it cannot
    hang the open) is not there. Raises ValueError for a name that is not
    ours, FileNotFoundError for one that is not a backup on the disk."""
    if not SAFE.match(name) or not NAME.match(name):
        raise ValueError(f"not a backup name: {name!r}")
    path = (DEFAULT_DIR if directory is None else directory) / name
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError as exc:
        if exc.errno in (errno.ENOENT, errno.ELOOP, errno.ENOTDIR):
            raise FileNotFoundError(name) from None
        raise
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise FileNotFoundError(name)
        return os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise


def forget(name: str, directory: Path = DEFAULT_DIR) -> None:
    if not SAFE.match(name) or not NAME.match(name):
        raise ValueError(f"not a backup name: {name!r}")
    (directory / name).unlink(missing_ok=True)
    logger.info("backup: deleted %s", name)


# -- ADR-0083 as amended 2026-10-17: a backup uploaded in Settings -----------

NEWER = "That backup is from a newer version of gexis. Update this player first, then add it."


def upload_part(directory: Path = DEFAULT_DIR) -> tuple[int, Path]:
    """An open file to stream an upload into, hidden in the share under a
    name `_sweep_parts` removes if the upload never finishes."""
    directory.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".gexis-upload.tgz.", suffix=".part", dir=directory)
    return fd, Path(name)


def add_upload(part: Path, filename: str | None, known_migrations: int,
               directory: Path = DEFAULT_DIR) -> dict:
    """**Check an uploaded file and add it to the share** (ADR-0083 as
    amended 2026-10-17; George: *"It should stay in the restore list"*):
    never restored by itself, never in place of a file already there.
    Returns `{"name", "already"}`; raises `Refused` with the sentence for the
    page. `part` is gone afterwards either way."""
    try:
        seen = inspect(part, known_migrations)
        if seen["newer"]:
            raise Refused(NEWER)
        # **The same backup under another name is already there** (a file
        # renamed on the computer): said, not added twice.
        size = part.stat().st_size
        for listed in available(directory):
            if listed.size == size and _same(part, directory / listed.name):
                return {"name": listed.name, "already": True}
        given = Path(filename or "").name
        if given.endswith(".tgz.gz"):
            given = given[:-3]
        if not (NAME.match(given) and SAFE.match(given)):
            stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(seen["made"] or time.time()))
            given = f"gexis-{_slug(seen.get('name') or 'gexis')}-{stamp}.tgz"
        final = directory / given
        if final.exists() or final.is_symlink():
            if _same(part, final):
                return {"name": given, "already": True}
            given = f"gexis-{_slug(seen.get('name') or 'gexis')}-{time.strftime('%Y%m%d-%H%M%S')}.tgz"
            final = directory / given
        with part.open("rb+") as f:
            os.fchmod(f.fileno(), 0o644)
            _give_to_pi(f.fileno())
            os.fsync(f.fileno())
        # A link, not a rename: it fails rather than replace whatever
        # arrived under that name in the meantime.
        os.link(part, final)
        _sync_dir(directory)
        logger.info("backup: %s added from an upload (%s)", given, seen.get("name"))
        return {"name": given, "already": False}
    except FileExistsError as exc:
        raise Refused("A backup with that name arrived at the same moment. Try again.") from exc
    finally:
        part.unlink(missing_ok=True)


def _same(a: Path, b: Path) -> bool:
    try:
        if not stat.S_ISREG(b.lstat().st_mode) or a.stat().st_size != b.stat().st_size:
            return False
        with a.open("rb") as x, b.open("rb") as y:
            while True:
                one, two = x.read(1 << 20), y.read(1 << 20)
                if one != two:
                    return False
                if not one:
                    return True
    except OSError:
        return False
