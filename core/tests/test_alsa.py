"""Unit tests for /proc/asound/cards parsing.

Regression coverage for a bug found on hardware, 2026-09-06: the id field
is padded to a fixed 15 characters, and "sndrpihifiberry" is exactly 15
characters - no padding, so a \\S+-based match runs past the closing
bracket. The old fixture apparently only ever covered the padded case.
This one covers both, in the same file, so that can't happen again.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from gexis_core import alsa
from gexis_core.alsa import resolve_card_number

# Real /proc/asound/cards shape: an 8-char id ("vc4hdmi0") padded with
# trailing spaces to fill the 15-char bracketed field, and a 15-char id
# ("sndrpihifiberry") that exactly fills it with none to spare.
CARDS_FIXTURE = """\
 0 [vc4hdmi0       ]: vc4-hdmi - vc4-hdmi-0
                      vc4-hdmi-0
 1 [sndrpihifiberry]: sndrpihifiberry - snd_rpi_hifiberry_dacplushd
                      snd_rpi_hifiberry_dacplushd
"""


@pytest.fixture
def cards_file(tmp_path: Path) -> Path:
    path = tmp_path / "cards"
    path.write_text(CARDS_FIXTURE)
    return path


def test_resolves_a_padded_short_id(cards_file):
    assert resolve_card_number("vc4hdmi0", cards_file) == 0


def test_resolves_an_id_that_exactly_fills_the_field(cards_file):
    assert resolve_card_number("sndrpihifiberry", cards_file) == 1


def test_unknown_id_raises(cards_file):
    with pytest.raises(RuntimeError, match="not found"):
        resolve_card_number("doesnotexist", cards_file)


# Regression coverage for a bug found on hardware, 2026-09-08: the release
# ladder's old `device_busy()` asked "is anyone holding the PCM", which
# reports True once the *incoming* renderer has already opened it, even
# though the *outgoing* one released cleanly - see arbitration.py's
# `_busy` docstring. `device_held_by(unit)` asks specifically whether that
# unit's own PID is among the holders.


@pytest.fixture
def pcm_node(tmp_path: Path, monkeypatch) -> Path:
    node = tmp_path / "pcmC1D0p"
    node.touch()
    monkeypatch.setattr(alsa, "playback_pcm_node", lambda card_id=alsa.CARD_ID: node)
    return node


def test_device_held_by_true_when_units_own_pid_is_a_holder(pcm_node, monkeypatch):
    def run(cmd, **kw):
        if cmd[:2] == ["systemctl", "show"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="884", stderr="")
        if cmd[0] == "fuser":
            return subprocess.CompletedProcess(cmd, 0, stdout="884\n", stderr="")
        raise AssertionError(f"unexpected command {cmd!r}")

    monkeypatch.setattr(subprocess, "run", run)
    assert alsa.device_held_by("go-librespot.service") is True


def test_device_held_by_false_when_a_different_pid_holds_it(pcm_node, monkeypatch):
    """The exact hardware scenario: go-librespot (pid 884) released, but
    squeezelite (pid 892, the incoming renderer) already holds the PCM by
    the time this check runs. Must read as "go-librespot released", not
    "still busy"."""

    def run(cmd, **kw):
        if cmd[:2] == ["systemctl", "show"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="884", stderr="")
        if cmd[0] == "fuser":
            return subprocess.CompletedProcess(cmd, 0, stdout="892\n", stderr="")
        raise AssertionError(f"unexpected command {cmd!r}")

    monkeypatch.setattr(subprocess, "run", run)
    assert alsa.device_held_by("go-librespot.service") is False


def test_device_held_by_false_when_unit_has_no_main_pid(pcm_node, monkeypatch):
    def run(cmd, **kw):
        if cmd[:2] == ["systemctl", "show"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="0", stderr="")
        raise AssertionError(f"unexpected command {cmd!r}")

    monkeypatch.setattr(subprocess, "run", run)
    assert alsa.device_held_by("go-librespot.service") is False


def test_device_held_by_false_when_node_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        alsa, "playback_pcm_node", lambda card_id=alsa.CARD_ID: tmp_path / "nope"
    )
    assert alsa.device_held_by("go-librespot.service") is False
