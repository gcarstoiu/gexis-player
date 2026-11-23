"""A measurement of the room from start to *Keep it* (ADR-0175, ADR-0177), on
a room made up in `room_sim`: the steps, the taps it waits for, the level, the
sweeps that disagree, the check, Skip, Cancel and the timeout."""
import asyncio

import pytest

np = pytest.importorskip("numpy")

from gexis_core import equaliser as eq  # noqa: E402
from gexis_core import room_correction as rc  # noqa: E402
from gexis_core import room_dsp as rd  # noqa: E402
from gexis_core import room_run  # noqa: E402
from gexis_core.room_run import Host, Run  # noqa: E402

import room_sim as sim  # noqa: E402
from room_sim import Audio  # noqa: E402

CAL = rc.Calibration("7071234", -1.378, ((10.0, 0.0), (20000.0, 0.0)), "2026-11-05")


class Rig:
    def __init__(self, audio=None, timeout_s=30.0):
        self.audio = audio or Audio()
        self.calls = []
        self.states = []
        self.ended = []
        self.kept = []

        async def take():
            self.calls.append("take")

        async def stage(cuts):
            self.calls.append(("stage", cuts))
            self.audio.stage = cuts

        async def loud():
            self.calls.append("loud")

        async def finish(measurement):
            self.calls.append("finish")
            self.kept.append(measurement)

        def publish(state, ended):
            if state is not None:
                self.states.append(state)
            if ended is not None:
                self.ended.append(ended)

        async def fast(_s):
            await asyncio.sleep(0)

        self.run = Run("DAC", self.audio, CAL, Host(take, stage, loud, finish, publish), sleep=fast,
                       timeout_s=timeout_s, today=lambda: "2026-11-05", sweep_s=1.0)

    async def until(self, step, position=None, checking=None, limit=60.0):
        loop = asyncio.get_running_loop()
        end = loop.time() + limit
        while loop.time() < end:
            s = self.run.state
            if (s.step == step and (position is None or s.position == position)
                    and (checking is None or s.checking == checking) and (self.run.waiting or step not in
                                                                         ("place", "move", "correction", "nothing", "result"))):
                return s
            if not self.run.running:
                raise AssertionError(f"the run ended waiting for {step}: {self.ended}")
            await asyncio.sleep(0.01)
        raise AssertionError(f"no {step} {position}: at {self.run.state}")

    async def measure_all(self):
        await self.run.start()
        await self.until("place")
        self.run.tap("start")
        for n in range(2, rc.POSITIONS + 1):
            await self.until("move", n)
            self.audio.position = n
            self.run.tap("next")
        return await self.until("correction")


async def test_a_whole_run_kept():
    rig = Rig()
    await rig.measure_all()
    assert rig.calls[:3] == ["take", ("stage", None), "loud"], "the room as it is, at the maximum level"
    pending = rig.run.pending
    assert not pending.checked
    freqs = [f for f, _, _ in pending.cuts("L")]
    assert any(abs(f / 87 - 1) < 0.08 for f in freqs), freqs
    rig.run.tap("check")
    for n in range(1, rc.POSITIONS + 1):
        await rig.until("move", n, checking=True)
        rig.audio.position = n
        rig.run.tap("next")
    state = await rig.until("result")
    assert not state.expected
    stage = [c for c in rig.calls if isinstance(c, tuple) and c[1] is not None][-1][1]
    assert stage.cuts == (pending.cuts("L"), pending.cuts("R")), "checked with the correction on"
    assert stage.above == (pending.above("L"), pending.above("R")) and any(stage.above), "the full range"
    assert stage.lift is None, "no headroom taken while it measures"
    rig.run.tap("keep")
    await asyncio.wait_for(rig.run._task, 5)
    kept = rig.kept[-1]
    assert kept.checked and kept.date == "2026-11-05" and kept.worse == () and kept.range == rc.FULL
    assert rig.ended[-1] == {"how": "kept", "why": None} and len({str(e) for e in rig.ended}) == 1
    s = kept.speakers["L"]
    fit = (rd.GRID >= 20) & (rd.GRID <= 250)
    assert np.max((np.array(s.after) - np.array(s.target))[fit]) < 3, "measured after, down near the target"
    above = (rd.GRID >= 300) & (rd.GRID <= 14000)
    gap = lambda c: np.max(np.abs(rd.smooth(np.array(c)) - np.array(s.target))[above])  # noqa: E731
    assert gap(s.after) < gap(s.before) - 1.5, "above the bass too, measured"
    assert s.within == rd.within_db(np.array(s.after), np.array(s.target)) and s.within < s.room_within


async def test_the_check_plays_its_sweeps_lower_by_what_the_corrections_raise():
    """ADR-0177 item 7: no headroom while a run measures, so the run's level
    stays the run's; the check's sweeps play lower by the raise instead, and
    no sweep peaks higher through the stage than the run's."""
    rig = Rig()
    await rig.measure_all()
    run_peaks = list(rig.audio.peaks)
    rig.run.tap("check")
    for n in range(1, rc.POSITIONS + 1):
        await rig.until("move", n, checking=True)
        rig.audio.position = n
        rig.run.tap("next")
    await rig.until("result")
    raise_db = rig.run._check_db
    assert 2 <= raise_db <= 3.0
    check_peaks = rig.audio.peaks[len(run_peaks):]
    assert max(check_peaks) == pytest.approx(max(run_peaks) * 10 ** (-raise_db / 20), rel=0.01)
    rig.run.cancel()
    await rig.run.wait()


async def test_bass_is_worked_out_from_the_check():
    """ADR-0177 item 8: the check plays the full range; what *Bass* gives is
    the broad corrections taken back out of what it measured."""
    rig = Rig()
    await rig.measure_all()
    rig.run.tap("check")
    for n in range(1, rc.POSITIONS + 1):
        await rig.until("move", n, checking=True)
        rig.audio.position = n
        rig.run.tap("next")
    await rig.until("result")
    s = rig.run.pending.speakers["R"]
    broad = rd.cuts_db([rd.Broad(f, g, q) for f, g, q in s.above], rd.GRID)
    assert np.allclose(np.array(s.after_bass), np.array(s.after) - broad)
    bass = rd.GRID <= 150
    assert np.max(np.abs(np.array(s.after_bass) - np.array(s.after))[bass]) < 0.5, "the bass the same"
    rig.run.cancel()
    await rig.run.wait()


async def test_it_never_moves_on_without_the_tap():
    rig = Rig()
    await rig.run.start()
    await rig.until("place")
    await asyncio.sleep(0.05)
    assert rig.audio.plays == [], "nothing plays before Start"
    rig.run.tap("start")
    await rig.until("move", 2)
    played = len(rig.audio.plays)
    await asyncio.sleep(0.1)
    assert len(rig.audio.plays) == played and rig.run.state.step == "move"
    rig.run.tap("check")
    await asyncio.sleep(0.05)
    assert rig.run.state.step == "move", "a tap it is not waiting for is ignored"
    rig.run.cancel()
    await rig.run.wait()


async def test_the_tap_is_followed_by_a_countdown():
    rig = Rig()
    await rig.run.start()
    await rig.until("place")
    rig.run.tap("start")
    await rig.until("move", 2)
    rig.run.tap("next")
    await rig.until("measure", 2)
    counts = [s.count for s in rig.states if s.step == "countdown"]
    assert counts == [3, 2, 1]
    rig.run.cancel()
    await rig.run.wait()


async def test_each_speaker_alone_then_both_two_sweeps_each():
    rig = Rig()
    levels = {}
    real = rig.audio.play

    async def play(signal, channel, tail_s=1.1):
        if channel is not None:
            # The sweep after its mark (ADR-0187 C4), on its first speaker.
            x = np.asarray(signal)[int(rd.MARK_GAP_S * rd.FS):, channel if isinstance(channel, int) else channel[0]]
            levels.setdefault(str(channel), float(np.sqrt(np.mean(np.square(x)))))
        return await real(signal, channel, tail_s)
    rig.audio.play = play
    await rig.run.start()
    await rig.until("place")
    rig.run.tap("start")
    await rig.until("move", 2)
    sweeps = [c for c, _ in rig.audio.plays if c not in (None, "frames")]
    assert sweeps == [0, 0, 1, 1, (0, 1), (0, 1)]
    before = [c for c, _ in rig.audio.plays[: -6]]
    level = before[:before.index("frames")]
    assert level == [None] * len(level), "the level with both"
    assert set(before[len(level):]) == {"frames"}, "then the speakers timed (ADR-0185)"
    assert levels["(0, 1)"] == pytest.approx(levels["0"] / 2), "both 6 dB lower each, no louder than one"
    rig.run.cancel()
    await rig.run.wait()


async def test_the_bass_is_designed_from_both_together_the_same_on_both():
    """George, 2026-11-05: both speakers, as heard - before in the run and
    after in the check. ADR-0175's amendment (George, 2026-11-17): the bass's
    cuts are designed from them and go on both speakers; above the bass the
    corrections stay each speaker's."""
    rig = Rig()
    await rig.measure_all()
    m = rig.run.pending
    both = m.speakers[rc.BOTH]
    assert both.cuts and both.above == () and len(both.after) == len(both.before)
    assert len(both.positions) == rc.POSITIONS and m.bass_from == rc.BOTH
    assert m.cuts("L") == m.cuts("R") == both.cuts
    assert rig.run._cuts().cuts == (both.cuts, both.cuts)
    assert m.speakers["L"].before != m.speakers["R"].before, "each speaker's own curves are kept"
    rig.run.tap("check")
    for n in range(1, rc.POSITIONS + 1):
        await rig.until("move", n, checking=True)
        rig.audio.position = n
        rig.run.tap("next")
    await rig.until("result")
    both = rig.run.pending.speakers[rc.BOTH]
    assert len(both.after) == len(both.before)
    fit = (rd.GRID >= 20) & (rd.GRID <= 250)
    gap_before = np.max((np.array(both.before) - np.array(both.target))[fit])
    gap_after = np.max((np.array(both.after) - np.array(both.target))[fit])
    assert gap_after < gap_before - 3, "the two together come down too"
    rig.run.cancel()
    await rig.run.wait()


async def _level_only(audio):
    rig = Rig(audio)
    await rig.run.start()
    await rig.until("place")
    rig.run.tap("start")
    for _ in range(600):
        s = rig.run.state
        if s.too_quiet or s.step != "level" and s.step != "place":
            break
        await asyncio.sleep(0.01)
    return rig


def _reading_at(level, gain=1.0):
    """What the made-up seat hears of the level step's noise at `level`."""
    noise = rd.pink_noise(room_run.LEVEL_BURST_S) * 10 ** (level / 20)
    rec = sim.record(noise, seed=1, gain=gain, noise_db=-200, tail_s=room_run.LEVEL_TAIL_S)
    lo, hi = (int(t * rd.FS) for t in room_run.LEVEL_WINDOW_S)
    return rd.band_level_db(rec[lo:hi]) + Audio().offset


def _gain_for(spl_at_cap):
    """The system's gain for a seat that hears `spl_at_cap` with the noise
    at its cap."""
    return 10 ** ((spl_at_cap - _reading_at(room_run.LEVEL_CAP_DBFS)) / 20)


def _noise_levels(audio):
    """The level step's noise as played, in dB of full scale."""
    real = audio.play
    levels = []

    async def play(signal, channel, tail_s=1.1):
        if channel is None and np.ndim(signal) == 1 and np.any(signal):
            levels.append(20 * float(np.log10(np.sqrt(np.mean(np.square(signal))))))
        return await real(signal, channel, tail_s)
    audio.play = play
    return levels


async def test_the_level_aims_for_60_db():
    """George, 2026-11-05: 60 dB in every room, over 75 and then 50."""
    rig = await _level_only(Audio(noise_db=-70))
    s = rig.run.state
    assert s.aim_db == room_run.AIM_DB == 60
    assert not s.too_quiet and abs(s.level_db - 60) <= room_run.AIM_WITHIN
    assert rig.run._level_dbfs <= room_run.LEVEL_CAP_DBFS
    rig.run.cancel()
    await rig.run.wait()


async def test_past_the_noises_cap_the_sweeps_go_the_rest_of_the_way():
    """sofapi as George sets it: 50 dB at -18 dBFS, so 56 at the noise's
    cap; the sweeps are set the 4 dB further, the noise never is."""
    audio = Audio(noise_db=-70, gain=_gain_for(56))
    levels = _noise_levels(audio)
    rig = await _level_only(audio)
    s = rig.run.state
    assert not s.too_quiet and abs(s.level_db - 60) <= room_run.AIM_WITHIN, s
    assert room_run.LEVEL_CAP_DBFS < rig.run._level_dbfs <= rig.run._sweep_cap
    assert max(levels) <= room_run.LEVEL_CAP_DBFS + 0.1
    rig.run.cancel()
    await rig.run.wait()


async def test_a_sweep_at_its_cap_peaks_at_its_most():
    """Phase 30: the cap is a sweep's peak. One to 20 kHz has less of itself
    in the bass, where the level is read, than Phase 29's to 1 kHz: matched
    there at -6 dBFS, its peaks would have reached +0.7."""
    audio = Audio(noise_db=-70, gain=_gain_for(45))
    peaks = []
    play = audio.play

    async def heard(signal, channel, tail_s=1.1):
        if channel is not None:
            peaks.append(float(np.max(np.abs(signal))))
        return await play(signal, channel, tail_s)
    audio.play = heard
    rig = await _level_only(audio)
    assert rig.run._level_dbfs == rig.run._sweep_cap
    await rig.run._curve("L")
    assert 20 * np.log10(peaks[-1]) == pytest.approx(room_run.SWEEP_PEAK_DBFS, abs=0.1)
    rig.run.cancel()
    await rig.run.wait()


async def test_short_of_the_aim_it_is_taken_from_45_db():
    """At the sweeps' cap, a level short of the aim but over 45 dB and 15 dB
    over the noise goes on: nobody is asked to turn the amplifier up for it."""
    rig = await _level_only(Audio(noise_db=-70, gain=_gain_for(45)))
    s = rig.run.state
    assert not s.too_quiet, s
    assert room_run.TAKE_MIN <= s.level_db < s.aim_db - room_run.AIM_WITHIN
    assert rig.run._level_dbfs == rig.run._sweep_cap
    rig.run.cancel()
    await rig.run.wait()


async def test_short_of_45_db_at_the_sweeps_cap_is_too_quiet():
    rig = await _level_only(Audio(noise_db=-70, gain=_gain_for(35)))
    assert rig.run.state.too_quiet
    rig.run.cancel()
    await rig.run.wait()


async def test_too_quiet_waits_for_try_again():
    rig = Rig(Audio(offset=45.0))
    await rig.run.start()
    await rig.until("place")
    rig.run.tap("start")
    for _ in range(200):
        if rig.run.state.too_quiet and rig.run.waiting:
            break
        await asyncio.sleep(0.01)
    assert rig.run.state.too_quiet and rig.run.state.level_db < 70
    levels = [c for c, _ in rig.audio.plays]
    assert levels and all(c is None for c in levels), "no sweep played"
    rig.audio.offset = 120.0    # the amplifier turned up
    rig.run.tap("again")
    await rig.until("move", 2)
    rig.run.cancel()
    await rig.run.wait()


async def test_a_microphone_that_does_not_hear_goes_no_higher_than_the_cap():
    """A covered microphone: the noise rises to the cap and no further."""
    audio = Audio(offset=60.0)
    levels = []

    async def silent(signal, channel, tail_s=1.5):
        audio.plays.append((channel, 1))
        levels.append(float(np.sqrt(np.mean(np.square(signal)))) if len(signal) else 0.0)
        return np.random.default_rng(len(audio.plays)).standard_normal(len(signal) + 48000) * 1e-4
    audio.play = silent
    rig = Rig(audio)
    await rig.run.start()
    await rig.until("place")
    rig.run.tap("start")
    for _ in range(300):
        if rig.run.state.too_quiet:
            break
        await asyncio.sleep(0.01)
    assert rig.run.state.too_quiet
    loudest = 20 * np.log10(max(levels))
    assert loudest <= room_run.LEVEL_CAP_DBFS + 0.5
    rig.run.cancel()
    await rig.run.wait()


async def test_a_microphone_that_stops_following_ends_it_early():
    """Heard, then not following the steps (something saturates): it stops
    within four steps, well under the cap."""
    audio = Audio()
    real = audio.play
    count = {"n": 0}

    async def flat(signal, channel, tail_s=1.5):
        count["n"] += 1
        # From the fourth burst on, the microphone hears the same as the third.
        if count["n"] >= 4 and channel is None and len(signal) and np.any(signal):
            signal = signal / np.sqrt(np.mean(np.square(signal))) * 10 ** ((room_run.LEVEL_START_DBFS + 6) / 20)
        return await real(signal, channel, tail_s)
    audio.play = flat
    audio.offset = 90.0
    rig = await _level_only(audio)
    assert rig.run.state.too_quiet
    assert count["n"] <= 1 + 3 + room_run.LEVEL_UNHEARD_STEPS + 1
    rig.run.cancel()
    await rig.run.wait()


async def test_a_spoiled_sweep_is_measured_again():
    rig = Rig(Audio(bursts=(2,)))
    await rig.run.start()
    await rig.until("place")
    rig.run.tap("start")
    await rig.until("move", 2)
    assert any(s.noise for s in rig.states if s.step == "measure"), "shown as spoiled"
    sweeps = [c for c, _ in rig.audio.plays if c not in (None, "frames")]
    assert sweeps.count(0) == 3 and sweeps.count(1) == 2
    rig.run.cancel()
    await rig.run.wait()


async def test_skip_keeps_the_expected_after():
    rig = Rig()
    await rig.measure_all()
    expected_after = rig.run.pending.speakers["L"].after
    rig.run.tap("check")
    await rig.until("move", 1, checking=True)
    rig.run.tap("next")
    await rig.until("move", 2, checking=True)
    rig.run.tap("skip")
    state = await rig.until("result")
    assert state.expected
    rig.run.tap("keep")
    await asyncio.wait_for(rig.run._task, 5)
    kept = rig.kept[-1]
    assert not kept.checked and kept.speakers["L"].after == expected_after


async def test_discard_keeps_nothing():
    rig = Rig()
    await rig.measure_all()
    rig.run.tap("discard")
    await asyncio.wait_for(rig.run._task, 5)
    assert rig.kept == [None] and rig.ended[-1]["how"] == "discarded"


async def test_cancel_at_any_step_gives_the_player_back():
    rig = Rig()
    await rig.run.start()
    await rig.until("place")
    rig.run.tap("start")
    await rig.until("measure", 1)
    rig.run.cancel()
    await rig.run.wait()
    assert rig.kept == [None] and rig.ended[0] == rig.ended[-1] == {"how": "cancelled", "why": "cancel"}
    assert rig.calls[-1] == "finish"


async def test_ten_minutes_without_a_tap_cancels_it():
    rig = Rig(timeout_s=0.2)
    await rig.run.start()
    await rig.until("place")
    await asyncio.wait_for(rig.run._task, 5)
    assert rig.ended[-1] == {"how": "cancelled", "why": "timeout"} and rig.kept == [None]
    assert room_run.TIMEOUT_S == 600


async def test_a_room_near_the_target_has_nothing_to_correct():
    rig = Rig(Audio(modes=(), broad=()))
    await rig.run.start()
    await rig.until("place")
    rig.run.tap("start")
    for n in range(2, rc.POSITIONS + 1):
        await rig.until("move", n)
        rig.audio.position = n
        rig.run.tap("next")
    await rig.until("nothing")
    rig.run.tap("done")
    await asyncio.wait_for(rig.run._task, 5)
    assert rig.kept == [None] and rig.ended[-1]["how"] == "done"


async def test_progress_only_goes_up():
    rig = Rig()
    await rig.measure_all()
    rig.run.tap("check")
    for n in range(1, rc.POSITIONS + 1):
        await rig.until("move", n, checking=True)
        rig.audio.position = n
        rig.run.tap("next")
    await rig.until("result")
    values = [s.progress for s in rig.states]
    assert values == sorted(values) and values[-1] == 1.0
    rig.run.cancel()
    await rig.run.wait()


async def test_skip_while_the_check_sweeps():
    rig = Rig()
    await rig.measure_all()
    rig.run.tap("check")
    await rig.until("move", 1, checking=True)
    rig.run.tap("next")
    await rig.until("checking", 1)
    rig.run.tap("skip")
    state = await rig.until("result")
    assert state.expected
    rig.run.cancel()
    await rig.run.wait()


async def test_measure_answers_before_the_player_is_ready():
    """George, 2026-11-05: Measure was slow. The run shows *place* at once;
    taking the device, the stage and the level follow behind it, and Start
    waits for them."""
    rig = Rig()
    gate = asyncio.Event()
    take = rig.run._host.take

    async def slow_take():
        await gate.wait()
        await take()
    rig.run._host.take = slow_take
    await asyncio.wait_for(rig.run.start(), 0.5)
    assert rig.run.state.step == "place" and rig.states[-1].step == "place"
    rig.run.tap("start")
    await asyncio.sleep(0.05)
    assert rig.audio.plays == [], "nothing plays before the player is ready"
    gate.set()
    await rig.until("move", 2)
    rig.run.cancel()
    await rig.run.wait()


async def test_cancel_ends_at_once_and_the_sound_stops():
    rig = Rig()
    stopped = asyncio.Event()
    real = rig.audio.play

    async def long_sweep(signal, channel, tail_s=1.1):
        if channel is None:
            return await real(signal, channel, tail_s)
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            stopped.set()
            raise
    rig.audio.play = long_sweep
    await rig.run.start()
    await rig.until("place")
    rig.run.tap("start")
    for _ in range(500):
        if rig.run.state.step == "measure":
            break
        await asyncio.sleep(0.01)
    rig.run.cancel()
    assert rig.run.ended == {"how": "cancelled", "why": "cancel"} and rig.ended, "shown at once"
    await asyncio.wait_for(stopped.wait(), 1)
    await rig.run.wait()
    assert rig.run.released and rig.calls[-1] == "finish"


# ---- ADR-0185: the speakers checked and aligned, fewer repeats ----------------------


async def _to(rig, step, position=None):
    await rig.run.start()
    await rig.until("place")
    rig.run.tap("start")
    return await rig.until(step, position)


async def test_the_nearer_speaker_is_delayed_so_both_arrive_together():
    """D2, C1: timed at position 1 before the sweeps; the left 10 cm nearer
    is delayed by its 0.3 ms from then on - the sweeps and the check measure
    what will play - and the measurement keeps it."""
    audio = Audio(jitter_s=0.05)
    audio.delays = {n: (left, right + 0.0003) for n, (left, right) in sim.SIDES.items()}
    rig = Rig(audio)
    await rig.measure_all()
    pending = rig.run.pending
    assert pending.distance_cm == pytest.approx(10.3, abs=1.0)
    assert pending.delay[0] == pytest.approx(0.3, abs=0.03) and pending.delay[1] == 0.0
    stages = [c[1] for c in rig.calls if isinstance(c, tuple) and c[1] is not None]
    assert stages[0].delay == pending.delay and not any(stages[0].cuts), "from before the first sweep"
    first_sweep = next(i for i, (c, _) in enumerate(audio.plays) if c not in (None, "frames"))
    assert rig.calls.index(("stage", stages[0])) < len(rig.calls) and first_sweep > 0
    rig.run.tap("check")
    for n in range(1, rc.POSITIONS + 1):
        await rig.until("move", n, checking=True)
        rig.audio.position = n
        rig.run.tap("next")
    await rig.until("result")
    check = [c[1] for c in rig.calls if isinstance(c, tuple) and c[1] is not None][-1]
    assert check.delay == pending.delay and any(check.cuts), "checked with the delay on"
    assert rig.run.state.distance_cm == pytest.approx(10.3, abs=1.0)
    rig.run.cancel()
    await rig.run.wait()


async def test_a_speaker_with_plus_and_minus_swapped_stops_the_run():
    audio = Audio()
    audio.polarity = (1.0, -1.0)
    rig = Rig(audio)
    await rig.run.start()
    await rig.until("place")
    rig.run.tap("start")
    await asyncio.wait_for(rig.run._task, 30)
    assert rig.ended[-1] == {"how": "cancelled", "why": "polarity"} and rig.kept == [None]
    assert not [c for c, _ in audio.plays if c not in (None, "frames")], "nothing swept"


async def test_speakers_far_apart_wait_for_measure_anyway():
    """C2: more than 1 ms apart, the screen says so and waits."""
    audio = Audio()
    audio.delays = {**audio.delays, 1: (0.0080, 0.0095)}
    rig = Rig(audio)
    state = await _to(rig, "far")
    assert state.distance_cm == pytest.approx(51.5, abs=1.0) and rig.run.waiting
    assert not [c for c, _ in audio.plays if c not in (None, "frames")]
    rig.run.tap("next")
    await rig.until("move", 2)
    rig.run.cancel()
    await rig.run.wait()


async def test_swapped_speakers_are_found_at_position_2():
    """D1: 40 cm to the left the left must be nearer; swapped, it is the
    further, and the run stops before position 2 is swept."""
    audio = Audio()
    audio.delays = dict(sim.SIDES)
    audio.swapped = True
    rig = Rig(audio)
    await _to(rig, "move", 2)
    audio.position = 2
    rig.run.tap("next")
    await asyncio.wait_for(rig.run._task, 30)
    assert rig.ended[-1] == {"how": "cancelled", "why": "swapped"} and rig.kept == [None]
    assert not [n for c, n in audio.plays if c not in (None, "frames") and n == 2], "position 2 not swept"


async def test_speakers_the_right_way_round_go_on_at_position_2():
    audio = Audio()
    audio.delays = dict(sim.SIDES)
    rig = Rig(audio)
    await rig.measure_all()
    assert rig.run.pending is not None and not rig.ended


async def test_noise_alone_no_longer_repeats_sweeps_and_is_not_corrected():
    """C3: in a noisy room (the bass's floor about 12 dB under the sweeps)
    the sweeps compared everywhere were repeated - judged only where both
    stand 20 dB over the room's noise, none is; the points still under 10
    dB once averaged are left uncorrected."""
    rig = Rig(Audio(noise_db=-55))
    await _to(rig, "move", 2)
    sweeps = [c for c, _ in rig.audio.plays if c not in (None, "frames")]
    assert sweeps == [0, 0, 1, 1, (0, 1), (0, 1)]
    trust = rig.run._trust("L")
    # Up to 200 Hz: the noise a sweep is judged by is one draw, whose points
    # scatter by 2-3 dB from draw to draw, and this room stands within about
    # 1 dB of the limit near 250 Hz (a longer, marked recording drew another).
    assert trust is not None and not trust.all() and trust[(rd.GRID >= 100) & (rd.GRID <= 200)].all()
    rig.run.cancel()
    await rig.run.wait()


async def test_the_check_takes_more_sweeps_for_playing_lower():
    """C3: the check plays lower by what the corrections raise, and makes it
    up in sweeps averaged."""
    rig = Rig()
    await rig.measure_all()
    rig.run.tap("check")
    await rig.until("move", 1, checking=True)
    rig.audio.position = 1
    rig.run.tap("next")
    await rig.until("move", 2, checking=True)
    assert rig.run._check_db > 0
    wanted = rig.run._sweeps_wanted(True)
    assert wanted > room_run.SWEEPS
    at_1 = [c for c, n in rig.audio.plays[-3 * wanted:] if n == 1]
    assert [at_1.count(c) for c in (0, 1, (0, 1))] == [wanted] * 3
    # George, 2026-11-23: it said *sweep 3 of 2*; the count is the check's.
    shown = [(s.sweep, s.sweeps) for s in rig.states if s.step == "checking" and s.position == 1]
    assert {n for _, n in shown} == {wanted} and max(k for k, _ in shown) == wanted
    rig.run.cancel()
    await rig.run.wait()


async def test_the_distance_steps_short_sweeps_light_the_speaker_they_come_from():
    """George, 2026-11-23: as the measuring sweeps do - the left, the
    right, the left again, then none."""
    rig = Rig()
    play = rig.audio.play

    async def slow(signal, channel, tail_s=1.1):
        if np.ndim(signal) == 2:            # the timing's frames: let time pass
            for _ in range(20):
                await asyncio.sleep(0)
        return await play(signal, channel, tail_s)
    rig.audio.play = slow
    await rig.run.start()
    await rig.until("place")
    rig.run.tap("start")
    await rig.until("measure", 1)
    lit = [s.speaker for s in rig.states if s.step == "timing"]
    changes = [k for i, k in enumerate(lit) if i == 0 or k != lit[i - 1]]
    assert changes[:5] == [None, "L", "R", "L", None], changes
    assert rig.run.state.as_dict()["sweeps"] == room_run.SWEEPS
    rig.run.cancel()
    await rig.run.wait()
