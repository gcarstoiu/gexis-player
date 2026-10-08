"""ADR-0123: the cable's address, checked, changed, and kept or put back."""
from __future__ import annotations

import asyncio

import pytest

from gexis_core import wired


class FakeNM:
    """One port, one profile: what `nmcli` would say and do."""

    def __init__(self, method="auto", dhcp="192.0.2.107/24", refuse_up=False):
        self.profile = {"method": method, "addresses": "", "gateway": "", "dns": ""}
        self.dhcp = dhcp
        self.refuse_up = refuse_up
        self.calls = []

    def live(self):
        if self.profile["method"] == "manual":
            return self.profile["addresses"], self.profile["gateway"], self.profile["dns"].split()
        return self.dhcp, "192.0.2.1", ["192.0.2.1"]

    async def __call__(self, *args, timeout=None):
        self.calls.append(args)
        if args[:3] == ("-t", "-f", "GENERAL.CONNECTION"):
            return 0, "GENERAL.CONNECTION:Wired connection 1\n", ""
        if args[0] == "-g":
            p = self.profile
            return 0, "\n".join([p["method"], p["addresses"], p["gateway"], p["dns"].replace(" ", ",")]) + "\n", ""
        if args[:3] == ("-t", "-f", "IP4.ADDRESS,IP4.GATEWAY,IP4.DNS"):
            address, gateway, dns = self.live()
            lines = [f"IP4.ADDRESS[1]:{address}", f"IP4.GATEWAY:{gateway}"] + [f"IP4.DNS[{i+1}]:{d}" for i, d in enumerate(dns)]
            return 0, "\n".join(lines) + "\n", ""
        if args[:2] == ("connection", "modify"):
            pairs = dict(zip(args[3::2], args[4::2]))
            self.profile.update(method=pairs["ipv4.method"], addresses=pairs["ipv4.addresses"],
                                gateway=pairs["ipv4.gateway"], dns=pairs["ipv4.dns"])
            return 0, "", ""
        if args[:2] == ("connection", "up"):
            return (4, "", "no carrier") if self.refuse_up else (0, "", "")
        return 1, "", "unexpected"


@pytest.fixture
def sys_net(tmp_path):
    port = tmp_path / "eth0"
    port.mkdir()
    (port / "carrier").write_text("1\n")
    (port / "speed").write_text("1000\n")
    return tmp_path


def test_a_manual_address_is_checked_as_typed():
    ok = wired.check("192.168.1.20/24", "192.168.1.1", "192.168.1.1 9.9.9.9")
    assert (ok.address, ok.gateway, ok.dns, ok.host) == ("192.168.1.20/24", "192.168.1.1", ["192.168.1.1", "9.9.9.9"], "192.168.1.20")
    for address, gateway, dns, sentence in [
        ("192.168.1.20", "192.168.1.1", "1.1.1.1", wired.BAD_ADDRESS),       # no prefix
        ("192.168.1.0/24", "192.168.1.1", "1.1.1.1", wired.BAD_ADDRESS),     # the network itself
        ("192.168.1.300/24", "192.168.1.1", "1.1.1.1", wired.BAD_ADDRESS),
        ("192.168.1.20/24", "10.0.0.1", "1.1.1.1", wired.BAD_GATEWAY),       # another network
        ("192.168.1.20/24", "192.168.1.20", "1.1.1.1", wired.BAD_GATEWAY),   # itself
        ("192.168.1.20/24", "192.168.1.1", "", wired.BAD_DNS),
        ("192.168.1.20/24", "192.168.1.1", "1.1.1.1 8.8.8.8 9.9.9.9", wired.BAD_DNS),
        ("192.168.1.20/24", "192.168.1.1", "dns.example", wired.BAD_DNS),
    ]:
        with pytest.raises(ValueError) as refused:
            wired.check(address, gateway, dns)
        assert str(refused.value) == sentence, (address, gateway, dns)


def test_the_row_reads_the_cable_at_a_glance(sys_net):
    state = asyncio.run(wired.status(run=FakeNM(), sys_net=sys_net))
    assert state["link"] and state["speed"] == 1000 and state["method"] == "auto"
    assert wired.summary(state) == "Connected · 1000 Mb/s · 192.0.2.107"
    (sys_net / "eth0" / "carrier").write_text("0\n")
    assert wired.summary(asyncio.run(wired.status(run=FakeNM(), sys_net=sys_net))) == "No link"


def _cable(sys_net, nm, changes):
    slept = []

    async def sleep(s):
        slept.append(s)
        await asyncio.sleep(0)

    return wired.Cable(run=nm, sys_net=sys_net, on_change=changes.append, sleep=sleep, clock=lambda: 1000.0)


def test_a_manual_address_kept_from_the_new_address_stays(sys_net):
    nm, changes = FakeNM(), []

    async def go():
        cable = _cable(sys_net, nm, changes)
        cable._sleep = lambda s: asyncio.sleep(3600)  # the keep wait does not run out here
        told = await cable.change("manual", "192.0.2.50/24", "192.0.2.1", "192.0.2.1")
        assert told == {"address": "192.0.2.50", "until": 1000.0 + wired.KEEP_S}
        assert not cable.keep("192.0.2.107", loopback=False), "the old address proves nothing"
        assert cable.keep("192.0.2.50", loopback=False)
        assert cable.pending is None
    asyncio.run(go())
    assert nm.profile["method"] == "manual" and nm.profile["addresses"] == "192.0.2.50/24"
    assert changes[-1] is None


def test_not_kept_in_time_the_old_address_comes_back(sys_net):
    nm, changes = FakeNM(), []

    async def go():
        cable = _cable(sys_net, nm, changes)
        await cable.change("manual", "192.0.2.50/24", "192.0.2.1", "192.0.2.1")
        await cable._timer
        assert cable.pending is None
    asyncio.run(go())
    assert nm.profile["method"] == "auto" and nm.profile["addresses"] == ""


def test_the_panel_can_keep_it_and_a_refused_address_changes_nothing(sys_net):
    async def go():
        nm = FakeNM()
        cable = _cable(sys_net, nm, [])
        cable._sleep = lambda s: asyncio.sleep(3600)
        await cable.change("manual", "192.0.2.50/24", "192.0.2.1", "192.0.2.1")
        assert cable.keep("127.0.0.1", loopback=True)
        refusing = FakeNM(refuse_up=True)
        other = _cable(sys_net, refusing, [])
        with pytest.raises(ValueError, match="could not take"):
            await other.change("manual", "192.0.2.60/24", "192.0.2.1", "192.0.2.1")
        assert refusing.profile["method"] == "auto" and other.pending is None
    asyncio.run(go())


def test_the_row_is_shown_with_a_cable_or_a_manual_address(sys_net):
    cable = wired.Cable(run=FakeNM(), sys_net=sys_net)
    assert cable.shown()
    (sys_net / "eth0" / "carrier").write_text("0\n")
    assert not cable.shown()
    cable.manual = True
    assert cable.shown(), "a fixed address keeps the row, cable or not"
    assert not wired.Cable(run=FakeNM(), sys_net=sys_net / "none").shown(), "no port, no row"


def test_the_wi_fi_port_is_changed_the_same_way(tmp_path):
    """ADR-0123 decision 2: the connected Wi-Fi network's address, through
    its own profile, kept or put back exactly as the cable's."""
    (tmp_path / "wlan0").mkdir()
    (tmp_path / "wlan0" / "carrier").write_text("1\n")
    nm = FakeNM()

    async def go():
        port = wired.Cable(device="wlan0", run=nm, sys_net=tmp_path, sleep=lambda s: asyncio.sleep(0), clock=lambda: 0.0)
        told = await port.change("manual", "192.0.2.60/24", "192.0.2.1", ["192.0.2.1"])
        assert told["address"] == "192.0.2.60"
        assert any(c[:2] == ("connection", "up") and "wlan0" in c for c in nm.calls)
        await port._timer
    asyncio.run(go())
    assert nm.profile["method"] == "auto", "not kept: put back"


def test_without_a_connection_the_sentence_names_the_port(tmp_path):
    class NoProfile(FakeNM):
        async def __call__(self, *args, timeout=None):
            if args[:3] == ("-t", "-f", "GENERAL.CONNECTION"):
                return 0, "GENERAL.CONNECTION:--\n", ""
            return await super().__call__(*args, timeout=timeout)

    async def go(device):
        with pytest.raises(ValueError) as refused:
            await wired.Cable(device=device, run=NoProfile(), sys_net=tmp_path).change("auto")
        return str(refused.value)
    assert asyncio.run(go("wlan0")) == "Join a Wi-Fi network first."
    assert "cable" in asyncio.run(go("eth0"))


@pytest.mark.asyncio
async def test_the_routes_reach_each_port_and_leave_the_wi_fi_details_alone():
    """`/network/wifi` is the connected network's details (0.9.3); the
    address is `/network/wifi/address`. Keep counts for whichever waits."""
    from aiohttp.test_utils import TestClient, TestServer
    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer

    class Port:
        def __init__(self, name):
            self.name, self.pending = name, None
        async def status(self):
            return {"port": True, "link": True, "speed": None, "address": f"{self.name}/24", "method": "auto",
                    "profile": self.name, "gateway": None, "dns": []}
        def keep(self, arrived_at, loopback):
            return loopback

    cable, wifi = Port("cable"), Port("wifi")
    async with TestClient(TestServer(StateServer(StateStore({}), cable=cable, wifi_address=wifi).make_app())) as client:
        assert (await (await client.get("/network/cable")).json())["profile"] == "cable"
        assert (await (await client.get("/network/wifi/address")).json())["profile"] == "wifi"
        wifi.pending = type("P", (), {"address": "10.0.0.9"})()
        r = await client.post("/network/cable", json={"method": "auto"})
        assert r.status == 409, "one change waits at a time"
        assert (await client.post("/network/keep")).status == 200, "loopback keeps whichever waits"


def test_an_automatic_address_that_comes_late_is_waited_for(sys_net):
    """guestpi, 2026-10-08: on Wi-Fi the address came only after the rejoin,
    and the phone was told to open http://None:8090."""
    class Late(FakeNM):
        def __init__(self):
            super().__init__(method="manual")
            self.profile.update(addresses="192.0.2.231/24", gateway="192.0.2.1", dns="192.0.2.1")
            self.reads = 0
        def live(self):
            if self.profile["method"] == "auto":
                self.reads += 1
                if self.reads < 3:
                    return "", "", []
            return super().live()

    async def go():
        nm = Late()
        port = wired.Cable(run=nm, sys_net=sys_net, sleep=lambda s: asyncio.sleep(0), clock=lambda: 0.0)
        port._timer = None
        told = await port.change("auto")
        return told
    assert asyncio.run(go())["address"] == "192.0.2.107"


class Ports:
    """`nmcli` for the cable-first rule: the Wi-Fi port's state, and what was done."""

    def __init__(self, wifi="HomeNet"):
        self.wifi = wifi
        self.done = []

    cable_up = True

    async def __call__(self, *args, timeout=None):
        if args[:3] == ("-t", "-f", "GENERAL.STATE,GENERAL.CONNECTION") and args[-1] == "eth0":
            if self.cable_up:
                return 0, "GENERAL.STATE:100 (connected)\nGENERAL.CONNECTION:Wired connection 1\n", ""
            return 0, "GENERAL.STATE:70 (connecting (getting IP configuration))\nGENERAL.CONNECTION:Wired connection 1\n", ""
        if args[:3] == ("-t", "-f", "GENERAL.STATE,GENERAL.CONNECTION"):
            if self.wifi:
                return 0, f"GENERAL.STATE:100 (connected)\nGENERAL.CONNECTION:{self.wifi}\n", ""
            return 0, "GENERAL.STATE:30 (disconnected)\nGENERAL.CONNECTION:--\n", ""
        self.done.append(args)
        if args[:2] == ("device", "disconnect"):
            self.wifi = None
        return 0, "", ""


def test_the_cable_wins_and_wi_fi_comes_back_without_it(sys_net):
    """George, 2026-10-08: "The cable should win"."""
    ports = Ports()
    rule = wired.CableFirst(run=ports, sys_net=sys_net)

    async def go():
        had = await rule.step(None)
        assert had and ports.done == [("device", "disconnect", "wlan0")]
        had = await rule.step(had)
        assert len(ports.done) == 1, "already off: nothing more"
        (sys_net / "eth0" / "carrier").write_text("0\n")
        had = await rule.step(had)
        assert ports.done[-1] == ("device", "connect", "wlan0") and not had
        await rule.step(had)
        assert len(ports.done) == 2, "no cable, no link change: nothing"
    asyncio.run(go())


def test_the_setup_network_is_never_taken_down_for_a_cable(sys_net):
    ports = Ports(wifi=wired.SETUP_PROFILE)
    asyncio.run(wired.CableFirst(run=ports, sys_net=sys_net).step(None))
    assert ports.done == []


def test_the_setup_profile_is_setup_s_own():
    from gexis_core import setup_network
    assert wired.SETUP_PROFILE == setup_network.PROFILE


def test_the_wi_fi_stays_until_the_cable_has_its_address(sys_net):
    """guestpi: a link, still getting its address - the Wi-Fi had already
    gone, and the player had no network for some seconds."""
    ports = Ports()
    ports.cable_up = False
    rule = wired.CableFirst(run=ports, sys_net=sys_net)
    assert asyncio.run(rule.step(None)) and ports.done == []
    ports.cable_up = True
    asyncio.run(rule.step(True))
    assert ports.done == [("device", "disconnect", "wlan0")]
