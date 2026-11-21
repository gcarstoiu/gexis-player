# SPDX-License-Identifier: GPL-3.0-or-later
"""**Spotify keeps playing on the lead through a group change** (ADR-0183).

A group change rewrites the chain under the lead's renderers, and every
renderer stops for it (LESSONS 21: a held card answers nothing), which for
go-librespot ends the Spotify Connect session. Its pause closes the ALSA
device and its resume opens it again after reading ALSA's configuration
afresh (`output/driver-alsa.go`), so the chain can be rewritten under a
paused session: the others stopped, the file written, the others restarted
and Spotify resumed - its unit never stopped. What the phone sees is a pause
for as long as the rewrite takes.

The steps are given in by the core (`__main__._group_rechain`), so the order
and every way out are tested here.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

#: How long go-librespot is given to let the device go after its pause.
LET_GO_S = 2.0
LET_GO_POLL_S = 0.1
#: go-librespot defers a state push within 200 ms of the one before
#: (`statePutMinInterval`); a resume that soon after the pause would leave the
#: phone the paused state unsent (the adapter's `release` waits the same).
SETTLE_S = 0.25


async def keep_spotify_playing(
    spotify,
    *,
    holds: Callable[[], bool],
    rewrite: Callable[[], Awaitable[None]],
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> bool:
    """Rewrite the chain under a paused Spotify, then resume it if it was
    playing. `holds()` says whether go-librespot still has the device;
    `rewrite()` stops the other renderers, writes the chain and restarts
    them, leaving go-librespot's unit alone.

    False, with nothing written, when Spotify's state cannot be read, its
    pause is refused or the device is not let go in `LET_GO_S`: the caller
    then rewrites as before, stopping go-librespot with the rest.
    """
    playing = await spotify.playing_now()
    if playing is None:
        logger.info("rechain: Spotify's state could not be read; the chain is rewritten as before")
        return False
    paused_at = None
    if playing:
        if not await spotify.pause():
            logger.warning("rechain: Spotify's pause was refused; the chain is rewritten as before")
            return False
        paused_at = clock()
    waited = 0.0
    while holds():
        if waited >= LET_GO_S:
            logger.warning("rechain: Spotify still held the device %.1f s after its pause; "
                           "the chain is rewritten as before", LET_GO_S)
            return False
        await sleep(LET_GO_POLL_S)
        waited += LET_GO_POLL_S
    logger.info("rechain: the group changed under Spotify - %s, rewriting (ADR-0183)",
                "paused" if playing else "already paused")
    await rewrite()
    if paused_at is not None:
        left = SETTLE_S - (clock() - paused_at)
        if left > 0:
            await sleep(left)
        if not await spotify.play():
            logger.warning("rechain: Spotify's resume after the group change was refused")
    return True
