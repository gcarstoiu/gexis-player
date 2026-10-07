# SPDX-License-Identifier: GPL-3.0-or-later
"""**Report this hardware** (ADR-0126; George, 2026-10-07: *"how do we crowd
source the testing of audio hats, dacs and displays. otherwise its impossible
to have coverage"*).

What the device itself knows about its sound card and its screen, for a
report its owner sends as a GitHub issue: the board (by its EEPROM where it
has one), its driver, overlay, volume controls and the rates and formats it
takes; the screen's maker, name and modes from its EDID and the touch
controller's name. **Never a serial number, an address or a name of a
person or a place** - nothing here reads one: the EDID's serial fields, the
EEPROM's UUID and the touch controller's serial are left unread.

The owner adds what only a person can say (did it sound right, did the
volume work, is the whole picture visible); the issue form takes the rest
pre-filled.
"""
from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlencode

from gexis_core import boards, screen_detect

logger = logging.getLogger("gexis_core.hardware_report")

ISSUE_FORM = "https://github.com/gcarstoiu/gexis-player/issues/new"
TEMPLATE = "hardware-report.yml"
#: GitHub refuses a longer address; the details are cut before it.
URL_MAX = 7500

CONFIG_TXT = Path("/boot/firmware/config.txt")
INPUT_DEVICES = Path("/proc/bus/input/devices")
ASOUND_CARDS = Path("/proc/asound/cards")
HAT = Path("/proc/device-tree/hat")


def _run(*cmd: str, timeout: float = 10) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def _read(path: Path) -> str:
    try:
        return path.read_bytes().rstrip(b"\0").decode(errors="replace").strip()
    except OSError:
        return ""


@dataclass
class Facts:
    pi: str = ""
    memory_mb: int | None = None
    version: str = ""
    kernel: str = ""
    # sound
    card: str = ""
    board: str | None = None
    board_id: str | None = None
    state: str | None = None
    eeprom_vendor: str = ""
    eeprom_product: str = ""
    eeprom_id: str = ""
    overlays: list[str] = field(default_factory=list)
    driver: str = ""
    controls: list[str] = field(default_factory=list)
    formats: str = ""
    rates: str = ""
    # screen
    screen_connected: bool = False
    edid_maker: str | None = None
    edid_name: str | None = None
    preferred: str | None = None
    screen_chosen: str | None = None
    touch: list[str] = field(default_factory=list)

    def text(self) -> str:
        """The facts as the issue's details field holds them."""
        lines = [
            f"Gexis {self.version} on a {self.pi}, {self.memory_mb} MB, kernel {self.kernel}",
            "",
            "Sound",
            f"- card: {self.card or 'none'}" + (f" - {self.board} ({self.state})" if self.board else
                                                (f" ({self.state})" if self.state else "")),
            f"- EEPROM: {self.eeprom_vendor} / {self.eeprom_product} / {self.eeprom_id}"
            if self.eeprom_product else "- EEPROM: none",
            f"- overlays: {', '.join(self.overlays) or 'none in config.txt'}",
            f"- driver: {self.driver or 'unknown'}",
            f"- controls: {', '.join(self.controls) or 'none'}",
            f"- formats: {self.formats or 'not read (card in use)'}",
            f"- rates: {self.rates or 'not read (card in use)'}",
            "",
            "Screen",
            f"- connected: {'yes' if self.screen_connected else 'no'}",
            f"- EDID: {self.edid_maker or '?'} / {self.edid_name or '?'}, preferred {self.preferred or '?'}",
            f"- chosen in Settings: {self.screen_chosen or 'none'}",
            f"- touch: {', '.join(self.touch) or 'none found'}",
        ]
        return "\n".join(lines) + "\n"


def _card_driver(card: str) -> str:
    for line in _read(ASOUND_CARDS).splitlines():
        m = re.match(r"^\s*\d+ \[(\S+)\s*\]: (\S+)", line)
        if m and m.group(1) == card:
            return m.group(2)
    return ""


def _hw_params(card: str) -> tuple[str, str]:
    """What the card takes, asked of the card - only when nobody holds it:
    asking means opening it."""
    # An empty raw input: the parameters are dumped and nothing is played
    # (raw, so aplay reads no header from it).
    # aplay prints the dump on stderr.
    try:
        out = subprocess.run(["aplay", "-t", "raw", "-f", "S16_LE", "-r", "44100", "-c", "2",
                              "--dump-hw-params", "-D", f"hw:{card}", "/dev/null"],
                             capture_output=True, text=True, timeout=10).stderr
    except (OSError, subprocess.SubprocessError):
        out = ""
    formats = re.search(r"^FORMAT:\s*(.+)$", out, re.M)
    rates = re.search(r"^RATE:\s*(.+)$", out, re.M)
    return (formats.group(1).strip() if formats else "", rates.group(1).strip() if rates else "")


def _touch() -> list[str]:
    """USB input devices by name and vendor:product - the touch controller
    among them. Never their serial (`U:` lines are not read)."""
    out = []
    for block in _read(INPUT_DEVICES).split("\n\n"):
        bus = re.search(r"Bus=(\w+) Vendor=(\w+) Product=(\w+)", block)
        name = re.search(r'N: Name="([^"]*)"', block)
        if bus and name and bus.group(1) == "0003":
            out.append(f"{name.group(1)} ({bus.group(2)}:{bus.group(3)})")
    return out


def collect(card: str | None, chosen_board: str | None = None, screen_chosen: str | None = None) -> Facts:
    facts = Facts()
    facts.pi = _read(Path("/proc/device-tree/model")) or "Raspberry Pi"
    mem = re.search(r"MemTotal:\s*(\d+)", _read(Path("/proc/meminfo")))
    facts.memory_mb = int(mem.group(1)) // 1024 if mem else None
    facts.version = _run("dpkg-query", "-W", "-f", "${Version}", "gexis-player").strip()
    facts.kernel = _run("uname", "-r").strip()

    if card:
        facts.card = card
        facts.eeprom_vendor = _read(HAT / "vendor")
        facts.eeprom_product = _read(HAT / "product")
        facts.eeprom_id = _read(HAT / "product_id")
        board, state = boards.identify(card, chosen=chosen_board, product=facts.eeprom_product or None)
        facts.board, facts.board_id, facts.state = (board.name if board else None,
                                                     board.id if board else None, state)
        facts.driver = _card_driver(card)
        # The board's own controls - not the software stage the player may
        # have added to the card (ADR-0124).
        from gexis_core.outputs import SOFTVOL_CONTROL
        facts.controls = [m for m in re.findall(r"Simple mixer control '([^']+)'",
                                                 _run("amixer", "-c", card, "scontrols"))
                          if m != SOFTVOL_CONTROL]
        facts.formats, facts.rates = _hw_params(card)
    facts.overlays = [l.split("=", 1)[1] for l in _read(CONFIG_TXT).splitlines()
                      if l.startswith("dtoverlay=") and not l.startswith(("dtoverlay=vc4", "dtoverlay=dwc2"))]
    try:
        seen = screen_detect.seen()
        facts.screen_connected = seen.connected
        facts.edid_maker, facts.edid_name = seen.edid_maker, seen.edid_name
        facts.preferred = f"{seen.preferred[0]}x{seen.preferred[1]}" if seen.preferred else None
    except Exception:  # noqa: BLE001 - a report is still worth having without it
        logger.warning("hardware report: the screen could not be read")
    facts.screen_chosen = screen_chosen
    facts.touch = _touch()
    return facts


#: The questions only a person can answer, by the issue form's field ids.
ANSWERS = ("sound", "volume", "clicks", "picture", "touch")


def issue_url(facts: Facts, answers: dict[str, str], notes: str = "") -> str:
    """The issue form, pre-filled: the board and screen in the title, the
    answers in their fields, the facts in the details. Kept under what GitHub
    accepts by cutting the details first."""
    what = facts.board or facts.card or "no sound card"
    screen = facts.screen_chosen or (f"{facts.edid_maker} {facts.edid_name}".strip() if facts.edid_name else "")
    params = {
        "template": TEMPLATE,
        "title": f"[Hardware] {what}" + (f" · {screen}" if screen else ""),
        "board": what,
        "screen": screen or "none",
        **{k: v for k, v in answers.items() if k in ANSWERS and v},
        "notes": notes.strip(),
    }
    details = facts.text()
    url = f"{ISSUE_FORM}?{urlencode({**params, 'details': details})}"
    while len(url) > URL_MAX and details:
        details = details[: max(0, len(details) - 200)]
        url = f"{ISSUE_FORM}?{urlencode({**params, 'details': details + ' [cut]'})}"
    return url
