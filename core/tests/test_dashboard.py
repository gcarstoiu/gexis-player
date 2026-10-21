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


def test_the_visualiser_does_not_come_up_over_the_dashboard():
    """Decision 3: the visualiser's automatic start does not replace it."""
    from gexis_core.peppy import PeppyController, UnattendedPlayback
    from test_standby import FakeScreen

    dashboard, _ = _dashboard()
    controller = PeppyController(FakeScreen(), UnattendedPlayback(300), blocked=lambda: dashboard.shown)
    dashboard.show()
    assert controller.request("show") is False
    dashboard.hide()
    assert controller.request("show") is True
