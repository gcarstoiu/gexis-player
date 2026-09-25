# SPDX-License-Identifier: GPL-3.0-or-later
"""Every relative link in the records lands somewhere.

**`docs/decisions/README.md` is the index the whole project navigates by** -
CLAUDE.md says to read it rather than the 81 records behind it - so a link in
it that 404s costs exactly where the index is meant to save.

Twenty-four of them did not land, found on 2026-09-25 when George asked what
the broken links in the index were. Every one was the same mistake: the link
was written from the record's **title** rather than its **filename**, from
memory, because the two are close enough to feel interchangeable.
`0009-alsa-device-indirection.md` for `0009-logical-output-device.md`,
`0012-enrichment-service.md` for `0012-enrichment-additive-only.md`. The
number was always right, so the text stayed true and only the navigation
broke - which is why nothing noticed for months.

A generated check, like `test_registry_wiring.py`: the machine knows what the
files are called and nobody has to.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s#]+)(?:#[^)]*)?\)")

#: **Verbatim by decision, and broken by the same decision.**
#: `docs/HANDOFF-ARCHIVE.md` carries blocks moved out of `HANDOFF.md`
#: unedited - its own header says so, "so a `git log -p` trail still matches".
#: Those blocks were written at the repository root, where `docs/decisions/x`
#: is the right path; from inside `docs/` it is not. **74 links, all of that
#: one kind.** Rewriting them would edit what the file promises never to
#: edit, so this check does not ask.
VERBATIM = {"HANDOFF-ARCHIVE.md"}


def _markdown() -> list[Path]:
    out = [p for p in (REPO / "docs").rglob("*.md") if p.name not in VERBATIM]
    out += [REPO / "CLAUDE.md", REPO / "HANDOFF.md"]
    return [p for p in out if p.exists()]


def test_the_sweep_finds_files_at_all():
    """Otherwise the test below passes by checking nothing."""
    files = _markdown()
    assert len(files) > 80
    assert any(f.name == "README.md" and f.parent.name == "decisions" for f in files)


def test_every_relative_link_in_the_records_lands():
    broken = []
    for f in _markdown():
        for match in LINK.finditer(f.read_text()):
            target = match.group(1)
            if "://" in target or target.startswith("mailto:"):
                continue
            if not (f.parent / target).resolve().exists():
                broken.append(f"{f.relative_to(REPO)} -> {target}")
    assert not broken, "links that do not land:\n  " + "\n  ".join(broken)


def test_the_archive_is_excluded_for_a_reason_that_still_holds():
    """If the archive ever stops declaring itself verbatim, its 74 links stop
    being a consequence of that promise and become ordinary rot."""
    archive = REPO / "docs" / "HANDOFF-ARCHIVE.md"
    assert "**Nothing here was edited.**" in archive.read_text()
