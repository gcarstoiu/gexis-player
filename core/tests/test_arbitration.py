"""Unit tests for the arbitration state machine and timeout ladder
(criteria 3, 4). No I/O, no hardware, no event loop wall-clock beyond a
few milliseconds - tier 1, runs on every commit.
"""
from __future__ import annotations

import pytest

from gexis_core.adapters.base import Adapter, ReleaseAction
from gexis_core.arbitration import BASE_RENDERER, Supervisor, TimeoutLadder

FAST_LADDER = TimeoutLadder(polite_grace=0.01, sigterm_grace=0.01, sigkill_grace=0.01)


class FakeAdapter(Adapter):
    """`holder` is a dict shared across all adapters in one test, standing
    in for "who currently has the ALSA device". `frees_at` controls which
    ladder step actually lets go, so tests can force each escalation path.
    """

    def __init__(self, renderer_id, release_action, holder, *, confirms=True, frees_at="release"):
        self.renderer_id = renderer_id
        self.release_action = release_action
        self._holder = holder
        self._confirms = confirms
        self._frees_at = frees_at  # "release" | "sigterm" | "sigkill"
        self.signals: list[str] = []
        self.release_calls = 0

    async def run(self, on_acquire):
        raise NotImplementedError("driven manually in these tests")

    async def release(self):
        self.release_calls += 1
        if self._frees_at == "release":
            self._holder["who"] = None
        return self._confirms

    async def signal_stop(self, force: bool) -> None:
        self.signals.append("SIGKILL" if force else "SIGTERM")
        if not force and self._frees_at == "sigterm":
            self._holder["who"] = None
        if force and self._frees_at in ("sigterm", "sigkill"):
            self._holder["who"] = None


def build(frees_at_map: dict[str, str] | None = None):
    frees_at_map = frees_at_map or {}
    holder = {"who": None}
    adapters = {
        "lms": FakeAdapter(
            "lms", ReleaseAction.PAUSE, holder, frees_at=frees_at_map.get("lms", "release")
        ),
        "spotify": FakeAdapter(
            "spotify",
            ReleaseAction.DISCONNECT,
            holder,
            frees_at=frees_at_map.get("spotify", "release"),
        ),
        "bluetooth": FakeAdapter(
            "bluetooth",
            ReleaseAction.DISCONNECT,
            holder,
            frees_at=frees_at_map.get("bluetooth", "release"),
        ),
    }
    supervisor = Supervisor(adapters, device_busy=lambda: holder["who"] is not None, ladder=FAST_LADDER)
    return supervisor, adapters, holder


@pytest.mark.asyncio
async def test_base_slot_is_lms_by_default():
    supervisor, _, _ = build()
    assert supervisor.active == BASE_RENDERER


@pytest.mark.asyncio
async def test_acquire_takes_the_device_and_releases_the_previous_one():
    supervisor, adapters, holder = build()
    holder["who"] = "lms"
    await supervisor.acquire("spotify")
    assert supervisor.active == "spotify"
    assert adapters["lms"].release_calls == 1  # LMS paused, uniformly (ADR-0010)


@pytest.mark.asyncio
async def test_reacquiring_the_current_renderer_is_a_noop():
    supervisor, adapters, holder = build()
    holder["who"] = "lms"
    await supervisor.acquire("spotify")
    await supervisor.acquire("spotify")
    assert adapters["lms"].release_calls == 1  # only released on the first takeover


@pytest.mark.asyncio
async def test_takeover_returns_to_lms_not_a_stack():
    """ADR-0010: not a stack, no history. Releasing bluetooth returns to
    LMS even though spotify connected more recently and never released."""
    supervisor, adapters, holder = build()
    holder["who"] = "lms"
    await supervisor.acquire("spotify")
    holder["who"] = "spotify"
    await supervisor.acquire("bluetooth")
    assert supervisor.active == "bluetooth"
    holder["who"] = "bluetooth"
    await supervisor.acquire("lms")
    assert supervisor.active == BASE_RENDERER  # not "spotify"


async def _make_spotify_active(supervisor, holder):
    """Get spotify into the active slot for real (through the supervisor's
    own state, not just the fake `holder`), then hand control back to the
    test to arrange the release scenario it wants to exercise."""
    holder["who"] = "lms"
    await supervisor.acquire("spotify")  # lms releases cleanly (default "release")
    holder["who"] = "spotify"


@pytest.mark.asyncio
async def test_ladder_stops_at_polite_when_that_frees_the_device():
    supervisor, adapters, holder = build({"spotify": "release"})
    await _make_spotify_active(supervisor, holder)
    await supervisor.acquire("lms")
    assert adapters["spotify"].signals == []
    assert adapters["spotify"].release_calls == 1


@pytest.mark.asyncio
async def test_ladder_escalates_to_sigterm():
    supervisor, adapters, holder = build({"spotify": "sigterm"})
    await _make_spotify_active(supervisor, holder)
    await supervisor.acquire("lms")
    assert adapters["spotify"].signals == ["SIGTERM"]


@pytest.mark.asyncio
async def test_ladder_escalates_to_sigkill():
    supervisor, adapters, holder = build({"spotify": "sigkill"})
    await _make_spotify_active(supervisor, holder)
    await supervisor.acquire("lms")
    assert adapters["spotify"].signals == ["SIGTERM", "SIGKILL"]


@pytest.mark.asyncio
async def test_unknown_renderer_rejected():
    supervisor, _, _ = build()
    with pytest.raises(ValueError):
        await supervisor.acquire("qobuz")


@pytest.mark.asyncio
async def test_base_renderer_missing_adapter_rejected():
    with pytest.raises(ValueError):
        Supervisor({"spotify": FakeAdapter("spotify", ReleaseAction.DISCONNECT, {})}, device_busy=lambda: False)
