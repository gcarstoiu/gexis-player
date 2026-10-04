# SPDX-License-Identifier: GPL-3.0-or-later
"""**The Sound card board setting, applied** (ADR-0117 decision 3).

A board with no EEPROM is not seen until its overlay is loaded. Choosing one
writes its `dtoverlay=` to `config.txt`, in a block of ours that replaces any
earlier choice, and the player restarts. **At the next start the card is
looked for: if it is not there, the block goes back to what it was, the
setting with it, and the player restarts again** - no question asked, since
there is nothing on a panel to judge sound by. The row then says the board
was not found.

The state is `/var/lib/gexis/board.json`: what was chosen, what was before,
whether it is still `pending` its card, and `not_found` after a go-back.
Nothing here restarts anything; the caller does.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import boards

CONFIG = Path("/boot/firmware/config.txt")
STATE = Path("/var/lib/gexis/board.json")

#: What the setting holds when no overlay is ours to write.
FOUND_BY_ITSELF = "Found by itself"

BEGIN = "# gexis: Sound card board (ADR-0117) - set in Settings, do not edit"
END = "# gexis: end of Sound card board"


def label(board: boards.Board) -> str:
    """`Maker/Model` for the grouped picker: Volumio's names lead with
    the maker ("HiFiBerry DAC2 HD")."""
    maker, _, model = board.name.partition(" ")
    return f"{maker}/{model or maker}"


def by_label(value: str | None) -> boards.Board | None:
    return next((b for b in boards.all_boards() if label(b) == value), None)


def options() -> tuple[str, ...]:
    """What the row offers: Found by itself, then every board the setting
    may write (a board whose row needs a script is not offered)."""
    return (FOUND_BY_ITSELF, *sorted(label(b) for b in boards.all_boards() if b.offered))


def tags() -> dict[str, str]:
    return {label(b): "Tested" if b.tested else "Known" for b in boards.all_boards() if b.offered}


def block_for(board: boards.Board | None) -> str:
    return "" if board is None else f"[all]\n{BEGIN}\n{board.dtoverlay}\n{END}\n"


def with_block(text: str, board: boards.Board | None) -> str:
    """config.txt with our block replaced, added or removed; every other
    line as it was."""
    lines, out, inside = text.splitlines(keepends=True), [], False
    for i, line in enumerate(lines):
        if line.strip() == BEGIN:
            inside = True
            # The `[all]` written before the block is ours too.
            if out and out[-1].strip() == "[all]":
                out.pop()
            continue
        if inside:
            if line.strip() == END:
                inside = False
            continue
        out.append(line)
    body = "".join(out)
    if body and not body.endswith("\n"):
        body += "\n"
    return body + block_for(board)


def written(config: Path = CONFIG) -> boards.Board | None:
    """The board our block loads now, or None."""
    try:
        text = config.read_text()
    except OSError:
        return None
    if BEGIN not in text:
        return None
    for line in text.split(BEGIN, 1)[1].splitlines():
        if line.startswith("dtoverlay="):
            overlay = line.removeprefix("dtoverlay=").strip()
            return next((b for b in boards.all_boards() if b.dtoverlay == f"dtoverlay={overlay}"), None)
    return None


def read_state(path: Path = STATE) -> dict:
    try:
        doc = json.loads(path.read_text())
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(doc: dict, path: Path = STATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=1))
    tmp.replace(path)


def choose(value: str, *, config: Path = CONFIG, state: Path = STATE) -> bool:
    """Write the chosen board's overlay (or none, for Found by itself).
    True when config.txt changed, which only a restart makes effective."""
    board = by_label(value)
    if value != FOUND_BY_ITSELF and board is None:
        raise ValueError(f"not a board gexis offers: {value!r}")
    before = written(config)
    if (before.id if before else None) == (board.id if board else None):
        return False
    text = config.read_text()
    tmp = config.with_name(config.name + ".gexis-tmp")
    tmp.write_text(with_block(text, board))
    tmp.replace(config)
    write_state({"chosen": board.id if board else None, "previous": before.id if before else None,
                 "pending": board is not None}, state)
    return True


def check(cards: list[str], *, config: Path = CONFIG, state: Path = STATE) -> str | None:
    """At start: a board waiting for its card either has it - kept - or
    does not, and the block goes back to the board before. Returns the
    board id that was not found (the caller restarts), else None."""
    doc = read_state(state)
    if not doc.get("pending"):
        return None
    board = boards.by_id(doc.get("chosen"))
    if board is not None and board.card in cards:
        write_state({**doc, "pending": False, "not_found": None}, state)
        return None
    previous = boards.by_id(doc.get("previous"))
    tmp = config.with_name(config.name + ".gexis-tmp")
    tmp.write_text(with_block(config.read_text(), previous))
    tmp.replace(config)
    write_state({"chosen": doc.get("previous"), "previous": None, "pending": False,
                 "not_found": doc.get("chosen")}, state)
    return doc.get("chosen")


def setting_value(state: Path = STATE, config: Path = CONFIG) -> str:
    """What the row says now: the board our block loads, or Found by itself."""
    board = written(config)
    return label(board) if board else FOUND_BY_ITSELF


def note(state: Path = STATE) -> str | None:
    """The row's note after a go-back."""
    missing = boards.by_id(read_state(state).get("not_found"))
    if missing is None:
        return None
    return (f"The {missing.name} was not found after the restart, so the player went back. "
            "Check the board is seated on the Pi's pins, or choose another.")
