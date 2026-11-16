#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR-0182: move a packaged part's pin to an upstream release.

    packaging/upstream-bump.py <part> <tag> [--keep <dir>]
    packaging/upstream-bump.py --parts        the parts it moves

Downloads the release's arm64 tarball and GitHub's archive of the tag's
source, checks the tarball holds the binary the build takes from it, and
writes the pin (version, address, sha256), the part's two lines in
packaging/inputs.tsv - the binary and the source beside it - and, where
image/verify-image.sh checks the binary itself (CamillaDSP), that checksum
(BUILD-TRAPS: raising a pin raises the image check's). With --keep the
two files are left in <dir> under their sha256, as the `inputs` mirror names
them. Run by packaging/upstream-daily.sh; nothing is committed here.

Exit 0: moved. Exit 3: the release is not what the pin expects (no such
asset, or no binary in it) - an issue, not a pull request.
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
INPUTS = ROOT / "packaging/inputs.tsv"

PARTS = {
    "go-librespot": {
        "repo": "devgianlu/go-librespot",
        "name": "go-librespot",
        "pins": "packaging/go-librespot/pins.sh",
        "var": "GO_LIBRESPOT",
        "asset": "go-librespot_linux_arm64.tar.gz",
        "binary": "go-librespot",
        "header": (
            "# The pin for go-librespot (ADR-0107): the one place it is written. Read by\n"
            "# packaging/go-librespot/build.sh and by the Makefile's image annotation.\n"
        ),
    },
    "camilladsp": {
        "repo": "HEnquist/camilladsp",
        "name": "CamillaDSP",
        "pins": "packaging/camilladsp/pins.sh",
        "var": "CAMILLADSP",
        "asset": "camilladsp-linux-aarch64.tar.gz",
        "binary": "camilladsp",
        "image_check": "CAMILLADSP_BINARY_SHA256",
        "header": (
            "# The pin for CamillaDSP (ADR-0162 D1, ADR-0107): the one place it is written.\n"
            "# Read by packaging/camilladsp/build.sh and by check-upstream.sh.\n"
        ),
    },
}


class NotSimple(Exception):
    """The release does not fit the pin: an issue for a person instead."""


def fetch(url: str, dest: pathlib.Path) -> str:
    """Download url to dest; return its sha256."""
    req = urllib.request.Request(url, headers={"User-Agent": "gexis-upstream-check"})
    h = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 16):
            h.update(chunk)
            f.write(chunk)
    return h.hexdigest()


def release_assets(repo: str, tag: str) -> list[str]:
    url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    headers = {"User-Agent": "gexis-upstream-check", "Accept": "application/vnd.github+json"}
    if token := os.environ.get("GH_TOKEN"):  # the workflow's: a runner shares the unauthenticated limit
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return [a["name"] for a in json.load(r)["assets"]]


def pins_text(part: dict, tag: str, sha: str) -> str:
    v = part["var"]
    return (
        part["header"]
        + f'{v}_VERSION="{tag}"\n'
        + f'{v}_ASSET="{part["asset"]}"\n'
        + f'{v}_URL="https://github.com/{part["repo"]}/releases/download/${{{v}_VERSION}}/${{{v}_ASSET}}"\n'
        + f'{v}_SHA256="{sha}"\n'
    )


def inputs_text(text: str, part: dict, tag: str, binary_sha: str, source_sha: str) -> str:
    """The part's two lines replaced where they stand: the binary's and its source's."""
    repo, name = part["repo"], part["name"]
    out, seen = [], []
    for line in text.splitlines(keepends=True):
        cols = line.rstrip("\n").split("\t")
        if line.startswith("#") or len(cols) != 4 or f"/{repo}/" not in cols[3]:
            out.append(line)
            continue
        source = "source of the binary we ship" in cols[2]
        seen.append("source" if source else "binary")
        if source:
            out.append(f"{source_sha}\t{cols[1]}\t{name} {tag}, source of the binary we ship\t"
                       f"https://codeload.github.com/{repo}/tar.gz/{tag}\n")
        else:
            out.append(f"{binary_sha}\t{cols[1]}\t{name}, binary {tag}\t"
                       f"https://github.com/{repo}/releases/download/{tag}/{part['asset']}\n")
    if sorted(seen) != ["binary", "source"]:
        raise NotSimple(f"packaging/inputs.tsv has {seen or 'no lines'} for {repo}, not one binary and one source")
    return "".join(out)


def image_check_text(text: str, var: str, tag: str, sha: str, today: str) -> str:
    """The image check's checksum of the binary, and the release and date beside it."""
    text, n = re.subn(rf'^{var}="[0-9a-f]*"$', f'{var}="{sha}"', text, flags=re.M)
    if n != 1:
        raise NotSimple(f"image/verify-image.sh has {n} lines setting {var}")
    return re.sub(r"(extracted from the pinned release, )v[0-9.]+, \d{4}-\d{2}-\d{2}\)",
                  rf"\g<1>{tag}, {today})", text)


def bump(part_id: str, tag: str, keep: pathlib.Path | None, root: pathlib.Path = ROOT,
         fetch=fetch, assets=release_assets) -> tuple[str, str]:
    part = PARTS[part_id]
    if part["asset"] not in assets(part["repo"], tag):
        raise NotSimple(f"{part['repo']} {tag} has no {part['asset']}")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        binary_sha = fetch(f"https://github.com/{part['repo']}/releases/download/{tag}/{part['asset']}",
                           tmp / "binary")
        with tarfile.open(tmp / "binary") as t:
            members = {m.name.removeprefix("./"): m for m in t.getmembers() if m.isfile()}
            if part["binary"] not in members:
                raise NotSimple(f"{part['asset']} of {tag} holds no {part['binary']} at its top")
            binary_itself = hashlib.sha256(t.extractfile(members[part["binary"]]).read()).hexdigest()
        source_sha = fetch(f"https://codeload.github.com/{part['repo']}/tar.gz/{tag}", tmp / "source")
        inputs = root / "packaging/inputs.tsv"
        new_inputs = inputs_text(inputs.read_text(), part, tag, binary_sha, source_sha)
        check = root / "image/verify-image.sh"
        if "image_check" in part:
            new_check = image_check_text(check.read_text(), part["image_check"], tag, binary_itself,
                                         datetime.date.today().isoformat())
        (root / part["pins"]).write_text(pins_text(part, tag, binary_sha))
        inputs.write_text(new_inputs)
        if "image_check" in part:
            check.write_text(new_check)
        if keep:
            keep.mkdir(parents=True, exist_ok=True)
            shutil.move(tmp / "binary", keep / binary_sha)
            shutil.move(tmp / "source", keep / source_sha)
    return binary_sha, source_sha


def main() -> int:
    if sys.argv[1:] == ["--parts"]:  # the parts it moves, for upstream-daily.sh
        print("\n".join(sorted(PARTS)))
        return 0
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("part", choices=sorted(PARTS))
    ap.add_argument("tag")
    ap.add_argument("--keep", type=pathlib.Path)
    a = ap.parse_args()
    try:
        binary_sha, source_sha = bump(a.part, a.tag, a.keep)
    except NotSimple as e:
        print(f"not moved: {e}", file=sys.stderr)
        return 3
    print(f"{PARTS[a.part]['name']} {a.tag}: binary {binary_sha}, source {source_sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
