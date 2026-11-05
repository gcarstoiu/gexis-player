"""A measurement of the room from start to *Keep it* (ADR-0175), on a room
made up in `room_sim`: the steps, the taps it waits for, the level, the
sweeps that disagree, the check, Skip, Cancel and the timeout."""
import asyncio

import pytest

np = pytest.importorskip("numpy")

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
        for n in range(2, 6):
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
    for n in range(1, 6):
        await rig.until("move", n, checking=True)
        rig.audio.position = n
        rig.run.tap("next")
    state = await rig.until("result")
    assert not state.expected
    stage = next(c for c in rig.calls if isinstance(c, tuple) and c[1] is not None)
    assert stage[1] == (pending.cuts("L"), pending.cuts("R")), "checked with the correction on"
    rig.run.tap("keep")
    await asyncio.wait_for(rig.run._task, 5)
    kept = rig.kept[-1]
    assert kept.checked and kept.date == "2026-11-05" and kept.worse == ()
    assert rig.ended[-1] == {"how": "kept", "why": None} and len({str(e) for e in rig.ended}) == 1
    s = kept.speakers["L"]
    fit = (rd.GRID >= 20) & (rd.GRID <= 250)
    assert np.max((np.array(s.after) - np.array(s.target))[fit]) < 3, "measured after, down near the target"


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


async def test_each_speaker_alone_two_sweeps_each():
    rig = Rig()
    await rig.run.start()
    await rig.until("place")
    rig.run.tap("start")
    await rig.until("move", 2)
    sweeps = [c for c, _ in rig.audio.plays if c is not None]
    assert sweeps == [0, 0, 1, 1]
    assert [c for c, _ in rig.audio.plays[: -4]] == [None] * (len(rig.audio.plays) - 4), "the level with both"
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


async def test_the_level_aims_20_db_above_the_rooms_noise():
    """George, 2026-11-05: from the room's noise, not 75 dB."""
    rig = await _level_only(Audio(noise_db=-70))
    s = rig.run.state
    assert room_run.AIM_MIN < s.aim_db < room_run.AIM_MAX
    assert not s.too_quiet and abs(s.level_db - s.aim_db) <= room_run.AIM_WITHIN
    assert rig.run._level_dbfs <= room_run.LEVEL_CAP_DBFS
    rig.run.cancel()
    await rig.run.wait()


async def test_a_quiet_room_aims_at_50_and_a_noisy_one_at_most_60():
    """George, 2026-11-05: 60 at most."""
    assert room_run.aim_for(20) == 50 and room_run.aim_for(35) == 55 and room_run.aim_for(50) == 60
    rig = await _level_only(Audio())
    assert rig.run.state.aim_db == 50
    rig.run.cancel()
    await rig.run.wait()


async def test_short_of_the_aim_it_is_taken_from_45_db():
    """At the cap, a level short of the aim but over 45 dB and 15 dB over
    the noise goes on: nobody is asked to turn the amplifier up for it."""
    rig = await _level_only(Audio(noise_db=-70, gain=10 ** (-61 / 20)))
    s = rig.run.state
    assert not s.too_quiet, s
    assert s.level_db < s.aim_db - room_run.AIM_WITHIN and s.level_db >= room_run.TAKE_MIN
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
    sweeps = [c for c, _ in rig.audio.plays if c is not None]
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


async def test_a_room_near_the_target_has_nothing_to_cut():
    rig = Rig(Audio(modes=()))
    await rig.run.start()
    await rig.until("place")
    rig.run.tap("start")
    for n in range(2, 6):
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
    for n in range(1, 6):
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
