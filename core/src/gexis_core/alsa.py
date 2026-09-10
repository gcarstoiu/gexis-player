# SPDX-License-Identifier: GPL-3.0-or-later
"""ALSA card/device resolution.

Never reference a card by index (project rule, Finding 005 - the index for
the same DAC model differs across `rig`, moOde and `gexis`). Resolve by the
card id string every time.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

CARD_ID = "sndrpihifiberry"


def resolve_card_number(card_id: str = CARD_ID, cards_file: Path | None = None) -> int:
    """Resolve e.g. "sndrpihifiberry" to its current ALSA card number."""
    path = cards_file or Path("/proc/asound/cards")
    for line in path.read_text().splitlines():
        # /proc/asound/cards pads the bracketed id to a fixed 15-char
        # field. A short id ("vc4hdmi0") has trailing spaces inside the
        # brackets that \S+ stops at; an id that exactly fills the field
        # ("sndrpihifiberry" - also 15 chars) has none, so a \S+ match
        # greedily runs past the closing bracket and the colon after it.
        # Found on hardware, 2026-09-06: this card id is the exact-fit
        # case, so the old \S+ pattern never matched it. Match up to the
        # bracket explicitly instead of relying on whitespace to stop it.
        m = re.match(r"\s*(\d+)\s+\[([^\]]+)\]", line)
        if m and m.group(2).strip() == card_id:
            return int(m.group(1))
    raise RuntimeError(f"ALSA card {card_id!r} not found in {path}")


def playback_pcm_node(card_id: str = CARD_ID) -> Path:
    """The kernel device node for the card's first playback PCM."""
    return Path(f"/dev/snd/pcmC{resolve_card_number(card_id)}D0p")


def device_busy(card_id: str = CARD_ID) -> bool:
    """Whether anything currently holds the playback PCM.

    Used by the timeout ladder (criterion 4) to decide whether a "polite
    stop" actually freed the device, rather than trusting an adapter's
    release() to mean the same thing everywhere - squeezelite's unit stays
    "active" whether or not it holds the device (`-C <seconds>` is what
    actually closes it), so unit state is not a usable proxy here.

    Kept for callers that genuinely want "is anyone at all holding it" -
    the release ladder itself does not want this (see `device_held_by`).
    """
    node = playback_pcm_node(card_id)
    if not node.exists():
        return False
    result = subprocess.run(
        ["fuser", str(node)], capture_output=True, text=True, check=False
    )
    return bool(result.stdout.strip())


def _unit_main_pid(unit: str) -> int | None:
    """A systemd unit's current MainPID, or None if it has none (not
    running, or systemd reports 0 for "no main process")."""
    result = subprocess.run(
        ["systemctl", "show", unit, "--property=MainPID", "--value"],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        pid = int(result.stdout.strip())
    except ValueError:
        return None
    return pid or None


def device_held_by(unit: str, card_id: str = CARD_ID) -> bool:
    """Whether `unit`'s own process specifically still holds the playback
    PCM - not just whether *something* does.

    Found on hardware, 2026-09-08: `device_busy` is too coarse for the
    release ladder's actual question. `Supervisor.acquire()` sets the new
    renderer active and restores its volume *before* releasing the
    outgoing one (arbitration.py), and the new renderer's own process
    (squeezelite reacting to LMS, say) can legitimately open the device
    while the outgoing renderer's release ladder is still running its
    checks. At that point `device_busy` reports True regardless of
    whether the outgoing renderer ever let go - the ladder read that as
    "still held", escalated to SIGTERM then SIGKILL against a renderer
    (go-librespot) that had already exited cleanly on `release()`'s own
    `/player/stop`, and logged a false "STILL holds the device after
    SIGKILL". Checking the *specific* unit's PID against `fuser`'s holder
    list, rather than "is the holder list non-empty", fixes this: once
    the outgoing renderer's PID is gone from that list, it has released,
    regardless of who (if anyone) holds the device now.
    """
    node = playback_pcm_node(card_id)
    if not node.exists():
        return False
    pid = _unit_main_pid(unit)
    if pid is None:
        return False
    result = subprocess.run(
        ["fuser", str(node)], capture_output=True, text=True, check=False
    )
    holder_pids = {int(p) for p in result.stdout.split() if p.strip().isdigit()}
    return pid in holder_pids
