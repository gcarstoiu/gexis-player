#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Assemble one size's skin pack from verified, extracted archives (ADR-0111).

    assemble.py --size 800x480 --index index.json --catalog <dir> --gelo5 <dir>
                --out <root>/opt/gexis-peppy/packs/800x480 --report report.json
                --work <scratch> [--letterbox letterbox.py]

`<catalog>/<name>/` holds each catalog zip of the size extracted as it is;
`<gelo5>/` holds Gelo5's set for the size. Nothing here fetches or verifies a
download: build.sh has done that against the pins before this runs.

**What a skin is.** A PeppyMeter skin is one section of a `meters.txt` - the
picker offers section names, never folders - so a folder is not the unit:
Gelo5's `00-99` folder holds the same skins as its `01-20`...`81-99` folders,
and a catalog `g5_*` pack holds twenty of them under the same names. A skin's
identity is therefore **its section's keys and values, with every value that
names a file in its folder replaced by that file's SHA256**, plus, when it names
a spectrum (`spectrum.name`), that spectrum section taken the same way. The
section's own name is not part of it: two names for byte-identical pictures
and numbers are one skin shown twice. Two skins with the same identity are
shipped once - the first met, in this order: Gelo5's merged folders, Gelo5's
split folders, then the catalog by name - and the rest are listed in the
report with the skin they repeat.

**The layout is the one the visualiser already reads**, under a root of its own
per size so several sizes never collide (`gexis-peppy-driver.py`'s
`load_corpus` and `spectrum_base`):

    <out>/<pack>/templates/<W>x<H>/meters.txt (+ the pictures it names)
    <out>/<pack>/templates_spectrum/<W>x<H>/meters.txt, spectrum.txt (+ pictures)
    <out>/pack.json

Dropped as not part of any skin (ADR-0111 decision 8, and the archives'
packaging debris): every `preview.png`, macOS metadata (`__MACOSX/`, `._*`,
`.DS_Store`), `.py` helper scripts, and files outside a skin folder. Each is
named in the report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SECTION = re.compile(r"^\s*\[(?P<name>.+?)\]\s*$")
SAFE = re.compile(r"[^A-Za-z0-9._+-]")
GELO5_FOLDER = re.compile(r"^(?P<size>\d+x\d+)_Gelo5 (?P<what>.+)_(?P<id>\d+)$")
TEMPLATES = ("templates", "templates_spectrum")


class PackError(Exception):
    pass


_SHA256: dict[Path, str] = {}


def sha256(path: Path) -> str:
    """Each file is hashed once: a skin names the same background as its
    neighbours, and the 1920x1080 pack is most of a gigabyte."""
    if path not in _SHA256:
        _SHA256[path] = hashlib.sha256(path.read_bytes()).hexdigest()
    return _SHA256[path]


def read_text(path: Path) -> str:
    return path.read_bytes().decode("utf-8", errors="surrogateescape")


def blocks(text: str) -> list[tuple[str | None, list[str]]]:
    """The file as (section name, lines) blocks, the preamble's name None.
    Lines keep their endings, so joining the blocks is the file again."""
    out: list[tuple[str | None, list[str]]] = [(None, [])]
    for line in text.splitlines(keepends=True):
        head = SECTION.match(line.rstrip("\r\n"))
        if head:
            out.append((head.group("name"), [line]))
        else:
            out[-1][1].append(line)
    return out


def options(lines: list[str]) -> dict[str, str]:
    """A section's keys, the last of a repeated key winning, as configparser
    (strict=False) has it."""
    found: dict[str, str] = {}
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")) or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        found[key.strip()] = value.strip()
    return found


def in_folder(token: str, directory: Path) -> bool:
    """A value that names a file of the skin: a plain name, or a path inside
    the folder (`icons/Akai_play.png`), never one that leaves it."""
    return bool(token) and ".." not in token.split("/") and not token.startswith("/") \
        and (directory / token).is_file()


def named_files(values: dict[str, str], directory: Path) -> set[str]:
    """The files in `directory` that a section's values name - a value may
    list several (`cdart.png,Vinyl_CD.png`)."""
    names = set()
    for value in values.values():
        for token in value.split(","):
            if in_folder(token.strip(), directory):
                names.add(token.strip())
    return names


def identity(values: dict[str, str], directory: Path) -> list:
    out = []
    for key in sorted(values):
        tokens = []
        for token in values[key].split(","):
            t = token.strip()
            tokens.append("sha256:" + sha256(directory / t) if in_folder(t, directory) else t)
        out.append([key, tokens])
    return out


def debris(path: Path) -> str | None:
    """Why a file is not part of any skin, or None if it may be."""
    parts = path.parts
    if "__MACOSX" in parts or path.name.startswith("._") or path.name == ".DS_Store":
        return "macOS metadata"
    if path.name.lower() == "preview.png":
        return "preview (ADR-0111 decision 8)"
    if path.suffix.lower() == ".py":
        return "helper script, not read by the visualiser"
    return None


def copy_unit(source: Path, target: Path, dropped: list[dict], label: str) -> None:
    """A skin folder's files into `target`, sub-folders kept (the animated
    packs' `icons/`), debris left behind and named."""
    target.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(source)
        why = debris(rel)
        if why:
            dropped.append({"pack": label, "file": str(rel), "reason": why})
            continue
        (target / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target / rel)


class Assembly:
    def __init__(self, size: str, out: Path, work: Path):
        self.size = size
        self.out = out
        self.staging = work / "staging"
        self.seen: dict[str, tuple[str, str]] = {}   # identity -> (pack, section)
        self.packs: list[dict] = []
        self.dropped_skins: list[dict] = []
        self.dropped_files: list[dict] = []
        self.dropped_packs: list[dict] = []

    # -- dedup ---------------------------------------------------------------
    def spectrum_sections(self, pack_dir: Path) -> tuple[Path, dict[str, dict[str, str]]]:
        directory = pack_dir / "templates_spectrum" / self.size
        path = directory / "spectrum.txt"
        if not path.is_file():
            return directory, {}
        return directory, {name: options(lines) for name, lines in blocks(read_text(path)) if name}

    def admit(self, name: str, pack_dir: Path, source: dict) -> None:
        """Keep a staged pack's new skins, drop its repeats; drop the pack
        when nothing of it is new."""
        spec_dir, spectra = self.spectrum_sections(pack_dir)
        kept_total = 0
        plans = []
        for templates in TEMPLATES:
            directory = pack_dir / templates / self.size
            meters = directory / "meters.txt"
            if not meters.is_file():
                continue
            parsed = blocks(read_text(meters))
            keep, drop = [], []
            for section, lines in parsed:
                if section is None:
                    continue
                values = options(lines)
                ident = identity(values, directory)
                linked = values.get("spectrum.name")
                if linked and linked in spectra:
                    ident.append(["@spectrum", identity(spectra[linked], spec_dir)])
                key = hashlib.sha256(json.dumps(ident).encode("utf-8", "surrogateescape")).hexdigest()
                if key in self.seen:
                    drop.append((section, lines, self.seen[key]))
                else:
                    self.seen[key] = (name, section)
                    keep.append((section, lines))
            plans.append((directory, meters, parsed, keep, drop))
            kept_total += len(keep)

        for directory, meters, parsed, keep, drop in plans:
            for section, _lines, same in drop:
                self.dropped_skins.append({
                    "pack": name, "skin": section, "file": f"{directory.parent.name}/meters.txt",
                    "same_as": f"{same[0]}: {same[1]}",
                })
        if kept_total == 0:
            shutil.rmtree(pack_dir)
            self.dropped_packs.append({"pack": name, "source": source["name"],
                                       "reason": "every skin repeats one already in the pack"})
            return

        for directory, meters, parsed, keep, drop in plans:
            if not drop:
                continue
            dropped_names = {section for section, _l, _s in drop}
            orphan = set()
            for section, lines in parsed:
                if section in dropped_names:
                    orphan |= named_files(options(lines), directory)
            if keep:
                text = "".join("".join(lines) for section, lines in parsed if section not in dropped_names)
                meters.write_bytes(text.encode("utf-8", errors="surrogateescape"))
            else:
                meters.unlink()   # this folder repeats; the pack's other one does not
            # A picture only a dropped skin named goes with it.
            for f in sorted(orphan - self.referenced(directory)):
                (directory / f).unlink()

        target = self.out / name
        if target.exists():
            raise PackError(f"two packs would be {name}")
        shutil.move(str(pack_dir), str(target))
        self.packs.append({"dir": name, "source": source["name"], **source.get("extra", {}),
                           "skins": kept_total})

    def referenced(self, directory: Path) -> set[str]:
        names: set[str] = set()
        for txt in ("meters.txt", "spectrum.txt"):
            path = directory / txt
            if path.is_file():
                for section, lines in blocks(read_text(path)):
                    if section:
                        names |= named_files(options(lines), directory)
        return names

    def stage(self, name: str) -> Path:
        """A pack is staged apart and moved into place only once something of
        it is kept: `1280x400_rose rs150` and `1280x400_rose_rs150` are one
        name on disk, and the second is a repeat."""
        pack_dir = self.staging / str(len(self.packs) + len(self.dropped_packs))
        if pack_dir.exists():
            shutil.rmtree(pack_dir)
        return pack_dir


def gelo5_folders(root: Path, size: str) -> list[tuple[str, str, dict[str, Path]]]:
    """Gelo5's skin folders as (id, what, {templates|templates_spectrum:
    folder}), the merged `00-99` first, then by id. A Spec&Met set is one id
    in both of the archive's top folders: its meters in one, its spectrum in
    the other."""
    found: dict[str, tuple[str, dict[str, Path]]] = {}
    for top in sorted(p for p in root.iterdir() if p.is_dir()):
        if top.name in ("template", "templates"):
            kind = "templates"
        elif top.name in ("template_spectrum", "templates_spectrum"):
            kind = "templates_spectrum"
        else:
            raise PackError(f"Gelo5 {size}: unexpected top folder {top.name!r}")
        for folder in sorted(p for p in top.iterdir() if p.is_dir()):
            m = GELO5_FOLDER.match(folder.name)
            if not m or m.group("size") != size:
                raise PackError(f"Gelo5 folder {folder.name!r} is not one this build knows")
            found.setdefault(m.group("id"), (m.group("what"), {}))[1][kind] = folder
    merged = [i for i, (what, _f) in found.items() if what.startswith("00-99")]
    if len(merged) != 1:
        raise PackError(f"Gelo5 {size}: expected one 00-99 folder, found {merged}")
    order = merged + sorted(i for i in found if i not in merged)
    return [(i, found[i][0], found[i][1]) for i in order]


def assemble(args) -> dict:
    size = args.size
    out: Path = args.out
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    work = args.work
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    a = Assembly(size, out, work)

    # -- Gelo5 -------------------------------------------------------------
    gelo = {"name": "Gelo5", "extra": {}}
    for top in sorted(args.gelo5.iterdir()):
        for loose in sorted(p for p in top.iterdir() if p.is_file()) if top.is_dir() else [top]:
            a.dropped_files.append({"pack": "Gelo5", "file": str(loose.relative_to(args.gelo5)),
                                    "reason": "outside any skin folder"})
    # **Upstream's own layout, not gexis-skins'.** A Spec&Met set's meters
    # stay in `templates/` and its spectrum in `templates_spectrum/`, as the
    # archive and the catalog have them. gexis-skins copied both into one
    # folder, and the spectrum's `<Name>_bgr.png` overwrote the meter's file
    # of the same name - which is what Finding 050 saw at 1280x800 (two
    # files; 3 to 14 per size elsewhere). Kept apart, nothing is overwritten
    # and nothing needs correcting; `check_backgrounds` holds that.
    #
    # The merged `00-99` folder is `gelo5`; every other folder is
    # `gelo5-<id>`, the split ones expected to go as repeats of `00-99`.
    for n, (ident, _what, kinds) in enumerate(gelo5_folders(args.gelo5, size)):
        name = "gelo5" if n == 0 else f"gelo5-{ident}"
        pack_dir = a.stage(name)
        for kind, folder in sorted(kinds.items()):
            copy_unit(folder, pack_dir / kind / size, a.dropped_files, name)
        a.admit(name, pack_dir, gelo)

    # -- the catalog ---------------------------------------------------------
    index = json.loads(Path(args.index).read_text())
    wanted = {size}
    if size == "1280x800":
        wanted.add("1280x720")   # letterboxed, as gexis-skins does (ADR-0096)
    entries = sorted((t for t in index["templates"] if f"{t['width']}x{t['height']}" in wanted),
                     key=lambda t: t["name"])
    for t in entries:
        tsize = f"{t['width']}x{t['height']}"
        src = args.catalog / t["name"]
        if not src.is_dir():
            raise PackError(f"{t['name']} was not extracted to {src}")
        name = SAFE.sub("_", t["name"])
        source = {"name": "foonerd/peppy_templates",
                  "extra": {"catalog": t["name"], "zip_sha256": t["sha256"]}}
        if tsize != size:
            source["extra"]["letterboxed_from"] = tsize
        units = t["units"]
        if tsize != size and any(u["install"] != "templates" for u in units):
            a.dropped_packs.append({"pack": name, "source": source["name"],
                                    "reason": f"{tsize} with a spectrum: letterbox.py moves meters.txt only"})
            continue
        pack_dir = a.stage(name)
        for u in units:
            unit_src = src / u["from"] if u["from"] else src
            if not unit_src.is_dir():
                raise PackError(f"{t['name']}: unit {u['from']!r} is not in the zip")
            if u["install"] not in TEMPLATES:
                raise PackError(f"{t['name']}: unit installs to {u['install']!r}")
            if tsize == size:
                copy_unit(unit_src, pack_dir / u["install"] / size, a.dropped_files, name)
                continue
            staged = work / name
            copy_unit(unit_src, staged, a.dropped_files, name)
            result = subprocess.run(
                [sys.executable, str(args.letterbox), str(staged), str(pack_dir / u["install"] / size),
                 "--from", tsize, "--to", size],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                shutil.rmtree(pack_dir, ignore_errors=True)
                a.dropped_packs.append({"pack": name, "source": source["name"],
                                        "reason": "letterbox refused: " + result.stderr.strip().split(": ", 2)[-1]})
                break
        else:
            a.admit(name, pack_dir, source)
        # Anything zipped beside the units (a preview, macOS metadata) is
        # named, so the report accounts for every file of every archive.
        unit_roots = {(src / u["from"]).resolve() if u["from"] else src.resolve() for u in units}
        for path in sorted(p for p in src.rglob("*") if p.is_file()):
            if not any(r == path.resolve() or r in path.resolve().parents for r in unit_roots):
                a.dropped_files.append({"pack": name, "file": str(path.relative_to(src)),
                                        "reason": debris(path.relative_to(src)) or "outside the install units"})

    # -- Finding 050, held ------------------------------------------------
    check_backgrounds(a)

    report = {
        "size": size,
        "skins": sum(p["skins"] for p in a.packs),
        "packs": a.packs,
        "dropped_packs": a.dropped_packs,
        "dropped_skins": a.dropped_skins,
        "dropped_files": a.dropped_files,
        "name_clashes": clashes(a),
    }
    return report


def check_backgrounds(a: Assembly) -> None:
    """**A circular meter may not draw a spectrum's panel** (Finding 050):
    asked of the pictures, not the names. meter-background-check.awk
    compares file names across a whole pack, which held while a pack was one
    folder; with meters and spectra in folders of their own, a meter's
    `Marantz_bgr.png` and the spectrum's are different files, and only their
    bytes say whether the dial is under a blank panel."""
    failures = []
    for pack in sorted(p for p in a.out.iterdir() if p.is_dir()):
        panels: dict[str, str] = {}
        for spectrum in sorted(pack.rglob("spectrum.txt")):
            for section, lines in blocks(read_text(spectrum)):
                bgr = options(lines).get("bgr.filename", "") if section else ""
                if bgr and (spectrum.parent / bgr).is_file():
                    panels[sha256(spectrum.parent / bgr)] = f"{section} ({bgr})"
        for meters in sorted(pack.rglob("meters.txt")):
            for section, lines in blocks(read_text(meters)):
                values = options(lines) if section else {}
                bgr = values.get("bgr.filename", "")
                if values.get("meter.type") != "circular" or not bgr:
                    continue
                path = meters.parent / bgr
                if path.is_file() and sha256(path) in panels:
                    failures.append(f"{meters.relative_to(a.out)} [{section}] draws {bgr}, "
                                    f"the panel of spectrum {panels[sha256(path)]}")
    if failures:
        raise PackError("a meter draws a spectrum panel (Finding 050):\n  " + "\n  ".join(failures))


def clashes(a: Assembly) -> list[dict]:
    """Skin names two packs share. The visualiser resolves a name to the
    first pack that has it, so the later one cannot be chosen by name."""
    where: dict[str, list[str]] = {}
    for pack in sorted(p for p in a.out.iterdir() if p.is_dir()):
        for templates in TEMPLATES:
            meters = pack / templates / a.size / "meters.txt"
            if meters.is_file():
                for name, _lines in blocks(read_text(meters)):
                    if name:
                        where.setdefault(name, []).append(f"{pack.name}/{templates}")
    return [{"skin": n, "in": w} for n, w in sorted(where.items()) if len(w) > 1]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--size", required=True)
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--catalog", type=Path, required=True)
    p.add_argument("--gelo5", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--letterbox", type=Path)
    args = p.parse_args(argv)
    try:
        report = assemble(args)
    except PackError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    args.report.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(f"{args.size}: {report['skins']} skins in {len(report['packs'])} packs; "
          f"{len(report['dropped_skins'])} repeated skins and {len(report['dropped_packs'])} packs dropped, "
          f"{len(report['dropped_files'])} files left out")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
