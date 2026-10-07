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


#: ADR-0126 decision 2: a short tone at each rate a listener's music is
#: likely to come in. -20 dBFS: clearly heard, never near full scale.
TONE_RATES = (44100, 96000, 192000)
TONE_HZ = 1000
TONE_DBFS = -20.0
TONE_S = 2.0


def _tone(path: Path, rate: int) -> None:
    """A stereo sine, 16-bit at 44.1 kHz, 24-bit in a 32-bit container
    above - what the renderers send."""
    import math, struct, wave
    width = 2 if rate == 44100 else 4
    amp = 10 ** (TONE_DBFS / 20) * (2 ** (8 * width - 1) - 1)
    n = int(rate * TONE_S)
    fade = int(rate * 0.02)          # 20 ms in and out: no click at the edges
    frames = bytearray()
    pack = "<hh" if width == 2 else "<ii"
    for i in range(n):
        g = min(1.0, i / fade, (n - 1 - i) / fade)
        v = int(amp * g * math.sin(2 * math.pi * TONE_HZ * i / rate))
        if width == 4:
            v &= ~0xFF             # 24 bits of it, as a 24-bit file would carry
        frames += struct.pack(pack, v, v)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(width); w.setframerate(rate); w.writeframes(bytes(frames))


def playing() -> bool:
    try:
        return any("RUNNING" in p.read_text(errors="ignore")
                   for p in Path("/proc/asound").glob("card*/pcm*p/sub*/status"))
    except OSError:
        return False


def play_tones(card: str, workdir: Path = Path("/tmp")) -> list[str]:
    """Each tone through the player's own `output` - so the volume, the
    software stage and the meter are as for music - and what the card ran
    at while it played. The caller has checked nothing else is playing."""
    import time
    results = []
    status = Path(f"/proc/asound/{card}/pcm0p/sub0/hw_params")
    for rate in TONE_RATES:
        path = workdir / f"gexis-tone-{rate}.wav"
        _tone(path, rate)
        proc = subprocess.Popen(["aplay", "-q", "-D", "output", str(path)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        time.sleep(0.6)
        hw = _read(status)
        proc.wait(timeout=TONE_S + 10)
        err = (proc.stderr.read() or "").strip().splitlines()[-1:] if proc.stderr else []
        path.unlink(missing_ok=True)
        got_rate = re.search(r"rate: (\d+)", hw)
        got_fmt = re.search(r"format: (\S+)", hw)
        if proc.returncode == 0 and got_rate:
            results.append(f"{rate / 1000:g} kHz: played, the card at {int(got_rate.group(1)) / 1000:g} kHz "
                           f"{got_fmt.group(1) if got_fmt else ''}".rstrip())
        else:
            results.append(f"{rate / 1000:g} kHz: did not play ({err[0] if err else 'no answer'})")
    return results


#: ADR-0126 decision 2: *"asks for four taps in the corners - touch
#: accuracy is measured, not asked"*. A touch screen set up wrongly (axes
#: swapped, mirrored, mapped to a different size) misses by a large part of
#: the screen; a finger that simply lands a little off misses by its own
#: width. 6 % of the diagonal: 91 px on a 1280x800 7", 132 px on a
#: 1920x1080 13.3", 119 px on a 1920x480 bar - well clear of a fingertip,
#: well short of the hundreds of pixels a wrong mapping is off by at the far
#: corners.
TAP_TOLERANCE = 0.06
CORNERS = ("top left", "top right", "bottom right", "bottom left")


def measure_taps(width: int, height: int, taps: list[dict]) -> dict:
    """Each tap's distance from the circle it was asked for, in the screen's
    own pixels, and whether all four landed. `taps` as the panel sends them:
    `{"corner", "x", "y", "tx", "ty"}` (where the finger was, where the
    circle was)."""
    limit = TAP_TOLERANCE * (width ** 2 + height ** 2) ** 0.5
    measured = []
    for tap in taps[: len(CORNERS)]:
        off = round(((float(tap["x"]) - float(tap["tx"])) ** 2 + (float(tap["y"]) - float(tap["ty"])) ** 2) ** 0.5)
        corner = str(tap.get("corner")) if tap.get("corner") in CORNERS else "?"
        measured.append({"corner": corner, "off": off})
    landed = len(measured) == len(CORNERS) and all(m["off"] <= limit for m in measured)
    return {"size": f"{int(width)}x{int(height)}", "taps": measured, "limit": round(limit), "landed": landed}


def screen_lines(result: dict) -> list[str]:
    """The screen check as the report's details hold it."""
    lines = [f"screen as the panel drew it: {result.get('size', '?')}"]
    if result.get("taps"):
        lines.append("taps, distance from the circle: " +
                     ", ".join(f"{t['corner']} {t['off']} px" for t in result["taps"]) +
                     f" - {'all within' if result.get('landed') else 'not all within'} {result.get('limit')} px")
    return lines


#: The questions only a person can answer, by the issue form's field ids.
ANSWERS = ("sound", "volume", "clicks", "picture", "touch")


def issue_url(facts: Facts, answers: dict[str, str], notes: str = "", tones: list[str] | None = None,
              screen_check: list[str] | None = None) -> str:
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
    if tones:
        details += "\nTest tones\n" + "".join(f"- {t}\n" for t in tones)
    if screen_check:
        details += "\nScreen check\n" + "".join(f"- {t}\n" for t in screen_check)
    url = f"{ISSUE_FORM}?{urlencode({**params, 'details': details})}"
    while len(url) > URL_MAX and details:
        details = details[: max(0, len(details) - 200)]
        url = f"{ISSUE_FORM}?{urlencode({**params, 'details': details + ' [cut]'})}"
    return url
