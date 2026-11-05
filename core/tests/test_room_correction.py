"""Room correction as the player keeps it (ADR-0175): each output's switch,
*Hear it without* and last measurement, and the microphones' calibrations."""
import pytest

from gexis_core import room_correction as rc
from gexis_core.room_correction import Measurement, Room, RoomError, Speaker

N = 122   # room_dsp.GRID's length


def speaker(cuts=((42.0, -4.0, 8.6), (86.0, -8.0, 5.7))):
    flat = tuple(0.0 for _ in range(N))
    return Speaker(cuts=cuts, before=tuple(3.0 if 80 < f < 95 else 0.0 for f in rc.grid(N)), target=flat,
                   after=flat, positions=(flat,) * 5)


def measurement(checked=True, cuts=((42.0, -4.0, 8.6), (86.0, -8.0, 5.7))):
    return Measurement("2026-11-05", checked, {"L": speaker(cuts), "R": speaker(cuts)})


CAL = """"Sens Factor =-1.378dB, AGain =18dB, SERNO: 7071234"
10.054	-2.4562
""" + "\n".join(f"{10 * 1.02 ** k:.3f}\t{-0.01 * k:.4f}" for k in range(1, 400)) + "\n"


def test_never_measured_it_cannot_be_switched_on():
    with pytest.raises(RoomError, match="Measure first"):
        Room().set_on("DAC", True)


def test_keep_switches_it_on_and_compares_from_the_start():
    room = Room().keep("DAC", measurement()).set_without("DAC", True)
    room = room.keep("DAC", measurement())
    assert room.output("DAC").on and not room.output("DAC").without


def test_nothing_to_cut_stays_off():
    room = Room().keep("DAC", measurement(cuts=()))
    assert not room.output("DAC").on
    with pytest.raises(RoomError):
        room.set_on("DAC", True)


def test_without_only_while_on():
    room = Room().keep("DAC", measurement()).set_on("DAC", False)
    with pytest.raises(RoomError, match="Only while"):
        room.set_without("DAC", True)


def test_the_stage_gets_the_cuts_or_nothing():
    room = Room().keep("DAC", measurement())
    left, right = room.stage("DAC")
    assert left == ((42.0, -4.0, 8.6), (86.0, -8.0, 5.7))
    assert room.in_path("DAC")
    without = room.set_without("DAC", True)
    assert without.stage("DAC")[0] == ((42.0, 0.0, 8.6), (86.0, 0.0, 5.7)), "the cuts at 0 dB"
    assert without.in_path("DAC"), "Without keeps the stage in the path"
    off = room.set_on("DAC", False)
    assert off.stage("DAC") is None and not off.in_path("DAC")
    assert Room().stage("HDMI") is None, "each output its own"


def test_stored_and_read_back():
    room = Room().keep("DAC", measurement(checked=False)).set_without("DAC", True)
    cal = rc.parse_calibration(CAL, "7071234", "2026-11-05")
    room = room.with_calibration(cal)
    again = Room.from_settings(room.to_settings())
    assert again.output("DAC").on and again.output("DAC").without
    assert again.output("DAC").measured.checked is False
    assert again.output("DAC").measured.cuts("R") == ((42.0, -4.0, 8.6), (86.0, -8.0, 5.7))
    assert again.microphones["7071234"].sens_db == -1.378


@pytest.mark.parametrize("bad", [None, "x", [], {"outputs": "x"}, {"outputs": {"DAC": {"on": True}}},
                                 {"outputs": {"DAC": {"on": True, "measured": {"date": "soon"}}}},
                                 {"microphones": {"7071234": {"serial": "7071234"}}}])
def test_read_leniently(bad):
    room = Room.from_settings(bad)
    assert not room.output("DAC").on and room.microphones == {}


def test_a_boost_in_the_store_is_dropped():
    stored = Room().keep("DAC", measurement()).to_settings()
    stored["outputs"]["DAC"]["measured"]["speakers"]["L"]["cuts"].append({"freq": 50, "gain": 3, "q": 2})
    assert len(Room.from_settings(stored).output("DAC").measured.cuts("L")) == 2


def test_a_calibration_file_is_read():
    cal = rc.parse_calibration(CAL, "7071234", "2026-11-05")
    assert cal.sens_db == -1.378 and cal.points[0] == (10.054, -2.4562)
    assert cal.points[-1][0] <= rc.KEEP_UP_TO
    assert cal.db_at(10.054) == -2.4562
    assert cal.db_at(5) == -2.4562 and cal.db_at(50000) == cal.points[-1][1], "held at its ends"


@pytest.mark.parametrize("text", ["<html><body>Not found</body></html>", "", "10 1\n20 2\n",
                                  '"Sens Factor =-1.3dB, SERNO: 7071234"\n100 1\n50 2\n'])
def test_anything_else_is_refused(text):
    with pytest.raises(RoomError, match="not a calibration file"):
        rc.parse_calibration(text, "7071234", "2026-11-05")


def test_a_file_for_another_microphone_is_refused():
    with pytest.raises(RoomError, match="for 707-1234, not 707-1235"):
        rc.parse_calibration(CAL, "7071235", "2026-11-05")


def test_the_serial_as_typed():
    assert rc.clean_serial(" 707-1234 ") == "7071234"
    assert rc.shown_serial("7071234") == "707-1234"
    for bad in ("70-1234", "abc", "", None, "707-12345"):
        with pytest.raises(RoomError):
            rc.clean_serial(bad)


def test_the_chart_up_to_300_hz():
    c = rc.chart(measurement(checked=False))
    assert c["freqs"][0] == 15 and max(c["freqs"]) <= 300 < max(rc.grid(N))
    assert len(c["speakers"]["L"]["before"]) == len(c["freqs"])
    assert len(c["speakers"]["L"]["positions"]) == 5
    assert c["after_kind"] == "expected", "not checked"
    assert rc.chart(measurement())["after_kind"] == "measured"
    assert c["speakers"]["L"]["cuts"] == [{"freq": 42, "gain": -4.0}, {"freq": 86, "gain": -8.0}]
    assert c["speakers"]["L"]["peaks_down"] == 3
    assert rc.chart(None) is None
