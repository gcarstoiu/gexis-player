"""ADR-0126 decisions 5 and 6: accepted reports become a fourth state,
Reported, through a script and a reviewed commit."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from gexis_core import board_apply, boards, hardware_reports

TOOL = Path(__file__).parents[2] / "tools" / "hardware-reports.py"


@pytest.fixture
def tool():
    spec = importlib.util.spec_from_file_location("hardware_reports_tool", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def body(board, screen, sound="Yes", volume="Yes", clicks="No", picture="Yes", touch="Yes", gexis="0.9.4"):
    """An issue form's body as GitHub renders it."""
    return (f"### Sound card\n\n{board}\n\n### Screen\n\n{screen}\n\n"
            f"### Did the music sound right?\n\n{sound}\n\n"
            f"### Did the volume change with the slider?\n\n{volume}\n\n"
            f"### Any clicks or gaps between tracks?\n\n{clicks}\n\n"
            f"### Is the whole picture visible on the screen?\n\n{picture}\n\n"
            f"### Does a tap land where the finger is?\n\n{touch}\n\n"
            "### Anything else\n\n_No response_\n\n"
            f"### What the player read\n\n```text\nGexis {gexis}+git52.158e16c on a Raspberry Pi 4\n\nSound\n"
            "- card: sndrpihifiberry - HiFiBerry DAC+ Pro (Known)\n```\n")


SCREEN = 'Adafruit/10.1" HDMI IPS (1280x800)'


def issue(n, **kw):
    return {"number": n, "url": f"https://github.com/gcarstoiu/gexis-player/issues/{n}",
            "body": body(kw.pop("board", "HiFiBerry DAC+ Pro"), kw.pop("screen", SCREEN), **kw)}


def test_the_form_s_headings_map_to_its_fields(tool):
    labels = tool.form_labels()
    assert labels["Did the music sound right?"] == "sound" and labels["What the player read"] == "details"
    a = tool.answers(issue(1)["body"], labels)
    assert a["board"] == "HiFiBerry DAC+ Pro" and a["touch"] == "Yes" and "notes" not in a


def test_two_that_work_and_one_against(tool):
    data, skipped = tool.collect([issue(1), issue(2, gexis="0.9.5"), issue(3, clicks="Yes", touch="No")],
                                 tool.form_labels())
    assert skipped == []
    board = data["boards"]["hifiberry-dacpluspro"]
    assert (board["works"], board["problems"], board["version"]) == (2, 1, "0.9.5")
    assert board["problem_issues"] == ["https://github.com/gcarstoiu/gexis-player/issues/3"]
    assert data["screens"][SCREEN]["problems"] == 1, "a tap that misses is a screen problem"
    assert hardware_reports.state(board) == "Reported with problems"


def test_nothing_tried_is_no_report_and_an_unknown_screen_is_named(tool):
    data, skipped = tool.collect([issue(1, sound="Not tried", picture="No screen", touch="No touch",
                                        screen="Acme Wonder 9")], tool.form_labels())
    assert data == {"boards": {}, "screens": {}}
    assert skipped == ["#1: screen 'Acme Wonder 9' not on the list"]


def test_a_reported_board_shows_reported_and_tested_stays_ours(monkeypatch):
    data = {"boards": {"hifiberry-dacpluspro": {"works": 2, "problems": 0, "version": "0.9.4", "issues": []},
                       "iqaudio-pi-dac-pro": {"works": 0, "problems": 3, "issues": ["x"], "problem_issues": ["x"]}},
            "screens": {SCREEN: {"works": 1, "problems": 0, "version": "0.9.4", "issues": []}}}
    monkeypatch.setattr(hardware_reports, "_load", lambda: data)
    assert boards.identify("sndrpihifiberry", chosen="hifiberry-dacpluspro")[1] == "Reported"
    assert boards.identify("IQaudIODAC", product="Pi-DAC PRO")[1] == "Tested", "a report never takes Tested away"
    tags = board_apply.tags()
    assert tags[board_apply.label(boards.by_id("hifiberry-dacpluspro"))] == "Reported"
    assert hardware_reports.sentence(data["boards"]["hifiberry-dacpluspro"]) == \
        "Reported to work by 2 owners (0.9.4)."
    assert hardware_reports.sentence(data["screens"][SCREEN]) == "Reported to work by 1 owner (0.9.4)."
    from gexis_core.settings_registry import _screen_tags
    assert _screen_tags()[SCREEN] == "Reported"


def test_the_table_lists_every_board_and_screen(tool):
    text = tool.table({"boards": {"hifiberry-dacpluspro": {"works": 2, "problems": 0}}, "screens": {}})
    assert text.startswith(tool.BEGIN) and text.endswith(tool.END)
    assert "| HiFiBerry DAC+ Pro | Reported | 2 works |" in text
    assert "| IQaudIO Pi-DAC PRO | Tested |  |" in text
    assert text.count("\n| ") >= len(boards.all_boards()), "every board, reported or not"


def test_the_shipped_file_is_well_formed():
    data = json.loads(hardware_reports.PATH.read_text())
    assert set(data) == {"boards", "screens"}
