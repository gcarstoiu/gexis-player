# SPDX-License-Identifier: GPL-3.0-or-later
"""**A browser drives the player only from the player's own pages**
(ADR-0178 decision 1).

The API has no sign-in: ADR-0022 and ADR-0028 trust the home network. A web
page open in a browser on that network is on it too, and it could post to
the player - a factory reset, the volume, a plugin - or, under a public name
pointed at the player's address, read what it answers. Two rules, for
requests a browser makes; Home Assistant, curl and plugins send no browser
headers and are not affected:

- **A change, or a socket, comes from the player's own page**: an `Origin`
  that is not the page's own, or `Sec-Fetch-Site: cross-site`, is refused.
- **The player is named the way only the home network can**: an address, a
  name without dots, `localhost`, or a name under `.local`. A public name
  has dots and is not under `.local`.
"""
from __future__ import annotations

import ipaddress
from collections.abc import Mapping

#: Methods that change nothing; a socket is a GET that does, and is checked.
READS = frozenset({"GET", "HEAD", "OPTIONS"})

ORIGIN = "origin"
NAME = "name"


def own_name(host: str) -> bool:
    """Whether a `Host` header (or an `Origin`'s host and port) names the
    player as only the home network can."""
    name = host.strip().lower()
    if name.startswith("["):
        name = name[1:name.find("]")] if "]" in name else ""
    elif name.count(":") == 1:
        name = name.partition(":")[0]
    name = name.rstrip(".")
    if not name:
        return False
    try:
        ipaddress.ip_address(name.partition("%")[0])
        return True
    except ValueError:
        pass
    return "." not in name or name.endswith(".local")


def from_browser(headers: Mapping[str, str]) -> bool:
    """A browser sends one of these on every request; a program that is not
    one sends none (Home Assistant's own requests, curl, a plugin)."""
    return ("Origin" in headers or "Sec-Fetch-Site" in headers or "Sec-Fetch-Mode" in headers
            or "Mozilla/" in headers.get("User-Agent", ""))


def refused(method: str, headers: Mapping[str, str]) -> str | None:
    """Why a request is refused - `NAME` or `ORIGIN` - or None."""
    if not from_browser(headers):
        return None
    host = headers.get("Host", "")
    if not own_name(host):
        return NAME
    changes = method.upper() not in READS or headers.get("Upgrade", "").lower() == "websocket"
    if not changes:
        return None
    origin = headers.get("Origin")
    if origin is not None and origin.lower().rstrip("/") not in (f"http://{host.lower()}", f"https://{host.lower()}"):
        return ORIGIN
    if headers.get("Sec-Fetch-Site", "").lower() == "cross-site":
        return ORIGIN
    return None
