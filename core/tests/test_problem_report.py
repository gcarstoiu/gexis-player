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
2026-10-07T08:12:47+02:00 livingroom python[812]: 2026-10-07 08:12:47,002 gexis_core.adapters.lms INFO lms: resolved player 'Kitchen Speaker' to id aa:bb:cc:00:00:04
2026-10-07T08:12:48+02:00 livingroom python[812]: 2026-10-07 08:12:48,003 gexis_core.enrichment INFO enrichment: looking up 'Blue Harbour Lights' by 'Nina Example'
2026-10-07T08:12:49+02:00 livingroom python[812]: 2026-10-07 08:12:49,004 gexis_core.weather INFO weather: 'Smalltown,12345, Region, Country' is Smalltown, XX (52.12345, 13.54321)
2026-10-07T08:12:50+02:00 livingroom python[812]: 2026-10-07 08:12:50,005 gexis_core.bluetooth_adapter_state INFO bluetooth: discoverable='Always'
2026-10-07T08:12:51+02:00 livingroom systemd[1]: Unmounting mnt-gexis\\x2dshares-Nasbox\\x2dlocal\\x2dTunes\\x2d9a8b7c.mount - /mnt/gexis-shares/Nasbox-local-Tunes-9a8b7c...
2026-10-07T08:12:52+02:00 livingroom bluealsa[893]: Adding new Stream End-Point: A4:5E:60:11:22:33: SRC: AAC
2026-10-07T08:12:53+02:00 livingroom wpa_supplicant[700]: wlan0: CTRL-EVENT-CONNECTED - Connection to 9c:c7:a6:00:11:22 completed [id=0 id_str=]
2026-10-07T08:12:54+02:00 livingroom systemd[1]: Started gexis-core.service - Gexis Player core at 11:45:23, version 1.2.3.4.5.
2026-10-07T08:12:56+02:00 livingroom go-librespot[2326]: time="2026-10-07T08:12:56+02:00" level=info msg="loaded track \\"Quiet Morning - 2012 Remaster\\" (paused: true)" uri="spotify:track:34xGLuxM0rkxhC"
2026-10-07T08:12:57+02:00 livingroom go-librespot[2326]: time="2026-10-07T08:12:57+02:00" level=info msg="accepted zeroconf from Phone 9 Max" username="11*****97"
2026-10-07T08:12:58+02:00 livingroom go-librespot[2326]: time="2026-10-07T08:12:58+02:00" level=error msg="failed connecting to dealer" error="failed to WebSocket dial"
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
                    "Qx7b2Lk9", "cb3a1f2e", "musicfan", "Quiet Morning", "34xGLuxM", "Phone 9 Max",
                    "11*****97"):
        assert private not in out, private


def test_what_says_what_the_software_did_stays():
    """The log still reads: unit names, versions, times, option labels, a
    built file's name."""
    _, out = scrubbed()
    for kept in ("gexis-core.service", "version 1.2.3.4.5", "11:45:23", "'Always'",
                 "nunito-sans-latin-wght-normal-BWQ3gi2K.woff2", "id=42", "Android 14", "SRC: AAC",
                 'msg="failed connecting to dealer"', "loaded track"):
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


def test_a_long_queue_over_a_long_journal_never_holds_up_the_rest_of_the_core():
    """Review, 2026-10-12: the known values were one alternation, and the
    regex engine holds the interpreter's lock for a whole call - a long
    queue's titles over the journal kept the event loop (volume,
    arbitration) waiting for seconds. A thread that wakes every 5 ms
    stands in for the loop."""
    import threading
    import time
    line = ("2026-10-07T08:12:49+02:00 box python[812]: 2026-10-07 08:12:49,004 gexis_core.library "
            "INFO library: queue add 1234 -> 17 tracks at 0.0123 s\n")
    text = line * 5000 + "2026-10-07T08:13:00+02:00 box python[812]: Jl title 2999 ends here\n"
    s = pr.Scrubber()
    for i in range(3000):       # a queue's worth, no two alike
        s.know(f"{chr(65 + i % 26)}{chr(97 + i // 26 % 26)} title {i}", "title")
    gaps, done = [], threading.Event()

    def loop():
        last = time.perf_counter()
        while not done.is_set():
            time.sleep(0.005)
            now = time.perf_counter()
            gaps.append(now - last)
            last = now
    ticker = threading.Thread(target=loop)
    ticker.start()
    try:
        out = s.scrub(text)
    finally:
        done.set()
        ticker.join()
    assert "Jl title 2999" not in out and "title-1 ends here" in out
    assert max(gaps) < 0.25, f"the loop waited {max(gaps):.2f} s"


def test_a_journal_is_scrubbed_in_whole_lines():
    s = pr.Scrubber()
    s.know("Nina Example", "title")
    text = "".join(f"line {n} by Nina Example at 10.0.4.{n % 200}\n" for n in range(400))
    assert "".join(pr._pieces(text, size=100)) == text
    assert all(p.endswith("\n") for p in pr._pieces(text, size=100))
    out = s.scrub(text)
    assert "Nina" not in out and "10.0.4." not in out and out.count("\n") == 400


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


def _quiet(monkeypatch, tmp_path):
    monkeypatch.setattr(pr, "UPDATES", tmp_path)
    monkeypatch.setattr(pr, "NM_CONNECTIONS", tmp_path / "nm")
    monkeypatch.setattr(pr, "BLUETOOTH", tmp_path / "bt")
    monkeypatch.setattr(pr, "hardware", lambda run=None: "Model: Raspberry Pi 4 Model B\n")

    def run(*cmd, timeout=None):
        return JOURNAL if cmd[0] == "journalctl" else ""
    return run


def test_the_checklist_is_told_every_step_in_order(monkeypatch, tmp_path):
    """ADR-0138 §1 (George: "details on what is being prepared similar to a
    checklist")."""
    told = []
    report = pr.build("It stopped.", ROWS, VALUES.get, shares=SHARES, run=_quiet(monkeypatch, tmp_path),
                      clock=lambda: 1791300000, progress=lambda step, detail: told.append((step, detail)))
    assert [s for s, _ in told] == [s for s, _ in pr.STEPS]
    assert dict(told)["scrub"] == report.summary
    assert dict(told)["write"].startswith(report.name)
    assert ("journal.txt", len(report.data)) not in report.files and any(n == "journal.txt" for n, _ in report.files)


def test_the_last_errors_are_the_newest_cleaned_and_bounded():
    log = "\n".join([f"2026-10-11T10:00:{i:02d} gexis_core INFO fine {i}" for i in range(50)] +
                    [f"2026-10-11T10:01:{i:02d} gexis_core ERROR broke {i}" for i in range(50)])
    errors = pr.last_errors(log, limit=300)
    assert "INFO" not in errors and errors.endswith("broke 49") and len(errors) <= 300


def test_the_issue_carries_what_happened_how_often_the_version_and_the_errors(monkeypatch, tmp_path):
    from urllib.parse import parse_qs, urlsplit
    report = pr.build("It stopped at 10.0.4.23.", ROWS, VALUES.get, shares=SHARES, run=_quiet(monkeypatch, tmp_path),
                      clock=lambda: 1791300000)
    report.errors = "\n".join(f"2026-10-11T10:01:{i % 60:02d} ERROR " + "x" * 200 for i in range(200))
    url = pr.issue_url("The sound stopped after a skip.\nThen nothing.", "Sometimes", "0.10.1", report)
    assert len(url) <= pr.URL_MAX
    q = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
    assert q["title"] == "[Problem] The sound stopped after a skip."
    assert (q["often"], q["version"]) == ("Sometimes", "0.10.1")
    assert report.name in q["report"] and "Last errors" in q["report"]
    assert "often" not in parse_qs(urlsplit(pr.issue_url("x", "Daily", "0.10.1", report)).query)


async def test_prepared_in_the_background_ticked_downloaded_sent_and_dropped_after_an_hour(tmp_path, monkeypatch):
    """ADR-0138: prepare, follow the checklist, then the file and the issue;
    gone after REPORT_KEEP_S."""
    import asyncio
    from aiohttp.test_utils import TestClient, TestServer
    from gexis_core.settings import SettingsStore
    from gexis_core.settings_registry import Settings
    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer

    def fake_build(what, rows, get, *, shares=(), now_playing=(), progress=None, **kw):
        for step, _ in pr.STEPS:
            progress(step, f"{step} done")
        return pr.Report(b"PK-zip", "gexis-report-x.zip", "2 addresses", [("journal.txt", 10)], "ERROR one")
    monkeypatch.setattr(pr, "build", fake_build)
    monkeypatch.setattr(pr, "_run", lambda *a, **k: "0.10.1+git5.abc")
    settings = Settings(SettingsStore(tmp_path / "s.db"), seed_path=tmp_path / "none.json")
    server = StateServer(StateStore({}), settings=settings)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await (await client.get("/report/status")).json())["state"] == "idle"
        assert (await client.post("/report/prepare", json={"what": "It stopped.", "often": "Once so far"})).status == 200
        for _ in range(50):
            status = await (await client.get("/report/status")).json()
            if status["state"] == "ready":
                break
            await asyncio.sleep(0.02)
        assert status["state"] == "ready" and all(s["done"] for s in status["steps"])
        assert status["files"] == [{"name": "journal.txt", "size": 10}]
        file = await client.get("/report/file")
        assert file.status == 200 and await file.read() == b"PK-zip"
        url = (await (await client.get("/report/issue")).json())["url"]
        assert "often=Once+so+far" in url and "version=0.10.1" in url
        server._report_job["at"] -= server.REPORT_KEEP_S + 1
        assert (await client.get("/report/file")).status == 404
        assert (await (await client.get("/report/status")).json())["state"] == "idle"
