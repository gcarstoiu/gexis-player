# SPDX-License-Identifier: GPL-3.0-or-later
"""**What the radio's routes call** (ADR-0180): the directory's lists, the
favourites, and playing a station - the panel, the phone and Home Assistant
all through this.

Playing a station is a takeover like any other (item 4): the device is
acquired for `radio` through the supervisor first, so whoever held it is
released as in any takeover, and only then does the renderer start mpv.

A station added by its address (decision 4, from the phone) is checked by
playing it before it is kept: it must sound within `CHECK_S`, or it is not
added and the radio stops.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from typing import Awaitable, Callable

from gexis_core import radio_favourites
from gexis_core.adapters.radio import PLAYING, NOT_ANSWERING, RadioAdapter
from gexis_core.radio_directory import PAGE, Directory, Station, Unreachable, playable
from gexis_core.radio_favourites import Favourites, address_id
from gexis_core.radio_logos import Logos

logger = logging.getLogger("gexis_core.radio_service")

#: How long a station added by its address has to start sounding.
CHECK_S = 20.0
#: A name given with an address, at most.
NAME_MOST = radio_favourites.NAME_MOST


class Off(Exception):
    """Internet radio is switched off (ADR-0077)."""


class Refused(Exception):
    """The supervisor did not give the device to the radio (an update is
    installing, say)."""


class RadioService:
    def __init__(self, *, directory: Directory, favourites: Favourites, adapter: RadioAdapter,
                 acquire: Callable[[str], Awaitable[None]], active: Callable[[], str | None],
                 enabled: Callable[[], bool], country: Callable[[], str | None],
                 logos: Logos | None = None) -> None:
        self.directory = directory
        #: Logos through the player (George, 2026-11-14): every station a
        #: screen is given names its logo by the player's own address.
        self.logos = logos
        self.favourites = favourites
        self.adapter = adapter
        self._acquire = acquire
        self._active = active
        self._enabled = enabled
        self._country = country

    # --- reading ---------------------------------------------------------

    def overview(self) -> dict:
        """The Radio screen's top: the favourites (which never need the
        directory), the country *Popular here* lists, and whether the
        directory answered last time it was asked."""
        return {"enabled": self._enabled(), "country": self._country(),
                "reachable": self.directory.reachable,
                "favourites": self.favourites_json()}

    def favourites_json(self) -> list[dict]:
        return [self.public(s) for s in self.favourites.all()]

    def public(self, station: Station) -> dict:
        """A station as a screen is given it: its logo at the player's
        address."""
        data = station.to_json()
        if self.logos is not None:
            data["logo"] = self.logos.path(station.logo)
        return data

    def station_from(self, data) -> Station | None:
        """A station a screen sends back, its logo given its own address
        again (an address of ours the player no longer remembers is none)."""
        if isinstance(data, dict) and self.logos is not None and isinstance(data.get("logo"), str):
            data = {**data, "logo": self.logos.source(data["logo"])}
        return Station.from_json(data)
    async def popular(self, offset: int = 0) -> dict:
        country = self._country()
        if not country:
            return self._page([], offset)
        return self._page(await self.directory.popular(country, offset), offset)

    async def stations(self, *, genre: str | None = None, country: str | None = None,
                       language: str | None = None, offset: int = 0) -> dict:
        if genre:
            found = await self.directory.by_tag(genre, offset)
        elif country:
            found = await self.directory.by_country(country, offset)
        elif language:
            found = await self.directory.by_language(language, offset)
        else:
            raise ValueError("a genre, a country or a language")
        return self._page(found, offset)

    async def search(self, text: str, offset: int = 0) -> dict:
        text = " ".join(text.split())
        if len(text) < 2:
            return self._page([], offset)
        return self._page(await self.directory.search(text[:100], offset), offset)

    async def genres(self) -> dict:
        return {"genres": await self.directory.tags(), "reachable": self.directory.reachable}

    async def countries(self) -> dict:
        return {"countries": await self.directory.countries(), "reachable": self.directory.reachable}

    async def languages(self) -> dict:
        return {"languages": await self.directory.languages(), "reachable": self.directory.reachable}

    def _page(self, stations: list[Station], offset: int) -> dict:
        favourite = set(self.favourites.ids())
        return {"stations": [{**self.public(s), "favourite": s.id in favourite} for s in stations],
                "offset": offset, "end": len(stations) < PAGE,
                "reachable": self.directory.reachable}

    # --- playing ---------------------------------------------------------

    async def play(self, station: Station) -> None:
        """Take the device for the radio, then play `station`."""
        if not self._enabled():
            raise Off()
        await self._acquire(RadioAdapter.renderer_id)
        if self._active() != RadioAdapter.renderer_id:
            raise Refused()
        await self.adapter.play_station(station)

    async def play_favourite(self, station_id: str) -> bool:
        station = self.favourites.get(station_id)
        if station is None:
            return False
        await self.play(station)
        return True

    async def resolve(self, station: Station) -> str:
        """**The address to play** (item 5, decision 5): a listed station's
        address now from the directory, which also counts the play; the kept
        one when the directory does not answer. A favourite keeps the
        address it was given."""
        if not station.listed:
            return station.url
        url = await self.directory.count_play(station.id)
        if url is None:
            return station.url
        if url != station.url and self.favourites.get(station.id) is not None:
            self.favourites.renew(station.id, url)
        return url

    # --- favourites ------------------------------------------------------

    def add(self, station: Station) -> bool:
        added = self.favourites.add(station)
        if added:
            asyncio.ensure_future(self.adapter.refresh_favourite())
        return added

    def remove(self, station_id: str) -> bool:
        removed = self.favourites.remove(station_id)
        if removed:
            asyncio.ensure_future(self.adapter.refresh_favourite())
        return removed

    def order(self, ids: list[str]) -> bool:
        return self.favourites.order(ids)

    async def add_by_address(self, url: str, name: str) -> Station | None:
        """**Checked by playing it before it is added** (decision 4): the
        station plays; if it sounds within `CHECK_S` it is kept as a
        favourite and goes on playing, otherwise it is not kept and the
        radio stops. None when it did not play."""
        url, name = url.strip(), " ".join(name.split())[:NAME_MOST]
        if not playable(url) or not name:
            raise ValueError("an http or https address and a name")
        station = Station(id=address_id(url), name=name, url=url, listed=False)
        kept = self.favourites.get(station.id)
        if kept is not None:
            station = replace(kept, name=name)
        await self.play(station)
        if not await self._sounds(station.id):
            logger.info("radio: %s did not play, not added", url)
            if self._active() == RadioAdapter.renderer_id and self.adapter.state.station \
                    and self.adapter.state.station.id == station.id:
                await self.adapter.pause()
            return None
        # What mpv told the radio once it sounded (codec, bitrate) is kept.
        playing = self.adapter.state.station
        if playing is not None and playing.id == station.id:
            station = playing
        self.add(station)
        return station

    def learned(self, station: Station) -> None:
        """A favourite added without its codec or bitrate keeps mpv's."""
        self.favourites.complete(station.id, station.codec, station.bitrate)

    async def _sounds(self, station_id: str) -> bool:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + CHECK_S
        while loop.time() < deadline:
            state = self.adapter.state
            if state.station is None or state.station.id != station_id:
                return False  # Something else was played meanwhile.
            if state.state == PLAYING:
                return True
            if state.state == NOT_ANSWERING:
                return False
            await asyncio.sleep(0.25)
        return False


__all__ = ["RadioService", "Off", "Refused", "Unreachable"]
