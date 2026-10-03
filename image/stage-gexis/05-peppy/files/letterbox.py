#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Letterbox a 1280x720 PeppyMeter pack into a 1280x800 screen (ADR-0096,
ADR-0111 decision 15).

Everything the pack draws moves down by a band (40 px), and every full-frame
picture is padded with that band above and below. Run at package build, over a
folder extracted from a verified zip:

    python3 letterbox.py <pack dir> <out dir> [--from 1280x720] [--to 1280x800]

A folder holds a `meters.txt`, a `spectrum.txt`, or both; each is rewritten
line for line - comments, order and CRLF kept - so a diff against upstream
shows only the moved numbers.

**Two ways to move a meter.**

- *Padded* - a section whose meter sits at 0,0 and whose `bgr`/`fgr` pictures
  are whole frames. The pictures are padded, and the meter-relative positions
  (bars, needle origins) move with everything else; the origin stays at 0,0.
  This is how the three animated packs were done first, and why: PeppyMeter
  adds the meter origin to a component's bounding box a second time
  (`meter.py`'s `add_image`), so with the origin at 0,0 the boxes are exact.
- *Moved* - every other section: a meter drawn away from the corner, or one
  whose `bgr`/`fgr` is a strip rather than a frame. Its `meter.y` moves down
  by the band and everything drawn relative to the meter goes with it, so its
  own pictures are left as they are; only its full-frame `screen.bgr` is
  padded. Its bounding boxes are off by `meter.y` as upstream's are - by 40
  px more than at 720 - which is the same error every pack whose meter is
  away from the corner already has at its native size.

**A spectrum** is drawn at its section's `spectrum.x`/`spectrum.y`, with its
background, bars and `origin.x/y` relative to that point, so `spectrum.y` is
the one number that moves.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

#: Meter-relative (linear bars, circular needle origins): moved only for a
#: padded section, whose origin is 0,0 and stays there.
Y_ONLY = {"left.y", "right.y", "mono.y", "left.origin.y", "right.origin.y", "mono.origin.y"}
#: An `x,y[,…]` position on the screen.
POINT_SUFFIXES = (".pos", ".center")
POINT_KEYS = {"tonearm.pivot.screen"}
#: Named like a position and are not one: a marker's `pos` is a percentage
#: along the progress bar, and `playinfo.center` is a flag.
NOT_A_POINT = re.compile(r"^(progress\.marker\.\d+\.pos|playinfo(\.text)?\.center)$")
#: Pictures a padded section draws as whole frames.
FULL_FRAME = ("bgr.filename", "fgr.filename", "screen.bgr")
#: Drawn at the meter's origin: a moved section's travel with it, unpadded.
AT_ORIGIN = ("bgr.filename", "fgr.filename")
#: The one screen position of a spectrum section.
SPECTRUM_Y = "spectrum.y"

LINE = re.compile(r"^(?P<key>[^=\[#;]+?)(?P<eq>\s*=\s*)(?P<value>.*?)(?P<end>\r?)$")
SECTION = re.compile(r"^\[(?P<name>.+?)\]\s*\r?$")


class LetterboxError(Exception):
    pass


def is_point(key: str) -> bool:
    if NOT_A_POINT.match(key):
        return False
    return key in POINT_KEYS or key.endswith(POINT_SUFFIXES)


def shift_value(key: str, value: str, band: int) -> str:
    if key in Y_ONLY or key in ("meter.y", SPECTRUM_Y):
        return str(int(value.strip() or 0) + band)
    parts = value.split(",")
    if len(parts) < 2:
        raise LetterboxError(f"{key} = {value!r} is not an x,y position")
    parts[1] = str(int(parts[1].strip()) + band)
    return ",".join(p.strip() if i < 2 else p for i, p in enumerate(parts))


def sections(text: str) -> dict[str, dict[str, str]]:
    """Each section's keys, the last of a repeated one winning."""
    out: dict[str, dict[str, str]] = {}
    section = None
    for raw in text.splitlines():
        head = SECTION.match(raw)
        if head:
            section = head.group("name")
            out.setdefault(section, {})
            continue
        match = LINE.match(raw)
        if section is not None and match and not raw.lstrip().startswith(("#", ";")):
            out[section][match.group("key").strip()] = match.group("value").strip()
    return out


def at_corner(options: dict[str, str]) -> bool:
    return all(options.get(k, "").strip() in ("", "0") for k in ("meter.x", "meter.y"))


def letterbox_text(text: str, band: int, moved: set[str] | None = None) -> tuple[str, dict[str, set[str]]]:
    """The pack's `meters.txt` with everything moved down by `band`, and the
    full-frame pictures to pad, each with the keys naming it.

    A section away from the corner, or named in `moved`, is moved by its
    origin; the rest are padded (see the module's docstring)."""
    by_origin = set(moved or ())
    for name, options in sections(text).items():
        if not at_corner(options):
            by_origin.add(name)
    out, pictures = [], {}
    section, seen_y = None, False
    for raw in text.splitlines(keepends=True):
        line = raw.rstrip("\n")
        newline = raw[len(line):]
        head = SECTION.match(line)
        if head:
            if section in by_origin and not seen_y:
                raise LetterboxError(f"[{section}] has no meter.y to move")
            section, seen_y = head.group("name"), False
            out.append(raw)
            continue
        match = LINE.match(line)
        if section is None or not match or line.lstrip().startswith(("#", ";")):
            out.append(raw)
            continue
        key, value = match.group("key").strip(), match.group("value")
        origin = section in by_origin
        if key in FULL_FRAME and value.strip() and not (origin and key in AT_ORIGIN):
            pictures.setdefault(value.strip(), set()).add(key)
        if (key == "meter.y" and origin) or (key in Y_ONLY and not origin) or is_point(key):
            seen_y = seen_y or key == "meter.y"
            if not value.strip() and key != "meter.y":
                out.append(raw)
                continue
            value = shift_value(key, value, band)
            line = f"{match.group('key')}{match.group('eq')}{value}{match.group('end')}"
            out.append(line + newline)
            continue
        out.append(raw)
    if section in by_origin and not seen_y:
        raise LetterboxError(f"[{section}] has no meter.y to move")
    return "".join(out), pictures


def letterbox_spectrum_text(text: str, band: int) -> str:
    """`spectrum.txt` with each section's `spectrum.y` moved down by `band`."""
    out, section, seen = [], None, set()
    for raw in text.splitlines(keepends=True):
        line = raw.rstrip("\n")
        newline = raw[len(line):]
        head = SECTION.match(line)
        if head:
            section = head.group("name")
            out.append(raw)
            continue
        match = LINE.match(line)
        if section is not None and match and not line.lstrip().startswith(("#", ";")) \
                and match.group("key").strip() == SPECTRUM_Y:
            value = shift_value(SPECTRUM_Y, match.group("value"), band)
            out.append(f"{match.group('key')}{match.group('eq')}{value}{match.group('end')}{newline}")
            seen.add(section)
            continue
        out.append(raw)
    missing = set(sections(text)) - seen
    if missing:
        raise LetterboxError(f"spectrum section(s) without spectrum.y: {sorted(missing)}")
    return "".join(out)


def pad_picture(path: Path, size: tuple[int, int], band: int, opaque: bool) -> None:
    """**A background's band is opaque black; an overlay's is transparent.**
    A background drawn with a transparent band would leave whatever the
    previous skin drew showing above and below this one.

    A frame drawn taller than the screen (`McIntosh_tube.jpg`, 1280x743 in
    `1280x720_g5_701_meters`) is cut to the screen first: the rows below it
    were never shown, and left in they would show in the lower band."""
    from PIL import Image

    frame = (size[0], size[1] - 2 * band)
    with Image.open(path) as image:
        image.load()
        if image.size[0] == frame[0] and image.size[1] > frame[1]:
            image = image.crop((0, 0, frame[0], frame[1]))
        if image.size != frame:
            raise LetterboxError(f"{path.name} is {image.size}, not a full {frame[0]}x{frame[1]} frame")
        mode = "RGBA" if image.mode in ("RGBA", "LA", "P") else "RGB"
        fill = (0, 0, 0, 255 if opaque else 0) if mode == "RGBA" else (0, 0, 0)
        canvas = Image.new(mode, size, fill)
        canvas.paste(image.convert(mode), (0, band))
        fmt = "PNG" if path.suffix.lower() == ".png" else "JPEG"
        canvas.save(path, fmt, **({"quality": 95} if fmt == "JPEG" else {}))


def strips(source: Path, text: str, frame: tuple[int, int]) -> set[str]:
    """Sections at the corner whose `bgr`/`fgr` is not a whole frame: they
    cannot be padded, so they are moved by their origin."""
    from PIL import Image

    out = set()
    for name, options in sections(text).items():
        if not at_corner(options):
            continue
        for key in AT_ORIGIN:
            picture = options.get(key, "")
            if picture and (source / picture).is_file():
                with Image.open(source / picture) as image:
                    if image.size != frame:
                        out.add(name)
    return out


def letterbox_pack(source: Path, target: Path, frm: tuple[int, int], to: tuple[int, int]) -> int:
    if frm[0] != to[0] or (to[1] - frm[1]) % 2:
        raise LetterboxError(f"{frm} -> {to} is not a vertical letterbox")
    band = (to[1] - frm[1]) // 2
    meters, spectrum = source / "meters.txt", source / "spectrum.txt"
    if not meters.is_file() and not spectrum.is_file():
        raise LetterboxError("neither meters.txt nor spectrum.txt is in the pack")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    padded = 0
    if meters.is_file():
        text = meters.read_bytes().decode("utf-8", errors="surrogateescape")
        moved, pictures = letterbox_text(text, band, strips(source, text, frm))
        # A picture one section pads and another draws as it is would be
        # wrong for one of them.
        for name, options in sections(text).items():
            origin = name in strips(source, text, frm) or not at_corner(options)
            for key in AT_ORIGIN:
                if origin and options.get(key) in pictures:
                    raise LetterboxError(f"{options[key]} is padded for one section and not for [{name}]")
        for name, roles in sorted(pictures.items()):
            picture = target / name
            if not picture.is_file():
                raise LetterboxError(f"{name} is named by the pack and not in it")
            pad_picture(picture, to, band, opaque=bool(roles & {"bgr.filename", "screen.bgr"}))
        (target / "meters.txt").write_bytes(moved.encode("utf-8", errors="surrogateescape"))
        padded = len(pictures)
    if spectrum.is_file():
        text = spectrum.read_bytes().decode("utf-8", errors="surrogateescape")
        (target / "spectrum.txt").write_bytes(
            letterbox_spectrum_text(text, band).encode("utf-8", errors="surrogateescape"))
    return padded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--from", dest="frm", default="1280x720")
    parser.add_argument("--to", default="1280x800")
    args = parser.parse_args(argv)
    size = lambda s: tuple(int(v) for v in s.lower().split("x"))  # noqa: E731
    try:
        count = letterbox_pack(args.source, args.target, size(args.frm), size(args.to))
    except LetterboxError as exc:
        print(f"ERROR: letterbox {args.source}: {exc}", file=sys.stderr)
        return 1
    print(f"letterbox: {args.source.name} -> {args.target} ({count} full-frame pictures padded)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
