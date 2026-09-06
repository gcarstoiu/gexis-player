"""Unit tests for /proc/asound/cards parsing.

Regression coverage for a bug found on hardware, 2026-09-06: the id field
is padded to a fixed 15 characters, and "sndrpihifiberry" is exactly 15
characters - no padding, so a \\S+-based match runs past the closing
bracket. The old fixture apparently only ever covered the padded case.
This one covers both, in the same file, so that can't happen again.
"""
from __future__ import annotations

from pathlib import Path

import pytest

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
