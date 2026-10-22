# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR-0156: a Home Assistant dashboard on the screen."""
import datetime

from gexis_core.dashboard import Dashboard, DashboardSchedule, explain

EVERY_DAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _dashboard():
    told = []
    return Dashboard(publish=lambda shown, by: told.append((shown, by))), told


def test_up_and_down_are_told_once_each():
    dashboard, told = _dashboard()
    assert dashboard.show() and not dashboard.show()
    assert dashboard.hide() and not dashboard.hide()
    assert told == [(True, "asked"), (False, None)]


def test_a_persons_ask_over_the_schedules_makes_it_theirs():
    """The schedule's end takes down only what the schedule put up: someone
    who asked for it while it was up keeps it."""
    dashboard, told = _dashboard()
    dashboard.show("schedule")
    assert dashboard.show("asked") and dashboard.by == "asked"
    assert not dashboard.show("schedule") and dashboard.by == "asked"


def _schedule(settings, at, dashboard=None):
    dashboard = dashboard or _dashboard()[0]
    times = []
    schedule = DashboardSchedule(dashboard, settings.get, times.append, now=lambda: at)
    return schedule, dashboard, times


ON = {"dashboard_schedule": True, "dashboard_url": "http://ha.example:8123/lovelace/0",
      "dashboard_times": [{"from": "18:00", "until": "23:00", "days": EVERY_DAY}]}


def test_inside_its_times_the_panel_is_told_to_show_it_for_the_idle_screen():
    schedule, _, times = _schedule(ON, datetime.datetime(2026, 10, 21, 19, 0))
    schedule.tick()
    assert times == [True]


def test_no_address_switched_off_or_headless_is_never_a_dashboard_time():
    at = datetime.datetime(2026, 10, 21, 19, 0)
    for settings in ({**ON, "dashboard_url": ""}, {**ON, "dashboard_schedule": False},
                     {**ON, "headless": True}):
        schedule, _, times = _schedule(settings, at)
        schedule.tick()
        assert times == [False], settings


def test_its_times_ending_take_down_what_the_schedule_put_up_and_nothing_else():
    at = datetime.datetime(2026, 10, 21, 23, 30)
    schedule, dashboard, _ = _schedule(ON, at)
    dashboard.show("schedule")
    schedule.tick()
    assert not dashboard.shown
    dashboard.show("asked")
    schedule.tick()
    assert dashboard.shown, "a person's dashboard stays until it is dismissed"


def test_the_panel_says_what_to_set_and_where():
    """Decision 8: the player changes nothing in Home Assistant, so it says
    what the user has to set there."""
    assert "Send X-Frame-Options" in explain("refuses framing")
    assert "use_x_frame_options: false" in explain("refuses framing")
    assert "Settings" in explain("unconfigured")
    assert "404" in explain("http 404")
    assert explain(None) is None


async def test_the_panel_a_phone_or_home_assistant_put_it_up_and_take_it_down():
    from aiohttp.test_utils import TestClient, TestServer

    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer

    store = StateStore({})
    dashboard = Dashboard(publish=lambda shown, by: store.set_panel(dashboard={"shown": shown, "by": by}))

    async def page():
        return {"url": None, "embeddable": False, "reason": "unconfigured", "message": explain("unconfigured")}

    server = StateServer(store, dashboard=dashboard, dashboard_page=page)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await (await client.post("/panel/dashboard/show")).json()) == {"shown": True, "by": "asked"}
        assert store.state.panel["dashboard"] == {"shown": True, "by": "asked"}
        checked = await (await client.get("/panel/dashboard")).json()
        assert checked["shown"] is True and checked["reason"] == "unconfigured" and checked["message"]
        assert (await (await client.post("/panel/dashboard/hide")).json()) == {"shown": False, "by": None}
        assert (await (await client.post("/panel/dashboard/show?by=schedule")).json())["by"] == "schedule"
        assert (await client.post("/panel/dashboard/sideways")).status == 404


def test_the_visualiser_takes_over_from_the_dashboard():
    """Decision 3 as amended (George, 2026-10-22): "If the user deliberately
    opens the visualizer then it should take over. Also if the timeout
    triggers it." A show takes the dashboard down first; standby still
    keeps the visualiser down."""
    import asyncio

    from gexis_core.peppy import PeppyController, UnattendedPlayback
    from test_standby import FakeScreen

    dashboard, published = _dashboard()
    standby = {"off": False}
    screen = FakeScreen()
    controller = PeppyController(screen, UnattendedPlayback(300), blocked=lambda: standby["off"],
                                 before_show=lambda: dashboard.hide("visualiser"))
    dashboard.show()
    assert controller.request("show") is True
    assert dashboard.shown is False and screen.visible, "asked for: the dashboard went down"
    screen.visible = False
    dashboard.show()
    assert asyncio.run(controller.request_async("show")) is True and not dashboard.shown
    screen.visible = False
    dashboard.show()
    standby["off"] = True
    assert controller.request("show") is False and dashboard.shown, "standby still wins, and nothing changes"


async def test_the_timer_s_show_takes_over_from_the_dashboard_too():
    """The same amendment: the visualiser's automatic start replaces it."""
    import asyncio
    import time
    import types

    from gexis_core.peppy import PeppyController
    from test_standby import FakeScreen

    dashboard, _ = _dashboard()
    screen = FakeScreen()
    timer = types.SimpleNamespace(due=lambda: True, stop_due=lambda: False, _now=time.monotonic,
                                  attention=lambda: None, stop_after_s=None)
    controller = PeppyController(screen, timer, tick_s=0.01, before_show=lambda: dashboard.hide("visualiser"))
    dashboard.show()
    run = asyncio.ensure_future(controller.run())
    for _ in range(100):
        await asyncio.sleep(0.01)
        if screen.visible:
            break
    run.cancel()
    assert screen.visible and not dashboard.shown


async def test_the_phone_input_over_a_frame_is_made_real_by_the_core():
    """ADR-0157: the panel hands the phone's tap, text and keys over the
    dashboard's frame to the core, which checks them before making them."""
    from aiohttp.test_utils import TestClient, TestServer

    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer

    made = []

    class FakeInput:
        async def tap(self, x, y):
            made.append(("tap", x, y))

        async def type(self, text):
            made.append(("text", text))
            return True

        async def key(self, name):
            made.append(("key", name))
            return name in ("Backspace", "Enter", "Tab")

    server = StateServer(StateStore({}), panel_input=FakeInput())
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.post("/panel/input", json={"kind": "tap", "x": 0.5, "y": 0.25})).status == 200
        assert (await client.post("/panel/input", json={"kind": "text", "text": "pässwörd"})).status == 200
        assert (await client.post("/panel/input", json={"kind": "key", "key": "Enter"})).status == 200
        assert (await client.post("/panel/input", json={"kind": "tap", "x": 1.5, "y": 0})).status == 400
        assert (await client.post("/panel/input", json={"kind": "key", "key": "F13"})).status == 400
        assert (await client.post("/panel/input", json={"kind": "text", "text": ""})).status == 400
        assert (await client.post("/panel/input", json={"kind": "move"})).status == 400
    assert made == [("tap", 0.5, 0.25), ("text", "pässwörd"), ("key", "Enter"), ("key", "F13")]


def test_the_panel_layout_is_read_from_labwc_and_its_characters_found(tmp_path):
    """ADR-0157: text is typed as key presses on the compositor's own layout.
    `wlrctl keyboard type` typed ASCII only and lost characters (sofapi,
    2026-10-21: "test.user@example.com" arrived as "test.usereaple.co")."""
    import pytest

    from gexis_core.panel_input import char_keys, compositor_layout

    environ = tmp_path / "environ"
    environ.write_bytes(b"HOME=/home/pi\0XKB_DEFAULT_LAYOUT=de\0XKB_DEFAULT_VARIANT=nodeadkeys\0")
    assert compositor_layout(environ) == {"layout": "de", "variant": "nodeadkeys"}
    assert compositor_layout(tmp_path / "gone") == {}

    us = char_keys({"layout": "us"})
    if not us:
        pytest.skip("libxkbcommon or its layouts are not on this machine")
    assert us["a"] == (30, False, False) and us["A"] == (30, True, False)
    assert us["@"] == (3, True, False) and us["/"] == (53, False, False)
    assert "£" not in us
    de = char_keys({"layout": "de"})
    assert de["z"] == (21, False, False), "the German layout swaps Y and Z"
    assert de["@"] == (16, False, True), "AltGr+Q on a German keyboard"
