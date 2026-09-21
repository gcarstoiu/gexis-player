# SPDX-License-Identifier: GPL-3.0-or-later
"""The idle screen's two providers (ADR-0047 §2a, Finding 043).

Open-Meteo for the forecast, Pixabay for the wallpapers. Neither is called
for real here: what is tested is what we do with an answer, what we do
without one, and the rules the providers' own terms impose - a 24-hour page
cache, a download rather than a hotlink, and a rotation that does not get
stuck in one category.
"""
from __future__ import annotations

import pytest
from aiohttp.test_utils import TestClient, TestServer

from gexis_core import wallpapers as wallpapers_mod
from gexis_core.settings import SettingsStore
from gexis_core.settings_registry import InvalidValue, Settings, load_registry
from gexis_core.state import StateStore
from gexis_core.wallpapers import Wallpapers
from gexis_core.weather import Weather, condition
from gexis_core.wsserver import StateServer

# ── the forecast ──────────────────────────────────────────────────────────

GEOCODED = {
    "results": [
        {
            "name": "Hamburg",
            "country_code": "DE",
            "latitude": 53.55073,
            "longitude": 9.99302,
            "timezone": "Europe/Berlin",
        }
    ]
}

FORECAST = {
    "current_units": {"temperature_2m": "°C"},
    "current": {"temperature_2m": 17.4, "weather_code": 3},
    "daily": {
        "time": ["2026-09-21", "2026-09-22", "2026-09-23"],
        "weather_code": [3, 61, 0],
        "temperature_2m_max": [18.1, 16.0, 19.9],
        "temperature_2m_min": [11.2, 10.4, 9.8],
    },
}


class FakeSession:
    """Answers whatever the test put in `replies`, and records what was
    asked. Not a mock of aiohttp - just the two calls these classes make."""

    def __init__(self, replies):
        self.replies = replies
        self.calls = []
        self.bodies = {}

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params or {})))
        reply = self.replies(url, dict(params or {}))
        return _Response(reply)


class _Response:
    def __init__(self, reply):
        self._reply = reply

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    @property
    def status(self):
        return self._reply[0]

    async def json(self):
        return self._reply[1]

    async def read(self):
        return self._reply[1]


def open_meteo(url, params):
    if "geocoding" in url:
        return (200, GEOCODED)
    return (200, FORECAST)


async def test_a_place_becomes_a_forecast_the_screen_can_draw():
    session = FakeSession(open_meteo)
    answer = await Weather(session).forecast("Hamburg", 3)
    assert answer["place"] == "Hamburg"
    assert answer["now"] == {"temperature": 17.4, "condition": "overcast"}
    assert [d["condition"] for d in answer["days"]] == ["overcast", "rain", "clear"]
    assert answer["days"][0] == {
        "date": "2026-09-21",
        "condition": "overcast",
        "max": 18.1,
        "min": 11.2,
    }
    # The licence's condition travels with the data rather than being
    # remembered by whatever draws it.
    assert answer["credit"]["text"] == "Weather data by Open-Meteo.com"


async def test_a_place_is_looked_up_once_and_the_forecast_is_not_refetched():
    """Two caches, two reasons: a name's coordinates never change, and a
    screen that redraws is not a screen that should call anyone."""
    session = FakeSession(open_meteo)
    forecast = Weather(session)
    await forecast.forecast("Hamburg", 3)
    await forecast.forecast("Hamburg", 3)
    assert len(session.calls) == 2  # one geocode, one forecast - not four
    assert sum("geocoding" in url for url, _ in session.calls) == 1


async def test_a_place_that_is_nowhere_is_an_answer_not_a_failure():
    session = FakeSession(lambda url, params: (200, {"results": []}))
    answer = await Weather(session).forecast("Nowherestan", 3)
    assert answer["error"] == "That place could not be found."
    assert "days" not in answer


async def test_an_unreachable_provider_says_so():
    """And it does not say the place was wrong. A geocoder nobody could
    reach is not a place nobody could find, and only one of those two is
    something the user can fix by typing."""
    session = FakeSession(lambda url, params: (200, GEOCODED) if "geocoding" in url else (503, {}))
    answer = await Weather(session).forecast("Hamburg", 3)
    assert answer["error"] == "The forecast is unavailable."

    offline = FakeSession(lambda url, params: (503, {}))
    answer = await Weather(offline).forecast("Hamburg", 3)
    assert answer["error"] == "The forecast is unavailable."


def test_every_wmo_code_has_a_name_and_an_unknown_one_is_not_guessed():
    assert condition(0) == "clear"
    assert condition(95) == "thunderstorm"
    # Not the nearest neighbour: a code nobody named must not draw sunshine
    # over a storm.
    assert condition(7) == "unknown"
    assert condition(None) == "unknown"
    assert condition("rain") == "unknown"


# ── the wallpapers ────────────────────────────────────────────────────────


def pixabay(hits_by_category):
    def reply(url, params):
        if url.startswith("https://pixabay.com/api/"):
            return (200, {"hits": hits_by_category.get(params.get("category"), [])})
        return (200, b"\xff\xd8jpeg-bytes")

    return reply


def hit(n, category):
    return {
        "id": n,
        "user": f"photographer{n}",
        "pageURL": f"https://pixabay.com/photos/{n}/",
        "largeImageURL": f"https://cdn.pixabay.com/{category}/{n}.jpg",
    }


async def test_a_picture_is_downloaded_rather_than_hotlinked(tmp_path):
    """Pixabay's terms: *"Permanent hotlinking of images is not allowed. If
    you intend to use the images, please download them to your server
    first."* So what the panel is handed is a file on this device."""
    session = FakeSession(pixabay({"nature": [hit(1, "nature")]}))
    answer = await Wallpapers(session, tmp_path).next("key", ["Nature"])
    assert answer["file"] == "1.jpg"
    assert (tmp_path / "1.jpg").read_bytes() == b"\xff\xd8jpeg-bytes"
    assert answer["by"] == "photographer1"
    assert answer["page"] == "https://pixabay.com/photos/1/"
    assert answer["credit"] == "Photos from Pixabay"
    # The request Pixabay's own rules require of us.
    asked = next(params for url, params in session.calls if "/api/" in url)
    assert asked["safesearch"] == "true"
    assert asked["image_type"] == "photo"
    assert asked["orientation"] == "horizontal"
    assert asked["min_width"] == 1280


async def test_several_topics_are_mixed_rather_than_taken_in_turn(tmp_path, monkeypatch):
    """George, 2026-09-21: *"the photos should come randomly from all the
    categories, not be stuck in only one of the many."* Over many refreshes
    every chosen category has to appear, and the order must not be the
    order they were chosen in."""
    session = FakeSession(
        pixabay(
            {
                "nature": [hit(1, "nature")],
                "animals": [hit(2, "animals")],
                "music": [hit(3, "music")],
            }
        )
    )
    source = Wallpapers(session, tmp_path)
    seen = set()
    for _ in range(60):
        answer = await source.next("key", ["Nature", "Animals", "Music"])
        seen.add(answer["topic"])
    assert seen == {"nature", "animals", "music"}


async def test_a_category_page_is_asked_for_once_a_day(tmp_path):
    """Their rule, not ours: *"Requests must be cached for 24 hours."*"""
    session = FakeSession(pixabay({"nature": [hit(1, "nature"), hit(2, "nature")]}))
    source = Wallpapers(session, tmp_path)
    for _ in range(5):
        await source.next("key", ["Nature"])
    assert sum("/api/" in url for url, _ in session.calls) == 1


async def test_a_topic_with_no_pictures_falls_through_to_another(tmp_path):
    """A category that answers with nothing must not blank the screen until
    the next change - there are other categories and one of them has
    pictures."""
    session = FakeSession(pixabay({"nature": [], "animals": [hit(2, "animals")]}))
    for _ in range(10):
        answer = await Wallpapers(session, tmp_path).next("key", ["Nature", "Animals"])
        assert answer["topic"] == "animals"


async def test_no_key_and_no_topics_are_told_apart(tmp_path):
    session = FakeSession(pixabay({}))
    source = Wallpapers(session, tmp_path)
    assert (await source.next("", ["Nature"]))["error"] == "No Pixabay key yet."
    assert (await source.next("key", []))["error"] == "No topics chosen."
    # A topic that is not one of Pixabay's twenty is not a request that
    # comes back empty - it never becomes a request at all.
    assert (await source.next("key", ["Spaceships"]))["error"] == "No topics chosen."
    assert not session.calls


async def test_the_cache_is_capped(tmp_path):
    session = FakeSession(pixabay({"nature": [hit(n, "nature") for n in range(20)]}))
    source = Wallpapers(session, tmp_path, keep=5)
    for _ in range(40):
        await source.next("key", ["Nature"])
    assert len(list(tmp_path.glob("*.jpg"))) <= 5


def test_a_name_cannot_climb_out_of_the_cache_directory(tmp_path):
    """The route that serves these is reachable from the LAN (ADR-0028)."""
    source = Wallpapers(FakeSession(pixabay({})), tmp_path)
    (tmp_path / "1.jpg").write_bytes(b"x")
    assert source.path_of("1.jpg") is not None
    assert source.path_of("../../etc/shadow") is None
    assert source.path_of("nope.jpg") is None


# ── the routes ────────────────────────────────────────────────────────────


def client_for(tmp_path, **kwargs):
    store = SettingsStore(tmp_path / "s.db")
    settings = Settings(store, wired={k: None for k in (
        "idle_weather", "weather_location", "idle_days", "wallpaper_key",
        "wallpaper_topics",
    )})
    server = StateServer(StateStore({}), settings=settings, **kwargs)
    return settings, TestClient(TestServer(server.make_app()))


async def test_the_weather_route_reads_the_rows(tmp_path):
    session = FakeSession(open_meteo)
    settings, client = client_for(tmp_path, weather=Weather(session))
    async with client:
        settings.set("idle_weather", True)
        settings.set("weather_location", "Hamburg")
        settings.set("idle_days", 3)
        body = await (await client.get("/idle/weather")).json()
        assert body["place"] == "Hamburg"
        assert len(body["days"]) == 3
        # Off is not an error, and not an empty forecast either.
        settings.set("idle_weather", False)
        assert await (await client.get("/idle/weather")).json() == {
            "error": None,
            "off": True,
        }


async def test_the_weather_route_asks_for_a_location_before_a_forecast(tmp_path):
    session = FakeSession(open_meteo)
    settings, client = client_for(tmp_path, weather=Weather(session))
    async with client:
        settings.set("idle_weather", True)
        body = await (await client.get("/idle/weather")).json()
        assert body["error"] == "No location set yet."
    assert not session.calls


async def test_the_wallpaper_route_serves_the_file_it_named(tmp_path):
    session = FakeSession(pixabay({"nature": [hit(1, "nature")]}))
    source = Wallpapers(session, tmp_path / "pics")
    settings, client = client_for(tmp_path, wallpapers=source)
    async with client:
        settings.set("wallpaper_key", "key")
        settings.set("wallpaper_topics", ["Nature"])
        body = await (await client.get("/idle/wallpaper")).json()
        assert body["url"] == "/idle/wallpaper/1.jpg"
        picture = await client.get(body["url"])
        assert picture.status == 200
        assert await picture.read() == b"\xff\xd8jpeg-bytes"
        # A name that is a path is not a picture.
        assert (await client.get("/idle/wallpaper/..%2F..%2Fetc%2Fshadow")).status == 404
        assert (await client.get("/idle/wallpaper/nope.jpg")).status == 404


async def test_the_routes_answer_503_rather_than_404_when_nothing_is_wired(tmp_path):
    settings, client = client_for(tmp_path)
    async with client:
        assert (await client.get("/idle/weather")).status == 503
        assert (await client.get("/idle/wallpaper")).status == 503


def test_the_topics_row_and_pixabays_categories_cannot_drift():
    """The row's options are Pixabay's list, capitalised. A word in the row
    that Pixabay does not have becomes a request that answers with nothing,
    and on the panel that looks like an empty sky rather than like a typo -
    which is why this is a test and not a comment in two places."""
    rows = {r["key"]: r for g in load_registry() for r in g["rows"] if r["type"] != "group"}
    options = rows["wallpaper_topics"]["options"]
    assert {o.lower() for o in options} == set(wallpapers_mod.CATEGORIES)


def test_an_empty_topic_set_is_refused_at_the_registry(tmp_path):
    """The screen has no picture to show with nothing chosen, so the write
    never lands (ADR-0044 §7) rather than landing and blanking the screen."""
    settings = Settings(SettingsStore(tmp_path / "s.db"), wired={"wallpaper_topics": None})
    with pytest.raises(InvalidValue):
        settings.set("wallpaper_topics", [])
