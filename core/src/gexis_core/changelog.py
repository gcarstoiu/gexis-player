# SPDX-License-Identifier: GPL-3.0-or-later
"""**Change logs** (ADR-0116; George, 2026-10-03: *"another tile in settings
called change logs which displays the last 10. If user wants more he is
pointed to the git page where we have them all"*).

Every release's notes, exactly as approved, signed and published, are in
`release_notes.json` beside this file - the same file `publish.sh` publishes
them from. The page is drawn like Legal and Credits: a section per release.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

NOTES = Path(__file__).with_name("release_notes.json")
SHOWN = 10
#: ADR-0116, not settled: where the older ones are.
OLDER = "https://github.com/gcarstoiu/gexis-player/releases"


def _key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _day(text: str) -> str:
    d = date.fromisoformat(text)
    return f"{d.day} {d.strftime('%B')} {d.year}"


def releases(path: Path = NOTES) -> list[tuple[str, dict]]:
    """(version, {date, notes}), newest first."""
    data = json.loads(path.read_text())["releases"]
    return sorted(data.items(), key=lambda item: _key(item[0]), reverse=True)


def page(path: Path = NOTES, shown: int = SHOWN) -> dict:
    """The page, as the panel draws a document."""
    every = releases(path)
    sections = [{"heading": f"{version} · {_day(entry['date'])}", "paragraphs": [], "notes": entry["notes"]}
                for version, entry in every[:shown]]
    sections.append({"heading": "Older releases", "paragraphs": [
        f"The last {min(shown, len(every))} releases are here. Every release and its notes are on GitHub:"],
        "url": OLDER})
    return {"title": "Change logs", "updated": None, "sections": sections}
