# SPDX-License-Identifier: GPL-3.0-or-later
"""Arbitration supervisor: base slot + active slot (ADR-0010).

Base slot is permanently LMS - its connection is structural, not a user
session. Active slot holds at most one other renderer. Not a stack, no
history: release always returns to base, and nothing is restored because
nothing was stored.

This module is pure policy and has no I/O of its own - it is driven by
adapters (adapters/base.py) and is unit-testable without hardware or a
running event loop's real time (see tests/test_arbitration.py).
"""
from __future__ import annotations

import asyncio
import enum
import logging
import time
from dataclasses import dataclass

from gexis_core.adapters.base import Adapter

logger = logging.getLogger("gexis_core.arbitration")

BASE_RENDERER = "lms"


@dataclass(frozen=True)
class TimeoutLadder:
    """Escalation timings for release (criterion 4), in seconds."""

    polite_grace: float = 3.0
    sigterm_grace: float = 3.0
    sigkill_grace: float = 2.0


class ReleaseOutcome(enum.Enum):
    POLITE = "polite_stop"
    SIGTERM = "sigterm"
    SIGKILL = "sigkill"
    STILL_HELD = "still_held_after_sigkill"


class Supervisor:
    def __init__(
        self,
        adapters: dict[str, Adapter],
        *,
        device_busy,
        ladder: TimeoutLadder | None = None,
        restore_volume=None,
    ) -> None:
        """`device_busy` is a one-arg callable (sync or async), taking a
        renderer_id and returning whether *that specific renderer* still
        holds the shared ALSA device - not whether anyone does. Checking
        "anyone" is wrong here: by the time the release ladder runs, the
        incoming renderer (set active earlier in `acquire`, above) may
        already have legitimately opened the device, which would make a
        generic busy check report True forever regardless of whether the
        outgoing renderer ever released - found on hardware, 2026-09-08,
        as a false "still holds the device after SIGKILL" against
        go-librespot after it had already exited cleanly. Injected rather
        than imported directly so the state machine is testable without
        touching /proc or spawning fuser.

        `restore_volume`, if given, is an async callable taking the
        renderer_id that just acquired the device - George's decision,
        2026-09-07: each renderer keeps its own volume, restored when it
        becomes active (not reset to the boot-safe level on every
        takeover). Injected rather than imported for the same testing
        reason as `device_busy`; the lookup-remembered-or-default and
        hardware-mixer-scale logic lives in renderer_volume.py and
        __main__.py's wiring, not here - this module stays pure policy.
        """
        if BASE_RENDERER not in adapters:
            raise ValueError(f"base slot renderer {BASE_RENDERER!r} must have an adapter")
        self._adapters = adapters
        self._device_busy = device_busy
        self._ladder = ladder or TimeoutLadder()
        self._restore_volume = restore_volume
        self._active: str | None = None  # None means LMS (base) is current
        self._lock = asyncio.Lock()

    @property
    def active(self) -> str:
        return self._active or BASE_RENDERER

    async def acquire(self, renderer_id: str) -> None:
        """`renderer_id`'s acquisition event fired. Apply ADR-0010 policy:
        takeover disconnects the outgoing renderer (pause if it's LMS), no
        auto-resume, and re-acquiring the current renderer is a no-op.
        """
        if renderer_id not in self._adapters:
            raise ValueError(f"unknown renderer {renderer_id!r}")
        async with self._lock:
            if renderer_id == self.active:
                logger.debug("acquire: %s already current, ignoring", renderer_id)
                return
            outgoing = self.active
            self._active = None if renderer_id == BASE_RENDERER else renderer_id
            logger.info("acquire: %s takes the device (was %s)", renderer_id, outgoing)
            # ADR-0010: "release, uniformly" - LMS is not skipped just
            # because it's the base. Whoever was current gets released,
            # full stop.
            #
            # Released *before* restoring the incoming renderer's volume,
            # not after - found on hardware, 2026-09-10 (Finding 012).
            # Both write the same shared real DAC; the old order wrote the
            # incoming renderer's target volume first, which the outgoing
            # renderer's still-playing audio would carry for however long
            # its release ladder took (its own polite-stop grace is
            # seconds, not instant) - confirmed directly in gexis's log,
            # a Bluetooth->LMS handoff wrote the real DAC to LMS's 240/240
            # target 2.3s before Bluetooth's release actually completed,
            # audible as a brief loud blip on the Bluetooth audio still
            # playing. The incoming renderer generally can't produce
            # sound yet at this point anyway - the shared device is still
            # held by whoever's being released - so restoring its volume
            # only after release completes costs nothing and removes the
            # blip.
            await self._release_with_ladder(outgoing)
            if self._restore_volume is not None:
                await self._restore_volume(renderer_id)

    async def _release_with_ladder(self, renderer_id: str) -> ReleaseOutcome:
        adapter = self._adapters[renderer_id]
        ladder = adapter.release_ladder or self._ladder
        t0 = time.monotonic()

        confirmed = await adapter.release()
        if not confirmed:
            logger.warning(
                "release[%s]: adapter's own API did not confirm the action",
                renderer_id,
            )
        if not await self._busy(renderer_id):
            logger.info(
                "release[%s]: polite stop freed the device (%.1fs)",
                renderer_id,
                time.monotonic() - t0,
            )
            return ReleaseOutcome.POLITE

        if ladder.polite_grace > 0:
            await asyncio.sleep(ladder.polite_grace)
            if not await self._busy(renderer_id):
                logger.info(
                    "release[%s]: freed within polite grace (%.1fs)",
                    renderer_id,
                    time.monotonic() - t0,
                )
                return ReleaseOutcome.POLITE

        logger.warning(
            "release[%s]: still holds the device after polite stop, sending SIGTERM",
            renderer_id,
        )
        await adapter.signal_stop(force=False)
        await asyncio.sleep(ladder.sigterm_grace)
        if not await self._busy(renderer_id):
            logger.warning(
                "release[%s]: freed after SIGTERM (%.1fs)",
                renderer_id,
                time.monotonic() - t0,
            )
            return ReleaseOutcome.SIGTERM

        logger.error(
            "release[%s]: still holds the device after SIGTERM, sending SIGKILL",
            renderer_id,
        )
        await adapter.signal_stop(force=True)
        await asyncio.sleep(ladder.sigkill_grace)
        if await self._busy(renderer_id):
            logger.error(
                "release[%s]: STILL holds the device after SIGKILL (%.1fs)",
                renderer_id,
                time.monotonic() - t0,
            )
            return ReleaseOutcome.STILL_HELD
        logger.error(
            "release[%s]: freed after SIGKILL (%.1fs)", renderer_id, time.monotonic() - t0
        )
        return ReleaseOutcome.SIGKILL

    async def _busy(self, renderer_id: str) -> bool:
        result = self._device_busy(renderer_id)
        if asyncio.iscoroutine(result):
            return await result
        return result
