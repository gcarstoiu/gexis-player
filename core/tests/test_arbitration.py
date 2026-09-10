"""Unit tests for the arbitration state machine and timeout ladder
(criteria 3, 4). No I/O, no hardware, no event loop wall-clock beyond a
few milliseconds - tier 1, runs on every commit.
"""
from __future__ import annotations

import asyncio

import pytest

from gexis_core.adapters.base import Adapter, ReleaseAction
from gexis_core.arbitration import BASE_RENDERER, Supervisor, TimeoutLadder

FAST_LADDER = TimeoutLadder(polite_grace=0.01, sigterm_grace=0.01, sigkill_grace=0.01)


class FakeAdapter(Adapter):
    """`holder` is a dict shared across all adapters in one test, standing
    in for "who currently has the ALSA device". `frees_at` controls which
    ladder step actually lets go, so tests can force each escalation path.
    """

    def __init__(
        self,
        renderer_id,
        release_action,
        holder,
        *,
        confirms=True,
        frees_at="release",
        frees_to=None,
        release_ladder=None,
    ):
        self.renderer_id = renderer_id
        self.unit_name = f"{renderer_id}.service"
        self.release_action = release_action
        self._holder = holder
        self._confirms = confirms
        self._frees_at = frees_at  # "release" | "sigterm" | "sigkill"
        # What the shared holder becomes once freed - None (nobody holds
        # it) by default, but a test can pass another renderer_id to
        # model the incoming renderer already having grabbed the device
        # by the time this one's release is checked.
        self._frees_to = frees_to
        self.release_ladder = release_ladder
        self.signals: list[str] = []
        self.release_calls = 0

    async def run(self, on_acquire):
        raise NotImplementedError("driven manually in these tests")

    async def release(self):
        self.release_calls += 1
        if self._frees_at == "release":
            self._holder["who"] = self._frees_to
        return self._confirms

    async def signal_stop(self, force: bool) -> None:
        self.signals.append("SIGKILL" if force else "SIGTERM")
        if not force and self._frees_at == "sigterm":
            self._holder["who"] = self._frees_to
        if force and self._frees_at in ("sigterm", "sigkill"):
            self._holder["who"] = self._frees_to


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
    supervisor = Supervisor(adapters, device_busy=lambda renderer_id: holder["who"] == renderer_id, ladder=FAST_LADDER)
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
async def test_release_not_confused_by_incoming_renderer_already_holding_device():
    """Found on hardware, 2026-09-08: the incoming renderer isn't driven by
    our own acquire() call - LMS tells squeezelite to play independently
    of it - so it can legitimately grab the device while the outgoing
    renderer's release ladder is still running. A busy check that only
    asks "is anyone holding it" can't tell that apart from the outgoing
    renderer never having let go, and escalated to SIGTERM then SIGKILL
    against go-librespot after it had already released cleanly - this is
    why `device_busy` takes the renderer_id being checked (alsa.py's
    `device_held_by`), not just "anyone"."""
    holder = {"who": None}
    lms = FakeAdapter("lms", ReleaseAction.PAUSE, holder)
    # spotify's release() here frees the device to "lms", not to None -
    # modelling the incoming renderer already holding it by the time this
    # release() call lands, the actual race reproduced on hardware.
    spotify = FakeAdapter(
        "spotify", ReleaseAction.DISCONNECT, holder, frees_at="release", frees_to="lms"
    )
    bluetooth = FakeAdapter("bluetooth", ReleaseAction.DISCONNECT, holder)
    supervisor = Supervisor(
        {"lms": lms, "spotify": spotify, "bluetooth": bluetooth},
        device_busy=lambda renderer_id: holder["who"] == renderer_id,
        ladder=FAST_LADDER,
    )

    holder["who"] = "lms"
    await supervisor.acquire("spotify")
    holder["who"] = "spotify"
    await supervisor.acquire("lms")  # "lms" already holds it by the time spotify's release() runs

    assert spotify.signals == []  # never escalated - correctly read as freed


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
async def test_adapter_specific_ladder_skips_the_polite_wait(monkeypatch):
    """George's decision, 2026-09-06: LMS shouldn't wait out squeezelite's
    `-C` idle timer at all. An adapter with `release_ladder.polite_grace
    == 0` should escalate to SIGTERM with no sleep in between, not just
    "a short one" - verified by recording every asyncio.sleep call rather
    than trusting wall-clock timing in a unit test.
    """
    slept: list[float] = []
    real_sleep = asyncio.sleep

    async def recording_sleep(seconds):
        slept.append(seconds)
        await real_sleep(0)  # yield control without actually waiting

    monkeypatch.setattr("gexis_core.arbitration.asyncio.sleep", recording_sleep)

    holder = {"who": "lms"}
    lms = FakeAdapter(
        "lms",
        ReleaseAction.PAUSE,
        holder,
        frees_at="sigterm",
        release_ladder=TimeoutLadder(polite_grace=0.0, sigterm_grace=5.0, sigkill_grace=5.0),
    )
    spotify = FakeAdapter("spotify", ReleaseAction.DISCONNECT, holder)
    bluetooth = FakeAdapter("bluetooth", ReleaseAction.DISCONNECT, holder)
    supervisor = Supervisor(
        {"lms": lms, "spotify": spotify, "bluetooth": bluetooth},
        device_busy=lambda renderer_id: holder["who"] == renderer_id,
        ladder=FAST_LADDER,
    )

    holder["who"] = "lms"  # lms is active by default (supervisor starts on base)
    await supervisor.acquire("spotify")  # takeover: lms is released, using its own ladder

    assert lms.signals == ["SIGTERM"]  # escalated, frees_at="sigterm" resolves it there
    # Only the sigterm_grace sleep happened - no 0.0 polite sleep, and no
    # sigkill_grace sleep since SIGTERM already freed it.
    assert slept == [5.0]


@pytest.mark.asyncio
async def test_unknown_renderer_rejected():
    supervisor, _, _ = build()
    with pytest.raises(ValueError):
        await supervisor.acquire("qobuz")


@pytest.mark.asyncio
async def test_base_renderer_missing_adapter_rejected():
    with pytest.raises(ValueError):
        Supervisor(
            {"spotify": FakeAdapter("spotify", ReleaseAction.DISCONNECT, {})},
            device_busy=lambda renderer_id: False,
        )


@pytest.mark.asyncio
async def test_restore_volume_called_with_the_newly_active_renderer():
    """George's decision, 2026-09-07: each renderer's volume is restored
    when it becomes active - not reset to the boot-safe level on every
    takeover."""
    holder = {"who": None}
    adapters = {
        "lms": FakeAdapter("lms", ReleaseAction.PAUSE, holder),
        "spotify": FakeAdapter("spotify", ReleaseAction.DISCONNECT, holder),
        "bluetooth": FakeAdapter("bluetooth", ReleaseAction.DISCONNECT, holder),
    }
    restored: list[str] = []

    async def restore_volume(renderer_id):
        restored.append(renderer_id)

    supervisor = Supervisor(
        adapters, device_busy=lambda renderer_id: holder["who"] == renderer_id, ladder=FAST_LADDER,
        restore_volume=restore_volume,
    )

    holder["who"] = "lms"
    await supervisor.acquire("spotify")
    holder["who"] = "spotify"
    await supervisor.acquire("bluetooth")

    assert restored == ["spotify", "bluetooth"]


@pytest.mark.asyncio
async def test_restore_volume_not_called_on_a_noop_reacquire():
    holder = {"who": None}
    adapters = {
        "lms": FakeAdapter("lms", ReleaseAction.PAUSE, holder),
        "spotify": FakeAdapter("spotify", ReleaseAction.DISCONNECT, holder),
        "bluetooth": FakeAdapter("bluetooth", ReleaseAction.DISCONNECT, holder),
    }
    restored: list[str] = []

    async def restore_volume(renderer_id):
        restored.append(renderer_id)

    supervisor = Supervisor(
        adapters, device_busy=lambda renderer_id: holder["who"] == renderer_id, ladder=FAST_LADDER,
        restore_volume=restore_volume,
    )

    holder["who"] = "lms"
    await supervisor.acquire("spotify")
    await supervisor.acquire("spotify")  # already active - no-op

    assert restored == ["spotify"]
