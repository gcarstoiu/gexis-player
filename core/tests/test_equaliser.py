"""The equaliser's bands, presets, state and CamillaDSP configuration (ADR-0162)."""
import math

import pytest

from gexis_core import equaliser as eq
from gexis_core.equaliser import Equaliser, EqualiserError


def test_bands_an_octave_apart_from_31_hz():
    assert eq.CENTRES[0] == 31.25 and eq.CENTRES[-1] == 16000
    assert all(b / a == 2 for a, b in zip(eq.CENTRES, eq.CENTRES[1:]))
    assert len(eq.BANDS) == len(eq.CENTRES) == 10


def test_presets_as_adr_0162_has_them():
    assert [p.name for p in eq.PRESETS] == ["Flat", "Rock", "Pop", "Jazz", "Classical", "Electronic",
                                            "Hip-hop", "Acoustic", "Vocal", "Late night"]
    assert eq.PRESET["rock"].gains == (4, 3, 2, 0, -1, -1, 0, 2, 3, 4)
    assert eq.PRESET["late"].gains == (5, 4, 2, 0, 0, 0, 0, 1, 2, 3)
    assert all(len(p.gains) == 10 and all(-12 <= g <= 12 for g in p.gains) for p in eq.PRESETS)


@pytest.mark.parametrize("bad", [None, [0] * 9, [0] * 11, [13] + [0] * 9, ["1"] + [0] * 9, [True] + [0] * 9,
                                 [float("nan")] + [0] * 9])
def test_gains_refused(bad):
    with pytest.raises(EqualiserError):
        eq.gains_from(bad)


def test_one_band_peaks_at_its_gain_at_its_centre():
    for i, c in enumerate(eq.CENTRES):
        g = [0] * 10
        g[i] = 6
        assert eq.response_db(g, c) == pytest.approx(6, abs=1e-6)


def test_headroom_is_the_curves_peak_rounded_up():
    assert eq.headroom_db(eq.FLAT) == 0
    assert eq.headroom_db((-3,) * 10) == 0, "a cut lowers nothing"
    # The design's figures (eq-data.js at 48 kHz) for the presets.
    assert eq.headroom_db(eq.PRESET["rock"].gains) == 5
    assert eq.headroom_db(eq.PRESET["hiphop"].gains) == 6
    for p in eq.PRESETS:
        h = eq.headroom_db(p.gains)
        assert h * 2 == int(h * 2), "in 0.5 dB steps"
        assert h >= max(eq.peak_db(p.gains, fs) for fs in eq.RATES) - 0.05


def test_neighbouring_boosts_add_up():
    two = [0, 0, 0, 0, 6, 6, 0, 0, 0, 0]
    assert eq.headroom_db(tuple(two)) > 6


def test_never_less_than_the_peak():
    """Rounded strictly up: the design's drawing lets 0.05 dB through."""
    g = (2, 2, 1, 0, 0, -1, -1, 0, 1, 1)
    assert eq.headroom_db(g) >= eq.peak_db(g)


#: Every rate the stage runs at: a stream's, up to the loopback's 192 kHz,
#: and a card's highest when it converts.
STAGE_RATES = (44100, 48000, 88200, 96000, 176400, 192000, 352800, 384000, 705600, 768000)


def test_no_setting_rises_above_its_headroom_at_any_rate_the_stage_runs_at():
    """**The review of 1.16.1.** The headroom was taken at 44.1 and 48 kHz,
    where the top bands narrow; at 96 kHz and up they keep their width, and
    a treble boost of one's own (+6/+12/+12 at 4, 8 and 16 kHz) rose 1.2 to
    1.6 dB above it - clipped at CamillaDSP's output."""
    lift = (((12000.0, 3.0, 1.0),), ((9000.0, 3.0, 0.8),))
    for gains in [(0,) * 7 + (6, 12, 12), (0,) * 7 + (12, 12, 12), (0,) * 8 + (6, 6), (0,) * 6 + (3, 9, 12, 12)]:
        h = eq.headroom_db(gains)
        assert all(eq.peak_db(gains, fs) <= h for fs in STAGE_RATES), gains
        h = eq.headroom_db(gains, lift)
        assert all(eq.peak_db(gains, fs, channel) <= h for fs in STAGE_RATES for channel in lift), gains
    for p in eq.PRESETS:
        assert all(eq.peak_db(p.gains, fs) <= eq.headroom_db(p.gains) for fs in STAGE_RATES), p.key


def test_the_peak_is_the_filters_summed_at_each_point_of_the_curve():
    gains, extra = (3, -2, 0, 4, 0, 0, 1, 6, 12, -3), ((60.0, -6.0, 4.0), (9000.0, 2.5, 0.9))
    for fs in (44100, 96000, 768000):
        points = [eq.CENTRES[0] * 2 ** (-0.5 + (eq._OCT_END + 0.5) * j / (eq._POINTS - 1))
                  for j in range(eq._POINTS)]
        want = max([0.0] + [eq.response_db(gains, f, fs) + sum(eq.band_db(f0, g, f, fs, q) for f0, g, q in extra)
                            for f in points if f < fs / 2])
        assert eq.peak_db(gains, fs, extra) == pytest.approx(want, abs=1e-9)


def test_choose_a_preset_then_move_a_band_makes_custom():
    e = Equaliser().choose("dac", "rock")
    assert e.output("dac").sel == "rock" and e.output("dac").gains == eq.PRESET["rock"].gains
    e = e.set_band("dac", 2, 5)
    out = e.output("dac")
    assert out.sel == "custom" and out.source == "rock" and out.gains[2] == 5
    e = e.set_band("dac", 3, 1)
    assert e.output("dac").source == "rock", "Custom remembers where it came from"
    e = e.set_band("dac", 3, 0).set_band("dac", 2, 2)
    assert e.output("dac").sel == "rock" and e.output("dac").source is None, "back where it was"


def test_each_output_keeps_its_own():
    e = Equaliser().set_on("dac", True).choose("dac", "jazz")
    assert e.output("hdmi").on is False and e.output("hdmi").sel == "flat"
    assert e.output("dac").on and e.output("dac").sel == "jazz"


def test_save_rename_delete():
    e = Equaliser().choose("dac", "rock").set_band("dac", 0, 6)
    e, own = e.save_as("dac", "  Evening  ")
    assert own.name == "Evening" and own.key == "own-1" and own.gains[0] == 6
    assert e.output("dac").sel == "own-1"
    e = e.choose("hdmi", "own-1")
    e = e.rename("own-1", "Late evening")
    assert e.name_of("own-1") == "Late evening"
    e = e.set_band("dac", 1, 0)
    assert e.output("dac").source == "own-1"
    e = e.delete("own-1")
    assert e.own == ()
    assert e.output("hdmi").sel == "flat" and e.output("hdmi").gains == eq.FLAT, "back to Flat"
    assert e.output("dac").sel == "custom" and e.output("dac").source is None, "Custom keeps its bands"


def test_names_are_needed_and_unique():
    e, _ = Equaliser().save_as("dac", "Mine")
    for bad in ("", "   ", "mine", "Rock", "x" * 41, 7):
        with pytest.raises(EqualiserError):
            e.save_as("dac", bad)


def test_ten_at_most():
    e = Equaliser()
    for i in range(10):
        e, _ = e.save_as("dac", f"S{i}")
    with pytest.raises(EqualiserError, match="Ten saved already"):
        e.save_as("dac", "One more")
    e = e.delete("own-3")
    e, own = e.save_as("dac", "Again")
    assert own.key == "own-3", "a free key is reused"


def test_round_trip_through_settings():
    e = Equaliser().set_on("dac", True).choose("dac", "pop").set_band("dac", 9, -4)
    e, _ = e.save_as("hdmi", "Telly")
    back = Equaliser.from_settings(e.to_settings())
    assert back == e


def test_bad_stored_values_are_dropped():
    back = Equaliser.from_settings({
        "outputs": {"dac": {"on": True, "sel": "own-9", "gains": [1] * 10},
                    "hdmi": {"gains": "loud"}},
        "own": [{"key": "own-1", "name": "Ok", "gains": [0] * 10},
                {"key": "own-1", "name": "Twice", "gains": [0] * 10},
                {"key": "bad", "name": "No", "gains": [0] * 10},
                {"name": "No key"}],
    })
    assert [o.name for o in back.own] == ["Ok"]
    assert back.output("dac").sel == "flat" and back.output("dac").gains == eq.FLAT
    assert "hdmi" not in back.outputs
    assert Equaliser.from_settings(None) == Equaliser()


def test_camilla_config():
    c = eq.camilla_config(96000, "S32_LE", 2, eq.PRESET["rock"].gains, "eq_out")
    d = c["devices"]
    assert d["samplerate"] == 96000 and d["chunksize"] == 2048 and d["enable_rate_adjust"] is True
    assert d["capture"] == {"type": "Alsa", "channels": 2, "device": "hw:Loopback,1,0",
                            "format": "S32_LE", "stop_on_inactive": True}
    assert d["playback"]["device"] == "eq_out"
    names = c["pipeline"][0]["names"]
    assert names[0] == "headroom" and len(names) == 11, "every band in the pipeline, 0 dB ones too"
    assert c["filters"]["headroom"]["parameters"]["fader"] == "Aux1"
    band = c["filters"]["band_1k"]["parameters"]
    assert band == {"type": "Peaking", "freq": 1000, "gain": -1, "q": math.sqrt(2)}
    assert eq.camilla_config(44100, "S24_3LE", 2, eq.FLAT, "x")["devices"]["capture"]["format"] == "S24_3_LE"
    with pytest.raises(EqualiserError):
        eq.camilla_config(44100, "DSD_U32_BE", 2, eq.FLAT, "x")


def test_camilladsps_hold_is_two_chunks_at_every_rate():
    """ADR-0166 D7 as amended: the chunk it fills, and its target level (the
    chunk size by default) left in the card's buffer."""
    from gexis_core import equaliser as eq
    for rate in (44100, 88200, 176400):
        assert round(eq.latency_ms(rate), 1) == 46.4
    for rate in (48000, 96000, 192000):
        assert round(eq.latency_ms(rate), 1) == 42.7
    # The chunk stays at 4096 above 192 kHz, so it holds half as long.
    assert round(eq.latency_ms(352800), 1) == 23.2 and round(eq.latency_ms(384000), 1) == 21.3


# ---- ADR-0175: room correction's cuts in the same stage ---------------------------


def test_room_slots_are_fourteen_for_each_speaker_the_rest_idle():
    """Eight for the bass's cuts, six for the broad corrections above it
    (ADR-0177 item 6)."""
    slots = eq.room_slots([(42.1, -4.1, 8.6), (86.2, -8.4, 5.7)])
    assert len(slots) == eq.ROOM_SLOTS + eq.ABOVE_SLOTS == 14
    assert slots[:2] == ((42.1, -4.1, 8.6), (86.2, -8.4, 5.7))
    assert slots[2:] == (eq.ROOM_IDLE,) * 12
    assert eq.room_slots([(50, 3, 2)])[0] == (50.0, 0.0, 2.0), "never a boost in the bass (decision 2)"
    assert len(eq.room_slots([(50, -1, 2)] * 12)) == 14
    above = eq.room_slots([], [(480, 2.5, 1.4), (1800, -3, 0.8), (6000, 5, 1)])
    assert above[:8] == (eq.ROOM_IDLE,) * 8
    assert above[8:11] == ((480.0, 2.5, 1.4), (1800.0, -3.0, 0.8), (6000.0, 3.0, 1.0)), "±3 dB at most above"
    assert eq.room_stage(None) == ((eq.ROOM_IDLE,) * 14, (eq.ROOM_IDLE,) * 14)
    play = eq.RoomPlay(([(42, -4, 8.6)], []), ([], [(480, 2, 1.4)]), None)
    left, right = eq.room_stage(play)
    assert left[0] == (42.0, -4.0, 8.6) and right[8] == (480.0, 2.0, 1.4)
    assert eq.room_stage((left, right)) == (left, right), "the slots again are the same slots"


def test_room_cuts_follow_the_bands_one_step_for_each_speaker():
    c = eq.camilla_config(48000, "S32_LE", 2, eq.FLAT, "eq_out", room=([(42, -4, 8.6)], [(87, -8, 5.7)]))
    steps = c["pipeline"]
    assert steps[0]["names"][0] == "headroom" and "channels" not in steps[0]
    assert steps[1] == {"type": "Filter", "channels": [0], "names": [f"room_l_{i}" for i in range(1, 15)]}
    assert steps[2] == {"type": "Filter", "channels": [1], "names": [f"room_r_{i}" for i in range(1, 15)]}
    assert c["filters"]["room_l_1"]["parameters"] == {"type": "Peaking", "freq": 42.0, "gain": -4.0, "q": 8.6}
    assert c["filters"]["room_r_1"]["parameters"]["freq"] == 87.0
    assert c["filters"]["room_r_2"]["parameters"]["gain"] == 0.0


def test_room_slots_are_there_with_nothing_measured():
    """The pipeline's shape is the same with or without a correction, so
    switching it is a change of gains."""
    c = eq.camilla_config(44100, "S16_LE", 2, eq.FLAT, "x")
    assert len(c["pipeline"]) == 3
    assert all(c["filters"][f"room_{s}_{i}"]["parameters"]["gain"] == 0 for s in "lr" for i in range(1, 15))


def test_the_rooms_raises_join_the_headroom():
    """ADR-0177 item 7: room correction's filters as measured join the curve
    the signal is lowered by - beside the bands, or alone."""
    lift = (((42.0, -6.0, 5.0), (480.0, 3.0, 1.4)), ((1800.0, 2.0, 1.0),))
    assert eq.headroom_db(eq.FLAT, lift) == 3.0
    assert eq.headroom_db(eq.FLAT, (((42.0, -6.0, 5.0),),)) == 0, "cuts lower nothing"
    rock = eq.PRESET["rock"].gains
    assert eq.headroom_db(rock, lift) >= eq.headroom_db(rock)
    # A raise where the bands cut adds less than where they boost.
    at_boost = eq.headroom_db(rock, (((31.25, 3.0, 1.0),),))
    at_cut = eq.headroom_db(rock, (((700.0, 3.0, 1.0),),))
    assert at_boost > at_cut >= eq.headroom_db(rock)
    assert eq.room_lift(eq.RoomPlay(lift=lift)) == lift
    assert eq.room_lift(None) is None and eq.room_lift(([(42, -4, 8)], [])) is None


def test_a_mono_stream_has_the_left_speakers_cuts_only():
    c = eq.camilla_config(44100, "S16_LE", 1, eq.FLAT, "x", room=([(42, -4, 8)], [(87, -8, 5)]))
    assert [s.get("channels") for s in c["pipeline"]] == [None, [0]]
