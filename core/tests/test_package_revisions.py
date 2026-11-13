"""**A package versioned by its upstream carries our own files too; when
they change, its revision must** (LESSONS 53). apt does not reinstall a
version it has, so a unit changed under the same version never reached a
player: the review of 1.16.1 changed CamillaDSP's unit and its address
beside an unchanged `4.1.3-1`, and an updated player's core would have
spoken to an address CamillaDSP was not on.

`packaging/revisions.json` records, for each such package, its revision and
a hash of the files of ours its build copies. A change to those files fails
here until the revision is raised and the record updated with it."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "packaging" / "revisions.json"
#: A version that does not move with the repository: upstream's, then ours.
FIXED = re.compile(r'^VERSION="[^"]*-(\d+)"$', re.M)
SKIP = ("pins.sh", "fetch-cached.sh", "fetch-source.sh")


def _ours(script: Path) -> list[Path]:
    text = script.read_text()
    stage = re.search(r"^STAGE_DIR=/src/(\S+)$", text, re.M)
    paths = [ROOT / stage.group(1) / p for p in re.findall(r'\$STAGE_DIR/([A-Za-z0-9_./@-]+)', text)] if stage else []
    paths += [ROOT / p for p in re.findall(r"/src/([A-Za-z0-9_./@-]+)", text)]
    return sorted({p for p in paths if p.is_file() and p.name not in SKIP})


def _fixed_packages() -> dict[str, tuple[int, str]]:
    found = {}
    for script in sorted((ROOT / "packaging").glob("*/build.sh")):
        revision = FIXED.search(script.read_text())
        if revision is None or "${1" in revision.group(0):
            continue
        digest = hashlib.sha256()
        for path in _ours(script):
            digest.update(str(path.relative_to(ROOT)).encode() + b"\0" + path.read_bytes() + b"\0")
        found[script.parent.name] = (int(revision.group(1)), digest.hexdigest())
    return found


def test_a_package_s_own_files_change_with_its_revision():
    record = json.loads(RECORD.read_text())
    found = _fixed_packages()
    assert set(found) == set(record), "every package with a fixed revision is recorded, and only those"
    for name, (revision, digest) in found.items():
        kept = record[name]
        if digest != kept["sha256"]:
            assert revision > kept["revision"], (
                f"{name}: its own files changed - raise the revision in packaging/{name}/build.sh "
                f"(it is -{revision}) and record the new one and this hash, {digest}")
        assert (revision, digest) == (kept["revision"], kept["sha256"]), (
            f"{name}: record -{revision} and {digest} in packaging/revisions.json")
