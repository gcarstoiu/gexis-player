# SPDX-License-Identifier: GPL-3.0-or-later
"""**What owners reported** (ADR-0126 decisions 5 and 6).

`hardware_reports.json` is written by `tools/hardware-reports.py` from the
GitHub *Hardware report* issues labelled `accepted`, and changes only in a
reviewed commit: a report never reaches a device by itself, so a wrong one
cannot reach anyone unreviewed.

**A fourth state, *Reported*** (amends ADR-0117, and ADR-0109 for screens):
a board or screen that is not *Tested*, with at least one accepted report
that it works and none against. One against makes it *Reported with
problems*, with the issue linked. *Tested* is never given by a report - it
stays ours alone, played and measured here.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

PATH = Path(__file__).with_name("hardware_reports.json")

REPORTED = "Reported"
REPORTED_WITH_PROBLEMS = "Reported with problems"


@lru_cache(maxsize=1)
def _load(path: Path = PATH) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {"boards": {}, "screens": {}}
    return {"boards": data.get("boards") or {}, "screens": data.get("screens") or {}}


def board(key: str | None) -> dict | None:
    """By board id, or by ALSA card for a card no listed board makes."""
    return _load()["boards"].get(key) if key else None


def screen(label: str | None) -> dict | None:
    return _load()["screens"].get(label) if label else None


def state(entry: dict | None) -> str | None:
    if not entry:
        return None
    if entry.get("problems"):
        return REPORTED_WITH_PROBLEMS
    if entry.get("works"):
        return REPORTED
    return None


def sentence(entry: dict | None) -> str | None:
    """*"Reported to work by 2 owners (0.9.3)"*, or the problem, linked."""
    found = state(entry)
    if found == REPORTED_WITH_PROBLEMS:
        issues = entry.get("problem_issues") or entry.get("issues") or []
        return "Reported with problems" + (f": {issues[0]}" if issues else ".")
    if found == REPORTED:
        n = entry["works"]
        version = f" ({entry['version']})" if entry.get("version") else ""
        return f"Reported to work by {n} owner{'s' if n != 1 else ''}{version}."
    return None
