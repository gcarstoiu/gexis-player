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
    ) -> None:
        """`device_busy` is a zero-arg callable (sync or async) returning
        whether the shared ALSA device is currently held by anything -
        injected rather than imported directly so the state machine is
        testable without touching /proc or spawning fuser.
        """
        if BASE_RENDERER not in adapters:
            raise ValueError(f"base slot renderer {BASE_RENDERER!r} must have an adapter")
        self._adapters = adapters
        self._device_busy = device_busy
        self._ladder = ladder or TimeoutLadder()
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
            await self._release_with_ladder(outgoing)

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
        if not await self._busy():
            logger.info(
                "release[%s]: polite stop freed the device (%.1fs)",
                renderer_id,
                time.monotonic() - t0,
            )
            return ReleaseOutcome.POLITE

        if ladder.polite_grace > 0:
            await asyncio.sleep(ladder.polite_grace)
            if not await self._busy():
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
        if not await self._busy():
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
        if await self._busy():
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

    async def _busy(self) -> bool:
        result = self._device_busy()
        if asyncio.iscoroutine(result):
            return await result
        return result
