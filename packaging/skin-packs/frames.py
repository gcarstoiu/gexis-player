#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""**Every skin of a pack, drawn whole and drawn again** (Finding 131).

    frames.py <pack root> <W>x<H> <engines dir> [--driver <path>] [--only <n>] [--json <out>]

`<pack root>` is an installed pack's directory (`.../packs/<W>x<H>`), and
`<engines dir>` the one holding `peppymeter/` (what gexis-peppy-engines
installs as /opt/gexis-peppy). Headless: SDL's dummy driver, the engine's
noise source. For each skin, through the driver that ships - its own
`load_corpus` and `Rotation`, so what is checked is what draws on a player:

1. **It starts**: the meter is built and its first frame drawn.
2. **Its picture is the pack's size**, or noted: a `screen.bgr` of another
   size is drawn from the corner on black (1480x310 in the 1480x320 pack,
   1920x1115 in the 1920x1080 one, 2026-10-20).
3. **A lost frame does not come back by itself**: the window is filled with
   a colour no skin uses, two seconds of needle frames are run, and the
   share of the frame they bring back is recorded - what PeppyMeter's own
   redraws restore after a window loses its picture.
4. **`Rotation.refresh()` brings all of it back**: after the loss, the
   repaint must give exactly the frame the skin started with.

5. **Its start paints every pixel**: started over a colour no skin uses
   (confirmed with a second), nothing of it may be left.

Exits 1 if any skin fails 1, 4 or 5; 2 is a note and 3 a measurement. A spectrum is not
drawn here (the engine is meters only): its region is part of the skin's
picture in every pack measured.
"""
from __future__ import annotations

import argparse
import configparser
import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

#: The colour a lost frame is filled with: one no skin in the packs measured
#: uses (pure magenta is in 69G5_Boombox).
LOST = (3, 254, 1)
#: A second one, to tell a pixel left unpainted from one a skin paints LOST.
OTHER = (251, 2, 249)
#: Needle frames run after the loss: two seconds at the engine's 30 a second.
NEEDLE_FRAMES = 60

HERE = Path(__file__).resolve().parent
DRIVER = HERE.parents[1] / "image/stage-gexis/05-peppy/files/gexis-peppy-driver.py"


def load_driver(path: Path):
    spec = importlib.util.spec_from_file_location("gexis_peppy_driver", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def engine_config(engines: Path, base_folder: Path, meter_folder: str, size: tuple[int, int], work: Path) -> Path:
    """The engine's own config.txt, pointed at this pack, headless and fed by
    noise. Written into a copy of the engine directory, since the engine
    reads ./config.txt."""
    meter_dir = work / "peppymeter"
    meter_dir.mkdir(parents=True)
    for item in (engines / "peppymeter").iterdir():
        if item.name != "config.txt":
            (meter_dir / item.name).symlink_to(item)
    config = configparser.ConfigParser()
    config.optionxform = str
    shipped = engines / "peppymeter" / "config.txt"
    if shipped.is_file():
        config.read(shipped)
    else:
        config.read(DRIVER.parent / "peppy-meter.txt")
    config["current"]["meter"] = "random"
    config["current"]["base.folder"] = str(base_folder)
    config["current"]["meter.folder"] = meter_folder
    config["current"]["screen.width"] = str(size[0])
    config["current"]["screen.height"] = str(size[1])
    config["current"]["use.logging"] = "False"
    config["sdl.env"]["video.driver"] = "dummy"
    config["data.source"]["type"] = "noise"
    with open(meter_dir / "config.txt", "w") as out:
        config.write(out)
    return meter_dir


class NoSpectrum:
    """The spectrum half, absent: meters only."""

    def follow(self, skin, home=None) -> None:
        self.active = False


def share_lost(window: pygame.Surface, started: pygame.Surface | None = None) -> float:
    """The share of the window still the loss colour - not counting pixels
    the skin itself paints that colour, when its started frame is given."""
    lost = pygame.mask.from_threshold(window, LOST, (1, 1, 1, 255))
    if started is not None:
        lost.erase(pygame.mask.from_threshold(started, LOST, (1, 1, 1, 255)), (0, 0))
    w, h = window.get_size()
    return lost.count() / (w * h)


def indicator_boxes(meter) -> list[pygame.Rect]:
    """A linear meter's indicators, where they are drawn: the bar's first
    sliver is a pixel wider or narrower after a restart, which is the
    indicator's state, not the picture. A circular meter gets none - at rest
    its needles are drawn exactly where they started."""
    if getattr(meter, "meter_type", None) != "linear":
        return []
    boxes = []
    for component in getattr(meter, "components", []) or []:
        if component is None or component is meter.bgr or component is meter.fgr:
            continue
        content = getattr(component, "content", None)
        image = content[1] if isinstance(content, tuple) and len(content) > 1 else None
        if image is not None:
            boxes.append(pygame.Rect(int(component.content_x), int(component.content_y), *image.get_size()))
    return boxes


def differing_outside(a: pygame.Surface, b: pygame.Surface, boxes: list[pygame.Rect]) -> int:
    """Pixels that differ between `a` and `b` outside every box."""
    from PIL import Image, ImageChops, ImageDraw

    size = a.get_size()
    one = Image.frombytes("RGB", size, pygame.image.tobytes(a, "RGB"))
    two = Image.frombytes("RGB", size, pygame.image.tobytes(b, "RGB"))
    diff = ImageChops.difference(one, two).convert("L").point(lambda v: 255 if v else 0)
    draw = ImageDraw.Draw(diff)
    for box in boxes:
        draw.rectangle([box.left, box.top, box.right - 1, box.bottom - 1], fill=0)
    return diff.histogram()[255]


def check_pack(root: Path, size: tuple[int, int], engines: Path, driver_path: Path, only: int | None,
               dump: Path | None = None, show: set[str] | None = None) -> dict:
    driver = load_driver(driver_path)
    meter_folder = f"{size[0]}x{size[1]}"
    # Any of the pack's template directories will do for the engine's own
    # base folder: `load_corpus` reads every directory beside it.
    first = next(iter(sorted(root.glob(f"*/templates/{meter_folder}/meters.txt"))), None)
    if first is None:
        raise SystemExit(f"{root}: no */templates/{meter_folder}/meters.txt")
    base_folder = first.parent.parent
    work = Path(tempfile.mkdtemp(prefix="frames-"))
    meter_dir = engine_config(engines, base_folder, meter_folder, size, work)
    sys.path[:0] = [str(meter_dir), str(driver_path.parent)]
    os.chdir(meter_dir)

    skins, homes = driver.load_corpus(base_folder, meter_folder)
    names = sorted(skins)[: only or None]

    from peppymeter import Peppymeter

    peppy = Peppymeter(standalone=True, timer_controlled_random_meter=False, quit_pygame_on_stop=False)
    peppy.init_display()
    peppy.meter.random_meter = False
    peppy.meter.list_meter = False
    window = pygame.display.get_surface()
    # As the driver's main(): the engine parsed one directory, the others are
    # adopted into the same config so the factory builds from any of them.
    corpus = base_folder / meter_folder
    for directory in {home for home in homes.values()} - {corpus}:
        driver.adopt_sections(peppy.util.meter_config, directory)

    rotation = driver.Rotation(peppy, skins, NoSpectrum(), None, homes, driver.Selection())
    rotation.prepare_next = lambda name=None: None  # one skin at a time, built below
    results = []
    for name in names:
        row = {"skin": name, "home": str(homes.get(name, "")), "problems": []}
        results.append(row)
        skin = skins[name]
        picture = (skin.get("screen.bgr") or "").strip()
        if picture and name in homes:
            path = homes[name] / picture
            try:
                found = pygame.image.load(str(path)).get_size()
            except (pygame.error, OSError) as exc:
                row["problems"].append(f"screen.bgr {picture!r} does not load: {exc}")
            else:
                if found != size:
                    # Drawn from the corner on black, by the engine and the
                    # text layer alike: a note for the pack, not a fault.
                    row["notes"] = [f"screen.bgr {picture!r} is {found[0]}x{found[1]}, not the pack's {meter_folder}"]
        started = time.monotonic()
        # Started over the loss colour: whatever a skin's start leaves
        # unpainted shows as it, where on a player it would be the skin before.
        window.fill(LOST)
        try:
            rotation._prepare(name)
            rotation.switch(name)
        except Exception as exc:  # noqa: BLE001 - one skin, recorded
            row["problems"].append(f"does not start: {type(exc).__name__}: {exc}")
            continue
        row["start_s"] = round(time.monotonic() - started, 3)
        if share_lost(window) > 0:
            # Confirmed with a second colour: a skin may paint the first.
            first_try = pygame.mask.from_threshold(window, LOST, (1, 1, 1, 255))
            window.fill(OTHER)
            rotation._prepare(name)
            rotation.switch(name)
            both = first_try.overlap_mask(pygame.mask.from_threshold(window, OTHER, (1, 1, 1, 255)), (0, 0))
            if both.count():
                w, h = window.get_size()
                row["problems"].append(f"its start leaves {both.count() / (w * h):.2%} of the frame unpainted")
        started_frame = window.copy()

        # A lost frame, painted again at once: the needles have not moved, so
        # the repaint must be the started frame exactly.
        window.fill(LOST)
        refresh = getattr(rotation, "refresh", None)
        if refresh is None or not refresh():
            row["problems"].append("a lost frame is never painted again (no refresh())")
            continue
        again = window.copy()
        if share_lost(again, started_frame) > 0:
            row["problems"].append(f"refresh() left {share_lost(again, started_frame):.4%} of the frame unpainted")
        elif (outside := differing_outside(again, started_frame, indicator_boxes(rotation.vumeter.meter))):
            row["problems"].append(f"refresh() differs from the started frame ({outside} px)")
            if dump is not None:
                safe = name.replace("/", "_")
                pygame.image.save(started_frame, str(dump / f"{safe}.started.png"))
                pygame.image.save(again, str(dump / f"{safe}.again.png"))

        # Lost again, and left to the engine: what two seconds of needle
        # frames bring back by themselves - the screen before this fix.
        window.fill(LOST)
        meter = rotation.vumeter.meter
        for _ in range(NEEDLE_FRAMES):
            meter.run()
        row["back_by_itself"] = round(1 - share_lost(window, started_frame), 4)
        if show is not None and name in show:
            safe = name.replace("/", "_")
            pygame.image.save(started_frame, str(dump or Path(".")) + f"/{safe}.started.png")
            pygame.image.save(window, str(dump or Path(".")) + f"/{safe}.lost.png")
    return {"pack": str(root), "size": meter_folder, "skins": len(names), "results": results}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", type=Path)
    parser.add_argument("size")
    parser.add_argument("engines", type=Path)
    parser.add_argument("--driver", type=Path, default=DRIVER)
    parser.add_argument("--only", type=int)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--dump", type=Path, help="save the two frames of a skin whose repaint differs")
    parser.add_argument("--show", action="append", help="save this skin's started and lost frames (repeatable)")
    args = parser.parse_args(argv)
    w, h = (int(v) for v in args.size.lower().split("x"))
    started = time.monotonic()
    report = check_pack(args.root.resolve(), (w, h), args.engines.resolve(), args.driver.resolve(), args.only,
                        args.dump, set(args.show or []))
    report["seconds"] = round(time.monotonic() - started, 1)
    failed = [r for r in report["results"] if r["problems"]]
    back = [r["back_by_itself"] for r in report["results"] if "back_by_itself" in r]
    if args.json:
        args.json.write_text(json.dumps(report, indent=1))
    for row in failed:
        for problem in row["problems"]:
            print(f"{row['skin']}: {problem}")
    for row in report["results"]:
        for note in row.get("notes", []):
            print(f"{row['skin']}: note: {note}")
    if back:
        print(f"after a lost frame, needle redraws alone brought back {min(back):.0%}-{max(back):.0%} "
              f"of it (median {sorted(back)[len(back) // 2]:.0%})")
    print(f"{report['size']}: {report['skins']} skins, {len(failed)} with a problem, {report['seconds']} s")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        code = main()
    except BaseException:  # noqa: BLE001 - reported, then out
        import traceback

        traceback.print_exc()
        code = 2
    sys.stdout.flush()
    # The engine's data-source thread never ends; out for real, as the driver.
    os._exit(code)
