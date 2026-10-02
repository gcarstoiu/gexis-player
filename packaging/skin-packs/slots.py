#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Measure every skin's badge slot in an assembled pack (ADR-0111).

    slots.py <pack root> <W>x<H> <reasons.json> [<reviewed badge-slots.json>]
        ->  <pack root>/badge-slots.json; each skin's outcome in <reasons.json>

**Why.** A skin declares the renderer's mark box (`playinfo.type.pos`,
`.dimension`), and upstream drew that box off-centre in a wider slot: it held
a format icon with the sample rate beside it, and the sample rate is never
drawn here. image/stage-gexis/05-peppy/files/badge-slots.json fixed it for
1280x800's first 99 skins, by name; every pack measures its own here, the
same way: **flood-fill the composed background from the middle of the
declared box**, and take what was filled.

The composed background is what the panel shows under the badge:
`screen.bgr` over the whole screen, then the meter's `bgr.filename` and
`fgr.filename` at its origin (the order MotionLayer and the engine use).

A measured slot is kept only when it is clearly the box's own window:
- it contains the declared box, give or take 6 px, and has a badge window's
  shape (MAX_HEIGHT, MAX_WIDTH - beyond that the fill ran over artwork);
- no text the skin places runs into it (a slot that also holds the time or
  a title is the skin's layout, not a badge window - the shipped table left
  those alone too, and so does every skin it lists as left alone).
When the fill around the box fails its shape, the fill is read again around
the **mark** the renderer draws there (BADGE_FILL of the box's shorter side,
square, centred): kept when it has room for the mark and is a window for a
mark that size (MARK_WIDE, MARK_TALL), with no text the skin places in it -
George, 2026-10-02, on the logo-centring sweep. NOT_A_WINDOW and SET_ASIDE
name the skins whose fill was checked by eye and is not the window.
Otherwise the skin keeps its declared box, and the summary says why.

PIL only: the package builder has no numpy.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from assemble import TEMPLATES, blocks, options, read_text  # noqa: E402

#: How far a pixel may be from the seed's colour and still be the slot.
THRESHOLD = 28
#: The declared box may poke out of the measured slot by this much.
SLACK = 6
#: **A badge window is a strip around the box**: every slot in the reviewed
#: table is 0.8-1.6 times the box high and 1.4-5.8 times it wide. A fill
#: taller or wider than this ran over the skin's artwork instead.
MAX_HEIGHT = 1.6
MAX_WIDTH = 6.0
#: Keys whose position is text drawn by the skin.
TEXT = ("playinfo.title.pos", "playinfo.artist.pos", "playinfo.album.pos", "time.remaining.pos",
        "time.elapsed.pos", "time.total.pos", "playinfo.ticker.pos")


def point(value: str | None) -> tuple[int, int] | None:
    try:
        parts = [p.strip() for p in (value or "").split(",")]
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return None


def load(directory: Path, name: str | None) -> Image.Image | None:
    name = (name or "").strip()
    if not name or not (directory / name).is_file():
        return None
    try:
        with Image.open(directory / name) as image:
            return image.convert("RGBA")
    except OSError:
        return None


def composed(skin: dict[str, str], directory: Path, size: tuple[int, int]) -> Image.Image:
    canvas = Image.new("RGBA", size, (0, 0, 0, 255))
    screen = load(directory, skin.get("screen.bgr"))
    if screen is not None:
        if screen.size != size:
            screen = screen.resize(size, Image.BILINEAR)
        canvas.alpha_composite(screen)
    origin = point(f"{skin.get('meter.x') or 0},{skin.get('meter.y') or 0}") or (0, 0)
    for key in ("bgr.filename", "fgr.filename"):
        picture = load(directory, skin.get(key))
        if picture is not None and origin[0] >= 0 and origin[1] >= 0:
            canvas.alpha_composite(picture, origin)
    return canvas.convert("RGB")


#: The renderer draws the mark at this share of its field (BADGE_FILL).
BADGE_FILL = 0.8
#: A window around the mark itself: at most this many marks wide and tall.
MARK_WIDE = 6
MARK_TALL = 3


def measure(skin: dict[str, str], directory: Path, size: tuple[int, int]):
    """(slot or None, why): the window around the declared box, or failing
    that the window around the mark itself (George, 2026-10-02, on the
    sweep's recommendations). Both fills start where the mark is drawn - the
    middle of the box - but the second asks only that the window hold the
    mark, as the renderer draws it, and be a window for a mark of that size:
    a box that reserved room for the sample rate beside the mark can be
    wider or taller than the window the mark sits in."""
    slot, why = measure_box(skin, directory, size)
    if slot is not None or not why.startswith("the fill"):
        return slot, why
    again, why_again = measure_mark(skin, directory, size)
    if again is not None:
        return again, "measured around the mark"
    return None, f"{why}; around the mark: {why_again}"


def fill(picture: Image.Image, seed: tuple[int, int], near: tuple[int, int, int, int]):
    """The bounding box the fill from `seed` covers inside `near`, and
    whether it reached the edge of `near` (more than any window)."""
    crop = picture.crop(near)
    filled = crop.copy()
    local = (seed[0] - near[0], seed[1] - near[1])
    marker = (255, 0, 254) if crop.getpixel(local) != (255, 0, 254) else (0, 255, 1)
    ImageDraw.floodfill(filled, local, marker, thresh=THRESHOLD)
    changed = ImageChops.difference(filled, crop).getbbox()
    if changed is None:
        return None, False
    x0, y0, x1, y1 = changed[0] + near[0], changed[1] + near[1], changed[2] + near[0], changed[3] + near[1]
    open_ = (x0 == near[0] and near[0] > 0) or (y0 == near[1] and near[1] > 0) or \
        (x1 == near[2] and near[2] < picture.width) or (y1 == near[3] and near[3] < picture.height)
    return (x0, y0, x1, y1), open_


def badge_box(skin: dict[str, str]):
    pos, dim = point(skin.get("playinfo.type.pos")), point(skin.get("playinfo.type.dimension")) or (50, 50)
    if pos is None:
        return None, None, None
    box = (pos[0], pos[1], pos[0] + dim[0], pos[1] + dim[1])
    return box, dim, ((box[0] + box[2]) // 2, (box[1] + box[3]) // 2)


def measure_box(skin: dict[str, str], directory: Path, size: tuple[int, int]):
    """The window around the declared box."""
    box, dim, seed = badge_box(skin)
    if box is None:
        return None, "no badge box"
    if not (0 <= seed[0] < size[0] and 0 <= seed[1] < size[1]):
        return None, "the box is off the screen"
    # Filled inside a neighbourhood of the box only: a fill that reaches its
    # edge is beyond any slot this keeps, and stopping there keeps PIL's
    # pure-Python fill from crawling over a whole open background.
    near = (max(0, box[0] - 5 * dim[0]), max(0, box[1] - 3 * dim[1]),
            min(size[0], box[2] + 5 * dim[0]), min(size[1], box[3] + 3 * dim[1]))
    found, open_ = fill(composed(skin, directory, size), seed, near)
    if found is None:
        return None, "nothing to fill"
    x0, y0, x1, y1 = found
    if open_:
        return None, f"the fill [{x0}, {y0}, {x1}, {y1}] runs into open background"
    if x0 > box[0] + SLACK or y0 > box[1] + SLACK or x1 < box[2] - SLACK or y1 < box[3] - SLACK:
        return None, f"the fill [{x0}, {y0}, {x1}, {y1}] is smaller than the box"
    if (y1 - y0) > MAX_HEIGHT * dim[1] or (x1 - x0) > MAX_WIDTH * dim[0]:
        return None, f"the fill [{x0}, {y0}, {x1}, {y1}] is not a badge window"
    for key in TEXT:
        p = point(skin.get(key))
        # A line starting left of the slot on its rows runs into it: the
        # slot is then the skin's display, shared with the time or a title.
        if p is not None and y0 - dim[1] // 2 <= p[1] < y1 and x0 - MAX_WIDTH * dim[0] <= p[0] < x1:
            return None, f"{key} shares the window"
    if (x0, y0, x1, y1) == box:
        return None, "the slot is the box"
    return [x0, y0, x1, y1], "measured"


def measure_mark(skin: dict[str, str], directory: Path, size: tuple[int, int]):
    """The window around the mark: the renderer's marks are square, at most
    BADGE_FILL of the box's shorter side, centred in the box. A window for it
    has room for it and is no more than MARK_WIDE marks wide and MARK_TALL tall -
    the sweep's measure of a window, against the mark rather than the box."""
    box, dim, seed = badge_box(skin)
    side = max(1, int(min(dim) * BADGE_FILL))
    mark = (seed[0] - side // 2, seed[1] - side // 2, seed[0] - side // 2 + side, seed[1] - side // 2 + side)
    near = (max(0, mark[0] - MARK_WIDE * side), max(0, mark[1] - MARK_TALL * side),
            min(size[0], mark[2] + MARK_WIDE * side), min(size[1], mark[3] + MARK_TALL * side))
    found, open_ = fill(composed(skin, directory, size), seed, near)
    if found is None:
        return None, "nothing to fill"
    x0, y0, x1, y1 = found
    if open_:
        return None, "open background"
    # Room for the mark, not the mark where the box put it: a box drawn
    # half off its window is the misplacement this corrects.
    if (x1 - x0) < side - 2 or (y1 - y0) < side - 2:
        return None, "smaller than the mark"
    if (x1 - x0) > MARK_WIDE * side or (y1 - y0) > MARK_TALL * side:
        return None, "a display, not a window for the mark"
    for key, value in skin.items():
        p = point(value) if key.endswith(".pos") and key.startswith(("playinfo.", "time.")) else None
        if p is not None and key not in ("playinfo.type.pos", "playinfo.samplerate.pos") \
                and x0 <= p[0] < x1 and y0 <= p[1] < y1:
            return None, f"{key} is in the window"
    return [x0, y0, x1, y1], "measured around the mark"


#: **The slots George reviewed** (image/stage-gexis/05-peppy/files/
#: badge-slots.json): 1280x800, measured on gexis-skins' skins and checked
#: tile by tile, nine read by eye where a fill leaked or stopped short. The
#: same skins, the same pictures and the same pixels are in these folders of
#: the 1280x800 pack, so their reviewed slot stands over a fresh fill.
REVIEWED_FOLDERS = {
    "gelo5", "gelo5-420", "stock", "1280x720_g5_710_Turntables", "1280x720_g5_711_Tape_Recorder",
    "1280x720_g5_712_Cassette", "1280x800_t1800_pack7",
}


#: The skins that table names as left alone on purpose - a slot that also
#: holds the time, or the logo (its `_about`).
LEFT_ALONE = {
    "48G5_Vertical blue", "28G5_Technisc_Black", "29G5_Technisc_Silver", "168G5_Philips Cassette",
    "163G5_TEAC cassette", "159G5_Technics Rec", "145G5_01_McIntosh MTI100", "145G5_02_McIntosh MTI100",
    "145G5_03_McIntosh MTI100", "148G5_01_Reloop RL7000", "148G5_02_Reloop RL7000", "148G5_03_Reloop RL7000",
    "144G5_01_Naim Turntable", "144G5_02_Naim Turntable", "144G5_03_Naim Turntable", "170G5_SonyK770 cassette",
    "06G5_McIntosh", "08G5_McIntosh Hybrid",
}


#: Measurements George had checked by eye and set aside (2026-10-02: "Going
#: with whatever recommendation you might have for the doubtful logos"): the
#: fill ran under the art (Streamer CD), over open wood (Eher, PipeWood) or
#: into a neighbouring control (LG Syitren). They keep their declared box.
#: Keyed "<size>/<folder>/<skin>".
SET_ASIDE = {
    "1280x800/1280x720_g5_444_rotate/18G5_Streamer CD",
    "1480x320/gelo5/45G5_Eher only meters",
    "1280x400/gelo5-220/111G5_PipeWood Spectrum",
    "1920x1080/1920x1080_g5_FanartCD/305G5_LG_Syitren Fanart",
    # The sweep, 2026-10-02: its fill is not the window the mark shows in,
    # from the box or from the mark - left on its box as George asked.
    "1280x800/1280x720_g5_FanarTurntable/359G5_Turn Black_Fanart",
    # Its fill from the mark is accepted by the shape rules, but the
    # before/after sheet puts the mark on the artwork - a knob, a legend, the
    # maker's logo - so it stays on its box, as Turn Black_Fanart does.
    "1280x400/gelo5-220/112G5_Osciloscope S+M",
    "1280x400/gelo5/13G5_Onkyo 5570",
    "1280x800/1280x800_g5_420_meters/01G5_Accuphase",
    "1920x1080/gelo5/05G5_Accuphase",
    "1280x800/gelo5/11G5_Kenwood Rev",
}


#: The sweep's windows that are a picture, not a place for the mark (George,
#: 2026-10-02): a fill from the mark would centre it on artwork. They keep
#: their declared box. Keyed "<size>/<folder>/<skin>".
NOT_A_WINDOW = {
    "1280x800/1280x720_g5_705_meters/99G5_Merc",
    "1920x1080/1920x1080_g5_705_meters/99G5_Merc",
    "1920x1080/1920x1080_g5_711_Tape_Recorder/157G5_Revox B77",
    "1280x800/gelo5/66G5_HelixOne",
    "1920x1080/gelo5/60G5_HelixOne",
}
#: Reviewed slots measured afresh (George, 2026-10-02): the sweep found the
#: mark about 50 px left of the window's centre. The table's other slots stand.
REMEASURED = {"black-blue", "black-blue-spectrum"}


def main(argv: list[str]) -> int:
    root, size_text = Path(argv[0]), argv[1]
    size = tuple(int(v) for v in size_text.split("x"))
    reviewed = {}
    if len(argv) > 3 and size_text == "1280x800":
        reviewed = json.loads(Path(argv[3]).read_text()).get("slots", {})
    slots, why = {}, {}
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        for kind in TEMPLATES:
            meters = folder / kind / size_text / "meters.txt"
            if not meters.is_file():
                continue
            for name, lines in blocks(read_text(meters)):
                if not name:
                    continue
                if f"{size_text}/{folder.name}/{name}" in NOT_A_WINDOW:
                    slot, reason = None, "its window is artwork (George, 2026-10-02)"
                elif folder.name in REVIEWED_FOLDERS and name in reviewed and name not in REMEASURED:
                    slot, reason = list(reviewed[name][:4]), "reviewed (the shipped table)"
                elif folder.name in REVIEWED_FOLDERS and name in LEFT_ALONE and reviewed:
                    slot, reason = None, "left alone on review (the shipped table)"
                elif f"{size_text}/{folder.name}/{name}" in SET_ASIDE:
                    slot, reason = None, "set aside on review (George, 2026-10-02)"
                else:
                    slot, reason = measure(options(lines), meters.parent, size)
                key = f"{folder.name}/{name}"
                if slot is not None:
                    slots[key] = slot
                why[key] = reason
    (root / "badge-slots.json").write_text(json.dumps({
        "_about": "Each skin's badge slot, measured at package build by flood-filling the "
                  "composed background from the middle of the skin's playinfo.type box "
                  "(packaging/skin-packs/slots.py). Keyed <folder>/<skin>; [x0, y0, x1, y1] in "
                  "this pack's pixels. A skin absent here keeps its declared box.",
        "slots": slots,
    }, indent=1, sort_keys=True) + "\n")
    counts: dict[str, int] = {}
    for reason in why.values():
        counts[reason.split(" [")[0] if reason.startswith("the fill") else reason] = \
            counts.get(reason.split(" [")[0] if reason.startswith("the fill") else reason, 0) + 1
    print(f"badge slots {size_text}: {len(slots)} measured;",
          ", ".join(f"{n} {r}" for r, n in sorted(counts.items(), key=lambda x: -x[1]) if r != "measured"))
    if len(argv) > 2 and argv[2] != "-":   # each skin's outcome, for review; not shipped
        Path(argv[2]).write_text(json.dumps(why, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
