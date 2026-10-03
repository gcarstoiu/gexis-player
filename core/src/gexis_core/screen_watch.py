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
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from . import screen_detect

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
    }
