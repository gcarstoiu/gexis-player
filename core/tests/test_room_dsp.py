"""Room correction's numbers (ADR-0175): the sweep and its recording, the
curves, the target and the cuts, on a room made up in `room_sim`."""
import math

import pytest

np = pytest.importorskip("numpy")

from gexis_core import equaliser as eq  # noqa: E402
from gexis_core import room_dsp as rd  # noqa: E402

import room_sim as sim  # noqa: E402

FIT = (rd.GRID >= rd.FIT_LO) & (rd.GRID <= rd.LIMIT)


def test_the_grid_is_a_24th_of_an_octave_from_15_hz():
    assert rd.GRID[0] == 15
    assert rd.GRID[-1] <= 500 < rd.GRID[-1] * 2 ** (1 / 24)
    assert np.allclose(rd.GRID[1:] / rd.GRID[:-1], 2 ** (1 / 24))


def test_the_target_rises_3_db_below_80_hz():
    assert rd.target_db(15) == pytest.approx(3, abs=0.01)
    assert rd.target_db(70) == pytest.approx(1.5)
    assert rd.target_db(250) < 0.02


def test_the_sweep_is_five_seconds_and_never_clips():
    x = rd.log_sweep()
    assert len(x) == 5 * rd.FS
    assert np.max(np.abs(x)) <= 1
    assert abs(x[0]) < 1e-6 and abs(x[-1]) < 1e-3, "faded in and out"


def test_a_recording_gives_the_rooms_curve():
    sweep = rd.log_sweep() * 0.1
    got = rd.response_db(rd.transfer(sim.record(sweep, seed=1, noise_db=-80), sweep))
    inside = (rd.GRID >= 18) & (rd.GRID <= 450)
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


def _design(modes=sim.MODES):
    return rd.design([sim.curve(s, modes) for s in sim.positions(modes=modes)])


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


def test_the_target_sits_on_the_level_an_octave_above():
    d = _design()
    above = (rd.GRID > rd.LIMIT) & (rd.GRID <= 2 * rd.LIMIT)
    assert float(np.mean(d.before[above])) == pytest.approx(0, abs=1e-6)
    assert d.target[0] == pytest.approx(rd.target_db(rd.GRID[0]))


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
    assert np.allclose(d.after, d.before)


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


def test_band_level_of_nothing():
    assert rd.band_level_db([]) == -200
    assert math.isfinite(rd.band_level_db(np.zeros(100)))
