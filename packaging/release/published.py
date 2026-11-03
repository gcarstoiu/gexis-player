#!/usr/bin/env python3
"""ADR-0173: what the published releases hold, read from GitHub and proven
by the release key, so a build needs no earlier release on its own disk.

    published.py indexes <dir>
        Every published part's InRelease, checked with packaging/keys'
        public key, and its Packages, checked against the InRelease, into
        <dir>/<part>/Packages. A part without a good InRelease is left out:
        nothing unsigned is trusted.

    published.py last <dir> <out dir> <package> ...
        The newest release on the testing channel: each named package's file
        from the part holding it, checked against its index, into <out dir>.
        A build cache filled this way reuses the published file of a version
        that did not change (BUILD-TRAPS, 1.4.0).

    published.py prefer <dir> <part dir>
        A file in <part dir> that a published part holds under the same name
        with other bytes is replaced by the published one: one name and
        version, one content (reuse.py).

Each file in a part is listed as `./<file>`; `../<other part>/<file>` is a
file that other part holds, and only the holder is used here.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO = "gcarstoiu/gexis-player"
BASE = f"https://github.com/{REPO}/releases/download"
KINDS = ("ours", "skins", "rpi", "debian")
KEY = Path(__file__).resolve().parents[2] / "packaging/keys/gexis-release.asc"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def get(url: str, dest: Path) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=120) as r, dest.open("wb") as out:
            while block := r.read(1 << 20):
                out.write(block)
        return True
    except OSError:
        dest.unlink(missing_ok=True)
        return False


def verified(signed: Path) -> str | None:
    """The text a clearsigned file carries, if the release key signed it."""
    with tempfile.TemporaryDirectory() as home:
        keyring = Path(home) / "key.gpg"
        subprocess.run(["gpg", "--batch", "--homedir", home, "-o", str(keyring), "--dearmor", str(KEY)],
                       check=True, capture_output=True)
        r = subprocess.run(["gpgv", "--keyring", str(keyring), "--output", "-", str(signed)],
                           capture_output=True)
    return r.stdout.decode() if r.returncode == 0 else None


def part_tags() -> list[str]:
    out = subprocess.run(["gh", "api", "--paginate", f"repos/{REPO}/releases", "--jq", ".[].tag_name"],
                         check=True, capture_output=True, text=True).stdout.split()
    return sorted(t for t in out if t.split("-", 1)[0] in KINDS)


def indexes(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    kept = 0
    for tag in part_tags():
        d = dest / tag
        if (d / "Packages").exists():
            kept += 1
            continue
        d.mkdir(exist_ok=True)
        if not (get(f"{BASE}/{tag}/InRelease", d / "InRelease") and get(f"{BASE}/{tag}/Packages", d / "Packages")):
            print(f"  {tag}: no InRelease or Packages, left out")
            continue
        release = verified(d / "InRelease")
        want = re.search(r"^ ([0-9a-f]{64}) +\d+ Packages$", release or "", re.M)
        if not want or sha256(d / "Packages") != want.group(1):
            print(f"  {tag}: not signed by the release key, or its Packages does not match; left out")
            for f in d.iterdir():
                f.unlink()
            d.rmdir()
            continue
        kept += 1
    print(f"{kept} published parts, each index proven by the release key")


def records(packages: Path):
    for record in packages.read_text().split("\n\n"):
        f = dict(l.split(": ", 1) for l in record.splitlines() if l and not l[0].isspace() and ": " in l)
        if {"Package", "Version", "Filename", "SHA256"} <= set(f):
            yield f


def held(dest: Path) -> dict[str, list[tuple[str, str]]]:
    """file name -> [(holding part, sha256)]: before reproducible builds a
    name was sometimes published twice with other bytes (reuse.py)."""
    out: dict[str, list[tuple[str, str]]] = {}
    for packages in sorted(dest.glob("*/Packages")):
        for f in records(packages):
            if f["Filename"].startswith("./"):
                out.setdefault(f["Filename"][2:], []).append((packages.parent.name, f["SHA256"]))
    return out


def fetch(name: str, holder: tuple[str, str], out: Path) -> Path:
    part, sum_ = holder
    target = out / name
    if target.exists() and sha256(target) == sum_:
        return target
    partial = out / (name + ".partial")
    if not get(f"{BASE}/{part}/{name}", partial) or sha256(partial) != sum_:
        partial.unlink(missing_ok=True)
        sys.exit(f"ERROR: {part}/{name} could not be fetched as its index records it")
    partial.replace(target)
    return target


def last(dest: Path, out: Path, packages: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        channel = Path(tmp) / "testing"
        if not get(f"{BASE}/channels/testing", channel):
            sys.exit("ERROR: the testing channel could not be read")
        text = verified(channel) or sys.exit("ERROR: the testing channel is not signed by the release key")
    parts = re.search(r"^Repositories: (.+)$", text, re.M).group(1).split()
    files = held(dest)
    out.mkdir(parents=True, exist_ok=True)
    for part in parts:
        for f in records(dest / part / "Packages"):
            if f["Package"] in packages:
                name = Path(f["Filename"]).name
                holder = next((h for h in files.get(name, ()) if h[1] == f["SHA256"]), None)
                if not holder:
                    sys.exit(f"ERROR: {name} is in no published part as {part} records it")
                fetch(name, holder, out)
                print(f"  {name}, from {holder[0]}")


def prefer(dest: Path, part_dir: Path) -> None:
    files = held(dest)
    for deb in sorted(part_dir.glob("*.deb")):
        holders = files.get(deb.name, [])
        if not holders or sha256(deb) in {h[1] for h in holders}:
            continue
        if len({h[1] for h in holders}) > 1:
            sys.exit(f"ERROR: {deb.name} is published with more than one content; give it a new version")
        deb.unlink()
        fetch(deb.name, holders[0], part_dir)
        print(f"  {deb.name}: the published file, from {holders[0][0]}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "indexes":
        indexes(Path(sys.argv[2]))
    elif cmd == "last":
        last(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4:])
    elif cmd == "prefer":
        prefer(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        sys.exit(__doc__)
