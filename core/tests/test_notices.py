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
    for script in STAGES.glob("*/0*-run*.sh"):
        urls |= set(re.findall(r"https://[^\"' ]+", script.read_text()))
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
    package = json.loads((ROOT / "ui" / "package.json").read_text())
    # The panel's build has no runtime dependencies in name: everything is a
    # devDependency, and what is bundled into it is the framework and fonts.
    ui = {n for n in {**package.get("dependencies", {}), **package.get("devDependencies", {})}
          if n == "svelte" or n.startswith("@fontsource")}
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
