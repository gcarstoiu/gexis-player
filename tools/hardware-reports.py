#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""**From owners' reports to the player, by a reviewed change** (ADR-0126
decision 6).

Reads the GitHub *Hardware report* issues labelled `accepted`, and writes

- `core/src/gexis_core/hardware_reports.json` - per board and per screen, how
  many accepted reports say it works, how many report a problem, the newest
  Gexis version reported and the issues; the player's *Reported* state and
  the rows' sentences come from it (`hardware_reports.py`);
- the table between the markers in `docs/HARDWARE.md`: every board and screen
  the player lists, its state, and the number of reports.

Nothing is committed: the change is read, reviewed and committed like any
other, and reaches devices with the next release. A report alone never
changes a device.

    tools/hardware-reports.py            # from GitHub (gh, authenticated)
    tools/hardware-reports.py --issues issues.json   # from a saved list

Run from the repository root.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core" / "src"))

from gexis_core import boards, hardware_reports, screens  # noqa: E402

TEMPLATE = ROOT / ".github" / "ISSUE_TEMPLATE" / "hardware-report.yml"
HARDWARE_MD = ROOT / "docs" / "HARDWARE.md"
BEGIN = "<!-- hardware-reports:begin (tools/hardware-reports.py writes this table) -->"
END = "<!-- hardware-reports:end -->"


def form_labels(path: Path = TEMPLATE) -> dict[str, str]:
    """The form's field ids by the heading GitHub gives each answer."""
    text = path.read_text()
    labels = {}
    for block in re.split(r"\n\s*- type:", text):
        ident = re.search(r"\n\s*id:\s*(\S+)", block)
        label = re.search(r"\n\s*label:\s*(.+)", block)
        if ident and label:
            labels[label.group(1).strip().strip('"')] = ident.group(1).strip()
    return labels


def answers(body: str, labels: dict[str, str]) -> dict[str, str]:
    """An issue form's body is `### <label>` then the answer; `_No response_`
    is no answer."""
    out = {}
    for heading, value in re.findall(r"^### (.+?)\n+(.*?)(?=^### |\Z)", body or "", re.S | re.M):
        field = labels.get(heading.strip())
        value = value.strip()
        if field and value and value != "_No response_":
            out[field] = value
    return out


def version(details: str) -> str | None:
    m = re.search(r"Gexis (\S+) on a", details or "")
    return m.group(1).split("+")[0] if m else None


def board_key(name: str) -> str | None:
    """The board's id by its name as the report gives it; for a card no
    listed board makes, the card itself ("- card: <card>" in the details)."""
    for board in boards.all_boards():
        if board.name == name:
            return board.id
    return None


def screen_key(value: str) -> str | None:
    model = screens.by_label(value)
    if model is None:
        model = next((s for s in screens.all_screens()
                      if f"{s.maker} {s.model}" == value or s.model == value), None)
    return model.label if model else None


def verdict(a: dict[str, str], kind: str) -> str | None:
    """`works`, `problem`, or None when nothing was tried."""
    if kind == "board":
        if "No" in (a.get("sound"), a.get("volume")) or a.get("clicks") == "Yes":
            return "problem"
        return "works" if a.get("sound") == "Yes" else None
    if "No" in (a.get("picture"), a.get("touch")):
        return "problem"
    return "works" if a.get("picture") == "Yes" else None


def _add(table: dict, key: str, how: str, issue: dict, gexis: str | None) -> None:
    entry = table.setdefault(key, {"works": 0, "problems": 0, "version": None,
                                   "issues": [], "problem_issues": []})
    if how == "works":
        entry["works"] += 1
    else:
        entry["problems"] += 1
        entry["problem_issues"].append(issue["url"])
    entry["issues"].append(issue["url"])
    if gexis and (entry["version"] is None or _newer(gexis, entry["version"])):
        entry["version"] = gexis


def _newer(a: str, b: str) -> bool:
    def key(v):
        return tuple(int(x) for x in re.findall(r"\d+", v))
    return key(a) > key(b)


def collect(issues: list[dict], labels: dict[str, str]) -> tuple[dict, list[str]]:
    data, skipped = {"boards": {}, "screens": {}}, []
    for issue in sorted(issues, key=lambda i: i["number"]):
        a = answers(issue.get("body", ""), labels)
        gexis = version(a.get("details", ""))
        board = a.get("board")
        if board and board != "no sound card":
            key = board_key(board)
            if key is None:
                card = re.search(r"- card: (\S+)", a.get("details", ""))
                key = card.group(1) if card else None
            how = verdict(a, "board")
            if key and how:
                _add(data["boards"], key, how, issue, gexis)
            elif not key:
                skipped.append(f"#{issue['number']}: board {board!r} not on the list")
        screen = a.get("screen")
        if screen and screen != "none":
            key = screen_key(screen)
            how = verdict(a, "screen")
            if key and how:
                _add(data["screens"], key, how, issue, gexis)
            elif not key:
                # ADR-0126 decision 7 - a screen not yet recognised - is a
                # change to the screen list, made by hand from the report.
                skipped.append(f"#{issue['number']}: screen {screen!r} not on the list")
    return data, skipped


def table(data: dict) -> str:
    def count(entry):
        if not entry:
            return ""
        parts = [f"{entry['works']} works"] if entry["works"] else []
        if entry["problems"]:
            parts.append(f"{entry['problems']} with problems")
        return ", ".join(parts)

    lines = [BEGIN, "", "| Sound card | State | Reports |", "|---|---|---|"]
    for board in sorted(boards.all_boards(), key=lambda b: b.name.lower()):
        entry = data["boards"].get(board.id)
        state = "Tested" if board.tested else hardware_reports.state(entry) or "Known"
        lines.append(f"| {board.name} | {state} | {count(entry)} |")
    lines += ["", "| Screen | State | Reports |", "|---|---|---|"]
    for model in sorted(screens.all_screens(), key=lambda s: s.label.lower()):
        entry = data["screens"].get(model.label)
        state = "Tested" if model.tested else hardware_reports.state(entry) or "Untested"
        lines.append(f"| {model.maker} {model.model} | {state} | {count(entry)} |")
    lines += ["", END]
    return "\n".join(lines)


def fetch() -> list[dict]:
    out = subprocess.run(
        ["gh", "issue", "list", "--state", "all", "--limit", "1000",
         "--label", "hardware report", "--label", "accepted",
         "--json", "number,url,body,title"],
        capture_output=True, text=True, check=True, cwd=ROOT).stdout
    return json.loads(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--issues", type=Path, help="a saved `gh issue list --json number,url,body` list")
    args = parser.parse_args(argv)
    issues = json.loads(args.issues.read_text()) if args.issues else fetch()
    data, skipped = collect(issues, form_labels())
    hardware_reports.PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    text = HARDWARE_MD.read_text()
    if BEGIN in text and END in text:
        head, rest = text.split(BEGIN, 1)
        text = head + table(data) + rest.split(END, 1)[1]
    else:
        text = text.rstrip("\n") + "\n\n## Reported by owners\n\n" + table(data) + "\n"
    HARDWARE_MD.write_text(text)
    print(f"{len(issues)} accepted reports: {len(data['boards'])} boards, {len(data['screens'])} screens")
    for line in skipped:
        print("skipped", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
