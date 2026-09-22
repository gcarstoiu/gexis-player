"""Unit tests for the volume bridge's echo suppression and per-renderer
memory attribution (criterion 5).

Regression coverage for a real ratchet-to-zero measured on hardware,
2026-09-06, and for the per-renderer-volume decision, 2026-09-07 (see
volume.py's module docstring for both). Only `_on_adapter_volume` is
exercised directly here - `run()`'s `alsactl monitor` side needs a real
subprocess and isn't covered by these tests; the shared
value-matched echo suppression and remember/apply logic is the same code path
either way.
"""
from __future__ import annotations

import asyncio
import time as time_module

import pytest

from gexis_core import volume as volume_module
from gexis_core.volume import (
    ECHO_WINDOW_S,
    VolumeBridge,
    db_to_raw,
    dummy_raw_to_hardware_raw,
    get_raw,
    hardware_raw_to_spotify_fraction,
    raw_to_db,
    spotify_fraction_to_hardware_raw,
)


class FakeSpotify:
    renderer_id = "spotify"

    def __init__(self):
        self._callback = None

    def on_volume_change(self, callback):
        self._callback = callback

    async def get_volume_steps(self):
        return 100

    async def set_volume(self, value):
        pass


class FakeVolumeMemory:
    def __init__(self):
        self.remembered: list[tuple[str, int]] = []

    def remember(self, renderer_id, raw):
        self.remembered.append((renderer_id, raw))

    def get(self, renderer_id):
        for rid, raw in reversed(self.remembered):
            if rid == renderer_id:
                return raw
        return None


async def settle():
    """Let a write finish. Since ADR-0052 §4 a level change is a *ramp* -
    `write_hardware` awaits an inner task - so one loop turn no longer
    drains it."""
    for _ in range(20):
        await asyncio.sleep(0)


@pytest.fixture(autouse=True)
def fake_set_raw(monkeypatch):
    calls = []

    async def fake(mixer_name, value):
        calls.append((mixer_name, value))

    monkeypatch.setattr(volume_module, "set_raw", fake)
    return calls


def make_bridge(active="spotify"):
    memory = FakeVolumeMemory()
    bridge = VolumeBridge(
        "DAC", FakeSpotify(), volume_memory=memory, get_active_renderer=lambda: active
    )
    return bridge, memory


@pytest.mark.asyncio
async def test_spotify_echo_of_our_own_value_is_ignored(fake_set_raw):
    """An echo carries back exactly what we pushed out - that, and only
    that, is what gets dropped."""
    bridge, _ = make_bridge()
    bridge._expected_adapter_value = (71, time_module.monotonic())

    bridge._on_adapter_volume(71, 100)
    await settle()

    assert fake_set_raw == []


@pytest.mark.asyncio
async def test_a_different_value_arriving_immediately_is_still_applied(fake_set_raw):
    """Blocker 4, found on hardware 2026-09-11: the old blanket time
    window dropped *everything* for 750ms after our own write, so a fast
    Spotify slider drag lost every value after the first - including the
    one the user let go on. Measured: a fast ramp to 100/100 left the DAC
    at 226/240, 7.0dB low, reproducibly, where the same ramp spaced 1.5s
    apart reached 240/240. A value we did not write is a genuine change,
    however fast it arrives."""
    bridge, _ = make_bridge()
    bridge._expected_adapter_value = (71, time_module.monotonic())

    bridge._on_adapter_volume(72, 100)  # one step away, immediately after
    await settle()

    assert fake_set_raw == [("DAC", spotify_fraction_to_hardware_raw(0.72))]


@pytest.mark.asyncio
async def test_fast_ramp_to_max_reaches_full_scale(fake_set_raw):
    """The drag that blocker 4 was reported as: every value lands, and the
    last one reaches 0dB (240/240), not somewhere short of it."""
    bridge, _ = make_bridge()

    for value in (40, 55, 70, 85, 100):
        bridge._on_adapter_volume(value, 100)
        await settle()

    # Since ADR-0052 §4 the hardware is *walked* between targets, so the
    # call list carries the steps in between as well. What blocker 4 was
    # about is unchanged and is what is asserted: **every target lands, in
    # order, and the last one is full scale** - not somewhere short of it.
    written = [raw for _, raw in fake_set_raw]
    targets = [spotify_fraction_to_hardware_raw(v / 100) for v in (40, 55, 70, 85, 100)]
    at = -1
    for target in targets:
        at = written.index(target, at + 1)  # raises if a target never landed
    assert fake_set_raw[-1] == ("DAC", 240)  # 100% is 0dB, full scale
    assert written == sorted(written)  # a ramp only ever moves one way here


@pytest.mark.asyncio
async def test_a_stale_expectation_does_not_suppress_a_genuine_change(fake_set_raw):
    """If our echo never arrives (dropped frame, a value that rounded
    differently coming back), the expectation must expire rather than
    silently swallow a later genuine change carrying the same number."""
    bridge, _ = make_bridge()
    bridge._expected_adapter_value = (50, time_module.monotonic() - ECHO_WINDOW_S - 1)

    bridge._on_adapter_volume(50, 100)
    await settle()

    assert fake_set_raw == [("DAC", 195)]


@pytest.mark.asyncio
async def test_genuine_spotify_change_outside_window_is_applied(fake_set_raw):
    bridge, memory = make_bridge()
    bridge._expected_adapter_value = None

    bridge._on_adapter_volume(50, 100)
    await settle()

    # dB-linear (spotify_fraction_to_hardware_raw), not raw-linear: 50%
    # is -22.5dB on the -45..0dB curve Spotify shares with LMS/Bluetooth
    # for consistency, not 50/100 * 240 = 120.
    assert fake_set_raw == [("DAC", 195)]
    assert memory.remembered == [("spotify", 195)]


@pytest.mark.asyncio
async def test_write_hardware_arms_the_echo_window(fake_set_raw):
    """Found on hardware, 2026-09-08: restore_volume (__main__.py) called
    set_raw() directly on every acquisition, bypassing the echo window -
    that write still shows up on alsactl monitor, so it got treated as a
    genuine external change and echoed straight back to Spotify via
    _on_adapter_volume's own path, racing go-librespot's own volume
    report. write_hardware() is what restore_volume and the unmanaged-
    renderer floor bump now call instead; this is the fix's core
    property: a write through it must not be mistaken for a fresh
    external change afterward."""
    bridge, _ = make_bridge()
    bridge._expected_hw_raw = None

    await bridge.write_hardware(120)

    assert fake_set_raw == [("DAC", 120)]
    # Recorded as *that* value, so the monitor line it produces is
    # recognised as our own - and nothing else is.
    assert bridge._consume(bridge._expected_hw_raw, 120)
    assert not bridge._consume(bridge._expected_hw_raw, 121)


@pytest.mark.asyncio
async def test_spotify_volume_while_inactive_is_remembered_not_applied(fake_set_raw):
    """Spotify isn't the active renderer - its own volume report must not
    move the mixer someone else currently owns, but should still be
    remembered for when it next becomes active."""
    bridge, memory = make_bridge(active="lms")
    bridge._expected_adapter_value = None

    bridge._on_adapter_volume(50, 100)
    await settle()

    assert fake_set_raw == []  # not applied to the live mixer
    assert memory.remembered == [("spotify", 195)]  # but remembered


def test_echo_window_is_positive_and_not_absurdly_long():
    # Sanity bound, not a precise spec - see module docstring on why this
    # is a mitigation rather than a proven-convergent design.
    assert 0 < ECHO_WINDOW_S < 5


class FakeProcess:
    def __init__(self, stdout: bytes):
        self._stdout = stdout

    async def communicate(self):
        return self._stdout, b""


class TestGetRawNegativeValues:
    """Regression coverage for a bug found on hardware, 2026-09-08: the
    dummy controls' own range is -50..100 (unlike the real DAC's 0..240),
    and the parsing regex's `\\d+` silently dropped the sign on every
    negative reading ("-50" parsed as 50) - a wrong value, not a parse
    failure, so `get_raw()` returning *something* didn't mean it returned
    the right thing. Affects roughly the bottom third of the dummy
    controls' range; invisible on the real DAC, which never goes
    negative."""

    @pytest.mark.asyncio
    async def test_negative_dummy_reading_parses_with_its_sign(self, monkeypatch):
        # Live-format capture, 2026-09-08: `amixer -D hw:gexislmsvol sget
        # Master` at LMS 0%.
        stdout = (
            b"Simple mixer control 'Master',0\n"
            b"  Capabilities: volume cswitch\n"
            b"  Playback channels: Front Left - Front Right\n"
            b"  Capture channels: Front Left - Front Right\n"
            b"  Limits: -50 - 100\n"
            b"  Front Left: -50 [0%] [-45.00dB] Capture [off]\n"
            b"  Front Right: -50 [0%] [-45.00dB] Capture [off]\n"
        )

        async def fake_exec(*args, **kwargs):
            return FakeProcess(stdout)

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

        assert await get_raw("Master", device="hw:gexislmsvol") == -50

    @pytest.mark.asyncio
    async def test_positive_reading_still_parses(self, monkeypatch):
        stdout = b"  Front Left: Playback 216 [90%] [-12.00dB]\n"

        async def fake_exec(*args, **kwargs):
            return FakeProcess(stdout)

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

        assert await get_raw("DAC") == 216


class TestDbConversion:
    """ADR-0018's documented scale: raw 0 = -120dB (mute), raw 240 =
    0dB, 0.5dB/step. Regression coverage for the finding that reasoning
    about this control in raw-step percentages is misleading - it's
    dB-linear per step, not perceptually linear (2026-09-08)."""

    def test_endpoints(self):
        assert raw_to_db(0) == -120.0
        assert raw_to_db(240) == 0.0

    def test_matches_measured_hardware_points(self):
        # 230/240 measured as -5dB, 60/240 as -90dB (HANDOFF.md,
        # 2026-09-07/08 hardware sessions).
        assert raw_to_db(230) == -5.0
        assert raw_to_db(60) == -90.0

    def test_round_trip(self):
        for raw in (0, 60, 120, 170, 230, 240):
            assert db_to_raw(raw_to_db(raw)) == raw

    def test_db_to_raw_clamps_to_hardware_range(self):
        assert db_to_raw(-200.0) == 0
        assert db_to_raw(50.0) == 240


class TestDummyRawToHardwareRaw:
    """B2, George's decision 2026-09-08: LMS and Bluetooth each write to
    a private snd-dummy control instead of the real DAC directly (see
    volume.py's module docstring and DummyMixerBridge). This is the
    translation between the dummy's own scale (-50..100 raw, -45..0dB,
    measured on hardware) and the real DAC's (0..240 raw, -120..0dB,
    ADR-0018) - a direct dB copy, clamped to the DAC's range.

    **Not** fractional-position rescaling, which is what this used to do
    until found wrong on hardware, 2026-09-08 (George: LMS silent below
    ~75%). Measured directly: squeezelite derives its percent-to-dB curve
    from the *target control's own declared TLV range*, so pointed at the
    dummy (-45dB span) it produces a much gentler curve than it would
    against the DAC directly (-120dB span) - rescaling by fractional
    position undid that gentleness by re-stretching the curve back across
    the DAC's full range, recreating the exact "everything crammed into
    the last quarter" compression the dummy's narrower range had
    incidentally fixed. See dummy_raw_to_hardware_raw's own docstring."""

    def test_endpoint_dont_reach_true_mute(self):
        # The dummy's floor (-45dB) is the quietest LMS/Bluetooth can
        # reach via this path - short of the DAC's true mute (-120dB),
        # accepted: silence is pause/mute's job, not the volume slider's.
        assert dummy_raw_to_hardware_raw(-50) == 150  # -45dB
        assert dummy_raw_to_hardware_raw(100) == 240  # 0dB, unattenuated

    def test_dont_rescale_by_fractional_position(self):
        # Dummy raw 25 is -22.5dB ((-45 + 75*0.30)). A direct copy lands
        # the DAC at the *same* -22.5dB (raw 195) - not at 50% of the
        # DAC's own -120..0dB span (which the old, wrong formula computed
        # as -60dB / raw 120).
        assert dummy_raw_to_hardware_raw(25) == 195

    def test_measured_hardware_point(self):
        # Live reading, 2026-09-08: dummy raw 59 measured as -12.30dB.
        # Copied directly: raw 215 on the DAC (-12.5dB, nearest 0.5dB step).
        assert dummy_raw_to_hardware_raw(59) == 215

    def test_measured_lms_percent_curve_stays_audible_below_75_percent(self):
        # Regression coverage for the actual reported symptom: LMS set to
        # 25/50/75% via its own RPC measured as dummy raw -23/18/59
        # (2026-09-08, live). None of these should land near the DAC's
        # silent end.
        assert dummy_raw_to_hardware_raw(-23) == 166  # LMS ~25%, -36.9dB
        assert dummy_raw_to_hardware_raw(18) == 191  # LMS ~50%, -24.6dB
        assert dummy_raw_to_hardware_raw(59) == 215  # LMS ~75%, -12.3dB


class TestSpotifyFractionToHardwareRaw:
    """Regression coverage for a bug found on hardware, 2026-09-08 - same
    day, same shape as LMS's own curve bug (TestDummyRawToHardwareRaw),
    just never touched by that fix: `_on_adapter_volume` mapped Spotify's
    value/max_ fraction *linearly in raw steps* onto the DAC's full
    0..240 - raw steps are dB-linear, not perceptually linear, so this
    compressed nearly all perceived loudness change into the last
    quarter of the slider. George: "60% volume there is no sound." Fixed
    the same way LMS was: dB-linear across a reasonable span (-45..0dB,
    matching LMS's own effective curve for consistency), not raw-linear
    across the DAC's full 120dB."""

    def test_endpoints(self):
        assert spotify_fraction_to_hardware_raw(0.0) == 150  # -45dB
        assert spotify_fraction_to_hardware_raw(1.0) == 240  # 0dB

    def test_reported_symptom_60_percent_is_now_audible(self):
        # Old (raw-linear) formula: round(0.6 * 240) = 144 -> -108dB.
        # New (dB-linear): -45 + 0.6*45 = -18dB -> raw 204.
        assert spotify_fraction_to_hardware_raw(0.6) == 204

    def test_round_trip_recovers_the_original_fraction(self):
        # Within 1 percentage point, not exact - the DAC's 0.5dB raw
        # steps quantise both directions, so a round trip can land one
        # step off (e.g. 25% -> raw 172 -> 24.4%, not a bug).
        for pct in (0, 25, 50, 60, 75, 90, 100):
            frac = pct / 100
            raw = spotify_fraction_to_hardware_raw(frac)
            recovered = hardware_raw_to_spotify_fraction(raw) * 100
            assert abs(recovered - pct) <= 1

    def test_hardware_raw_below_the_curves_floor_clamps_to_zero(self):
        # Reachable from LMS/Bluetooth's own lower range, or a manual
        # amixer write - not a fraction Spotify's own slider can express
        # a negative version of.
        assert hardware_raw_to_spotify_fraction(0) == 0.0


def _async_return(value):
    async def _get(*args, **kwargs):
        return value

    return _get


def _record(sink):
    async def _set(control, raw):
        sink.append((control, raw))

    return _set


class TestDummyMixerBridgePauseFadeGate:
    """George, 2026-09-17: LMS fades the player out when it pauses, by
    sending volume steps that squeezelite applies to the dummy control this
    bridge watches - measured 22 -> 7 -> -6 -> -20 -> -50 in ~150 ms.
    Mirrored, the DAC went to its -45dB floor, the panel published 0%, and
    the faded level was remembered as LMS's own.

    The decision waits for the control to settle, because the transport is
    only right by then: measured on hardware, LMS fades *before* it reports
    the pause, and that report reaches the core 0.51 s later. Deciding per
    step read "playing" and mirrored the whole fade."""

    @staticmethod
    def _bridge(monkeypatch, *, playing, active="lms", settled_raw=22):
        writes = []
        remembered = []
        monkeypatch.setattr(volume_module, "SETTLE_S", 0)
        monkeypatch.setattr(volume_module, "get_raw", _async_return(settled_raw))
        monkeypatch.setattr(volume_module, "set_raw", _record(writes))

        class Memory:
            def remember(self, renderer_id, raw):
                remembered.append((renderer_id, raw))

        bridge = volume_module.DummyMixerBridge(
            "lms",
            "gexislmsvol",
            "Master",
            "DAC",
            volume_memory=Memory(),
            get_active_renderer=lambda: active,
            is_playing=playing,
        )
        return bridge, writes, remembered

    @staticmethod
    async def _steps(bridge, *raws):
        """Feed control steps, then let the settle task run."""
        for raw in raws:
            await bridge._on_dummy_change(raw)
        if bridge._settling is not None:
            await bridge._settling

    @pytest.mark.asyncio
    async def test_a_pause_fade_is_not_mirrored_or_remembered(self, monkeypatch):
        """The measured fade. By the time it settles, the pause has been
        reported, which is the whole point of settling."""
        bridge, writes, remembered = self._bridge(
            monkeypatch, playing=lambda: False, settled_raw=-50
        )

        await self._steps(bridge, 7, -6, -20, -50)

        assert writes == []
        assert remembered == []

    @pytest.mark.asyncio
    async def test_a_volume_change_while_playing_is_mirrored_once(self, monkeypatch):
        """A drag sends many steps; one decision comes out of it."""
        bridge, writes, remembered = self._bridge(
            monkeypatch, playing=lambda: True, settled_raw=59
        )

        await self._steps(bridge, 30, 45, 59)

        assert writes == [("DAC", 215)]  # -12.3dB, the measured 75% point
        assert remembered == [("lms", 215)]

    @pytest.mark.asyncio
    async def test_a_late_transport_report_is_what_decides(self, monkeypatch):
        """The transport can still say "playing" while the fade arrives; the
        settled decision reads it after the report lands."""
        playing = True
        bridge, writes, _ = self._bridge(
            monkeypatch, playing=lambda: playing, settled_raw=-50
        )
        for raw in (7, -6, -20, -50):
            await bridge._on_dummy_change(raw)
        playing = False  # the pause report lands 0.51 s later (measured)

        await bridge._settling

        assert writes == []

    @pytest.mark.asyncio
    async def test_a_renderer_without_a_gate_never_ends_on_a_stale_level(self, monkeypatch):
        """Bluetooth's volume does not fade, and its AVRCP updates during a
        drag must not be swallowed (see DummyMixerBridge).

        **Since ADR-0052 §5 "not swallowed" means the latest value always
        lands, not that every step is written.** The mirror writes at most
        once per 40 ms and keeps the newest of whatever arrived in between -
        a finger never produces that rate, and a bluealsa meltdown produced
        750 changes a second (Finding 045 §10), every one of which used to
        become a 16 ms hardware write. What the old contract protected
        against was a *stale* level, and that is asserted here.
        """
        bridge, writes, _ = self._bridge(monkeypatch, playing=None)

        await self._steps(bridge, -50, 0, 50)
        if bridge._mirror_soon is not None:
            await bridge._mirror_soon

        # dummy -50/0/50 are -45/-30/-15dB (dummy_raw_to_db), i.e. 150/180/210.
        assert writes[0] == ("DAC", 150)  # the first is immediate
        assert writes[-1] == ("DAC", 210)  # and the last value is where it ends
        assert len(writes) <= 3

    @pytest.mark.asyncio
    async def test_a_storm_of_changes_becomes_a_handful_of_writes(self, monkeypatch):
        """Finding 045 §10, in a test: bluealsa wrote the dummy ~750 times a
        second while it melted down. The mirror must not turn that into 750
        hardware writes - and must still end on the last value."""
        bridge, writes, _ = self._bridge(monkeypatch, playing=None)

        await self._steps(bridge, *range(-50, 50))
        if bridge._mirror_soon is not None:
            await bridge._mirror_soon

        assert len(writes) <= 3, writes
        assert writes[-1][1] == dummy_raw_to_hardware_raw(49)

    @pytest.mark.asyncio
    async def test_an_inactive_renderer_is_remembered_but_not_applied(self, monkeypatch):
        bridge, writes, remembered = self._bridge(
            monkeypatch, playing=lambda: True, settled_raw=59, active="spotify"
        )

        await self._steps(bridge, 59)

        assert writes == []
        assert remembered == [("lms", 215)]

    @pytest.mark.asyncio
    async def test_the_resume_fade_restores_nothing_the_pause_took_away(self, monkeypatch):
        """Both halves are ignored, so the DAC never moves for a pause: the
        asymmetry - mirroring one half - is what left it at -45dB on
        hardware, 2026-09-17."""
        playing = False
        bridge, writes, _ = self._bridge(
            monkeypatch, playing=lambda: playing, settled_raw=-50
        )
        await self._steps(bridge, 7, -50)
        assert writes == []

        monkeypatch.setattr(volume_module, "get_raw", _async_return(22))
        playing = True
        await self._steps(bridge, -20, 0, 22)

        # Mirrored, but to the level the control already had before the
        # fade - so nothing audible changed across the pause.
        assert writes == [("DAC", 193)]
