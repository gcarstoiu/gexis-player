# SPDX-License-Identifier: GPL-3.0-or-later
"""The idle screen's forecast, from Open-Meteo (ADR-0047 §2a).

**Chosen because it needs no key and no account** ([Finding
043](../../../docs/findings/043-the-idle-screens-two-providers.md)): the
device works out of the box, and `weather_key` left the registry rather than
sitting there storing nothing. Its free tier is non-commercial, which is why
the choice waited on George answering whether a Gexis is ever sold. It is
not.

**Two calls, and the first happens once.** A place is typed as words and a
forecast is asked for in coordinates, so `geocode` turns one into the other
through Open-Meteo's own key-free geocoder. The answer is remembered for as
long as the daemon runs: a restart costs one lookup, and nothing about a
place name changes in between.

**Attribution is a licence condition, not a courtesy.** The data is CC BY
4.0 and the licence asks for `Weather data by Open-Meteo.com` as a link
beside it, so the payload carries the credit rather than leaving the panel
to remember.
"""
from __future__ import annotations

import asyncio
import logging
import time

import aiohttp

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_S = 8.0

#: How many candidates a name is allowed to return before the qualifiers
#: choose between them. Five is what `Berlin` alone comes back with.
CANDIDATES = 10

#: A lookup that could not be made, as distinct from one that came back
#: empty. The difference is the whole of what the user is told.
UNREACHABLE = object()

#: What the licence asks to be shown next to the data.
CREDIT = {"text": "Weather data by Open-Meteo.com", "url": "https://open-meteo.com/"}

#: How long a forecast is kept before it is asked for again. Open-Meteo's
#: own models update hourly; fifteen minutes is far inside every published
#: limit (10,000 a day) and means the screen redrawing does not mean a call.
FRESH_S = 15 * 60

#: WMO 4677, grouped the way a forecast is read on a panel rather than the
#: way it is coded. The name is what the icon sets are keyed on, so adding a
#: set is drawing three files, not editing this table (ADR-0047 §1).
WMO = {
    0: "clear",
    1: "mostly-clear", 2: "partly-cloudy", 3: "overcast",
    45: "fog", 48: "fog",
    51: "drizzle", 53: "drizzle", 55: "drizzle",
    56: "freezing-drizzle", 57: "freezing-drizzle",
    61: "rain", 63: "rain", 65: "heavy-rain",
    66: "freezing-rain", 67: "freezing-rain",
    71: "snow", 73: "snow", 75: "heavy-snow", 77: "snow-grains",
    80: "showers", 81: "showers", 82: "heavy-showers",
    85: "snow-showers", 86: "snow-showers",
    95: "thunderstorm", 96: "thunderstorm-hail", 99: "thunderstorm-hail",
}


def condition(code) -> str:
    """The icon name for a WMO code.

    An unknown code is `unknown` rather than a guess at the nearest one:
    the table above covers the codes Open-Meteo documents, and a silent
    substitution would draw sunshine over a storm nobody had a name for.
    """
    try:
        return WMO.get(int(code), "unknown")
    except (TypeError, ValueError):
        return "unknown"


def _matches(result: dict, qualifiers: list[str]) -> int:
    """How many of the typed qualifiers this candidate satisfies.

    **An unmatched qualifier is ignored, not fatal.** A postcode is the
    reason: Open-Meteo carries them for some places and not for others, and
    a place it *does* know must not become unfindable because the user also
    typed a number it does not hold. Ranking rather than filtering keeps
    "Berlin, DE" pointing at the German one - which is the case that matters,
    since the first `Berlin` a bare search returns is not always it.
    """
    haystack = {
        str(result.get(field, "")).strip().lower()
        for field in ("country", "country_code", "admin1", "admin2", "admin3", "admin4")
        if result.get(field)
    }
    haystack |= {str(code).strip().lower() for code in (result.get("postcodes") or [])}
    return sum(1 for q in qualifiers if q and q.lower() in haystack)


def _clock(iso: str | None) -> str | None:
    """`2026-09-22T06:52` -> `06:52`. The provider answers in the timezone it
    was asked for, so this is a slice rather than a conversion - and a slice
    cannot get the day wrong the way a reparse can."""
    if not iso or "T" not in str(iso):
        return None
    return str(iso).split("T", 1)[1][:5]


class Weather:
    """Forecasts for one device, cached in memory.

    Holds two caches with different reasons: places, because a name's
    coordinates do not change, and the forecast itself, because a screen
    that redraws is not a screen that should fetch.
    """

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._places: dict[str, dict] = {}
        self._forecast: tuple[str, int, float, dict] | None = None
        #: One lookup at a time. The idle screen can ask twice within a
        #: frame of itself - two clients, or a reload - and the second
        #: should wait for the first rather than start its own.
        self._lock = asyncio.Lock()

    async def _json(self, url: str, params: dict) -> dict | None:
        try:
            async with self._session.get(
                url, params=params, timeout=aiohttp.ClientTimeout(total=TIMEOUT_S)
            ) as response:
                if response.status >= 400:
                    logger.info("weather: %s answered HTTP %s", url, response.status)
                    return None
                return await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            logger.info("weather: %s failed: %s", url, exc)
            return None

    async def geocode(self, place: str) -> dict | None | object:
        """Where a typed place is, `None` if it is nowhere, `UNREACHABLE` if
        nobody could be asked.

        **Those last two must not share a message.** "That place could not
        be found" tells the user to type something else; saying it when the
        network is down sends them to fix a row that was already right.

        **The row asks for "City, country" and the provider takes a name.**
        Measured on the device, 2026-09-21: `Berlin` returns five places,
        `Berlin, DE` — *the design's own example value* — returns **none**,
        and so does a full postal address. So the splitting is ours: the
        first part looks the place up, the rest choose between the answers.
        Without this the row's placeholder describes an input that fails.
        """
        key = place.strip().lower()
        if not key:
            return None
        if key in self._places:
            return self._places[key]
        name, *qualifiers = [part.strip() for part in place.split(",")]
        if not name:
            return None
        body = await self._json(
            GEOCODE_URL, {"name": name, "count": CANDIDATES, "format": "json"}
        )
        if body is None:
            return UNREACHABLE
        results = body.get("results") or []
        if not results:
            logger.info("weather: no place called %r", name)
            return None
        best = max(results, key=lambda r: _matches(r, qualifiers))
        found = {
            "name": best.get("name") or name,
            "country": best.get("country_code") or "",
            "latitude": best["latitude"],
            "longitude": best["longitude"],
            "timezone": best.get("timezone") or "auto",
        }
        self._places[key] = found
        logger.info(
            "weather: %r is %s, %s (%.4f, %.4f)",
            place, found["name"], found["country"], found["latitude"], found["longitude"],
        )
        return found

    async def forecast(self, place: str, days: int) -> dict:
        """What the idle screen draws, or an `error` saying why not.

        The shape is the screen's, not the API's: a current temperature and
        condition, then one entry per day with a high and a low. Whether the
        panel shows the low is `idle_minmax`'s business - the number is sent
        either way, because hiding it here would mean fetching again when the
        setting changes.
        """
        async with self._lock:
            days = max(1, min(int(days or 4), 16))
            cached = self._forecast
            if (
                cached is not None
                and cached[0] == place.strip().lower()
                and cached[1] == days
                and time.monotonic() - cached[2] < FRESH_S
            ):
                return cached[3]

            found = await self.geocode(place)
            if found is UNREACHABLE:
                return {"error": "The forecast is unavailable.", "credit": CREDIT}
            if found is None:
                return {"error": "That place could not be found.", "credit": CREDIT}
            body = await self._json(
                FORECAST_URL,
                {
                    "latitude": found["latitude"],
                    "longitude": found["longitude"],
                    "timezone": found["timezone"],
                    "forecast_days": days,
                    # The screen draws all of these (design, 2026-09-22), and
                    # they arrive in the one request the forecast already
                    # costs - 3.4 KB against 748 B, no second call and no key.
                    "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
                    "daily": ("weather_code,temperature_2m_max,temperature_2m_min,"
                              "sunrise,sunset"),
                },
            )
            if body is None:
                return {"error": "The forecast is unavailable.", "credit": CREDIT}
            now = body.get("current") or {}
            daily = body.get("daily") or {}
            times = daily.get("time") or []
            answer = {
                "place": found["name"],
                "country": found["country"],
                "now": {
                    "temperature": now.get("temperature_2m"),
                    # **Always sent, even when it equals the reading** - the
                    # design shows it unconditionally, because a feels-like
                    # that appears only when it differs is a number whose
                    # absence has to be interpreted.
                    "feels_like": now.get("apparent_temperature"),
                    "wind": now.get("wind_speed_10m"),
                    "condition": condition(now.get("weather_code")),
                },
                #: Today's, and only today's: the screen shows one pair.
                "sun": {
                    "rise": _clock((daily.get("sunrise") or [None])[0]),
                    "sets": _clock((daily.get("sunset") or [None])[0]),
                },
                "days": [
                    {
                        "date": times[i],
                        "condition": condition((daily.get("weather_code") or [None])[i]),
                        "max": (daily.get("temperature_2m_max") or [None])[i],
                        "min": (daily.get("temperature_2m_min") or [None])[i],
                    }
                    for i in range(len(times))
                ],
                "unit": (body.get("current_units") or {}).get("temperature_2m", "°C"),
                "wind_unit": (body.get("current_units") or {}).get("wind_speed_10m", "km/h"),
                "credit": CREDIT,
                "error": None,
            }
            self._forecast = (place.strip().lower(), days, time.monotonic(), answer)
            return answer
