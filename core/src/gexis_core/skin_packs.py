# SPDX-License-Identifier: GPL-3.0-or-later
"""Which skin pack a screen gets, and which ones the device has (ADR-0111).

One pack per device, chosen by the screen: the pack drawn for its exact
size, or else the largest pack that fits inside it without cropping, which
the visualiser centres on black. Packs are `gexis-skins-<W>x<H>` packages
under `/opt/gexis-peppy/packs/<W>x<H>/`; a device that had today's
`gexis-skins` before keeps it, and it counts as the 1280x800 pack
(decision 10).
"""
from __future__ import annotations

import json
from pathlib import Path

PACKS = Path("/opt/gexis-peppy/packs")
#: Today's gexis-skins, kept on the devices that have it (decision 10).
LEGACY = Path("/opt/gexis-peppy/skins")

#: The sizes there are packs for (decision 1; not 3840x2160).
SIZES: tuple[tuple[int, int], ...] = ((1920, 1080), (1280, 800), (1280, 400), (1480, 320), (800, 480))

#: A screen with no screen.env yet is the panel gexis has always had.
DEFAULT_SCREEN = (1280, 800)


#: How many skins each pack holds, which setup names before anything is
#: downloaded. The pack build refuses a pack that disagrees.
COUNTS: dict[str, int] = json.loads((Path(__file__).parent / "skin_counts.json").read_text())


def package(size: tuple[int, int]) -> str:
    return f"gexis-skins-{size[0]}x{size[1]}"


def for_screen(width: int, height: int, sizes=SIZES) -> tuple[int, int] | None:
    """The pack this screen gets: its own size, or the largest that fits
    inside it uncropped (by area); None if none fits. `sizes` narrows the
    choice, to the packs a device has."""
    if (width, height) in sizes:
        return (width, height)
    fitting = [s for s in sizes if s[0] <= width and s[1] <= height]
    # A bar's pack on a Standard screen (or the reverse) would leave most of
    # it black: the screen's own family first, then the largest by area.
    same = [s for s in fitting if family(*s) == family(width, height)]
    pool = same or fitting
    return max(pool, key=lambda s: s[0] * s[1]) if pool else None


def family(width: int, height: int) -> str:
    """ADR-0109's families, by aspect (lib/family.svelte.js: the same 2.4)."""
    return "bar" if width / height >= 2.4 else "standard"


def installed(packs: Path = PACKS, legacy: Path = LEGACY) -> list[tuple[int, int]]:
    """The packs on this device, by size."""
    out = []
    for manifest in sorted(packs.glob("*/pack.json")):
        try:
            w, h = (int(n) for n in json.loads(manifest.read_text())["size"].split("x"))
        except (OSError, ValueError, KeyError):
            continue
        out.append((w, h))
    if legacy.is_dir() and DEFAULT_SCREEN not in out:
        out.append(DEFAULT_SCREEN)
    return out


def root_of(size: tuple[int, int], packs: Path = PACKS, legacy: Path = LEGACY) -> Path | None:
    """Where a size's skins are: its pack, or the kept gexis-skins."""
    own = packs / f"{size[0]}x{size[1]}"
    if (own / "pack.json").exists():
        return own
    if size == DEFAULT_SCREEN and legacy.is_dir():
        return legacy
    return None


def current(screen: tuple[int, int] | None = None, packs: Path = PACKS,
            legacy: Path = LEGACY) -> tuple[Path, str] | None:
    """**The skins the visualiser draws now**: the installed pack this screen
    uses, as (its root, its resolution folder) - the root holding one folder
    per source, each with `templates{,_spectrum}/<resolution>`.

    The screen's own pack when it is in; otherwise, while that one is still
    being fetched after a change of screen, the installed pack that fits best
    (decision 2: the old one shows, letterboxed), and failing that whichever
    the device has. None when it has none.
    """
    have = installed(packs, legacy)
    if not have:
        return None
    width, height = screen or screen_size()
    size = for_screen(width, height, tuple(have)) or have[0]
    root = root_of(size, packs, legacy)
    return (root, f"{size[0]}x{size[1]}") if root else None


def plan(screen: tuple[int, int], have: list[tuple[int, int]]) -> tuple[tuple[int, int] | None, list[tuple[int, int]]]:
    """(the pack to install, the packs to remove once it is in) for this
    screen. One pack per device (decision 2)."""
    want = for_screen(*screen)
    install = want if want is not None and want not in have else None
    remove = [s for s in have if s != want]
    return install, remove


#: What the updater last said about a pack (gexis-update pack-install).
PACK_STATUS = Path("/var/lib/gexis/updates/pack.json")


def status(path: Path = PACK_STATUS, packs: Path = PACKS, legacy: Path = LEGACY) -> dict:
    """The pack's download line, in the shape ADR-0100's rows read
    (Settings' `downloadLine`): state, label, where from, and the share."""
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        doc = {}
    have = installed(packs, legacy)
    label = f"the {have[0][0]} × {have[0][1]} skins" if have else "the skins"
    state = doc.get("state")
    if state in ("downloading", "installing"):
        size = (doc.get("package") or "").removeprefix("gexis-skins-").replace("x", " × ")
        return {"state": state, "label": f"the {size} skins" if size else label,
                "from": "the release", "share": doc.get("progress")}
    if state == "failed":
        return {"state": "failed", "label": label, "from": "the release",
                "error": f"The skins were not installed: {doc.get('message', 'see the log')}"}
    if have:
        return {"state": "installed", "label": label, "from": "the release"}
    return {"state": "absent", "label": "the skins for this screen", "from": "the release"}


def screen_size(env: Path = Path("/etc/gexis/screen.env")) -> tuple[int, int]:
    """The attached screen's size (ADR-0109's screen.env), or the panel's."""
    try:
        fields = dict(l.split("=", 1) for l in env.read_text().splitlines() if "=" in l and not l.startswith("#"))
        return int(fields["GEXIS_SCREEN_WIDTH"]), int(fields["GEXIS_SCREEN_HEIGHT"])
    except (OSError, KeyError, ValueError):
        return DEFAULT_SCREEN
