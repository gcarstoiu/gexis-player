# SPDX-License-Identifier: GPL-3.0-or-later
"""moOde-compatible metadata file writer (Phase 3 criterion 4).

Writes `/var/local/www/currentsong.txt` in moOde's own key=value format,
so existing external display projects built against moOde's file - not
our own WebSocket - keep working unchanged (ARCHITECTURE.md §8). Sourced
directly from moode-player/moode's `www/daemon/worker.php`
(`updExtMetaFile()`), not assumed: plain `key=value\\n` lines, written to
a `.tmp` file then renamed into place and chmod 0666 - not JSON, despite
some forum/UI documentation describing a JSON shape elsewhere in moOde's
own stack.

**Scope, George's decision 2026-09-12: only the fields our model already
has** - `file`, `artist`, `album`, `title`, `coverurl`. moOde's own
"external renderer active" branch (the shape closest to our own
architecture - none of our three sources is moOde's own local MPD
playback) also writes `encoded`/`bitrate` (codec + bit depth, from a
renderer-specific metadata cache file we have no equivalent of) and
`outrate` (live ALSA hw_params - nothing in this codebase queries that
yet). Left out rather than faked; a reader missing a key it wants is the
same gap moOde's own two write-branches already have between each other.

Renderer name strings match moOde's own vocabulary exactly (`worker.php`
sets `$renderer` to one of these for each renderer it supports) - moOde
already has a category for each of our three sources by coincidence of
what it supports, so an existing reader's own renderer-name handling (if
it has any) sees a string it may already recognise.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from gexis_core.model import PlaybackState

logger = logging.getLogger("gexis_core.metadata_file")

DEFAULT_PATH = Path("/var/local/www/currentsong.txt")

#: A line break in a title would start a line of its own in the file.
_UNWRITABLE = re.compile(r"[\x00-\x1f\x7f\u2028\u2029]")


def allowed(path: Path) -> Path:
    """`path` if it is a file in moOde's own folder, else moOde's own path
    (the review of 1.16.1, 2026-11-10). The path comes from `core.toml`, and
    the core writing it runs as root: one put back from a crafted backup
    named `cmdline.txt`, which the core replaced at its first state."""
    if path.parent == DEFAULT_PATH.parent and path.name not in ("", ".", ".."):
        return path
    logger.warning("metadata_file: %s is outside %s; writing %s", path, DEFAULT_PATH.parent, DEFAULT_PATH)
    return DEFAULT_PATH

RENDERER_LABELS = {
    "lms": "Squeezelite Active",
    "spotify": "Spotify Active",
    "bluetooth": "Bluetooth Active",
}

_FIELDS = ("file", "artist", "album", "title", "coverurl")


class MetadataFileWriter:
    """Subscribed directly to `StateStore` (`store.subscribe(writer.write)`),
    the same shape as `wsserver.StateServer`'s own broadcast callback -
    called synchronously on every published state change.
    """

    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self._path = path
        self._last_written: str | None = None

    def write(self, state: PlaybackState) -> None:
        data = self._render(state)
        if data == self._last_written:
            # moOde's own updExtMetaFile() reads the existing file back and
            # compares before writing too, for the same reason: needless
            # writes are needless flash wear on an SD card.
            return
        self._write_atomically(data)
        self._last_written = data

    def _render(self, state: PlaybackState) -> str:
        if state.active is None:
            # No renderer holds the device (ADR-0027) - blank every field
            # rather than leave a stale renderer's last-known track
            # sitting in the file, matching this project's own "blank the
            # region" convention (ADR-0014) for the same situation
            # elsewhere (model.py's BLANK_METADATA).
            return "".join(f"{field}=\n" for field in _FIELDS)
        metadata = state.metadata
        values = {
            "file": RENDERER_LABELS.get(state.active, state.active),
            "artist": metadata.artist or "",
            "album": metadata.album or "",
            "title": metadata.title or "",
            "coverurl": metadata.artwork or "",
        }
        return "".join(f"{field}={_UNWRITABLE.sub(' ', values[field])}\n" for field in _FIELDS)

    def _write_atomically(self, data: str) -> None:
        tmp_path = self._path.with_name(self._path.name + ".tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            # Made new, never through a link left at the name; 0666 on the
            # descriptor, as moOde leaves it, whatever the umask.
            tmp_path.unlink(missing_ok=True)
            fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
            with os.fdopen(fd, "wb") as out:
                out.write(data.encode(errors="replace"))
                os.fchmod(out.fileno(), 0o666)
            tmp_path.rename(self._path)
        except OSError as exc:
            logger.warning("metadata_file: failed to write %s: %s", self._path, exc)
