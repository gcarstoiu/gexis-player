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


# --- ADR-0027: pause-then-power-off, and replaying what the user left ------


class FakeRpc:
    """Records the commands `release()`/`device_freed()` send, and answers
    the one status query they make. Stands in for the whole aiohttp session
    so these stay tier-1 tests with no network."""

    def __init__(self, mode="play"):
        self.mode = mode
        self.commands = []

    async def __call__(self, session, player, command):
        self.commands.append(list(command))
        if command[0] == "status":
            return {"result": {"mode": self.mode, "power": 1}}
        return {"result": {}}


def _adapter(monkeypatch, mode):
    rpc = FakeRpc(mode)
    monkeypatch.setattr(LmsAdapter, "_rpc", rpc)
    adapter = LmsAdapter("127.0.0.1", 9000, "gexis")
    adapter._player_id = "aa:bb:cc:dd:ee:ff"
    return adapter, rpc


@pytest.mark.asyncio
async def test_release_pauses_before_powering_off(monkeypatch):
    """Order is the whole point (ADR-0027, Finding 018). Powering off a
    *playing* player makes LMS restore it as playing, which fires
    squeezelite's ALSA open 58ms later against a device the incoming
    renderer hasn't released - it fails and then waits out an untunable 5s
    retry tick. Pausing first means it is restored paused and makes no
    attempt at all."""
    adapter, rpc = _adapter(monkeypatch, mode="play")

    assert await adapter.release() is True

    assert rpc.commands == [["status", "-", 1], ["pause", 1], ["power", 0]]


@pytest.mark.asyncio
async def test_release_records_that_it_was_playing_and_device_freed_resumes(monkeypatch):
    adapter, rpc = _adapter(monkeypatch, mode="play")
    await adapter.release()
    rpc.commands.clear()

    await adapter.device_freed()

    assert rpc.commands == [["play"]]


@pytest.mark.asyncio
async def test_a_player_left_paused_comes_back_paused(monkeypatch):
    """George, 2026-09-12: the transport state on return is whatever the
    user left, never something we impose. A paused player gets no play."""
    adapter, rpc = _adapter(monkeypatch, mode="pause")
    await adapter.release()
    rpc.commands.clear()

    await adapter.device_freed()

    assert rpc.commands == []


@pytest.mark.asyncio
async def test_the_resume_fires_once_not_on_every_later_acquisition(monkeypatch):
    """Otherwise a user who activates the player themselves, long after an
    unrelated takeover, would have playback start under them."""
    adapter, rpc = _adapter(monkeypatch, mode="play")
    await adapter.release()
    await adapter.device_freed()
    rpc.commands.clear()

    await adapter.device_freed()

    assert rpc.commands == []


@pytest.mark.asyncio
async def test_device_freed_sends_nothing_without_a_preceding_release(monkeypatch):
    """Activating the player with no takeover involved - first boot, or the
    user turning it on after turning it off themselves. LMS restores its own
    transport state natively there; we must not add a play on top."""
    adapter, rpc = _adapter(monkeypatch, mode="play")

    await adapter.device_freed()

    assert rpc.commands == []
