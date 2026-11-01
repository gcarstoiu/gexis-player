"""ADR-0169: one store for every plugin - what is added, and the routes that
add and remove."""
from __future__ import annotations

from types import SimpleNamespace

from aiohttp.test_utils import TestClient, TestServer

from gexis_core import plugin_store
from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer


def plugin(pid, **extra):
    return SimpleNamespace(id=pid, name=pid.title(), kind="service", area="system", summary=f"{pid} does things",
                           tag=None, notice=None, built_in=False, uploaded=False, **extra)


def test_the_store_holds_ours_but_not_the_player_s_own_sources_or_uploads():
    found = plugin_store.optional([plugin("plexamp"),
                                   SimpleNamespace(id="lms", built_in=True, uploaded=False),
                                   SimpleNamespace(id="mine", built_in=False, uploaded=True)])
    assert [p.id for p in found] == ["plexamp"]


def test_an_update_starts_from_what_is_in_use():
    on = {"airplay": True, "plexamp": False, "beszel": False}
    downloaded = {"plexamp"}
    added = plugin_store.first(["airplay", "plexamp", "beszel"], on=lambda pid: on[pid],
                               downloaded=lambda pid: pid in downloaded, skins=True)
    assert added == ["airplay", "plexamp", plugin_store.SKINS]


def test_the_record_reads_back_or_is_absent():
    assert plugin_store.read(None) is None
    assert plugin_store.read(["a", 3, "b"]) == {"a", "b"}


def test_tiles_say_which_are_added_skins_included():
    tiles = plugin_store.tiles([plugin("plexamp"), plugin("beszel")], {"plexamp"})
    by_id = {t["id"]: t for t in tiles}
    assert by_id["plexamp"]["added"] and not by_id["beszel"]["added"]
    assert by_id[plugin_store.SKINS]["area"] == "display" and not by_id[plugin_store.SKINS]["added"]


async def test_the_routes_add_and_remove_keeping_unless_told_not_to():
    calls = []

    async def add(pid):
        calls.append(("add", pid))
        return pid != "nope"

    async def remove(pid, keep):
        calls.append(("remove", pid, keep))
        return True

    server = StateServer(StateStore({}), store_view=lambda: {"ours": []}, store_add=add, store_remove=remove)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await (await client.get("/plugins/store")).json()) == {"ours": []}
        assert (await client.post("/plugins/plexamp/add")).status == 200
        assert (await client.post("/plugins/nope/add")).status == 404
        assert (await client.post("/plugins/plexamp/remove")).status == 200
        assert (await client.post("/plugins/plexamp/remove", json={"keep": False})).status == 200
    assert calls == [("add", "plexamp"), ("add", "nope"), ("remove", "plexamp", True), ("remove", "plexamp", False)]
