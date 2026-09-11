"""Unit tests for the parts of LmsAdapter that don't need a network.

signal_stop's escalation mechanism has changed twice - see adapters/lms.py's
class-level comment for the reasoning behind each. As of 2026-09-11 it uses
stop_unit (not a raw kill signal) regardless of the ladder rung that called
it, paired with restart_after_release bringing squeezelite back explicitly
rather than relying on systemd's Restart=on-failure at all; release_ladder
has no override (the supervisor's default grace periods are used, made to
work by -C 1 on squeezelite.service, not by adapter-specific timing). These
tests guard all of this independently - a future attempt to "simplify" by
reverting to kill_unit, or dropping restart_after_release, should fail
loudly, not silently reproduce a defect this project already paid for once.

The CometD/JSON-RPC parts need a real LMS server and are covered by live
hardware sessions instead (see adapters/lms.py's own module docstring).
"""
from __future__ import annotations

import pytest

from gexis_core.adapters.lms import LmsAdapter


@pytest.mark.asyncio
async def test_signal_stop_always_stops_the_unit_regardless_of_force(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "gexis_core.adapters.lms.stop_unit",
        lambda unit: calls.append(unit),
    )

    adapter = LmsAdapter("127.0.0.1", 9000, "gexis")

    await adapter.signal_stop(force=False)  # the ladder's "SIGTERM" rung
    await adapter.signal_stop(force=True)  # the ladder's "SIGKILL" rung

    assert calls == ["squeezelite.service", "squeezelite.service"]


@pytest.mark.asyncio
async def test_restart_after_release_starts_the_unit(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "gexis_core.adapters.lms.start_unit",
        lambda unit: calls.append(unit),
    )

    adapter = LmsAdapter("127.0.0.1", 9000, "gexis")
    await adapter.restart_after_release()

    assert calls == ["squeezelite.service"]


def test_no_release_ladder_override():
    # -C 1 (squeezelite.service) makes the supervisor's default grace
    # periods work fine for LMS - no per-adapter timing override needed.
    # Escalation frequency and escalation signal are independent
    # decisions; this test is only about the former.
    assert LmsAdapter.release_ladder is None
