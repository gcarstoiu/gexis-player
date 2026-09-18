"""Phase 7 step 9: the radio subtree (ADR-0038 §5, §8).

The SlimBrowse replies here are made up, but their *shapes* are the ones
Finding 029 §6 recorded against LMS 9.1.1: folder items carry their own
`actions.go`; station items carry none at all and lean on the list's
`base.actions` through a `goAction`, and in a station list that inherited
action is `… playlist play`. A walker that treated it as "open this"
started playing a station on George's system, which is what these tests
exist to prevent.
"""
from __future__ import annotations

import pytest
from aiohttp.test_utils import TestClient, TestServer

from gexis_core.radio import RadioBrowser, UnknownHandle
from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer

ROOT = {
    "count": 4,
    "item_loop": [
        {"text": "Local Radio", "actions": {"go": {"cmd": ["local", "items"], "params": {"menu": "local"}}}},
        {"text": "Radio Now Playing", "actions": {"go": {"cmd": ["radionowplaying", "items"], "params": {"menu": "radionowplaying"}}}},
        # Excluded by its command: the reply carries no id to exclude by.
        {"text": "Podcasts", "actions": {"go": {"cmd": ["podcast", "items"], "params": {"menu": "podcast"}}}},
        # Excluded because it wants typed text (Search TuneIn today).
        {"text": "Search TuneIn", "input": {"len": 1}, "actions": {"go": {"cmd": ["search", "items"], "params": {"menu": "search"}}}},
    ],
}

FOLDER = {
    "title": "Local Radio",
    "count": 1,
    "item_loop": [
        {"text": "Stations", "actions": {"go": {"cmd": ["local", "items"], "params": {"item_id": "20fac368.0", "menu": "local"}}}},
    ],
}

STATIONS = {
    "title": "Stations",
    "count": 2,
    # The list's shared action is a *play*, not a browse.
    "base": {
        "actions": {
            "go": {
                "cmd": ["local", "playlist", "play"],
                "params": {"menu": "local"},
                "itemsParams": "params",
                "nextWindow": "nowPlaying",
            }
        }
    },
    "item_loop": [
        {
            "text": "100% Deutsch (German Music)\nEin Hoch auf uns",
            "type": "audio",
            "goAction": "play",
            "params": {"item_id": "20fac368.0.4", "isContextMenu": 1},
            "presetParams": {"favorites_url": "http://opml.radiotime.com/Tune.ashx?id=s252804", "favorites_type": "audio"},
        },
        {
            "text": "Talk Radio One",
            "type": "audio",
            "params": {"item_id": "20fac368.0.5"},
        },
    ],
}


class FakeLms:
    """Answers by the command's first element, and records what was sent."""

    def __init__(self):
        self.sent = []
        self.players = []

    async def __call__(self, command, player=""):
        self.sent.append(list(command))
        self.players.append(player)
        if command[0] == "radios":
            return ROOT
        if command[0] == "local" and "items" in command:
            return FOLDER if not any("item_id" in str(c) for c in command) else STATIONS
        if command[0] in ("local", "playlist") :
            return {}
        return {}


def _browser(lms=None, player="aa:bb:cc:dd:ee:ff"):
    return RadioBrowser(lms or FakeLms(), lambda: player)


# --- browsing --------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_root_is_the_radios_subtree_never_home():
    """ADR-0030: everything unwanted is unreachable by construction, not
    filtered - which only holds if the entry point is this one."""
    lms = FakeLms()

    await _browser(lms).browse()

    assert lms.sent[0][:2] == ["radios", 0]
    assert "menu:radio" in lms.sent[0]


@pytest.mark.asyncio
async def test_podcasts_and_text_input_items_are_dropped():
    page = await _browser().browse()

    assert [row["label"] for row in page["items"]] == ["Local Radio", "Radio Now Playing"]


@pytest.mark.asyncio
async def test_a_station_list_is_read_as_stations_not_folders():
    """The list's inherited action ends in `play`, so its items are
    stations - the distinction that stopped a browse from playing."""
    lms = FakeLms()
    browser = _browser(lms)
    root = await browser.browse()
    folder = await browser.browse(root["items"][0]["handle"])

    stations = await browser.browse(folder["items"][0]["handle"])

    assert [row["kind"] for row in stations["items"]] == ["station", "station"]
    assert [c for c in lms.sent if c[-1].endswith("play")] == []


@pytest.mark.asyncio
async def test_a_stations_second_line_is_its_subtitle():
    browser = _browser()
    root = await browser.browse()
    folder = await browser.browse(root["items"][0]["handle"])
    stations = await browser.browse(folder["items"][0]["handle"])

    assert stations["items"][0]["label"] == "100% Deutsch (German Music)"
    assert stations["items"][0]["subtitle"] == "Ein Hoch auf uns"


@pytest.mark.asyncio
async def test_browsing_a_station_is_refused():
    """A station is not a folder; asking to open one is a bug, not a walk."""
    browser = _browser()
    root = await browser.browse()
    folder = await browser.browse(root["items"][0]["handle"])
    stations = await browser.browse(folder["items"][0]["handle"])

    with pytest.raises(UnknownHandle):
        await browser.browse(stations["items"][0]["handle"])


@pytest.mark.asyncio
async def test_a_handle_this_core_did_not_issue_does_nothing():
    """ADR-0038 §5: the API is unauthenticated by decision, so a handle is
    the only thing it will act on."""
    browser = _browser()

    with pytest.raises(UnknownHandle):
        await browser.browse("made-up-handle")
    with pytest.raises(UnknownHandle):
        await browser.play("made-up-handle")


# --- playing ---------------------------------------------------------------


async def _station(lms):
    browser = _browser(lms)
    root = await browser.browse()
    folder = await browser.browse(root["items"][0]["handle"])
    stations = await browser.browse(folder["items"][0]["handle"])
    return browser, stations["items"]


@pytest.mark.asyncio
async def test_a_station_with_its_own_url_is_played_directly():
    """One command, no menu session: measured working in Finding 029 §6."""
    lms = FakeLms()
    browser, stations = await _station(lms)

    await browser.play(stations[0]["handle"])

    assert lms.sent[-1] == ["playlist", "play", "http://opml.radiotime.com/Tune.ashx?id=s252804"]
    assert lms.players[-1] == "aa:bb:cc:dd:ee:ff"


@pytest.mark.asyncio
async def test_a_station_without_a_url_falls_back_to_its_own_action():
    lms = FakeLms()
    browser, stations = await _station(lms)

    await browser.play(stations[1]["handle"])

    assert lms.sent[-1][:3] == ["local", "playlist", "play"]
    assert "item_id:20fac368.0.5" in lms.sent[-1]


@pytest.mark.asyncio
async def test_adding_a_station_to_the_queue_does_not_play_it():
    lms = FakeLms()
    browser, stations = await _station(lms)

    result = await browser.play(stations[0]["handle"], "add")

    assert lms.sent[-1][:2] == ["playlist", "add"]
    assert result == {"played": False}


@pytest.mark.asyncio
async def test_nothing_is_sent_before_the_player_is_resolved():
    lms = FakeLms()
    browser = RadioBrowser(lms, lambda: None)
    root = await browser.browse()
    folder = await browser.browse(root["items"][0]["handle"])
    stations = await browser.browse(folder["items"][0]["handle"])

    with pytest.raises(UnknownHandle):
        await browser.play(stations["items"][0]["handle"])

    assert not [c for c in lms.sent if c[0] == "playlist"]


# --- the routes ------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_routes_answer_503_when_radio_is_not_wired():
    server = StateServer(StateStore({}))
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.get("/radio")).status == 503
        assert (await client.post("/radio/play", json={"handle": "x"})).status == 503


@pytest.mark.asyncio
async def test_the_route_browses_and_plays_by_handle():
    lms = FakeLms()
    server = StateServer(StateStore({}), radio=_browser(lms))

    async with TestClient(TestServer(server.make_app())) as client:
        root = await (await client.get("/radio")).json()
        folder = await (await client.get(f"/radio?at={root['items'][0]['handle']}")).json()
        stations = await (await client.get(f"/radio?at={folder['items'][0]['handle']}")).json()
        resp = await client.post("/radio/play", json={"handle": stations["items"][0]["handle"]})

        assert resp.status == 200
        assert lms.sent[-1][:2] == ["playlist", "play"]


@pytest.mark.asyncio
async def test_an_unknown_handle_on_the_route_is_404():
    server = StateServer(StateStore({}), radio=_browser())

    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.get("/radio?at=nope")).status == 404
        assert (await client.post("/radio/play", json={"handle": "nope"})).status == 404
        assert (await client.post("/radio/play", json={})).status == 400
