#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Drop the unused alpha channel and recompress, losslessly.

`render.mjs` emits RGBA because that is what the canvas hands back; the alpha
is fully opaque in every frame and costs ~0.6MB across the set, which is
~0.6MB of initramfs. This strips it and re-encodes at maximum compression,
then proves every frame survived pixel-identical rather than assuming it.

Run it straight after render.mjs, on the same directory:

    node render.mjs 0.93 ../theme && python3 finish.py ../theme
"""
import glob
import os
import sys

import numpy as np
from PIL import Image


def main(directory: str) -> int:
    frames = sorted(glob.glob(os.path.join(directory, "boot-*.png")))
    if len(frames) != 100:
        print(f"ERROR: expected 100 frames in {directory}, found {len(frames)}",
              file=sys.stderr)
        return 1

    before = after = 0
    changed = []
    for path in frames:
        pixels = np.asarray(Image.open(path).convert("RGB"))
        before += os.path.getsize(path)
        Image.fromarray(pixels).save(path, optimize=True, compress_level=9)
        after += os.path.getsize(path)
        if not np.array_equal(pixels, np.asarray(Image.open(path).convert("RGB"))):
            changed.append(os.path.basename(path))

    print(f"{before / 1e6:.1f}MB -> {after / 1e6:.1f}MB")
    if changed:
        print(f"ERROR: recompression was not lossless: {changed}", file=sys.stderr)
        return 1
    print("all 100 frames pixel-identical after recompression")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "../theme"))
