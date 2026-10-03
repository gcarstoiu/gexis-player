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
#: ADR-0116 decision 7 (George, 2026-10-03: *"B"*): every release's notes in
#: CHANGELOG.md, generated from the same file, on `main` - which each release
#: is merged into.
OLDER = "https://github.com/gcarstoiu/gexis-player/blob/main/CHANGELOG.md"


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
        f"The last {min(shown, len(every))} releases are here. Every release's notes are on GitHub:"],
        "url": OLDER})
    return {"title": "Change logs", "updated": None, "sections": sections}


def markdown(path: Path = NOTES) -> str:
    """`CHANGELOG.md` at the repository's root, from the same file."""
    lines = ["# Changelog", "",
             "Every release of Gexis Player and its notes, newest first. Generated from",
             "`core/src/gexis_core/release_notes.json` by `python -m gexis_core.changelog` -",
             "edit that file, not this one. The player shows the last 10 under",
             "Settings → System → Change logs.", ""]
    for version, entry in releases(path):
        lines += [f"## {version} — {_day(entry['date'])}", ""]
        for line in entry["notes"].splitlines():
            if line in ("New", "Fixed", "Good to know"):
                if lines[-1] != "":
                    lines.append("")
                lines += [f"### {line}", ""]
            elif line.startswith("• "):
                lines.append("- " + line[2:])
            elif line.strip():
                lines += [line, ""]
        if lines[-1] != "":
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


if __name__ == "__main__":
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("CHANGELOG.md")
    target.write_text(markdown())
    print(f"wrote {target}")
