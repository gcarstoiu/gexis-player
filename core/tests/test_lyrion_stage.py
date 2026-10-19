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
    got = stage(True, True, {"rescan": 1, "progressdone": "38", "progresstotal": "422",
                             "progressname": "Scanning new music files"}, True)
    assert got["phase"] == "scanning" and got["done"] and abs(got["share"] - 38 / 422) < 1e-6
    assert got["line"].startswith("Scanning new music files: 38 of 422.")
    # Measured on sofapi: discovering reports 1/0 - no count to give.
    disc = stage(True, True, {"rescan": 1, "progressdone": 1, "progresstotal": 0,
                              "progressname": "Discovering files/directories"}, True)
    assert disc["line"].startswith("Discovering files/directories. ") and disc["share"] is None
    assert stage(True, True, {"rescan": 1}, True)["share"] is None


def test_ready_says_what_is_in_the_library_or_that_nothing_is():
    assert stage(True, True, {"info total songs": 760, "info total albums": 47}, True)["line"] == \
        "760 songs on 47 albums in the library."
    empty = stage(True, True, {"info total songs": 0}, False)
    assert empty["phase"] == "ready" and "Settings" in empty["line"]


def test_only_a_first_read_is_first():
    """Finding 127: a rescan keeps the old library, so it is not a first read;
    a reboot's Starting, with the add-ons in, is not either."""
    assert stage(True, False, {}, True)["first"] is True
    assert stage(True, True, {"rescan": 1, "info total songs": 0}, True)["first"] is True
    assert stage(True, True, {"rescan": 1, "info total songs": 760}, True)["first"] is False
    assert stage(False, True, None, True)["first"] is False
    assert stage(True, True, {"info total songs": 760}, True)["first"] is False


def test_one_add_on_that_will_not_install_does_not_hold_the_rest_back():
    """sofapi, 2026-10-19: Radio Now Playing's download failed Lyrion's
    check ("digest does not match"); the checklist stayed on step 3."""
    addons = {"MaterialSkin": True, "MusicArtistInfo": True, "RadioNowPlaying": False}
    got = stage(True, addons, {"rescan": 1, "info total songs": 0, "progressname": "Scanning new music files",
                               "progressdone": 5, "progresstotal": 50}, True)
    assert got["phase"] == "scanning"
    assert [a["in"] for a in got["addons"]] == [True, True, False]
    assert got["addons"][2]["name"] == "Radio Now Playing"
    waiting = stage(True, {"MaterialSkin": False, "MusicArtistInfo": True, "RadioNowPlaying": True}, {}, True)
    assert waiting["phase"] == "addons", "Material Skin is the one a person sees"
