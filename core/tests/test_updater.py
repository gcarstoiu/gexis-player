"""ADR-0105 §4, ADR-0108: the updater's own judgement, without a device."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import io
import time
import json
import subprocess
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "updater" / "gexis-update"


@pytest.fixture
def up(tmp_path, monkeypatch):
    loader = importlib.machinery.SourceFileLoader("gexis_update", str(PATH))
    spec = importlib.util.spec_from_loader("gexis_update", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    monkeypatch.setattr(module, "STATE", tmp_path / "updates")
    return module


def channel_text(channel="testing", serial=3, release="0.2.1+git900.abc1234"):
    return (f"Channel: {channel}\nSerial: {serial}\nDate: 2026-10-01T00:00:00Z\n"
            f"Release: {release}\nRepositories: r{release.replace('+', '-')} r{release.replace('+', '-')}-debian\n")


def serve(monkeypatch, up, text, verified=True):
    """The channel file as GitHub would hand it, and gpgv's verdict on it."""
    monkeypatch.setattr(up.urllib.request, "urlopen", lambda url, timeout=0: io.BytesIO(b"signed"))
    def fake_run(args, input=None, capture_output=False, **kw):
        assert args[0] == "gpgv", "only gpgv reads what came from the network"
        return subprocess.CompletedProcess(args, 0 if verified else 1, text.encode() if verified else b"", b"")
    monkeypatch.setattr(up.subprocess, "run", fake_run)


def test_a_verified_channel_is_read(monkeypatch, up):
    serve(monkeypatch, up, channel_text())
    ch = up.read_channel("testing")
    assert ch["Release"] == "0.2.1+git900.abc1234" and ch["_serial"] == 3


def test_an_unverified_channel_is_refused(monkeypatch, up):
    serve(monkeypatch, up, channel_text(), verified=False)
    with pytest.raises(up.Stop, match="not signed"):
        up.read_channel("testing")


def test_a_serial_that_went_down_is_refused(monkeypatch, up):
    """ADR-0108: an old, genuinely signed file cannot hold a device back."""
    up.remember_serial("testing", 5)
    serve(monkeypatch, up, channel_text(serial=4))
    with pytest.raises(up.Stop, match="serial went down"):
        up.read_channel("testing")


def test_a_channel_in_a_newer_format_says_the_updater_is_too_old(monkeypatch, up):
    """LESSONS 49: a layout this updater cannot read is named, not a 404."""
    serve(monkeypatch, up, "Format: 3\n" + channel_text())
    with pytest.raises(up.Stop, match="needs a newer updater"):
        up.read_channel("testing")


def test_a_channel_in_this_format_or_none_is_read(monkeypatch, up):
    for text in ("Format: 2\n" + channel_text(), channel_text()):
        serve(monkeypatch, up, text)
        assert up.read_channel("testing")["Release"] == "0.2.1+git900.abc1234"


def test_a_file_for_the_other_channel_is_refused(monkeypatch, up):
    serve(monkeypatch, up, channel_text(channel="stable"))
    with pytest.raises(up.Stop, match="says it is for"):
        up.read_channel("testing")


def test_the_tag_is_the_version_with_plus_spelled_as_dash(up):
    assert up.tag_of("0.2.1+git833.1006239") == "r0.2.1-git833.1006239"


def test_the_plan_reads_what_apt_would_change(monkeypatch, up):
    sim = ("Inst gexis-core [0.2.1+git828.523f5cc] (0.2.1+git900.abc1234 Gexis Player:r0.2.1-git900.abc1234 [arm64])\n"
           "Inst libfoo (1.0-1 Gexis Player:r0.2.1-git900.abc1234 [arm64])\n"
           "Conf gexis-core (0.2.1+git900.abc1234 Gexis Player:r0.2.1-git900.abc1234 [arm64])\n")
    monkeypatch.setattr(up, "apt", lambda opts, *a: subprocess.CompletedProcess(a, 0, sim, ""))
    assert up.plan([], "0.2.1+git900.abc1234") == [
        ("gexis-core", "0.2.1+git828.523f5cc", "0.2.1+git900.abc1234"),
        ("libfoo", None, "1.0-1"),
    ]


def view_of(up, opts):
    lists = next(o for o in opts if o.startswith("Dir::State::lists="))
    return Path(lists.split("=", 1)[1]).parent


def test_apt_sees_only_the_listed_repositories_and_prefers_them_when_going_back(up):
    opts = up.apt_env(["ours-aaa", "debian-bbb"], pins=["ours-aaa", "debian-bbb"])
    view = view_of(up, opts)
    sources = (view / "sources.list").read_text()
    assert sources.count("deb [signed-by=") == 2 and "/ours-aaa/ ./" in sources and "/debian-bbb/ ./" in sources
    parts = view / "sources.list.d"
    assert f"Dir::Etc::sourceparts={parts}" in opts and not any(parts.iterdir()), \
        "the device's own sources are not read: the parts folder is ours, and empty"
    prefs = (view / "preferences").read_text()
    assert prefs.count("Pin-Priority: 1001") == 2 and "a=debian-bbb" in prefs


def test_the_release_kept_for_going_back_does_not_replace_the_one_going_in(up):
    """Found on the device, 2026-09-30: one shared index, and the install
    found no gexis-player - the going-back fetch had replaced it."""
    going_in = up.apt_env(["ours-new", "debian-same"])
    going_back = up.apt_env(["ours-old", "debian-same"], pins=["ours-old", "debian-same"])
    cache = lambda opts: next(o for o in opts if o.startswith("Dir::Cache::archives="))
    assert view_of(up, going_in) != view_of(up, going_back)
    assert cache(going_in) == cache(going_back), "one cache: a file is the same file"


def test_a_release_with_a_parts_file_goes_back_to_its_parts(up, monkeypatch):
    """ADR-0108 as amended: a release is parts, named by content."""
    serve(monkeypatch, up, "Release: 0.2.1+git900.abc\nParts: ours-111 skins-222 rpi-333 debian-444\n")
    assert up.parts_of("0.2.1+git900.abc") == (["ours-111", "skins-222", "rpi-333", "debian-444"],) * 2


def test_a_release_from_before_parts_is_read_the_old_way(up, monkeypatch):
    def gone(url, timeout=0):
        raise OSError("404")
    monkeypatch.setattr(up.urllib.request, "urlopen", gone)
    assert up.parts_of("0.2.1+git852.13f1359") == (["r0.2.1-git852.13f1359", "r0.2.1-git852.13f1359-debian"],
                                                  ["r0.2.1-git852.13f1359"])


def test_an_unsigned_parts_file_is_refused(up, monkeypatch):
    serve(monkeypatch, up, "Release: 1\nParts: ours-x\n", verified=False)
    with pytest.raises(up.Stop, match="not signed"):
        up.parts_of("1")


def test_stable_is_the_channel_when_nothing_was_chosen(up, tmp_path, monkeypatch):
    monkeypatch.setattr(up, "SETTINGS_DB", tmp_path / "missing.db")
    assert up.channel_name(None) == "stable"


def test_an_update_never_restarts_itself_or_the_shutdown_pause(up, monkeypatch):
    """The first update on the device listed both: restarting the unit the
    updater runs as ends it mid-update, and stopping gexis-park pauses LMS."""
    files = "\n".join(f"/usr/lib/systemd/system/{u}" for u in
                      ("gexis-core.service", "gexis-park.service", "gexis-update-install.service",
                       "gexis-update-check.service", "gexis-update-check.timer"))
    restarted = []
    def fake_run(*args, check=True, env=None):
        if args[:2] == ("dpkg", "-L"):
            return subprocess.CompletedProcess(args, 0, files, "")
        if args[:2] == ("systemctl", "try-restart"):
            restarted.append(args[2])
        return subprocess.CompletedProcess(args, 0, "", "")
    monkeypatch.setattr(up, "run", fake_run)
    monkeypatch.setattr(up, "REBOOT_MARKER", up.STATE / "no-marker")
    up.restart([("gexis-core", "1", "2")])
    assert restarted == ["gexis-core.service"]


def test_manual_never_installs_at_night(up, monkeypatch):
    monkeypatch.setattr(up, "check", lambda args: ("testing", {"Release": "2", "_serial": 2}))
    monkeypatch.setattr(up, "setting", lambda key: "Manual" if key == "updates" else None)
    monkeypatch.setattr(up, "install", lambda args: (_ for _ in ()).throw(AssertionError("installed")))
    assert up.scheduled(None) == 0


def test_automatic_skips_a_release_that_failed_here_and_takes_a_newer_one(up, monkeypatch):
    """Finding 105: without this, a broken release is tried every night."""
    up.STATE.mkdir(parents=True, exist_ok=True)
    (up.STATE / "failed-testing").write_text("2")
    monkeypatch.setattr(up, "setting", lambda key: "Automatic" if key == "updates" else None)
    monkeypatch.setattr(up, "installed", lambda p: "1")
    monkeypatch.setattr(up, "playing", lambda: False)
    installs = []
    monkeypatch.setattr(up, "install", lambda args: installs.append(1) or 0)
    monkeypatch.setattr(up, "check", lambda args: ("testing", {"Release": "2", "_serial": 2}))
    up.scheduled(None)
    assert installs == [], "the failed release is not retried by itself"
    monkeypatch.setattr(up, "check", lambda args: ("testing", {"Release": "3", "_serial": 3}))
    up.scheduled(None)
    assert installs == [1], "a newer release is"


def test_a_release_s_signed_notes_are_read(up, monkeypatch):
    """2026-10-01: the release says what changed, signed like the channel."""
    serve(monkeypatch, up, "New: release notes.\n")
    assert up.release_notes("0.2.1+git900.abc1234") == "New: release notes."


def test_a_release_s_notes_are_kept_whole(up, monkeypatch):
    """2026-10-05: notes were cut at 1,200 characters - 0.9.0's and 0.9.1's
    ended mid-word ("Starting volume is now b") on the phone's dialog."""
    notes = "New\n" + "\n".join(f"• Change number {n}, said in a sentence of its own." for n in range(40))
    assert len(notes) > 1900
    serve(monkeypatch, up, notes + "\n")
    assert up.release_notes("0.2.1+git900.abc1234") == notes


def test_notes_that_do_not_verify_are_not_shown(up, monkeypatch):
    serve(monkeypatch, up, "anything", verified=False)
    assert up.release_notes("0.2.1+git900.abc1234") is None


def test_a_release_without_notes_updates_all_the_same(up, monkeypatch):
    def missing(url, timeout=0):
        raise OSError("404")
    monkeypatch.setattr(up.urllib.request, "urlopen", missing)
    assert up.release_notes("0.2.1+git900.abc1234") is None


def test_a_night_that_finds_music_does_not_wait_and_tries_tomorrow(up, monkeypatch):
    """ADR-0110 §4: nobody can be asked at night, so nothing is stopped."""
    monkeypatch.setattr(up, "setting", lambda key: "Automatic" if key == "updates" else None)
    monkeypatch.setattr(up, "installed", lambda p: "1")
    monkeypatch.setattr(up, "check", lambda args: ("testing", {"Release": "2", "_serial": 2}))
    monkeypatch.setattr(up, "playing", lambda: True)
    monkeypatch.setattr(up, "install", lambda args: (_ for _ in ()).throw(AssertionError("installed")))
    assert up.scheduled(None) == 0
    doc = json.loads((up.STATE / "status.json").read_text())
    assert doc["state"] == "available" and "tomorrow night" in doc["message"]


def fake_install(up, monkeypatch, *, fail_install=False, answers=True):
    """An install with apt, the core and the network replaced: what it
    reports, step by step."""
    seen, order = [], []
    real_report = up.report
    def report(state, **fields):
        real_report(state, **fields)
        seen.append(json.loads((up.STATE / "status.json").read_text()))
    monkeypatch.setattr(up, "report", report)
    monkeypatch.setattr(up, "check", lambda args: ("testing", {"Release": "2", "_serial": 2,
                                                                "Repositories": "ours-x", "_whats_new": "New."}))
    monkeypatch.setattr(up, "installed", lambda p: "1")
    monkeypatch.setattr(up, "parts_of", lambda v: (["ours-old"], ["ours-old"]))
    monkeypatch.setattr(up, "apt_env", lambda repos, pins=None: [])
    monkeypatch.setattr(up, "plan", lambda opts, v: [("gexis-core", "1", "2")])
    def apt(opts, *args, prefix=None):
        if fail_install and "--no-download" in args and "dist-upgrade" in args and prefix and "--allow-downgrades" not in args:
            return subprocess.CompletedProcess(args, 100, "", "E: broken")
        return subprocess.CompletedProcess(args, 0, "", "")
    monkeypatch.setattr(up, "apt", apt)
    def apt_progress(opts, *args, state, report_as, reporter=None, prefix=None, span=(0.0, 1.0), sizes=None):
        r = apt(opts, *args, prefix=prefix)
        if r.returncode == 0:
            up.PROGRESS["progress"] = span[1]
            up.report(state, **report_as)
        return r
    monkeypatch.setattr(up, "apt_progress", apt_progress)
    def apt_download(opts, *args, report_as):
        up.PROGRESS["progress"] = 0.5
        up.report("downloading", **report_as)
        return subprocess.CompletedProcess(args, 0, "", "")
    monkeypatch.setattr(up, "apt_download", apt_download)
    monkeypatch.setattr(up, "back_up", lambda: order.append("backup") or "b.tgz")
    monkeypatch.setattr(up, "stop_playback", lambda: order.append("stop"))
    monkeypatch.setattr(up, "verify", lambda v: None)
    monkeypatch.setattr(up, "restart", lambda changes: order.append("restart") or "services: gexis-core.service")
    monkeypatch.setattr(up, "core_answers", lambda timeout=120: answers)
    monkeypatch.setattr(up, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, "", ""))
    up.STATE.mkdir(parents=True, exist_ok=True)
    return seen, order


def test_an_install_reports_every_step_and_the_download_s_share(up, monkeypatch):
    """ADR-0110 §3: every step listed from the start, each marked as it goes."""
    seen, order = fake_install(up, monkeypatch)
    assert up.install(None) == 0
    first = next(s for s in seen if "steps" in s)
    assert list(first["steps"]) == list(up.STEPS) and set(first["steps"].values()) <= {"pending", "active"}
    assert any(s["state"] == "downloading" and s.get("progress") == 0.5 for s in seen)
    assert order == ["backup", "stop", "restart"], "playback stops after the backup, before the install"
    last = seen[-1]
    assert last["state"] == "done" and set(last["steps"].values()) == {"done"}
    assert last["whats_new"] == "New." and last["previous"] == "1"


def test_a_failed_install_marks_its_step_and_goes_back(up, monkeypatch):
    seen, order = fake_install(up, monkeypatch, fail_install=True)
    assert up.install(None) == 1
    last = seen[-1]
    assert last["state"] == "failed" and last["steps"]["install"] == "failed"
    assert last["attempted"] == "2"


def test_apt_s_download_status_becomes_the_share_done(up, monkeypatch):
    lines = ["dlstatus:1:0.0000:Retrieving file 1 of 3\n", "dlstatus:2:42.5:Retrieving file 2 of 3\n",
             "Get:1 http://x y [1 kB]\n", "dlstatus:3:100:Done\n"]
    class Proc:
        def __init__(self, *a, **k):
            self.stdout = iter(lines)
            self.stderr = io.StringIO("")
            self.returncode = 0
        def wait(self):
            return 0
    monkeypatch.setattr(up.subprocess, "Popen", Proc)
    up.STATE.mkdir(parents=True, exist_ok=True)
    shares = []
    monkeypatch.setattr(up, "report", lambda state, **f: shares.append(up.PROGRESS.get("progress")))
    monkeypatch.setattr(up.time, "monotonic", iter(range(0, 100, 2)).__next__)
    r = up.apt_download([], "--download-only", "dist-upgrade", report_as={})
    assert r.returncode == 0 and up.PROGRESS["progress"] == 1.0
    assert 0.425 in shares


def test_dpkg_s_install_status_moves_the_install_bar_within_its_span(up, monkeypatch):
    # George, 2026-10-04: the install step showed no progress.
    lines = ["pmstatus:gexis-core:10.0:Preparing gexis-core\n", "Setting up gexis-core (2) ...\n",
             "pmstatus:gexis-ui:50:Installing gexis-ui\n", "pmstatus:dpkg-exec:100:Done\n"]
    class Proc:
        def __init__(self, *a, **k):
            self.stdout = iter(lines)
            self.stderr = io.StringIO("")
            self.returncode = 0
        def wait(self):
            return 0
    monkeypatch.setattr(up.subprocess, "Popen", Proc)
    up.STATE.mkdir(parents=True, exist_ok=True)
    up.PROGRESS.clear()
    seen = []
    monkeypatch.setattr(up, "report", lambda state, **f: seen.append((state, up.PROGRESS.get("progress"))))
    monkeypatch.setattr(up.time, "monotonic", iter(range(0, 100, 2)).__next__)
    up.apt_progress([], "--no-download", "dist-upgrade", state="installing", report_as={}, span=(0.0, 0.95))
    assert ("installing", 0.475) in seen and up.PROGRESS["progress"] == 0.95


#: dpkg's lines from 0.9.1's install on gexis (2026-10-05), and its archives.
INSTALL_091 = [("gexis-player", "Preparing gexis-player"), ("gexis-player", "Unpacking gexis-player"),
               ("gexis-player", "Installing gexis-player"), ("gexis-core", "Preparing gexis-core"),
               ("gexis-core", "Unpacking gexis-core")]
SIZES_091 = {"gexis-core": 75_691_828, "gexis-player": 13_540}


def test_dpkg_s_share_weighs_packages_by_size_and_moves_on_with_time(up):
    """George, 2026-10-05: 0 % for 35 s, then 42 %. The 13 KB package no
    longer counts as much as the 75 MB one, and while gexis-core unpacks the
    bar moves - never as far as the next action."""
    now = [0.0]
    dpkg = up.DpkgShare(SIZES_091, clock=lambda: now[0])
    for package, action in INSTALL_091:
        dpkg.saw(package, action)
    at_start = dpkg.share()
    assert 0.04 < at_start < 0.06, "gexis-player's own steps are next to nothing"
    shares = []
    for second in range(0, 61, 5):
        now[0] = second
        shares.append(dpkg.share())
    assert shares == sorted(shares) and shares[-1] > shares[0] + 0.3, shares
    assert all(s < 0.7 for s in shares), "never past where dpkg says unpacking ends"
    assert 0.25 < shares[3] < 0.55, f"after 15 s of a 35 s unpack: {shares[3]:.2f}"
    dpkg.saw("gexis-core", "Installing gexis-core")
    assert abs(dpkg.share() - 0.7) < 0.01
    for package in SIZES_091:
        dpkg.saw(package, f"Installed {package}")
    assert dpkg.share() == 1.0
    # An action seen again, or out of order, never takes the bar back.
    dpkg.saw("gexis-core", "Unpacking gexis-core")
    assert dpkg.share() == 1.0


def test_a_share_read_while_another_was_just_reported_still_reaches_the_screen(up, monkeypatch):
    """2026-10-05: lines within a second of the last report were not passed
    on, and dpkg then went quiet - the screen showed the older share. A
    timer passes on the newest one while apt is quiet."""
    reported, quiet = [], []

    def lines():
        yield "pmstatus:gexis-core:10.0:Preparing gexis-core\n"
        yield "pmstatus:gexis-core:33.3:Unpacking gexis-core\n"
        quiet.append(True)
        time.sleep(1.3)    # dpkg unpacking, saying nothing
        yield "pmstatus:dpkg-exec:100:Done\n"

    class Proc:
        def __init__(self, *a, **k):
            self.stdout = lines()
            self.stderr = io.StringIO("")
            self.returncode = 0
        def wait(self):
            return 0
    monkeypatch.setattr(up.subprocess, "Popen", Proc)
    up.STATE.mkdir(parents=True, exist_ok=True)
    up.PROGRESS.clear()
    monkeypatch.setattr(up, "report", lambda state, **f: reported.append((bool(quiet), up.PROGRESS.get("progress"))))
    monkeypatch.setattr(up.time, "monotonic", lambda: 0.0)   # never a second since the last
    up.apt_progress([], "--no-download", "dist-upgrade", state="installing", report_as={})
    assert (True, 0.333) in reported, reported


def test_an_install_s_bar_reaches_the_end(up, monkeypatch):
    seen, _ = fake_install(up, monkeypatch)
    assert up.install(None) == 0
    installing = [d.get("progress") for d in seen if d["state"] == "installing"]
    assert installing[0] == 0.0 and installing[-1] == 1.0


def test_only_a_skin_pack_is_installed_or_removed_this_way(up):
    """ADR-0111: the helper installs gexis-skins-<W>x<H> and nothing else."""
    for bad in ("gexis-core", "gexis-skins", "gexis-skins-1920x1080; rm -rf /", None):
        with pytest.raises(up.Stop):
            up.pack_install(bad)
    # Removing also takes today's gexis-skins, which kept devices have
    # (ADR-0111 decision 10); nothing else.
    for bad in ("gexis-core", "gexis-skins-1920x1080; rm -rf /", None):
        with pytest.raises(up.Stop):
            up.pack_remove(bad)


def test_a_pack_comes_from_the_installed_release_s_own_parts(up, monkeypatch):
    calls = []
    monkeypatch.setattr(up, "installed", lambda p: "0.4.0" if p == "gexis-player" else "0.4.0")
    monkeypatch.setattr(up, "parts_of", lambda v: (["ours-a", "skins-b"], ["ours-a", "skins-b"]) if v == "0.4.0" else None)
    monkeypatch.setattr(up, "apt_env", lambda repos, pins=None: calls.append(("env", repos, pins)) or ["opts"])
    monkeypatch.setattr(up, "apt", lambda opts, *a, **k: calls.append(("apt",) + a) or subprocess.CompletedProcess(a, 0, "", ""))
    def fetch(opts, name, activity):
        up.PROGRESS["progress"] = 0.5
        up.report_pack("downloading", package=name, message=f"fetching {name}")
        calls.append(("download", "--download-only", "install", name))
        return subprocess.CompletedProcess([], 0, "", "")
    monkeypatch.setattr(up, "pack_fetch", fetch)
    real = up.Activity
    monkeypatch.setattr(up, "Activity", lambda **kw: real(playing_now=lambda: False, follow=False))
    up.STATE.mkdir(parents=True, exist_ok=True)
    assert up.pack_install("gexis-skins-1920x1080") == 0
    assert calls[0] == ("env", ["ours-a", "skins-b"], ["ours-a", "skins-b"])
    assert ("download", "--download-only", "install", "gexis-skins-1920x1080") in calls
    assert ("apt", "--no-download", "install", "gexis-skins-1920x1080") in calls
    doc = json.loads((up.STATE / "pack.json").read_text())
    assert doc["state"] == "installed" and doc["package"] == "gexis-skins-1920x1080"
    assert not (up.STATE / "status.json").exists(), "a pack never writes the update's status"


def test_a_pack_for_an_unpublished_release_comes_from_the_channel_s(up, monkeypatch):
    # Found 2026-10-04: a preview (0.8.6+git16) has no release to read, and
    # every pack failed with apt's words on the row.
    envs = []
    monkeypatch.setattr(up, "installed", lambda p: "0.8.6+git16.d91a4bc")
    monkeypatch.setattr(up, "parts_of", lambda v: (["r0.8.6-git16.d91a4bc"], ["r0.8.6-git16.d91a4bc"]))
    monkeypatch.setattr(up, "channel_name", lambda given: "testing")
    monkeypatch.setattr(up, "read_channel", lambda ch: {"Repositories": "ours-f skins-9 rpi-d debian-7"})
    monkeypatch.setattr(up, "apt_env", lambda repos, pins=None: envs.append(repos) or repos)
    monkeypatch.setattr(up, "apt", lambda opts, *a, **k: subprocess.CompletedProcess(
        a, 100 if (a == ("update",) and opts[0].startswith("r0.8.6-git16")) else 0, "", ""))
    monkeypatch.setattr(up, "pack_fetch", lambda opts, name, activity: subprocess.CompletedProcess([], 0, "", ""))
    real = up.Activity
    monkeypatch.setattr(up, "Activity", lambda **kw: real(playing_now=lambda: False, follow=False))
    up.STATE.mkdir(parents=True, exist_ok=True)
    assert up.pack_install("gexis-skins-1920x1080") == 0
    assert envs == [["r0.8.6-git16.d91a4bc"], ["ours-f", "skins-9", "rpi-d", "debian-7"]]


def test_a_pack_no_release_can_give_says_so_in_words(up, monkeypatch):
    monkeypatch.setattr(up, "installed", lambda p: "0.8.6+git16.d91a4bc")
    monkeypatch.setattr(up, "parts_of", lambda v: (["r-x"], ["r-x"]))
    def no_channel(ch):
        raise up.Stop("could not reach it")
    monkeypatch.setattr(up, "read_channel", no_channel)
    monkeypatch.setattr(up, "channel_name", lambda given: "stable")
    monkeypatch.setattr(up, "apt_env", lambda repos, pins=None: repos)
    monkeypatch.setattr(up, "apt", lambda opts, *a, **k: subprocess.CompletedProcess(a, 100, "", ""))
    up.STATE.mkdir(parents=True, exist_ok=True)
    with pytest.raises(up.Stop) as stop:
        up.pack_install("gexis-skins-1920x1080")
    assert str(stop.value) == up.UNREACHABLE and "apt" not in str(stop.value)


def test_a_kept_gexis_skins_is_marked_installed_by_hand(up, monkeypatch):
    """ADR-0111 decision 10: no release depends on it any more."""
    fake_install(up, monkeypatch)
    calls = []
    monkeypatch.setattr(up, "run", lambda *a, **k: calls.append(a) or subprocess.CompletedProcess(a, 0, "", ""))
    assert up.install(None) == 0
    assert ("apt-mark", "manual", "gexis-skins") in calls


def test_an_update_waits_for_a_pack_download_and_says_so(up, monkeypatch):
    """Found on George's player, 2026-10-03: the update failed on apt's lock
    while the core was downloading the 1920x1080 pack. One apt at a time."""
    import fcntl
    import threading

    up.STATE.mkdir(parents=True)
    other = (up.STATE / "apt-turn.lock").open("w")
    fcntl.flock(other, fcntl.LOCK_EX)          # the pack download, holding it
    said = []
    monkeypatch.setattr(up.time, "sleep", lambda s: None)
    threading.Timer(0.05, other.close).start()  # ...and finishing
    held = up.take_turn(lambda: said.append("waiting"))
    assert said == ["waiting"] and held is not None


def test_a_turn_not_given_within_the_hour_is_a_failure(up, monkeypatch):
    import fcntl

    up.STATE.mkdir(parents=True)
    other = (up.STATE / "apt-turn.lock").open("w")
    fcntl.flock(other, fcntl.LOCK_EX)
    monkeypatch.setattr(up, "TURN_WAIT_S", 0)
    with pytest.raises(up.Stop, match="did not finish within an hour"):
        up.take_turn(lambda: None)
    other.close()


def test_apt_listchanges_is_off_for_an_install(up):
    """It read every package's changelog before dpkg began: 8.8 s for
    gexis-core on a Pi 4, the bar at 0 for 16 s (2026-10-06)."""
    assert up.APT_ENV["APT_LISTCHANGES_FRONTEND"] == "none"
    assert up.APT_ENV["DEBIAN_FRONTEND"] == "noninteractive"


def test_the_settings_button_checks_and_never_installs():
    """"Check for updates" started the nightly unit, whose `scheduled` run
    installs when Updates is Automatic (2026-10-06)."""
    from gexis_core import updates

    unit = Path(__file__).resolve().parents[1] / "updater" / "units" / updates.CHECK_UNIT
    assert updates.CHECK_UNIT != "gexis-update-check.service"
    exec_start = next(l for l in unit.read_text().splitlines() if l.startswith("ExecStart="))
    assert exec_start.split()[-1] == "check"
    build = (Path(__file__).resolve().parents[2] / "packaging" / "core" / "build.sh").read_text()
    assert updates.CHECK_UNIT in build


# --- ADR-0110 amended 2026-10-07: every skipped release's notes -------------

def _vkey(v):
    """dpkg's order for the versions these tests use: x.y.z, then a
    +gitN build of it after the release itself."""
    base, _, build = v.partition("+git")
    nums = tuple(int(p) for p in base.split("."))
    return nums + ((1, int(build.split(".")[0])) if build else (0, 0))


def serve_history(monkeypatch, up, releases, verified=True):
    text = json.dumps({"releases": releases})
    monkeypatch.setattr(up.urllib.request, "urlopen", lambda url, timeout=0: io.BytesIO(b"signed"))
    def fake_run(args, input=None, capture_output=False, **kw):
        if args[0] == "dpkg":
            a, op, b = args[2], args[3], args[4]
            assert op == "gt"
            return subprocess.CompletedProcess(args, 0 if _vkey(a) > _vkey(b) else 1, "", "")
        assert args[0] == "gpgv", "only gpgv reads what came from the network"
        return subprocess.CompletedProcess(args, 0 if verified else 1, text.encode() if verified else b"", b"")
    monkeypatch.setattr(up.subprocess, "run", fake_run)


HISTORY = {v: {"date": f"2026-10-0{i}", "notes": f"New\n• What {v} changed."}
           for i, v in enumerate(["0.9.5", "0.9.4", "0.9.3", "0.9.2", "0.9.1"], start=1)}


def test_every_release_after_the_installed_one_is_shown_newest_first(up, monkeypatch):
    """George, 2026-10-07: "the update screen should show all until the
    current one"."""
    serve_history(monkeypatch, up, HISTORY)
    got = up.release_history("0.9.4", "0.9.1")
    assert [e["release"] for e in got] == ["0.9.4", "0.9.3", "0.9.2"]
    assert got[0]["notes"] == "New\n• What 0.9.4 changed." and got[0]["date"] == "2026-10-02"


def test_a_build_between_releases_counts_as_its_release(up, monkeypatch):
    """A preview build of 0.9.2 already has what 0.9.2 changed."""
    serve_history(monkeypatch, up, HISTORY)
    assert [e["release"] for e in up.release_history("0.9.3", "0.9.2+git32.b8a250b")] == ["0.9.3"]


def test_a_history_that_does_not_verify_falls_back_to_the_notes(up, monkeypatch):
    serve_history(monkeypatch, up, HISTORY, verified=False)
    assert up.release_history("0.9.4", "0.9.1") is None


def test_a_release_without_a_history_falls_back_to_the_notes(up, monkeypatch):
    def missing(url, timeout=0):
        raise OSError("404")
    monkeypatch.setattr(up.urllib.request, "urlopen", missing)
    assert up.release_history("0.9.4", "0.9.1") is None


def test_a_long_history_keeps_the_newest_and_counts_the_rest(up, monkeypatch):
    long_notes = "New\n" + "• A change said at length. " * 600
    many = {f"0.{n}.0": {"date": "2026-10-01", "notes": long_notes} for n in range(1, 31)}
    serve_history(monkeypatch, up, many)
    got = up.release_history("0.30.0", "0.0.1")
    kept = [e for e in got if e["release"]]
    assert kept[0]["release"] == "0.30.0" and len(kept) < 30
    assert sum(len(e["notes"]) for e in kept) <= up.HISTORY_MAX
    assert got[-1] == {"release": None, "date": None, "earlier": 30 - len(kept)}


# --- ADR-0111 amended 2026-10-07: a pack downloads gently while in use -------

class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_in_use_while_something_plays_and_for_ten_minutes_after_a_phone(up):
    clock, playing = Clock(), [False]
    a = up.Activity(clock=clock, playing_now=lambda: playing[0], follow=False)
    assert not a.in_use(), "a quiet player downloads at full speed"
    a.saw()                       # "accepted zeroconf from ..." - nothing plays yet
    clock.t += up.QUIET_S - 1
    assert a.in_use()
    clock.t += 2
    assert not a.in_use(), "ten quiet minutes"
    playing[0] = True
    assert a.in_use()


def test_go_librespot_s_own_errors_are_not_a_person(up):
    assert up._activity_line('Oct 07 12:03:47 p go-librespot[2326]: level=info msg="accepted zeroconf from x"')
    assert not up._activity_line('Oct 07 12:59:53 p go-librespot[2326]: level=error msg="failed receiving dealer message"')
    assert up._activity_line("Oct 07 12:04:10 p bluealsa[893]: Adding new Stream End-Point")


def test_a_pack_downloads_capped_in_use_and_restarts_when_that_changes(up, monkeypatch):
    clock, playing = Clock(), [False]
    a = up.Activity(clock=clock, playing_now=lambda: playing[0], follow=False)
    calls = []

    def apt_progress(opts, *args, state, report_as, reporter=None, stop_when=None, **kw):
        calls.append(any("Dl-Limit" in o for o in opts))
        if len(calls) == 1:
            playing[0] = True          # a phone starts playing mid-download
            assert stop_when(), "the watcher sees it"
            return subprocess.CompletedProcess(args, up.INTERRUPTED, "", "")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(up, "apt_progress", apt_progress)
    r = up.pack_fetch(["-o", "Dir::State=x"], "gexis-skins-1920x1080", a)
    assert r.returncode == 0
    assert calls == [False, True], "full speed, then capped, resuming the same download"


def test_a_pack_that_ends_on_its_own_is_not_restarted(up, monkeypatch):
    a = up.Activity(clock=Clock(), playing_now=lambda: False, follow=False)
    n = []
    monkeypatch.setattr(up, "apt_progress",
                        lambda opts, *args, stop_when=None, **kw: n.append(1) or subprocess.CompletedProcess(args, 100, "", "E: x"))
    assert up.pack_fetch([], "gexis-skins-1920x1080", a).returncode == 100 and n == [1]


def test_a_player_that_does_not_answer_after_the_update_goes_back(up, monkeypatch):
    """ADR-0105 §4 step 6, built 2026-10-07: until then it was reported
    failed and left on the new release."""
    seen, order = fake_install(up, monkeypatch, answers=False)
    assert up.install(None) == 1
    last = seen[-1]
    assert last["state"] == "failed" and last["attempted"] == "2"
    assert "Back on 1" in last["message"] and last["steps"]["check"] == "failed"
    assert any(s["state"] == "going-back" for s in seen)
    assert order == ["backup", "stop", "restart", "restart"], "the old release's code restarted too"
    assert (up.STATE / "failed-testing").read_text() == "2"


def reboot_install(up, monkeypatch, *, answers=True):
    seen, order = fake_install(up, monkeypatch, answers=answers)
    ran = []
    monkeypatch.setattr(up, "restart", lambda changes: order.append("restart") or "reboot")
    monkeypatch.setattr(up, "run", lambda *a, **k: ran.append(a) or subprocess.CompletedProcess(a, 0, "", ""))
    return seen, order, ran


def test_an_update_that_reboots_is_checked_after_the_boot(up, monkeypatch):
    """ADR-0105 §4 step 5, built 2026-10-07: before, the check was ticked
    before rebooting and nothing looked afterwards."""
    seen, order, ran = reboot_install(up, monkeypatch)
    assert up.install(None) == 0
    assert seen[-1]["state"] == "restarting" and seen[-1]["steps"]["restart"] == "active"
    assert seen[-1]["steps"]["check"] == "pending", "not ticked before the boot"
    assert ("systemctl", "reboot") in ran and up.pending().exists()

    assert up.postboot(None) == 0
    assert seen[-1]["state"] == "done" and set(seen[-1]["steps"].values()) == {"done"}
    assert not up.pending().exists()
    assert up.postboot(None) == 0, "a boot with nothing to check does nothing"


def test_a_boot_that_does_not_answer_goes_back_once(up, monkeypatch):
    seen, order, ran = reboot_install(up, monkeypatch, answers=False)
    assert up.install(None) == 0
    ran.clear()
    assert up.postboot(None) == 1
    last = seen[-1]
    assert last["state"] == "failed" and "Back on 1" in last["message"]
    assert ("systemctl", "reboot") in ran, "what went back lands at a boot"
    assert not up.pending().exists(), "the boot after going back is not checked again"


AUDIT_BROKEN = ("The following packages are in a mess due to serious problems during\n"
                "installation.  They must be reinstalled for them (and any packages\n"
                "that depend on them) to function properly:\n"
                " gexis-skins-1480x320 (no description available)\n\n"
                "The following packages are missing the list control file in the\n"
                "database, they need to be reinstalled:\n"
                " gexis-skins-1480x320 (no description available)\n")


def _dpkg(monkeypatch, up, tmp_path, journal, audits, configure_rc=0):
    """A dpkg cut short: a journal file until `--configure -a` runs, and
    `dpkg --audit` answering from `audits` in turn. Every command recorded."""
    updates = tmp_path / "dpkg-updates"
    updates.mkdir()
    if journal:
        (updates / "0000").write_text("x")
    monkeypatch.setattr(up, "DPKG_UPDATES", updates)
    calls = []
    left = list(audits)

    def fake_run(*args, check=True, env=None):
        calls.append(list(args))
        if args[:2] == ("dpkg", "--audit"):
            out = left.pop(0) if left else ""
            return subprocess.CompletedProcess(args, 0, out, "")
        if args[:3] == ("dpkg", "--configure", "-a"):
            for f in updates.iterdir():
                f.unlink()
            return subprocess.CompletedProcess(args, configure_rc, "", "")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(up, "run", fake_run)
    applied = []
    monkeypatch.setattr(up, "apt", lambda opts, *a, prefix=None: applied.append(list(a))
                        or subprocess.CompletedProcess(a, 0, "", ""))
    (tmp_path / "updates").mkdir(exist_ok=True)
    return calls, applied


def test_a_clean_dpkg_is_left_alone(monkeypatch, up, tmp_path):
    calls, applied = _dpkg(monkeypatch, up, tmp_path, journal=False, audits=[""])
    up.heal(["-o", "x"])
    assert ["dpkg", "--configure", "-a"] not in calls and applied == []


def test_an_install_cut_short_is_finished_then_the_broken_package_reinstalled(monkeypatch, up, tmp_path):
    """ShelvesPi, 2026-10-08: a power cut mid-install; every apt run since
    refused with "dpkg was interrupted". The updater finishes it, and the
    pack that lost its file list is installed again."""
    calls, applied = _dpkg(monkeypatch, up, tmp_path, journal=True,
                           audits=[AUDIT_BROKEN, AUDIT_BROKEN, ""])
    up.heal(["-o", "x"])
    assert ["dpkg", "--configure", "-a"] in calls
    assert applied == [["--allow-change-held-packages", "install", "--reinstall", "gexis-skins-1480x320"]]
    assert "dpkg --configure -a" in (tmp_path / "updates" / "apt.log").read_text()


def test_configure_alone_can_be_enough(monkeypatch, up, tmp_path):
    calls, applied = _dpkg(monkeypatch, up, tmp_path, journal=True, audits=["", ""])
    up.heal(["-o", "x"])
    assert ["dpkg", "--configure", "-a"] in calls and applied == []


def test_a_pack_apt_cannot_reinstall_is_removed_for_a_fresh_install(monkeypatch, up, tmp_path):
    """ShelvesPi again, with the first version of this: the half-installed
    pack's exact version was in no repository, so apt could not reinstall
    it. A pack is removed, and the install that follows fetches it fresh."""
    calls, applied = _dpkg(monkeypatch, up, tmp_path, journal=True,
                           audits=[AUDIT_BROKEN, AUDIT_BROKEN, AUDIT_BROKEN, ""])
    up.heal(["-o", "x"])
    assert ["dpkg", "--remove", "--force-remove-reinstreq", "gexis-skins-1480x320"] in calls


def test_anything_else_that_cannot_be_finished_says_so(monkeypatch, up, tmp_path):
    """Never removes a package of the player itself."""
    core = AUDIT_BROKEN.replace("gexis-skins-1480x320", "gexis-core")
    calls, _ = _dpkg(monkeypatch, up, tmp_path, journal=True, audits=[core, core, core])
    with pytest.raises(up.Stop, match="cut short"):
        up.heal(["-o", "x"])
    assert not any(c[:2] == ["dpkg", "--remove"] for c in calls)


def test_empty_package_lists_are_dropped_before_an_update(up, tmp_path, monkeypatch):
    """ShelvesPi after its power cuts: every saved list at 0 bytes, kept by
    apt's "Hit" forever - no package could be found. They are thrown away so
    apt fetches them again; real lists and apt's lock stay."""
    lists = tmp_path / "updates" / "apt" / "ecd84854c1b3ae58" / "lists"
    lists.mkdir(parents=True)
    (lists / "x_skins-bbb_._Packages").write_text("")
    (lists / "x_skins-bbb_._InRelease").write_text("signed")
    (lists / "x_ours_._Packages").write_text("Package: gexis-core\n")
    (lists / "lock").write_text("")
    seen = []
    monkeypatch.setattr(up, "run", lambda *a, **k: seen.append(sorted(p.name for p in lists.iterdir()))
                        or subprocess.CompletedProcess(a, 0, "", ""))
    up.apt(["-o", "x"], "update")
    assert seen == [["lock", "x_ours_._Packages", "x_skins-bbb_._InRelease"]]
