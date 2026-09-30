#!/usr/bin/env python3
"""ADR-0108: fetch the tested set - every OS package the image was built with,
at its exact version - into the release's two halves.

Runs inside gexis-deb-builder, with:
  /in/installed.txt   name version arch, one per line (the image's dpkg status)
  /in/keyrings/       the image's archive keyrings (Debian, Raspberry Pi)
  /cache              a cache of .deb files kept between releases
  /out/main, /out/debian   where each half's files go

`apt-get update` fetches the archives' indexes and checks their signatures;
everything after reads those indexes directly. (The first version asked apt
three times per package, and each apt start takes seconds under qemu: 347
packages in forty minutes.) Every file is checked against the SHA256 its
signed index gives before it is used - a cached one too - so a file here is
exactly what the archive published. A version no index lists stops the
release with its name: a tested set that cannot be fetched is not one.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SOURCES = """\
deb [signed-by=/in/keyrings/debian-archive-keyring.pgp] http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb [signed-by=/in/keyrings/debian-archive-keyring.pgp] http://deb.debian.org/debian trixie-updates main contrib non-free non-free-firmware
deb [signed-by=/in/keyrings/debian-archive-keyring.pgp] http://deb.debian.org/debian-security trixie-security main contrib non-free non-free-firmware
deb [signed-by=/in/keyrings/raspberrypi-archive-keyring.pgp] http://archive.raspberrypi.com/debian trixie main
"""
LISTS = Path("/var/lib/apt/lists")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def base_url(list_name: str) -> str:
    """deb.debian.org_debian-security_dists_trixie-security_... ->
    http://deb.debian.org/debian-security/"""
    root = list_name.split("_dists_", 1)[0]
    return "http://" + root.replace("_", "/") + "/"


def read_indexes() -> dict[tuple[str, str, str], tuple[str, str, str]]:
    """(name, version, arch) -> (url, filename, sha256), from the lists apt
    fetched and verified. `apt-helper cat-file` reads them compressed or not."""
    index: dict[tuple[str, str, str], tuple[str, str, str]] = {}
    for path in sorted(LISTS.glob("*_Packages*")):
        text = subprocess.run(["/usr/lib/apt/apt-helper", "cat-file", str(path)],
                              check=True, capture_output=True, text=True).stdout
        base = base_url(path.name)
        for record in text.split("\n\n"):
            fields = {}
            for line in record.splitlines():
                if line and not line[0].isspace() and ": " in line:
                    key, value = line.split(": ", 1)
                    fields[key] = value
            if "Package" in fields and "Filename" in fields:
                key = (fields["Package"], fields["Version"], fields["Architecture"])
                index.setdefault(key, (base + fields["Filename"], Path(fields["Filename"]).name, fields["SHA256"]))
    return index


def fetch(job: tuple[str, str, str, Path]) -> str | None:
    url, filename, expected, cached = job
    if cached.exists() and sha256(cached) == expected:
        return None
    partial = cached.with_suffix(".partial")
    with urllib.request.urlopen(url, timeout=120) as response, partial.open("wb") as out:
        shutil.copyfileobj(response, out)
    if sha256(partial) != expected:
        partial.unlink()
        return f"{filename} does not match its archive's index"
    partial.replace(cached)
    return None


def main() -> int:
    Path("/etc/apt/sources.list").write_text("")
    for old in Path("/etc/apt/sources.list.d").glob("*"):
        old.unlink()
    Path("/etc/apt/sources.list.d/tested-set.list").write_text(SOURCES)
    subprocess.run(["apt-get", "-q", "update"], check=True, stdout=subprocess.DEVNULL)
    index = read_indexes()

    wanted = [tuple(line.split()) for line in Path("/in/installed.txt").read_text().splitlines() if line.strip()]
    missing = [w for w in wanted if w not in index]
    if missing:
        print(f"ERROR: {len(missing)} package(s) of the tested set are in no archive's index:", file=sys.stderr)
        for m in missing:
            print("  " + " ".join(m), file=sys.stderr)
        return 1

    cache = Path("/cache")
    jobs = [(index[w][0], index[w][1], index[w][2], cache / index[w][1]) for w in wanted]
    with ThreadPoolExecutor(max_workers=8) as pool:
        errors = [e for e in pool.map(fetch, jobs) if e]
    if errors:
        for e in errors:
            print("ERROR: " + e, file=sys.stderr)
        return 1

    placed = {"main": 0, "debian": 0}
    for url, filename, _sha, cached in jobs:
        half = "main" if "archive.raspberrypi.com" in url else "debian"
        shutil.copy2(cached, Path("/out") / half / filename)
        placed[half] += 1
    print(f"tested set: {len(wanted)} packages, {placed['main']} from Raspberry Pi, {placed['debian']} from Debian")
    return 0


if __name__ == "__main__":
    sys.exit(main())
