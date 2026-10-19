# SPDX-License-Identifier: GPL-3.0-or-later
"""**The Music share stops at 4 GB free** (ADR-0115 decision 27; George,
2026-10-18: *"4 GB fixed in code"*).

The share writes as Lyrion's own user, so music copied onto it cannot take
the filesystem's root-only reserve - and neither can Lyrion, Spotify,
Plexamp or the screen's browser, which a full card would stop. Below
`FLOOR` free the core makes the share read-only; above `REOPEN` it opens
again, the gap keeping it from flapping at the line.

How: the share's section ends with `include = /run/gexis/music-share.conf`
(`gexis-music.conf`). The file holds `read only = yes` while closed and is
empty otherwise; a missing file is an open share (checked with `testparm`
on sofapi, 2026-10-18). Samba reads it again on `reload-config`.
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

FLOOR = 4_000_000_000
REOPEN = 4_500_000_000
PATH = Path("/run/gexis/music-share.conf")
CLOSED = "   read only = yes\n"


def closed(free: int, was_closed: bool) -> bool:
    """Whether the share should be closed now, given the free bytes."""
    return free < (REOPEN if was_closed else FLOOR)


def is_closed(path: Path = PATH) -> bool:
    try:
        return path.read_text() == CLOSED
    except OSError:
        return False


def apply(close: bool, path: Path = PATH, run=subprocess.run) -> bool:
    """Write the share's include and have Samba read it again. True if it
    changed. A Samba that is not running has nothing to reload."""
    want = CLOSED if close else ""
    try:
        if path.exists() and path.read_text() == want:
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(want)
        os.replace(tmp, path)
    except OSError as exc:
        logger.warning("music floor: cannot write %s: %s", path, exc)
        return False
    try:
        run(["smbcontrol", "smbd", "reload-config"], capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        logger.info("music floor: Samba not reloaded (%s)", exc)
    return True
