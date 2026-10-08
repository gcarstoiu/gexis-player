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

#: **The databases the core holds open** (ADR-0131 §5). Put back by writing
#: beside them and renaming, so an open connection keeps the file it had and
#: never sees one overwritten underneath it.
REPLACED = ("var/lib/gexis-core/settings.db", "var/lib/gexis-core/enrichment.db")
SETTINGS_DB = "var/lib/gexis-core/settings.db"

#: `gexis-<name>-<stamp>.tgz`. The name is the device's, so an archive says
#: where it came from - ADR-0083 does not prevent restoring one device's
#: archive onto another, and this is what makes it visible.
NAME = re.compile(r"^gexis-.*-\d{8}-\d{6}\.tgz$")

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
            "meta": f"{when} · {self.size / 1_048_576:.1f} MB",
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


def create(device_name: str, directory: Path = DEFAULT_DIR, root: Path = Path("/")) -> str:
    """Write one, and return its name.

    **Written to a temporary name and renamed**, so a half-written archive is
    never listed as a whole one - the share is read by a person who cannot
    tell the difference.
    """
    directory.mkdir(parents=True, exist_ok=True)
    name = f"gexis-{_slug(device_name)}-{time.strftime('%Y%m%d-%H%M%S')}.tgz"
    final = directory / name
    partial = directory / f".{name}.part"
    try:
        with tarfile.open(partial, "w:gz") as archive:
            for member in MEMBERS:
                source = root / member
                if not source.exists():
                    logger.info("backup: %s is not here, skipping", member)
                    continue
                archive.add(source, arcname=member)
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


def _checked(archive: tarfile.TarFile, label: str) -> list[tarfile.TarInfo]:
    """The members to put back. Refuses a link and a member that would land
    outside the paths this module writes - the share is guest-writable, so an
    archive in it is not necessarily one we made."""
    allowed = tuple(MEMBERS)
    members = []
    for member in archive.getmembers():
        if member.issym() or member.islnk():
            raise ValueError(f"{label}: refuses a link, {member.name!r}")
        if member.name.startswith(allowed):
            members.append(member)
        elif member.name.startswith(FORMERLY_BACKED_UP):
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


def restore_file(path: Path, root: Path = Path("/")) -> int:
    """Put back the archive at `path`, whatever it is called - setup's
    upload is not in the share (ADR-0131). Returns how many paths."""
    with tarfile.open(path, "r:gz") as archive:
        members = _checked(archive, path.name)
        swapped = [m for m in members if m.name in REPLACED and m.isfile()]
        archive.extractall(root, members=[m for m in members if m not in swapped])
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
    logger.warning("backup: restored %s over %d path(s); a reboot follows", path.name, len(members))
    return len(members)


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
        brings.append("Beszel identity")
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
    return {
        "name": name,
        "made": made,
        "newer": isinstance(schema, int) and schema > known_migrations,
        "settings": {key: values[key] for key in APPLIED if key in values},
        "enabled": sorted(k[:-len(".enabled")] for k, v in values.items()
                          if k.endswith(".enabled") and v is True),
        "brings": brings,
    }


def forget(name: str, directory: Path = DEFAULT_DIR) -> None:
    if not SAFE.match(name) or not NAME.match(name):
        raise ValueError(f"not a backup name: {name!r}")
    (directory / name).unlink(missing_ok=True)
    logger.info("backup: deleted %s", name)
