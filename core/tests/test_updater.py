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


def test_apt_sees_only_the_release_and_prefers_it_when_going_back(up):
    opts = up.apt_env(["r1"], pin_tag="r1")
    sources = (up.STATE / "apt" / "sources.list").read_text()
    assert sources.count("deb [signed-by=") == 2 and "/r1/ ./" in sources and "/r1-debian/ ./" in sources
    assert "Dir::Etc::sourceparts=-" in opts, "the device's own sources are not read"
    assert "Pin-Priority: 1001" in (up.STATE / "apt" / "preferences").read_text()


def test_stable_is_the_channel_when_nothing_was_chosen(up, tmp_path, monkeypatch):
    monkeypatch.setattr(up, "SETTINGS_DB", tmp_path / "missing.db")
    assert up.channel_name(None) == "stable"
