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
