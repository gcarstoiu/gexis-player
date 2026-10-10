# SPDX-License-Identifier: GPL-3.0-or-later
"""**The player's own wallpapers** (ADR-0133): the next picture for the
*Gexis wallpapers* and *Space pictures* backgrounds.

The pictures are `gexis-wallpapers`' (`/usr/share/gexis/wallpapers/<set>/`),
listed with their credits in `credits.json`. Which set a picture comes from:

- **A holiday's days** - New Year everywhere; Christmas and Easter where they
  are public holidays - show that holiday's pictures **instead of** the rest,
  while *Holidays* is on (George, 2026-10-10: *"They replace them. For the
  time being if option is selected."*).
- **Otherwise** each change picks one of the active sets at random - the
  chosen *Wallpaper styles*, the hour's set when *Follow the time of day* is
  on, the season's when *Seasons* is on - and then a picture from it, as the
  online topics are mixed (ADR-0047).

**The country and the hemisphere** come from the weather location once one
is set, and from the time zone before that (ADR-0133 §4). Everything here is
pure, given the date, the country and the latitude, so the rules are tested
without a device.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import random
from pathlib import Path

logger = logging.getLogger("gexis_core.own_wallpapers")

ROOT = Path("/usr/share/gexis/wallpapers")
ZONE_TAB = Path("/usr/share/zoneinfo/zone.tab")

#: The settings' style names, and their folders.
STYLES = {"Calm": "calm", "Colourful": "colourful", "Psychedelic": "psychedelic"}
SPACE = "space"

#: Local hours. Fixed, not the sun: the weather's sunrise is not always there,
#: and a set chosen by the clock is what the setting promises.
HOURS = (("night", 0), ("dawn", 5), ("day", 8), ("dusk", 17), ("night", 21))

#: Orthodox Easter, by the Julian computus (ADR-0133 §4).
ORTHODOX = frozenset({"RO", "GR", "BG", "RS", "CY", "MK", "ME", "RU", "UA", "BY", "GE", "MD"})
#: Where 25 December is not a public holiday, so no Christmas pictures and no
#: Easter either. Countries keeping Orthodox Christmas on 7 January are here
#: too: their day is a later addition (ADR-0133, "later, per country").
NO_CHRISTMAS = frozenset({
    "AE", "AF", "AZ", "BH", "BT", "BY", "CN", "DZ", "GE", "IL", "IR", "JP", "KG", "KP", "KW", "KZ",
    "LA", "LY", "MA", "MN", "MR", "MV", "NP", "OM", "QA", "RS", "RU", "SA", "SO", "TH", "TJ", "TM",
    "TN", "TR", "UZ", "YE",
})


# ---- the calendar --------------------------------------------------------

def easter_western(year: int) -> dt.date:
    """Easter Sunday, Gregorian (the anonymous Gregorian algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return dt.date(year, month, day + 1)


def easter_orthodox(year: int) -> dt.date:
    """Easter Sunday, Julian computus, as a Gregorian date (Meeus). The
    calendars are 13 days apart from 1900 to 2099."""
    a, b, c = year % 4, year % 7, year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month, day = divmod(d + e + 114, 31)
    return dt.date(year, month, day + 1) + dt.timedelta(days=13)


def holiday(day: dt.date, country: str | None) -> str | None:
    """The holiday set for this date in this country, or None. An unknown
    country gets New Year only: it is the one that holds everywhere."""
    if (day.month, day.day) in ((12, 31), (1, 1)):
        return "newyear"
    if not country or country in NO_CHRISTMAS:
        return None
    if day.month == 12 and 24 <= day.day <= 26:
        return "christmas"
    sunday = easter_orthodox(day.year) if country in ORTHODOX else easter_western(day.year)
    if sunday - dt.timedelta(days=2) <= day <= sunday + dt.timedelta(days=1):
        return "easter"
    return None


def season(day: dt.date, southern: bool) -> str:
    """Meteorological seasons, by hemisphere."""
    month = (day.month + 6 - 1) % 12 + 1 if southern else day.month
    return ("winter", "winter", "spring", "spring", "spring", "summer",
            "summer", "summer", "autumn", "autumn", "autumn", "winter")[month - 1]


def time_of_day(hour: int) -> str:
    name = HOURS[0][0]
    for set_name, start in HOURS:
        if hour >= start:
            name = set_name
    return name


def system_zone(localtime: Path = Path("/etc/localtime")) -> str | None:
    """The zone the system runs in, from `/etc/localtime`'s link. Not
    `/etc/timezone`: setting the zone on this Debian does not update that
    file, which a factory reset had left at the image's own (found on the bar
    player, 2026-10-10: the file said London, the system Berlin)."""
    try:
        target = str(localtime.resolve())
    except OSError:
        return None
    marker = "/zoneinfo/"
    return target.split(marker, 1)[1] if marker in target else None


def from_time_zone(zone: str | None, zone_tab: Path = ZONE_TAB) -> tuple[str | None, float | None]:
    """The country and latitude tzdata gives a zone (`zone.tab`'s own
    coordinates), or (None, None)."""
    if not zone:
        return None, None
    try:
        lines = zone_tab.read_text().splitlines()
    except OSError:
        return None, None
    for line in lines:
        if line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 3 and parts[2] == zone:
            coords = parts[1]
            # ±DDMM or ±DDMMSS, then the longitude's sign.
            cut = max(coords.find("+", 1), coords.find("-", 1))
            lat = coords[:cut]
            degrees = int(lat[1:3]) + int(lat[3:5]) / 60
            return parts[0], degrees if lat[0] == "+" else -degrees
    return None, None


def active_sets(now: dt.datetime, *, styles: list[str], time_of_day_on: bool, seasons_on: bool,
                holidays_on: bool, country: str | None, latitude: float | None) -> list[str]:
    """The sets the next picture may come from."""
    if holidays_on:
        today = holiday(now.date(), country)
        if today:
            return [today]
    sets = [STYLES[s] for s in styles if s in STYLES]
    if time_of_day_on:
        sets.append(time_of_day(now.hour))
    if seasons_on:
        sets.append(season(now.date(), southern=latitude is not None and latitude < 0))
    return sets or [STYLES["Calm"]]


# ---- the pictures ----------------------------------------------------------

class OwnWallpapers:
    """The installed pictures and their credits, and which was shown last."""

    def __init__(self, root: Path = ROOT, rng: random.Random | None = None) -> None:
        self._root = root
        self._rng = rng or random.Random()
        self._credits: dict[str, dict] | None = None
        self._shown: dict[str, list[str]] = {}

    def _load(self) -> dict[str, dict]:
        if self._credits is None:
            try:
                entries = json.loads((self._root / "credits.json").read_text())
            except (OSError, ValueError) as exc:
                logger.warning("own wallpapers: %s/credits.json unreadable: %s", self._root, exc)
                entries = []
            self._credits = {e["file"]: e for e in entries
                             if isinstance(e, dict) and (self._root / e.get("file", "")).is_file()}
        return self._credits

    def files(self, set_name: str) -> list[str]:
        return sorted(f for f, e in self._load().items() if e.get("set") == set_name)

    def next(self, sets: list[str], avoid: str | None = None) -> dict | None:
        """A picture from one of `sets`, chosen at random among those that
        have any, none twice in a set until all of it has been shown."""
        sets = [s for s in sets if self.files(s)]
        if not sets:
            return None
        set_name = self._rng.choice(sets)
        names = self.files(set_name)
        shown = self._shown.setdefault(set_name, [])
        fresh = [n for n in names if n not in shown and n != avoid]
        if not fresh:
            shown.clear()
            fresh = [n for n in names if n != avoid] or names
        name = self._rng.choice(fresh)
        shown.append(name)
        return self.answer(name)

    def answer(self, name: str) -> dict:
        """What the screen draws: the picture's address and its credit line,
        in the shape the other backgrounds use (`by`, `page`, `credit`)."""
        entry = self._load()[name]
        licence = entry.get("licence") or ""
        if entry.get("credit"):
            # CC BY: the line its release asks for, then the licence.
            by, credit = None, f"{entry['credit']} · {licence}"
        else:
            # Commons writes "Unknown author" where nobody is named; the line
            # then gives the licence alone rather than "Photo by Unknown".
            author = (entry.get("author") or "").strip()
            by = None if not author or author.lower().startswith("unknown") else author
            credit = "Public domain" if licence.lower().startswith("public domain") else licence
        return {"url": f"/idle/wallpaper/own/{name}", "file": name, "by": by,
                "page": entry.get("source") or "", "credit": credit, "error": None}

    def path_of(self, name: str) -> Path | None:
        """The file behind a name `answer` handed out. Only names in the
        credits list: the route is reachable from the LAN."""
        return self._root / name if name in self._load() else None
