# SPDX-License-Identifier: GPL-3.0-or-later
"""The DAC boards gexis knows (ADR-0117, Phase 13d): what names a board, and
what the *Sound card board* setting offers for one that cannot name itself.

**Seeded from Volumio's list** - `volumio3-backend`'s
`app/plugins/system_controller/i2s_dacs/dacs.json`, read at master
e4cc75aeb5 (the file last changed at c82d2341a3, 2025-07-11), GPL-3.0, kept
as it came in `boards_data/` with its licence (THIRD-PARTY.md; George,
2026-10-01: *"We will use the volumio one which means staying at 3.0"*).
Its Raspberry Pi rows only: 98.

**The card answers first** (ADR-0117 decision 1): the volume scale is never
read from here, only from the card (`mixer_scale`). The list names a board,
says which control to prefer when a card has several, and is the only source
of the overlay for a board with no EEPROM.

**Read, not only imported** (Finding 106) - `CORRECTIONS` says what was
changed, and why.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DACS = Path(__file__).with_name("boards_data") / "dacs.json"

#: ADR-0117 decision 2: *Tested* - played and measured here, with a finding.
#: The IQaudio DAC+ joins once 13d's tests pass on George's board.
TESTED: frozenset[str] = frozenset({"hifiberry-dac2hd"})

#: Changes to Volumio's rows, by id, applied when the list is read.
CORRECTIONS: dict[str, dict] = {
    # The IQaudio DAC+ carries the DigiAMP+'s amplifier: `unmute_amp` (with
    # a trailing space) and `iqamp-unmute.sh`. The DAC+ has no amplifier;
    # its overlay alone is the board (to be shown on George's, 13d).
    "iqaudio-dacplus": {"overlay": "iqaudio-dacplus", "script": ""},
}


@dataclass(frozen=True)
class Board:
    id: str
    name: str
    overlay: str          # the dtoverlay name
    params: tuple[str, ...]
    card: str             # the ALSA card id it makes
    mixer: str | None     # the control to prefer, if the list names one
    eeprom: str | None    # what /proc/device-tree/hat/product says
    script: str | None    # an init script Volumio runs: not run here

    @property
    def tested(self) -> bool:
        return self.id in TESTED

    @property
    def offered(self) -> bool:
        """Whether the setting offers it (ADR-0117 §"What 13d does not do"):
        a board whose row needs a script is listed, not offered, until
        someone has one to try."""
        return not self.script

    @property
    def dtoverlay(self) -> str:
        """The `config.txt` line that loads it."""
        return "dtoverlay=" + ",".join((self.overlay, *self.params))


def _clean(value) -> str:
    return str(value or "").strip()


@lru_cache(maxsize=1)
def all_boards(path: Path = DACS) -> tuple[Board, ...]:
    doc = json.loads(path.read_text())
    rows = next(d["data"] for d in doc["devices"] if d["name"] == "Raspberry PI")
    out = []
    for row in rows:
        row = {**row, **CORRECTIONS.get(row.get("id"), {})}
        overlay, *params = [p for p in (_clean(x) for x in _clean(row.get("overlay")).split(",")) if p]
        out.append(Board(
            id=_clean(row["id"]),
            name=_clean(row["name"]),
            overlay=overlay,
            params=tuple(params),
            card=_clean(row.get("alsacard")),
            mixer=_clean(row.get("mixer")) or None,
            eeprom=_clean(row.get("eeprom_name")) or None,
            script=_clean(row.get("script")) or None,
        ))
    return tuple(out)


def by_id(board_id: str | None) -> Board | None:
    return next((b for b in all_boards() if b.id == board_id), None)


def by_eeprom(product: str | None) -> Board | None:
    """The board whose EEPROM says `product` ("DAC 2 HD")."""
    product = _clean(product)
    return next((b for b in all_boards() if product and b.eeprom == product), None)


def by_card(card: str) -> list[Board]:
    """The boards that make this ALSA card - several share one (four make
    `IQaudIODAC`)."""
    return [b for b in all_boards() if b.card == card]


def mixer_for(card: str) -> str | None:
    """The control to prefer on this card, when every board that makes it
    agrees (ADR-0117: *Digital* over the IQaudio's *Analogue* gain)."""
    names = {b.mixer for b in by_card(card) if b.mixer}
    return names.pop() if len(names) == 1 else None


HAT_PRODUCT = Path("/proc/device-tree/hat/product")


def hat_product(path: Path = HAT_PRODUCT) -> str | None:
    """What a board with an EEPROM calls itself, or None."""
    try:
        return path.read_bytes().rstrip(b"\0").decode(errors="replace").strip() or None
    except OSError:
        return None


#: The Pi's own outputs: not boards, so no state (ADR-0117 decision 2 is
#: about DACs).
BUILT_IN = frozenset({"Headphones", "vc4hdmi0", "vc4hdmi1"})


def identify(card: str, chosen: str | None = None,
             product: str | None = None) -> tuple[Board | None, str | None]:
    """(the board, its state) for an ALSA card (ADR-0117 decisions 1 and 2):
    the board chosen in the setting, else the one the EEPROM names, else the
    one board that makes this card. State: *Tested*, *Known* - also a card
    several listed boards make, when which one is not known - or *Detected*,
    working by discovery alone. None for the Pi's own outputs."""
    if card in BUILT_IN:
        return None, None
    board = by_id(chosen) if chosen else None
    if board is None or board.card != card:
        named = by_eeprom(product)
        board = named if named is not None and named.card == card else None
    makers = by_card(card)
    if board is None and len(makers) == 1:
        board = makers[0]
    if board is None:
        return None, "Known" if makers else "Detected"
    return board, "Tested" if board.tested else "Known"
