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
#: The list is asked for when the phone opens it; a second phone, or a second
#: look, within this long gets the same answer.
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
    try:
        proc = await asyncio.create_subprocess_exec(
            "avahi-browse", "-rpt", SERVICE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=BROWSE_TIMEOUT_S)
    except (OSError, asyncio.TimeoutError) as exc:
        logger.info("players: could not look for other players: %s", exc)
        return ""
    return out.decode(errors="replace")


class Players:
    """The others, with their status, kept for `FRESH_S`."""

    def __init__(self, own_host, *, browse=_browse, clock=time.monotonic) -> None:
        self._own_host = own_host
        self._browse = browse
        self._clock = clock
        self._kept: tuple[float, list[dict]] | None = None
        self._lock = asyncio.Lock()

    async def others(self, session: aiohttp.ClientSession) -> list[dict]:
        async with self._lock:
            if self._kept and self._clock() - self._kept[0] < FRESH_S:
                return self._kept[1]
            peers = parse_browse(await self._browse(), self._own_host())
            answers = await asyncio.gather(*(self._status(session, p) for p in peers))
            listed = [a for a in answers if a is not None]
            self._kept = (self._clock(), listed)
            return listed

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
        # The page to open is the player's own name, so a bookmark made there
        # survives its address changing.
        return {**body, "url": f"http://{peer['host']}:{peer['port']}/"}
