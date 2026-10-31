# SPDX-License-Identifier: GPL-3.0-or-later
"""**The panel proves itself** (ADR-0170, found 2026-10-30).

The panel was told apart by arriving on loopback (ADR-0035 §6). A plugin calls
the core from 127.0.0.1 too, so loopback alone let one report touches, answer
*Keep this screen?*, keep a new address, park the renderers or read the phone's
touchpad. The core keeps a token per boot in `/run`, readable by root and the
kiosk's user only; the kiosk opens its page with it, and the page sends it
with its requests. A plugin's unit cannot see the kiosk's command line
(`ProtectProc=invisible`).
"""
from __future__ import annotations

import grp
import logging
import os
import secrets
from pathlib import Path

logger = logging.getLogger("gexis_core.panel_token")

#: Kept until the next boot: the core restarts after an install, the kiosk
#: does not, and its page keeps the token it was opened with.
PATH = Path("/run/gexis/panel-token")
#: The kiosk's user (`gexis-kiosk.service`).
GROUP = "pi"
#: How the page sends it; a socket, which cannot send headers, puts it in
#: its address as `?panel=`.
HEADER = "X-Gexis-Panel"
QUERY = "panel"


def ensure(path: Path = PATH, group: str = GROUP) -> str | None:
    """This boot's token, made by the first start after boot. None when it
    can be neither read nor made: loopback alone then, as before."""
    try:
        token = path.read_text().strip()
        if token:
            return token
    except OSError:
        pass
    token = secrets.token_urlsafe(32)
    tmp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640)
        with os.fdopen(fd, "w") as out:
            out.write(token + "\n")
        try:
            os.chown(tmp, 0, grp.getgrnam(group).gr_gid)
        except (KeyError, PermissionError) as exc:
            logger.warning("panel token: not given to %s: %s", group, exc)
        os.replace(tmp, path)
    except OSError as exc:
        logger.error("panel token: not made (%s); the panel is told apart by loopback alone", exc)
        return None
    return token
