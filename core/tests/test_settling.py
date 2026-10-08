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
                                "error": None, "state": "busy"}
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
