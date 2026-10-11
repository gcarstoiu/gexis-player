# SPDX-License-Identifier: GPL-3.0-or-later
"""**Problem report** (ADR-0125; George, 2026-10-07: *"have an option to
download logs - pii scrubed - for users to be able to report possible issues
back to us"*).

One zip of plain-text files: the journal, the updater's log, what is
installed, the hardware, the settings without secrets, and the user's own
line about what happened. **Everything personal is taken out on the device,
before the file is written:** each kind replaced by a stable token, so the
same address reads `ip-3` everywhere and the log still makes sense.

Two ways in, both needed (the first alone misses what was never written
down; the second alone misses what was):

- **Known values** the device itself holds - its name, the Wi-Fi networks
  it knows, shares, servers, paired devices, the weather location, every
  free-text and secret setting, the music it is playing - replaced
  wherever they appear.
- **Patterns** for the rest: addresses, query-string values, quoted text
  that reads like a name or a title, paths into a library, key-shaped runs.

Taking things out by pattern can miss something, which the row says.
"""
from __future__ import annotations

import io
import json
import logging
import re
import socket
import subprocess
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

logger = logging.getLogger("gexis_core.problem_report")

#: The newest part of the journal kept (ADR-0125 decision 2).
JOURNAL_MAX = 20 * 1024 * 1024
#: The updater's apt log is long; its end is what an update problem needs.
APT_LOG_MAX = 2 * 1024 * 1024
#: A value this short is not worth hunting for: it would match inside words.
KNOWN_MIN = 3

UPDATES = Path("/var/lib/gexis/updates")
NM_CONNECTIONS = Path("/etc/NetworkManager/system-connections")
BLUETOOTH = Path("/var/lib/bluetooth")

#: Where the report says to send it (ADR-0125 decision 5). The e-mail route
#: is added when George names the address.
ISSUE_URL = "https://github.com/gcarstoiu/gexis-player/issues/new?template=problem-report.yml"
#: For people without a GitHub account (ADR-0125 decision 5; George, 2026-10-07).
EMAIL = "george.carstoiu@gexis.net"

# --- the scrubber ------------------------------------------------------------

#: Followed by a full stop is still an address ("with address 10.0.0.5.");
#: followed by ".7" is a longer number.
_IPV4 = re.compile(r"(?<![\d.])((?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3})(?!\d)(?!\.\d)")
#: An IPv6 address has "::" or eight groups; a clock time ("11:45:23") has
#: neither.
_IPV6 = re.compile(r"(?<![0-9A-Fa-f:])((?:[0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4}|(?:[0-9A-Fa-f]{1,4}:){1,6}:(?:[0-9A-Fa-f]{1,4}(?::[0-9A-Fa-f]{1,4}){0,5})?)(?![0-9A-Fa-f:])")
_MAC = re.compile(r"(?<![0-9A-Fa-f:])((?:[0-9A-Fa-f]{2}[:_-]){5}[0-9A-Fa-f]{2})(?![0-9A-Fa-f])(?!:[0-9A-Fa-f])")
#: A share's mount point, as systemd escapes it in a unit's name
#: ("mnt-gexis\x2dshares-<host>\x2dlocal\x2d<share>...mount").
_SHARE_UNIT = re.compile(r"(gexis(?:\\x2d|-)shares[-/][^\s/]+?)(?=\.mount\b|[\s:/]|$)")
_LOCAL_NAME = re.compile(r"\b([A-Za-z0-9][A-Za-z0-9-]*\.local)\b")
_QUERY_VALUE = re.compile(r"([?&][A-Za-z_]+=)([^&\s\"']*)")
_QUOTED = re.compile(r"""(?P<q>['"])(?P<text>[^'"\n]{1,200})(?P=q)""")
_LIBRARY_PATH = re.compile(r"(/(?:mnt/gexis-shares|media|srv|home/[^/\s]+/Music|var/lib/gexis-core/music)/[^\s'\"]+)")
#: Never across a "/": a path is not a key.
_KEYISH = re.compile(r"\b([A-Za-z0-9+_-]{32,}={0,2})\b")
_FINGERPRINT = re.compile(r"\b((?:SHA256|MD5):[A-Za-z0-9+/:=]{20,})")
#: go-librespot's lines (logfmt): a title is quoted inside the message
#: (msg="loaded track \"Title\""), a person in its fields (username="..."),
#: and the phone that connected after "zeroconf from". Its plain messages -
#: "failed connecting to dealer" - stay.
_ESCAPED_QUOTED = re.compile(r'\\"([^"\\]{1,200})\\"')
_PERSON_FIELD = re.compile(r'\b(username|user|user_name|device_name|display_name)="([^"]*)"')
_CONNECTED_FROM = re.compile(r'((?:zeroconf|connection|connected|request) from )([^"\n]+?)(?="|$)')
#: A Spotify link names its track, album, playlist or listener to anyone
#: who looks it up.
_SPOTIFY_URI = re.compile(r"\b(spotify:(?:track|album|artist|playlist|episode|show|user):[A-Za-z0-9]+)")
#: The core's own lines; the quoted-text rule reads only these.
_CORE_LINE = re.compile(r"\bgexis_core[.\s]")
_ACCESS_LINE = re.compile(r"\baiohttp\.access\b")
#: Coordinates come in pairs - "(52.75, 13.45)" or "52.75,13.45" - which a
#: single measurement ("0.26812 s") never is.
_COORDS = re.compile(r"(?<![\d.])(-?\d{1,3}\.\d{3,}),\s*(-?\d{1,3}\.\d{3,})(?![\d.])")

#: What a known value begins with, when it begins with a letter or digit.
_HEAD = re.compile(r"[A-Za-z0-9]+")
_ALNUM = re.compile(r"[A-Za-z0-9]").match

#: How much of a log is scrubbed at a time (`Scrubber.scrub`): about 10 ms
#: of the slowest pattern on a desktop.
PIECE = 64 * 1024


def _pieces(text: str, size: int = PIECE) -> Iterable[str]:
    """`text` in whole lines, each piece about `size` long."""
    start = 0
    while start < len(text):
        end = text.find("\n", start + size)
        end = len(text) if end < 0 else end + 1
        yield text[start:end]
        start = end


#: Lines that name a place or an artist without quotes, found by their
#: shape (review, 2026-10-12). The geocoder's own name for the weather
#: location is not what the owner typed - "munich" comes back "München, DE"
#: - so no known value covers it (weather.geocode: "%r is %s, %s (lat,
#: lon)"). The covers sweep logs library artists, whom the device knows
#: only while they play ("sweep: %s failed (...)", "... scored %s, below
#: the threshold", "could not store <namespace>/<artist>"); "failed" puts
#: the line in the public issue's last errors.
_WEATHER_PLACE = re.compile(r"(\bweather: .*? is )([^\n]+?)(?= \(-?\d{1,3}\.\d+, -?\d{1,3}\.\d+\))")
_SWEEP_ARTIST = re.compile(r"(\bsweep: (?!could not ))([^\n]+?)(?= failed \(| scored -?[\d.]+, below the threshold)")
_SWEEP_KEY = re.compile(r"(\bsweep: could not (?:store|read) [\w-]+/)([^\n]+?)(?= \()")
#: A query string's coordinates are a place, though they read as numbers.
_COORD_KEYS = {"lat", "lon", "lng", "latitude", "longitude"}
#: The log's own words, which a known value matches only in its own case.
_LOG_WORDS = {"DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL", "FATAL"}

#: Kept as they are: they identify nobody.
_KEEP_IPS = {"127.0.0.1", "0.0.0.0", "255.255.255.255", "::1", "::"}
#: Never a private value, whatever a row holds: the product, the image's
#: user, the names every device has.
_NOT_PRIVATE = {"gexis", "gexis player", "pi", "raspberrypi", "localhost", "music", "default"}


@dataclass
class Scrubber:
    """Replaces what identifies a person or a home, each kind by its own
    stable token. One instance across every file of a report, so a token
    means the same thing in all of them."""
    known: dict[str, str] = field(default_factory=dict)     # value -> kind
    #: Words the quoted-text rule leaves alone: every option a setting
    #: offers ("Always", "Fanart") - fixed by the player, not by a person.
    allowed: set[str] = field(default_factory=set)
    tokens: dict[tuple[str, str], str] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    #: `known` arranged for `scrub_known`, made again when a value is added.
    _index: tuple | None = field(default=None, init=False, repr=False)

    def know(self, value, kind: str) -> None:
        """A value the device holds that must not leave it."""
        if not isinstance(value, str):
            return
        value = value.strip()
        if len(value) < KNOWN_MIN or value.lower() in ("true", "false", "none", "null") \
                or value.lower() in _NOT_PRIVATE:
            return
        if value not in self.known:
            self.known[value] = kind
            self._index = None

    def token(self, kind: str, value: str) -> str:
        key = (kind, value)
        if key not in self.tokens:
            n = sum(1 for k in self.tokens if k[0] == kind) + 1
            self.tokens[key] = f"{kind}-{n}"
            self.counts[kind] = self.counts.get(kind, 0) + 1
        return self.tokens[key]

    def scrub_known(self, text: str) -> str:
        """The device's own values only. Longest first, so "Living Room Pi"
        goes before "Living Room"; never inside a longer word.

        **Looked up word by word, not as one alternation of every value.**
        The regex engine holds the interpreter's lock for the whole of a
        call and tries each alternative at each place in the text, so a
        long queue's titles over a 20 MB journal kept the core's event loop
        - volume, arbitration - waiting for seconds (review, 2026-10-12;
        4.1 s measured on a desktop for 3,000 values over 2 MB). Here the
        text is read once, and only a word some value begins with is
        compared.

        **In any case** (review, 2026-10-12): a place typed "munich,
        germany" is logged by others as "Munich". The log's own level words
        are the exception - a track called "Warning" must not take every
        "WARNING" with it."""
        if not self.known:
            return text
        heads, starts = self._known_index()
        out: list[str] = []
        done = 0
        for m in starts.finditer(text):
            at = m.start()
            if at < done:
                continue        # inside a value already taken out
            for value, low in heads.get(m.group().lower(), ()):
                end = at + len(value)
                seg = text[at:end]
                if (seg == value or (seg.lower() == low and seg not in _LOG_WORDS)) \
                        and not (end < len(text) and _ALNUM(text[end])):
                    out.append(text[done:at])
                    out.append(self.token(self.known[value], value))
                    done = end
                    break
        out.append(text[done:])
        return "".join(out)

    def _known_index(self) -> tuple[dict[str, list[tuple[str, str]]], re.Pattern]:
        """Each known value, with its lower case, under the word it begins
        with - its first run of letters and digits, or its first character
        when that is neither ("(What's ...") - in lower case, longest first;
        and the pattern that finds every place in a text where one of those
        can begin."""
        if self._index is None:
            heads: dict[str, list[tuple[str, str]]] = {}
            others: set[str] = set()
            for value in sorted(self.known, key=len, reverse=True):
                head = _HEAD.match(value)
                key = (head.group() if head else value[0]).lower()
                if not head:
                    others.update(c for c in (value[0], value[0].lower(), value[0].upper()) if len(c) == 1)
                heads.setdefault(key, []).append((value, value.lower()))
            first = "|[" + "".join(map(re.escape, sorted(others))) + "]" if others else ""
            self._index = (heads, re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z0-9]+" + first + ")"))
        return self._index

    def scrub(self, text: str) -> str:
        """A log: the known values, then the patterns, line by line where a
        rule depends on whose line it is.

        **A piece at a time**, whole lines, so no one pass of a pattern
        holds the interpreter's lock for longer than `PIECE` takes to read
        (the event loop waits on it - see `scrub_known`)."""
        return "".join(self._scrub(piece) for piece in _pieces(text))

    def _scrub(self, text: str) -> str:
        # Before the known values, while the coordinates still mark the line.
        text = _WEATHER_PLACE.sub(lambda m: m.group(1) + self._unquoted("place", m.group(2)), text)
        text = _SWEEP_ARTIST.sub(lambda m: m.group(1) + self._unquoted("title", m.group(2)), text)
        text = _SWEEP_KEY.sub(lambda m: m.group(1) + self._unquoted("title", m.group(2)), text)
        text = self.scrub_known(text)
        text = _FINGERPRINT.sub(lambda m: self.token("secret", m.group(1)), text)
        text = _SHARE_UNIT.sub(lambda m: self.token("share", m.group(1)), text)
        text = _LIBRARY_PATH.sub(lambda m: self.token("path", m.group(1)), text)
        text = _MAC.sub(lambda m: self.token("mac", m.group(1).lower().replace("_", ":").replace("-", ":")), text)
        text = _IPV4.sub(lambda m: m.group(1) if m.group(1) in _KEEP_IPS else self.token("ip", m.group(1)), text)
        text = _IPV6.sub(lambda m: m.group(1) if m.group(1) in _KEEP_IPS or ":" not in m.group(1) or m.group(1).count(":") < 2 else self.token("ip", m.group(1)), text)
        text = _LOCAL_NAME.sub(lambda m: self.token("host", m.group(1)), text)
        text = _QUERY_VALUE.sub(self._query, text)
        text = _SPOTIFY_URI.sub(lambda m: self.token("title", m.group(1)), text)
        text = _ESCAPED_QUOTED.sub(lambda m: '\\"' + self.token("title", m.group(1)) + '\\"', text)
        text = _PERSON_FIELD.sub(lambda m: f'{m.group(1)}="{self.token("user", m.group(2))}"' if m.group(2) else m.group(0), text)
        text = _CONNECTED_FROM.sub(lambda m: m.group(1) + self.token("device", m.group(2).strip()), text)
        text = "\n".join(_QUOTED.sub(self._quoted, line) if _CORE_LINE.search(line) and not _ACCESS_LINE.search(line)
                         else line for line in text.split("\n"))
        text = _KEYISH.sub(self._keyish, text)
        text = _COORDS.sub(lambda m: self.token("place", m.group(0)), text)
        return text

    def _query(self, m: re.Match) -> str:
        value = m.group(2)
        if value and m.group(1)[1:-1].lower() in _COORD_KEYS:
            return m.group(1) + self.token("place", value)
        if not value or re.fullmatch(r"[\d.,x-]+", value):
            return m.group(0)
        return m.group(1) + self.token("text", value)

    def _unquoted(self, kind: str, text: str) -> str:
        """A name a line's shape says is one, quoted (%r) or not."""
        q = text[0] if len(text) > 1 and text[0] in "'\"" and text[-1] == text[0] else ""
        return q + self.token(kind, text[1:-1] if q else text) + q

    def _quoted(self, m: re.Match) -> str:
        """A quoted name or title: anything with a space, a capital or a
        letter outside ASCII. Lowercase words - commands, keys, unit names -
        say what the software did and stay."""
        text = m.group("text")
        if text.startswith(tuple(k + "-" for k in ("ip", "mac", "host", "net", "device", "share", "user",
                                                   "title", "text", "path", "place", "secret", "name"))):
            return m.group(0)
        if text in self.allowed:
            return m.group(0)
        if re.search(r"[\sA-Z]", text) or any(ord(c) > 127 for c in text):
            return m.group("q") + self.token("text", text) + m.group("q")
        return m.group(0)

    def _keyish(self, m: re.Match) -> str:
        run = m.group(1)
        # A long run of one character class is a path or a word, not a key.
        if not (re.search(r"\d", run) and re.search(r"[A-Za-z]", run)):
            return run
        # Words joined by hyphens with a hash on the end - a built file's name
        # ("nunito-sans-latin-wght-normal-BWQ3gi2K") - are not a key: keys
        # never hold two plain words.
        if sum(1 for part in run.split("-") if re.fullmatch(r"[a-z]{3,}", part)) >= 2:
            return run
        return self.token("secret", run)

    def summary(self) -> str:
        #: kind -> (one, several)
        names = {"ip": ("address", "addresses"), "mac": ("hardware address", "hardware addresses"),
                 "host": ("host name", "host names"), "net": ("network name", "network names"),
                 "device": ("device name", "device names"), "share": ("share", "shares"),
                 "user": ("user or account name", "user or account names"),
                 "title": ("track, album or artist name", "track, album or artist names"),
                 "text": ("name or title", "names or titles"), "path": ("library path", "library paths"),
                 "place": ("location", "locations"), "secret": ("key or token", "keys or tokens"),
                 "name": ("name", "names")}
        parts = []
        for kind, n in sorted(self.counts.items(), key=lambda kv: -kv[1]):
            one, several = names.get(kind, (kind, kind + "s"))
            parts.append(f"{n} {one if n == 1 else several}")
        return ", ".join(parts) if parts else "nothing"


# --- what goes in ------------------------------------------------------------

def _run(*cmd: str, timeout: float = 20) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _read(path: Path, limit: int | None = None) -> str:
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    if limit is not None and len(data) > limit:
        data = data[-limit:]
    return data.decode("utf-8", errors="replace")


def journal(limit: int = JOURNAL_MAX, run: Callable[..., str] = _run) -> str:
    """The journal: since this start, or the kept one when Debug logs is on
    (ADR-0103) - journalctl reads whichever exists. The newest `limit`
    bytes."""
    text = run("journalctl", "--no-pager", "-o", "short-iso", "-n", "200000", timeout=60)
    data = text.encode("utf-8", errors="replace")
    if len(data) > limit:
        data = data[-limit:]
        text = data.decode("utf-8", errors="replace")
        text = text[text.find("\n") + 1:]
    return text


def versions(run: Callable[..., str] = _run) -> str:
    lines = ["Packages:", run("dpkg-query", "-W", "-f", "${Package} ${Version}\n", "gexis-*").strip(),
             "", "Kernel: " + run("uname", "-r").strip(),
             "Image: " + _read(Path("/etc/gexis/image-build")).strip()]
    return "\n".join(lines) + "\n"


def hardware(run: Callable[..., str] = _run) -> str:
    from gexis_core import screen_detect
    model = _read(Path("/proc/device-tree/model")).strip("\x00\n ")
    mem = next((l for l in _read(Path("/proc/meminfo")).splitlines() if l.startswith("MemTotal")), "")
    try:
        screen = json.dumps(screen_detect.seen().to_json())
    except Exception:  # noqa: BLE001 - a report is still worth having without it
        screen = "unreadable"
    parts = [
        f"Model: {model}", mem,
        "", "Sound cards (/proc/asound/cards):", _read(Path("/proc/asound/cards")).rstrip(),
        "", "Playback devices (aplay -l):", run("aplay", "-l").rstrip(),
        "", "Mixer controls (hw:sndrpihifiberry):", run("amixer", "-D", "hw:sndrpihifiberry", "scontrols").rstrip(),
        "", "Screen (EDID maker, name, preferred mode; USB devices - no serial numbers):", screen,
        "", "Temperature: " + run("vcgencmd", "measure_temp").strip(),
        "Throttling: " + run("vcgencmd", "get_throttled").strip(),
    ]
    return "\n".join(parts) + "\n"


def settings_text(rows: Iterable[dict], get: Callable[[str], object], scrubber: "Scrubber") -> str:
    """Every registry row and its value. A secret row says only whether it
    is set (ADR-0125 decision 2: keys, tokens, passwords never leave); a
    row a person filled in - a name, an address, a place - shows its token;
    a fixed choice ("Hardware", "Cubic") shows as it is."""
    out = []
    for row in rows:
        key = row.get("key")
        if not key or row.get("type") in ("action", "document", "heading"):
            continue
        value = get(key)
        if row.get("secret"):
            value = "(set, not included)" if value else "(not set)"
        elif _private(row) and value not in (None, "", [], row.get("default")):
            # The same token the logs give it, so the two can be read together.
            raw = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            value = f"({scrubber.token(scrubber.known.get(raw, 'name'), raw)})"
        out.append(f"{key} = {json.dumps(value, ensure_ascii=False)}")
    return scrubber.scrub_known("\n".join(out) + "\n")


#: Row types whose values a person typed or picked from their own world -
#: names, addresses, places - as against a fixed list of options.
_FREE_TYPES = ("text", "list", "multi", "share", "share-login")


def _private(row: dict) -> bool:
    return row.get("type") in _FREE_TYPES or "." in (row.get("key") or "")


def learn(scrubber: Scrubber, rows: Iterable[dict], get: Callable[[str], object],
          shares: Iterable[dict] = (), now_playing: Iterable[str] = ()) -> None:
    """Teach the scrubber what this device holds."""
    for row in rows:
        key = row.get("key")
        if not key:
            continue
        for option in row.get("options") or ():
            scrubber.allowed.add(option if isinstance(option, str) else str(option))
        value = get(key)
        if value == row.get("default"):
            continue
        if row.get("secret"):
            for v in (value if isinstance(value, list) else [value]):
                scrubber.know(v if isinstance(v, str) else None, "secret")
        elif _private(row):
            for v in (value if isinstance(value, list) else [value]):
                if isinstance(v, dict):
                    for vv in v.values():
                        scrubber.know(vv, "name")
                else:
                    scrubber.know(v, "name")
                    # "Town,12345, Region, Country": the town is logged on its own.
                    if isinstance(v, str) and "," in v:
                        for part in v.split(","):
                            scrubber.know(part, "name")
    for share in shares:
        address = share.get("address") or ""
        scrubber.know(address, "share")
        for part in re.split(r"[/:]+", address):
            scrubber.know(part, "share")
            for word in re.split(r"[.\-_ ]+", part):     # "Tower.local" -> "Tower"
                scrubber.know(word, "share")
        scrubber.know(share.get("user"), "user")
    try:
        scrubber.know(socket.gethostname(), "host")
    except OSError:
        pass
    for conn in sorted(NM_CONNECTIONS.glob("*.nmconnection")) if NM_CONNECTIONS.is_dir() else ():
        for line in _read(conn).splitlines():
            if line.startswith(("ssid=", "id=")):
                scrubber.know(line.split("=", 1)[1], "net")
            elif line.startswith(("psk=", "password=")):
                scrubber.know(line.split("=", 1)[1], "secret")
    for info in BLUETOOTH.glob("*/*/info") if BLUETOOTH.is_dir() else ():
        for line in _read(info).splitlines():
            if line.startswith(("Name=", "Alias=")):
                scrubber.know(line.split("=", 1)[1], "device")
    for text in now_playing:
        scrubber.know(text, "title")


@dataclass
class Report:
    data: bytes
    name: str
    summary: str
    #: ADR-0138: what the zip holds (name, bytes), and the log's last errors
    #: and warnings, cleaned, for the GitHub issue.
    files: list[tuple[str, int]] = field(default_factory=list)
    errors: str = ""


#: ADR-0138 §1: the checklist the Preparing step shows, in the order the
#: player works down it.
STEPS = (
    ("log", "Reading the player's log"),
    ("updater", "Reading the updater's log"),
    ("versions", "Reading the versions and the hardware"),
    ("settings", "Reading the settings - keys, tokens and passwords left out"),
    ("learn", "Learning what is personal on this player"),
    ("scrub", "Taking out personal details"),
    ("write", "Writing the file"),
)


def _size(n: int) -> str:
    return f"{n / 1024 / 1024:.1f} MB" if n >= 1024 * 1024 else f"{max(1, round(n / 1024))} KB"


def _journal_said(text: str) -> str:
    """How much of the log, and from when: the first line's time."""
    first = re.match(r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})", text)
    since = f", from {first.group(1)} {first.group(2)}" if first else ""
    return f"{_size(len(text.encode('utf-8', errors='replace')))}{since}"


#: The last errors and warnings, for the issue itself (ADR-0138 decision 1):
#: a link carries about 7,500 characters in all.
ERRORS_MAX = 3000
_ERRORISH = re.compile(r"\b(ERROR|WARNING|CRITICAL|Traceback|Exception|failed|refused)\b")


def last_errors(journal_text: str, limit: int = ERRORS_MAX) -> str:
    """The newest error and warning lines of a cleaned journal, newest last,
    each at most 220 characters, together at most `limit`."""
    picked: list[str] = []
    total = 0
    for line in reversed(journal_text.splitlines()):
        if not _ERRORISH.search(line):
            continue
        line = line[:220]
        if total + len(line) + 1 > limit:
            break
        picked.append(line)
        total += len(line) + 1
    return "\n".join(reversed(picked))


def build(note: str, rows: list[dict], get: Callable[[str], object], *, shares: Iterable[dict] = (),
          now_playing: Iterable[str] = (), run: Callable[..., str] = _run,
          clock: Callable[[], float] = time.time,
          progress: Callable[[str, str], None] | None = None) -> Report:
    """The report, step by step; `progress(step, detail)` is told as each of
    `STEPS` is done (ADR-0138)."""
    tell = progress or (lambda step, detail: None)
    stamp = time.strftime("%Y-%m-%d-%H%M", time.localtime(clock()))
    files = {"what-happened.txt": (note or "").strip() + "\n"}
    files["journal.txt"] = journal(run=run)
    tell("log", _journal_said(files["journal.txt"]))
    files["updater/apt.log"] = _read(UPDATES / "apt.log", APT_LOG_MAX)
    files["updater/status.json"] = _read(UPDATES / "status.json")
    tell("updater", _size(len(files["updater/apt.log"].encode())) if files["updater/apt.log"] else "nothing yet")
    files["versions.txt"] = versions(run=run)
    files["hardware.txt"] = hardware(run=run)
    tell("versions", "")
    secret_rows = sum(1 for r in rows if r.get("secret") and get(r.get("key")) not in (None, "", r.get("default")))
    tell("settings", f"{len(rows)} rows, {secret_rows} kept back" if secret_rows else f"{len(rows)} rows")
    scrubber = Scrubber()
    learn(scrubber, rows, get, shares=shares, now_playing=now_playing)
    tell("learn", "network names, this player's name, paired devices, music shares, what is playing")
    scrubbed = {name: scrubber.scrub(text) for name, text in files.items()}
    scrubbed["settings.txt"] = settings_text(rows, get, scrubber)
    summary = scrubber.summary()
    tell("scrub", summary)
    readme = (
        "Gexis Player problem report\n"
        f"Made {stamp}.\n\n"
        "Personal details were taken out on the player before this file was written,\n"
        "each replaced by a token such as ip-3 or text-12, the same token wherever the\n"
        f"same value appeared. Taken out: {summary}.\n\n"
        "Taking things out by pattern can miss something: read the files before\n"
        "sharing them. Nothing was sent anywhere by the player.\n\n"
        f"To report the problem: {ISSUE_URL}\n"
        f"Or by e-mail, with this file attached: {EMAIL}\n"
    )
    buf = io.BytesIO()
    listed = [("README.txt", len(readme.encode()))]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", readme)
        for name, text in scrubbed.items():
            z.writestr(name, text)
            listed.append((name, len(text.encode("utf-8", errors="replace"))))
    name = f"gexis-report-{stamp}.zip"
    data = buf.getvalue()
    tell("write", f"{name}, {_size(len(data))}")
    return Report(data, name, summary, listed, last_errors(scrubbed["journal.txt"]))


#: The issue form's fields (`.github/ISSUE_TEMPLATE/problem-report.yml`).
OFTEN = ("Every time", "Sometimes", "Once so far")
URL_MAX = 7500


def issue_url(what: str, often: str | None, version: str, report: Report) -> str:
    """ADR-0138 §3: the problem on GitHub, filled in - what happened, how
    often, the version, what was taken out and the log's last errors. A link
    cannot carry the file; the step offers it to attach. The errors are cut
    first, then what happened, to stay under what GitHub takes."""
    from urllib.parse import urlencode
    base = "https://github.com/gcarstoiu/gexis-player/issues/new"
    title = "[Problem] " + (what.strip().splitlines()[0][:70] if what.strip() else "")

    def body(errors: str) -> str:
        head = (f"Prepared on the player: {report.name}. Taken out: {report.summary}.\n"
                "The full report can be attached here too: drag the file onto this box.\n")
        return head + (f"\nLast errors and warnings in the log (cleaned):\n```\n{errors}\n```\n" if errors else "")

    def build_url(what_now: str, errors: str) -> str:
        params = {"template": "problem-report.yml", "title": title, "what": what_now,
                  "version": version, "report": body(errors)}
        if often in OFTEN:
            params["often"] = often
        return f"{base}?{urlencode(params)}"

    errors, what_now = report.errors, what.strip()
    url = build_url(what_now, errors)
    while len(url) > URL_MAX and errors:
        errors = errors[errors.find("\n") + 1:] if "\n" in errors else ""
        url = build_url(what_now, errors)
    while len(url) > URL_MAX and what_now:
        what_now = what_now[:-50]
        url = build_url(what_now + " [cut]", errors)
    return url
