"""ADR-0128: the first start after setup, until the player has settled."""
from __future__ import annotations

from gexis_core import settling

ITEMS = [{"id": "skins", "name": "The visualiser's skins"}, {"id": "plexamp", "name": "Plexamp"}]


def record(started=1000.0):
    return {"started": started, "items": ITEMS}


def test_it_settles_while_anything_waits_or_downloads():
    view = settling.view(record(), {"skins": {"state": "downloading", "received": 5, "total": 10}}, now=1010.0)
    assert view["phase"] == "settling"
    assert view["items"][0] == {"id": "skins", "name": "The visualiser's skins", "received": 5, "total": 10,
                                "share": None, "error": None, "state": "busy", "step": "downloading"}
    assert view["items"][1]["state"] == "waiting"


def test_ready_when_everything_finished():
    view = settling.view(record(), {"skins": {"state": "installed"}, "plexamp": {"state": "installed"}}, now=1010.0)
    assert view["phase"] == "ready" and {i["state"] for i in view["items"]} == {"done"}


def test_a_failed_download_is_named_once_the_rest_are_done():
    """George: "Leave it for settings but inform user"."""
    status = {"skins": {"state": "installed"}, "plexamp": {"state": "failed", "error": "Plex did not answer"}}
    view = settling.view(record(), status, now=1010.0)
    assert view["phase"] == "failed"
    assert view["items"][1]["state"] == "failed" and view["items"][1]["error"] == "Plex did not answer"


def test_a_download_that_never_starts_fails_after_the_wait():
    """No home network: the screen must still be able to finish."""
    view = settling.view(record(), {"skins": {"state": "installed"}}, now=1000.0 + settling.WAIT_S + 1)
    assert view["phase"] == "failed" and view["items"][1]["error"] == "The download did not start"


def test_begin_read_end(tmp_path):
    path = tmp_path / "settling.json"
    settling.begin([], path)
    assert settling.read(path) is None, "nothing to wait for writes nothing"
    settling.begin(ITEMS, path, now=5.0)
    assert settling.read(path)["items"] == ITEMS
    settling.end(path)
    assert settling.read(path) is None


def test_a_skin_pack_s_share_reaches_the_screen():
    """George's bar player, 2026-10-09: the skins showed no progress, then
    were done - a pack reports a share, and only bytes were passed on."""
    record = {"started": 0, "items": [{"id": "skins", "name": "The visualiser's skins"}]}
    v = settling.view(record, {"skins": {"state": "downloading", "share": 0.42}}, now=1)
    assert v["items"][0]["state"] == "busy" and v["items"][0]["share"] == 0.42


def test_put_away_it_follows_on_and_comes_back_only_for_a_failure(tmp_path):
    """ADR-0128 amended 2026-10-10: the owner can put the screen away at once;
    the downloads go on, and a failure brings it back to be told."""
    path = tmp_path / "settling.json"
    settling.begin([{"id": "skins", "name": "Visualiser skins"}], path, now=0)
    assert settling.view(settling.read(path), {}, now=1)["hidden"] is False
    settling.hide(path)
    busy = settling.view(settling.read(path), {"skins": {"state": "downloading"}}, now=2)
    assert busy["phase"] == "settling" and busy["hidden"] is True
    failed = settling.view(settling.read(path), {"skins": {"state": "failed", "error": "x"}}, now=3)
    assert failed["phase"] == "failed" and failed["hidden"] is False
    settling.end(path)
    settling.hide(path)                      # nothing to put away: writes nothing
    assert not path.exists()


def test_a_pack_being_installed_says_so_rather_than_100_percent():
    """George, 2026-10-11: the skins showed 100 % for the 4 min 18 s their
    install took on the bar. The step goes to the screen, which says
    Installing."""
    v = settling.view(record(), {"skins": {"state": "installing", "share": 1.0}}, now=1010.0)
    assert v["items"][0]["state"] == "busy" and v["items"][0]["step"] == "installing"


LYRION = [{"id": "lyrion", "name": "Lyrion Server", "follow": True}]


def test_lyrion_is_followed_past_its_download_until_it_has_read_the_music():
    """ADR-0149 decision 43 (George, 2026-10-19: the plate "was showing
    something getting ready and then the next minute the library was there in
    full"): installed is the first of Lyrion's steps, not the last."""
    rec = {"started": 1000.0, "items": LYRION}
    adding = {"lyrion": {"state": "installed", "after": {"phase": "addons", "label": "Adding its add-ons",
                                                         "line": "Lyrion fetches ...", "addons": [
                                                             {"name": "Material Skin", "in": True},
                                                             {"name": "Radio Now Playing", "in": False}]}}}
    view = settling.view(rec, adding, now=1010.0)
    item = view["items"][0]
    assert view["phase"] == "settling"
    assert (item["state"], item["step"], item["label"]) == ("busy", "after", "Adding its add-ons")
    assert [s[1] for s in item["steps"]] == ["done", "done", "now", "next", "next"]
    assert item["steps"][2][0] == "Add Material Skin ✓, Radio Now Playing · one restart, about 3 minutes"

    reading = {"lyrion": {"state": "installed", "after": {"phase": "scanning", "label": "Reading your music",
                                                          "share": 0.42, "line": "..."}}}
    item = settling.view(rec, reading, now=1010.0)["items"][0]
    assert item["share"] == 0.42 and item["steps"][3] == ["Read your music · 42 %", "now"]

    # Just installed, before the core has read Lyrion once: starting, not done.
    item = settling.view(rec, {"lyrion": {"state": "installed"}}, now=1010.0)["items"][0]
    assert (item["state"], item["label"]) == ("busy", "Starting")

    read = {"lyrion": {"state": "installed", "after": {"phase": "ready", "label": "Ready",
                                                       "line": "760 songs on 47 albums in the library."}}}
    view = settling.view(rec, read, now=1010.0)
    assert view["phase"] == "ready" and view["items"][0]["state"] == "done"
    assert view["items"][0]["steps"][4] == ["Ready · 760 songs on 47 albums in the library.", "done"]


def test_while_lyrion_downloads_its_steps_say_so():
    steps = settling.lyrion_steps({"state": "downloading", "received": 30, "total": 120})
    assert steps[0] == ["Download Lyrion · 25 %", "now"] and {s[1] for s in steps[1:]} == {"next"}
    assert settling.lyrion_steps({"state": "failed"})[0][0] == "Download Lyrion · did not finish"


def test_the_downloads_are_in_while_lyrion_still_reads():
    """Decision 37's restart waits for the downloads, never for the read."""
    rec = {"started": 1000.0, "items": [{"id": "skins", "name": "Skins"}, *LYRION]}
    reading = {"state": "installed", "after": {"phase": "scanning", "label": "Reading your music", "share": 0.1}}
    assert not settling.downloads_in(settling.view(rec, {"skins": {"state": "installing"}, "lyrion": reading}, now=1010.0))
    assert settling.downloads_in(settling.view(rec, {"skins": {"state": "installed"}, "lyrion": reading}, now=1010.0))
    assert settling.downloads_in(None)
