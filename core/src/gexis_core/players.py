# SPDX-License-Identifier: GPL-3.0-or-later
"""**The other players on the network** (ADR-0136), for the phone's switcher.

Each player announces `_gexis._tcp` through avahi. This finds them with
`avahi-browse`, asks each for its `/player/status`, and answers the phone with
the list - the browser never reaches across addresses itself. A player that
is off, unreachable or too old to announce is simply not listed.
"""
from __future__ import annotations

import asyncio
import logging
import time

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
        self._lock = asyncio.Lock()

    async def others(self, session: aiohttp.ClientSession) -> list[dict]:
        """What was last found; looked for now only if nothing has been yet,
        or what was found has gone stale (the watch not running)."""
        if self._kept and self._clock() - self._kept[0] < 2 * FRESH_S:
            return self._kept[1]
        return await self.refresh(session)

    async def refresh(self, session: aiohttp.ClientSession) -> list[dict]:
        async with self._lock:
            peers = parse_browse(await self._browse(), self._own_host())
            answers = await asyncio.gather(*(self._status(session, p) for p in peers))
            # **This player, found under another name, is still this player**
            # (George, 2026-10-12: GuestPi twice in the switcher). avahi had
            # renamed it `guestpi-2.local` after a name conflict, so the
            # hostname did not leave it out; its own status does.
            listed = [a for a in answers if a is not None
                      and not (self._own_instance and a.get("instance") == self._own_instance)]
            self._kept = (self._clock(), listed)
            return listed

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
