"""ADR-0104 §4: the answers the core keeps, and applying them."""
from __future__ import annotations

import asyncio
import stat

import pytest

from gexis_core import setup_network as sn
from gexis_core.setup_flow import SetupFlow

from test_setup_network import NOTHING, FakeNM, setup


class FakeSettings:
    def __init__(self, **values):
        self.values = {"device_name": "gexis", **values}
        self.sets = []

    def value(self, key):
        return self.values.get(key)

    def set(self, key, value):
        if key == "output_device" and value == "Nowhere":
            raise ValueError("not an option")
        self.sets.append((key, value))
        self.values[key] = value


def make(tmp_path, nm, settings=None, **kw):
    kw_servers = {"servers": kw.pop("servers", [])}
    net, clock = setup(tmp_path, nm, **kw)
    countries, reboots = [], []

    async def country(c):
        countries.append(c)

    async def reboot():
        reboots.append(True)

    servers = kw_servers.pop("servers", [])

    async def find():
        return list(servers)

    flow = SetupFlow(
        net, settings or FakeSettings(), reboot=reboot,
        answers=tmp_path / "answers.json", marker=tmp_path / "setup-done",
        set_country=country, find_servers=find, sleep=clock.sleep,
    )
    return flow, net, clock, countries, reboots


def test_the_password_is_kept_but_never_handed_back(tmp_path):
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    out = flow.save({"ssid": "Home", "password": "hunter22", "name": "Den"})
    assert "password" not in out and out["has_password"] and out["ssid"] == "Home"
    assert stat.S_IMODE((tmp_path / "answers.json").stat().st_mode) == 0o600


def test_unknown_or_mistyped_answers_are_refused(tmp_path):
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    with pytest.raises(ValueError):
        flow.save({"favourite": "x"})
    with pytest.raises(ValueError):
        flow.save({"spotify": "yes"})


def test_a_new_password_clears_the_last_error(tmp_path):
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    flow._write({"ssid": "Home", "error": {"ssid": "Home", "reason": "The password was not accepted."}})
    assert flow.save({"password": "again123"}).get("error") is None


def test_country_from_the_time_zone(tmp_path):
    tab = tmp_path / "zone.tab"
    tab.write_text("# comment\nDE\t+5230+01322\tEurope/Berlin\tmost of Germany\nRO\t+4426+02606\tEurope/Bucharest\n")
    assert sn.country_for("Europe/Berlin", tab) == "DE"
    assert sn.country_for("Europe/Bucharest", tab) == "RO"
    assert sn.country_for("Mars/Olympus", tab) is None
    assert sn.country_for(None, tab) is None


def finish(flow, net):
    async def go():
        net._state = "open"
        net._needed = True
        flow.finish()
        await flow._task
    asyncio.run(go())


def test_finishing_writes_the_settings_then_joins_and_marks_the_device_set_up(tmp_path):
    nm = FakeNM(devices=NOTHING)
    settings = FakeSettings()
    flow, net, _, countries, reboots = make(tmp_path, nm, settings)
    flow.save({"ssid": "Home", "password": "hunter22", "name": "gexis", "timezone": "Europe/Berlin",
               "spotify": False, "bluetooth": True, "headless": False, "output": "HiFiBerry DAC+ HD",
               "clock": "12 h"})
    finish(flow, net)
    keys = [k for k, _ in settings.sets]
    assert "timezone" in keys and "spotify_enabled" in keys and "output_device" in keys
    assert ("clock_format", "12 h") in settings.sets
    assert "device_name" not in keys, "an unchanged value is not written again"
    assert countries == ["DE"]
    add = nm.did("connection", "add")[0]
    assert add[add.index("con-name") + 1] == "Home" and "hunter22" in add
    assert (tmp_path / "setup-done").exists() and not (tmp_path / "answers.json").exists()
    assert net.status()["network"] == "online" and not net.needed
    assert reboots == [], "no rename, no restart"


def test_a_rename_restarts_the_device_after_the_join(tmp_path):
    nm = FakeNM(devices=NOTHING)
    flow, net, _, _, reboots = make(tmp_path, nm)
    flow.save({"ssid": "Home", "password": "hunter22", "name": "Den"})
    finish(flow, net)
    assert reboots == [True]


def test_a_wrong_password_keeps_every_answer_but_the_password_and_reopens_setup(tmp_path):
    nm = FakeNM(devices=NOTHING, up_rc=4)
    flow, net, _, _, reboots = make(tmp_path, nm)
    flow.save({"ssid": "Home", "password": "wrongpass", "name": "Den", "timezone": "Europe/Berlin"})
    finish(flow, net)
    kept = flow.answers()
    assert kept["name"] == "Den" and kept["timezone"] == "Europe/Berlin" and kept["ssid"] == "Home"
    assert not kept["has_password"] and kept["step"] == "wifi"
    assert kept["error"] == {"ssid": "Home", "reason": "The password was not accepted."}
    assert nm.did("connection", "delete", "Home")[-1], "the wrong password is not kept by NetworkManager"
    assert net.status()["network"] == "open", "the setup network is back"
    assert net.status()["reason"] == "The password was not accepted." and net.status()["failed"] == "Home"
    assert not (tmp_path / "setup-done").exists() and reboots == []


def test_one_refused_setting_does_not_stop_setup(tmp_path):
    nm = FakeNM(devices=NOTHING)
    flow, net, *_ = make(tmp_path, nm)
    flow.save({"ssid": "Home", "password": "hunter22", "output": "Nowhere", "timezone": "Europe/Berlin"})
    finish(flow, net)
    assert (tmp_path / "setup-done").exists()


def test_without_a_network_there_is_nothing_to_finish(tmp_path):
    flow, net, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    net._state = "open"
    with pytest.raises(ValueError):
        flow.finish()


def test_the_retry_keeps_running_after_a_failed_join_from_setup(tmp_path):
    """The loop once ended when the network went down, so a join from setup
    that failed and reopened it left the device with no retry at all."""
    nm = FakeNM(devices=NOTHING, saved={"Home": "preconfigured"}, in_range=set(), up_rc=4)
    net, clock = setup(tmp_path, nm, stations=0)

    async def go():
        task = asyncio.create_task(net.run())
        while net.status()["network"] != "open":
            await asyncio.sleep(0)
        await net.join_new("Other", "wrongpass")
        assert net.status()["network"] == "open"
        nm.in_range = {"Home"}
        nm.up_rc = 0
        for _ in range(10_000):
            await asyncio.sleep(0)
            if net.status()["network"] == "online":
                break
        task.cancel()

    asyncio.run(go())
    assert net.status()["network"] == "online"
    assert nm.did("connection", "up", "preconfigured")


def test_without_an_address_one_lyrion_server_found_after_joining_is_used(tmp_path):
    nm = FakeNM(devices=NOTHING)
    settings = FakeSettings()
    flow, net, clock, *_ = make(tmp_path, nm, settings,
                                servers=[{"address": "192.168.1.10:9000", "name": "den-lms"}])
    seen = []
    net._on_change = seen.append
    flow.save({"ssid": "Home", "password": "hunter22", "lms_mode": "find"})
    finish(flow, net)
    assert ("lms_server", "192.168.1.10:9000") in settings.sets
    done = [s for s in seen if s["network"] == "done"][0]
    assert done["finished"] == {"ssid": "Home", "restarting": False, "restart_for": None, "name": "gexis",
                                "library": {"state": "found", "name": "den-lms", "address": "192.168.1.10:9000"}}
    assert net.status()["network"] == "online" and not net.status()["finished"]


def test_several_servers_are_named_and_none_is_chosen(tmp_path):
    nm = FakeNM(devices=NOTHING)
    settings = FakeSettings()
    flow, net, *_ = make(tmp_path, nm, settings,
                         servers=[{"address": "a:9000", "name": "one"}, {"address": "b:9000", "name": "two"}])
    seen = []
    net._on_change = seen.append
    flow.save({"ssid": "Home", "password": "hunter22", "lms_mode": "find"})
    finish(flow, net)
    assert not [k for k, _ in settings.sets if k == "lms_server"]
    assert [s for s in seen if s["network"] == "done"][0]["finished"]["library"] == {"state": "several", "names": ["one", "two"]}


def test_an_address_given_in_setup_is_not_searched_over(tmp_path):
    nm = FakeNM(devices=NOTHING)
    flow, net, *_ = make(tmp_path, nm, servers=[{"address": "x:9000", "name": "x"}])
    seen = []
    net._on_change = seen.append
    flow.save({"ssid": "Home", "password": "hunter22", "lms": "192.168.1.5:9000", "lms_mode": "address"})
    finish(flow, net)
    assert [s for s in seen if s["network"] == "done"][0]["finished"]["library"] == {"state": "given", "address": "192.168.1.5:9000"}


def test_the_last_screen_says_a_rename_restarts(tmp_path):
    nm = FakeNM(devices=NOTHING)
    flow, net, _, _, reboots = make(tmp_path, nm)
    seen = []
    net._on_change = seen.append
    flow.save({"ssid": "Home", "password": "hunter22", "name": "Den"})
    finish(flow, net)
    assert [s for s in seen if s["network"] == "done"][0]["finished"]["restarting"] is True
    assert reboots == [True]
    assert seen[-1]["network"] == "done", "no ordinary screen between setup and the restart"


def test_nothing_is_searched_for_or_adopted_without_being_asked(tmp_path):
    """George, 2026-09-29: a server the user did not ask for, found behind
    his back, is the thing to avoid."""
    nm = FakeNM(devices=NOTHING)
    settings = FakeSettings()
    flow, net, *_ = make(tmp_path, nm, settings, servers=[{"address": "x:9000", "name": "x"}])
    seen = []
    net._on_change = seen.append
    flow.save({"ssid": "Home", "password": "hunter22"})
    finish(flow, net)
    assert not [k for k, _ in settings.sets if k.startswith("lms")]
    assert [s for s in seen if s["network"] == "done"][0]["finished"]["library"] == {"state": "unchanged"}


def test_i_dont_use_lyrion_switches_it_off_and_ignores_a_typed_address(tmp_path):
    nm = FakeNM(devices=NOTHING)
    settings = FakeSettings(lms_enabled=True)
    flow, net, *_ = make(tmp_path, nm, settings)
    flow.save({"ssid": "Home", "password": "hunter22", "lms": "1.2.3.4:9000", "lms_mode": "off"})
    finish(flow, net)
    assert ("lms_enabled", False) in settings.sets
    assert not [k for k, _ in settings.sets if k == "lms_server"], "the field is not the answer"


def test_an_unknown_lms_mode_is_refused(tmp_path):
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    with pytest.raises(ValueError):
        flow.save({"lms_mode": "maybe"})


def test_the_panel_never_leaves_setup_between_the_join_and_the_last_screen(tmp_path):
    """George, 2026-09-29: the home screen showed between the join and the
    last setup screen, for as long as the Lyrion search took."""
    nm = FakeNM(devices=NOTHING)
    flow, net, *_ = make(tmp_path, nm, servers=[{"address": "a:9000", "name": "one"}])
    seen = []
    net._on_change = seen.append
    flow.save({"ssid": "Home", "password": "hunter22", "lms_mode": "find"})
    finish(flow, net)
    states = [s["network"] for s in seen]
    assert states.index("done") == states.index("joining") + 1, states
    assert states[-1] == "online"


def test_a_screen_chosen_in_setup_restarts_at_the_end_where_keep_is_asked(tmp_path):
    """ADR-0109 decision 5: the screen is written during setup and the
    restart that ends it is where the panel asks Keep this screen?."""
    from gexis_core import setup_network as sn
    net = sn.SetupNetwork()
    net.finished("Home", {"state": "off"}, "screen", "gexis")
    assert net.status()["finished"]["restart_for"] == "screen" and net.status()["finished"]["restarting"]
    net.finished("Home", {"state": "off"}, True, "gexis")
    assert net.status()["finished"]["restart_for"] == "name"


def test_the_phone_is_told_in_words_not_the_core_s_text():
    """George, 2026-10-04: "Human readable errors." The core's own text is
    for the log."""
    from gexis_core import setup_flow as sf
    assert sf.said("no network chosen") == "Choose a Wi-Fi network first, or connect the player by cable."
    assert sf.said("setup is not running") == "Setup has already finished. Open the player at its address instead."
    assert sf.said("unknown screen Acme/Panel 9") == "That screen isn't on the list. Choose another, or Headless."
    assert sf.said("choose a screen or headless, not both") == "Choose a screen or Headless, not both."
    for raw in ("answers must be an object", "unknown answer colour", "step must be text", "setup is not wired up"):
        assert sf.said(raw) == "Something went wrong saving that. Try again."
