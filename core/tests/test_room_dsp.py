"""Room correction's numbers (ADR-0175, ADR-0177): the sweep and its
recording, the curves, the target, the cuts in the bass and the broad
corrections above it, on a room made up in `room_sim`."""
import math

import pytest

np = pytest.importorskip("numpy")

from gexis_core import equaliser as eq  # noqa: E402
from gexis_core import room_dsp as rd  # noqa: E402

import room_sim as sim  # noqa: E402

FIT = (rd.GRID >= rd.FIT_LO) & (rd.GRID <= rd.LIMIT)


def test_the_grid_is_a_24th_of_an_octave_from_15_hz_to_20_khz():
    assert rd.GRID[0] == 15
    assert rd.GRID[-1] <= 20000 < rd.GRID[-1] * 2 ** (1 / 24)
    assert np.allclose(rd.GRID[1:] / rd.GRID[:-1], 2 ** (1 / 24))


def test_the_target_rises_3_db_below_80_hz():
    assert rd.target_db(15) == pytest.approx(3, abs=0.01)
    assert rd.target_db(70) == pytest.approx(1.5)
    assert rd.target_db(250) < 0.02


def test_the_sweep_is_eight_seconds_to_20_khz_and_never_clips():
    """Phase 30: to 20 kHz, its time in each octave of the bass as Phase 29's
    5 s to 1 kHz had it."""
    x = rd.log_sweep()
    assert len(x) == 8 * rd.FS and rd.SWEEP_HI == 20000
    assert rd.SWEEP_S / math.log2(rd.SWEEP_HI / rd.SWEEP_LO) == pytest.approx(5 / math.log2(100), rel=0.05)
    assert np.max(np.abs(x)) <= 1
    assert abs(x[0]) < 1e-6 and abs(x[-1]) < 1e-3, "faded in and out"


def test_a_recording_gives_the_rooms_curve():
    """From the bass to the treble; the last sixth of an octave below 20 kHz
    takes in where the sweep stops."""
    sweep = rd.log_sweep() * 0.1
    got = rd.response_db(rd.transfer(sim.record(sweep, seed=1, noise_db=-80), sweep))
    inside = (rd.GRID >= 18) & (rd.GRID <= 17000)
    assert np.max(np.abs(got - sim.curve(1))[inside]) < 0.5


def test_its_level_is_the_rooms_whatever_the_sweeps():
    """The same room at two sweep levels comes to the same curve."""
    sweep = rd.log_sweep()
    a = rd.response_db(rd.transfer(sim.record(sweep * 0.3, seed=2, noise_db=-100), sweep * 0.3))
    b = rd.response_db(rd.transfer(sim.record(sweep * 0.03, seed=2, noise_db=-100), sweep * 0.03))
    assert np.max(np.abs(a - b)[FIT]) < 0.2


def test_two_sweeps_disagree_when_a_noise_spoils_one():
    sweep = rd.log_sweep() * 0.05
    clean = rd.response_db(rd.transfer(sim.record(sweep, seed=3), sweep))
    again = rd.response_db(rd.transfer(sim.record(sweep, seed=3), sweep))
    spoiled = rd.response_db(rd.transfer(sim.record(sweep, seed=3, burst=(3.0, -20)), sweep))
    assert rd.agree_db(clean, again) < rd.AGREE_DB / 3
    assert rd.agree_db(clean, spoiled) > rd.AGREE_DB


def test_a_cut_is_the_equalisers_peaking_filter():
    for f in (30, 87, 170, 400):
        assert rd.peaking_db(87, -8, eq.Q, [f])[0] == pytest.approx(eq.band_db(87, -8, f, rd.FS), abs=1e-6)
    assert rd.peaking_db(87, -8, 5.6, [87])[0] == pytest.approx(-8, abs=1e-6)


def test_pink_noise_and_its_level():
    x = rd.pink_noise(1.0)
    assert np.sqrt(np.mean(x ** 2)) == pytest.approx(1, rel=0.05)
    t = np.arange(rd.FS) / rd.FS
    assert rd.band_level_db(np.sin(2 * np.pi * 100 * t)) == pytest.approx(-3.01, abs=0.05)
    assert rd.band_level_db(np.sin(2 * np.pi * 2000 * t)) < -100, "outside the band"


def _design(modes=sim.MODES, broad=sim.BROAD, channel=0):
    return rd.design([sim.curve(s, modes, broad=broad) for s in sim.positions(channel=channel, modes=modes)])


def test_the_cuts_land_on_the_peaks_and_leave_the_dips():
    d = _design()
    freqs = [c.freq for c in d.cuts]
    for peak in (42, 87, 170):
        assert any(abs(f / peak - 1) < 0.08 for f in freqs), f"no cut near {peak} Hz: {freqs}"
    for dip in (65, 110):
        assert not any(abs(f / dip - 1) < 0.05 for f in freqs), f"a cut in the dip at {dip} Hz"


def test_the_cuts_keep_to_the_limits():
    d = _design()
    assert 0 < len(d.cuts) <= rd.MAX_CUTS
    for c in d.cuts:
        assert -rd.MAX_CUT_DB <= c.gain <= -rd.CUT_MIN_DB
        assert rd.Q_MIN <= c.q <= rd.Q_MAX
        assert rd.FIT_LO <= c.freq <= rd.LIMIT
    assert [c.freq for c in d.cuts] == sorted(c.freq for c in d.cuts)


def test_the_peaks_come_down_to_the_target():
    d = _design()
    before = float(np.max((d.before - d.target)[FIT]))
    after = float(np.max((d.after - d.target)[FIT]))
    assert before > 6 and after < 2
    assert rd.peaks_down_db(d.before, d.after) > 6


def test_above_the_limit_is_left_alone():
    d = _design()
    above = rd.GRID >= 1.3 * rd.LIMIT
    assert np.max(np.abs(rd.cuts_db(d.cuts, rd.GRID)[above])) < 0.5


def test_one_target_the_bass_rise_joined_to_the_speakers_slope():
    """ADR-0177 items 2-3: the line through the average from 300 Hz to
    10 kHz above the limit, the bass's rise below it on the line's level
    there - one curve, its 0 at the limit."""
    d = _design()
    line = rd.slope(d.before)
    above = rd.GRID > rd.LIMIT
    assert np.allclose(d.target[above], line[above] + rd.target_db(rd.GRID[above]))
    at = float(np.interp(math.log(rd.LIMIT), np.log(rd.GRID), d.target))
    assert at == pytest.approx(0, abs=0.05)
    assert d.target[0] == pytest.approx(rd.target_db(rd.GRID[0]), abs=0.05)
    steps = np.abs(np.diff(d.target))
    assert np.max(steps) < 0.3, "no step where the two meet"


def test_the_slope_is_the_speakers_own():
    """A speaker tilted 1 dB an octave down keeps its tilt as the target."""
    tilt = -1.0 * np.log2(rd.GRID / 1000)
    curves = [sim.curve(s, broad=()) + tilt for s in sim.positions()]
    line = rd.slope(rd.power_average(curves))
    fit = (rd.GRID >= 300) & (rd.GRID <= 10000)
    a = np.polyfit(np.log2(rd.GRID[fit]), line[fit], 1)[0]
    assert a == pytest.approx(-1.0, abs=0.1)
    d = rd.design(curves)
    assert d.broad == () and d.room_within <= rd.ABOVE_LEAVE_DB, "a tilt is the speaker's, left alone"


def test_smoothing_is_a_power_average_a_third_of_an_octave_wide():
    rng = np.random.default_rng(3)
    c = rng.normal(0, 3, len(rd.GRID))
    k = 4
    p = 10 ** (c / 10)
    slow = [10 * math.log10(p[max(0, i - k): i + k + 1].mean()) for i in range(len(p))]
    assert np.allclose(rd.smooth(c), slow)


def test_no_position_is_made_worse():
    d = _design()
    after = d.positions + rd.cuts_db(d.cuts, rd.GRID)
    assert rd.worse_positions(d.positions, after, d.target, d.cuts) == []


def _dipped(*which):
    """The positions, those in `which` (from 0) with a dip at 87 Hz, where
    the others peak."""
    curves = [sim.curve(s) for s in sim.positions()]
    i = int(np.argmin(np.abs(rd.GRID - 87)))
    for k in which:
        curves[k][i - 4:i + 5] -= 18
    return curves


def _cut_near(d, f=87):
    return sum(c.gain for c in d.cuts if abs(c.freq / f - 1) < 0.08)


def test_a_cut_that_would_spoil_most_positions_is_made_smaller():
    """Two positions of three have a dip where the third peaks: the cut
    there would dig them deeper, so it is held back."""
    d = rd.design(_dipped(1, 2))
    assert abs(_cut_near(d)) < abs(_cut_near(_design()))
    after = d.positions + rd.cuts_db(d.cuts, rd.GRID)
    assert len(rd.worse_positions(d.positions, after, d.target, d.cuts)) <= 1


def test_one_position_in_a_dip_is_outvoted():
    """George, 2026-11-05: on sofapi one position of five held the room's
    main peak to a 1 dB cut. One position in a dip the others do not share
    no longer holds a cut back."""
    alone = rd.design(_dipped(2))
    held = rd.design(_dipped(1, 2))
    assert abs(_cut_near(alone)) > abs(_cut_near(held)) + 3


def test_a_room_near_the_target_has_nothing_to_cut():
    d = _design(modes=())
    assert d.nothing_to_cut and d.cuts == ()
    assert not d.nothing_to_correct, "the broad bumps above are still corrected"
    bass = rd.GRID <= 150
    assert np.allclose(d.after[bass], d.before[bass], atol=0.5)


def test_a_room_near_the_target_throughout_has_nothing_to_correct():
    d = _design(modes=(), broad=())
    assert d.nothing_to_correct and d.cuts == () and d.broad == ()
    assert d.room_within <= rd.ABOVE_LEAVE_DB
    assert np.allclose(d.after, d.before)


# ---- above the bass (ADR-0177) -------------------------------------------------------


def test_the_broad_corrections_raise_the_dip_and_lower_the_bump():
    d = _design()
    near = lambda f: [b for b in d.broad if abs(math.log2(b.freq / f)) < 0.5]  # noqa: E731
    assert near(450) and all(b.gain > 0 for b in near(450)), d.broad
    assert near(1800) and all(b.gain < 0 for b in near(1800)), d.broad
    assert near(6000) and all(b.gain > 0 for b in near(6000)), d.broad


def test_the_broad_corrections_keep_to_the_limits():
    for channel in (0, 1):
        d = _design(channel=channel)
        assert 0 < len(d.broad) <= rd.MAX_ABOVE
        for b in d.broad:
            assert abs(b.gain) <= rd.ABOVE_DB + 1e-9 and abs(b.gain) >= rd.CUT_MIN_DB
            assert rd.ABOVE_Q_MIN - 1e-9 <= b.q <= rd.ABOVE_Q_MAX + 1e-9
            assert rd.LIMIT - 1e-6 <= b.freq <= rd.ABOVE_HI + 1e-6
        freqs = [b.freq for b in d.broad]
        assert freqs == sorted(freqs)
        assert all(math.log2(b / a) >= rd.ABOVE_APART - 1e-6 for a, b in zip(freqs, freqs[1:])), freqs
        total = rd.cuts_db(d.broad, rd.GRID)
        assert np.max(np.abs(total)) <= rd.ABOVE_DB + 0.05, "the total within ±3 dB too"


def test_above_the_bass_comes_closer_to_the_slope():
    d = _design()
    assert d.within < d.room_within - 1
    assert d.within == rd.within_db(d.after, d.target)
    after = d.positions + rd.cuts_db(list(d.cuts) + list(d.broad), rd.GRID)
    inside = (rd.GRID >= 250) & (rd.GRID <= 14000)
    for b, a in zip(d.positions, after):
        rms = lambda c: float(np.sqrt(np.mean(((rd.smooth(c) - d.target)[inside]) ** 2)))  # noqa: E731
        assert rms(a) < rms(b), "every position closer"


def test_nothing_is_corrected_above_14_khz():
    d = _design()
    top = rd.GRID >= 16000
    assert np.max(np.abs(rd.cuts_db(d.broad, rd.GRID)[top])) < 1.0


def test_within_is_the_largest_gap_rounded_up_to_half_a_decibel():
    target = np.zeros(len(rd.GRID))
    curve = np.where((rd.GRID > 600) & (rd.GRID < 1600), 2.2, 0.0)
    assert rd.within_db(curve, target) == 2.5
    assert rd.within_db(np.zeros(len(rd.GRID)), target) == 0
    far = np.where(rd.GRID > 16000, 9.0, 0.0)
    assert rd.within_db(far, target) <= 0.5, "read from 300 Hz to 14 kHz"


def test_less_where_the_positions_disagree():
    """A dip at one position only, at 3 kHz, is not chased: the positions
    disagree there, and the correction is held near none; shared by all
    three, it is raised."""
    i = (rd.GRID > 2500) & (rd.GRID < 3600)
    at = int(np.argmin(np.abs(rd.GRID - 3000)))

    def correction(which):
        curves = [sim.curve(s) - np.where(i & (k in which), 9, 0) for k, s in enumerate(sim.positions())]
        return rd.cuts_db(rd.design(curves).broad, rd.GRID)[at], curves
    one, curves = correction({2})
    every, _ = correction({0, 1, 2})
    assert abs(one) < 0.5 and every > 1.5, (one, every)
    assert rd.spread_weight(curves)[at] == 0


def test_a_bass_alone_after_for_bass():
    d = _design()
    assert np.allclose(d.after_bass, rd.power_average(d.positions + rd.cuts_db(d.cuts, rd.GRID)))


def test_a_worse_position_is_found():
    d = _design()
    after = d.positions + rd.cuts_db(d.cuts, rd.GRID)
    worse = after.copy()
    i = int(np.argmin(np.abs(rd.GRID - d.cuts[0].freq)))
    worse[2][i - 2:i + 3] -= 6
    found = rd.worse_positions(d.positions, worse, d.target, d.cuts)
    assert [n for n, _ in found] == [3]


def test_the_cut_dict_is_rounded_for_the_store():
    assert rd.Cut(86.234, -8.437, 5.6789).as_dict() == {"freq": 86.2, "gain": -8.4, "q": 5.68}
    assert rd.Broad(1834.5, 2.46, 1.234).as_dict() == {"freq": 1834.5, "gain": 2.5, "q": 1.23}


def test_band_level_of_nothing():
    assert rd.band_level_db([]) == -200
    assert math.isfinite(rd.band_level_db(np.zeros(100)))
