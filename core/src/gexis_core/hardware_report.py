# SPDX-License-Identifier: GPL-3.0-or-later
"""**Hardware feedback**, first called Report this hardware (ADR-0126; George, 2026-10-07: *"how do we crowd
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
    #: The Pi's own output in use (HDMI, the headphone jack): no DAC.
    builtin: str | None = None
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

    def _no_card(self) -> str:
        return f"none - {self.builtin}, the Pi's own output" if self.builtin else "none"

    def text(self) -> str:
        """The facts as the issue's details field holds them."""
        lines = [
            f"Gexis {self.version} on a {self.pi}, {self.memory_mb} MB, kernel {self.kernel}",
            "",
            "Sound",
            f"- card: {self.card or self._no_card()}"
            + (f" - {self.board} ({self.state})" if self.board else (f" ({self.state})" if self.state else "")),
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


def _bit(words: str, n: int) -> bool:
    """Bit `n` of a capability mask as /proc/bus/input/devices prints it:
    hex words, the highest first, each as wide as the kernel's long."""
    parts = words.split()
    index, bit = divmod(n, 64)   # a long on the Pi 4's 64-bit kernel
    if index >= len(parts):
        return False
    try:
        return bool(int(parts[len(parts) - 1 - index], 16) >> bit & 1)
    except ValueError:
        return False


BTN_TOUCH, ABS_X, ABS_Y, ABS_MT_X, ABS_MT_Y = 0x14A, 0x00, 0x01, 0x35, 0x36


def _touch() -> list[str]:
    """**Touch controllers** by name and vendor:product: devices that report a
    touch (BTN_TOUCH) and where it lands (X and Y, single or multi-touch), on
    any bus - USB or I2C. A keyboard, an IR receiver or a DAC's buttons is not
    a touch screen (it was, until 2026-10-11: any USB input device counted,
    and a screen without touch was asked for four taps). Never their serial
    (`U:` lines are not read)."""
    out = []
    for block in _read(INPUT_DEVICES).split("\n\n"):
        bus = re.search(r"Bus=(\w+) Vendor=(\w+) Product=(\w+)", block)
        name = re.search(r'N: Name="([^"]*)"', block)
        key = re.search(r"^B: KEY=(.+)$", block, re.M)
        axes = re.search(r"^B: ABS=(.+)$", block, re.M)
        if not (bus and name and key and axes):
            continue
        placed = (_bit(axes.group(1), ABS_X) and _bit(axes.group(1), ABS_Y)) or \
                 (_bit(axes.group(1), ABS_MT_X) and _bit(axes.group(1), ABS_MT_Y))
        if _bit(key.group(1), BTN_TOUCH) and placed:
            out.append(f"{name.group(1).strip()} ({bus.group(2)}:{bus.group(3)})")
    return out


def collect(card: str | None, chosen_board: str | None = None, screen_chosen: str | None = None,
            builtin: str | None = None) -> Facts:
    facts = Facts()
    facts.builtin = None if card else builtin
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


ASOUND = Path("/proc/asound")


def busy(card: str | None, root: Path = ASOUND) -> str | None:
    """**Why the tones cannot play now, or None.** Not only a card that is
    playing: one held open and paused or prepared refuses another player
    too, and three "did not play (busy)" lines would then say the card had
    failed (review, 2026-10-11). Every playback stream on the output card
    is looked at; on another card, only one that is playing."""
    try:
        for status in root.glob("card*/pcm*p/sub*/status"):
            text = status.read_text(errors="ignore")
            if "RUNNING" in text:
                return "playing"
            on_output = card is not None and (root / card).resolve() == status.parents[2].resolve()
            if on_output and "closed" not in text:
                return "held"
    except OSError:
        return None
    return None


class CardBusy(Exception):
    """The card was taken while the tones played."""


def play_tones(card: str, workdir: Path | None = None) -> list[str]:
    """Each tone through the player's own `output` - so the volume, the
    software stage and the meter are as for music - and what the card ran
    at while it played. The caller has checked the card is free, and holds
    the one lock: two at once shared these files (review, 2026-10-11)."""
    import tempfile
    import time
    results = []
    status = ASOUND / card / "pcm0p/sub0/hw_params"
    with tempfile.TemporaryDirectory(prefix="gexis-tones-", dir=workdir) as tmp:
        for rate in TONE_RATES:
            path = Path(tmp) / f"tone-{rate}.wav"
            _tone(path, rate)
            proc = subprocess.Popen(["aplay", "-q", "-D", "output", str(path)],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            # What the card runs at, read once it is open: the chain (plug,
            # software stage, meter) can take longer than a fixed wait.
            hw = ""
            deadline = time.monotonic() + TONE_S
            while time.monotonic() < deadline and proc.poll() is None:
                hw = _read(status)
                if "rate:" in hw:
                    break
                time.sleep(0.1)
            try:
                proc.wait(timeout=TONE_S + 10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            err = (proc.stderr.read() or "").strip().splitlines()[-1:] if proc.stderr else []
            if err and "busy" in err[0].lower():
                raise CardBusy(err[0])
            got_rate = re.search(r"rate: (\d+)", hw)
            got_fmt = re.search(r"format: (\S+)", hw)
            if proc.returncode == 0 and got_rate:
                results.append(f"{rate / 1000:g} kHz: played, the card at {int(got_rate.group(1)) / 1000:g} kHz "
                               f"{got_fmt.group(1) if got_fmt else ''}".rstrip())
            elif proc.returncode == 0:
                results.append(f"{rate / 1000:g} kHz: played (the card's rate was not read)")
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


#: ADR-0126 decision 1: *"Offered once, unprompted, after a week on a board
#: or screen that is not Tested: a single line on Settings' System page ...
#: dismissed for good with one tap."*
PROMPT_KEY = "_hardware_prompt"

#: **The last feedback prepared, kept** (ADR-0126 amended 2026-10-11): sent
#: again or started over from the System row, and forgotten when the sound
#: card or the screen it was made on is no longer the one in use.
KEPT_KEY = "_hardware_feedback"


def identity(card: str | None, board_id: str | None, screen_label: str | None,
             screen_seen: str | None = None) -> str:
    """The sound card and screen in use, as one key: a board is told apart
    from another on the same card (HiFiBerry's share one) by its id; a
    screen by what is connected (its EDID), so unplugging it, swapping one
    the list does not know or going Headless is another screen too
    (review, 2026-10-11) - and by its label in Settings."""
    return f"sound:{board_id or card or 'none'}|screen:{screen_label or 'none'}|seen:{screen_seen or 'none'}"


def kept_for(stored: dict | None, now_identity: str) -> dict | None:
    """What is kept, if it was made on the hardware in use now."""
    if not isinstance(stored, dict) or stored.get("identity") != now_identity or not stored.get("url"):
        return None
    return stored


def names(facts: Facts, display: bool = True) -> tuple[str, str]:
    """The sound card and the screen as the feedback names them. The Pi's
    own output is named as that, never as a DAC; a screen only when one is
    there to look at (`display`: connected, not Headless)."""
    what = facts.board or facts.card or (f"{facts.builtin} (the Pi's own output)" if facts.builtin
                                         else "no sound card")
    screen = ""
    if display and facts.screen_connected:
        screen = facts.screen_chosen or (f"{facts.edid_maker or ''} {facts.edid_name or ''}".strip())
    return what, screen


PROMPT_AFTER_S = 7 * 24 * 3600


def untested(card: str | None, board_id: str | None, board_state: str | None,
             screen_label: str | None, screen_tested: bool | None) -> dict[str, str]:
    """What on this device is not Tested, by kind: `{"sound": key,
    "screen": key}`, each key naming that piece of hardware. The Pi's own
    outputs are no DAC to report; no screen chosen is nothing to report."""
    out = {}
    if card and board_state is not None and board_state != "Tested":
        out["sound"] = f"sound:{board_id or card}"
    if screen_label and screen_tested is False:
        out["screen"] = f"screen:{screen_label}"
    return out


def prompt(stored: dict | None, pieces: dict[str, str], now: float) -> tuple[str | None, dict]:
    """The line to show, if any, and the record to keep. A piece is first
    seen now unless the record already has it; it is due a week after that,
    unless dismissed (or reported, which dismisses it)."""
    record = {"seen": dict((stored or {}).get("seen") or {}),
              "dismissed": list((stored or {}).get("dismissed") or [])}
    due = []
    for kind, key in pieces.items():
        since = record["seen"].setdefault(key, now)
        if key not in record["dismissed"] and now - since >= PROMPT_AFTER_S:
            due.append(kind)
    if not due:
        return None, record
    if len(due) == 2:
        return "Help others with this DAC and screen: share how they work", record
    what = "this DAC" if due == ["sound"] else "this screen"
    return f"Help others with {what}: share how it works", record


def dismissed(stored: dict | None, pieces: dict[str, str]) -> dict:
    record = {"seen": dict((stored or {}).get("seen") or {}),
              "dismissed": list((stored or {}).get("dismissed") or [])}
    for key in pieces.values():
        if key not in record["dismissed"]:
            record["dismissed"].append(key)
    return record


def board_reports(output) -> str | None:
    """What owners reported of the board behind `output`, as the Sound card
    board row says it (ADR-0126 decision 5); None for a Tested board, the
    Pi's own outputs, or nothing reported."""
    from gexis_core import board_apply, hardware_reports
    if output is None or output.card in boards.BUILT_IN:
        return None
    written = board_apply.written()
    board, state = boards.identify(output.card, chosen=written.id if written else None,
                                   product=_read(HAT / "product") or None)
    if state == "Tested":
        return None
    return hardware_reports.sentence(hardware_reports.board(board.id if board else output.card))


def screen_reports(label: str | None) -> str | None:
    from gexis_core import hardware_reports, screens
    model = screens.by_label(label) if label else None
    if model is None or model.tested:
        return None
    return hardware_reports.sentence(hardware_reports.screen(model.label))


#: The questions only a person can answer, by the issue form's field ids.
ANSWERS = ("sound", "volume", "clicks", "picture", "touch")


#: The details' first lines - the version and the card - are what the script
#: reading reports needs; they are never cut.
DETAILS_KEPT = 5


def issue_url(facts: Facts, answers: dict[str, str], notes: str = "", tones: list[str] | None = None,
              screen_check: list[str] | None = None, display: bool = True) -> str:
    """The issue form, pre-filled: the board and screen in the title, the
    answers in their fields, the facts in the details. Kept under what GitHub
    accepts by cutting the details first, down to their first lines, then the
    notes: a letter outside ASCII takes 6 to 12 characters in the address,
    and 2,000 of them had cut every detail and still been too long (review,
    2026-10-11)."""
    what, screen = names(facts, display)
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
    def build(details_now: str, notes_now: str) -> str:
        return f"{ISSUE_FORM}?{urlencode({**params, 'notes': notes_now, 'details': details_now})}"

    url = build(details, params["notes"])
    floor = "\n".join(details.splitlines()[:DETAILS_KEPT]) + "\n"
    cut = details
    while len(url) > URL_MAX and len(cut) > len(floor):
        cut = cut[: max(len(floor), len(cut) - 200)]
        url = build(cut + " [cut]", params["notes"])
    notes_now = params["notes"]
    while len(url) > URL_MAX and notes_now:
        notes_now = notes_now[: max(0, len(notes_now) - 50)]
        url = build(cut + (" [cut]" if cut != details else ""), notes_now + " [cut]")
    return url


#: The form's questions, by field id, as the text file names them.
QUESTIONS = {"sound": "Did the music sound right?", "volume": "Did the volume change with the slider?",
             "clicks": "Any clicks or gaps between tracks?", "picture": "Is the whole picture visible on the screen?",
             "touch": "Does a tap land where the finger is?"}


def feedback_text(url: str) -> str:
    """**ADR-0138 decision 3: the feedback as one readable text file**, for
    e-mail - made from the link it was prepared as, so the two never differ."""
    from urllib.parse import parse_qs, urlsplit
    q = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
    lines = [q.get("title", "[Hardware]"), "",
             f"Sound card: {q.get('board', '?')}", f"Screen: {q.get('screen', 'none')}", ""]
    lines += [f"{label} {q.get(key, '-')}" for key, label in QUESTIONS.items()]
    lines += ["", "Anything else:", q.get("notes") or "-", "", "What the player read:", q.get("details", "")]
    return "\n".join(lines).rstrip() + "\n"
