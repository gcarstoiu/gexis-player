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
    return [
        {
            "address": address,
            "name": fields.get("NAME", "").strip(),
            "version": fields.get("VERS", "").strip(),
            "uuid": fields.get("UUID", "").strip(),
        }
        for address, fields in sorted(protocol.found.items())
    ]
