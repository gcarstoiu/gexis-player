#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Letterbox a 1280x720 PeppyMeter pack into this 1280x800 panel (ADR-0096).

Every full-frame picture is padded with a band above and below, and every
position the pack's sections name is moved down by the same band. Run at image
build time, inside the target, over a pack extracted from a verified zip:

    python3 letterbox.py <pack dir> <out dir> [--from 1280x720] [--to 1280x800]

**Why not move `meter.y` instead.** PeppyMeter's linear meter draws its bars at
`meter.x/y + left.x/y` but adds `meter.x/y` to their bounding box a second time
(`meter.py:106` and `:136`), and the driver presents those boxes - so a shifted
meter origin would redraw each bar 40 px from where it is drawn. With the origin
kept at 0,0 the meter-relative positions are shifted like the rest, and the
script refuses a section whose origin is not 0,0 rather than guess.

The pack's own `meters.txt` is rewritten line for line - comments, order and
CRLF kept - so a diff against upstream shows only the moved numbers.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

#: Meter-relative (linear bars, circular needle origins) - absolute here only
#: because the meter's origin is 0,0, which `letterbox_text` insists on.
Y_ONLY = {"left.y", "right.y", "mono.y", "left.origin.y", "right.origin.y", "mono.origin.y"}
#: An `x,y[,…]` position on the screen.
POINT_SUFFIXES = (".pos", ".center")
POINT_KEYS = {"tonearm.pivot.screen"}
#: Named like a position and are not one: a marker's `pos` is a percentage
#: along the progress bar, and `playinfo.center` is a flag.
NOT_A_POINT = re.compile(r"^(progress\.marker\.\d+\.pos|playinfo(\.text)?\.center)$")
#: Pictures that cover the whole frame and are drawn at the meter's origin.
FULL_FRAME = ("bgr.filename", "fgr.filename", "screen.bgr")

LINE = re.compile(r"^(?P<key>[^=\[#;]+?)(?P<eq>\s*=\s*)(?P<value>.*?)(?P<end>\r?)$")
SECTION = re.compile(r"^\[(?P<name>.+?)\]\s*\r?$")


class LetterboxError(Exception):
    pass


def is_point(key: str) -> bool:
    if NOT_A_POINT.match(key):
        return False
    return key in POINT_KEYS or key.endswith(POINT_SUFFIXES)


def shift_value(key: str, value: str, band: int) -> str:
    if key in Y_ONLY:
        return str(int(value.strip()) + band)
    parts = value.split(",")
    if len(parts) < 2:
        raise LetterboxError(f"{key} = {value!r} is not an x,y position")
    parts[1] = str(int(parts[1].strip()) + band)
    return ",".join(p.strip() if i < 2 else p for i, p in enumerate(parts))


def letterbox_text(text: str, band: int) -> tuple[str, dict[str, set[str]]]:
    """The pack's `meters.txt` with every position moved down by `band`, and
    the full-frame pictures its sections name, each with the keys naming it."""
    out, pictures = [], {}
    section, origin = None, {}
    for raw in text.splitlines(keepends=True):
        line = raw.rstrip("\n")
        newline = raw[len(line):]
        head = SECTION.match(line)
        if head:
            section, origin = head.group("name"), {}
            out.append(raw)
            continue
        match = LINE.match(line)
        if section is None or not match or line.lstrip().startswith(("#", ";")):
            out.append(raw)
            continue
        key, value = match.group("key").strip(), match.group("value")
        if key in ("meter.x", "meter.y"):
            origin[key] = value.strip()
            if value.strip() not in ("", "0"):
                raise LetterboxError(f"[{section}] {key} = {value.strip()}: the meter origin must be 0,0")
        if key in FULL_FRAME and value.strip():
            pictures.setdefault(value.strip(), set()).add(key)
        if key in Y_ONLY or is_point(key):
            if not value.strip():
                out.append(raw)
                continue
            value = shift_value(key, value, band)
            line = f"{match.group('key')}{match.group('eq')}{value}{match.group('end')}"
            out.append(line + newline)
            continue
        out.append(raw)
    return "".join(out), pictures


def pad_picture(path: Path, size: tuple[int, int], band: int, opaque: bool) -> None:
    """**A background's band is opaque black; an overlay's is transparent.**
    A background drawn with a transparent band would leave whatever the
    previous skin drew showing above and below this one."""
    from PIL import Image

    with Image.open(path) as image:
        if image.size != (size[0], size[1] - 2 * band):
            raise LetterboxError(f"{path.name} is {image.size}, not a full {size[0]}x{size[1] - 2 * band} frame")
        mode = "RGBA" if image.mode in ("RGBA", "LA", "P") else "RGB"
        fill = (0, 0, 0, 255 if opaque else 0) if mode == "RGBA" else (0, 0, 0)
        canvas = Image.new(mode, size, fill)
        canvas.paste(image.convert(mode), (0, band))
        fmt = "PNG" if path.suffix.lower() == ".png" else "JPEG"
        canvas.save(path, fmt, **({"quality": 95} if fmt == "JPEG" else {}))


def letterbox_pack(source: Path, target: Path, frm: tuple[int, int], to: tuple[int, int]) -> int:
    if frm[0] != to[0] or (to[1] - frm[1]) % 2:
        raise LetterboxError(f"{frm} -> {to} is not a vertical letterbox")
    band = (to[1] - frm[1]) // 2
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    meters = target / "meters.txt"
    text = meters.read_bytes().decode("utf-8", errors="surrogateescape")
    moved, pictures = letterbox_text(text, band)
    for name, roles in sorted(pictures.items()):
        picture = target / name
        if not picture.is_file():
            raise LetterboxError(f"{name} is named by the pack and not in it")
        pad_picture(picture, to, band, opaque=bool(roles & {"bgr.filename", "screen.bgr"}))
    meters.write_bytes(moved.encode("utf-8", errors="surrogateescape"))
    return len(pictures)


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
