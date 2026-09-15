# SPDX-License-Identifier: GPL-3.0-or-later
"""Whether the configured idle page can be shown (Phase 4 step 4d, ADR-0019).

The panel embeds the page in an iframe, and a cross-origin iframe cannot
tell the UI why it is blank. So the daemon asks instead: unconfigured,
unreachable, an error status, or headers that forbid framing all mean the
UI shows its built-in clock. Headers only — a page that frame-busts from
script still passes this check.
"""
from __future__ import annotations

import asyncio
import logging

import aiohttp
from multidict import CIMultiDict, CIMultiDictProxy

logger = logging.getLogger("gexis_core.idle_page")

PROBE_TIMEOUT_S = 5.0


def framing_allowed(headers: CIMultiDictProxy[str] | CIMultiDict[str]) -> bool:
    if headers.get("X-Frame-Options", "").strip():
        return False
    for policy in headers.getall("Content-Security-Policy", []):
        for directive in policy.split(";"):
            parts = directive.split()
            if parts and parts[0].lower() == "frame-ancestors" and "*" not in parts[1:]:
                return False
    return True


async def probe(url: str, session: aiohttp.ClientSession) -> dict:
    if not url:
        return {"url": None, "embeddable": False, "reason": "unconfigured"}
    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=PROBE_TIMEOUT_S), allow_redirects=True
        ) as response:
            if response.status >= 400:
                return {"url": url, "embeddable": False, "reason": f"http {response.status}"}
            if not framing_allowed(response.headers):
                return {"url": url, "embeddable": False, "reason": "refuses framing"}
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        logger.info("idle_page: %s unreachable: %s", url, exc)
        return {"url": url, "embeddable": False, "reason": "unreachable"}
    return {"url": url, "embeddable": True, "reason": None}
