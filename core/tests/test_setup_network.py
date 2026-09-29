"""ADR-0104: when the device needs setup, and when the setup network opens."""
from __future__ import annotations

import asyncio

import pytest

from gexis_core import setup_network as sn


class FakeNM:
    """`nmcli` as far as the setup network asks it anything. `devices` is
    what `nmcli device` reports, and may be a list of reports to walk through
    one call at a time; `saved` maps SSID to connection name."""

    def __init__(self, *, devices=(), saved=None, in_range=(), hotspot_rc=0, up_rc=0):
        self.devices = devices if isinstance(devices, list) and devices and isinstance(devices[0], list) else [list(devices)]
        self.saved = dict(saved or {})
        self.in_range = set(in_range)
        self.hotspot_rc = hotspot_rc
        self.up_rc = up_rc
        self.calls: list[tuple] = []
        self.profiles: set[str] = set()
        self.unblocked = 0
        #: Set by `setup`, so the hotspot's moment can be read off the clock.
        self.clock = None
        self.hotspot_at = None

    async def __call__(self, *args, timeout=None):
        self.calls.append(args)
        if args[-1] == "device" and "DEVICE,TYPE,STATE,CONNECTION" in args:
            report = self.devices[0] if len(self.devices) == 1 else self.devices.pop(0)
            return 0, "\n".join(":".join(row) for row in report), ""
        if args[:4] == ("-t", "-f", "NAME,UUID,TYPE", "connection"):
            rows = [f"{name}:uuid-{name}:802-11-wireless" for name in self.saved.values()]
            rows += [f"{p}:uuid-{p}:802-11-wireless" for p in self.profiles]
            return 0, "\n".join(rows), ""
        if args[:3] == ("-t", "-f", "802-11-wireless.ssid"):
            name = args[-1].removeprefix("uuid-")
            ssid = next((s for s, n in self.saved.items() if n == name), name)
            return 0, f"802-11-wireless.ssid:{ssid}", ""
        if args[:4] == ("-t", "-f", "NAME", "connection"):
            return 0, "\n".join(sorted(self.profiles | set(self.saved.values()))), ""
        if args[:2] == ("-g", "IP4.ADDRESS"):
            return 0, "192.168.1.50/24\n", ""
        if args[:3] == ("device", "wifi", "hotspot"):
            if self.hotspot_at is None and self.clock is not None:
                self.hotspot_at = self.clock()
            if self.hotspot_rc == 0:
                self.profiles.add(sn.PROFILE)
            return self.hotspot_rc, "", "" if self.hotspot_rc == 0 else "Error: no AP mode"
        if args[:2] == ("connection", "delete"):
            self.profiles.discard(args[2])
            return 0, "", ""
        if args[:2] == ("connection", "up"):
            return self.up_rc, "", "" if self.up_rc == 0 else "Error: secrets were required"
        if "list" in args and "--rescan" in args:
            return 0, "\n".join(sorted(self.in_range | {sn.SSID})), ""
        return 0, "", ""

    async def unblock(self):
        self.unblocked += 1
        self.calls.append(("rfkill", "unblock", "wifi"))

    def did(self, *prefix):
        return [c for c in self.calls if c[: len(prefix)] == prefix]


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    async def sleep(self, seconds):
        self.now += seconds
        # Yield, as a real sleep does, or a loop that only sleeps never lets
        # the test look at it.
        await asyncio.sleep(0)


def setup(tmp_path, nm, *, panel=True, carrier=False, stations=0, trial=None):
    drm = tmp_path / "drm"
    (drm / "card1-HDMI-A-1").mkdir(parents=True)
    (drm / "card1-HDMI-A-1" / "status").write_text("connected\n" if panel else "disconnected\n")
    net = tmp_path / "net"
    (net / "eth0").mkdir(parents=True)
    (net / "eth0" / "carrier").write_text("1\n" if carrier else "0\n")
    trial_file = tmp_path / "trial"
    if trial is not None:
        trial_file.write_text(trial)
    clock = Clock()
    nm.clock = clock

    async def count():
        return stations() if callable(stations) else stations

    return sn.SetupNetwork(
        run=nm, clock=clock, sleep=clock.sleep,
        marker=tmp_path / "setup-done", password_file=tmp_path / "setup-password",
        trial_file=trial_file, drm=drm, net_root=net, stations=count,
        unblock=nm.unblock,
    ), clock


WIFI_UP = [("wlan0", "wifi", "connected", "preconfigured"), ("lo", "loopback", "connected (externally)", "lo")]
NOTHING = [("wlan0", "wifi", "disconnected", "--"), ("eth0", "ethernet", "unavailable", "--")]
ETH_UP = [("eth0", "ethernet", "connected", "Wired connection 1"), ("wlan0", "wifi", "disconnected", "--")]


def run(coro):
    return asyncio.run(coro)


# -- needs setup (§2) ------------------------------------------------------


def test_a_saved_wifi_means_no_setup(tmp_path):
    assert not sn.needs_setup(1, tmp_path / "setup-done")


def test_the_marker_means_no_setup(tmp_path):
    (tmp_path / "setup-done").touch()
    assert not sn.needs_setup(0, tmp_path / "setup-done")


def test_nothing_saved_and_no_marker_needs_setup(tmp_path):
    assert sn.needs_setup(0, tmp_path / "setup-done")


# -- the decision at boot (§3) ---------------------------------------------


def test_a_provisioned_card_on_its_wifi_never_opens_the_network(tmp_path):
    nm = FakeNM(devices=WIFI_UP, saved={"Home": "preconfigured"})
    net, _ = setup(tmp_path, nm)
    run(net.run())
    assert not net.needed and net.status()["network"] == "online"
    assert not nm.did("device", "wifi", "hotspot")
    assert net.status()["address"] is None, "nothing to show a configured device"
    assert net.status()["panel"], "known from the start, not only once the network opens"


def test_ethernet_with_an_address_never_opens_the_network_even_when_setup_is_needed(tmp_path):
    """ADR-0031 amendment 8: setup runs over Ethernet, and there is no AP."""
    nm = FakeNM(devices=ETH_UP)
    net, _ = setup(tmp_path, nm, carrier=True)
    run(net.run())
    assert net.needed and net.status()["network"] == "online"
    assert not nm.did("device", "wifi", "hotspot")
    assert net.status()["address"] == "http://192.168.1.50:8090/", "the page is on the LAN"


def test_a_new_device_without_a_cable_opens_after_15_s_not_90(tmp_path):
    nm = FakeNM(devices=NOTHING)
    net, clock = setup(tmp_path, nm, stations=1)

    async def go():
        task = asyncio.create_task(net.run())
        while nm.hotspot_at is None:
            await asyncio.sleep(0)
        task.cancel()
        return nm.hotspot_at

    opened = run(go())
    assert sn.NEW_WAIT_S <= opened < sn.CONFIGURED_WAIT_S


def test_a_new_device_with_a_link_but_no_address_waits_the_90_s(tmp_path):
    nm = FakeNM(devices=NOTHING)
    net, clock = setup(tmp_path, nm, carrier=True, stations=1)

    async def go():
        task = asyncio.create_task(net.run())
        while nm.hotspot_at is None:
            await asyncio.sleep(0)
        task.cancel()
        return nm.hotspot_at

    assert run(go()) >= sn.CONFIGURED_WAIT_S


def test_a_configured_device_waits_90_s_for_its_wifi(tmp_path):
    nm = FakeNM(devices=NOTHING, saved={"Home": "preconfigured"})
    net, clock = setup(tmp_path, nm, stations=1)

    async def go():
        task = asyncio.create_task(net.run())
        while nm.hotspot_at is None:
            await asyncio.sleep(0)
        task.cancel()
        return nm.hotspot_at

    assert run(go()) >= sn.CONFIGURED_WAIT_S
    assert not net.needed, "a configured device needs the network, not setup"


def test_wifi_that_arrives_inside_the_90_s_keeps_the_network_closed(tmp_path):
    nm = FakeNM(devices=[NOTHING] * 10 + [WIFI_UP], saved={"Home": "preconfigured"})
    net, clock = setup(tmp_path, nm)
    run(net.run())
    assert net.status()["network"] == "online" and clock.now < sn.CONFIGURED_WAIT_S
    assert not nm.did("device", "wifi", "hotspot")


# -- the network itself ------------------------------------------------------


def test_the_profile_is_made_never_to_come_up_by_itself(tmp_path):
    nm = FakeNM(devices=NOTHING)
    net, _ = setup(tmp_path, nm)
    run(net.open())
    assert nm.did("connection", "modify", sn.PROFILE, "connection.autoconnect", "no")


def test_a_leftover_profile_is_deleted_at_startup(tmp_path):
    nm = FakeNM(devices=WIFI_UP, saved={"Home": "preconfigured"})
    nm.profiles.add(sn.PROFILE)
    net, _ = setup(tmp_path, nm)
    run(net.run())
    assert nm.did("connection", "delete", sn.PROFILE) and sn.PROFILE not in nm.profiles


def test_with_a_panel_the_password_is_made_up_and_kept(tmp_path):
    nm = FakeNM(devices=NOTHING)
    net, _ = setup(tmp_path, nm, panel=True)
    run(net.open())
    first = net.status()["password"]
    assert len(first) == 8 and set(first) <= set(sn.PASSWORD_ALPHABET)
    net2, _ = setup(tmp_path / "again", nm, panel=True)
    net2._password_file = tmp_path / "setup-password"
    run(net2.open())
    assert net2.status()["password"] == first, "a restart keeps the password on the screen"


def test_without_a_panel_the_password_is_the_fixed_one(tmp_path):
    nm = FakeNM(devices=NOTHING)
    net, _ = setup(tmp_path, nm, panel=False)
    run(net.open())
    assert net.status()["password"] == "gexis-setup" and not net.status()["panel"]


def test_the_password_is_shown_only_while_the_network_is_open(tmp_path):
    nm = FakeNM(devices=WIFI_UP, saved={"Home": "preconfigured"})
    net, _ = setup(tmp_path, nm)
    run(net.run())
    assert net.status()["password"] is None and net.status()["ssid"] is None


def test_a_network_that_does_not_come_up_says_why(tmp_path):
    nm = FakeNM(devices=NOTHING, hotspot_rc=4)
    net, _ = setup(tmp_path, nm)
    run(net.open())
    assert net.status()["network"] == "failed" and "no AP mode" in net.status()["reason"]


# -- the retry (§3, amendment 7) --------------------------------------------


def hold(net, nm, clock, until):
    async def go():
        task = asyncio.create_task(net.run())
        for _ in range(10_000):
            await asyncio.sleep(0)
            if until():
                break
        task.cancel()
    run(go())


def test_the_retry_rejoins_a_saved_network_in_range_when_nobody_is_on(tmp_path):
    nm = FakeNM(devices=NOTHING, saved={"Home": "preconfigured"}, in_range={"Home", "Neighbour"})
    net, clock = setup(tmp_path, nm, stations=0)
    hold(net, nm, clock, lambda: net.status()["network"] == "online")
    assert net.status()["network"] == "online"
    assert nm.did("connection", "up", "preconfigured")
    assert clock.now >= sn.CONFIGURED_WAIT_S + sn.RETRY_S


def test_the_retry_never_scans_with_a_phone_on_the_network(tmp_path):
    nm = FakeNM(devices=NOTHING, saved={"Home": "preconfigured"}, in_range={"Home"})
    net, clock = setup(tmp_path, nm, stations=1)
    hold(net, nm, clock, lambda: clock.now > sn.CONFIGURED_WAIT_S + 3 * sn.RETRY_S)
    assert net.status()["network"] == "open"
    assert not [c for c in nm.calls if "--rescan" in c]


def test_a_saved_network_out_of_range_keeps_the_setup_network(tmp_path):
    nm = FakeNM(devices=NOTHING, saved={"Home": "preconfigured"}, in_range={"Neighbour"})
    net, clock = setup(tmp_path, nm, stations=0)
    hold(net, nm, clock, lambda: clock.now > sn.CONFIGURED_WAIT_S + 3 * sn.RETRY_S)
    assert net.status()["network"] == "open" and not nm.did("connection", "up")


def test_the_setup_network_seeing_itself_is_not_a_way_home(tmp_path):
    """Finding 099: the scan while hosting lists `gexis-setup`."""
    nm = FakeNM(devices=NOTHING, in_range=set())
    nm.saved = {}
    net, clock = setup(tmp_path, nm, stations=0)
    hold(net, nm, clock, lambda: clock.now > sn.NEW_WAIT_S + 2 * sn.RETRY_S)
    assert net.status()["network"] == "open" and not nm.did("connection", "up")


def test_a_failed_rejoin_opens_the_setup_network_again_with_the_reason(tmp_path):
    nm = FakeNM(devices=NOTHING, saved={"Home": "preconfigured"}, in_range={"Home"}, up_rc=4)
    net, clock = setup(tmp_path, nm, stations=0)
    hold(net, nm, clock, lambda: len(nm.did("connection", "up")) == 1 and net.status()["network"] == "open")
    assert net.status()["network"] == "open"
    assert net.status()["reason"] == "The password was not accepted."
    assert net.status()["failed"] == "Home"


# -- the trial ---------------------------------------------------------------


def test_a_trial_opens_the_network_over_working_wifi_and_is_read_once(tmp_path):
    nm = FakeNM(devices=WIFI_UP, saved={"Home": "preconfigured"}, in_range={"Home"})
    net, clock = setup(tmp_path, nm, stations=0, trial="retry=60\n")
    hold(net, nm, clock, lambda: net.status()["network"] == "online")
    assert nm.did("device", "wifi", "hotspot"), "the trial opens it with the Wi-Fi up"
    assert nm.did("connection", "up", "preconfigured"), "the retry gives the Wi-Fi back"
    assert clock.now == pytest.approx(60.0)
    assert not (tmp_path / "trial").exists()


def test_a_trial_retry_is_never_shorter_than_30_s(tmp_path):
    (tmp_path / "t").write_text("retry=1\n")
    assert sn.read_trial(tmp_path / "t") == 30.0
    (tmp_path / "t").write_text("\n")
    assert sn.read_trial(tmp_path / "t") == sn.RETRY_S
    assert sn.read_trial(tmp_path / "missing") is None


def test_online_ignores_loopback_and_the_setup_network():
    assert sn.online([("lo", "loopback", "connected (externally)", "lo")]) is None
    assert sn.online([("wlan0", "wifi", "connected", sn.PROFILE)]) is None
    assert sn.online([("wlan0", "wifi", "connecting (getting IP configuration)", "Home")]) is None
    assert sn.online(ETH_UP) == "eth0"


# -- what is published (§5) --------------------------------------------------


def test_the_broadcast_follows_the_network_and_never_carries_the_password(tmp_path):
    nm = FakeNM(devices=NOTHING, saved={"Home": "preconfigured"}, in_range={"Home"})
    seen = []
    net, clock = setup(tmp_path, nm, stations=0)
    net._on_change = seen.append
    hold(net, nm, clock, lambda: net.status()["network"] == "online")
    assert [s["network"] for s in seen] == ["waiting", "open", "joining", "online"]
    assert all(s["password"] is None for s in seen)
    assert seen[1]["ssid"] == sn.SSID and seen[1]["address"] == "http://10.42.0.1:8090/"


def test_the_state_store_refuses_a_password():
    from gexis_core.state import StateStore

    store = StateStore({})
    with pytest.raises(ValueError):
        store.set_setup({"network": "open", "password": "naccw4n2"})
    store.set_setup({"network": "open", "password": None})
    assert store.state.to_json()["setup"]["network"] == "open"


def test_the_reason_is_networkmanagers_error_line_not_its_hint():
    """Found on gexis, 2026-09-28: the last line is a hint to run journalctl."""
    err = ("Error: Connection activation failed: The Wi-Fi network could not be found\n"
           "Hint: use 'journalctl -xe NM_CONNECTION=c936 + NM_DEVICE=wlan0' to get more details.")
    assert sn.join_reason(4, err) == "No network with that name is in range."
    err = ("Error: Connection activation failed: The base network connection was interrupted\n"
           "Hint: use 'journalctl -xe NM_CONNECTION=c936 + NM_DEVICE=wlan0' to get more details.")
    assert sn.join_reason(4, err) == "The base network connection was interrupted."
    wrong = ("Warning: password for '802-11-wireless-security.psk' not given in 'passwd-file' and nmcli cannot ask without '--ask' option.\n"
             "Error: Connection activation failed: Secrets were required, but not provided")
    assert sn.join_reason(4, wrong) == "The password was not accepted."
    assert sn.join_reason(124, "") == "It took too long. The network may be out of range."


def test_the_radio_is_switched_on_before_the_network_on_2_4_ghz(tmp_path):
    """Found on the first blank card, 2026-09-29: Raspberry Pi OS keeps Wi-Fi
    blocked until a country is set, and a new device has none."""
    nm = FakeNM(devices=NOTHING)
    net, _ = setup(tmp_path, nm)
    run(net.open())
    order = [c[:3] for c in nm.calls]
    assert order.index(("rfkill", "unblock", "wifi")) < order.index(("device", "wifi", "hotspot"))
    assert order.index(("radio", "wifi", "on")) < order.index(("device", "wifi", "hotspot"))
    hotspot = nm.did("device", "wifi", "hotspot")[0]
    assert hotspot[hotspot.index("band") + 1] == "bg", "nothing on 5 GHz before a country is known"
