"""ADR-0108 as amended: a release reuses a published file only when it is the
same bytes - and stops when one name and version would carry two contents
(found 2026-10-03: gexis-lyrion-server 9.1.1-2, twice). Since ADR-0173 the
published bytes are known from the holding part's own index, proven by the
release key (published.py), not from copies built on one machine."""
from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

RELEASE = Path(__file__).parents[2] / "packaging/release"


def load(name: str):
    sys.path.insert(0, str(RELEASE))
    try:
        spec = importlib.util.spec_from_file_location(name.replace("-", "_"), RELEASE / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(RELEASE))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def index(directory: Path, *entries: tuple[str, str, bytes]) -> None:
    """A part's Packages: (package, Filename, bytes it records)."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "Packages").write_text("".join(
        f"Package: {p}\nVersion: 1\nArchitecture: all\nFilename: {f}\nSHA256: {sha(b)}\n\n" for p, f, b in entries))


def new_part(tmp_path: Path, data: bytes) -> Path:
    part = tmp_path / "build" / "ours"
    index(part, ("pkg", "./pkg_1_all.deb", data))
    (part / "pkg_1_all.deb").write_bytes(data)
    return part


def test_the_same_bytes_are_fetched_from_the_part_that_has_them(tmp_path):
    indexes = tmp_path / "published"
    index(indexes / "ours-old", ("pkg", "./pkg_1_all.deb", b"same"))
    part = new_part(tmp_path, b"same")
    load("reuse").part(part, indexes)
    assert "Filename: ../ours-old/pkg_1_all.deb" in (part / "Packages").read_text()


def test_one_name_and_version_with_two_contents_stops_the_release(tmp_path):
    indexes = tmp_path / "published"
    index(indexes / "ours-old", ("pkg", "./pkg_1_all.deb", b"before"))
    part = new_part(tmp_path, b"after")
    with pytest.raises(SystemExit, match="already published with different content.*pkg_1_all.deb \\(in ours-old\\)"):
        load("reuse").part(part, indexes)


def test_an_older_different_copy_does_not_stop_a_release_another_part_matches(tmp_path):
    """Built before builds were reproducible, an old part may hold other bytes
    under the same name; a later part holding these exact bytes is reused."""
    indexes = tmp_path / "published"
    index(indexes / "ours-old", ("pkg", "./pkg_1_all.deb", b"before"))
    index(indexes / "ours-later", ("pkg", "./pkg_1_all.deb", b"after"))
    part = new_part(tmp_path, b"after")
    load("reuse").part(part, indexes)
    assert "Filename: ../ours-later/pkg_1_all.deb" in (part / "Packages").read_text()


def test_only_the_part_holding_a_file_counts_as_having_it(tmp_path):
    """A part that refers to another's file does not hold it: the bytes are
    the holder's, and the download is from the holder."""
    indexes = tmp_path / "published"
    index(indexes / "ours-a", ("pkg", "./pkg_1_all.deb", b"x"))
    index(indexes / "ours-b", ("pkg", "../ours-a/pkg_1_all.deb", b"x"))
    assert load("published").held(indexes) == {"pkg_1_all.deb": [("ours-a", sha(b"x"))]}


def test_a_version_the_archive_dropped_comes_from_the_published_part_holding_it(tmp_path):
    prev = tmp_path / "published"
    index(prev / "rpi-1", ("libgtk", "./libgtk_1_all.deb", b"gtk"))
    index(prev / "rpi-2", ("libgtk", "../rpi-1/libgtk_1_all.deb", b"gtk"))
    index(prev / "ours-1", ("gexis-core", "./gexis-core_1_all.deb", b"core"))
    ours = load("fetch-tested-set").read_ours(prev)
    assert ours == {("libgtk", "1", "all"): (
        "https://github.com/gcarstoiu/gexis-player/releases/download/rpi-1/libgtk_1_all.deb",
        "libgtk_1_all.deb", sha(b"gtk"), "rpi")}
