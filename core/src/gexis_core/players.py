# SPDX-License-Identifier: GPL-3.0-or-later
"""**The other players on the network** (ADR-0136), for the phone's switcher.

Each player announces `_gexis._tcp` through avahi. This finds them with
`avahi-browse`, asks each for its `/player/status`, and answers the phone with
the list - the browser never reaches across addresses itself. A player that
is off, unreachable or too old to announce is simply not listed; one that
does not answer this player but answers another is listed through it
(`via`).
"""
from __future__ import annotations

import asyncio
import functools
import hashlib
import logging
import time
from pathlib import Path
from typing import Awaitable, Callable

import aiohttp

logger = logging.getLogger(__name__)

SERVICE = "_gexis._tcp"
BROWSE_TIMEOUT_S = 5.0
STATUS_TIMEOUT_S = 2.0
#: **Kept warm in the background** (George, 2026-10-11: the switch "takes some
#: time to show up" - a search measured 1.0 s of the 1.16 s the phone waited).
#: The core looks every `FRESH_S`, so the phone's request is answered from
#: what was found.
FRESH_S = 30.0
#: **Asked again when a list opens** (George, 2026-11-14: bedroompi's menu
#: still showed a group he had undone on sofapi). Older than this, the
#: players already found are asked for their status once more - not the
#: network search, which takes up to `BROWSE_TIMEOUT_S`.
ASK_AGAIN_S = 5.0
#: **Told by another player that its group changed** (George, 2026-11-14:
#: undone on sofapi, still shown on the bar's list): the others are asked
#: again this long after, so the members' word, sent together, is one look.
HEARD_S = 0.3
#: ADR-0160 D5: the board's own serial number, which every Pi carries.
SERIAL = Path("/proc/device-tree/serial-number")


def parse_browse(out: str, own_host: str) -> list[dict]:
    """`avahi-browse -rpt` lines, resolved ones only (`=`), IPv4, one per
    host, this player left out. Fields: `=;iface;proto;name;type;domain;
    host;address;port;txt`."""
    found: dict[str, dict] = {}
    own = own_host.lower().removesuffix(".local")
    for line in out.splitlines():
        parts = line.split(";")
        if len(parts) < 9 or parts[0] != "=" or parts[2] != "IPv4" or parts[4] != SERVICE:
            continue
        host = parts[6].lower()
        if host.removesuffix(".local") == own or host in found:
            continue
        try:
            port = int(parts[8])
        except ValueError:
            continue
        found[host] = {"host": host, "address": parts[7], "port": port}
    return sorted(found.values(), key=lambda p: p["host"])


def stable_id(serial: Path = SERIAL) -> str | None:
    """ADR-0160 D5: an id that outlives a rename, a reflash and a factory
    reset - a hash of the board's serial, never the serial itself. None off
    a Pi."""
    try:
        raw = serial.read_text(errors="replace").strip("\x00\n ")
    except OSError:
        return None
    return hashlib.sha256(f"gexis:{raw}".encode()).hexdigest()[:16] if raw else None


@functools.cache
def own_id() -> str | None:
    return stable_id()


def status_line(state, sources) -> dict:
    """What this player says of itself: whether it plays, and through what."""
    metadata = getattr(state, "metadata", None)
    transport = getattr(metadata, "transport", None) or "stopped"
    active = getattr(state, "active", None)
    renderer = None
    if active:
        renderer = next((s.get("name") for s in sources if s.get("id") == active), None) or active
    return {"transport": transport, "renderer": renderer}


async def _browse() -> str:
    """What answered within `BROWSE_TIMEOUT_S`. **A player that never
    resolves does not take the others with it** (sofapi, 2026-10-16): one
    announced as `bedroompi-2` never answered, avahi-browse waited for it
    until its own 5 s, this gave up at the same 5 s, and every search came
    back empty - so the phone's switch to other players disappeared."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "avahi-browse", "-rpt", SERVICE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    except OSError as exc:
        logger.info("players: could not look for other players: %s", exc)
        return ""
    lines: list[bytes] = []

    async def read() -> None:
        while line := await proc.stdout.readline():
            lines.append(line)

    try:
        await asyncio.wait_for(read(), timeout=BROWSE_TIMEOUT_S)
    except asyncio.TimeoutError:
        logger.debug("players: a player did not answer in %s s; the others kept", BROWSE_TIMEOUT_S)
    finally:
        if proc.returncode is None:
            proc.kill()
        await proc.wait()
    return b"".join(lines).decode(errors="replace")


class Players:
    """The others, with their status, kept for `FRESH_S`."""

    def __init__(self, own_host, *, own_instance: str | None = None, browse=_browse,
                 clock=time.monotonic) -> None:
        self._own_host = own_host
        #: What this core's own status carries: an answer with it is this
        #: player, whatever name it was found under (see `refresh`).
        self._own_instance = own_instance
        self._browse = browse
        self._clock = clock
        self._kept: tuple[float, list[dict]] | None = None
        #: Where the last search found them, for asking again without one.
        self._found: list[dict] = []
        self._lock = asyncio.Lock()
        #: **Where each player answered, by its id** (ADR-0166): a group's
        #: members reach each other here. Not in the list the phone is given.
        self.addresses: dict[str, tuple[str, int]] = {}
        #: Told the statuses found, by id, after each look (the group's
        #: `reconcile`).
        self.on_refresh: Callable[[dict[str, dict]], Awaitable[None]] | None = None
        #: Called once the others are asked again after another player said
        #: its group changed (the state's `players_revision`).
        self.on_heard: Callable[[], None] | None = None
        self._heard = False
        self._hearing: asyncio.Task | None = None

    async def others(self, session: aiohttp.ClientSession, *, fresh: bool = False) -> list[dict]:
        """What was last found; looked for now only if nothing has been yet,
        or what was found has gone stale (the watch not running). `fresh`
        (a list opening): older than `ASK_AGAIN_S`, the players found are
        asked again what they are doing and with whom."""
        if self._kept and self._clock() - self._kept[0] < 2 * FRESH_S:
            if fresh and self._clock() - self._kept[0] >= ASK_AGAIN_S:
                return await self.ask_again(session)
            return self._kept[1]
        return await self.refresh(session)

    async def refresh(self, session: aiohttp.ClientSession) -> list[dict]:
        """The network searched, and each player found asked its status."""
        return await self._look(session, search=True)

    async def ask_again(self, session: aiohttp.ClientSession) -> list[dict]:
        """The players the last search found, asked their status again; a
        player that has come since waits for the next search."""
        return await self._look(session, search=False)

    async def _look(self, session: aiohttp.ClientSession, *, search: bool) -> list[dict]:
        async with self._lock:
            if search:
                self._found = parse_browse(await self._browse(), self._own_host())
            peers = self._found
            answers = await asyncio.gather(*(self._status(session, p) for p in peers))
            # **This player, found under another name, is still this player**
            # (George, 2026-10-12: GuestPi twice in the switcher). avahi had
            # renamed it `guestpi-2.local` after a name conflict, so the
            # hostname did not leave it out; its own status does.
            listed = [a for a in answers if a is not None
                      and not (self._own_instance and a.get("instance") == self._own_instance)]
            for peer, answer in zip(peers, answers):
                if answer is not None and answer.get("id") and answer in listed:
                    self.addresses[str(answer["id"])] = (peer["address"], peer["port"])
            if any(a is None for a in answers) and listed:
                direct = [(peer, a) for peer, a in zip(peers, answers) if a is not None and a in listed]
                listed = listed + await self._through(session, direct, listed)
            self._kept = (self._clock(), listed)
        if self.on_refresh is not None:
            try:
                # The group reaches only the players it can itself.
                await self.on_refresh({str(a["id"]): a for a in listed if a.get("id") and not a.get("via")})
            except Exception:  # noqa: BLE001 - a look must not fail for what is done with it
                logger.exception("players: what was found could not be passed on")
        return listed

    async def _through(self, session: aiohttp.ClientSession, direct: list[tuple[dict, dict]],
                       listed: list[dict]) -> list[dict]:
        """**A player found that did not answer, listed through one that
        did** (ADR-0136 item 5; George, 2026-11-14: bedroompi and guestpi
        could not reach each other on the home network, each reached the
        other two). Each player that answered is asked for its own list; a
        player one of them reached itself, and this one did not, is added
        with `via`, that player's name. One hop: never one it had through a
        third."""
        ids = {str(p["id"]) for p in listed if p.get("id")}
        urls = {p.get("url") for p in listed}
        lists = await asyncio.gather(*(self._list_of(session, peer) for peer, _ in direct))
        added: dict[str, dict] = {}
        for (peer, answer), theirs in zip(direct, lists):
            for other in theirs:
                if not isinstance(other, dict) or other.get("via") or not other.get("url"):
                    continue
                if self._own_instance and other.get("instance") == self._own_instance:
                    continue
                key = str(other["id"]) if other.get("id") else other["url"]
                if key in ids or key in added or other["url"] in urls:
                    continue
                added[key] = {**other, "via": answer.get("name") or peer["host"]}
        return list(added.values())

    @staticmethod
    async def _list_of(session: aiohttp.ClientSession, peer: dict) -> list:
        """The players another player lists (`GET /players`), as it keeps them."""
        try:
            async with session.get(f"http://{peer['address']}:{peer['port']}/players",
                                   timeout=aiohttp.ClientTimeout(total=STATUS_TIMEOUT_S)) as response:
                if response.status != 200:
                    return []
                body = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            return []
        others = body.get("others") if isinstance(body, dict) else None
        return others if isinstance(others, list) else []

    async def tell_others(self) -> int:
        """**This player's group changed: every player found is told**
        (`POST /players/changed`), so its list asks again now rather than at
        its next look. One older than this answers 404 and waits for that
        look. The number told."""
        targets = list(dict.fromkeys(self.addresses.values()))
        if not targets:
            return 0
        async with aiohttp.ClientSession() as session:
            told = await asyncio.gather(*(self._tell(session, a, p) for a, p in targets))
        return sum(told)

    @staticmethod
    async def _tell(session: aiohttp.ClientSession, address: str, port: int) -> bool:
        try:
            async with session.post(f"http://{address}:{port}/players/changed",
                                    timeout=aiohttp.ClientTimeout(total=STATUS_TIMEOUT_S)) as response:
                return response.status == 200
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return False

    def heard(self) -> None:
        """Another player said its group changed: the players found are
        asked again `HEARD_S` later - once for several told together, again
        for one told meanwhile - then `on_heard`."""
        self._heard = True
        if self._hearing is None or self._hearing.done():
            self._hearing = asyncio.ensure_future(self._hear())

    async def _hear(self) -> None:
        while self._heard:
            self._heard = False
            await asyncio.sleep(HEARD_S)
            try:
                async with aiohttp.ClientSession() as session:
                    await self.ask_again(session)
            except Exception:  # noqa: BLE001 - the next look finds them
                logger.exception("players: asking again after a change failed")
                continue
            if self.on_heard is not None:
                self.on_heard()

    def status_of(self, player_id: str) -> dict | None:
        """What a player last said of itself, by id; not one listed only
        through another, which the group cannot reach."""
        listed = self._kept[1] if self._kept else []
        return next((p for p in listed if str(p.get("id")) == player_id and not p.get("via")), None)

    async def watch(self, every: float = FRESH_S) -> None:
        """Look for the others every `every` seconds, for the life of the core."""
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    await self.refresh(session)
                except Exception:  # noqa: BLE001 - a watch must not die quietly
                    logger.exception("players: looking for other players failed")
                await asyncio.sleep(every)

    @staticmethod
    async def _status(session: aiohttp.ClientSession, peer: dict) -> dict | None:
        url = f"http://{peer['address']}:{peer['port']}"
        try:
            async with session.get(f"{url}/player/status",
                                   timeout=aiohttp.ClientTimeout(total=STATUS_TIMEOUT_S)) as response:
                if response.status != 200:
                    return None
                body = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            return None
        if not isinstance(body, dict):
            # Not a player's status: one odd peer must not fail the whole list.
            return None
        # The page to open is the player's own name, so a bookmark made there
        # survives its address changing.
        return {**body, "url": f"http://{peer['host']}:{peer['port']}/"}
