"""Unit tests for the parts of LmsAdapter that don't need a network -
signal_stop's SIGKILL-always behaviour (George's decision, 2026-09-07).
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


def test_polite_grace_is_still_skipped():
    # Unchanged from the earlier decision - still don't wait out -C.
    assert LmsAdapter.release_ladder.polite_grace == 0.0
