# SPDX-License-Identifier: GPL-3.0-or-later
"""Arbitration supervisor: at most one renderer holds the device (ADR-0027).

**No base slot.** Every renderer is a peer: it takes the device on its own
acquisition event and gives it up on release, LMS included. `active` is
`None` whenever nobody holds it, which is a routine state rather than an
error - LMS is deactivated on every takeover and stays deactivated until
the user activates it again, so "nothing is playing and nothing is
current" is where the system sits between sessions.

Not a stack, no history (ADR-0010, still in force): release does not hand
the device back to whoever had it before, and nothing is restored because
nothing was stored.

**Superseded premise, kept so the change is legible:** until 2026-09-12
this module implemented ADR-0010's base slot - LMS was permanently
current, `_active = None` *meant* "LMS", and release always returned
there. That model assumed squeezelite's LMS connection was structural
rather than a user session. ADR-0027 removed the assumption: LMS's player
power is now the arbitration mechanism, which makes it as absent as any
other renderer when it is off.

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

# Finding 016: the polite rung used to `asyncio.sleep(ladder.polite_grace)`
# blind, then check once - the "freed within polite grace" log line was
# measuring the sleep, not the renderer, and every LMS handoff landed at
# ~polite_grace regardless of how fast the device actually freed. Polling
# at this cadence makes that log line - and the time it feeds into
# criterion 8's numbers - an actual measurement instead.
POLITE_POLL_INTERVAL = 0.1


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
        on_active_change=None,
        on_handoff_change=None,
        enabled=None,
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

        `on_active_change`, if given, is a callable taking the new active
        renderer id (or None for nobody) - Phase 3 criterion 1's state
        store (state.py) hooks in here so the published model reflects a
        takeover the moment it happens, not on some later poll. Called
        after `_active` is already updated, so a callback that reads
        `self.active` back sees the new value; called synchronously, so it
        must not block - state.py's own callback is a plain dict/list
        update, no I/O.
        """
        if not adapters:
            raise ValueError("supervisor needs at least one adapter")
        self._adapters = adapters
        self._device_busy = device_busy
        self._ladder = ladder or TimeoutLadder()
        self._restore_volume = restore_volume
        self._on_active_change = on_active_change
        #: Phase 4 criterion 4. Called `(outgoing, incoming)` when a
        #: takeover starts and `(None, None)` when it finishes - both
        #: edges, so a transition screen has something to appear and
        #: disappear on. Same sync, non-blocking contract as
        #: `on_active_change`.
        self._on_handoff_change = on_handoff_change
        #: **ADR-0077.** A one-arg predicate taking a renderer_id and saying
        #: whether that source is switched on. `None` means every renderer is,
        #: which is what the tests and every caller before ADR-0077 assume.
        #:
        #: Checked here rather than at the callers because arbitration is the
        #: one place every route into taking the device passes through - an
        #: acquisition event, `activate` from the panel, the reclaim after a
        #: session ends - and a gate at three callers is a gate missing from
        #: the fourth.
        self._enabled = enabled
        # None means *nobody* holds the device (ADR-0027). Until
        # 2026-09-12 this same None meant "LMS", which is why the
        # distinction is called out rather than left to the type.
        self._active: str | None = None
        self._lock = asyncio.Lock()

    @property
    def active(self) -> str | None:
        """The renderer currently holding the device, or None for nobody.

        None is routine, not an error state and not a stand-in for LMS -
        see the module docstring. Callers that compare against a renderer
        id are fine; callers that *use* the value (attributing a volume
        change, say) have to handle None explicitly.
        """
        return self._active

    async def acquire(self, renderer_id: str) -> None:
        """`renderer_id`'s acquisition event fired. Apply ADR-0010 policy as
        amended by ADR-0027: whoever held the device is released (for LMS
        that is pause-then-power-off, in its adapter), no auto-resume, and
        re-acquiring the current renderer is a no-op. Acquiring when nobody
        holds the device is the ordinary cold-start case - there is simply
        nothing to release.
        """
        if renderer_id not in self._adapters:
            raise ValueError(f"unknown renderer {renderer_id!r}")
        # ADR-0077: a renderer that is switched off does not take the device,
        # whatever fired. Refused outside the lock and before anything is
        # published: nothing about this is a takeover, so there is no handoff
        # to report and nobody is released.
        if self._enabled is not None and not self._enabled(renderer_id):
            logger.info("acquire: %s is switched off, refusing", renderer_id)
            return
        async with self._lock:
            if renderer_id == self._active:
                logger.debug("acquire: %s already current, ignoring", renderer_id)
                return
            outgoing = self._active
            self._active = renderer_id
            self._notify_active_change()
            logger.info(
                "acquire: %s takes the device (was %s)", renderer_id, outgoing or "nobody"
            )
            # ADR-0010: "release, uniformly" - no renderer is skipped.
            # Whoever was current gets released, full stop. `outgoing` is
            # None only when nobody held the device, and then there is
            # nothing to release.
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
            # Phase 4 criterion 4: a takeover is in flight from here until
            # the whole sequence below finishes. Reported at both edges so
            # the UI can show a transition state for the *pair* - and
            # cleared in a `finally` because a handoff that got stuck on
            # screen because the ladder raised would be exactly the
            # unaccountable state ADR-0010 exists to prevent. Only a
            # takeover has a pair: a cold acquisition with nobody holding
            # the device reports nothing.
            if outgoing is not None:
                self._notify_handoff(outgoing, renderer_id)
            try:
                await self._acquire_sequence(outgoing, renderer_id)
            finally:
                if outgoing is not None:
                    self._notify_handoff(None, None)

    async def _acquire_sequence(self, outgoing: str | None, renderer_id: str) -> None:
        """The release/restore/retry steps of an acquisition, extracted from
        `acquire` only so the handoff edges above can bracket it in a
        `finally` without indenting the whole body."""
        if outgoing is not None:
            await self._release_with_ladder(outgoing)
        if self._restore_volume is not None:
            await self._restore_volume(renderer_id)
        # Finding 014: give the incoming renderer a chance to retry its
        # own acquisition now that the device is confirmed free - by
        # default a no-op (adapters/base.py's device_freed docstring),
        # only SpotifyAdapter currently overrides it. Volume is
        # restored first so a renderer whose retry actually starts
        # audible playback here does so at the right level from the
        # first sample, not a beat later.
        await self._adapters[renderer_id].device_freed()
        # Finding 013 §1's recurrence, 2026-09-11: give the outgoing
        # renderer a chance to come back under our own control if it
        # had to be stopped rather than relying on systemd's automatic
        # Restart= - by default a no-op, only LmsAdapter currently
        # overrides it. Called last, after the incoming renderer has
        # had its own settled chance at the device, not because that
        # guarantees success (see adapters/base.py's docstring on the
        # residual risk), just because it's the best available
        # ordering.
        if outgoing is not None:
            await self._adapters[outgoing].restart_after_release()

    async def relinquish(self, renderer_id: str) -> None:
        """`renderer_id` gave up the device without anyone taking it over -
        the user deactivating the LMS player being the case ADR-0027
        creates deliberately. Leaves nobody holding it.

        **Ignored unless `renderer_id` is currently active**, which is what
        makes this safe to call from an adapter that cannot tell our own
        release apart from the user's. During a takeover the supervisor has
        already recorded the incoming renderer by the time our own
        pause-then-power-off lands, so LMS's resulting "powered off" event
        arrives for a renderer that is no longer active and correctly does
        nothing. That is deliberate: ADR-0027 declines to track *who*
        deactivated the player (George, 2026-09-12) on the grounds that the
        device's state is what matters, and this check is what makes that
        stance implementable without provenance.
        """
        if renderer_id not in self._adapters:
            raise ValueError(f"unknown renderer {renderer_id!r}")
        async with self._lock:
            if renderer_id != self._active:
                logger.debug(
                    "relinquish: %s is not current (%s is), ignoring",
                    renderer_id,
                    self._active or "nobody",
                )
                return
            self._active = None
            self._notify_active_change()
            logger.info("relinquish: %s gave up the device, nobody holds it now", renderer_id)

    def _notify_active_change(self) -> None:
        if self._on_active_change is not None:
            self._on_active_change(self._active)

    def _notify_handoff(self, from_renderer: str | None, to_renderer: str | None) -> None:
        if self._on_handoff_change is not None:
            self._on_handoff_change(from_renderer, to_renderer)

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
            deadline = time.monotonic() + ladder.polite_grace
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                await asyncio.sleep(min(POLITE_POLL_INTERVAL, remaining))
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
