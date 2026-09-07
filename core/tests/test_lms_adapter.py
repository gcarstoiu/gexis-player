"""Unit tests for the parts of LmsAdapter that don't need a network.

signal_stop and release_ladder went through two reverted attempts
(2026-09-06, 2026-09-07) at routing around squeezelite's -C idle timer
before landing on the actual fix (-C 1, squeezelite.service) - see
adapters/lms.py's class-level comment. As of 2026-09-08 this adapter is
back to the supervisor's default ladder behaviour, same as any other
adapter with no override; these tests guard against a *third* attempt
silently reintroducing special-casing.

The CometD/JSON-RPC parts need a real LMS server and are covered by live
hardware sessions instead (see adapters/lms.py's own module docstring).
"""
from __future__ import annotations

import pytest

from gexis_core.adapters.lms import LmsAdapter


@pytest.mark.asyncio
async def test_signal_stop_respects_force_like_any_other_adapter(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "gexis_core.adapters.lms.kill_unit",
        lambda unit, force: calls.append((unit, force)),
    )

    adapter = LmsAdapter("127.0.0.1", 9000, "gexis")

    await adapter.signal_stop(force=False)
    await adapter.signal_stop(force=True)

    assert calls == [
        ("squeezelite.service", False),
        ("squeezelite.service", True),
    ]


def test_no_release_ladder_override():
    # -C 1 (squeezelite.service) makes the supervisor's default grace
    # periods work fine for LMS now - no per-adapter override needed.
    assert LmsAdapter.release_ladder is None
