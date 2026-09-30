"""ADR-0105 §4, ADR-0108: the updater's own judgement, without a device."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import io
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
    installs = []
    monkeypatch.setattr(up, "install", lambda args: installs.append(1) or 0)
    monkeypatch.setattr(up, "check", lambda args: ("testing", {"Release": "2", "_serial": 2}))
    up.scheduled(None)
    assert installs == [], "the failed release is not retried by itself"
    monkeypatch.setattr(up, "check", lambda args: ("testing", {"Release": "3", "_serial": 3}))
    up.scheduled(None)
    assert installs == [1], "a newer release is"
