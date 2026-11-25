# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR-0189: the history's files - ids, order, what does not read."""
import datetime

from gexis_core import room_correction as rc
from gexis_core.room_history import History


def _m(date="2026-11-25"):
    return rc.Measurement(date, True, {"L": rc.Speaker(), "R": rc.Speaker()})


def test_entries_are_newest_first_and_name_their_time_and_kind(tmp_path):
    at = iter([datetime.datetime(2026, 11, 25, 11, 42, 57), datetime.datetime(2026, 11, 25, 12, 0, 1)])
    h = History(tmp_path, now=lambda: next(at))
    first = h.add_measurement("AUDIO", _m())
    second = h.add_speakers("AUDIO", rc.Alignment(date="2026-11-25", delay=(0.13, 0.0)))
    assert first == "20261125-114257-room" and second == "20261125-120001-speakers"
    got = h.entries("AUDIO")
    assert [e.id for e in got] == [second, first] and got[1].time == "11:42"
    assert got[0].alignment.delay == (0.13, 0.0) and got[1].measurement.date == "2026-11-25"
    assert h.entries("other") == []


def test_two_in_one_second_both_kept(tmp_path):
    now = datetime.datetime(2026, 11, 25, 11, 0, 0)
    h = History(tmp_path, now=lambda: now)
    assert h.add_measurement("AUDIO", _m()) != h.add_measurement("AUDIO", _m())
    assert len(h.entries("AUDIO")) == 2


def test_a_file_that_does_not_read_is_passed_over_and_ids_are_checked(tmp_path):
    h = History(tmp_path)
    kept = h.add_measurement("AUDIO", _m())
    (tmp_path / "AUDIO" / "20261125-000000-room.json").write_text("{not json")
    assert [e.id for e in h.entries("AUDIO")] == [kept]
    for bad in ("../AUDIO/" + kept, kept + "/..", "x", "", None):
        assert h.get("AUDIO", bad) is None
    assert h.get("AUDIO", kept).measurement is not None


def test_a_measurement_from_before_is_dated_by_itself(tmp_path):
    h = History(tmp_path, now=lambda: datetime.datetime(2026, 11, 30, 9, 0))
    got = h.get("AUDIO", h.seed("AUDIO", _m("2026-11-03")))
    assert got.date == "2026-11-03" and got.time is None


def test_a_card_name_never_leaves_the_folder(tmp_path):
    h = History(tmp_path)
    h.add_measurement("../../x", _m())
    assert all(p.resolve().is_relative_to(tmp_path.resolve()) for p in tmp_path.rglob("*"))


def test_unwritable_is_logged_not_fatal(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("")
    assert History(blocker).add_measurement("AUDIO", _m()) is None
