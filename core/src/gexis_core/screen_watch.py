# SPDX-License-Identifier: GPL-3.0-or-later
"""**A new screen, noticed at start** (ADR-0109, amended 2026-10-03; George:
*"Upon boot couldn't we detect that a new display was connected and give the
user the choice to keep the new resolution?"*, then all three decisions as
recommended).

When a screen is kept, what it reported is remembered: EDID maker, name and
preferred mode. At each start what is attached is compared with that, and a
different screen is asked about - by name when a tested model is recognised,
by its size otherwise. **Not the touch controller**: a USB stick plugged in
would read as a new screen; it still counts toward recognising a model
(`screen_detect.suggest`). "Not now" is remembered for that screen. A player
that has nothing remembered yet - one updating to this - takes what is
attached as what was kept, and asks nothing.

**Every new screen is switched to before the panel starts** (amended again
2026-10-04; George, after the bars: *"we know the screen resolution so we
should render in that resolution already, asking the user whether to keep it
or not. If the display gets garbled up, after the 2 minutes we restart with
the previous setting in place. Also for resolutions like the bar's we should
put it into landscape automatically ... these apply on the go changes and not
when the setup takes care of things"*). `gexis-screen-check.service` runs
`at_start` before the core and the panel: the recognised model, else the one
listed model of that size, else the screen laid out from its own mode
(`screens.other`) - and the panel's first frame is the new screen's, with
Keep. A change of the kernel's mode (a bar's `video=`) restarts the device
first, before anything is drawn.

**Formerly: a recognised screen is switched to, not asked about** (amended 2026-10-04;
George: *"if we know that another display was connected why not show directly
in the correct resolution and ask the user to keep it?"*). The core does the
switching; this remembers that it was **tried**, so a switch that went back
- not kept, or no touch - is asked about at the next start instead of tried
again, and again.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from . import screen_detect, screens

logger = logging.getLogger(__name__)

STATE = Path("/var/lib/gexis/screen-seen.json")


def key(seen: screen_detect.Seen) -> list | None:
    """What makes a screen this screen, or None when nothing readable is
    attached (no EDID: nothing to tell one screen from another by)."""
    if not seen.connected or seen.preferred is None or not (seen.edid_maker or seen.edid_name):
        return None
    return [seen.edid_maker, seen.edid_name, f"{seen.preferred[0]}x{seen.preferred[1]}"]


def _read(path: Path) -> dict:
    try:
        doc = json.loads(path.read_text())
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(doc: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=1))
    tmp.replace(path)


def kept(seen: screen_detect.Seen, path: Path = STATE) -> None:
    """The screen attached now is the one in use."""
    k = key(seen)
    if k is None:
        return
    doc = _read(path)
    doc["kept"] = k
    # A screen kept is a fresh start: the next one recognised is switched to.
    doc.pop("tried", None)
    _write(doc, path)


def tried(k: list, path: Path = STATE) -> None:
    """A recognised screen was switched to without asking."""
    doc = _read(path)
    doc["tried"] = [*[t for t in doc.get("tried", []) if t != k], k]
    _write(doc, path)


def not_now(k: list, path: Path = STATE) -> None:
    doc = _read(path)
    declined = [d for d in doc.get("declined", []) if d != k]
    doc["declined"] = [*declined, k]
    _write(doc, path)


def question(seen: screen_detect.Seen, *, headless: bool, path: Path = STATE) -> dict | None:
    """What to ask about the screen attached now, or None."""
    if headless:
        return None
    k = key(seen)
    if k is None:
        return None
    doc = _read(path)
    if doc.get("kept") is None:
        # Updating to this: what is attached is what was kept.
        kept(seen, path)
        return None
    if k == doc["kept"] or k in doc.get("declined", []):
        return None
    model = screen_detect.suggest(seen)
    logger.info("screen: a different screen is attached (%s, was %s)", k, doc["kept"])
    return {
        "key": k,
        "size": k[2],
        "label": model.label if model else None,
        "name": f"{model.maker} {model.model}" if model else None,
        # Switched to once already and not kept: ask this time.
        "tried": k in doc.get("tried", []),
    }


def target(seen: screen_detect.Seen) -> screens.Screen:
    """What a new screen is switched to: the recognised model; else, for a
    bar, the one listed bar of exactly its mode; else itself, from its own mode.
    Several listed models of one size (1920 x 1080 has dozens) name none of
    them - the size alone does not say which."""
    model = screen_detect.suggest(seen)
    if model is not None:
        return model
    width, height = seen.preferred
    # **The mode as the panel reports it, orientation and all** (found in
    # the tests, 2026-10-04): a 1920 x 1200 monitor matched by size alone the
    # one listed model of that size - a Seeed 10.1" that is a 1200 x 1920
    # portrait panel turned - and would have been turned on its side.
    def native(s: screens.Screen) -> tuple[int, int]:
        return (s.height, s.width) if s.rotation in (90, 270) else (s.width, s.height)
    # **Only a bar is named by its size.** A bar's size is its own (1280 x
    # 400, 1480 x 320), and its preset carries the mode it needs; a standard
    # size is any monitor's, and naming a 1024 x 768 monitor after the one
    # small panel listed at that size would be a guess. Its layout is the
    # same either way.
    same = [s for s in screens.all_screens()
            if s.interface == "hdmi" and s.family == "bar" and native(s) == (width, height)]
    return same[0] if len(same) == 1 else screens.other(width, height)


SETTINGS_DB = Path("/var/lib/gexis-core/settings.db")
CONNECTIONS = Path("/etc/NetworkManager/system-connections")


def _headless(db: Path = SETTINGS_DB) -> bool:
    """The Headless row, read-only - the core owns the store and is not up."""
    import sqlite3
    try:
        with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = 'headless'").fetchone()
        return bool(json.loads(row[0])) if row else False
    except (sqlite3.Error, ValueError):
        return False


def _setup_needed(connections: Path = CONNECTIONS) -> bool:
    """ADR-0104 §2, read from the files - NetworkManager is not up yet: no
    saved Wi-Fi and no `setup-done` marker. Setup's Screen step decides then."""
    from .setup_network import needs_setup
    try:
        wifi = sum(1 for f in connections.glob("*.nmconnection") if "type=wifi" in f.read_text())
    except OSError:
        wifi = 0
    return needs_setup(wifi)


def at_start(seen: screen_detect.Seen | None = None, *, headless: bool | None = None,
             setup_needed: bool | None = None, path: Path = STATE, files: dict | None = None) -> str:
    """Before the panel: a different screen is switched to, pending a Keep.
    Returns what happened - "same", "asks" (a switch here already went back:
    the core asks), "switched", or "restart" (the kernel's mode changed)."""
    from . import screen_apply
    if setup_needed if setup_needed is not None else _setup_needed():
        return "same"
    seen = screen_detect.seen() if seen is None else seen
    q = question(seen, headless=_headless() if headless is None else headless, path=path)
    if q is None:
        return "same"
    if q["tried"]:
        return "asks"
    model = target(seen)
    tried(q["key"], path)
    applied = screen_apply.Applied(model.id, 0)
    # `files`: screen_apply's env, cmdline and state, for a test.
    files = files or {}
    where = {k: files[k] for k in ("env", "cmdline") if k in files}
    restart = screen_apply.picture(**where)[0] != screen_apply.picture_of(applied)[0]
    if not screen_apply.choose(applied, **files):
        kept(seen, path)
        return "same"
    logger.info("screen: %s attached, switched to %s before the panel starts", q["key"], model.id)
    return "restart" if restart else "switched"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        outcome = at_start()
    except Exception:  # noqa: BLE001 - the panel starts on what it had
        logger.exception("screen: the attached screen was not compared")
        return 0
    print(f"screen-check: {outcome}", flush=True)
    if outcome == "restart":
        import subprocess
        subprocess.run(["systemctl", "--no-block", "reboot"], check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
