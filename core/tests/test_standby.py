"""ADR-0135: display standby - the screen off, the player still playing."""
from __future__ import annotations

import asyncio

from aiohttp.test_utils import TestClient, TestServer

from gexis_core import standby as sb
from gexis_core.peppy import PeppyController, UnattendedPlayback
from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer


def test_off_is_the_output_off_in_the_kiosks_session():
    cmd = sb.output_command(False, {"GEXIS_SCREEN_CONNECTOR": "HDMI-A-2"}, 1000)
    assert cmd[:4] == ["runuser", "-u", "pi", "--"]
    assert "XDG_RUNTIME_DIR=/run/user/1000" in cmd and "WAYLAND_DISPLAY=wayland-0" in cmd
    assert cmd[-4:] == ["wlr-randr", "--output", "HDMI-A-2", "--off"]


def test_on_gives_the_output_back_its_turn():
    """A bar is a portrait panel used sideways: waking must not leave it upright."""
    bar = sb.output_command(True, {"GEXIS_SCREEN_TRANSFORM": "90"}, 1000)
    assert bar[-3:] == ["--on", "--transform", "90"]
    plain = sb.output_command(True, {"GEXIS_SCREEN_TRANSFORM": "normal"}, 1000)
    assert plain[-1] == "--on"
    assert sb.output_command(True, {}, 1000)[-2:] == ["HDMI-A-1", "--on"]


def test_screen_env_is_read_as_the_kiosk_reads_it(tmp_path):
    env = tmp_path / "screen.env"
    env.write_text("# a comment\nGEXIS_SCREEN_CONNECTOR=HDMI-A-1\nGEXIS_SCREEN_TRANSFORM=270\n")
    assert sb.screen_env(env) == {"GEXIS_SCREEN_CONNECTOR": "HDMI-A-1", "GEXIS_SCREEN_TRANSFORM": "270"}
    assert sb.screen_env(tmp_path / "missing") == {}


def test_sleep_and_wake_publish_once_each_and_in_order():
    events = []

    async def switch(on):
        events.append(("switch", on))
        return True

    standby = sb.Standby(switch=switch, publish=lambda off, reason: events.append(("publish", off, reason)))

    async def go():
        await standby.sleep("asked")
        await standby.sleep("asked")            # twice is once
        assert standby.off and standby.reason == "asked"
        await standby.wake("touch")
        await standby.wake("touch")
    asyncio.run(go())
    # The black cover is published before the output goes, and the output is
    # back before the panel is told it may draw again.
    assert events == [("publish", True, "asked"), ("switch", False),
                      ("switch", True), ("publish", False, None)]
    assert not standby.off


def test_a_screen_whose_output_cannot_switch_still_goes_black():
    async def refuse(on):
        return False
    published = []
    standby = sb.Standby(switch=refuse, publish=lambda off, reason: published.append(off))
    asyncio.run(standby.sleep("asked"))
    assert standby.off and published == [True]


class FakeScreen:
    def __init__(self):
        self.visible = False

    def show(self):
        self.visible = True
        return True

    def hide(self):
        self.visible = False
        return True


def test_the_visualiser_does_not_come_up_in_standby():
    asleep = {"off": True}
    controller = PeppyController(FakeScreen(), UnattendedPlayback(300), blocked=lambda: asleep["off"])
    assert controller.request("show") is False
    asleep["off"] = False
    assert controller.request("show") is True


async def test_a_touch_and_the_phone_wake_the_screen_and_the_phone_can_put_it_to_sleep():
    switched = []

    async def switch(on):
        switched.append(on)
        return True

    store = StateStore({})
    standby = sb.Standby(switch=switch, publish=lambda off, reason: store.set_panel(standby=off))
    server = StateServer(store, standby=standby)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await (await client.post("/panel/standby/on")).json()) == {"standby": True}
        assert store.state.panel["standby"] is True
        await client.post("/touch")
        assert not standby.off and store.state.panel["standby"] is False
        await client.post("/panel/standby/on")
        assert (await (await client.post("/panel/standby/off")).json()) == {"standby": False}
        assert (await client.post("/panel/standby/sideways")).status == 404
    assert switched == [False, True, False, True]


# -- the schedule -------------------------------------------------------------

import datetime  # noqa: E402

EVERY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
NIGHT = [{"from": "23:00", "until": "07:00", "days": EVERY}]


def at(day, hhmm):
    """A local time on a weekday: 2026-10-12 is a Monday."""
    hours, minutes = map(int, hhmm.split(":"))
    return datetime.datetime(2026, 10, 12 + EVERY.index(day), hours, minutes)


def test_a_standby_time_past_midnight_belongs_to_the_day_it_starts():
    friday_night = [{"from": "23:00", "until": "07:00", "days": ["Fri"]}]
    assert sb.in_standby_time(at("Fri", "23:30"), friday_night)
    assert sb.in_standby_time(at("Sat", "06:59"), friday_night)
    assert not sb.in_standby_time(at("Sat", "07:00"), friday_night)
    assert not sb.in_standby_time(at("Thu", "23:30"), friday_night)
    assert not sb.in_standby_time(at("Fri", "06:00"), friday_night)
    weekdays = [{"from": "09:30", "until": "12:00", "days": ["Mon", "Tue", "Wed", "Thu", "Fri"]}]
    assert sb.in_standby_time(at("Wed", "10:00"), weekdays)
    assert not sb.in_standby_time(at("Sat", "10:00"), weekdays)
    assert not sb.in_standby_time(at("Wed", "12:00"), weekdays)


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def scheduled(values, *, now, playing=False):
    clock = Clock()
    switched = []

    async def switch(on):
        switched.append(on)
        return True

    standby = sb.Standby(switch=switch, clock=clock)
    music = {"on": playing}
    schedule = sb.Schedule(standby, lambda k: values.get(k), lambda: music["on"],
                           clock=clock, now=lambda: now["at"])
    return standby, schedule, clock, music


def test_inside_a_standby_time_the_screen_goes_off_once_unused_and_after_the_wake_it_goes_back():
    values = {"standby_schedule": True, "standby_times": NIGHT, "standby_wake": 2}
    now = {"at": at("Mon", "23:30")}
    standby, schedule, clock, music = scheduled(values, now=now)

    async def go():
        clock.t = 30.0                       # used half a minute ago: not yet
        await schedule.tick()
        assert not standby.off
        clock.t = 121.0
        await schedule.tick()
        assert standby.off and standby.reason == "schedule"
        await standby.wake("touch")          # woken at night ...
        clock.t += 119
        await schedule.tick()
        assert not standby.off               # ... kept for the wake's two minutes
        clock.t += 2
        await schedule.tick()
        assert standby.off
        await standby.wake("music")
        music["on"] = True                   # music playing keeps it on
        clock.t += 600
        await schedule.tick()
        assert not standby.off
        music["on"] = False
        clock.t += 121
        await schedule.tick()
        assert standby.off
        now["at"] = at("Tue", "07:00")       # the window over: the schedule wakes it
        await schedule.tick()
        assert not standby.off
    asyncio.run(go())


def test_the_schedule_leaves_alone_a_screen_the_owner_turned_off_and_wakes_its_own_when_switched_off():
    values = {"standby_schedule": True, "standby_times": NIGHT, "standby_wake": 2}
    now = {"at": at("Mon", "12:00")}
    standby, schedule, clock, _ = scheduled(values, now=now)

    async def go():
        await standby.sleep("asked")
        await schedule.tick()                # outside a standby time
        assert standby.off and standby.reason == "asked"
        await standby.wake("touch")
        now["at"] = at("Mon", "23:30")
        clock.t += 300
        await schedule.tick()
        assert standby.off and standby.reason == "schedule"
        values["standby_schedule"] = False   # switched off: its own standby ends
        await schedule.tick()
        assert not standby.off
        values["standby_schedule"] = True
        values["headless"] = True            # no screen, no schedule
        clock.t += 300
        await schedule.tick()
        assert not standby.off
    asyncio.run(go())
