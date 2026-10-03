#!/usr/bin/env python3
"""ADR-0108 as amended 2026-10-01: each package file is uploaded once, ever.

    reuse.py assets <out.json>
        Ask GitHub which files each part already published holds, and write
        {part: [file, ...]}. Once per release build.

    reuse.py part <part dir> <assets.json> <releases dir>
        Rewrite the part's Packages so a file some published part already
        holds - the same name and the same SHA256 - is fetched from there
        (`Filename: ../<that part>/<file>`), and print those files, which
        the part then does not carry.

**The same bytes, proven here, not assumed from a name.** The SHA256 is the
one the new index records for the file it was built from; it must equal the
SHA256 of the copy in that part as built here (packaging/release/out). A part
published but not built on this machine has no local copy to compare with,
and its files are uploaded again rather than trusted. apt checks the SHA256
of every file it downloads against this index anyway: a wrong reference
fails the download, before anything is installed.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = "gcarstoiu/gexis-player"
KINDS = ("ours", "skins", "rpi", "debian")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def assets(out: Path) -> None:
    """{part tag: [uploaded file names]} for every published part."""
    found: dict[str, list[str]] = {}
    for line in gh("api", "--paginate", f"repos/{REPO}/releases", "--jq", ".[] | [.id, .tag_name] | @tsv").splitlines():
        rid, tag = line.split("\t")
        if tag.split("-", 1)[0] not in KINDS:
            continue
        names = gh("api", "--paginate", f"repos/{REPO}/releases/{rid}/assets?per_page=100",
                   "--jq", '.[] | select(.state == "uploaded") | .name').split()
        found[tag] = sorted(n for n in names if n.endswith(".deb"))
    out.write_text(json.dumps(found, indent=1))
    print(f"{sum(len(v) for v in found.values())} files in {len(found)} published parts")


def records(packages: Path) -> list[dict[str, str]]:
    out = []
    for record in packages.read_text().split("\n\n"):
        fields = {}
        for line in record.splitlines():
            if line and not line[0].isspace() and ": " in line:
                key, value = line.split(": ", 1)
                fields[key] = value
        if fields:
            out.append(fields)
    return out


def part(part_dir: Path, assets_json: Path, releases: Path) -> None:
    published: dict[str, list[str]] = json.loads(assets_json.read_text())
    holders: dict[str, list[str]] = {}
    for tag, names in published.items():
        for name in names:
            holders.setdefault(name, []).append(tag)
    # The copies built here, by part: what a published file's bytes are.
    local: dict[tuple[str, str], Path] = {}
    for path in releases.glob("*/repos/*/*.deb"):
        local.setdefault((path.parent.name, path.name), path)

    packages = part_dir / "Packages"
    text = packages.read_text()
    reused = []
    clashes = []
    for fields in records(packages):
        name = Path(fields["Filename"]).name
        want = fields["SHA256"]
        others = [t for t in sorted(holders.get(name, ())) if t != part_dir.name]
        copies = {t: local[(t, name)] for t in others if (t, name) in local}
        same = [t for t, copy in copies.items() if sha256(copy) == want]
        if same:
            old = f"Filename: {fields['Filename']}\n"
            assert text.count(old) == 1, old
            text = text.replace(old, f"Filename: ../{same[-1]}/{name}\n")
            reused.append(name)
        elif copies:
            # **One name and version, one content** (found 2026-10-03:
            # gexis-lyrion-server 9.1.1-2 was published twice with
            # different bytes; a device fetching 0.8.1 had its copy
            # replaced by 0.8.0's for the rollback, and the install
            # stopped). apt keys its cache by name and version, so a new
            # content under a published version is never right: bump it.
            # Copies that differed before reproducible builds are history;
            # what this refuses is adding one more.
            clashes.append(f"{name} (in {', '.join(copies)})")
    if clashes:
        sys.exit("ERROR: already published with different content - give each a new version: "
                 + ", ".join(clashes))
    packages.write_text(text)
    for name in reused:
        print(name)


if __name__ == "__main__":
    if sys.argv[1] == "assets":
        assets(Path(sys.argv[2]))
    elif sys.argv[1] == "part":
        part(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    else:
        sys.exit(__doc__)
