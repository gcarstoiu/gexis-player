# SPDX-License-Identifier: GPL-3.0-or-later
"""The Legal and Credits pages (ADR-0099).

**One source of truth.** `notices.json`, beside this module, lists every
third-party component the player ships, fetches, installs on request or was
reimplemented from, with its author, licence, link and how it arrives. Both
pages are built from it, so a component credited on one is accounted for on
the other, and the build checks that everything the image installs has an
entry (`core/tests/test_notices.py`).

The prose around the list - the warranty, the unofficial-software notice, the
trademarks - is in the same file, as George approves it.
"""
from __future__ import annotations

import json
from pathlib import Path

NOTICES_PATH = Path(__file__).with_name("notices.json")
DOCUMENTS = ("legal", "credits")


def load(path: Path = NOTICES_PATH) -> dict:
    return json.loads(path.read_text())


def document(name: str, path: Path = NOTICES_PATH) -> dict | None:
    """A page, as the panel draws it: a title, then sections of paragraphs
    and entries. None for a document that does not exist."""
    if name not in DOCUMENTS:
        return None
    data = load(path)
    page = data["documents"][name]
    components = data["components"]
    sections = []
    for section in page["sections"]:
        out = {"heading": section.get("heading"), "paragraphs": list(section.get("paragraphs", []))}
        wanted = section.get("components")
        if wanted is not None:
            out["entries"] = [
                {key: c.get(key) for key in ("name", "role", "author", "licence", "url", "arrives")}
                for c in components
                if c.get("group") in wanted and (name == "legal" or c.get("credit", True))
            ]
        sections.append(out)
    return {"title": page["title"], "updated": data.get("updated"), "sections": sections}


def third_party_markdown(path: Path = NOTICES_PATH) -> str:
    """`THIRD-PARTY.md` at the repository's root, from the same file."""
    data = load(path)
    lines = [
        "# Third-party components",
        "",
        "Generated from `core/src/gexis_core/notices.json` by",
        "`python -m gexis_core.notices` - edit that file, not this one. The same",
        "list is on the player, under Settings → System → Legal and Credits.",
        "",
        "| Component | What it does | Licence | Author | How it arrives |",
        "|---|---|---|---|---|",
    ]
    for c in data["components"]:
        cells = [f"[{c['name']}]({c['url']})", c.get("role", ""), c["licence"], c.get("author", ""),
                 c.get("arrives", "")]
        lines.append("| " + " | ".join(str(x).replace("|", "\\|") for x in cells) + " |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("THIRD-PARTY.md")
    target.write_text(third_party_markdown())
    print(f"wrote {target}")
