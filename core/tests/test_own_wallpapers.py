"""ADR-0133: the player's own wallpapers - which set the next picture comes
from, by style, hour, season and holiday, and what the screen is handed."""
from __future__ import annotations

import datetime as dt
import json
import random

import pytest

from gexis_core import own_wallpapers as ow


@pytest.mark.parametrize("year,western,orthodox", [
    (2024, dt.date(2024, 3, 31), dt.date(2024, 5, 5)),
    (2025, dt.date(2025, 4, 20), dt.date(2025, 4, 20)),
    (2026, dt.date(2026, 4, 5), dt.date(2026, 4, 12)),
])
def test_easter_both_ways(year, western, orthodox):
    assert ow.easter_western(year) == western
    assert ow.easter_orthodox(year) == orthodox


@pytest.mark.parametrize("day,country,expected", [
    (dt.date(2026, 12, 31), None, "newyear"),        # everywhere, even unknown
    (dt.date(2027, 1, 1), "JP", "newyear"),
    (dt.date(2026, 12, 24), "DE", "christmas"),
    (dt.date(2026, 12, 26), "RO", "christmas"),
    (dt.date(2026, 12, 27), "DE", None),
    (dt.date(2026, 12, 25), "JP", None),             # not a public holiday there
    (dt.date(2026, 12, 25), None, None),             # unknown country: New Year only
    (dt.date(2026, 4, 3), "DE", "easter"),           # Good Friday, Western
    (dt.date(2026, 4, 6), "DE", "easter"),           # Easter Monday
    (dt.date(2026, 4, 7), "DE", None),
    (dt.date(2026, 4, 10), "DE", None),              # the Orthodox Good Friday, not here
    (dt.date(2026, 4, 10), "RO", "easter"),          # ... but here
    (dt.date(2026, 4, 13), "GR", "easter"),
    (dt.date(2026, 4, 5), "RO", None),               # the Western Sunday, not here
])
def test_holidays_by_country(day, country, expected):
    assert ow.holiday(day, country) == expected


def test_seasons_follow_the_hemisphere():
    assert ow.season(dt.date(2026, 1, 15), southern=False) == "winter"
    assert ow.season(dt.date(2026, 1, 15), southern=True) == "summer"
    assert ow.season(dt.date(2026, 4, 1), southern=False) == "spring"
    assert ow.season(dt.date(2026, 4, 1), southern=True) == "autumn"
    assert ow.season(dt.date(2026, 7, 1), southern=False) == "summer"
    assert ow.season(dt.date(2026, 10, 10), southern=False) == "autumn"


@pytest.mark.parametrize("hour,expected", [(0, "night"), (4, "night"), (5, "dawn"), (7, "dawn"),
                                           (8, "day"), (16, "day"), (17, "dusk"), (20, "dusk"), (21, "night"),
                                           (23, "night")])
def test_the_hour_chooses_its_set(hour, expected):
    assert ow.time_of_day(hour) == expected


def test_country_and_latitude_from_the_time_zone(tmp_path):
    tab = tmp_path / "zone.tab"
    tab.write_text("# comment\nDE\t+5230+01322\tEurope/Berlin\nAU\t-3352+15113\tAustralia/Sydney\n"
                   "US\t+404251-0740023\tAmerica/New_York\n")
    country, lat = ow.from_time_zone("Europe/Berlin", tab)
    assert country == "DE" and lat == pytest.approx(52.5)
    country, lat = ow.from_time_zone("Australia/Sydney", tab)
    assert country == "AU" and lat < 0
    country, lat = ow.from_time_zone("America/New_York", tab)
    assert country == "US" and lat == pytest.approx(40.7, abs=0.01)
    assert ow.from_time_zone("Nowhere/Else", tab) == (None, None)
    assert ow.from_time_zone(None, tab) == (None, None)


def test_a_holiday_replaces_everything_else_while_holidays_is_on():
    christmas = dt.datetime(2026, 12, 25, 22)
    common = dict(styles=["Calm", "Psychedelic"], time_of_day_on=True, seasons_on=True,
                  country="DE", latitude=52.5)
    assert ow.active_sets(christmas, holidays_on=True, **common) == ["christmas"]
    assert ow.active_sets(christmas, holidays_on=False, **common) == ["calm", "psychedelic", "night", "winter"]


def test_no_style_falls_back_to_calm():
    sets = ow.active_sets(dt.datetime(2026, 6, 1, 12), styles=[], time_of_day_on=False, seasons_on=False,
                          holidays_on=True, country="DE", latitude=52.5)
    assert sets == ["calm"]


def _installed(tmp_path):
    entries = []
    for set_name, names in {"calm": ["a", "b", "c"], "space": ["s1"]}.items():
        (tmp_path / set_name).mkdir()
        for n in names:
            (tmp_path / set_name / f"{n}.webp").write_bytes(b"x")
            entries.append({"file": f"{set_name}/{n}.webp", "set": set_name, "author": "A. Author",
                            "licence": "Public domain", "source": "https://example.org/" + n})
    entries[-1].update({"licence": "CC BY 4.0", "credit": "ESA/Webb, NASA & CSA"})
    entries.append({"file": "calm/missing.webp", "set": "calm", "licence": "CC0"})   # no file: never offered
    (tmp_path / "credits.json").write_text(json.dumps(entries))
    return ow.OwnWallpapers(tmp_path, rng=random.Random(1))


def test_every_picture_once_before_any_twice(tmp_path):
    walls = _installed(tmp_path)
    seen = [walls.next(["calm"])["file"] for _ in range(3)]
    assert sorted(seen) == ["calm/a.webp", "calm/b.webp", "calm/c.webp"]
    assert walls.next(["calm"], avoid="calm/a.webp")["file"] != "calm/a.webp"


def test_what_the_screen_is_handed(tmp_path):
    walls = _installed(tmp_path)
    pd = walls.answer("calm/a.webp")
    assert pd["url"] == "/idle/wallpaper/own/calm/a.webp"
    assert pd["by"] == "A. Author" and pd["credit"] == "Public domain" and pd["page"] == "https://example.org/a"
    cc = walls.answer("space/s1.webp")
    assert cc["by"] is None and cc["credit"] == "ESA/Webb, NASA & CSA · CC BY 4.0"


def test_a_set_with_no_pictures_is_passed_over(tmp_path):
    walls = _installed(tmp_path)
    assert walls.next(["winter", "space"])["file"] == "space/s1.webp"
    assert walls.next(["winter"]) is None


def test_only_listed_pictures_are_served(tmp_path):
    walls = _installed(tmp_path)
    assert walls.path_of("calm/a.webp") == tmp_path / "calm/a.webp"
    assert walls.path_of("calm/missing.webp") is None
    assert walls.path_of("../credits.json") is None
    assert walls.path_of("calm/../../etc/passwd") is None


# ── through the core's routes ───────────────────────────────────────────────

async def test_the_idle_route_serves_the_players_own_pictures(tmp_path):
    from aiohttp.test_utils import TestClient, TestServer

    from gexis_core.settings import SettingsStore
    from gexis_core.settings_registry import Settings
    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer

    (tmp_path / "walls").mkdir()
    walls = _installed(tmp_path / "walls")
    settings = Settings(SettingsStore(tmp_path / "s.db"), wired={k: None for k in (
        "idle_background", "wallpaper_styles", "wallpaper_time_of_day", "wallpaper_seasons",
        "wallpaper_holidays", "weather_location", "timezone", "lms_enabled")})
    server = StateServer(StateStore({}), settings=settings, own=walls)
    async with TestClient(TestServer(server.make_app())) as client:
        # A new player's default: Gexis wallpapers. Only Calm is installed
        # here, so with the other sets off every picture comes from it.
        settings.set("wallpaper_time_of_day", False)
        settings.set("wallpaper_seasons", False)
        settings.set("wallpaper_holidays", False)
        body = await (await client.get("/idle/wallpaper")).json()
        assert body["url"].startswith("/idle/wallpaper/own/calm/") and body["credit"] == "Public domain"
        served = await client.get(body["url"])
        assert served.status == 200 and await served.read() == b"x"
        # A climb out of the folder never reaches credits.json (aiohttp
        # normalises it onto another route, which does not serve it either).
        assert (await client.get("/idle/wallpaper/own/../credits.json")).status != 200

        settings.set("idle_background", "Space pictures")
        body = await (await client.get("/idle/wallpaper")).json()
        assert body["url"] == "/idle/wallpaper/own/space/s1.webp"
        assert body["credit"] == "ESA/Webb, NASA & CSA · CC BY 4.0"

        # ADR-0133 §2: no library while the LMS client is off, so artist
        # pictures give way to the player's own.
        settings.set("idle_background", "Artist pictures")
        settings.set("lms_enabled", False)
        body = await (await client.get("/idle/wallpaper")).json()
        assert body["url"].startswith("/idle/wallpaper/own/")


def test_the_system_zone_is_read_from_the_localtime_link(tmp_path):
    zone = tmp_path / "usr/share/zoneinfo/Europe/Berlin"
    zone.parent.mkdir(parents=True)
    zone.write_text("tz")
    link = tmp_path / "localtime"
    link.symlink_to(zone)
    assert ow.system_zone(link) == "Europe/Berlin"
    assert ow.system_zone(tmp_path / "missing") is None


def test_an_unknown_author_is_not_named(tmp_path):
    walls = _installed(tmp_path)
    walls._load()["calm/a.webp"]["author"] = "Unknown author"
    answer = walls.answer("calm/a.webp")
    assert answer["by"] is None and answer["credit"] == "Public domain"
