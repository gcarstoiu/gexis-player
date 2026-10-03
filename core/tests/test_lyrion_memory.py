"""ADR-0115 decision 18: the Lyrion server and the player's memory."""
from __future__ import annotations

from gexis_core import lyrion_memory as lm


def test_a_1_gb_player_is_not_offered_the_server_and_2_gb_is(tmp_path):
    info = tmp_path / "meminfo"
    info.write_text("MemTotal:         925000 kB\nMemFree: 1 kB\n")
    assert lm.too_small(lm.total_mb(info)) == \
        "This player has 0.9 GB of memory. The Lyrion server needs a player with 2 GB or more."
    info.write_text("MemTotal:        1873000 kB\n")
    assert lm.too_small(lm.total_mb(info)) is None
    assert lm.too_small(None) is None, "unreadable: not refused on a guess"


def test_files_that_fit_follow_the_measured_cost():
    """Finding 109: 61,362 files took 1,876 MB on High and 1,191 MB on
    Normal; a 4 GB Pi's 2.7 GB fits them on either, with room."""
    assert 61_362 < lm.files_that_fit(2771, highmem=1) < 120_000
    assert lm.files_that_fit(2771, highmem=0) > 2 * 80_000
    assert lm.files_that_fit(800) == 15_000
    assert lm.files_that_fit(100) == 0


def _events(cg, kills):
    cg.mkdir(exist_ok=True)
    (cg / "memory.events").write_text(f"low 0\nhigh 0\nmax 12\noom 1\noom_kill {kills}\n")
    (cg / "memory.max").write_text(str(1024 * 1048576) + "\n")


def test_a_scan_stopped_for_memory_is_said_until_one_finishes(tmp_path):
    cg, stopped = tmp_path / "cg", tmp_path / "stopped.json"
    watch = lm.Watch(stopped, cg)
    _events(cg, 0)
    assert watch.update(scanning=True) is False
    _events(cg, 1)
    assert watch.update(scanning=True, highmem=1) is True
    note = lm.stopped_note(stopped)
    assert "too large for this player's memory" in note and "About 24,000 files fit." in note
    assert "Set Database Memory Config to Normal" in note and "about 49,000 fit" in note, \
        "George: on High, Normal is the way to a larger library"
    assert watch.update(scanning=False) is False, "this scan was the one stopped: still said"
    assert watch.update(scanning=True) is False
    assert watch.update(scanning=False) is True, "the next one finished without a stop"
    assert lm.stopped_note(stopped) is None


def test_a_restart_of_the_server_is_not_read_as_a_stop(tmp_path):
    cg, stopped = tmp_path / "cg", tmp_path / "stopped.json"
    watch = lm.Watch(stopped, cg)
    _events(cg, 3)
    watch.update(scanning=False)
    _events(cg, 0)
    assert watch.update(scanning=False) is False and not stopped.exists()


def test_on_normal_the_note_does_not_suggest_normal(tmp_path):
    stopped = tmp_path / "stopped.json"
    lm.remember_stopped(1024, 0, stopped)
    note = lm.stopped_note(stopped)
    assert "About 49,000 files fit." in note and "Normal" not in note
