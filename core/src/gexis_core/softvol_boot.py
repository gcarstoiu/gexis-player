# SPDX-License-Identifier: GPL-3.0-or-later
"""**The software volume is set before any renderer starts** (ADR-0140;
George, 2026-10-12: "Do it now").

ALSA makes the software stage's control (ADR-0124) when its PCM is first
opened, and makes it at 0 dB. The core sets the remembered level on it as it
starts - but the core starts after squeezelite, go-librespot and
bluealsa-aplay, so after a power cut a renderer that resumed by itself could
play its first second or so through the software stage at 0 dB, on HDMI
especially, where nothing else attenuates.

`gexis-softvol-restore.service` runs this once, before the renderers: when
the volume type in force is Software, the control is made and given the
level the core would give it; otherwise nothing. **It never fails the
boot** - a missing card, store or control is logged, and the renderers start
as they did before. **It never sets a level above the core's**: the same
level, chosen by the same rule (`start_level`), and the card's own control
is left alone (the core parks it at 0 dB only once its own write is read
back).

Read only: the store is opened read-only and nothing is written to it.
"""
from __future__ import annotations

import logging
import sqlite3
import subprocess
import time
from pathlib import Path

from gexis_core import outputs

logger = logging.getLogger("gexis_core.softvol_boot")

#: ADR-0127: one row, `output_mode` - Hardware, Software or Fixed.
VOLUME_KEY = "output_mode"
HARDWARE, SOFTWARE, FIXED = "Hardware", "Software", "Fixed"
#: ADR-0124: where the software level is kept across restarts - ALSA forgets
#: a software control with its PCM, and makes it again at 0 dB.
SOFTWARE_LEVEL_KEY = "_software_level_db"
#: A first start with no level remembered and none to carry over: quiet.
SOFTWARE_LEVEL_FIRST_DB = -30.0

STORE = Path("/var/lib/gexis-core/settings.db")
#: How long the output's card is waited for, should it not be listed yet.
#: Bounded: the renderers wait on this unit.
CARD_WAIT_S = 3.0


def volume_mode(stored, output) -> str:
    """What is in force for `output` (ADR-0127 §2): the stored choice, except
    Hardware on an output with no control of its own, where Software takes
    its place - or Fixed, on an output that feeds a device with its own
    volume (ADR-0155 decision 3). The same answer `Settings.value` gives once
    the row is restricted; this one is for start-up, before `Settings`
    exists."""
    mode = stored if stored in (HARDWARE, SOFTWARE, FIXED) else HARDWARE
    if mode == HARDWARE and output is not None and output.control is None:
        return FIXED if getattr(output, "fixed_by_default", False) else SOFTWARE
    return mode


def start_level(remembered, card_db: float | None) -> float:
    """The software level at a start (ADR-0124), in order: the one
    remembered; else the card's own, which is what the listener was hearing
    when it was switched on; else quiet. One rule for the core and for the
    boot step, so the boot step never sets more than the core then does."""
    if remembered is not None:
        return float(remembered)
    if card_db is not None:
        return float(card_db)
    return SOFTWARE_LEVEL_FIRST_DB


def read_store(path: Path = STORE) -> dict | None:
    """The two rows and the output, read-only; None when there is no store."""
    import json
    if not path.exists():
        return None
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = dict(conn.execute(
            "SELECT key, value FROM settings WHERE key IN (?, ?, ?)",
            (VOLUME_KEY, SOFTWARE_LEVEL_KEY, "output_device"),
        ).fetchall())
    finally:
        conn.close()
    return {key: json.loads(value) for key, value in rows.items()}


def _amixer(*args: str) -> str | None:
    try:
        return subprocess.run(["amixer", "-D", "output", *args], capture_output=True,
                              text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("softvol-boot: amixer failed: %s", exc)
        return None


def get_raw(control: str) -> int | None:
    from gexis_core.volume import _VALUE_RE
    out = _amixer("sget", control)
    match = _VALUE_RE.search(out.encode()) if out else None
    return int(match.group(1)) if match else None


def set_raw(control: str, raw: int) -> None:
    _amixer("sset", control, str(raw))


def _wait_for_card(card: str, wait_s: float = CARD_WAIT_S) -> bool:
    deadline = time.monotonic() + wait_s
    while True:
        try:
            if f"[{card}]" in outputs.CARDS.read_text().replace(" ", ""):
                return True
        except OSError:
            pass
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.1)


def restore(store_path: Path = STORE) -> str:
    """Set the software level before the renderers start; what was done."""
    rows = read_store(store_path)
    if rows is None:
        return "no settings store: nothing to set"
    card = outputs.configured()
    if card and not _wait_for_card(card):
        return f"card {card} not listed: nothing set"
    output = outputs.resolve(rows.get("output_device"))
    if output is None:
        return "no output: nothing set"
    mode = volume_mode(rows.get(VOLUME_KEY), output)
    if mode != SOFTWARE:
        return f"{mode} volume on {output.label}: nothing to set"
    card_db = None
    if rows.get(SOFTWARE_LEVEL_KEY) is None and output.control and output.scale:
        raw = get_raw(output.control)
        card_db = output.scale.db(raw) if raw is not None else None
    db = start_level(rows.get(SOFTWARE_LEVEL_KEY), card_db)
    if not outputs.create_softvol_control():
        logger.warning("softvol-boot: the software control could not be made")
    want = outputs.SOFTVOL_SCALE.raw(db)
    set_raw(outputs.SOFTVOL_CONTROL, want)
    got = get_raw(outputs.SOFTVOL_CONTROL)
    if got != want:
        return f"the software level did not take (wanted {want}, read {got})"
    return f"software volume at {db:.2f} dB on {output.label}"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        outcome = restore()
    except Exception:  # noqa: BLE001 - the renderers start as they did before
        logger.exception("softvol-boot: the software level was not set")
        return 0
    print(f"softvol-boot: {outcome}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
