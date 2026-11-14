# SPDX-License-Identifier: GPL-3.0-or-later
"""**The radio directory: radio-browser.info, read by the core** (ADR-0180
item 1).

Not Lyrion's radio (`radio.py`): this is the player's own, with or without a
Lyrion server.

- **The server is found, never written in.** `all.api.radio-browser.info`
  names every server the directory runs; each address is named back to its
  host (`de1.api.radio-browser.info`) and they are tried in turn, in a random
  order as the directory asks. On 2026-11-12 there was one (`de1`), and it
  has been down before - so a server that fails is passed over, and when
  every one fails the directory is *unreachable*, which is an answer of its
  own (`Unreachable`), never an empty list.
- **Every list is kept on the device for a day** (ADR-0022, [H]): browsing
  again costs nothing, and a directory that is down still shows what was
  seen that day. Older than a day, a list is asked for again; if the
  directory cannot answer, it is unreachable - the list is not shown stale.
- **Only stations whose last check passed** (`hidebroken`).
- **A station's logo** is the directory's `favicon`, or none: a third are
  missing and some are `.ico`, which count as none (ADR-0180 item 4).
- **A play is counted** (decision 5): `url/{uuid}` counts it and answers the
  station's address now, which is also how a favourite's address is asked
  for again at play time (item 5).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable
from urllib.parse import urlsplit

import aiohttp

logger = logging.getLogger("gexis_core.radio_directory")

#: The name that lists every server (the directory's own advice).
DISCOVERY_HOST = "all.api.radio-browser.info"
#: Only a name under this is taken as one of the directory's servers.
SERVER_SUFFIX = ".api.radio-browser.info"
#: Where the day's lists are kept. A cache: losing it costs one more ask.
CACHE_DIR = Path("/var/cache/gexis-core/radio")
#: ADR-0022 [H]: each answer kept for a day.
FRESH_S = 24 * 3600
#: The servers are looked up again after this long, or after all failed.
SERVERS_FRESH_S = 3600
#: Per server. A list is on a screen's path, so a server that does not
#: answer in this long is passed over for the next.
TIMEOUT_S = 6.0
#: The play count and the address at play time: the tap waits for it, so it
#: is short, and the kept address is played when it runs out.
PLAY_TIMEOUT_S = 3.0
#: Stations per page of a list.
PAGE = 50
#: Genres and languages: the directory has thousands of tags, most with a
#: station or two. The best-filled are offered; search finds the rest.
TOP_TAGS = 200
TOP_LANGUAGES = 120
#: Files kept in the cache before the oldest are removed.
CACHE_KEEP = 400


class Unreachable(Exception):
    """No server of the directory answered."""


@dataclass(frozen=True)
class Station:
    """One station, as the player keeps and shows it."""

    #: The directory's `stationuuid`; for a station added by its address,
    #: an id of our own (`radio_favourites.address_id`).
    id: str
    name: str
    #: The address to play: the directory's resolved one where it has it.
    url: str
    logo: str | None = None
    country: str | None = None
    countrycode: str | None = None
    codec: str | None = None
    #: kb/s; None when the directory does not know (it says 0).
    bitrate: int | None = None
    hls: bool = False
    #: Whether the id is the directory's, so the address can be asked for
    #: again and a play counted.
    listed: bool = True

    def to_json(self) -> dict:
        return {"id": self.id, "name": self.name, "url": self.url, "logo": self.logo,
                "country": self.country, "countrycode": self.countrycode, "codec": self.codec,
                "bitrate": self.bitrate, "hls": self.hls, "listed": self.listed}

    @classmethod
    def from_json(cls, data: dict) -> "Station | None":
        """A station as `to_json` wrote it - a kept favourite - or None if
        it is not one (no id, name or playable address)."""
        if not isinstance(data, dict):
            return None
        sid, name, url = data.get("id"), data.get("name"), data.get("url")
        if not (isinstance(sid, str) and sid and isinstance(name, str) and name.strip()
                and playable(url)):
            return None
        bitrate = data.get("bitrate")
        return cls(id=sid, name=name.strip(), url=url, logo=logo_of(data.get("logo")),
                   country=_text(data.get("country")), countrycode=_text(data.get("countrycode")),
                   codec=_text(data.get("codec")),
                   bitrate=bitrate if isinstance(bitrate, int) and not isinstance(bitrate, bool)
                   and bitrate > 0 else None,
                   hls=bool(data.get("hls")), listed=data.get("listed", True) is not False)

    @classmethod
    def from_directory(cls, data: dict) -> "Station | None":
        """A station as the directory lists it, or None if it cannot be
        played or named."""
        if not isinstance(data, dict):
            return None
        sid = data.get("stationuuid")
        name = data.get("name")
        url = data.get("url_resolved") or data.get("url")
        if not (isinstance(sid, str) and sid and isinstance(name, str) and name.strip()
                and playable(url)):
            return None
        bitrate = data.get("bitrate")
        return cls(id=sid, name=name.strip(), url=url, logo=logo_of(data.get("favicon")),
                   country=_text(data.get("country")),
                   countrycode=_text(data.get("countrycode")),
                   codec=_codec(data.get("codec")),
                   bitrate=bitrate if isinstance(bitrate, int) and not isinstance(bitrate, bool)
                   and bitrate > 0 else None,
                   hls=data.get("hls") in (1, True))


def _text(value) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def _codec(value) -> str | None:
    """The directory's codec name, as a person reads it; `UNKNOWN` is none."""
    text = _text(value)
    if text is None or text.upper() == "UNKNOWN":
        return None
    return text


def playable(url) -> bool:
    """An address mpv is given: http or https, with a host."""
    if not isinstance(url, str) or len(url) > 2048:
        return False
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and bool(parts.netloc)


def logo_of(favicon) -> str | None:
    """**The station's logo, or None** (ADR-0180 item 4): missing, not a web
    address, or an `.ico` - which count as none."""
    if not playable(favicon):
        return None
    path = urlsplit(favicon.strip()).path.lower()
    if path.endswith(".ico"):
        return None
    return favicon.strip()


async def discover() -> list[str]:
    """**The directory's servers, as base addresses** (`https://de1...`), in
    a random order: every address `all.api.radio-browser.info` gives, named
    back to its server. A name that is not one of the directory's is passed
    over. When no address names back, the discovery name itself is the one
    server: it reaches one of them, and its certificate covers it."""
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(DISCOVERY_HOST, 443, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        logger.info("radio directory: %s did not resolve (%s)", DISCOVERY_HOST, exc)
        return []
    names: set[str] = set()
    for address in {info[4][0] for info in infos}:
        try:
            name = (await loop.run_in_executor(None, socket.gethostbyaddr, address))[0]
        except OSError:
            continue
        name = name.rstrip(".").lower()
        if name.endswith(SERVER_SUFFIX):
            names.add(name)
    servers = [f"https://{name}" for name in names] or [f"https://{DISCOVERY_HOST}"]
    random.shuffle(servers)
    logger.info("radio directory: servers %s", ", ".join(servers))
    return servers


class Directory:
    """The directory as the core reads it: lists by country, genre and
    language, search by name, kept a day; the play count."""

    def __init__(self, *, user_agent: str, cache_dir: Path = CACHE_DIR,
                 servers: Callable[[], Awaitable[list[str]]] = discover,
                 session_factory: Callable[[], aiohttp.ClientSession] | None = None,
                 clock: Callable[[], float] = time.time) -> None:
        self._user_agent = user_agent
        self._cache_dir = cache_dir
        self._discover = servers
        self._session_factory = session_factory
        self._session: aiohttp.ClientSession | None = None
        self._clock = clock
        self._servers: list[str] = []
        self._servers_at = 0.0
        #: Whether the last ask reached a server: None until one is made.
        #: The Radio screen says the directory is unreachable from this,
        #: while it still shows the day's lists.
        self.reachable: bool | None = None

    # --- the lists -------------------------------------------------------

    async def popular(self, countrycode: str, offset: int = 0) -> list[Station]:
        """*Popular here*: the country's most played stations."""
        return await self._stations({"countrycode": countrycode.upper(), "order": "clickcount",
                                     "reverse": "true"}, offset)

    async def by_tag(self, tag: str, offset: int = 0) -> list[Station]:
        return await self._stations({"tag": tag, "tagExact": "true", "order": "clickcount",
                                     "reverse": "true"}, offset)

    async def by_country(self, countrycode: str, offset: int = 0) -> list[Station]:
        return await self.popular(countrycode, offset)

    async def by_language(self, language: str, offset: int = 0) -> list[Station]:
        return await self._stations({"language": language, "languageExact": "true",
                                     "order": "clickcount", "reverse": "true"}, offset)

    async def search(self, name: str, offset: int = 0) -> list[Station]:
        """Stations whose name holds `name`, the most played first."""
        return await self._stations({"name": name.strip(), "order": "clickcount",
                                     "reverse": "true"}, offset)

    async def tags(self) -> list[dict]:
        """The genres: `{"name", "stations"}`, the best-filled first."""
        data = await self._list("/json/tags", {"order": "stationcount", "reverse": "true",
                                               "hidebroken": "true", "limit": str(TOP_TAGS)})
        return [{"name": t["name"].strip(), "stations": t["stationcount"]}
                for t in data if _named_count(t)]

    async def countries(self) -> list[dict]:
        """`{"code", "name", "stations"}`, the best-filled first."""
        data = await self._list("/json/countries", {"order": "stationcount", "reverse": "true",
                                                    "hidebroken": "true"})
        return [{"code": c["iso_3166_1"].upper(), "name": c["name"].strip(),
                 "stations": c["stationcount"]}
                for c in data if _named_count(c) and isinstance(c.get("iso_3166_1"), str)
                and len(c["iso_3166_1"]) == 2]

    async def languages(self) -> list[dict]:
        """`{"name", "code", "stations"}`, the best-filled first."""
        data = await self._list("/json/languages", {"order": "stationcount", "reverse": "true",
                                                    "hidebroken": "true",
                                                    "limit": str(TOP_LANGUAGES)})
        return [{"name": lang["name"].strip(), "code": _text(lang.get("iso_639")),
                 "stations": lang["stationcount"]}
                for lang in data if _named_count(lang)]

    # --- playing ---------------------------------------------------------

    async def count_play(self, station_id: str) -> str | None:
        """**Count a play, and the station's address now** (decisions 4 and
        5): None when the directory cannot say, and the kept address plays.
        Never cached - it is the play."""
        try:
            # Bounded as a whole: looking the servers up and trying each in
            # turn must not keep a tap waiting longer than one ask.
            data = await asyncio.wait_for(
                self._ask(f"/json/url/{station_id}", None, timeout=PLAY_TIMEOUT_S,
                          rediscover=False), PLAY_TIMEOUT_S + 1.0)
        except (Unreachable, asyncio.TimeoutError):
            return None
        if isinstance(data, dict) and data.get("ok") in (True, "true") and playable(data.get("url")):
            return data["url"]
        return None

    # --- underneath ------------------------------------------------------

    async def _stations(self, query: dict, offset: int) -> list[Station]:
        params = {**query, "hidebroken": "true", "limit": str(PAGE),
                  "offset": str(max(0, int(offset)))}
        data = await self._list("/json/stations/search", params)
        stations = []
        seen = set()
        for entry in data:
            station = Station.from_directory(entry)
            if station is not None and station.id not in seen:
                seen.add(station.id)
                stations.append(station)
        return stations

    async def _list(self, path: str, params: dict) -> list:
        """A list from the cache when it is under a day old, else asked.
        Raises `Unreachable` when it cannot be asked and none is kept."""
        key = self._key(path, params)
        kept = self._read(key)
        if kept is not None:
            return kept
        data = await self._ask(path, params)
        if not isinstance(data, list):
            # A server that answered something else answered nothing usable;
            # it is not kept, so the next look asks again.
            logger.warning("radio directory: %s answered %s, not a list", path, type(data).__name__)
            return []
        self._write(key, path, params, data)
        return data

    async def _ask(self, path: str, params: dict | None, *, timeout: float = TIMEOUT_S,
                   rediscover: bool = True):
        """Each server in turn until one answers. A 4xx is an answer (the
        directory has no such thing); a 5xx, a timeout or a refused
        connection passes to the next."""
        servers = await self._server_list(rediscover)
        session = self._ensure()
        for base in servers:
            try:
                async with session.get(f"{base}{path}", params=params,
                                       timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                    if response.status >= 500:
                        logger.info("radio directory: %s answered %s", base, response.status)
                        continue
                    self.reachable = True
                    if response.status >= 400:
                        return None
                    return await response.json(content_type=None)
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
                logger.info("radio directory: %s did not answer (%s)", base, exc or type(exc).__name__)
                continue
        self.reachable = False
        # Every server failed: look them up afresh next time.
        self._servers_at = 0.0
        raise Unreachable(path)

    async def _server_list(self, rediscover: bool) -> list[str]:
        now = self._clock()
        if self._servers and now - self._servers_at < SERVERS_FRESH_S:
            return self._servers
        if not rediscover and self._servers:
            return self._servers
        servers = await self._discover()
        if servers:
            self._servers, self._servers_at = list(servers), now
        return self._servers

    def _ensure(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            if self._session_factory is not None:
                self._session = self._session_factory()
            else:
                self._session = aiohttp.ClientSession(headers={"User-Agent": self._user_agent})
        return self._session

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()

    @staticmethod
    def _key(path: str, params: dict) -> str:
        text = path + "?" + "&".join(f"{k}={params[k]}" for k in sorted(params))
        return hashlib.sha256(text.encode()).hexdigest()[:32]

    def _read(self, key: str) -> list | None:
        path = self._cache_dir / f"{key}.json"
        try:
            kept = json.loads(path.read_text())
        except (OSError, ValueError):
            return None
        at = kept.get("at") if isinstance(kept, dict) else None
        if not isinstance(at, (int, float)) or not 0 <= self._clock() - at < FRESH_S:
            return None
        data = kept.get("data")
        return data if isinstance(data, list) else None

    def _write(self, key: str, path: str, params: dict, data: list) -> None:
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            target = self._cache_dir / f"{key}.json"
            temporary = target.with_suffix(".tmp")
            temporary.write_text(json.dumps({"at": self._clock(), "path": path,
                                             "params": params, "data": data}))
            temporary.replace(target)
            self._trim()
        except OSError as exc:
            logger.warning("radio directory: cannot keep %s: %s", path, exc)

    def _trim(self) -> None:
        files = list(self._cache_dir.glob("*.json"))
        if len(files) <= CACHE_KEEP:
            return
        files.sort(key=lambda p: p.stat().st_mtime)
        for old in files[:len(files) - CACHE_KEEP]:
            old.unlink(missing_ok=True)


def _named_count(entry) -> bool:
    return (isinstance(entry, dict) and isinstance(entry.get("name"), str)
            and entry["name"].strip() != ""
            and isinstance(entry.get("stationcount"), int) and entry["stationcount"] > 0)
