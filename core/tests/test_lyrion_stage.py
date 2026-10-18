"""ADR-0115 decision 28: what the Lyrion server is doing after its download,
in the order sofapi went through it on 2026-10-18."""

from gexis_core.lyrion_stage import stage


def test_starting_then_add_ons_then_waiting_none_of_them_done():
    assert stage(False, False, None, True)["phase"] == "starting"
    assert "first start" not in stage(False, True, None, True)["line"], "after a reboot it is not the first"
    addons = stage(True, False, {"info total songs": 0}, True)
    assert addons["phase"] == "addons" and "3 minutes" in addons["line"] and not addons["done"]
    assert all(name in addons["line"] for name in ("Material Skin", "Music & Artist Information", "Radio Now Playing"))
    assert stage(True, True, {"info total songs": 0}, True)["phase"] == "waiting"


def test_reading_counts_the_files_and_lets_the_player_be_used():
    got = stage(True, True, {"rescan": 1, "progressdone": "1234", "progresstotal": "5000",
                             "progressname": "/mnt/gexis-shares/x|audio_new"}, True)
    assert got["phase"] == "scanning" and got["done"] and abs(got["share"] - 0.2468) < 1e-6
    assert got["line"].startswith("1,234 of 5,000 new files read so far.")
    art = stage(True, True, {"rescan": 1, "progressdone": 37, "progresstotal": 46, "progressname": "precacheArtwork"}, True)
    assert art["line"].startswith("37 of 46 albums' artwork so far."), "measured on sofapi: not files"
    assert stage(True, True, {"rescan": 1}, True)["share"] is None


def test_ready_says_what_is_in_the_library_or_that_nothing_is():
    assert stage(True, True, {"info total songs": 760, "info total albums": 47}, True)["line"] == \
        "760 songs on 47 albums in the library."
    empty = stage(True, True, {"info total songs": 0}, False)
    assert empty["phase"] == "ready" and "Settings" in empty["line"]
