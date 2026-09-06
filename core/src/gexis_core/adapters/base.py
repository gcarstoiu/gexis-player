"""The adapter protocol every renderer implements (ARCHITECTURE.md §8).

Policy - who wins, what happens to who loses - lives in the supervisor
(arbitration.py). An adapter owns *mechanism* only: how this specific
renderer is told to let go, and how to tell whether it actually did.
"""
from __future__ import annotations

import abc
import enum


class ReleaseAction(enum.Enum):
    """What happens to a renderer that loses the device (ADR-0010 table)."""

    PAUSE = "pause"  # LMS only: stays connected, becomes idle
    DISCONNECT = "disconnect"  # everyone else


class Adapter(abc.ABC):
    """One renderer's acquisition/release behaviour."""

    #: Set by subclasses. Matches the key it's registered under in the
    #: supervisor's adapter map.
    renderer_id: str
    release_action: ReleaseAction

    @abc.abstractmethod
    async def run(self, on_acquire) -> None:
        """Long-running task. Watch for this renderer's acquisition event
        (ADR-0010's table - a deliberate connect/play, not a stream start)
        and call `on_acquire()` (sync, non-blocking) each time it fires.
        Runs for the lifetime of the process; must not return on a
        transient error, only log and keep watching.
        """

    @abc.abstractmethod
    async def release(self) -> bool:
        """Act on this renderer through its own control channel per
        `release_action` (pause for LMS, disconnect for everyone else).
        Return True if the renderer's own API confirmed the action - this
        is the "polite stop" step, not a guarantee the device is free; the
        supervisor checks that separately (alsa.device_busy).
        """

    @abc.abstractmethod
    async def signal_stop(self, force: bool) -> None:
        """Process-level escalation when `release()` didn't free the device
        in time. `force=False` is the SIGTERM step, `force=True` is SIGKILL.
        """
