"""ADR-0136: the other players on the network, for the phone's switcher."""
from __future__ import annotations

import aiohttp
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
