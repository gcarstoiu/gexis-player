# SPDX-License-Identifier: GPL-3.0-or-later
"""What the Peppy screen needs to draw (Phase 5 criterion 7, ADR-0014).

The meter process is not ours and has no client for `/state`: it is system
Python with pygame, not the daemon's venv. So the daemon writes what it needs
to a small JSON file on tmpfs, and the driver reads it — the same shape as
`metadata_file.py`, for a different reader.

**Not `currentsong.txt`.** That file is moOde's format for moOde's readers
(Phase 3 criterion 4) and deliberately carries only moOde's fields; position
and duration are not among them, and the Peppy screen needs both for the
remaining time ADR-0014 lists.

Absent is absent: a field the renderer has nothing for is `null` here and
draws nothing (criterion 7). Phase 8's enrichment will fill some of those
gaps later; where it finds nothing, blank is correct (George, 2026-09-16).
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from gexis_core.model import PlaybackState

logger = logging.getLogger("gexis_core.peppy_metadata")

#: tmpfs: rewritten on every track change and position update, so it must
#: never touch the card.
DEFAULT_PATH = Path("/run/gexis/nowplaying.json")


class PeppyMetadataWriter:
    """Subscribed to `StateStore`, like `MetadataFileWriter`."""

    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self._path = path
        self._last: str | None = None

    def write(self, state: PlaybackState) -> None:
        metadata = state.metadata
        payload = json.dumps(
            {
                "source": state.active,
                "title": metadata.title,
                "artist": metadata.artist,
                "album": metadata.album,
                "artwork": metadata.artwork,
                "position": metadata.position,
                "duration": metadata.duration,
                "transport": metadata.transport,
                # The reader advances position itself between writes, so it
                # needs to know how old this one is.
                "written_at": time.time(),
            },
            separators=(",", ":"),
        )
        # `written_at` changes every time, so compare without it.
        fingerprint = payload[: payload.rindex(',"written_at"')]
        if fingerprint == self._last:
            return
        self._last = fingerprint

        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._path.with_suffix(".tmp")
            temporary.write_text(payload)
            os.replace(temporary, self._path)  # readers never see half a file
        except OSError as exc:
            logger.warning("peppy metadata: cannot write %s: %s", self._path, exc)
