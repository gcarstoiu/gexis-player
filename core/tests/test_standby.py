"""ADR-0135: display standby - the screen off, the player still playing."""
from __future__ import annotations

import asyncio

import pytest

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

    async def show_async(self):
        return self.show()

    async def hide_async(self):
        return self.hide()


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


async def test_after_a_core_restart_the_first_touch_or_the_phone_gives_the_picture_back():
    """Review, 2026-10-12: the output's state lives in the kiosk's session,
    which outlives a core restart, while `off` starts False. A restart during
    standby (a plugin upload, a crash) left a dark panel that no touch, no
    phone and no music could wake."""
    switched = []

    async def switch(on):
        switched.append(on)
        return True

    store = StateStore({})
    standby = sb.Standby(switch=switch, publish=lambda off, reason: store.set_panel(standby=off))
    server = StateServer(store, standby=standby)
    async with TestClient(TestServer(server.make_app())) as client:
        await client.post("/touch")
        assert switched == [True], "the output is turned on, whatever the core last knew"
        await client.post("/touch")
        assert switched == [True], "once: a touch is not a subprocess every time"
    fresh = sb.Standby(switch=switch)
    await fresh.wake("phone")
    assert switched == [True, True] and not fresh.off


async def test_an_output_that_would_not_come_on_is_tried_again_at_the_next_touch():
    results = [False, True]
    switched = []

    async def switch(on):
        switched.append(on)
        return results.pop(0)

    standby = sb.Standby(switch=switch)
    assert standby.may_be_dark
    await standby.wake("touch")
    assert standby.may_be_dark
    await standby.wake("touch")
    assert not standby.may_be_dark and switched == [True, True]


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


def test_the_schedule_does_not_blank_a_screen_while_keep_this_screen_is_asked():
    """Finding 125 #17 (2026-10-14): a new screen chosen at 23:30 with *Back
    to standby after* at 2 min. The question counts down its 120 s from
    when it is drawn, some seconds after the core starts; the schedule put
    the black cover over it at 120 s from the start, and the change went
    back unseen."""
    values = {"standby_schedule": True, "standby_times": NIGHT, "standby_wake": 2}
    now = {"at": at("Mon", "23:30")}
    clock = Clock()

    async def switch(on):
        return True

    standby = sb.Standby(switch=switch, clock=clock)
    asked = {"on": True}
    schedule = sb.Schedule(standby, lambda k: values.get(k), lambda: False, clock=clock,
                           now=lambda: now["at"], blocked=lambda: asked["on"])

    async def go():
        clock.t = 121.0
        await schedule.tick()
        assert not standby.off, "the question is still on the screen"
        asked["on"] = False                  # answered: its two minutes from then
        clock.t += 119
        await schedule.tick()
        assert not standby.off
        clock.t += 2
        await schedule.tick()
        assert standby.off and standby.reason == "schedule"
    asyncio.run(go())


def test_the_question_drawn_counts_as_use_and_holds_the_schedule():
    """Finding 125 #17: wired as the pairing frame is (review, 2026-10-12)."""
    from test_main_wiring import MAIN, _closure
    shown = _closure("_screen_shown")
    assert "standby.used()" in shown and "standby.wake('screen')" in shown
    source = MAIN.read_text()
    block = source[source.index("standby_schedule = Schedule("):]
    block = block[:block.index("peppy = PeppyController(")]
    assert "blocked=lambda: state_store.state.screen_confirm is not None" in block


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


def test_standby_turns_off_the_port_the_screen_is_on(tmp_path, monkeypatch):
    """ADR-0109 (George, 2026-10-12): a screen on the second port is applied
    there, and standby turns off the output screen.env names - with no
    screen chosen, the one a screen is connected to, not always HDMI-A-1."""
    from gexis_core import screen_apply, screen_detect

    env = tmp_path / "screen.env"
    screen_apply.write_files(screen_apply.Applied("waveshare-13.3-hdmi-h", 0, "HDMI-A-2"),
                             env=env, cmdline=tmp_path / "cmdline.txt")
    assert sb.output_command(False, sb.screen_env(env), 1000)[-2:] == ["HDMI-A-2", "--off"]
    monkeypatch.setattr(screen_detect, "seen",
                        lambda *a, **k: screen_detect.Seen(connected=True, connector="HDMI-A-2"))
    assert sb.seen_connector() == "HDMI-A-2"
    assert sb.output_command(False, {}, 1000, sb.seen_connector())[-2:] == ["HDMI-A-2", "--off"]
    monkeypatch.setattr(screen_detect, "seen", lambda *a, **k: screen_detect.Seen())
    assert sb.seen_connector() == "HDMI-A-1"


# ── ADR-0135 as amended 2026-10-20: power down, keep the output; the real
# screen at start ──────────────────────────────────────────────────────────


def test_lit_is_wlr_randrs_enabled():
    assert sb.lit(True) is True and sb.lit(False) is False and sb.lit(None) is None


def test_touchscreens_are_the_devices_that_report_btn_touch(tmp_path):
    """BTN_TOUCH is bit 330: in the `key` capability's hex words (the last the
    lowest bits) it is in the second word from the end on a 64-bit kernel."""
    def dev(name, words):
        (tmp_path / name / "device" / "capabilities").mkdir(parents=True)
        (tmp_path / name / "device" / "capabilities" / "key").write_text(words + "\n")
    dev("event4", "400 0 0 0 0 0")          # 0x400 << 320: bit 330 - the bar's touchscreen
    dev("event1", "70000 0 0 0 0 0 0 0 0")  # a keyboard's keys, no BTN_TOUCH
    dev("event2", "0")
    assert sb.touchscreens(tmp_path) == [sb.Path("/dev/input/event4")]


def test_finger_downs_counts_only_a_finger_coming_down():
    ev = lambda typ, code, value: sb.EVENT.pack(0, 0, typ, code, value)
    data = ev(3, 0, 120) + ev(1, 330, 1) + ev(0, 0, 0) + ev(1, 330, 0) + ev(1, 330, 1)
    assert sb.finger_downs(data) == 2
    assert sb.finger_downs(ev(1, 272, 1)) == 0, "a mouse button is not a finger"


@pytest.mark.asyncio
async def test_a_finger_on_the_dark_screen_wakes_it(tmp_path):
    """ShelvesPi (2026-10-20): the bar's touch is mapped to its output, so with
    the output off no tap reached the page. The core reads the kernel."""
    import os
    r, w = os.pipe()
    fifo = tmp_path / "touch"
    os.mkfifo(fifo)
    calls, published = [], []
    s = _standby(calls, published)
    s.touch_watch = sb.TouchWatch(lambda: asyncio.ensure_future(s.wake("touch")), devices=lambda: [fifo])
    writer = os.open(fifo, os.O_RDWR | os.O_NONBLOCK)
    await s.sleep("asked")
    assert calls == [False] and s.touch_watch._open
    os.write(writer, sb.EVENT.pack(0, 0, 1, 330, 1))
    for _ in range(50):
        await asyncio.sleep(0.01)
        if not s.off:
            break
    assert not s.off and calls == [False, True] and published[-1] == (False, None)
    assert not s.touch_watch._open, "the watch stops when the screen is on"
    os.close(writer); os.close(r); os.close(w)


def _standby(calls, published):
    async def switch(on):
        calls.append(on)
        return True
    s = sb.Standby(switch=switch, publish=lambda off, reason: published.append((off, reason)))
    s.touch_watch = sb.TouchWatch(lambda: None, devices=lambda: [])  # not this machine's devices
    return s


@pytest.mark.asyncio
async def test_dark_at_start_outside_a_standby_time_is_woken():
    """The ShelvesPi case: asked off at 22:50, the update restarted the core at
    03:45, and the screen stayed dark all day with the core calling it on."""
    calls, published = [], []
    s = _standby(calls, published)
    await s.reconcile(False, inside_standby_time=False)
    assert calls == [True] and not s.off and not s.may_be_dark


@pytest.mark.asyncio
async def test_dark_at_start_inside_a_standby_time_is_the_schedules_standby():
    """Kept dark, but said: the phone offers to wake it, a touch wakes it, and
    the schedule wakes it when the time ends."""
    calls, published = [], []
    s = _standby(calls, published)
    await s.reconcile(False, inside_standby_time=True)
    assert calls == [] and s.off and s.reason == "schedule" and published == [(True, "schedule")]
    await s.wake("touch")
    assert calls == [True] and not s.off and published[-1] == (False, None)


@pytest.mark.asyncio
async def test_lit_at_start_is_known_on_and_unknown_changes_nothing():
    calls, published = [], []
    s = _standby(calls, published)
    await s.reconcile(True, inside_standby_time=True)
    assert calls == [] and not s.off and not s.may_be_dark
    s2 = _standby(calls, published)
    await s2.reconcile(None, inside_standby_time=False)
    assert calls == [] and s2.may_be_dark, "unread: a touch still switches it on, as before"


def test_inside_now_follows_the_schedule_and_headless():
    import datetime as dt
    vals = {"standby_schedule": True, "headless": False,
            "standby_times": [{"from": "22:30", "until": "07:00", "days": list(sb.DAYS)}]}
    s = sb.Schedule(sb.Standby(), vals.get, lambda: False, now=lambda: dt.datetime(2026, 10, 20, 23, 0))
    assert s.inside_now()
    vals["headless"] = True
    assert not s.inside_now()
    vals["headless"], vals["standby_schedule"] = False, False
    assert not s.inside_now()
