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

    def know(self, value, kind: str) -> None:
        """A value the device holds that must not leave it."""
        if not isinstance(value, str):
            return
        value = value.strip()
        if len(value) < KNOWN_MIN or value.lower() in ("true", "false", "none", "null") \
                or value.lower() in _NOT_PRIVATE:
            return
        self.known.setdefault(value, kind)

    def token(self, kind: str, value: str) -> str:
        key = (kind, value)
        if key not in self.tokens:
            n = sum(1 for k in self.tokens if k[0] == kind) + 1
            self.tokens[key] = f"{kind}-{n}"
            self.counts[kind] = self.counts.get(kind, 0) + 1
        return self.tokens[key]

    def scrub_known(self, text: str) -> str:
        """The device's own values only. Longest first, so "Living Room Pi"
        goes before "Living Room"; never inside a longer word."""
        if not self.known:
            return text
        # One pass for all of them: an alternation tries the longest first.
        values = sorted(self.known, key=len, reverse=True)
        pattern = re.compile(r"(?<![A-Za-z0-9])(" + "|".join(map(re.escape, values)) + r")(?![A-Za-z0-9])")
        return pattern.sub(lambda m: self.token(self.known[m.group(1)], m.group(1)), text)

    def scrub(self, text: str) -> str:
        """A log: the known values, then the patterns, line by line where a
        rule depends on whose line it is."""
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
        if not value or re.fullmatch(r"[\d.,x-]+", value):
            return m.group(0)
        return m.group(1) + self.token("text", value)

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
    a fixed choice ("Variable", "Cubic") shows as it is."""
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


def build(note: str, rows: list[dict], get: Callable[[str], object], *, shares: Iterable[dict] = (),
          now_playing: Iterable[str] = (), run: Callable[..., str] = _run,
          clock: Callable[[], float] = time.time) -> Report:
    scrubber = Scrubber()
    learn(scrubber, rows, get, shares=shares, now_playing=now_playing)
    stamp = time.strftime("%Y-%m-%d-%H%M", time.localtime(clock()))
    files = {
        "what-happened.txt": (note or "").strip() + "\n",
        "journal.txt": journal(run=run),
        "updater/apt.log": _read(UPDATES / "apt.log", APT_LOG_MAX),
        "updater/status.json": _read(UPDATES / "status.json"),
        "versions.txt": versions(run=run),
        "hardware.txt": hardware(run=run),
    }
    scrubbed = {name: scrubber.scrub(text) for name, text in files.items()}
    scrubbed["settings.txt"] = settings_text(rows, get, scrubber)
    summary = scrubber.summary()
    readme = (
        "Gexis Player problem report\n"
        f"Made {stamp}.\n\n"
        "Personal details were taken out on the player before this file was written,\n"
        "each replaced by a token such as ip-3 or text-12, the same token wherever the\n"
        f"same value appeared. Taken out: {summary}.\n\n"
        "Taking things out by pattern can miss something: read the files before\n"
        "sharing them. Nothing was sent anywhere by the player.\n\n"
        f"To report the problem: {ISSUE_URL}\n"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", readme)
        for name, text in scrubbed.items():
            z.writestr(name, text)
    return Report(buf.getvalue(), f"gexis-report-{stamp}.zip", summary)
