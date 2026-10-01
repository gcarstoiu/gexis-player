"""ADR-0105 §4, ADR-0108: the updater's own judgement, without a device."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import io
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
    def dl(opts, *a, report_as, reporter=None):
        up.PROGRESS["progress"] = 0.5
        reporter("downloading", **report_as)
        calls.append(("download",) + a)
        return subprocess.CompletedProcess(a, 0, "", "")
    monkeypatch.setattr(up, "apt_download", dl)
    up.STATE.mkdir(parents=True, exist_ok=True)
    assert up.pack_install("gexis-skins-1920x1080") == 0
    assert calls[0] == ("env", ["ours-a", "skins-b"], ["ours-a", "skins-b"])
    assert ("download", "--download-only", "install", "gexis-skins-1920x1080") in calls
    assert ("apt", "--no-download", "install", "gexis-skins-1920x1080") in calls
    doc = json.loads((up.STATE / "pack.json").read_text())
    assert doc["state"] == "installed" and doc["package"] == "gexis-skins-1920x1080"
    assert not (up.STATE / "status.json").exists(), "a pack never writes the update's status"
