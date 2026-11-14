# SPDX-License-Identifier: GPL-3.0-or-later
"""**The radio's favourites: the player's own list** (ADR-0180 item 5,
decision 4).

Apart from Lyrion's, in the order the owner sets, kept in the player's
settings so a backup carries it. Each keeps what playing it needs without the
directory - its id, name, logo and address - so a favourite plays with the
directory down. A station the directory lacks is added by its address from
the phone, under an id of our own (`address_id`).

Next and Previous step through this list while a favourite plays, like a
radio's presets (decision 6), round from the last to the first.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import replace
from typing import Callable

from gexis_core.radio_directory import Station

logger = logging.getLogger("gexis_core.radio_favourites")

#: Kept with the settings (ADR-0022: *Radio favourites*, [N]) under an
#: `_`-key: a value the player keeps for itself, which no Settings row shows -
#: the list is managed on the Radio screen. The whole store is what a backup
#: carries, `_`-keys included (`backups.py`).
KEY = "_radio_favourites"
#: A list longer than anyone scrolls; it bounds what a phone can add.
MOST = 200
#: A favourite's name, as long as it is kept.
NAME_MOST = 120


def address_id(url: str) -> str:
    """The id of a station added by its address: the same address, the same
    id, so it is not added twice."""
    return "address-" + hashlib.sha256(url.strip().encode()).hexdigest()[:20]


class Full(Exception):
    """The list is at `MOST`."""


class Favourites:
    """Read and written through the settings store's `get` and `set`, so the
    list is where every other setting is - backed up, restored, reset."""

    def __init__(self, get: Callable[[str], object], set_: Callable[[str, object], None],
                 on_change: Callable[[], None] | None = None) -> None:
        self._get = get
        self._set = set_
        self._on_change = on_change

    def all(self) -> list[Station]:
        """The list as kept; anything in it that is not a station is passed
        over (a hand-edited or damaged list must not stop the radio)."""
        raw = self._get(KEY)
        if not isinstance(raw, list):
            return []
        stations, seen = [], set()
        for entry in raw:
            station = Station.from_json(entry)
            if station is None or station.id in seen:
                continue
            seen.add(station.id)
            stations.append(station)
        return stations

    def ids(self) -> list[str]:
        return [s.id for s in self.all()]

    def get(self, station_id: str) -> Station | None:
        return next((s for s in self.all() if s.id == station_id), None)

    def add(self, station: Station) -> bool:
        """Added at the end; False if it was already there."""
        stations = self.all()
        if any(s.id == station.id for s in stations):
            return False
        if len(stations) >= MOST:
            raise Full()
        stations.append(replace(station, name=station.name[:NAME_MOST]))
        self._save(stations)
        return True

    def remove(self, station_id: str) -> bool:
        stations = self.all()
        kept = [s for s in stations if s.id != station_id]
        if len(kept) == len(stations):
            return False
        self._save(kept)
        return True

    def order(self, ids: list[str]) -> bool:
        """**Put the list in this order.** Every favourite must be named, once:
        a phone and the panel reordering at once would otherwise lose one.
        False, and nothing changed, when they are not."""
        stations = self.all()
        if sorted(ids) != sorted(s.id for s in stations) or len(set(ids)) != len(ids):
            return False
        by_id = {s.id: s for s in stations}
        self._save([by_id[i] for i in ids])
        return True

    def renew(self, station_id: str, url: str) -> None:
        """The directory gave the station's address now: kept, so it plays
        from there when the directory is down next time."""
        stations = self.all()
        changed = False
        for i, s in enumerate(stations):
            if s.id == station_id and s.url != url:
                stations[i] = replace(s, url=url)
                changed = True
        if changed:
            self._save(stations)

    def step(self, station_id: str, by: int) -> Station | None:
        """The favourite `by` places on from this one, round the ends; None
        when this station is not a favourite."""
        stations = self.all()
        ids = [s.id for s in stations]
        if station_id not in ids:
            return None
        return stations[(ids.index(station_id) + by) % len(stations)]

    def _save(self, stations: list[Station]) -> None:
        self._set(KEY, [s.to_json() for s in stations])
        if self._on_change is not None:
            self._on_change()
