# SPDX-License-Identifier: GPL-3.0-or-later
"""Now Playing's lines from what a station sends (ADR-0180 item 4)."""
from __future__ import annotations

import pytest

from gexis_core.radio_lines import from_metadata, split_title


@pytest.mark.parametrize("line, expected", [
    ("Artist - Title", ("Artist", "Title")),
    ("A - B - C", ("A", "B - C")),                 # the first " - " only
    ("  Artist   -   Title ", ("Artist", "Title")),
    ("Morning Show with Somebody", (None, "Morning Show with Somebody")),
    ("Artist -", (None, "Artist -")),               # one half: the whole line
    ("- Title", (None, "- Title")),
    ("Artist-Title", (None, "Artist-Title")),       # no spaces: not the separator
    ("", (None, None)),
    ("   ", (None, None)),
    (" - ", (None, None)),
    (None, (None, None)),
])
def test_split_title(line, expected):
    assert split_title(line) == expected


def test_a_line_that_repeats_the_stations_name_is_nothing_sent():
    assert split_title("Example FM", "Example  FM") == (None, None)
    assert split_title("EXAMPLE fm", "Example FM") == (None, None)
    assert split_title("Example FM - Live", "Example FM") == ("Example FM", "Live")


def test_from_metadata_prefers_icy_title():
    assert from_metadata({"icy-title": "A - B", "title": "x", "artist": "y"}) == ("A", "B")
    assert from_metadata({"icy-name": "Station", "icy-title": ""}) == (None, None)


def test_from_metadata_takes_ogg_tags():
    assert from_metadata({"ARTIST": "Band", "TITLE": "Song"}) == ("Band", "Song")
    assert from_metadata({"title": "Only a title"}) == (None, "Only a title")
    assert from_metadata({"title": "Station", "artist": "x"}, "Station") == (None, None)
    assert from_metadata({"icy-name": "Station"}) == (None, None)
    assert from_metadata(None) == (None, None)
