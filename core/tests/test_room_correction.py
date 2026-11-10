"""Room correction as the player keeps it (ADR-0175, ADR-0177): each output's
switch, *Hear it without*, how far it reaches and last measurement, and the
microphones' calibrations."""
import pytest

from gexis_core import room_correction as rc
from gexis_core.room_correction import Measurement, Room, RoomError, Speaker

N = 250   # room_dsp.GRID's length


ABOVE = ((480.0, 2.5, 1.4), (1800.0, -3.0, 0.8))


def speaker(cuts=((42.0, -4.0, 8.6), (86.0, -8.0, 5.7)), above=ABOVE):
    flat = tuple(0.0 for _ in range(N))
    return Speaker(cuts=cuts, before=tuple(3.0 if 80 < f < 95 else 0.0 for f in rc.grid(N)), target=flat,
                   after=flat, positions=(flat,) * 5, above=above, after_bass=flat, within=1.0, room_within=3.5)


def test_both_speakers_are_kept_and_an_older_measurement_reads_without():
    flat = tuple([0.0] * N)
    both = rc.Speaker(before=flat, target=flat, positions=(flat,) * 3)
    m = rc.Measurement("2026-11-05", False, {"L": speaker(), "R": speaker(), rc.BOTH: both}, 3)
    again = rc.Measurement.from_dict(m.as_dict())
    assert again.speakers[rc.BOTH].after == () and again.speakers[rc.BOTH].cuts == ()
    assert again.positions == 3 and not again.nothing_to_cut
    older = m.as_dict()
    del older["speakers"][rc.BOTH]
    assert rc.BOTH not in rc.Measurement.from_dict(older).speakers


def measurement(checked=True, cuts=((42.0, -4.0, 8.6), (86.0, -8.0, 5.7)), above=ABOVE):
    return Measurement("2026-11-05", checked, {"L": speaker(cuts, above), "R": speaker(cuts, above)})


def bass_only():
    """A measurement kept before Phase 30: curves to 500 Hz, no range."""
    stored = measurement(above=()).as_dict()
    del stored["range"]
    for sp in stored["speakers"].values():
        for k in ("before", "target", "after"):
            sp[k] = sp[k][:122]
        sp["positions"] = [p[:122] for p in sp["positions"]]
        for k in ("above", "after_bass", "within", "room_within"):
            sp.pop(k, None)
    return Measurement.from_dict(stored)


CAL = """"Sens Factor =-1.378dB, AGain =18dB, SERNO: 7071234"
"Auto-generated 90-degree calibration file"
10.054	-2.4562
""" + "\n".join(f"{10 * 1.02 ** k:.3f}\t{-0.01 * k:.4f}" for k in range(1, 400)) + "\n"


def test_never_measured_it_cannot_be_switched_on():
    with pytest.raises(RoomError, match="Measure first"):
        Room().set_on("DAC", True)


def test_keep_switches_it_on_and_compares_from_the_start():
    room = Room().keep("DAC", measurement()).set_without("DAC", True)
    room = room.keep("DAC", measurement())
    assert room.output("DAC").on and not room.output("DAC").without


def test_nothing_to_correct_stays_off():
    room = Room().keep("DAC", measurement(cuts=(), above=()))
    assert not room.output("DAC").on
    with pytest.raises(RoomError):
        room.set_on("DAC", True)


def test_nothing_to_cut_in_the_bass_is_still_on_for_above_it():
    room = Room().keep("DAC", measurement(cuts=()))
    assert room.output("DAC").on and room.output("DAC").measured.nothing_to_cut
    assert not room.output("DAC").measured.nothing_to_correct


def test_without_only_while_on():
    room = Room().keep("DAC", measurement()).set_on("DAC", False)
    with pytest.raises(RoomError, match="Only while"):
        room.set_without("DAC", True)


def test_the_stage_gets_the_corrections_or_nothing():
    room = Room().keep("DAC", measurement())
    play = room.stage("DAC")
    assert play.cuts[0] == ((42.0, -4.0, 8.6), (86.0, -8.0, 5.7))
    assert play.above[1] == ABOVE, "a new measurement starts at the full range"
    assert room.in_path("DAC")
    without = room.set_without("DAC", True).stage("DAC")
    assert without.cuts[0] == ((42.0, 0.0, 8.6), (86.0, 0.0, 5.7)), "the cuts at 0 dB"
    assert without.above[0] == ((480.0, 0.0, 1.4), (1800.0, 0.0, 0.8)), "and the broad ones"
    assert room.set_without("DAC", True).in_path("DAC"), "Without keeps the stage in the path"
    bass = room.set_reach("DAC", rc.BASS).stage("DAC")
    assert bass.cuts == play.cuts and bass.above[0] == ((480.0, 0.0, 1.4), (1800.0, 0.0, 0.8))
    lift = ((42.0, -4.0, 8.6), (86.0, -8.0, 5.7)) + ABOVE
    assert play.lift == bass.lift == without.lift == (lift, lift), "one headroom whatever plays"
    off = room.set_on("DAC", False)
    assert off.stage("DAC") is None and not off.in_path("DAC") and off.lift("DAC") is None
    assert Room().stage("HDMI") is None, "each output its own"


def test_the_reach_is_saved_and_needs_it_on():
    room = Room().keep("DAC", measurement()).set_reach("DAC", rc.BASS)
    again = Room.from_settings(room.to_settings())
    assert again.output("DAC").reach == rc.BASS
    assert Room.from_settings(again.set_reach("DAC", rc.FULL).to_settings()).output("DAC").reach == rc.FULL
    with pytest.raises(RoomError, match="Only while"):
        room.set_on("DAC", False).set_reach("DAC", rc.FULL)
    with pytest.raises(RoomError):
        room.set_reach("DAC", "treble")


def test_a_measurement_from_before_is_held_at_the_bass():
    """ADR-0177 item 9: one kept by Phase 29 says no range; it is the
    bass's, and Full range waits for the room measured again."""
    old = bass_only()
    assert old.range == rc.BASS and old.above("L") == () and len(old.speakers["L"].before) == 122
    stored = Room().keep("DAC", measurement()).to_settings()
    stored["outputs"]["DAC"]["measured"] = old.as_dict()
    del stored["outputs"]["DAC"]["measured"]["range"]
    stored["outputs"]["DAC"].pop("reach")
    room = Room.from_settings(stored)
    assert room.output("DAC").on and room.output("DAC").reach == rc.BASS
    with pytest.raises(RoomError, match="covers the bass only"):
        room.set_reach("DAC", rc.FULL)
    assert room.stage("DAC").above == ((), ())
    assert room.keep("DAC", measurement()).output("DAC").reach == rc.FULL, "measured again, full"
    stored["outputs"]["DAC"]["reach"] = rc.FULL
    assert Room.from_settings(stored).output("DAC").reach == rc.BASS, "a full reach stored over it ignored"


def test_stored_and_read_back():
    room = Room().keep("DAC", measurement(checked=False)).set_without("DAC", True)
    cal = rc.parse_calibration(CAL, "2026-11-05")
    room = room.with_calibration(cal)
    again = Room.from_settings(room.to_settings())
    assert again.output("DAC").on and again.output("DAC").without
    assert again.output("DAC").measured.checked is False
    assert again.output("DAC").measured.cuts("R") == ((42.0, -4.0, 8.6), (86.0, -8.0, 5.7))
    assert again.microphones["7071234"].sens_db == -1.378
    assert again.calibration().serial == "7071234" and again.calibration().gain_db == 18


@pytest.mark.parametrize("bad", [None, "x", [], {"outputs": "x"}, {"outputs": {"DAC": {"on": True}}},
                                 {"outputs": {"DAC": {"on": True, "measured": {"date": "soon"}}}},
                                 {"microphones": {"7071234": {"serial": "7071234"}}}])
def test_read_leniently(bad):
    room = Room.from_settings(bad)
    assert not room.output("DAC").on and room.microphones == {}


def test_a_boost_in_the_store_is_dropped():
    stored = Room().keep("DAC", measurement()).to_settings()
    stored["outputs"]["DAC"]["measured"]["speakers"]["L"]["cuts"].append({"freq": 50, "gain": 3, "q": 2})
    stored["outputs"]["DAC"]["measured"]["speakers"]["L"]["above"].append({"freq": 5000, "gain": 4, "q": 1})
    m = Room.from_settings(stored).output("DAC").measured
    assert len(m.cuts("L")) == 2 and m.above("L") == ABOVE, "cuts only in the bass, ±3 dB above"


def test_a_calibration_file_is_read():
    cal = rc.parse_calibration(CAL, "2026-11-05", "7071234_90deg.txt")
    assert cal.serial == "7071234" and cal.gain_db == 18 and cal.angle == 90
    assert cal.sens_db == -1.378 and cal.points[0] == (10.054, -2.4562)
    assert cal.points[-1][0] > 20000 and cal.full, "the whole file kept"
    assert cal.db_at(10.054) == -2.4562
    assert cal.db_at(5) == -2.4562 and cal.db_at(50000) == cal.points[-1][1], "held at its ends"


@pytest.mark.parametrize("text", ["<p style=\"color:red;\">Unable to locate calibration data.</p>", "",
                                  "10 1\n20 2\n", '"Sens Factor =-1.3dB, SERNO: 7071234"\n100 1\n50 2\n'])
def test_anything_else_is_refused(text):
    with pytest.raises(RoomError, match="not a calibration file"):
        rc.parse_calibration(text, "2026-11-05")


def test_the_0_degree_file_is_refused():
    zero = CAL.replace('"Auto-generated 90-degree calibration file"\n', "")
    with pytest.raises(RoomError, match="0° file"):
        rc.parse_calibration(zero, "2026-11-05", "7071234.txt")
    assert rc.parse_calibration(zero, "2026-11-05", "7071234_90deg.txt").angle == 90, "named as one"


def test_a_file_that_stops_short_of_the_treble_is_refused():
    short = "\n".join(line for line in CAL.splitlines() if not line[:1].isdigit() or float(line.split()[0]) < 10000)
    with pytest.raises(RoomError, match="not a calibration file"):
        rc.parse_calibration(short, "2026-11-05", "7071234_90deg.txt")


def test_a_calibration_kept_to_2_khz_is_not_for_the_full_range():
    """Phase 29 kept the files to 2 kHz; Phase 30 measures to 20 kHz."""
    kept = rc.parse_calibration(CAL, "2026-11-05", "7071234_90deg.txt").as_dict()
    kept["points"] = [p for p in kept["points"] if p[0] <= 2000]
    assert not rc.Calibration.from_dict(kept).full


def test_a_file_that_names_no_microphone_is_refused():
    with pytest.raises(RoomError, match="which microphone"):
        rc.parse_calibration(CAL.replace(", SERNO: 7071234", ""), "2026-11-05")


def test_the_serial_as_the_label_prints_it():
    assert rc.shown_serial("7071234") == "707-1234"


def test_the_chart_over_the_whole_range():
    c = rc.chart(measurement(checked=False))
    assert c["freqs"][0] == 15 and c["freqs"][-1] > 19000 and len(c["freqs"]) == N and c["range"] == rc.FULL
    sp = c["speakers"]["L"]
    assert len(sp["before"]) == len(sp["after_bass"]) == len(c["freqs"])
    assert len(sp["positions"]) == 5
    assert c["after_kind"] == "expected", "not checked"
    assert rc.chart(measurement())["after_kind"] == "measured"
    assert sp["cuts"] == [{"freq": 42, "gain": -4.0}, {"freq": 86, "gain": -8.0}]
    assert sp["above"] == [{"freq": 480, "gain": 2.5}, {"freq": 1800, "gain": -3.0}]
    assert sp["peaks_down"] == 3 and sp["within"] == 1.0 and sp["room_within"] == 3.5
    assert rc.chart(None) is None


def test_the_chart_of_a_measurement_from_before():
    c = rc.chart(bass_only())
    assert c["range"] == rc.BASS and c["freqs"][-1] < 520 and c["speakers"]["L"]["above"] == []
    assert c["speakers"]["L"]["after_bass"] == c["speakers"]["L"]["after"]
    assert c["speakers"]["L"]["within"] is None
