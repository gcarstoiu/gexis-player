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

import json
import logging
import os
import re
import shutil
import sqlite3
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
STOPPED_FOR_RESTORE = (("var/lib/beszel-hub", "beszel-hub.service"),)

#: SQLite's companions of a database in WAL mode.
WAL_FILES = ("-wal", "-shm")

#: `gexis-<name>-<stamp>.tgz`. The name is the device's, so an archive says
#: where it came from - ADR-0083 does not prevent restoring one device's
#: archive onto another, and this is what makes it visible.
NAME = re.compile(r"^gexis-.*-\d{8}-\d{6}\.tgz$")

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


@dataclass(frozen=True)
class Archive:
    name: str
    made: float
    size: int

    def to_item(self) -> dict:
        """The shape a `list` row's items take (ADR-0044 §1)."""
        when = time.strftime("%-d %b %Y, %H:%M", time.localtime(self.made))
        return {
            "name": self.name,
            "meta": f"{when} · {self.size / 1_048_576:.1f} MB"
                    + (" · before an update" if AUTOMATIC.match(self.name) else ""),
            "state": "saved",
            "bars": None,
        }


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
        if not entry.is_file() or not NAME.match(entry.name):
            continue
        try:
            stat = entry.stat()
        except OSError:
            continue
        found.append(Archive(entry.name, stat.st_mtime, stat.st_size))
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
    """
    directory.mkdir(parents=True, exist_ok=True)
    mark = AUTOMATIC_MARK if automatic else ""
    name = f"gexis-{_slug(device_name)}{mark}-{time.strftime('%Y%m%d-%H%M%S')}.tgz"
    final = directory / name
    partial = directory / f".{name}.part"
    try:
        with tempfile.TemporaryDirectory() as work, tarfile.open(partial, "w:gz") as archive:
            copied: list[tuple[tarfile.TarInfo, Path]] = []

            def live_databases(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
                path = root / info.name
                if not info.isfile():
                    return info
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
                archive.add(source, arcname=member, filter=live_databases)
            # The copies, under the live files' names, owners and modes.
            for info, into in copied:
                info.size = into.stat().st_size
                with open(into, "rb") as data:
                    archive.addfile(info, data)
        partial.replace(final)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    # The share is `force user = pi`; an archive root wrote has to be
    # replaceable by the next writer.
    try:
        subprocess.run(["chown", "pi:pi", str(final)], check=False, capture_output=True)
    except OSError:
        pass
    logger.info("backup: wrote %s (%d bytes)", name, final.stat().st_size)
    return name


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
    archive `create` writes has one."""
    members = []
    for member in archive.getmembers():
        if member.issym() or member.islnk():
            raise ValueError(f"{label}: refuses a link, {member.name!r}")
        if not (member.isfile() or member.isdir()):
            raise ValueError(f"{label}: refuses a device or a pipe, {member.name!r}")
        parts = member.name.split("/")
        if member.name.startswith("/") or any(part in ("", ".", "..") for part in parts):
            raise ValueError(f"{label}: refuses to write {member.name!r}")
        if _under(member.name, MEMBERS):
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
    path = directory / name
    if not path.is_file():
        raise FileNotFoundError(str(path))
    restore_file(path, root)


def restore_file(path: Path, root: Path = Path("/"), leave: tuple[str, ...] = (), run=None) -> int:
    """Put back the archive at `path`, whatever it is called - setup's
    upload is not in the share (ADR-0131). `leave`: paths not put back, the
    identities of a backup restored as another player. Returns how many
    paths. `run`: how services are stopped (`STOPPED_FOR_RESTORE`) - on the
    device's own root, systemctl; elsewhere nothing unless a test passes
    one."""
    if run is None and root == Path("/"):
        run = subprocess.run
    with tarfile.open(path, "r:gz") as archive:
        members = [m for m in _checked(archive, path.name) if not _under(m.name, leave)]
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


def _stop_for_restore(members: list[tarfile.TarInfo], run) -> list[str]:
    """Stop each service whose files the archive brings; return those that
    were running."""
    stopped = []
    if run is None:
        return stopped
    for prefix, unit in STOPPED_FOR_RESTORE:
        if not any(_under(m.name, (prefix,)) for m in members):
            continue
        active = run(["systemctl", "is-active", "--quiet", unit], check=False, capture_output=True)
        run(["systemctl", "stop", unit], check=False, capture_output=True)
        if getattr(active, "returncode", 1) == 0:
            stopped.append(unit)
        logger.info("backup: %s stopped for the restore", unit)
    return stopped


def _put_back(archive: tarfile.TarFile, members: list[tarfile.TarInfo], root: Path) -> None:
    """The extraction itself: the core's databases beside and renamed, the
    rest by `extractall`."""
    swapped = [m for m in members if m.name in REPLACED and m.isfile()]
    # **`tar`, named** (the review of 2026-10-12): Python 3.13 on the
    # device has no default filter and 3.14's is `data`, which would put
    # Plexamp's claim back owned by root, where `pi` cannot write it.
    # `tar` keeps owners, drops setuid bits, and refuses a path that
    # would leave `root` - a second guard behind `_checked`.
    archive.extractall(root, members=[m for m in members if m not in swapped], filter="tar")
    for member in swapped:
        target = root / member.name
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(f".{target.name}.restoring")
        source = archive.extractfile(member)
        if source is None:
            continue
        with source, open(partial, "wb") as out:
            shutil.copyfileobj(source, out)
        os.chmod(partial, member.mode & 0o777)
        try:
            os.chown(partial, member.uid, member.gid)
        except OSError:  # not root: the tests, and nothing else
            pass
        partial.replace(target)
    # A WAL the archive does not bring is not left beside the database it
    # brings: the next open would apply it to the restored file.
    brought = {m.name for m in members}
    for member in members:
        if member.isfile() and member not in swapped:
            for suffix in WAL_FILES:
                if member.name + suffix not in brought:
                    (root / (member.name + suffix)).unlink(missing_ok=True)


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
    stamp = re.search(r"-(\d{8}-\d{6})\.tgz$", path.name)
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
    if not path.is_file():
        raise FileNotFoundError(name)
    return path


def forget(name: str, directory: Path = DEFAULT_DIR) -> None:
    if not SAFE.match(name) or not NAME.match(name):
        raise ValueError(f"not a backup name: {name!r}")
    (directory / name).unlink(missing_ok=True)
    logger.info("backup: deleted %s", name)
