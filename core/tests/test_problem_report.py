"""ADR-0125: a problem report with the personal parts taken out. Every value
here is invented; the shapes are the ones a real journal holds."""
from __future__ import annotations

import io
import zipfile

from gexis_core import problem_report as pr

JOURNAL = """\
2026-10-07T08:12:45+02:00 livingroom avahi-daemon[758]: Joining mDNS multicast group on interface wlan0.IPv4 with address 10.0.4.17.
2026-10-07T08:12:45+02:00 livingroom sshd-session[901]: Accepted publickey for pi from 10.0.4.23 port 51234 ssh2: ED25519 SHA256:Qx7b2Lk9fP0aZr4TmW8vYc3NhE6uJd1sKo5gBi2XyA
2026-10-07T08:12:46+02:00 livingroom python[812]: 2026-10-07 08:12:46,001 aiohttp.access INFO 10.0.4.23 [07/Oct/2026:08:12:46 +0200] "GET /library/artist-info?id=42&name=Nina%20Example HTTP/1.1" 200 512 "-" "Mozilla/5.0 (Linux; Android 14)"
2026-10-07T08:12:47+02:00 livingroom python[812]: 2026-10-07 08:12:47,002 gexis_core.adapters.lms INFO lms: resolved player 'Kitchen Speaker' to id 3c:22:fb:01:9a:7e
2026-10-07T08:12:48+02:00 livingroom python[812]: 2026-10-07 08:12:48,003 gexis_core.enrichment INFO enrichment: looking up 'Blue Harbour Lights' by 'Nina Example'
2026-10-07T08:12:49+02:00 livingroom python[812]: 2026-10-07 08:12:49,004 gexis_core.weather INFO weather: 'Smalltown,12345, Region, Country' is Smalltown, XX (52.12345, 13.54321)
2026-10-07T08:12:50+02:00 livingroom python[812]: 2026-10-07 08:12:50,005 gexis_core.bluetooth_adapter_state INFO bluetooth: discoverable='Always'
2026-10-07T08:12:51+02:00 livingroom systemd[1]: Unmounting mnt-gexis\\x2dshares-Nasbox\\x2dlocal\\x2dTunes\\x2d9a8b7c.mount - /mnt/gexis-shares/Nasbox-local-Tunes-9a8b7c...
2026-10-07T08:12:52+02:00 livingroom bluealsa[893]: Adding new Stream End-Point: A4:5E:60:11:22:33: SRC: AAC
2026-10-07T08:12:53+02:00 livingroom wpa_supplicant[700]: wlan0: CTRL-EVENT-CONNECTED - Connection to 9c:c7:a6:00:11:22 completed [id=0 id_str=]
2026-10-07T08:12:54+02:00 livingroom systemd[1]: Started gexis-core.service - Gexis Player core at 11:45:23, version 1.2.3.4.5.
2026-10-07T08:12:55+02:00 livingroom python[812]: GET /assets/nunito-sans-latin-wght-normal-BWQ3gi2K.woff2 boot cb3a1f2e-5b7d-4e8a-9c21-7d4e5f6a8b90
"""

ROWS = [
    {"key": "device_name", "type": "text", "default": "gexis"},
    {"key": "weather_location", "type": "text", "default": None},
    {"key": "lms_server", "type": "list", "default": None},
    {"key": "bt_discoverable", "type": "choice", "options": ["Always", "When asked"], "default": "When asked"},
    {"key": "output_mode", "type": "choice", "options": ["Variable", "Fixed"], "default": "Variable"},
    {"key": "fanart_key", "type": "text", "secret": True, "default": None},
    {"key": "backup", "type": "action", "default": None},
]
VALUES = {"device_name": "livingroom", "weather_location": "Smalltown,12345, Region, Country",
          "lms_server": "10.0.4.5:9000", "bt_discoverable": "Always", "output_mode": "Fixed",
          "fanart_key": "f00dfeedcafebabe0123456789abcdef"}
SHARES = [{"address": "//Nasbox.local/Tunes", "user": "musicfan"}]


def scrubbed(text=JOURNAL, now_playing=("Blue Harbour Lights", "Nina Example")):
    s = pr.Scrubber()
    pr.learn(s, ROWS, VALUES.get, shares=SHARES, now_playing=now_playing)
    return s, s.scrub(text)


def test_nothing_personal_is_left():
    _, out = scrubbed()
    for private in ("10.0.4.17", "10.0.4.23", "Nina", "Blue Harbour", "Kitchen Speaker", "3c:22:fb",
                    "Smalltown", "52.12345", "Nasbox", "A4:5E:60", "9c:c7:a6", "livingroom",
                    "Qx7b2Lk9", "cb3a1f2e", "musicfan"):
        assert private not in out, private


def test_what_says_what_the_software_did_stays():
    """The log still reads: unit names, versions, times, option labels, a
    built file's name."""
    _, out = scrubbed()
    for kept in ("gexis-core.service", "version 1.2.3.4.5", "11:45:23", "'Always'",
                 "nunito-sans-latin-wght-normal-BWQ3gi2K.woff2", "id=42", "Android 14", "SRC: AAC"):
        assert kept in out, kept


def test_the_same_value_is_the_same_token_everywhere():
    s, out = scrubbed()
    token = s.tokens[("ip", "10.0.4.23")]
    assert out.count(token) == 2


def test_the_product_name_is_not_taken_for_a_private_one():
    """A device left named "gexis" is not private, and "gexis-core" must
    survive whatever the device is called."""
    s = pr.Scrubber()
    pr.learn(s, ROWS, {**VALUES, "device_name": "gexis"}.get)
    assert "gexis-core.service" in s.scrub(JOURNAL)


def test_settings_show_choices_and_hide_what_a_person_typed():
    s = pr.Scrubber()
    pr.learn(s, ROWS, VALUES.get)
    text = pr.settings_text(ROWS, VALUES.get, s)
    assert 'output_mode = "Fixed"' in text and 'bt_discoverable = "Always"' in text
    assert "f00dfeed" not in text and 'fanart_key = "(set, not included)"' in text
    assert "Smalltown" not in text and "livingroom" not in text and "10.0.4.5" not in text
    assert "backup" not in text


def test_the_report_is_one_zip_with_a_readme_that_says_what_went(monkeypatch, tmp_path):
    monkeypatch.setattr(pr, "UPDATES", tmp_path)
    (tmp_path / "apt.log").write_text("Get:1 https://example.invalid/r0.9.2 gexis-core\n")
    (tmp_path / "status.json").write_text('{"state": "current"}')
    monkeypatch.setattr(pr, "NM_CONNECTIONS", tmp_path / "nm")
    monkeypatch.setattr(pr, "BLUETOOTH", tmp_path / "bt")
    monkeypatch.setattr(pr, "hardware", lambda run=None: "Model: Raspberry Pi 4 Model B\n")

    def run(*cmd, timeout=None):
        return JOURNAL if cmd[0] == "journalctl" else ""

    report = pr.build("The sound stopped at 10.0.4.23 after a skip.", ROWS, VALUES.get, shares=SHARES,
                      now_playing=("Blue Harbour Lights",), run=run, clock=lambda: 1791300000)
    assert report.name.startswith("gexis-report-") and report.name.endswith(".zip")
    with zipfile.ZipFile(io.BytesIO(report.data)) as z:
        names = set(z.namelist())
        assert {"README.txt", "what-happened.txt", "journal.txt", "updater/apt.log", "updater/status.json",
                "versions.txt", "hardware.txt", "settings.txt"} <= names
        everything = "".join(z.read(n).decode() for n in names)
        readme = z.read("README.txt").decode()
        note = z.read("what-happened.txt").decode()
    assert "10.0.4.23" not in everything and "Nasbox" not in everything
    assert "read the files before" in readme and report.summary in readme
    assert note.startswith("The sound stopped at ip-") and "after a skip." in note


def test_a_journal_over_the_limit_keeps_its_newest_lines():
    lines = "".join(f"line {n}\n" for n in range(1000))
    out = pr.journal(limit=200, run=lambda *a, **k: lines)
    assert out.endswith("line 999\n") and len(out.encode()) <= 200 and out.startswith("line ")
