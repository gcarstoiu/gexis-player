"""Unit tests for the parts of LmsAdapter that don't need a network.

signal_stop went through a full revert-then-restore-then-revert,
2026-09-06 through 2026-09-11 - see adapters/lms.py's class-level comment
for the reasoning behind each. As of 2026-09-11 (second time) it always
sends SIGKILL regardless of the ladder rung that called it, relying on
systemd's own Restart=on-failure to bring squeezelite back - a same-day
attempt at an adapter-driven explicit restart (stop_unit/
restart_after_release) was reverted after live use reproduced the exact
residual risk that attempt's own docs had already named. release_ladder
has no override (the supervisor's default grace periods are used, made to
work by -C 1 on squeezelite.service, not by adapter-specific timing).
These tests guard the two independently - a future attempt to "simplify"
by reverting signal_stop again should fail loudly, not silently reproduce
a defect this project already paid for twice.

The CometD/JSON-RPC parts need a real LMS server and are covered by live
hardware sessions instead (see adapters/lms.py's own module docstring).
"""
from __future__ import annotations

import pytest

from gexis_core.adapters.lms import LmsAdapter


@pytest.mark.asyncio
async def test_signal_stop_always_sends_sigkill_regardless_of_force(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "gexis_core.adapters.lms.kill_unit",
        lambda unit, force: calls.append((unit, force)),
    )

    adapter = LmsAdapter("127.0.0.1", 9000, "gexis")

    await adapter.signal_stop(force=False)  # the ladder's "SIGTERM" rung
    await adapter.signal_stop(force=True)  # the ladder's "SIGKILL" rung

    assert calls == [
        ("squeezelite.service", True),
        ("squeezelite.service", True),
    ]


def test_no_release_ladder_override():
    # -C 1 (squeezelite.service) makes the supervisor's default grace
    # periods work fine for LMS - no per-adapter timing override needed.
    # Escalation frequency and escalation signal are independent
    # decisions; this test is only about the former.
    assert LmsAdapter.release_ladder is None


@pytest.mark.asyncio
async def test_restart_after_release_is_the_inherited_noop():
    # Reverted 2026-09-11 (same day as introduced) - squeezelite's own
    # restart is systemd's job again (Restart=on-failure), not this
    # adapter's. Guards against silently reintroducing the override
    # without also reconsidering signal_stop's mechanism alongside it -
    # the two were designed and reverted as a pair, not independently.
    adapter = LmsAdapter("127.0.0.1", 9000, "gexis")
    assert await adapter.restart_after_release() is None
