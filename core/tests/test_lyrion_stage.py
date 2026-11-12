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


def test_a_new_player_with_an_empty_music_folder_settles(tmp_path, monkeypatch):
    """The review of 1.16.1: part 2 chose the Lyrion server with its Music
    folder, empty on a new player; Lyrion's scan of it ended with no songs
    and left no mark, and Getting ready said *About to read your music* for
    good, its dialog up. Nothing to read is ready, with no music found."""
    from gexis_core import lyrion_folders, personalise, settling
    from gexis_core.__main__ import lyrion_chosen, lyrion_located

    music = tmp_path / "gexis-music"
    (music / "Playlists").mkdir(parents=True)
    monkeypatch.setattr(lyrion_folders, "MUSIC", music)

    class NoShares:
        def points(self):
            return []

    class NoDrives:
        def all(self):
            return []
    values = {"visualiser_skins": True, "lyrion-server.enabled": True,
              "lyrion-server.music_folder": True, "lyrion-server.usb": False}
    recorded = {}

    class Store:
        def value(self, key):
            return values.get(key)

        def set(self, key, value):
            values[key] = value
    personalise.apply(dict(values), Store(), [{"row": "lyrion-server.enabled", "component": "lyrion",
                                               "name": "Lyrion"}],
                      lambda items: recorded.setdefault("items", items), status={})
    path = tmp_path / "settling.json"
    settling.begin(recorded["items"], path, now=0)

    def view(status):
        after = stage(True, True, status, lyrion_located(values.get, NoShares(), NoDrives()),
                      chosen=lyrion_chosen(values.get, NoShares(), NoDrives()))
        return after, settling.view(settling.read(path), {"skins": {"state": "installed"},
                                                          "lyrion": {"state": "installed", "after": after}}, now=60)
    for status in ({"info total songs": 0, "lastscan": 0}, {}):
        after, seen = view(status)
        assert (after["phase"], after["label"], after["first"]) == ("ready", "Ready, no music found", False)
        assert seen["phase"] == "ready"
    (music / "Album").mkdir()
    (music / "Album" / "01.flac").write_bytes(b"fLaC")
    after, seen = view({"info total songs": 0})
    assert after["phase"] == "waiting" and seen["phase"] == "settling", "music to read: Lyrion reads it first"


def test_the_stage_is_worked_out_with_where_music_is_to_be_read():
    import ast
    from pathlib import Path
    main = Path(__file__).resolve().parents[1] / "src" / "gexis_core" / "__main__.py"
    [found] = [ast.unparse(n) for n in ast.walk(ast.parse(main.read_text()))
               if isinstance(n, ast.FunctionDef) and n.name == "_set_lyrion_stage"]
    assert "located = lyrion_located(settings.value, lyrion_shares, lyrion_usb)" in found


def test_a_read_that_ends_with_nothing_found_is_ready():
    """The review of 1.16.1: a network share or USB folder with no music in
    it - Lyrion reads it, finds nothing and leaves no mark - waited on *About
    to read your music* for good. A read seen to start and end with no song,
    or none at all for QUIET_S once it could have started, is ready."""
    from gexis_core.lyrion_stage import QUIET_S, Reads, found_nothing
    clock = [0.0]
    reads = Reads(clock=lambda: clock[0])
    waiting = stage(True, True, {"info total songs": 0}, True)
    assert waiting["phase"] == "waiting" and not reads.nothing_found(waiting["phase"])
    scanning = stage(True, True, {"rescan": 1, "info total songs": 0}, True)
    assert not reads.nothing_found(scanning["phase"])
    clock[0] = 20
    assert reads.nothing_found(waiting["phase"]), "read, and nothing found"
    got = found_nothing(waiting)
    assert (got["phase"], got["label"], got["done"], got["first"]) == ("ready", "Ready, no music found", True, False)
    assert "Lyrion found no music in the folders chosen" in got["line"] and got["addons"] == waiting["addons"]

    quiet = Reads(clock=lambda: clock[0])
    clock[0] = 100
    assert not quiet.nothing_found("waiting")
    clock[0] = 100 + QUIET_S - 1
    assert not quiet.nothing_found("waiting"), "a read may still start"
    clock[0] = 100 + QUIET_S
    assert quiet.nothing_found("waiting"), "no read in all that time: nothing to read"
    assert not quiet.nothing_found("starting") and not quiet.nothing_found("waiting"), "a restart starts it again"


def test_an_empty_music_folder_alone_is_read_and_found_empty():
    """Chosen, but nothing in it to read: not *Add where your music is*,
    which says to choose what was chosen."""
    got = stage(True, True, {"info total songs": 0}, False, chosen=True)
    assert (got["phase"], got["label"]) == ("ready", "Ready, no music found")
    nothing = stage(True, True, {"info total songs": 0}, False)
    assert (nothing["label"], nothing["line"]) == (
        "Ready, no music yet", "Add where your music is in Settings → Library → Lyrion Server.")


def test_the_core_follows_lyrion_s_reads():
    import ast
    from pathlib import Path
    main = Path(__file__).resolve().parents[1] / "src" / "gexis_core" / "__main__.py"
    [found] = [ast.unparse(n) for n in ast.walk(ast.parse(main.read_text()))
               if isinstance(n, ast.FunctionDef) and n.name == "_set_lyrion_stage"]
    assert "chosen=lyrion_chosen(settings.value, lyrion_shares, lyrion_usb)" in found
    assert "status is not None and lyrion_reads.nothing_found(now_stage['phase'])" in found
    assert found.index("lyrion_reads.nothing_found") < found.index("if status is None and")
