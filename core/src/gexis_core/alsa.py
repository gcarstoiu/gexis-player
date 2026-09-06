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
    """
    node = playback_pcm_node(card_id)
    if not node.exists():
        return False
    result = subprocess.run(
        ["fuser", str(node)], capture_output=True, text=True, check=False
    )
    return bool(result.stdout.strip())
