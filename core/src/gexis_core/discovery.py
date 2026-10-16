# SPDX-License-Identifier: GPL-3.0-or-later
"""Finding Lyrion servers on the network (ADR-0044 §1's `discover`).

**The protocol, verified against a real server on 2026-09-20** rather than
read from documentation: a datagram beginning with `e` and carrying 4-byte
tag names, each followed by a zero length byte, is broadcast to UDP 3483.
Every server answers with a datagram beginning with `E` and carrying the same
tags as `tag + length byte + value`:

    -> b'eIPAD\\x00NAME\\x00JSON\\x00VERS\\x00UUID\\x00'
    <- b'ENAME\\x1cLyrion Music Server (Docker)JSON\\x049000VERS\\x059.1.1UUID$...'

`IPAD` came back absent, so **the address is the datagram's source**, not a
field - a server behind more than one interface answers from the one that
can reach us, which is the one worth connecting to.

`JSON` is the CLI/web port, which is what an address in the settings means.
"""
from __future__ import annotations

import asyncio
import logging
import socket

logger = logging.getLogger(__name__)

#: What is asked for. Every tag is optional in the reply.
TAGS = (b"IPAD", b"NAME", b"JSON", b"VERS", b"UUID")
PORT = 3483
#: Long enough for a server on a busy network to answer, short enough that
#: the sheet does not feel stuck. Servers on the same LAN answered in well
#: under 100 ms in testing; this is the allowance for the ones that do not.
LISTEN_S = 2.5
#: The request is re-sent because UDP broadcast is not reliable and one lost
#: datagram would read as "no servers found".
RETRY_S = 0.8
#: How long a machine has to say its name (mDNS, all asked at once). One that
#: announces none - a server in Docker on its own address, found 2026-10-16 -
#: costs this much and is named another way.
RESOLVE_S = 2.0
#: The library name Lyrion gives itself unless someone changes it: it tells
#: one server from another no better than nothing.
DEFAULT_NAMES = ("Lyrion Music Server", "Logitech Media Server")


def _request() -> bytes:
    return b"e" + b"".join(tag + b"\x00" for tag in TAGS)


def parse(payload: bytes) -> dict[str, str]:
    """The TLV body of one reply. A truncated or unknown field ends the walk
    rather than raising: a server we cannot fully parse is still a server."""
    if not payload[:1] == b"E":
        return {}
    out: dict[str, str] = {}
    i = 1
    while i + 5 <= len(payload):
        tag = payload[i : i + 4].decode("ascii", "replace")
        length = payload[i + 4]
        start = i + 5
        if start + length > len(payload):
            break
        out[tag] = payload[start : start + length].decode("utf-8", "replace")
        i = start + length
    return out


class _Protocol(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self.found: dict[str, dict[str, str]] = {}

    def datagram_received(self, data: bytes, addr) -> None:
        fields = parse(data)
        if not fields:
            return
        host = addr[0]
        port = fields.get("JSON") or "9000"
        self.found[f"{host}:{port}"] = fields

    def error_received(self, exc) -> None:  # pragma: no cover - transport noise
        logger.debug("discovery: %s", exc)


async def find_servers(listen_s: float = LISTEN_S) -> list[dict[str, str]]:
    """Every Lyrion server that answers, newest answer wins per address.

    Never raises: a machine with no route to the broadcast address, or none
    at all, has found no servers - which is a true answer and the one the
    sheet's empty state is written for.
    """
    loop = asyncio.get_running_loop()
    try:
        transport, protocol = await loop.create_datagram_endpoint(
            _Protocol, family=socket.AF_INET, local_addr=("0.0.0.0", 0), allow_broadcast=True
        )
    except OSError as exc:
        logger.info("discovery: cannot open a socket: %s", exc)
        return []
    try:
        deadline = loop.time() + listen_s
        while loop.time() < deadline:
            try:
                transport.sendto(_request(), ("255.255.255.255", PORT))
            except OSError as exc:
                logger.info("discovery: cannot broadcast: %s", exc)
                break
            await asyncio.sleep(min(RETRY_S, max(0.0, deadline - loop.time())))
    finally:
        transport.close()
    found = sorted(protocol.found.items())
    hosts = await asyncio.gather(*(host_name(address.rsplit(":", 1)[0]) for address, _ in found))
    return [
        {
            "address": address,
            "name": fields.get("NAME", "").strip(),
            "version": fields.get("VERS", "").strip(),
            "uuid": fields.get("UUID", "").strip(),
            "host": host,
        }
        for (address, fields), host in zip(found, hosts)
    ]


async def host_name(ip: str, timeout_s: float = RESOLVE_S) -> str:
    """The name the machine at `ip` announces over mDNS (`Nuc.local` gives
    `Nuc`), or "" when it announces none or the tool is missing. Never
    raises: the address still names the server."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "avahi-resolve", "-a", ip,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    except OSError as exc:
        logger.info("discovery: no avahi-resolve: %s", exc)
        return ""
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout_s)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return ""
    parts = out.decode("utf-8", "replace").split()
    name = parts[1] if len(parts) >= 2 and parts[0] == ip else ""
    return name.removesuffix(".").removesuffix(".local")


def label(server: dict[str, str]) -> str:
    """What a found server is called on the screen (George, 2026-10-16:
    host names rather than addresses): the machine's own name, else the
    library name someone gave it in Lyrion, else its address."""
    name = server.get("name", "")
    if server.get("host"):
        return server["host"]
    if name and not name.startswith(DEFAULT_NAMES):
        return name
    return server["address"]
