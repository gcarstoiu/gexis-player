"""Every library row that reveals actions says so (Finding 125 #24).

The panel pointer outlines a row unless its actions are revealed, and since
2026-10-14 it knows a reveal only by a marker the screen puts on the row:
`is-revealed`. A row that reveals actions without the marker is outlined
over its own actions - the bar's rows were, after the pointer changed and
the bar's screen did not. This reads the sources: there is no UI test
harness, and the rule is one of markup, not behaviour.
"""
import re
from pathlib import Path

import pytest

UI = Path(__file__).parents[2] / "ui" / "src" / "screens"
SCREENS = [UI / "Library.svelte", UI / "bar" / "BarLibrary.svelte"]
REVEAL = re.compile(r"\{#if revealed === (`[^`]+`)\}")


@pytest.mark.parametrize("screen", SCREENS, ids=lambda p: p.name)
def test_each_reveal_is_marked_on_its_row(screen):
    source = screen.read_text()
    keys = REVEAL.findall(source)
    assert keys, "found the reveals, not nothing"
    unmarked = [k for k in keys if f"class:is-revealed={{revealed === {k}}}" not in source]
    assert not unmarked, f"{screen.name}: rows reveal actions without is-revealed: {unmarked}"
