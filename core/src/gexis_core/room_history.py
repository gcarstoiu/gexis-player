# SPDX-License-Identifier: GPL-3.0-or-later
"""**Every measurement and speaker check kept, to go back to** (ADR-0189 D2,
George 2026-11-25; C2-C4).

Per output, each measurement kept (whole, its check's curves included) with
the alignment it was measured with, and each speaker check kept on its own,
newest first. Each entry is a file of its own under the core's state, so
the settings stay small; nothing is dropped. An entry's id is its time and
kind - `20261125-114257-room` - and is all a route takes to name one.

Nothing here is fatal: a file that does not read is passed over, a write
that fails is logged and the measurement is kept all the same.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

from gexis_core import room_correction as rc

logger = logging.getLogger("gexis_core.room_history")

ROOT = Path("/var/lib/gexis/room-history")
ROOM = "room"
SPEAKERS = "speakers"
ID = re.compile(r"\d{8}-\d{6}-(room|speakers)(-\d+)?")


def _folder(card: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", card) or "_"


@dataclass(frozen=True)
class Entry:
    """One entry: its id, kind, when (ISO date, and the time when known),
    and what it kept."""
    id: str
    kind: str
    date: str
    time: str | None
    measurement: rc.Measurement | None
    alignment: rc.Alignment | None


class History:
    def __init__(self, root: Path = ROOT, now=None):
        self._root = Path(root)
        self._now = now or datetime.datetime.now

    def _dir(self, card: str) -> Path:
        return self._root / _folder(card)

    def _write(self, card: str, kind: str, body: dict, at: datetime.datetime | None = None,
               time_known: bool = True) -> str | None:
        at = at or self._now()
        base = at.strftime("%Y%m%d-%H%M%S") + f"-{kind}"
        folder = self._dir(card)
        try:
            folder.mkdir(parents=True, exist_ok=True)
            name, n = base, 1
            while (folder / f"{name}.json").exists():
                n += 1
                name = f"{base}-{n}"
            body = {"id": name, "kind": kind, "date": at.date().isoformat(),
                    "time": at.strftime("%H:%M") if time_known else None, **body}
            tmp = folder / f".{name}.tmp"
            tmp.write_text(json.dumps(body, separators=(",", ":")))
            os.replace(tmp, folder / f"{name}.json")
            return name
        except OSError:
            logger.exception("room history: could not keep a %s entry for %s", kind, card)
            return None

    def add_measurement(self, card: str, m: rc.Measurement, alignment: rc.Alignment | None = None,
                        at: datetime.datetime | None = None, time_known: bool = True) -> str | None:
        """A measurement kept (`Room.keep`), with the alignment it was
        measured with; its id."""
        a = alignment or rc.Alignment.of(m)
        return self._write(card, ROOM, {"measurement": m.as_dict(), "alignment": a.as_dict()}, at, time_known)

    def add_speakers(self, card: str, alignment: rc.Alignment) -> str | None:
        """A speaker check kept on its own (`Room.keep_speakers`); its id."""
        return self._write(card, SPEAKERS, {"alignment": alignment.as_dict()})

    def seed(self, card: str, m: rc.Measurement) -> str | None:
        """**A measurement kept before the history began** (C2): its first
        entry, dated by the measurement, the time unknown."""
        try:
            day = datetime.date.fromisoformat(m.date)
        except (TypeError, ValueError):
            day = self._now().date()
        return self.add_measurement(card, m, at=datetime.datetime.combine(day, datetime.time()), time_known=False)

    @staticmethod
    def _read(path: Path) -> Entry | None:
        try:
            v = json.loads(path.read_text())
            kind = v["kind"]
            if kind not in (ROOM, SPEAKERS) or not ID.fullmatch(v["id"]):
                return None
            m = rc.Measurement.from_dict(v["measurement"]) if kind == ROOM else None
            a = rc.Alignment.from_dict(v["alignment"]) if isinstance(v.get("alignment"), dict) else None
            time = v.get("time")
            return Entry(v["id"], kind, str(v["date"]), time if isinstance(time, str) else None, m, a)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return None

    def entries(self, card: str) -> list[Entry]:
        """Newest first; a file that does not read is passed over."""
        folder = self._dir(card)
        if not folder.is_dir():
            return []
        found = [e for p in folder.glob("*.json") if (e := self._read(p)) is not None]
        return sorted(found, key=lambda e: e.id, reverse=True)

    def get(self, card: str, entry_id: str) -> Entry | None:
        if not isinstance(entry_id, str) or not ID.fullmatch(entry_id):
            return None
        path = self._dir(card) / f"{entry_id}.json"
        return self._read(path) if path.is_file() else None
