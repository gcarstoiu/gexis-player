"""ADR-0108 as amended: a release reuses a published file only when it is the
same bytes - and stops when one name and version would carry two contents
(found 2026-10-03: gexis-lyrion-server 9.1.1-2, twice)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REUSE = Path(__file__).parents[2] / "packaging/release/reuse.py"


def reuse():
    spec = importlib.util.spec_from_file_location("reuse", REUSE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def release(tmp_path, old: bytes, new: bytes):
    """An earlier release's part holding pkg_1_all.deb, and a new part with
    its own pkg_1_all.deb."""
    out = tmp_path / "out"
    published = out / "r0.1.0" / "repos" / "ours-old"
    published.mkdir(parents=True)
    (published / "pkg_1_all.deb").write_bytes(old)
    part = out / "r0.2.0" / "repos" / "ours-new"
    part.mkdir(parents=True)
    (part / "pkg_1_all.deb").write_bytes(new)
    import hashlib
    (part / "Packages").write_text(
        f"Package: pkg\nVersion: 1\nFilename: ./pkg_1_all.deb\nSHA256: {hashlib.sha256(new).hexdigest()}\n\n")
    assets = tmp_path / "assets.json"
    assets.write_text(json.dumps({"ours-old": ["pkg_1_all.deb"]}))
    return part, assets, out


def test_the_same_bytes_are_fetched_from_the_part_that_has_them(tmp_path):
    part, assets, out = release(tmp_path, b"same", b"same")
    reuse().part(part, assets, out)
    assert "Filename: ../ours-old/pkg_1_all.deb" in (part / "Packages").read_text()


def test_one_name_and_version_with_two_contents_stops_the_release(tmp_path):
    part, assets, out = release(tmp_path, b"before", b"after")
    with pytest.raises(SystemExit, match="already published in ours-old with different content"):
        reuse().part(part, assets, out)
