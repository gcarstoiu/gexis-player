#!/usr/bin/env python3
"""ADR-0108 as amended 2026-10-01: each package file is uploaded once, ever.

    reuse.py part <part dir> <indexes dir>
        Rewrite the part's Packages so a file some published part already
        holds - the same name and the same SHA256 - is fetched from there
        (`Filename: ../<that part>/<file>`), and print those files, which
        the part then does not carry. <indexes dir> is published.py's.

**The same bytes, proven, not assumed from a name** (ADR-0173): the SHA256
the new index records for the file must equal the one the holding part's
own index records, and that index is proven by the release key
(published.py). Until 2026-11-02 this compared copies built on R2D2; the
signed index proves the same without them. apt checks the SHA256 of every
file it downloads against this index anyway: a wrong reference fails the
download, before anything is installed.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from published import held, records  # noqa: E402


def part(part_dir: Path, indexes: Path) -> None:
    holders = held(indexes)
    packages = part_dir / "Packages"
    text = packages.read_text()
    reused = []
    clashes = []
    for fields in records(packages):
        name = Path(fields["Filename"]).name
        want = fields["SHA256"]
        others = [h for h in holders.get(name, ()) if h[0] != part_dir.name]
        same = [tag for tag, sum_ in others if sum_ == want]
        if same:
            old = f"Filename: {fields['Filename']}\n"
            assert text.count(old) == 1, old
            text = text.replace(old, f"Filename: ../{same[-1]}/{name}\n")
            reused.append(name)
        elif others:
            # **One name and version, one content** (found 2026-10-03:
            # gexis-lyrion-server 9.1.1-2 was published twice with
            # different bytes; a device fetching 0.8.1 had its copy
            # replaced by 0.8.0's for the rollback, and the install
            # stopped). apt keys its cache by name and version, so a new
            # content under a published version is never right: bump it.
            # Copies that differed before reproducible builds are history;
            # what this refuses is adding one more.
            clashes.append(f"{name} (in {', '.join(tag for tag, _ in others)})")
    if clashes:
        sys.exit("ERROR: already published with different content - give each a new version: "
                 + ", ".join(clashes))
    packages.write_text(text)
    for name in reused:
        print(name)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "part":
        part(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        sys.exit(__doc__)
