"""Unit tests for /proc/asound/cards parsing.

Regression coverage for a bug found on hardware, 2026-09-06: the id field
is padded to a fixed 15 characters, and "sndrpihifiberry" is exactly 15
characters - no padding, so a \\S+-based match runs past the closing
bracket. The old fixture apparently only ever covered the padded case.
This one covers both, in the same file, so that can't happen again.
"""
from __future__ import annotations

import subprocess
import os
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
    # No cgroup file, so these take the `fuser` path whatever host runs them.
    monkeypatch.setattr(alsa, "CGROUP_ROOT", tmp_path / "no-cgroup")
    return node


def _cgroup(root: Path, unit: str, *pids: int) -> None:
    procs = root / "system.slice" / unit / "cgroup.procs"
    procs.parent.mkdir(parents=True)
    procs.write_text("".join(f"{p}\n" for p in pids))


def test_the_units_own_descriptors_answer_without_fuser(pcm_node, tmp_path, monkeypatch):
    """**2026-09-26: `fuser` cost 0.10 s and lost a takeover.** go-librespot
    opens the device as little as 0.26 s after announcing it; the ladder asked
    `fuser` before it escalated. The unit's own descriptors answer the same
    question in about a millisecond, and nothing is run."""
    monkeypatch.setattr(alsa, "CGROUP_ROOT", tmp_path / "cg")
    _cgroup(tmp_path / "cg", "plexamp.service", os.getpid())

    def run(cmd, **kw):
        raise AssertionError(f"ran {cmd!r}")

    monkeypatch.setattr(subprocess, "run", run)
    with open(pcm_node):
        assert alsa.device_held_by("plexamp.service") is True
    assert alsa.device_held_by("plexamp.service") is False


def test_a_template_instance_is_found_in_its_own_slice(pcm_node, tmp_path, monkeypatch):
    """Found 2026-09-30: an uploaded renderer's receiver held the card, the
    core looked in `system.slice/<unit>` - which does not exist for a template
    instance - and asked the launcher script instead. Spotify then found the
    card busy."""
    unit = "gexis-uploaded-renderer@radiofoo.service"
    assert alsa.unit_cgroup(unit) == (
        "system.slice/system-gexis\\x2duploaded\\x2drenderer.slice/" + unit)
    procs = tmp_path / "cg" / alsa.unit_cgroup(unit) / "cgroup.procs"
    procs.parent.mkdir(parents=True)
    procs.write_text(f"{os.getpid()}\n")
    monkeypatch.setattr(alsa, "CGROUP_ROOT", tmp_path / "cg")
    with open(pcm_node):
        assert alsa.device_held_by(unit) is True
    assert alsa.device_held_by(unit) is False


def test_a_running_unit_whose_cgroup_is_missing_is_said_once(pcm_node, tmp_path, monkeypatch, caplog):
    """LESSONS 47: the fallback answered "free" for two days without a word."""
    (tmp_path / "cg").mkdir()
    monkeypatch.setattr(alsa, "CGROUP_ROOT", tmp_path / "cg")
    monkeypatch.setattr(alsa, "_unfound", set())
    monkeypatch.setattr(alsa, "_unit_main_pid", lambda unit: 4242)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a, 0, "", ""))
    with caplog.at_level("WARNING", logger="gexis_core.alsa"):
        assert alsa.device_held_by("somewhere-else.service") is False
        assert alsa.device_held_by("somewhere-else.service") is False
    warned = [r for r in caplog.records if "no cgroup for running" in r.getMessage()]
    assert len(warned) == 1, "once per unit, not per poll"


def test_a_stopped_unit_is_not_warned_about(pcm_node, tmp_path, monkeypatch, caplog):
    (tmp_path / "cg").mkdir()
    monkeypatch.setattr(alsa, "CGROUP_ROOT", tmp_path / "cg")
    monkeypatch.setattr(alsa, "_unfound", set())
    monkeypatch.setattr(alsa, "_unit_main_pid", lambda unit: None)
    with caplog.at_level("WARNING", logger="gexis_core.alsa"):
        assert alsa.device_held_by("stopped.service") is False
    assert not caplog.records


def test_another_units_hold_is_not_this_ones(pcm_node, tmp_path, monkeypatch):
    """Same question as the `fuser` test below: the incoming renderer may
    already hold the device while the outgoing one's ladder is checking."""
    monkeypatch.setattr(alsa, "CGROUP_ROOT", tmp_path / "cg")
    _cgroup(tmp_path / "cg", "plexamp.service")  # empty: its process is gone
    with open(pcm_node):
        assert alsa.device_held_by("plexamp.service") is False


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


class TestArbitrationFollowsTheOutput:
    """**George, 2026-09-23: *"Any output holding the device follows the
    same arbitration as the DAC. Needs to be fixed."***

    Measured before the fix (Finding 048 §5): with the output on the
    headphone jack and something holding it, `device_busy()` answered
    `False`, because every function here defaulted to the card the device
    shipped with. The release ladder would have read "already released" the
    instant a polite stop was sent.
    """

    def setup_method(self):
        alsa.set_card(alsa.CARD_ID)

    def teardown_method(self):
        alsa.set_card(alsa.CARD_ID)

    def test_it_starts_on_the_card_the_device_ships_with(self):
        assert alsa.card() == alsa.CARD_ID

    def test_the_default_follows_the_chosen_output(self, tmp_path):
        cards = tmp_path / "cards"
        cards.write_text(
            " 4 [Headphones     ]: bcm2835_headpho - bcm2835 Headphones\n"
            " 5 [sndrpihifiberry]: HifiberryDacplu - snd_rpi_hifiberry_dacplushd\n"
        )
        assert alsa.resolve_card_number(cards_file=cards) == 5

        alsa.set_card("Headphones")

        assert alsa.resolve_card_number(cards_file=cards) == 4

    def test_an_explicit_card_still_wins(self, tmp_path):
        """The functions keep their argument, so a caller that genuinely
        means one card can still say so."""
        cards = tmp_path / "cards"
        cards.write_text(
            " 4 [Headphones     ]: bcm2835_headpho - bcm2835 Headphones\n"
            " 5 [sndrpihifiberry]: HifiberryDacplu - snd_rpi_hifiberry_dacplushd\n"
        )
        alsa.set_card("Headphones")

        assert alsa.resolve_card_number("sndrpihifiberry", cards_file=cards) == 5

    def test_an_empty_card_is_ignored_rather_than_believed(self):
        """A discovery that came back with nothing must not point
        arbitration at a card called ''."""
        alsa.set_card("")
        assert alsa.card() == alsa.CARD_ID
