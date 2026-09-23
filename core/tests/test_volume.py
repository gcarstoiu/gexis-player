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
    DUMMY_MAX_RAW,
    DUMMY_MIN_RAW,
    ECHO_WINDOW_S,
    VolumeBridge,
    db_to_raw,
    dummy_raw_to_hardware_raw,
    get_raw,
    hardware_raw_to_renderer_value,
    hardware_raw_to_spotify_fraction,
    raw_to_db,
    raw_to_slider_percent,
    renderer_percent_to_value,
    renderer_value_to_hardware_raw,
    renderer_value_to_percent,
    slider_percent_to_raw,
    spotify_fraction_to_hardware_raw,
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


def make_reporting_bridge(active="spotify"):
    """**Since ADR-0054 §3 this class no longer writes the DAC for a
    renderer's report.** There is one path from a renderer's number to the
    hardware - `__main__`'s `report_renderer_volume`, which applies the one
    curve - and this class's job on that side is to decide *which* reports
    are genuine. So these tests assert on what it passes on."""
    memory = FakeVolumeMemory()
    reported: list[tuple[str, int, int]] = []
    bridge = VolumeBridge(
        "DAC",
        FakeSpotify(),
        volume_memory=memory,
        get_active_renderer=lambda: active,
        on_renderer_value=lambda rid, value, steps: reported.append((rid, value, steps)),
    )
    return bridge, reported


@pytest.mark.asyncio
async def test_spotify_echo_of_our_own_value_is_ignored(fake_set_raw):
    """An echo carries back exactly what we pushed out - that, and only
    that, is what gets dropped."""
    bridge, reported = make_reporting_bridge()
    bridge._expected_adapter_value = (71, time_module.monotonic())

    bridge._on_adapter_volume(71, 100)
    await settle()

    assert fake_set_raw == []
    # Reported all the same: the *number* is true whoever caused it, and
    # ADR-0053's panel shows it. What the echo suppresses is the level
    # being pushed back out, not the level being known.
    assert reported == [("spotify", 71, 100)]


@pytest.mark.asyncio
async def test_a_different_value_arriving_immediately_is_still_applied(fake_set_raw):
    """Blocker 4, found on hardware 2026-09-11: the old blanket time
    window dropped *everything* for 750ms after our own write, so a fast
    Spotify slider drag lost every value after the first - including the
    one the user let go on. Measured: a fast ramp to 100/100 left the DAC
    at 226/240, 7.0dB low, reproducibly, where the same ramp spaced 1.5s
    apart reached 240/240. A value we did not write is a genuine change,
    however fast it arrives."""
    bridge, reported = make_reporting_bridge()
    bridge._expected_adapter_value = (71, time_module.monotonic())

    bridge._on_adapter_volume(72, 100)  # one step away, immediately after
    await settle()

    assert reported == [("spotify", 72, 100)]
    assert bridge._expected_adapter_value is not None  # not consumed by a non-echo


@pytest.mark.asyncio
async def test_fast_ramp_to_max_reaches_full_scale(fake_set_raw):
    """The drag that blocker 4 was reported as: every value lands, and the
    last one reaches 0dB (240/240), not somewhere short of it."""
    bridge, reported = make_reporting_bridge()

    for value in (40, 55, 70, 85, 100):
        bridge._on_adapter_volume(value, 100)
        await settle()

    # **Every value lands, in order, and the last one is the maximum** -
    # which is what blocker 4 was about. Where it goes from here is
    # ADR-0054 §3's single curve, and 100 of 100 is 0 dB on it.
    assert [value for _, value, _ in reported] == [40, 55, 70, 85, 100]
    assert renderer_value_to_hardware_raw(100, 100) == 240


@pytest.mark.asyncio
async def test_a_stale_expectation_does_not_suppress_a_genuine_change(fake_set_raw):
    """If our echo never arrives (dropped frame, a value that rounded
    differently coming back), the expectation must expire rather than
    silently swallow a later genuine change carrying the same number."""
    bridge, reported = make_reporting_bridge()
    bridge._expected_adapter_value = (50, time_module.monotonic() - ECHO_WINDOW_S - 1)

    bridge._on_adapter_volume(50, 100)
    await settle()

    assert reported == [("spotify", 50, 100)]


@pytest.mark.asyncio
async def test_genuine_spotify_change_outside_window_is_applied(fake_set_raw):
    bridge, reported = make_reporting_bridge()
    bridge._expected_adapter_value = None

    bridge._on_adapter_volume(50, 100)
    await settle()

    assert reported == [("spotify", 50, 100)]
    # And where that goes: 50 of 100 is -15.5 dB on ADR-0054 §3's curve -
    # not raw-linear's 50/100 * 240 = 120, which was -60 dB and the
    # 2026-09-08 symptom.
    assert renderer_value_to_hardware_raw(50, 100) == 209


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
async def test_spotify_volume_while_inactive_is_reported_but_never_written(fake_set_raw):
    """Spotify isn't the active renderer - its own volume report must not
    move the mixer someone else currently owns.

    **Since ADR-0054 §3 that decision is not made here.** This class writes
    the DAC for nobody's report; it passes the number on, and
    `report_renderer_volume` decides whether the renderer holds the device
    and remembers it either way. What is asserted here is the half that is
    still this class's: nothing reaches the hardware."""
    bridge, reported = make_reporting_bridge(active="lms")
    bridge._expected_adapter_value = None

    bridge._on_adapter_volume(50, 100)
    await settle()

    assert fake_set_raw == []
    assert reported == [("spotify", 50, 100)]


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

    def test_the_endpoints_reach_zero_but_not_true_mute(self):
        # **The top reaches 0 dB and the floor does not reach silence.**
        # Since the range became 0..127 (to match AVRCP exactly) the
        # control's own scale tops out at -6.90 dB, and the 6.9 is taken
        # back by the shift - so the renderer's window is -38.1..0 dB.
        # Measured on the device, 2026-09-22: LMS at 100% lands the DAC at
        # 0.00 dB and at 10% on -38.00.
        assert dummy_raw_to_hardware_raw(0) == 164  # -38.1dB, the floor
        assert dummy_raw_to_hardware_raw(127) == 240  # 0dB, unattenuated

    def test_dont_rescale_by_fractional_position(self):
        # Dummy raw 64 is -19.05 dB on the shifted window. A direct copy
        # lands the DAC at the *same* dB - not at half of the DAC's own
        # -120..0 span, which is what the old, wrong formula computed.
        assert dummy_raw_to_hardware_raw(64) == db_to_raw(-38.1 + 64 * 0.30)
        assert dummy_raw_to_hardware_raw(64) != 120  # the fractional answer

    def test_measured_lms_percent_curve(self):
        # Live, 2026-09-22, LMS set by its own RPC with the new range:
        # 25/50/75/100% measured as dummy raw 27/68/109/127.
        assert dummy_raw_to_hardware_raw(27) == 180  # LMS 25%, -30.0dB
        assert dummy_raw_to_hardware_raw(68) == 205  # LMS 50%, -17.5dB
        assert dummy_raw_to_hardware_raw(109) == 229  # LMS 75%, -5.5dB
        assert dummy_raw_to_hardware_raw(127) == 240  # LMS 100%, 0dB

    def test_the_range_is_avrcps_own(self):
        """128 values against AVRCP's 128, so a Bluetooth volume that goes
        out and comes back lands where it started - the drift that drove
        the ratchet (Finding 045 §12) cannot happen."""
        assert DUMMY_MAX_RAW - DUMMY_MIN_RAW + 1 == 128


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
        """**Zero is silence since ADR-0054 §3**, not -45 dB. It was -45
        because the 2026-09-08 fix gave Spotify "a reasonable span" rather
        than a floor, and George found the floor audible on 2026-09-23."""
        assert spotify_fraction_to_hardware_raw(0.0) == 0  # silence
        assert spotify_fraction_to_hardware_raw(1.0) == 240  # 0dB

    def test_reported_symptom_60_percent_is_now_audible(self):
        # Old (raw-linear) formula: round(0.6 * 240) = 144 -> -108dB, the
        # 2026-09-08 symptom. On ADR-0054's cubic taper 60% is -11.5 dB.
        assert spotify_fraction_to_hardware_raw(0.6) == 217

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
        """**Since ADR-0054 §2 this bridge reports an event, not a level.**

        The control's value is squeezelite's curve of LMS's number - LMS 25
        lands on 27, and LMS 10 and LMS 0 both land on 0 (Finding 046 §1) -
        so it could never say what LMS says. It says *when*, in 0.1 ms, and
        the daemon then asks LMS. So `moved` below is what used to be
        `writes`, and the gate's contract is unchanged: a pause fade
        produces no event at all.
        """
        moved = []
        remembered = []
        monkeypatch.setattr(volume_module, "SETTLE_S", 0)
        monkeypatch.setattr(volume_module, "get_raw", _async_return(settled_raw))

        class Memory:
            def remember(self, renderer_id, raw):
                remembered.append((renderer_id, raw))

        async def on_moved(renderer_id):
            moved.append(renderer_id)

        bridge = volume_module.DummyMixerBridge(
            "lms",
            "gexislmsvol",
            "Master",
            "DAC",
            volume_memory=Memory(),
            get_active_renderer=lambda: active,
            is_playing=playing,
            on_moved=on_moved,
        )
        return bridge, moved, remembered

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
        bridge, moved, remembered = self._bridge(
            monkeypatch, playing=lambda: False, settled_raw=DUMMY_MIN_RAW
        )

        await self._steps(bridge, 109, 82, 41, DUMMY_MIN_RAW)

        assert moved == []
        assert remembered == []

    @pytest.mark.asyncio
    async def test_a_volume_change_while_playing_is_mirrored_once(self, monkeypatch):
        """A drag sends many steps; one decision comes out of it."""
        bridge, moved, remembered = self._bridge(
            monkeypatch, playing=lambda: True, settled_raw=109
        )

        await self._steps(bridge, 80, 95, 109)

        assert moved == ["lms"]  # one event, whatever the control did
        # Remembering moved to `report_renderer_volume` with the curve
        # (ADR-0054 §3), because it is the renderer's *number* that is
        # worth remembering, not squeezelite's rendering of it.
        assert remembered == []

    @pytest.mark.asyncio
    async def test_a_late_transport_report_is_what_decides(self, monkeypatch):
        """The transport can still say "playing" while the fade arrives; the
        settled decision reads it after the report lands."""
        playing = True
        bridge, moved, _ = self._bridge(
            monkeypatch, playing=lambda: playing, settled_raw=DUMMY_MIN_RAW
        )
        for raw in (109, 82, 41, DUMMY_MIN_RAW):
            await bridge._on_dummy_change(raw)
        playing = False  # the pause report lands 0.51 s later (measured)

        await bridge._settling

        assert moved == []

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
        bridge, moved, _ = self._bridge(monkeypatch, playing=None)

        await self._steps(bridge, 0, 64, 127)
        if bridge._mirror_soon is not None:
            await bridge._mirror_soon

        # An event, not a level - the daemon reads the number afterwards, so
        # what matters is that a change never passes unnoticed and that a
        # burst does not become a burst of reads.
        assert moved
        assert len(moved) <= 3

    @pytest.mark.asyncio
    async def test_a_storm_of_changes_becomes_a_handful_of_writes(self, monkeypatch):
        """Finding 045 §10, in a test: bluealsa wrote the dummy ~750 times a
        second while it melted down. The mirror must not turn that into 750
        hardware writes - and must still end on the last value."""
        bridge, moved, _ = self._bridge(monkeypatch, playing=None)

        await self._steps(bridge, *range(0, 100))
        if bridge._mirror_soon is not None:
            await bridge._mirror_soon

        assert len(moved) <= 3, moved

    @pytest.mark.asyncio
    async def test_an_inactive_renderer_is_remembered_but_not_applied(self, monkeypatch):
        bridge, moved, _ = self._bridge(
            monkeypatch, playing=lambda: True, settled_raw=109, active="spotify"
        )

        await self._steps(bridge, 109)

        # Nothing to read and nothing to apply: a control that moved under
        # an inactive renderer is not this device's volume.
        assert moved == []

    @pytest.mark.asyncio
    async def test_the_resume_fade_restores_nothing_the_pause_took_away(self, monkeypatch):
        """Both halves are ignored, so the DAC never moves for a pause: the
        asymmetry - mirroring one half - is what left it at -45dB on
        hardware, 2026-09-17."""
        playing = False
        bridge, moved, _ = self._bridge(
            monkeypatch, playing=lambda: playing, settled_raw=DUMMY_MIN_RAW
        )
        await self._steps(bridge, 64, DUMMY_MIN_RAW)
        assert moved == []

        monkeypatch.setattr(volume_module, "get_raw", _async_return(109))
        playing = True
        await self._steps(bridge, 27, 68, 109)

        # One event on the resume, and the number it leads to is the one
        # LMS has now - which is the one it had before the fade, so nothing
        # audible changed across the pause.
        assert moved == ["lms"]


@pytest.mark.asyncio
async def test_a_ramps_own_steps_are_not_read_back_as_someone_turning_the_knob(fake_set_raw):
    """George, 2026-09-22: the volume drawer stayed on screen with nothing
    playing and nobody touching it.

    `alsactl monitor` reports every write, and the echo window matched only
    the *target* - so each of a ramp's dozen intermediate values looked like
    an external change, republished the level, and reset the drawer's
    auto-hide. Every value we write is ours."""
    bridge, _ = make_bridge()
    bridge._last_written = 120

    await bridge.write_hardware(160)

    written = [raw for _, raw in fake_set_raw]
    assert len(written) > 3, "this move should have ramped"
    for raw in written:
        assert bridge._was_ours(raw), f"{raw} would read back as an external change"


class TestTheCeilingIsTheTopOfEveryScale:
    """ADR-0052 §3 as amended, 2026-09-22.

    The first version clamped the hardware and told nobody: every control
    still displayed the number the renderer asked for, and the first move of
    any slider released the difference. George: *"We are taking away the
    decision from the user and creating what looks like an error because the
    sound jumps up or down with the first move of the volume."*

    So the ceiling is now where the top of each scale *sits*. What these
    pin is that claim, in the three places a position becomes a level.
    """

    @pytest.fixture(autouse=True)
    def _no_ceiling_afterwards(self):
        yield
        volume_module.set_ceiling_reader(lambda: None)

    @staticmethod
    def _at(db):
        volume_module.set_ceiling_reader(lambda: db)

    def test_unset_is_the_dac_s_own_maximum(self):
        assert volume_module.ceiling_db() == 0.0
        assert slider_percent_to_raw(100) == db_to_raw(0.0)
        assert dummy_raw_to_hardware_raw(DUMMY_MAX_RAW) == db_to_raw(0.0)
        assert spotify_fraction_to_hardware_raw(1.0) == db_to_raw(0.0)

    def test_every_scale_tops_out_at_the_ceiling(self):
        """One level, three controls, and none of them can ask for more."""
        self._at(-10.0)

        assert slider_percent_to_raw(100) == db_to_raw(-10.0)
        assert dummy_raw_to_hardware_raw(DUMMY_MAX_RAW) == db_to_raw(-10.0)
        assert spotify_fraction_to_hardware_raw(1.0) == db_to_raw(-10.0)

    def test_the_panel_never_reads_louder_than_what_comes_out(self):
        """The inverse has to move with the map, or the number lies in the
        other direction - which is the whole complaint."""
        self._at(-10.0)

        assert raw_to_slider_percent(db_to_raw(-10.0)) == 100
        assert hardware_raw_to_spotify_fraction(db_to_raw(-10.0)) == 1.0
        # Within a point, which is the DAC's own resolution and not the
        # ceiling's doing: 100 slider positions of 0.45 dB onto 0.5 dB raw
        # steps never round-trips exactly, with or without a ceiling.
        for percent in (0, 1, 25, 50, 75, 99, 100):
            assert abs(raw_to_slider_percent(slider_percent_to_raw(percent)) - percent) <= 1

    def test_a_step_keeps_its_size(self):
        """A shift, not a compression (ADR-0052's amendment §3). If the
        ceiling squeezed the window instead, a dummy step would shrink with
        the setting - the dummy's 128 values would stop landing on distinct
        DAC steps, and the gentle renderer curve recovered on 2026-09-08
        would be re-stretched."""
        def spans():
            return [
                dummy_raw_to_hardware_raw(raw + 1) - dummy_raw_to_hardware_raw(raw)
                for raw in range(DUMMY_MIN_RAW, DUMMY_MAX_RAW)
            ]

        loose = spans()
        self._at(-12.0)
        assert spans() == loose

    def test_the_whole_window_moves_down_together(self):
        """Not just the top: the same sound is the same position on the
        slider only if the floor moves too."""
        self._at(-12.0)

        assert raw_to_db(slider_percent_to_raw(100)) == pytest.approx(-12.0, abs=0.5)
        assert raw_to_db(slider_percent_to_raw(50)) == pytest.approx(-27.5, abs=0.5)
        assert raw_to_db(renderer_value_to_hardware_raw(1, 100)) == pytest.approx(
            -70.0, abs=0.5
        )

    def test_a_ceiling_above_zero_is_not_one(self):
        """A row can hold anything. Nothing may make the device louder than
        the DAC's own maximum."""
        self._at(6.0)
        assert volume_module.ceiling_db() == 0.0

    def test_an_unreadable_row_fails_open(self):
        """Open is a loud device and closed is a silent one; a setting that
        cannot be read must not mute the player."""
        def boom():
            raise RuntimeError("no settings store yet")

        volume_module.set_ceiling_reader(boom)
        assert volume_module.ceiling_db() == 0.0

        volume_module.set_ceiling_reader(lambda: "not a number")
        assert volume_module.ceiling_db() == 0.0


class TestTheRemoteRoundTripDoesNotRatchet:
    """ADR-0053's precondition, written before the model was built.

    This makes a *second* two-way volume sync, and the first one ratcheted:
    AVRCP's 128 values against the dummy's 151 meant a value went out and a
    different one came back, every drift was a fresh change, and bluealsa
    died retrying the push (Finding 045 §12). The same shape is available
    here, so it is pinned before anything can grow into it.
    """

    SCALES = {
        "lms": 100,
        "spotify": 100,
        "spotify-fallback": 65535,
        "bluetooth": 127,
    }

    def test_a_panel_position_survives_the_trip_to_every_renderer(self):
        """Drag to 37 and 37 comes back, on all three scales. This is the
        direction the model actually uses."""
        for name, steps in self.SCALES.items():
            for percent in range(101):
                value = renderer_percent_to_value(percent, steps)
                assert renderer_value_to_percent(value, steps) == percent, (
                    f"{name}: {percent}% -> {value} -> "
                    f"{renderer_value_to_percent(value, steps)}%"
                )

    def test_a_renderers_own_value_does_not_survive_being_sent_back(self):
        """**The reason for the invariant, asserted rather than assumed.**

        101 positions cannot name 128 values, so a phone's level shown as a
        percentage and pushed back out lands somewhere else for 27 of them -
        raw 101 shows as 80%, and 80% sends 102. Nothing in the daemon may
        ever close that loop; the panel's number is a view of what the
        renderer reported, and only a panel-originated change goes outward.
        """
        steps = self.SCALES["bluetooth"]
        drifting = [
            value
            for value in range(steps + 1)
            if renderer_percent_to_value(renderer_value_to_percent(value, steps), steps)
            != value
        ]

        assert len(drifting) == 27
        assert 101 in drifting
        assert renderer_value_to_percent(101, steps) == 80
        assert renderer_percent_to_value(80, steps) == 102

    def test_the_scales_that_are_the_panels_own_are_safe_in_both_directions(self):
        """LMS and Spotify are 0-100, the panel's own, so for them the loop
        would be harmless. The invariant still holds for all three, because
        a rule that is true of two renderers out of three is not a rule."""
        for steps in (100,):
            for value in range(steps + 1):
                assert renderer_percent_to_value(
                    renderer_value_to_percent(value, steps), steps
                ) == value

    def test_out_of_range_input_cannot_move_a_renderer_off_its_own_scale(self):
        for steps in self.SCALES.values():
            assert renderer_percent_to_value(-5, steps) == 0
            assert renderer_percent_to_value(140, steps) == steps
        assert renderer_value_to_percent(200, 127) == 100
        assert renderer_value_to_percent(-3, 127) == 0

    def test_a_renderer_that_reports_no_scale_reads_as_zero_not_as_a_crash(self):
        assert renderer_value_to_percent(50, 0) == 0


class TestTheOneCurve:
    """ADR-0054 §3. Until 2026-09-23 nobody's volume curve was ours:
    squeezelite derived its own from the dummy control's declared range,
    bluealsa applied its AVRCP curve, and we copied whatever dB came out.

    George's two findings, measured (Finding 047 §3): *"Even with volume at
    0 on any renderer there is still sound coming. Faint but still there"* —
    a renderer's zero was **−38 dB** — and *"below 40 the sound is really
    dim already. Feels almost like nothing is changing"* — LMS's 0%, 5% and
    10% were one value and 0–20% spanned one decibel.
    """

    @pytest.fixture(autouse=True)
    def _no_ceiling(self):
        yield
        volume_module.set_ceiling_reader(lambda: None)

    def test_zero_is_silence_on_every_scale(self):
        """The one that was accepted as a trade in 2026-09-08 and reversed
        on use: *"dead silence is what pause/mute are for, not the bottom of
        a renderer's own volume slider."*"""
        for steps in (100, 127, 1000):
            assert renderer_value_to_hardware_raw(0, steps) == 0

    def test_maximum_is_the_ceiling(self):
        assert renderer_value_to_hardware_raw(100, 100) == 240  # 0 dB
        assert renderer_value_to_hardware_raw(127, 127) == 240
        volume_module.set_ceiling_reader(lambda: -10.0)
        assert raw_to_db(renderer_value_to_hardware_raw(100, 100)) == -10.0

    def test_the_span_is_sixty_decibels(self):
        """librespot's `softvol` default, and what George found works on the
        same DAC (Finding 047 §5). It was 38.1 dB, and 45 before that."""
        assert volume_module.RENDERER_DB_SPAN == 60.0

    def test_the_taper_is_cubic_so_the_bottom_half_is_usable(self):
        """George, 2026-09-23: *"The bottom half of the volume range is
        quite quiet."* Linear in dB spent half its decibels on the bottom
        half of the slider - half travel was **-30 dB**, a twentieth of the
        loudness at the top.

        Cubic is how a volume control is normally tapered. Half travel is
        now -15.5 dB and a quarter -29.5, and the bottom still reaches
        -58 dB before the cliff to silence.
        """
        assert raw_to_db(renderer_value_to_hardware_raw(75, 100)) == -6.5
        assert raw_to_db(renderer_value_to_hardware_raw(50, 100)) == -15.5
        assert raw_to_db(renderer_value_to_hardware_raw(25, 100)) == -29.5
        assert raw_to_db(renderer_value_to_hardware_raw(1, 100)) == -58.0

    def test_a_wider_span_would_have_made_the_bottom_quieter_not_louder(self):
        """Pinned because it is the thing that is easy to get backwards, and
        was: the change asked for was *"60db might not be enough... let's
        increase it"*, and increasing it moves the bottom down."""
        at_sixty = raw_to_db(renderer_value_to_hardware_raw(50, 100))
        volume_module.RENDERER_DB_SPAN = 80.0
        try:
            at_eighty = raw_to_db(renderer_value_to_hardware_raw(50, 100))
        finally:
            volume_module.RENDERER_DB_SPAN = 60.0
        assert at_eighty < at_sixty

    def test_the_bottom_of_travel_actually_moves(self):
        """The direct answer to *"feels almost like nothing is changing"*.
        Every step below 40% is a distinct hardware level, where LMS's
        0/5/10 used to be one."""
        levels = [renderer_value_to_hardware_raw(v, 100) for v in range(1, 41)]
        assert len(set(levels)) == len(levels)
        assert raw_to_db(levels[0]) == pytest.approx(-58.0, abs=0.1)
        assert raw_to_db(levels[-1]) == pytest.approx(-20.0, abs=0.1)

    def test_the_cost_of_the_taper_is_at_the_top_and_is_inaudible(self):
        """**Stated rather than hidden**: above about 44% the curve is finer
        than the DAC's 0.5 dB steps, so 101 positions land on 81 levels and
        some pairs of percentages sound identical.

        That is the same shape of complaint moved elsewhere, and it is
        accepted because the pairs are 0.23 dB apart - inaudible - where the
        bottom-end collapse it replaces was ten positions on one value
        across a usable range."""
        levels = [renderer_value_to_hardware_raw(v, 100) for v in range(101)]
        assert len(set(levels)) == 81
        shared = [v for v in range(1, 101) if levels[v] == levels[v - 1]]
        assert min(shared) > 40

    def test_the_scales_agree_with_each_other(self):
        """One curve means LMS at half, a phone at half and the panel at
        half are the same level - which is the whole of ADR-0053 made
        true at the hardware."""
        assert renderer_value_to_hardware_raw(50, 100) == renderer_value_to_hardware_raw(
            64, 127
        ) == slider_percent_to_raw(50)

    def test_a_renderer_that_reports_no_scale_is_silent_not_loud(self):
        assert renderer_value_to_hardware_raw(50, 0) == 0

    def test_the_inverse_round_trips_within_a_point(self):
        """Exact until the taper became cubic; the DAC's 0.5 dB steps are
        coarser than the curve near the top, so a position can come back one
        off. It is used only for the no-renderer fallback display - while a
        renderer holds the device the number is its own, not derived."""
        for value in range(101):
            raw = renderer_value_to_hardware_raw(value, 100)
            assert abs(hardware_raw_to_renderer_value(raw, 100) - value) <= 1

    def test_a_128_position_scale_cannot_round_trip_and_that_is_safe(self):
        """**60 dB is 120 hardware steps and AVRCP has 128 positions**, so
        seven of them land on a level that reads back as their neighbour.
        That cannot be fixed by arithmetic, and it does not need to be:
        ADR-0053's invariant is that a renderer's own value is never sent
        back to it, and the panel's number comes from what the renderer
        reported rather than from the hardware. The inverse is used only
        for the no-renderer fallback, which is the 100-position scale
        above.

        Pinned so that a later change which *does* close that loop fails
        here rather than on George's phone (Finding 045 §12's ratchet)."""
        drifting = [
            value
            for value in range(128)
            if hardware_raw_to_renderer_value(
                renderer_value_to_hardware_raw(value, 127), 127
            )
            != value
        ]

        # 37 since the taper became cubic, from 7 - the curve is finer than
        # the DAC's steps over more of its length. Still never by more than
        # one, and still harmless for the same reason.
        assert len(drifting) == 37
        assert all(
            abs(
                hardware_raw_to_renderer_value(
                    renderer_value_to_hardware_raw(value, 127), 127
                )
                - value
            )
            <= 1
            for value in drifting
        )


def test_the_two_curves_the_registry_offers_are_the_two_that_exist():
    """ADR-0022's inventory, recorded 2026-09-23 on George's instruction:
    *"record the linear and cubic curves as settings for the next step."*

    The row is not wired yet, so this pins the arithmetic behind each name
    rather than a behaviour - so that whoever wires it has the numbers, and
    so that renaming one without the other fails here."""
    import json
    from pathlib import Path

    registry = json.loads(
        (Path(volume_module.__file__).parent / "settings_registry.json").read_text()
    )
    row = next(
        r
        for group in registry
        for r in group.get("rows", [])
        if r.get("key") == "travel_curve"
    )
    assert row["options"] == ["Cubic", "Linear (dB)"]
    assert row["default"] == "Cubic"

    # What each name means, at half travel, over the shared 60 dB span.
    cubic = raw_to_db(renderer_value_to_hardware_raw(50, 100))
    linear = -(1 - 0.5) * volume_module.RENDERER_DB_SPAN
    assert cubic == -15.5
    assert linear == -30.0
