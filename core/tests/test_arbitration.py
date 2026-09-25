"""Unit tests for the arbitration state machine and timeout ladder
(criteria 3, 4). No I/O, no hardware, no event loop wall-clock beyond a
few milliseconds - tier 1, runs on every commit.
"""
from __future__ import annotations

import asyncio

import pytest

from gexis_core.adapters.base import Adapter, ReleaseAction
from gexis_core.arbitration import Supervisor, TimeoutLadder

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
        self.device_freed_calls = 0
        self.restart_after_release_calls = 0

    async def run(self, on_acquire, on_release):
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

    async def device_freed(self) -> None:
        self.device_freed_calls += 1

    async def restart_after_release(self) -> None:
        self.restart_after_release_calls += 1


def build(frees_at_map: dict[str, str] | None = None, *, active: str | None = None):
    """`active` seeds "this renderer already holds the device when the test
    begins". Set directly rather than routed through `acquire()`, which
    would count adapter calls these tests then assert on. Needed explicitly
    since ADR-0027: the supervisor no longer assumes LMS is current, so a
    test wanting an outgoing renderer has to say which one."""
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
    if active is not None:
        supervisor._active = active
        holder["who"] = active
    return supervisor, adapters, holder


@pytest.mark.asyncio
async def test_nobody_holds_the_device_by_default():
    """ADR-0027 retired the base slot: `active` is None until some renderer
    actually acquires, where it used to report LMS unconditionally."""
    supervisor, _, _ = build()
    assert supervisor.active is None


@pytest.mark.asyncio
async def test_acquire_takes_the_device_and_releases_the_previous_one():
    supervisor, adapters, holder = build(active="lms")
    await supervisor.acquire("spotify")
    assert supervisor.active == "spotify"
    assert adapters["lms"].release_calls == 1  # LMS paused, uniformly (ADR-0010)


@pytest.mark.asyncio
async def test_reacquiring_the_current_renderer_is_a_noop():
    supervisor, adapters, holder = build(active="lms")
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
    assert supervisor.active == "lms"  # not "spotify" - no history


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

    holder["who"] = "lms"
    supervisor._active = "lms"  # ADR-0027: no implicit base, say so explicitly
    await supervisor.acquire("spotify")  # takeover: lms is released, using its own ladder

    assert lms.signals == ["SIGTERM"]  # escalated, frees_at="sigterm" resolves it there
    # Only the sigterm_grace sleep happened - no 0.0 polite sleep, and no
    # sigkill_grace sleep since SIGTERM already freed it.
    assert slept == [5.0]


@pytest.mark.asyncio
async def test_polite_grace_polls_instead_of_sleeping_blind(monkeypatch):
    """Finding 016: the polite rung used to sleep the full polite_grace
    blind, then check once - "freed within polite grace" was measuring the
    sleep, not the renderer. It must poll and return as soon as the device
    frees, well short of the ceiling, not wait it out."""
    slept: list[float] = []
    real_sleep = asyncio.sleep

    async def recording_sleep(seconds):
        slept.append(seconds)
        await real_sleep(0)  # yield control without actually waiting

    monkeypatch.setattr("gexis_core.arbitration.asyncio.sleep", recording_sleep)

    busy_calls = {"n": 0}

    def device_busy(renderer_id):
        busy_calls["n"] += 1
        # busy on release()'s own pre-sleep check and the first poll,
        # free by the second poll - independent of FakeAdapter's holder
        # dict, to pin down exactly how many polls ran.
        return busy_calls["n"] < 3

    holder = {"who": None}
    lms = FakeAdapter("lms", ReleaseAction.PAUSE, holder)
    spotify = FakeAdapter("spotify", ReleaseAction.DISCONNECT, holder)
    bluetooth = FakeAdapter("bluetooth", ReleaseAction.DISCONNECT, holder)
    supervisor = Supervisor(
        {"lms": lms, "spotify": spotify, "bluetooth": bluetooth},
        device_busy=device_busy,
        ladder=TimeoutLadder(polite_grace=1.0, sigterm_grace=0.01, sigkill_grace=0.01),
    )
    supervisor._active = "lms"  # ADR-0027: no implicit base, say so explicitly

    await supervisor.acquire("spotify")  # lms is released, polled for freedom

    # Two 0.1s polls, not one 1.0s blind sleep - freed long before the
    # 1.0s ceiling, which a blind sleep would have waited out regardless.
    assert slept == [pytest.approx(0.1), pytest.approx(0.1)]
    assert lms.signals == []  # never escalated - polling caught the release


@pytest.mark.asyncio
async def test_unknown_renderer_rejected():
    supervisor, _, _ = build()
    with pytest.raises(ValueError):
        await supervisor.acquire("qobuz")


@pytest.mark.asyncio
async def test_supervisor_needs_at_least_one_adapter():
    """ADR-0027: LMS is a peer, so there is no longer a *required* adapter -
    a build with no LMS is valid. An empty map is still a mistake."""
    with pytest.raises(ValueError):
        Supervisor({}, device_busy=lambda renderer_id: False)


@pytest.mark.asyncio
async def test_lms_is_not_privileged_anymore():
    supervisor = Supervisor(
        {"spotify": FakeAdapter("spotify", ReleaseAction.DISCONNECT, {"who": None})},
        device_busy=lambda renderer_id: False,
        ladder=FAST_LADDER,
    )
    assert supervisor.active is None
    await supervisor.acquire("spotify")
    assert supervisor.active == "spotify"


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
async def test_device_freed_called_on_incoming_adapter_only():
    """Finding 014: the incoming renderer gets a chance to retry its own
    acquisition once the outgoing renderer's release is confirmed - the
    default no-op costs nothing for adapters that don't need it, but the
    supervisor must call it on the right one, and only once."""
    supervisor, adapters, holder = build()
    holder["who"] = "lms"
    await supervisor.acquire("spotify")
    assert adapters["spotify"].device_freed_calls == 1
    assert adapters["lms"].device_freed_calls == 0
    assert adapters["bluetooth"].device_freed_calls == 0


@pytest.mark.asyncio
async def test_device_freed_not_called_on_noop_reacquire():
    supervisor, adapters, holder = build()
    holder["who"] = "lms"
    await supervisor.acquire("spotify")
    await supervisor.acquire("spotify")  # already active - no-op
    assert adapters["spotify"].device_freed_calls == 1


@pytest.mark.asyncio
async def test_device_freed_called_after_volume_restored():
    """Order matters (arbitration.py's own comment on the call site): if a
    renderer's retry actually starts audible playback, volume should
    already be at the right level, not a beat behind."""
    holder = {"who": None}
    adapters = {
        "lms": FakeAdapter("lms", ReleaseAction.PAUSE, holder),
        "spotify": FakeAdapter("spotify", ReleaseAction.DISCONNECT, holder),
        "bluetooth": FakeAdapter("bluetooth", ReleaseAction.DISCONNECT, holder),
    }
    order: list[str] = []

    async def restore_volume(renderer_id):
        order.append(f"restore_volume:{renderer_id}")

    class OrderedSpotify(FakeAdapter):
        async def device_freed(self):
            order.append("device_freed:spotify")
            await super().device_freed()

    adapters["spotify"] = OrderedSpotify("spotify", ReleaseAction.DISCONNECT, holder)

    supervisor = Supervisor(
        adapters, device_busy=lambda renderer_id: holder["who"] == renderer_id,
        ladder=FAST_LADDER, restore_volume=restore_volume,
    )

    holder["who"] = "lms"
    await supervisor.acquire("spotify")

    assert order == ["restore_volume:spotify", "device_freed:spotify"]


@pytest.mark.asyncio
async def test_restart_after_release_called_on_outgoing_adapter_only():
    """Finding 013 §1's recurrence: the *outgoing* renderer gets a chance
    to come back under our own control once release is confirmed -
    called on the one that was actually released, never the one taking
    over."""
    supervisor, adapters, holder = build(active="lms")
    await supervisor.acquire("spotify")
    assert adapters["lms"].restart_after_release_calls == 1
    assert adapters["spotify"].restart_after_release_calls == 0
    assert adapters["bluetooth"].restart_after_release_calls == 0


@pytest.mark.asyncio
async def test_restart_after_release_not_called_on_noop_reacquire():
    supervisor, adapters, holder = build(active="lms")
    await supervisor.acquire("spotify")
    await supervisor.acquire("spotify")  # already active - no-op
    assert adapters["lms"].restart_after_release_calls == 1


@pytest.mark.asyncio
async def test_restart_after_release_called_after_device_freed():
    """Order matters (arbitration.py's own comment on the call site):
    the outgoing renderer only gets its chance to come back after the
    incoming renderer has had its own settled shot at the device."""
    holder = {"who": None}
    order: list[str] = []

    class OrderedLms(FakeAdapter):
        async def restart_after_release(self):
            order.append("restart_after_release:lms")
            await super().restart_after_release()

    class OrderedSpotify(FakeAdapter):
        async def device_freed(self):
            order.append("device_freed:spotify")
            await super().device_freed()

    adapters = {
        "lms": OrderedLms("lms", ReleaseAction.PAUSE, holder),
        "spotify": OrderedSpotify("spotify", ReleaseAction.DISCONNECT, holder),
        "bluetooth": FakeAdapter("bluetooth", ReleaseAction.DISCONNECT, holder),
    }
    supervisor = Supervisor(
        adapters, device_busy=lambda renderer_id: holder["who"] == renderer_id,
        ladder=FAST_LADDER,
    )

    holder["who"] = "lms"
    supervisor._active = "lms"
    await supervisor.acquire("spotify")

    assert order == ["device_freed:spotify", "restart_after_release:lms"]


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


# --- ADR-0027: nobody holds the device ------------------------------------


@pytest.mark.asyncio
async def test_acquiring_from_nobody_releases_nothing():
    """The ordinary cold start. Under the base slot this path did not exist:
    something was always current, so every acquisition released someone."""
    supervisor, adapters, holder = build()
    await supervisor.acquire("spotify")
    assert supervisor.active == "spotify"
    assert all(a.release_calls == 0 for a in adapters.values())
    assert all(a.restart_after_release_calls == 0 for a in adapters.values())


@pytest.mark.asyncio
async def test_relinquish_leaves_nobody_holding_the_device():
    supervisor, _, holder = build(active="lms")
    await supervisor.relinquish("lms")
    assert supervisor.active is None


@pytest.mark.asyncio
async def test_relinquish_from_a_renderer_that_is_not_current_is_ignored():
    """This is what lets ADR-0027 skip tracking *who* deactivated the player
    (George, 2026-09-12). During a takeover the supervisor has already
    recorded the incoming renderer by the time our own power-off lands, so
    LMS's resulting "powered off" event arrives for a renderer that is no
    longer active - and must not blank out the renderer that just took over."""
    supervisor, _, holder = build(active="lms")
    await supervisor.acquire("spotify")
    assert supervisor.active == "spotify"

    await supervisor.relinquish("lms")  # the echo of our own release

    assert supervisor.active == "spotify"


@pytest.mark.asyncio
async def test_relinquish_rejects_an_unknown_renderer():
    supervisor, _, _ = build()
    with pytest.raises(ValueError):
        await supervisor.relinquish("qobuz")


# --- Phase 3 criterion 1: state store notification ------------------------


@pytest.mark.asyncio
async def test_on_active_change_fires_on_acquire():
    """state.py's StateStore hooks in here so the published model reflects
    a takeover the moment it happens (Phase 3 criterion 1)."""
    holder = {"who": None}
    adapters = {
        "lms": FakeAdapter("lms", ReleaseAction.PAUSE, holder),
        "spotify": FakeAdapter("spotify", ReleaseAction.DISCONNECT, holder),
        "bluetooth": FakeAdapter("bluetooth", ReleaseAction.DISCONNECT, holder),
    }
    changes: list[str | None] = []
    supervisor = Supervisor(
        adapters,
        device_busy=lambda renderer_id: holder["who"] == renderer_id,
        ladder=FAST_LADDER,
        on_active_change=changes.append,
    )

    await supervisor.acquire("lms")
    holder["who"] = "lms"
    await supervisor.acquire("spotify")

    assert changes == ["lms", "spotify"]


@pytest.mark.asyncio
async def test_on_active_change_fires_on_relinquish():
    changes: list[str | None] = []
    supervisor, _, holder = build(active="lms")
    supervisor._on_active_change = changes.append

    await supervisor.relinquish("lms")

    assert changes == [None]


@pytest.mark.asyncio
async def test_on_active_change_not_fired_on_noop_reacquire():
    changes: list[str | None] = []
    supervisor, _, holder = build(active="lms")
    supervisor._on_active_change = changes.append

    await supervisor.acquire("lms")  # already active - no-op

    assert changes == []


@pytest.mark.asyncio
async def test_on_active_change_not_fired_when_relinquish_is_ignored():
    changes: list[str | None] = []
    supervisor, _, holder = build(active="lms")
    await supervisor.acquire("spotify")
    supervisor._on_active_change = changes.append

    await supervisor.relinquish("lms")  # not current - ignored

    assert changes == []


@pytest.mark.asyncio
async def test_reacquiring_after_relinquish_works():
    """Nobody-holds-it is a state the system passes *through*, not a dead
    end: the user activates LMS again and it takes the device normally."""
    supervisor, adapters, holder = build(active="lms")
    await supervisor.relinquish("lms")
    assert supervisor.active is None

    await supervisor.acquire("lms")

    assert supervisor.active == "lms"
    assert adapters["lms"].device_freed_calls == 1


# --- Phase 4 criterion 4: handoff pair reporting ---------------------------


@pytest.mark.asyncio
async def test_handoff_reports_the_pair_at_both_edges():
    """The transition screen needs the pair, and needs a start and an end
    to appear and disappear on."""
    holder = {"who": None}
    adapters = {
        "lms": FakeAdapter("lms", ReleaseAction.PAUSE, holder),
        "spotify": FakeAdapter("spotify", ReleaseAction.DISCONNECT, holder),
        "bluetooth": FakeAdapter("bluetooth", ReleaseAction.DISCONNECT, holder),
    }
    seen: list[tuple[str | None, str | None]] = []
    supervisor = Supervisor(
        adapters,
        device_busy=lambda renderer_id: holder["who"] == renderer_id,
        ladder=FAST_LADDER,
        on_handoff_change=lambda f, t: seen.append((f, t)),
    )
    supervisor._active = "lms"
    holder["who"] = "lms"

    await supervisor.acquire("spotify")

    assert seen == [("lms", "spotify"), (None, None)]


@pytest.mark.asyncio
async def test_a_cold_acquisition_is_not_a_handoff():
    """Nobody holding the device is not a takeover - there is no pair, so
    nothing should be published for a transition screen to show."""
    supervisor, _, _ = build()
    seen: list[tuple[str | None, str | None]] = []
    supervisor._on_handoff_change = lambda f, t: seen.append((f, t))

    await supervisor.acquire("spotify")

    assert seen == []


@pytest.mark.asyncio
async def test_handoff_is_cleared_even_if_the_release_raises():
    """A transition screen stuck on forever because the ladder blew up
    would be exactly the unaccountable state ADR-0010 forbids."""
    holder = {"who": "lms"}

    class ExplodingLms(FakeAdapter):
        async def release(self):
            raise RuntimeError("boom")

    adapters = {
        "lms": ExplodingLms("lms", ReleaseAction.PAUSE, holder),
        "spotify": FakeAdapter("spotify", ReleaseAction.DISCONNECT, holder),
    }
    seen: list[tuple[str | None, str | None]] = []
    supervisor = Supervisor(
        adapters,
        device_busy=lambda renderer_id: holder["who"] == renderer_id,
        ladder=FAST_LADDER,
        on_handoff_change=lambda f, t: seen.append((f, t)),
    )
    supervisor._active = "lms"

    with pytest.raises(RuntimeError):
        await supervisor.acquire("spotify")

    assert seen == [("lms", "spotify"), (None, None)]


# ---------------------------------------------------------------------------
# ADR-0077: a source that is off does not take the device.
# ---------------------------------------------------------------------------


def _three(holder):
    return {
        "lms": FakeAdapter("lms", ReleaseAction.PAUSE, holder),
        "spotify": FakeAdapter("spotify", ReleaseAction.DISCONNECT, holder),
        "bluetooth": FakeAdapter("bluetooth", ReleaseAction.DISCONNECT, holder),
    }


@pytest.mark.asyncio
async def test_a_renderer_that_is_switched_off_does_not_acquire():
    """The whole point of the gate. An event from a renderer whose unit was
    just stopped - go-librespot's last `will_play`, say - must not take the
    device on its way out."""
    holder = {"who": None}
    supervisor = Supervisor(
        _three(holder),
        device_busy=lambda renderer_id: holder["who"] == renderer_id,
        ladder=FAST_LADDER,
        enabled=lambda renderer_id: renderer_id != "spotify",
    )

    await supervisor.acquire("spotify")
    assert supervisor.active is None


@pytest.mark.asyncio
async def test_a_renderer_that_is_off_cannot_displace_the_active_one():
    """Not just "it does not become active" - it must not release whoever
    holds the device either. A refused acquisition is not a takeover."""
    holder = {"who": "lms"}
    adapters = _three(holder)
    supervisor = Supervisor(
        adapters,
        device_busy=lambda renderer_id: holder["who"] == renderer_id,
        ladder=FAST_LADDER,
        enabled=lambda renderer_id: renderer_id != "bluetooth",
    )
    supervisor._active = "lms"  # ADR-0027: no implicit base, say so explicitly

    await supervisor.acquire("bluetooth")
    assert supervisor.active == "lms"
    assert adapters["lms"].release_calls == 0


@pytest.mark.asyncio
async def test_a_refused_acquisition_reports_no_handoff():
    """Phase 4 criterion 4's transition screen appears on the handoff edges.
    A renderer that is off never gets one, so nothing flashes on screen for a
    takeover that did not happen."""
    holder = {"who": None}
    edges = []
    supervisor = Supervisor(
        _three(holder),
        device_busy=lambda renderer_id: holder["who"] == renderer_id,
        ladder=FAST_LADDER,
        on_handoff_change=lambda a, b: edges.append((a, b)),
        on_active_change=lambda rid: edges.append(("active", rid)),
        enabled=lambda renderer_id: False,
    )

    await supervisor.acquire("lms")
    assert edges == []


@pytest.mark.asyncio
async def test_no_predicate_means_every_renderer_is_on():
    """Every caller before ADR-0077, and every other test in this file."""
    holder = {"who": None}
    supervisor = Supervisor(
        _three(holder),
        device_busy=lambda renderer_id: holder["who"] == renderer_id,
        ladder=FAST_LADDER,
    )

    await supervisor.acquire("spotify")
    assert supervisor.active == "spotify"


@pytest.mark.asyncio
async def test_an_unknown_renderer_still_raises_rather_than_being_refused():
    """The gate is checked after the membership test, so a typo in a renderer
    id stays a programming error rather than becoming a silent no-op."""
    holder = {"who": None}
    supervisor = Supervisor(
        _three(holder),
        device_busy=lambda renderer_id: holder["who"] == renderer_id,
        ladder=FAST_LADDER,
        enabled=lambda renderer_id: False,
    )

    with pytest.raises(ValueError):
        await supervisor.acquire("airplay")


@pytest.mark.asyncio
async def test_switching_off_the_active_renderer_leaves_nobody_holding_it():
    """**Found on the panel, 2026-09-25.** Turning Spotify off mid-track left
    it the active renderer forever: its watch is cancelled when the row goes
    off, so the `inactive` event that would have released the device never
    arrives and Now Playing went on showing its track. `_apply_renderer` says
    it instead - this is that call."""
    holder = {"who": "spotify"}
    supervisor = Supervisor(
        _three(holder),
        device_busy=lambda renderer_id: holder["who"] == renderer_id,
        ladder=FAST_LADDER,
        enabled=lambda renderer_id: renderer_id != "spotify",
    )
    supervisor._active = "spotify"

    # The row is already off by the time this is called, so the gate above
    # must not swallow it: `relinquish` is release, not acquisition.
    await supervisor.relinquish("spotify")
    assert supervisor.active is None


# --- ADR-0089: a renderer that arrives after construction --------------------


@pytest.mark.asyncio
async def test_a_plugin_renderer_can_be_registered_and_then_acquires():
    """**ADR-0089.** The supervisor's adapters used to be fixed at
    construction, and `acquire` raised `ValueError` for anything else - which
    is where a plugin renderer stopped being a renderer."""
    supervisor, _, holder = build()
    plexamp = FakeAdapter("plexamp", ReleaseAction.DISCONNECT, holder)

    with pytest.raises(ValueError):
        await supervisor.acquire("plexamp")

    supervisor.register(plexamp)
    await supervisor.acquire("plexamp")
    assert supervisor.active == "plexamp"


@pytest.mark.asyncio
async def test_a_duplicate_id_is_refused_not_replaced():
    """Replacing the adapter of a renderer that currently holds the device
    would leave the release ladder talking to a connection that never acquired
    anything."""
    supervisor, adapters, holder = build()
    with pytest.raises(ValueError):
        supervisor.register(FakeAdapter("lms", ReleaseAction.PAUSE, holder))
    assert supervisor._adapters["lms"] is adapters["lms"]


@pytest.mark.asyncio
async def test_a_plugin_that_goes_away_stops_being_active():
    """A renderer that is no longer here cannot be the active one. The change
    is published the way any other release is."""
    seen = []
    supervisor, _, holder = build()
    supervisor._on_active_change = lambda who: seen.append(who)
    supervisor.register(FakeAdapter("plexamp", ReleaseAction.DISCONNECT, holder))
    await supervisor.acquire("plexamp")
    seen.clear()

    supervisor.forget("plexamp")
    assert supervisor.active is None
    assert seen == [None]
    with pytest.raises(ValueError):
        await supervisor.acquire("plexamp")


@pytest.mark.asyncio
async def test_forgetting_a_renderer_that_is_not_active_leaves_the_active_one_alone():
    supervisor, _, holder = build(active="lms")
    supervisor.register(FakeAdapter("plexamp", ReleaseAction.DISCONNECT, holder))
    supervisor.forget("plexamp")
    assert supervisor.active == "lms"


@pytest.mark.asyncio
async def test_forgetting_something_that_was_never_registered_is_quiet():
    """A session refused during the handshake never registered, and the
    disconnect path must not care."""
    supervisor, _, _ = build(active="lms")
    supervisor.forget("never-here")
    assert supervisor.active == "lms"


@pytest.mark.asyncio
async def test_the_callers_adapter_dict_is_not_mutated():
    """`__main__` reads its own `adapters` elsewhere for the three built-ins'
    wiring; registering a plugin must not appear in it."""
    supervisor, adapters, holder = build()
    supervisor.register(FakeAdapter("plexamp", ReleaseAction.DISCONNECT, holder))
    assert set(adapters) == {"lms", "spotify", "bluetooth"}
