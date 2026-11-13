# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR-0108, ADR-0173: `packaging/release/publish.sh` against a fake GitHub.

The script runs as it is, from a copy of its folder, with `gh`, `curl`,
`gpg`, `git` and `sleep` replaced by stand-ins: GitHub's releases are
folders under `web/`, a signature is a first line `SIGNED`, an attestation
is a file's sha256 listed for a tag. Nothing reaches the network."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REPO = "gcarstoiu/gexis-player"
BASE = f"https://github.com/{REPO}/releases/download/"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")

COMMON = f'''#!{sys.executable} -I
import hashlib, json, os, shutil, sys
from pathlib import Path
T = Path(os.environ["FAKE_GITHUB"])
WEB = T / "web"
args = sys.argv[1:]
def state():
    return json.loads((T / "state.json").read_text())
def save(s):
    (T / "state.json").write_text(json.dumps(s))
def opt(name):
    return args[args.index(name) + 1] if name in args else None
with open(T / "calls.log", "a") as log:
    log.write(Path(sys.argv[0]).name + " " + " ".join(args) + "\\n")
'''

GH = COMMON + '''
s = state()
if s.get("fail_gh", 0) > 0:          # a one-off refusal, as GitHub's 502
    s["fail_gh"] -= 1
    save(s)
    sys.exit("HTTP 502: Bad Gateway")
def names(rel):
    return sorted(p.name for p in (WEB / rel).iterdir())
if args[0] == "api":
    path = next(a for a in args[1:] if a.startswith("repos/")).split("/", 3)[3]
    if path.startswith("releases?"):
        print("\\n".join(sorted(p.name for p in WEB.iterdir())))
        sys.exit(0)
    rel = path.split("/")[2] if path.startswith("releases/tags/") else path.split("/")[1]
    if not (WEB / rel).is_dir():
        sys.exit("HTTP 404: Not Found")
    print(rel if path.startswith("releases/tags/") else "\\n".join(names(rel)))
    sys.exit(0)
verb, rel = args[1], args[2]
if args[0] == "attestation":
    digest = hashlib.sha256(Path(rel).read_bytes()).hexdigest()
    sys.exit(0 if opt("--source-ref") in s.get("attested", {}).get(digest, []) else "no attestation")
if verb == "create":
    if (WEB / rel).is_dir():
        sys.exit("a release with the same tag name already exists")
    (WEB / rel).mkdir(parents=True)
    sys.exit(0)
if not (WEB / rel).is_dir():
    sys.exit("release not found")
if verb == "view" and "--json" in args:
    print("\\n".join(names(rel)))
elif verb == "upload":
    rest = args[3:]
    files = [a for i, a in enumerate(rest) if not a.startswith("--") and (i == 0 or rest[i - 1] != "--repo")]
    for f in files:
        shutil.copy(f, WEB / rel / Path(f).name)
'''

CURL = COMMON + '''
url, out = args[-1], opt("-o")
part = url[len("''' + BASE + '''"):]
s = state()
code = 200 if (WEB / part).is_file() else 404
if part in s.get("curl404", []):     # GitHub answering 404 for a file it has
    code = 404
    s["fail_gh"] = s.get("fail_after_404", 0)
    save(s)
if code == 200:
    shutil.copy(WEB / part, out)
if "-w" in args:
    print(code, end="")
sys.exit(22 if code != 200 and any(a.startswith("-f") for a in args) else 0)
'''

GPG = COMMON + '''
SIGNED = "SIGNED\\n"
if "--verify" in args:
    sys.exit(0 if Path(args[-1]).read_text().startswith(SIGNED) else 1)
if "--decrypt" in args:
    text = Path(args[-1]).read_text()
    sys.exit(print(text[len(SIGNED):], end="") if text.startswith(SIGNED) else 2)
Path(opt("-o")).write_text(SIGNED + Path(args[-1]).read_text() if "--clearsign" in args else "SIG\\n")
'''

GIT = COMMON + '''
version = args[1].split(":")[0][1:]
print(json.dumps({"releases": {version: {"date": "2026-11-10", "notes": "New\\n\\u2022 A thing."}}}))
'''

SLEEP = COMMON


class FakeGitHub:
    """The script's folder copied, the stand-ins on its PATH, GitHub as
    folders."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.tree = tmp / "tree"
        (self.tree / "packaging/release").mkdir(parents=True)
        shutil.copy(ROOT / "packaging/release/publish.sh", self.tree / "packaging/release/publish.sh")
        shutil.copy(ROOT / "packaging/release/sign.sh", self.tree / "packaging/release/sign.sh")
        self.web = tmp / "web"
        self.web.mkdir()
        self.bin = tmp / "bin"
        self.bin.mkdir()
        for name, text in (("gh", GH), ("curl", CURL), ("gpg", GPG), ("git", GIT), ("sleep", SLEEP)):
            (self.bin / name).write_text(text)
            (self.bin / name).chmod(0o755)
        self.state = {"attested": {}}
        self.save()

    def save(self) -> None:
        (self.tmp / "state.json").write_text(json.dumps(self.state))

    def put(self, release: str, name: str, text: str) -> Path:
        (self.web / release).mkdir(parents=True, exist_ok=True)
        path = self.web / release / name
        path.write_text(text)
        return path

    def attest(self, path: Path, tag: str) -> None:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.state["attested"].setdefault(digest, []).append(f"refs/tags/v{tag.lstrip('r')}")
        self.save()

    def run(self, *args: str) -> subprocess.CompletedProcess:
        self.save()
        env = {k: v for k, v in os.environ.items() if not k.startswith("GEXIS_")}
        env.update(PATH=f"{self.bin}:{os.environ['PATH']}", FAKE_GITHUB=str(self.tmp),
                   GEXIS_RELEASE_GNUPGHOME=str(self.tmp / "gnupg"), TMPDIR=str(self.tmp))
        r = subprocess.run(["bash", str(self.tree / "packaging/release/publish.sh"), *args],
                           env=env, capture_output=True, text=True, timeout=60)
        self.state = json.loads((self.tmp / "state.json").read_text())
        return r

    def serial(self, channel: str) -> int | None:
        path = self.web / "channels" / channel
        if not path.is_file():
            return None
        return int(next(l for l in path.read_text().splitlines() if l.startswith("Serial: "))[8:])


def _promotable(gh: FakeGitHub, tag: str = "r1.16.1") -> None:
    """A release built on GitHub, its image on its page, its parts signed."""
    image = gh.put(tag, "gexis-player.img.xz", "image")
    gh.put(tag, "gexis-player.img.xz.sha256",
           hashlib.sha256(b"image").hexdigest() + "  gexis-player.img.xz\n")
    gh.attest(image, tag)
    gh.put(tag, "parts", f"SIGNED\nRelease: {tag[1:]}\nParts: ours-abc skins-def\n")


# --- the channel's serial (the review of 1.16.1) ---------------------------

def test_a_channel_moves_on_from_the_serial_published(tmp_path):
    gh = FakeGitHub(tmp_path)
    _promotable(gh)
    gh.put("channels", "stable", "SIGNED\nChannel: stable\nSerial: 15\n")
    r = gh.run("--promote", "r1.16.1")
    assert r.returncode == 0, r.stderr
    assert gh.serial("stable") == 16


def test_a_404_and_one_failed_call_never_start_the_serial_again(tmp_path):
    """GitHub answered 404 for the channel file it had, and the one call meant
    to catch that failed once: taken for "no channels release", Serial: 1
    was signed over 15, and every device refused the channel."""
    gh = FakeGitHub(tmp_path)
    _promotable(gh)
    gh.put("channels", "stable", "SIGNED\nChannel: stable\nSerial: 15\n")
    gh.state.update(curl404=["channels/stable"], fail_after_404=1)
    r = gh.run("--promote", "r1.16.1")
    assert gh.serial("stable") == 15, r.stdout
    assert r.returncode != 0 and "404" in r.stderr


def test_a_404_while_github_keeps_refusing_stops_with_nothing_moved(tmp_path):
    gh = FakeGitHub(tmp_path)
    _promotable(gh)
    gh.put("channels", "stable", "SIGNED\nChannel: stable\nSerial: 15\n")
    gh.state.update(curl404=["channels/stable"], fail_after_404=50)
    r = gh.run("--promote", "r1.16.1")
    assert r.returncode != 0 and "kept refusing" in r.stderr
    assert gh.serial("stable") == 15


def test_a_channel_file_gone_from_github_goes_on_from_the_last_one_published_here(tmp_path):
    """An upload cut short after `--clobber` removed the old file: the next
    run found no file, truly, and started at 1."""
    gh = FakeGitHub(tmp_path)
    _promotable(gh)
    gh.put("channels", "testing", "SIGNED\nChannel: testing\nSerial: 69\n")
    seen = gh.tree / "packaging/release/out/serials"
    seen.mkdir(parents=True)
    (seen / "stable").write_text("15\n")
    r = gh.run("--promote", "r1.16.1")
    assert r.returncode == 0, r.stderr
    assert gh.serial("stable") == 16
    assert (seen / "stable").read_text().strip() == "16"


def test_a_channel_never_seen_starts_at_one(tmp_path):
    gh = FakeGitHub(tmp_path)
    _promotable(gh)
    r = gh.run("--promote", "r1.16.1")
    assert r.returncode == 0, r.stderr
    assert gh.serial("stable") == 1


# --- a part a tag left unsigned (the review of 1.16.1) ---------------------

PART = "skins-1957b7a7c16f"


def _built(gh: FakeGitHub, tag: str, date: str) -> Path:
    """`release/build.sh --unsigned`'s output for `tag`, as `release.yml`
    attests it: one part, whose Release each run dates."""
    dest = gh.tree / "packaging/release/out" / tag
    repo = dest / "repos" / PART
    repo.mkdir(parents=True)
    packages = "Package: gexis-skins-x\n"
    (repo / "Packages").write_text(packages)
    (repo / "Release").write_text(f"Date: {date}\nSHA256:\n {hashlib.sha256(packages.encode()).hexdigest()} "
                                  f"{len(packages)} Packages\n")
    (repo / "gexis-skins-x_1_all.deb").write_text("deb")
    (dest / "parts.plain").write_text(f"Release: {tag[1:]}\nParts: {PART}\n")
    (dest / "build.txt").write_text("Run: 1\n")
    (dest / "image").mkdir()
    (dest / "image/gexis-player.img.xz").write_text("image")
    for path in (repo / "Release", repo / "Packages", dest / "parts.plain", dest / "build.txt"):
        gh.attest(path, tag)
    return dest


def test_a_part_a_tag_left_unsigned_takes_the_next_tag_s_indexes(tmp_path):
    """1.17.0 uploaded, never signed (re-cut as 1.17.1), the same part in
    both: its Release stayed 1.17.0's, and signing 1.17.1 stopped at "no
    attestation from release.yml at v1.17.1"."""
    gh = FakeGitHub(tmp_path)
    _built(gh, "r1.17.0", "Mon, 01 Dec 2026 10:00:00 UTC")
    assert gh.run("--upload", "r1.17.0").returncode == 0
    shutil.rmtree(gh.tree / "packaging/release/out")
    dest = _built(gh, "r1.17.1", "Tue, 02 Dec 2026 10:00:00 UTC")
    r = gh.run("--upload", "r1.17.1")
    assert r.returncode == 0, r.stderr
    assert (gh.web / PART / "Release").read_text() == (dest / "repos" / PART / "Release").read_text()
    r = gh.run("--sign", "r1.17.1")
    assert r.returncode == 0, r.stderr
    assert (gh.web / PART / "InRelease").read_text().startswith("SIGNED\nDate: Tue")


def test_a_part_signed_before_keeps_its_indexes(tmp_path):
    gh = FakeGitHub(tmp_path)
    for name, text in (("Release", "Date: before\n"), ("InRelease", "SIGNED\nDate: before\n"),
                       ("Release.gpg", "SIG\n"), ("Packages", "Package: gexis-skins-x\n"),
                       ("gexis-skins-x_1_all.deb", "deb")):
        gh.put(PART, name, text)
    _built(gh, "r1.17.1", "Tue, 02 Dec 2026 10:00:00 UTC")
    r = gh.run("--upload", "r1.17.1")
    assert r.returncode == 0, r.stderr
    assert (gh.web / PART / "Release").read_text() == "Date: before\n"
    assert f"release upload {PART}" not in (tmp_path / "calls.log").read_text()
