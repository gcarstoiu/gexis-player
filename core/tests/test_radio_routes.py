# SPDX-License-Identifier: GPL-3.0-or-later
"""Internet radio through its routes (ADR-0180): the state server, the
radio service, a real supervisor with another source holding the output,
the renderer on a fake mpv, and a fake directory that can go down.

What the acceptance asks of the core, as far as it can be asked here:
a station found by country, genre or name plays and takes the output from
another source (1, 3); favourites keep and play with the directory down (2);
a station added by its address is kept only if it plays (decision 4).
"""
from __future__ import annotations

import asyncio
import tempfile

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gexis_core.adapters import radio as radio_mod
from gexis_core.adapters.base import Adapter, Capabilities, ReleaseAction, VolumeMechanism
from gexis_core.adapters.radio import RadioAdapter
from gexis_core.arbitration import Supervisor, TimeoutLadder
from gexis_core.radio_directory import Directory
from gexis_core.radio_favourites import Favourites
from gexis_core.radio_logos import Logos
from pathlib import Path
from gexis_core.radio_service import RadioService
from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer

from test_radio_adapter import FakeMpv, FakeUnits

UUID = "78012206-1aa1-11e9-a80b-52543be04c81"
LISTED = {"stationuuid": UUID, "name": "Example FM", "url": "http://example.org/listed.pls",
          "url_resolved": "http://example.org/listed", "favicon": "https://example.org/l.png",
          "country": "Germany", "countrycode": "DE", "codec": "MP3", "bitrate": 128, "hls": 0,
          "lastcheckok": 1}


class Other(Adapter):
    """Another source, holding the output when the radio is played."""

    renderer_id = "other"
    release_action = ReleaseAction.DISCONNECT
    unit_name = "other.service"
    capabilities = Capabilities(audio_connection="output", acquisition_events=frozenset(),
                                supports_artwork=False, supports_sample_rate=False,
                                volume_managed=False, volume_mechanism=VolumeMechanism.OUTPUT)

    def __init__(self) -> None:
        self.released = 0

    async def run(self, on_acquire, on_release):
        await asyncio.Event().wait()

    async def release(self) -> bool:
        self.released += 1
        return True

    async def signal_stop(self, force: bool) -> None:
        pass


class Directory503:
    def __init__(self) -> None:
        self.down = False
        self.asked: list[str] = []

    def app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/json/{rest:.*}", self.handle)
        return app

    async def handle(self, request):
        self.asked.append(request.path_qs)
        if self.down:
            return web.Response(status=503)
        if request.path == "/json/stations/search":
            return web.json_response([LISTED])
        if request.path.startswith("/json/url/"):
            return web.json_response({"ok": True, "url": "http://example.org/moved"})
        return web.json_response([])


@pytest.fixture
async def rig(monkeypatch):
    monkeypatch.setattr(radio_mod, "WATCHDOG_S", 0.2)
    monkeypatch.setattr(radio_mod, "SOCKET_WAIT_S", 1.0)
    monkeypatch.setattr("gexis_core.radio_service.CHECK_S", 2.0)
    fake_dir = Directory503()
    dir_server = TestServer(fake_dir.app())
    await dir_server.start_server()

    async def servers():
        return [f"http://{dir_server.host}:{dir_server.port}"]
    folder = tempfile.mkdtemp(prefix="mpv")
    mpv = FakeMpv(f"{folder}/s")
    units = FakeUnits(mpv)
    store: dict = {}
    switched = {"on": True}
    directory = Directory(user_agent="GexisPlayer/test", cache_dir=__import__("pathlib").Path(folder),
                          servers=servers)
    favourites = Favourites(store.get, store.__setitem__)
    radio = RadioAdapter(user_agent="GexisPlayer/test", resolve=lambda s: service.resolve(s),
                         step=favourites.step, is_favourite=lambda i: favourites.get(i) is not None,
                         units=units, socket_path=mpv.path)
    other = Other()
    adapters = {"other": other, "radio": radio}
    supervisor = Supervisor(adapters, device_busy=lambda rid: False,
                            ladder=TimeoutLadder(0.1, 0.1, 0.1),
                            enabled=lambda rid: rid != "radio" or switched["on"])
    service = RadioService(directory=directory, favourites=favourites, adapter=radio,
                           acquire=supervisor.acquire, active=lambda: supervisor.active,
                           enabled=lambda: switched["on"], country=lambda: "DE",
                           logos=Logos(user_agent="GexisPlayer/test", cache_dir=Path(folder) / "logos"))
    server = StateServer(StateStore({rid: a.capabilities for rid, a in adapters.items()}),
                         stations=service)
    client = TestClient(TestServer(server.make_app()))
    await client.start_server()
    await supervisor.acquire("other")

    class Rig:
        pass
    r = Rig()
    (r.client, r.dir, r.mpv, r.units, r.radio, r.other, r.supervisor, r.switched,
     r.favourites) = client, fake_dir, mpv, units, radio, other, supervisor, switched, favourites
    yield r
    await radio.release()
    await client.close()
    await dir_server.close()
    await directory.close()
    await mpv.stop()


async def until(predicate, timeout: float = 3.0) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not predicate():
        if loop.time() > deadline:
            raise AssertionError("never happened")
        await asyncio.sleep(0.01)


async def test_a_station_found_by_name_plays_and_takes_the_output(rig):
    found = await (await rig.client.get("/stations/search", params={"q": "example"})).json()
    assert found["stations"][0]["name"] == "Example FM" and found["end"] is True
    station = found["stations"][0]
    assert station["favourite"] is False
    resp = await rig.client.post("/stations/play", json={"station": station})
    assert resp.status == 200
    assert rig.supervisor.active == "radio" and rig.other.released == 1
    # Counted with the directory, which gave the address now.
    assert f"/json/url/{UUID}" in rig.dir.asked
    assert rig.mpv.loaded == ["http://example.org/moved"]
    await until(lambda: rig.radio.state.state == radio_mod.PLAYING)


@pytest.mark.parametrize("query", [{"genre": "jazz"}, {"country": "DE"}, {"language": "german"}])
async def test_lists_by_genre_country_and_language(rig, query):
    resp = await rig.client.get("/stations/list", params=query)
    assert resp.status == 200
    assert (await resp.json())["stations"][0]["id"] == UUID


async def test_a_list_needs_a_choice_and_a_country_is_two_letters(rig):
    assert (await rig.client.get("/stations/list")).status == 400
    assert (await rig.client.get("/stations/list", params={"country": "Germany"})).status == 400


async def test_the_directory_down_with_nothing_kept_says_so(rig):
    rig.dir.down = True
    resp = await rig.client.get("/stations/popular")
    assert resp.status == 503
    assert (await resp.json())["reachable"] is False
    overview = await (await rig.client.get("/stations")).json()
    assert overview["reachable"] is False and overview["country"] == "DE"


async def test_favourites_keep_their_order_and_play_with_the_directory_down(rig):
    station = (await (await rig.client.get("/stations/popular")).json())["stations"][0]
    second = {**station, "id": "address-1", "name": "Second", "url": "http://example.org/2", "listed": False}
    assert (await (await rig.client.post("/stations/favourites", json={"station": station})).json())["added"]
    assert (await (await rig.client.post("/stations/favourites", json={"station": second})).json())["added"]
    assert not (await (await rig.client.post("/stations/favourites", json={"station": second})).json())["added"]
    resp = await rig.client.put("/stations/favourites", json={"ids": ["address-1", UUID]})
    assert resp.status == 200
    assert (await rig.client.put("/stations/favourites", json={"ids": [UUID]})).status == 409
    listed = (await (await rig.client.get("/stations/favourites")).json())["favourites"]
    assert [s["id"] for s in listed] == ["address-1", UUID]
    # A list says which are favourites.
    assert (await (await rig.client.get("/stations/popular")).json())["stations"][0]["favourite"]

    rig.dir.down = True
    resp = await rig.client.post("/stations/play", json={"favourite": UUID})
    assert resp.status == 200
    assert rig.mpv.loaded[-1] == "http://example.org/listed", "the kept address, the directory being down"
    # Next steps through the favourites, round the end.
    assert await rig.radio.next()
    assert rig.radio.state.station.id == "address-1"

    assert (await rig.client.delete("/stations/favourites/address-1")).status == 200
    assert (await rig.client.delete("/stations/favourites/address-1")).status == 404


async def test_a_station_added_by_its_address_is_kept_only_if_it_plays(rig):
    resp = await rig.client.post("/stations/favourites/address",
                                 json={"url": "http://example.org/refused", "name": "Nope"})
    assert resp.status == 422
    assert rig.favourites.all() == []
    assert rig.radio.state.state in (radio_mod.STOPPED, radio_mod.NOT_ANSWERING)

    resp = await rig.client.post("/stations/favourites/address",
                                 json={"url": "http://example.org/fine", "name": "  My   station "})
    assert resp.status == 200
    kept = rig.favourites.all()
    assert [(s.name, s.url, s.listed) for s in kept] == [("My station", "http://example.org/fine", False)]
    assert rig.mpv.loaded[-1] == "http://example.org/fine", "an unlisted address is played as given"

    resp = await rig.client.post("/stations/favourites/address", json={"url": "file:///etc/passwd", "name": "x"})
    assert resp.status == 400


async def test_logos_come_through_the_player_and_go_back_as_they_were(rig):
    station = (await (await rig.client.get("/stations/popular")).json())["stations"][0]
    assert station["logo"].startswith("/stations/logo/")
    # Sent back as a favourite, it is kept with the logo's own address.
    assert (await (await rig.client.post("/stations/favourites", json={"station": station})).json())["added"]
    assert rig.favourites.all()[0].logo == "https://example.org/l.png"
    listed = (await (await rig.client.get("/stations/favourites")).json())["favourites"]
    assert listed[0]["logo"] == station["logo"]
    # A key the player never gave is nothing.
    assert (await rig.client.get("/stations/logo/0000000000000000")).status == 404


async def test_switched_off_it_does_not_play(rig):
    rig.switched["on"] = False
    station = {"id": "x", "name": "X", "url": "http://example.org/x"}
    resp = await rig.client.post("/stations/play", json={"station": station})
    assert resp.status == 409
    assert rig.supervisor.active == "other" and rig.mpv.loaded == []


async def test_a_body_that_names_no_station_is_refused(rig):
    for body in ({}, {"station": {"id": "x", "name": "X", "url": "ftp://x"}}, {"favourite": "nope"}):
        assert (await rig.client.post("/stations/play", json=body)).status == 400
