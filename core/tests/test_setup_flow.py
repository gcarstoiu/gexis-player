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
    net, clock = setup(tmp_path, nm, **kw)
    countries, reboots = [], []

    async def country(c):
        countries.append(c)

    async def reboot():
        reboots.append(True)

    flow = SetupFlow(
        net, settings or FakeSettings(), reboot=reboot,
        answers=tmp_path / "answers.json", marker=tmp_path / "setup-done",
        set_country=country,
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
