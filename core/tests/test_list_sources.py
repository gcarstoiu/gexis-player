# SPDX-License-Identifier: GPL-3.0-or-later
"""Where a `list` row's items come from (ADR-0044 §1), added in 9d.

The two sources built here are Wi-Fi through NetworkManager and Lyrion
servers over UDP broadcast. Bluetooth's trusted devices are 9f's.
"""
from __future__ import annotations

import asyncio

import pytest

from gexis_core import bluetooth_devices, discovery, wifi


# ── Lyrion discovery ──────────────────────────────────────────────────────

#: Captured from the server on George's network, 2026-09-20, by broadcasting
#: the request below and printing what came back. Not composed by hand: the
#: point of the test is that the real shape parses.
REAL_REPLY = (
    b"ENAME\x1cLyrion Music Server (Docker)JSON\x049000VERS\x059.1.1"
    b"UUID$fba29014-e9b5-4690-bf38-61bce6d29b73"
)


def test_the_request_asks_for_every_tag_with_a_zero_length():
    assert discovery._request() == b"eIPAD\x00NAME\x00JSON\x00VERS\x00UUID\x00"


def test_a_real_reply_parses():
    assert discovery.parse(REAL_REPLY) == {
        "NAME": "Lyrion Music Server (Docker)",
        "JSON": "9000",
        "VERS": "9.1.1",
        "UUID": "fba29014-e9b5-4690-bf38-61bce6d29b73",
    }


def test_anything_that_is_not_a_reply_is_not_one():
    assert discovery.parse(b"") == {}
    assert discovery.parse(b"eNAME\x04test") == {}, "our own request, heard back"


def test_a_truncated_reply_keeps_the_fields_that_arrived_whole():
    """A field claiming more bytes than arrived ends the walk, and is not
    itself emitted - half a name read as a whole one would be a lie about
    what the server is called. What came before it is kept."""
    assert discovery.parse(b"ENAME\x04abcdJSON\x40short") == {"NAME": "abcd"}
    assert discovery.parse(REAL_REPLY[:22]) == {}, "cut inside the first field"


def test_the_address_is_the_senders_and_the_port_is_the_json_one():
    protocol = discovery._Protocol()
    protocol.datagram_received(REAL_REPLY, ("192.168.178.188", 3483))
    assert "192.168.178.188:9000" in protocol.found
    # IPAD came back absent from the real server, so a reply with no JSON
    # field still has to produce an address.
    protocol.datagram_received(b"ENAME\x03box", ("10.0.0.5", 3483))
    assert "10.0.0.5:9000" in protocol.found


@pytest.mark.asyncio
async def test_finding_nothing_is_an_answer_not_an_error():
    """Zero servers is what the sheet's empty state is written for."""
    found = await discovery.find_servers(listen_s=0.05)
    assert isinstance(found, list)


# ── Wi-Fi ─────────────────────────────────────────────────────────────────

def test_terse_fields_respect_the_escapes_nmcli_writes():
    """`nmcli -t` escapes a colon inside a value. Splitting on ":" would cut
    a network called `2:1` in half and report two."""
    assert wifi._fields(r"*:H@l:58:WPA2") == ["*", "H@l", "58", "WPA2"]
    assert wifi._fields(r" :2\:1:44:WPA2") == [" ", "2:1", "44", "WPA2"]
    assert wifi._fields(r" :back\\slash:44:") == [" ", "back\\slash", "44", ""]


def test_signal_becomes_four_bars():
    assert [wifi._bars(s) for s in ("100", "75", "74", "55", "35", "1", "x")] == [
        4, 4, 3, 3, 2, 1, 0
    ]


def _fake_nmcli(monkeypatch, answers):
    """`answers` maps the first three argv words to (rc, stdout)."""
    seen = []

    async def run(*args, timeout=None):
        seen.append(args)
        for prefix, (rc, out) in answers.items():
            if args[: len(prefix)] == prefix:
                return rc, out, ""
        return 1, "", "no stub"

    monkeypatch.setattr(wifi, "_run", run)
    return seen


@pytest.mark.asyncio
async def test_a_scan_names_each_state_and_keeps_the_strongest_sighting(monkeypatch):
    _fake_nmcli(monkeypatch, {
        ("-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY"): (0, "\n".join([
            "*:H@l:58:WPA2",
            " :H@l:30:WPA2",          # the same network, weaker, second band
            " :Werkstatt:70:WPA2",    # secured, not saved
            " :Studio:64:WPA2",       # secured and saved
            " :Cafe Gast:22:",        # open
            " ::80:WPA2",             # hidden - no name, no item
        ])),
        ("-t", "-f", "NAME,UUID,TYPE"): (0, "preconfigured:uuid-1:802-11-wireless"),
        ("-t", "-f", "802-11-wireless.ssid"): (0, "802-11-wireless.ssid:Studio"),
    })
    items = await wifi.scan()
    assert [i["name"] for i in items] == ["H@l", "Studio", "Werkstatt", "Cafe Gast"]
    by = {i["name"]: i for i in items}
    assert by["H@l"]["state"] == "connected" and by["H@l"]["bars"] == 3
    assert by["Studio"]["state"] == "saved"
    assert by["Werkstatt"]["state"] == "locked" and by["Werkstatt"]["secured"] is True
    assert by["Cafe Gast"]["state"] == "open" and by["Cafe Gast"]["secured"] is False


@pytest.mark.asyncio
async def test_a_saved_network_is_matched_by_ssid_not_by_connection_name(monkeypatch):
    """This image's own saved connection is called `preconfigured`. Matching
    on the connection's name would report every known network as unknown."""
    _fake_nmcli(monkeypatch, {
        ("-t", "-f", "NAME,UUID,TYPE"): (0, "preconfigured:uuid-1:802-11-wireless\nWired:u2:802-3-ethernet"),
        ("-t", "-f", "802-11-wireless.ssid"): (0, "802-11-wireless.ssid:H@l"),
    })
    assert await wifi.saved_ssids() == {"H@l": "preconfigured"}


@pytest.mark.asyncio
async def test_joining_reports_what_network_manager_said(monkeypatch):
    seen = _fake_nmcli(monkeypatch, {
        ("device", "wifi", "connect"): (0, ""),
    })
    assert await wifi.join("Studio", "hunter2hunter2") == (True, None)
    # Not `seen[-1]`: a join re-reads the connected network afterwards, so
    # the last call is that read rather than the join.
    assert ("device", "wifi", "connect", "Studio", "password", "hunter2hunter2") in seen
    # A saved network is brought up without one.
    await wifi.join("Studio")
    assert ("device", "wifi", "connect", "Studio") in seen


@pytest.mark.asyncio
async def test_a_refused_password_comes_back_as_its_last_line(monkeypatch):
    async def run(*args, timeout=None):
        return 4, "", "Error: Connection activation failed: Secrets were required"

    monkeypatch.setattr(wifi, "_run", run)
    ok, error = await wifi.join("Studio", "wrong")
    assert ok is False and "Secrets were required" in error


@pytest.mark.asyncio
async def test_a_timeout_says_so_rather_than_failing_blankly(monkeypatch):
    async def run(*args, timeout=None):
        return 124, "", "timed out"

    monkeypatch.setattr(wifi, "_run", run)
    ok, error = await wifi.join("Far away")
    assert ok is False and "Took too long" in error


@pytest.mark.asyncio
async def test_forgetting_a_network_that_was_never_saved_says_so(monkeypatch):
    _fake_nmcli(monkeypatch, {("-t", "-f", "NAME,UUID,TYPE"): (0, "")})
    assert await wifi.forget("Studio") == (False, "That network is not saved.")


@pytest.mark.asyncio
async def test_forgetting_deletes_the_connection_that_carries_the_ssid(monkeypatch):
    seen = _fake_nmcli(monkeypatch, {
        ("-t", "-f", "NAME,UUID,TYPE"): (0, "preconfigured:uuid-1:802-11-wireless"),
        ("-t", "-f", "802-11-wireless.ssid"): (0, "802-11-wireless.ssid:H@l"),
        ("connection", "delete"): (0, ""),
    })
    assert await wifi.forget("H@l") == (True, None)
    assert ("connection", "delete", "preconfigured") in seen


@pytest.mark.asyncio
async def test_a_missing_nmcli_is_not_a_crash(monkeypatch):
    monkeypatch.setattr(wifi.shutil, "which", lambda _: None)
    assert wifi.available() is False


# ── the routes ────────────────────────────────────────────────────────────

from aiohttp.test_utils import TestClient, TestServer  # noqa: E402

from gexis_core.settings import SettingsStore  # noqa: E402
from gexis_core.settings_registry import Settings  # noqa: E402
from gexis_core.state import StateStore  # noqa: E402
from gexis_core.wsserver import StateServer  # noqa: E402

LISTS = [
    {
        "id": "g",
        "label": "G",
        "rows": [
            {"key": "wifi", "type": "list", "empty": "No networks."},
            {"key": "lms_server", "type": "list", "kind": "server", "default": "1.2.3.4:9000"},
            {"key": "bt_trusted", "type": "list", "empty": "Nothing paired."},
            {"key": "idle_timeout", "type": "number", "min": 1, "max": 60, "default": 5},
        ],
    }
]


def client_for(tmp_path):
    """Built inside the test, not in a fixture: aiohttp's TestServer wants a
    running loop at construction and a sync fixture has none."""
    store = SettingsStore(tmp_path / "s.db")
    settings = Settings(store, registry=LISTS, wired={"lms_server": None})
    server = StateServer(StateStore({}), settings=settings)
    return TestClient(TestServer(server.make_app()))


@pytest.mark.asyncio
async def test_a_list_with_no_source_yet_is_empty_rather_than_an_error(tmp_path, monkeypatch):
    """All three rows have a source now, so this is about the rule rather
    than about any of them: a `list` nothing serves opens on its own empty
    state, which is true, instead of on a 404 or a 500. The next one added
    to the registry lands here."""
    monkeypatch.setattr(StateServer, "LIST_SOURCES", ("wifi", "lms_server"))
    async with client_for(tmp_path) as client:
        response = await client.get("/settings/bt_trusted/items")
        assert response.status == 200
        assert await response.json() == {"items": []}


@pytest.mark.asyncio
async def test_bluetooth_devices_are_listed_and_forgotten(tmp_path, monkeypatch):
    calls = []

    async def known(bus):
        return [{"name": "Pixel 10 Pro", "meta": "Connected", "state": "connected"}]

    async def forget(bus, name):
        calls.append(name)
        return True, None

    monkeypatch.setattr(bluetooth_devices, "known", known)
    monkeypatch.setattr(bluetooth_devices, "forget", forget)

    async def run(call, *args):
        return await call(None, *args)

    monkeypatch.setattr(StateServer, "_bluetooth", staticmethod(run))
    async with client_for(tmp_path) as client:
        body = await (await client.get("/settings/bt_trusted/items")).json()
        assert body["items"][0]["name"] == "Pixel 10 Pro"
        answer = await client.post(
            "/settings/bt_trusted/items", json={"name": "Pixel 10 Pro", "action": "forget"}
        )
        assert await answer.json() == {"ok": True, "error": None}
        # Joining is Wi-Fi's word. A device list forgets and nothing else.
        bad = await client.post(
            "/settings/bt_trusted/items", json={"name": "Pixel 10 Pro", "action": "join"}
        )
        assert bad.status == 400
    assert calls == ["Pixel 10 Pro"]


@pytest.mark.asyncio
async def test_the_trusted_row_reads_out_how_many_are_paired(tmp_path, monkeypatch):
    """The row's value is a count, and it comes with the row.

    On the device, with a phone paired and listed by the sheet, the row
    still read "None" (George, on the panel, 2026-09-21): the panel counted
    `row.items`, which the settings payload has never carried - items are
    fetched when the sheet opens. A row has to read correctly before anyone
    opens it, so the count is published on the row.
    """

    async def known(bus):
        return [
            {"name": "Pixel 10 Pro", "meta": "Trusted", "state": "saved"},
            {"name": "Kitchen Echo", "meta": "Paired", "state": "saved"},
        ]

    async def run(call, *args):
        return await call(None, *args)

    monkeypatch.setattr(bluetooth_devices, "known", known)
    monkeypatch.setattr(StateServer, "_bluetooth", staticmethod(run))
    async with client_for(tmp_path) as client:
        body = await (await client.get("/settings")).json()
        row = next(r for g in body["groups"] for r in g["rows"] if r.get("key") == "bt_trusted")
        assert row["count"] == 2
        # Still not a stored value: counting it does not make it settable.
        assert row["value"] is None


@pytest.mark.asyncio
async def test_a_bluetooth_that_cannot_be_read_leaves_the_row_at_none(tmp_path, monkeypatch):
    """An adapter that is not there must cost the settings payload nothing.
    `_bluetooth` answers [] for anything that fails, and the row reads
    "None" - which is what its own empty state says - rather than 500."""

    async def run(call, *args):
        return []

    monkeypatch.setattr(StateServer, "_bluetooth", staticmethod(run))
    async with client_for(tmp_path) as client:
        response = await client.get("/settings")
        assert response.status == 200
        body = await response.json()
        row = next(r for g in body["groups"] for r in g["rows"] if r.get("key") == "bt_trusted")
        assert row["count"] == 0


@pytest.mark.asyncio
async def test_items_are_only_for_lists(tmp_path):
    async with client_for(tmp_path) as client:
        assert (await client.get("/settings/idle_timeout/items")).status == 405
        assert (await client.get("/settings/nope/items")).status == 404


@pytest.mark.asyncio
async def test_wifi_items_come_from_a_scan(tmp_path, monkeypatch):
    async def scan():
        return [{"name": "H@l", "meta": "Connected", "bars": 4, "state": "connected"}]

    monkeypatch.setattr(wifi, "available", lambda: True)
    monkeypatch.setattr(wifi, "scan", scan)
    async with client_for(tmp_path) as client:
        body = await (await client.get("/settings/wifi/items")).json()
        assert body["items"][0]["name"] == "H@l"


@pytest.mark.asyncio
async def test_no_network_manager_is_reported_not_hidden(tmp_path, monkeypatch):
    monkeypatch.setattr(wifi, "available", lambda: False)
    async with client_for(tmp_path) as client:
        body = await (await client.get("/settings/wifi/items")).json()
        assert body["items"] == [] and "NetworkManager" in body["error"]


@pytest.mark.asyncio
async def test_the_server_in_use_is_marked_current(tmp_path, monkeypatch):
    async def find_servers(*_a, **_k):
        return [
            {"address": "1.2.3.4:9000", "name": "Home", "version": "9.1.1", "uuid": ""},
            {"address": "5.6.7.8:9000", "name": "", "version": "", "uuid": ""},
        ]

    monkeypatch.setattr(discovery, "find_servers", find_servers)
    async with client_for(tmp_path) as client:
        items = (await (await client.get("/settings/lms_server/items")).json())["items"]
    assert [i["state"] for i in items] == ["current", "found"]
    assert items[0]["meta"] == "Home · 9.1.1"
    # A server that answers with no name at all still has to read as one.
    assert items[1]["meta"] == "Lyrion server"


@pytest.mark.asyncio
async def test_joining_and_forgetting_go_through_the_item_route(tmp_path, monkeypatch):
    calls = []

    async def join(ssid, password=None):
        calls.append(("join", ssid, password))
        return True, None

    async def forget(ssid):
        calls.append(("forget", ssid))
        return False, "That network is not saved."

    monkeypatch.setattr(wifi, "available", lambda: True)
    monkeypatch.setattr(wifi, "join", join)
    monkeypatch.setattr(wifi, "forget", forget)
    async with client_for(tmp_path) as client:
        ok = await client.post("/settings/wifi/items", json={"name": "Studio", "password": "p"})
        assert await ok.json() == {"ok": True, "error": None}
        # A refusal is a 200 with a reason: the sheet shows it and offers to
        # try again, which a 4xx would turn into "something went wrong".
        bad = await client.post(
            "/settings/wifi/items", json={"name": "Studio", "action": "forget"}
        )
        assert bad.status == 200
        assert (await bad.json())["ok"] is False
        assert (await client.post("/settings/wifi/items", json={})).status == 400
        assert (
            await client.post("/settings/wifi/items", json={"name": "x", "action": "dance"})
        ).status == 400
        # Choosing a server is a write, not a per-item command.
        assert (
            await client.post("/settings/lms_server/items", json={"name": "1.2.3.4:9000"})
        ).status == 405
    assert calls == [("join", "Studio", "p"), ("forget", "Studio")]


@pytest.mark.asyncio
async def test_the_connected_network_is_the_rows_own_value(monkeypatch):
    """George, on the panel: the Wi-Fi row said "None" while the device was
    connected."""
    monkeypatch.setattr(wifi, "available", lambda: True)
    _fake_nmcli(monkeypatch, {
        ("-t", "-f", "ACTIVE,SSID"): (0, "no:L0c@lh0st\nyes:H@l\nno:H@l\n"),
    })
    wifi._connected = None
    assert await wifi.refresh_connected() == "H@l"
    assert wifi.connected_ssid() == "H@l"


def test_reading_the_row_never_runs_a_subprocess(monkeypatch):
    """**The whole point of the rewrite.** It used to read `nmcli` itself
    when a TTL expired, which measured 3.2 s inside the request handler and
    blocked the daemon while the settings sheet sat there (George,
    2026-09-21). The accessor is now a pure read of what the watcher saw."""
    def explode(*_a, **_k):
        raise AssertionError("connected_ssid must not run anything")

    monkeypatch.setattr(wifi.shutil, "which", explode)
    wifi._connected = "H@l"
    assert wifi.connected_ssid() == "H@l"


@pytest.mark.asyncio
async def test_joining_re_reads_rather_than_leaving_the_old_name(monkeypatch):
    """Otherwise the row reports the network just left, at exactly the
    moment someone is looking at it."""
    monkeypatch.setattr(wifi, "available", lambda: True)
    _fake_nmcli(monkeypatch, {
        ("device", "wifi", "connect"): (0, ""),
        ("-t", "-f", "ACTIVE,SSID"): (0, "yes:New\n"),
    })
    wifi._connected = "Old"
    await wifi.join("New")
    assert wifi._connected == "New"


@pytest.mark.asyncio
async def test_a_device_with_no_wifi_at_all_reports_nothing(monkeypatch):
    monkeypatch.setattr(wifi, "available", lambda: False)
    wifi._connected = None
    assert await wifi.refresh_connected() is None
    assert wifi.connected_ssid() is None
