"""ADR-0099: everything the image installs is accounted for on the Legal and
Credits pages - the check that keeps them from drifting."""
from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest

from gexis_core import notices

ROOT = Path(__file__).parents[2]
STAGES = ROOT / "image" / "stage-gexis"
GROUPS = {"system", "renderer", "visualiser", "ui", "core", "build", "skins", "fonts", "marks",
          "downloaded", "user-installed", "services"}


@pytest.fixture(scope="module")
def data():
    return notices.load()


def test_every_component_says_what_it_is(data):
    for c in data["components"]:
        for field in ("name", "licence", "url", "arrives", "group"):
            assert c.get(field), f"{c.get('name')!r} has no {field}"
        assert c["group"] in GROUPS, f"{c['name']}: unknown group {c['group']!r}"


def test_every_fetch_in_the_build_is_accounted_for(data):
    """A URL a stage downloads from is matched by a component's `sources`."""
    urls = set()
    # The stages' own downloads, and what a user's switch fetches on the
    # device (ADR-0100) - both are ours to account for.
    for script in [*STAGES.glob("*/0*-run*.sh"), *STAGES.glob("*/files/components/*.env")]:
        urls |= set(re.findall(r"https://[^\"' \n]+", script.read_text()))
    assert urls, "the stages fetch something"
    missing = sorted(u for u in urls if not any(
        s in u for c in data["components"] for s in c.get("sources", [])))
    assert not missing, f"fetched but not in notices.json: {missing}"


def test_every_package_the_stages_install_is_accounted_for(data):
    packages = set()
    for listing in STAGES.glob("*/00-packages*"):
        packages |= {p for line in listing.read_text().splitlines()
                     if not line.strip().startswith("#") for p in line.split()}
    listed = {p for c in data["components"] for p in c.get("packages", [])}
    assert not sorted(packages - listed), f"installed but not in notices.json: {sorted(packages - listed)}"


def test_every_runtime_dependency_is_accounted_for(data):
    listed = {p for c in data["components"] for p in c.get("packages", [])}
    # The panel's build has no runtime dependencies in name: everything is a
    # devDependency. What is bundled into it is what `ui/scripts/licenses.mjs`
    # ships a licence for, so that list is read here rather than kept twice -
    # a hand-kept filter here once admitted only Svelte and the fonts, and a
    # new bundled library would have passed with no entry.
    script = (ROOT / "ui" / "scripts" / "licenses.mjs").read_text()
    bundled = re.search(r"const BUNDLED = \[([^\]]*)\]", script)
    assert bundled, "the bundled list was not found in licenses.mjs"
    ui = set(re.findall(r"'([^']+)'", bundled.group(1))) - {"vite"}
    assert "svelte" in ui, "read something, not nothing"
    core = tomllib.loads((ROOT / "core" / "pyproject.toml").read_text())["project"].get("dependencies", [])
    names = set(ui) | {re.split(r"[<>=!~\[; ]", d, maxsplit=1)[0] for d in core}
    assert not sorted(names - listed), f"a dependency with no entry: {sorted(names - listed)}"


@pytest.mark.parametrize("name", notices.DOCUMENTS)
def test_both_pages_render(name):
    page = notices.document(name)
    assert page["title"] and page["sections"]
    assert any(s.get("entries") for s in page["sections"]), "the list reaches the page"


def test_an_unknown_document_is_none():
    assert notices.document("../etc/passwd") is None


def test_the_repositorys_third_party_list_is_current():
    """Regenerate with `python -m gexis_core.notices` from the repository root."""
    assert (ROOT / "THIRD-PARTY.md").read_text() == notices.third_party_markdown()


def test_the_image_ships_the_repositorys_own_licence():
    """The stages cannot see the repository root, so 09-legal keeps a copy."""
    assert (STAGES / "09-legal" / "files" / "COPYING").read_bytes() == (ROOT / "LICENSE").read_bytes()


def test_the_change_logs_page_shows_the_last_ten_newest_first():
    """ADR-0116."""
    from gexis_core import changelog

    page = changelog.page()
    releases = [s for s in page["sections"] if s.get("notes")]
    assert len(releases) == 10
    assert releases[0]["heading"].startswith(changelog.releases()[0][0] + " · ")
    assert page["sections"][-1]["url"].startswith("https://github.com/")


def test_every_release_s_notes_follow_the_rules_from_when_they_had_sections():
    """What publish.sh refuses, checked where the notes are written."""
    from gexis_core import changelog

    for version, entry in changelog.releases():
        if changelog._key(version) < (0, 4, 0):
            continue  # prose, as published before the sections (0.4.0)
        lines = entry["notes"].splitlines()
        assert {"New", "Fixed", "Good to know"} & set(lines), version
        assert any(line.startswith("• ") for line in lines), version


def test_changelog_md_is_generated_from_the_release_notes():
    """ADR-0116 decision 7: the page's "older ones" point at it."""
    from gexis_core import changelog

    assert (ROOT / "CHANGELOG.md").read_text() == changelog.markdown(), \
        "run: cd core && python -m gexis_core.changelog ../CHANGELOG.md"
