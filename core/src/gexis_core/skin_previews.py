# SPDX-License-Identifier: GPL-3.0-or-later
"""**The skin picker's pictures, at the size it shows them** (ADR-0050,
amended 2026-10-03).

George, 2026-10-03, on a phone with the 1920 x 1080 pack: *"Skimming through
skins on phone can get slow after scrolling through a few. It also once
locked up and the picture wasn't loading anymore even though the name was
changing."* Each preview was the skin's own picture, whole: about 530 KB on
average and up to 3.7 MB of PNG, which a phone decodes to 8 MB of pixels and
keeps. So the picker asks for a width, and gets a JPEG of it, made once with
the system's Pillow (the core's own environment has none) and kept here: 154
KB at 960 pixels for the largest, 325 ms to make on a Pi 4, a file read after
that. A picture that cannot be scaled is served as it is.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE = Path("/var/cache/gexis-core/skin-previews")
#: The widths the picker may ask for; anything else is the original.
WIDTHS = (480, 960)
#: Kept at most; the oldest go first.
KEEP = 2000
PYTHON = "/usr/bin/python3"

SCALE = r"""
import os, sys
from PIL import Image
src, dst, width = sys.argv[1], sys.argv[2], int(sys.argv[3])
im = Image.open(src)
im.draft("RGB", (width, width))
im = im.convert("RGB")
im.thumbnail((width, width * 4), Image.LANCZOS)
tmp = dst + ".tmp"
im.save(tmp, "JPEG", quality=82, optimize=True)
os.replace(tmp, dst)
"""

_locks: dict[Path, asyncio.Lock] = {}


def path_for(picture: Path, width: int, cache: Path = CACHE) -> Path:
    """Named by the picture's path, size and time, so a pack that changes a
    picture gets a new one rather than the old one back."""
    stat = picture.stat()
    key = hashlib.sha256(f"{picture}|{stat.st_size}|{stat.st_mtime_ns}".encode()).hexdigest()[:24]
    return cache / f"{key}-{width}.jpg"


def _prune(cache: Path, keep: int) -> None:
    files = sorted(cache.glob("*.jpg"), key=lambda p: p.stat().st_mtime)
    for old in files[:-keep] if len(files) > keep else []:
        old.unlink(missing_ok=True)


async def scaled(picture: Path, width: int, *, cache: Path = CACHE, run=subprocess.run,
                 keep: int = KEEP) -> Path | None:
    """The picture at `width`, made if it is not yet; None if it cannot be."""
    if width not in WIDTHS:
        return None
    try:
        target = path_for(picture, width, cache)
    except OSError:
        return None
    if target.is_file():
        return target
    lock = _locks.setdefault(target, asyncio.Lock())
    async with lock:
        if target.is_file():
            return target

        def make() -> None:
            cache.mkdir(parents=True, exist_ok=True)
            run(["nice", "-n", "10", PYTHON, "-c", SCALE, str(picture), str(target), str(width)],
                capture_output=True, timeout=30, check=True)
            _prune(cache, keep)

        try:
            await asyncio.to_thread(make)
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("skins: no %d px preview of %s (%s)", width, picture, exc)
            return None
        finally:
            _locks.pop(target, None)
    return target if target.is_file() else None
