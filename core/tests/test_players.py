"""ADR-0136: the other players on the network, for the phone's switcher."""
from __future__ import annotations

import asyncio
import os

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from gexis_core import players as pl
from gexis_core.model import TrackMetadata

BROWSE = "\n".join([
    "+;wlan0;IPv4;sofapi;_gexis._tcp;local",
    "=;wlan0;IPv4;sofapi;_gexis._tcp;local;sofapi.local;192.0.2.31;8090;",
    "=;wlan0;IPv6;sofapi;_gexis._tcp;local;sofapi.local;fd00::31;8090;",
    "=;wlan0;IPv4;shelvespi;_gexis._tcp;local;shelvespi.local;192.0.2.22;8090;",
    "=;eth0;IPv4;shelvespi;_gexis._tcp;local;shelvespi.local;192.0.2.23;8090;",
    "=;wlan0;IPv4;printer;_ipp._tcp;local;printer.local;192.0.2.9;631;",
])


def test_browsing_keeps_one_resolved_ipv4_entry_per_other_player():
    found = pl.parse_browse(BROWSE, "sofapi")
    assert found == [{"host": "shelvespi.local", "address": "192.0.2.22", "port": 8090}]


class State:
    def __init__(self, active, transport):
        self.active = active
        self.metadata = TrackMetadata(transport=transport)


def test_a_player_says_whether_it_plays_and_through_what():
    sources = ({"id": "spotify", "name": "Spotify"},)
    assert pl.status_line(State("spotify", "playing"), sources) == {"transport": "playing", "renderer": "Spotify"}
    assert pl.status_line(State(None, "stopped"), sources) == {"transport": "stopped", "renderer": None}


async def test_the_others_are_asked_for_their_status_and_kept_a_while():
    app = web.Application()
    app.router.add_get("/player/status", lambda r: web.json_response(
        {"name": "ShelvesPi", "host": "shelvespi.local", "transport": "paused", "renderer": "Lyrion"}))
    async with TestServer(app) as peer:
        port = peer.port
        calls = []

        async def browse():
            calls.append(1)
            return (f"=;wlan0;IPv4;shelvespi;_gexis._tcp;local;shelvespi.local;127.0.0.1;{peer.port};\n"
                    "=;wlan0;IPv4;gone;_gexis._tcp;local;gone.local;127.0.0.1;9;\n")
        finder = pl.Players(lambda: "sofapi", browse=browse)
        async with aiohttp.ClientSession() as session:
            first = await finder.others(session)
            again = await finder.others(session)
    # The one that answers is listed, by its name; the one that does not, not.
    assert first == [{"name": "ShelvesPi", "host": "shelvespi.local", "transport": "paused",
                      "renderer": "Lyrion", "url": f"http://shelvespi.local:{port}/"}]
    assert again == first and len(calls) == 1


async def test_a_list_opening_asks_the_players_again_without_a_search():
    """George, 2026-11-14: bedroompi's menu still showed a group undone on
    sofapi. A list opening asks what is a few seconds old again."""
    group = {"value": {"id": "g1", "members": [{"id": "a"}, {"id": "b"}]}}
    app = web.Application()
    app.router.add_get("/player/status", lambda r: web.json_response(
        {"name": "SofaPi", "host": "sofapi.local", "id": "a", "group": group["value"]}))
    async with TestServer(app) as peer:
        searches, now = [], [100.0]

        async def browse():
            searches.append(1)
            return f"=;wlan0;IPv4;sofapi;_gexis._tcp;local;sofapi.local;127.0.0.1;{peer.port};\n"
        finder = pl.Players(lambda: "bedroompi", browse=browse, clock=lambda: now[0])
        async with aiohttp.ClientSession() as session:
            assert (await finder.others(session))[0]["group"]["id"] == "g1"
            group["value"] = None                       # undone on sofapi
            now[0] += pl.ASK_AGAIN_S - 1
            assert (await finder.others(session, fresh=True))[0]["group"] is not None, "still fresh enough"
            now[0] += 2
            assert (await finder.others(session))[0]["group"] is not None, "kept, unless a list opens"
            fresh = await finder.others(session, fresh=True)
            assert fresh[0]["group"] is None and fresh[0]["url"] == f"http://sofapi.local:{peer.port}/"
            assert len(searches) == 1, "asked again, not searched again"
            # Kept from then on, as a search's answer is.
            assert (await finder.others(session))[0]["group"] is None


async def test_a_group_change_is_told_to_every_player_found():
    """George, 2026-11-14: each player found hears of it at once; one older,
    without the route, answers 404 and is not counted."""
    heard = []
    app = web.Application()
    app.router.add_post("/players/changed", lambda r: heard.append(1) or web.json_response({"heard": True}))
    older = web.Application()
    async with TestServer(app) as new, TestServer(older) as old:
        finder = pl.Players(lambda: "sofapi")
        finder.addresses = {"a": ("127.0.0.1", new.port), "b": ("127.0.0.1", old.port), "c": ("127.0.0.1", 9)}
        assert await finder.tell_others() == 1
    assert heard == [1]
    assert await pl.Players(lambda: "sofapi").tell_others() == 0, "nobody found: nobody told"


async def test_hearing_of_a_change_asks_again_once_for_several_then_says_so(monkeypatch):
    monkeypatch.setattr(pl, "HEARD_S", 0.05)
    group = {"value": {"id": "g1", "members": [{"id": "a"}, {"id": "b"}]}}
    asked = []

    def status(request):
        asked.append(1)
        return web.json_response({"name": "GuestPi", "id": "b", "group": group["value"]})
    app = web.Application()
    app.router.add_get("/player/status", status)
    async with TestServer(app) as peer:
        async def browse():
            return f"=;wlan0;IPv4;guestpi;_gexis._tcp;local;guestpi.local;127.0.0.1;{peer.port};\n"
        finder = pl.Players(lambda: "shelvespi", browse=browse)
        told = []
        finder.on_heard = lambda: told.append(finder.status_of("b")["group"])
        async with aiohttp.ClientSession() as session:
            await finder.refresh(session)
        group["value"] = None                          # undone
        for _ in range(3):                             # each member's word
            finder.heard()
        await asyncio.sleep(0.4)
    assert len(asked) == 2, "the search's ask, then one more for the three"
    assert told == [None], "said once, after asking again"


def _peer(name, status, others, asked):
    """A player answering its status and, asked, its own list."""
    app = web.Application()
    app.router.add_get("/player/status", lambda r: web.json_response({"name": name, **status}))

    def players(request):
        asked.append(name)
        return web.json_response({"self": {"name": name, **status}, "others": others})
    app.router.add_get("/players", players)
    return app


GUEST = {"name": "GuestPi", "host": "guestpi.local", "id": "g", "instance": "gi", "transport": "playing",
         "renderer": "Radio", "url": "http://guestpi.local:8090/"}


async def test_a_player_found_that_does_not_answer_is_listed_through_one_that_does():
    """ADR-0136 item 5 (George, 2026-11-14): bedroompi and guestpi could not
    reach each other on the home network; each reached the other two."""
    asked = []
    # This player as the others last heard it: before its restart (another
    # token) - by its board's id, and, from one without ids, by its name.
    me = {"name": "BedroomPi", "host": "bedroompi.local", "id": "b", "instance": "before-restart",
          "url": "http://bedroompi.local:8090/"}
    me_by_name = {"name": "BedroomPi", "host": "bedroompi.local", "url": "http://bedroompi-2.local:8090/"}
    third = {"name": "Kitchen", "host": "kitchen.local", "id": "k", "url": "http://kitchen.local:8090/",
             "via": "Study"}
    shelves = _peer("ShelvesPi", {"host": "shelvespi.local", "id": "s"}, [GUEST, me, me_by_name], asked)
    sofa = _peer("SofaPi", {"host": "sofapi.local", "id": "a"},
                 [GUEST, me, third, {"name": "ShelvesPi", "host": "shelvespi.local", "id": "s",
                                     "url": "http://shelvespi.local:8090/"}], asked)
    async with TestServer(shelves) as s, TestServer(sofa) as a:
        async def browse():
            return (f"=;wlan0;IPv4;shelvespi;_gexis._tcp;local;shelvespi.local;127.0.0.1;{s.port};\n"
                    f"=;wlan0;IPv4;sofapi;_gexis._tcp;local;sofapi.local;127.0.0.1;{a.port};\n"
                    "=;wlan0;IPv4;guestpi;_gexis._tcp;local;guestpi.local;127.0.0.1;9;\n")
        finder = pl.Players(lambda: "bedroompi", own_instance="me", browse=browse, own_board=lambda: "b")
        seen = []

        async def on_refresh(statuses):
            seen.append(sorted(statuses))
        finder.on_refresh = on_refresh
        async with aiohttp.ClientSession() as session:
            listed = await finder.refresh(session)
    # Each listed once; this player and one had through a third, not at all.
    assert sorted(p["name"] for p in listed) == ["GuestPi", "ShelvesPi", "SofaPi"]
    guest = next(p for p in listed if p["name"] == "GuestPi")
    assert guest["via"] == "ShelvesPi" and guest["url"] == "http://guestpi.local:8090/"
    assert guest["transport"] == "playing" and sorted(asked) == ["ShelvesPi", "SofaPi"]
    assert not any(p.get("via") for p in listed if p["name"] != "GuestPi")
    # Not one the group reaches, follows or tells.
    assert "g" not in finder.addresses and finder.status_of("g") is None
    assert finder.status_of("s")["name"] == "ShelvesPi"
    assert seen == [["a", "s"]]


async def test_when_every_player_found_answers_no_list_is_asked():
    asked = []
    async with TestServer(_peer("SofaPi", {"host": "sofapi.local", "id": "a"}, [GUEST], asked)) as a:
        async def browse():
            return f"=;wlan0;IPv4;sofapi;_gexis._tcp;local;sofapi.local;127.0.0.1;{a.port};\n"
        finder = pl.Players(lambda: "bedroompi", own_instance="me", browse=browse)
        async with aiohttp.ClientSession() as session:
            listed = await finder.refresh(session)
    assert [p["name"] for p in listed] == ["SofaPi"] and asked == []


async def test_a_peer_that_answers_something_other_than_an_object_is_left_out():
    """Review, 2026-10-12: `{**body}` on a list raised TypeError, which failed
    the whole refresh and with it `/players`."""
    app = web.Application()
    app.router.add_get("/player/status", lambda r: web.json_response([1, 2]))
    async with TestServer(app) as peer:
        async def browse():
            return f"=;wlan0;IPv4;odd;_gexis._tcp;local;odd.local;127.0.0.1;{peer.port};\n"
        finder = pl.Players(lambda: "sofapi", browse=browse)
        async with aiohttp.ClientSession() as session:
            assert await finder.others(session) == []


async def test_this_player_under_a_name_avahi_gave_it_is_still_left_out():
    """George, 2026-10-12: GuestPi twice in the switcher. avahi had renamed it
    `guestpi-2.local` after a name conflict, so its hostname did not match;
    its own status, carrying this core's token, does."""
    app = web.Application()
    app.router.add_get("/player/status", lambda r: web.json_response(
        {"name": "GuestPi", "host": "guestpi.local", "instance": "me", "transport": "stopped"}))
    async with TestServer(app) as peer:
        async def browse():
            return f"=;wlan0;IPv4;guestpi-2;_gexis._tcp;local;guestpi-2.local;127.0.0.1;{peer.port};\n"
        finder = pl.Players(lambda: "guestpi", own_instance="me", browse=browse)
        other = pl.Players(lambda: "sofapi", own_instance="someone-else", browse=browse)
        async with aiohttp.ClientSession() as session:
            assert await finder.refresh(session) == []
            assert [p["name"] for p in await other.refresh(session)] == ["GuestPi"]


@pytest.mark.asyncio
async def test_a_player_that_never_answers_does_not_take_the_others_with_it(tmp_path, monkeypatch):
    """sofapi, 2026-10-16: one announcement never resolved, avahi-browse
    waited for it past the search's own limit, and every search came back
    empty - the phone's switch to other players disappeared."""
    tool = tmp_path / "avahi-browse"
    tool.write_text("#!/bin/sh\n"
                    "echo '=;wlan0;IPv4;guestpi;_gexis._tcp;local;guestpi.local;10.0.0.8;8090;'\n"
                    "exec sleep 5\n")
    tool.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")
    monkeypatch.setattr(pl, "BROWSE_TIMEOUT_S", 0.5)
    out = await pl._browse()
    assert "guestpi.local" in out


def test_a_player_keeps_one_id_from_its_board_and_never_shows_the_serial(tmp_path):
    """ADR-0160 D5: Home Assistant knows a player by this id."""
    serial = tmp_path / "serial-number"
    serial.write_bytes(b"10000000abcdef01\x00")
    first = pl.stable_id(serial)
    assert first == pl.stable_id(serial) and len(first) == 16 and int(first, 16) >= 0
    assert "abcdef01" not in first
    other = tmp_path / "other"
    other.write_bytes(b"10000000abcdef02\x00")
    assert pl.stable_id(other) != first
    empty = tmp_path / "empty"
    empty.write_bytes(b"\x00")
    assert pl.stable_id(empty) is None
    assert pl.stable_id(tmp_path / "absent") is None, "off a Pi"


@pytest.mark.asyncio
async def test_the_status_carries_the_id_and_whether_there_is_a_screen(tmp_path, monkeypatch):
    """ADR-0160 D5: what Home Assistant reads before it adds a player."""
    from aiohttp.test_utils import TestClient

    from gexis_core import wsserver
    from gexis_core.settings import SettingsStore
    from gexis_core.settings_registry import Settings
    from gexis_core.state import StateStore

    monkeypatch.setattr(wsserver, "own_id", lambda: "0123456789abcdef")
    registry = [{"id": "g", "label": "G", "rows": [{"key": "headless", "type": "toggle", "default": False},
                                                   {"key": "idle_enabled", "type": "toggle", "default": False}]}]
    settings = Settings(SettingsStore(tmp_path / "s.db"), registry=registry, wired={"headless": None, "idle_enabled": None})
    server = wsserver.StateServer(StateStore({}), settings=settings)
    async with TestClient(TestServer(server.make_app())) as client:
        status = await (await client.get("/player/status")).json()
        assert status["id"] == "0123456789abcdef" and status["screen"] is True
        assert status["idle_screen"] is False
        settings.set("idle_enabled", True)
        assert (await (await client.get("/player/status")).json())["idle_screen"] is True
        settings.set("headless", True)
        assert (await (await client.get("/player/status")).json())["screen"] is False


async def test_the_route_hears_a_change_and_the_state_says_so_after_asking_again(monkeypatch):
    """`POST /players/changed`: the players found asked again, then the
    state's `players_revision` moves for the screens' lists."""
    from aiohttp.test_utils import TestClient

    from gexis_core import wsserver
    from gexis_core.state import StateStore
    monkeypatch.setattr(pl, "HEARD_S", 0.01)
    store = StateStore({})
    server = wsserver.StateServer(store)
    asked = []

    async def ask_again(session):
        asked.append(1)
        return []
    server._players.ask_again = ask_again
    before = store.state.players_revision
    async with TestClient(TestServer(server.make_app())) as client:
        answer = await client.post("/players/changed")
        assert answer.status == 200 and (await answer.json()) == {"heard": True}
        await asyncio.sleep(0.2)
    assert asked == [1] and store.state.players_revision == before + 1
    assert store.state.to_json()["players_revision"] == before + 1
