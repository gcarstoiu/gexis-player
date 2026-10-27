"""ADR-0055 — which output the device plays to.

**The switch is cheap because ADR-0009 made it cheap.** Every renderer plays
to `pcm.output` and the daemon opens its mixer through `ctl.output`, so
choosing an output is the two lines of `/etc/alsa/conf.d/output.conf` that
name the card. The visualiser follows for nothing: `pcm.output` is a
`type meter` wrapped *around* the slave, so whatever the slave becomes, the
peppyalsa scope taps it (ADR-0011).

**Discovered, not written down.** There is no `dtoverlay=hifiberry-…` in
`config.txt` on this device - the HAT's EEPROM is read at boot - so the card
name *and* its volume control's name are properties of whatever board is
fitted. Anything that hardcodes `DAC` hardcodes one device.

**Two of the four outputs measured on `gexis` have no volume control at
all** (both HDMI). Choosing one of those *is*
[ADR-0046](../../../docs/decisions/0046-fixed-output-hides-the-slider.md)'s
fixed output, arrived at from the other direction, which is why 9i and 9j
were one conversation.
"""
from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, NamedTuple

from gexis_core import boards, mixer_scale

logger = logging.getLogger("gexis_core.outputs")

CONF_PATH = Path("/etc/alsa/conf.d/output.conf")

#: **What the shipped `output.conf` says**, and what `render` uses when it is
#: given nothing. Both are peppyalsa's, both are about how the visualisation
#: *moves* rather than what it measures, and both are settings
#: ([ADR-0058](../../../docs/decisions/0058-the-visualisations-ballistics-are-settings.md)).
DECAY_MS = 400
SMOOTHING_FACTOR = 90


class Tuning(NamedTuple):
    """How the meter and the spectrum move, as peppyalsa takes it.

    `decay_ms` is how long the *VU level* takes to fall full scale; its rise
    is instant and there is no knob for that. `smoothing_factor` is the
    percentage of each spectrum band's previous value kept on every block -
    higher is slower, in both directions.
    """

    decay_ms: int = DECAY_MS
    smoothing_factor: int = SMOOTHING_FACTOR
DRM = Path("/sys/class/drm")

#: Our own snd-dummy cards. They have a mixer and no audio path, which is
#: exactly the shape that would otherwise pass every test below. And the
#: equaliser's loopback (ADR-0162 D1): a card every renderer plays into while
#: the equaliser is on, never an output of its own.
LOOPBACK = "Loopback"
OURS = frozenset({"gexislmsvol", "gexisbtvol", LOOPBACK})
#: What CamillaDSP plays to while the equaliser is on: the rest of the
#: output's chain, after the loopback (ADR-0162 D1, D8).
EQ_OUT = "gexis_eq_out"

#: Friendly names for the board's own outputs, whose ALSA ids are stable
#: and unhelpful. Anything else is named from what `aplay -l` says it is,
#: because anything else is a HAT nobody has met yet.
LABELS = {
    "Headphones": "Headphones (3.5 mm)",
    "vc4hdmi0": "HDMI 1",
    "vc4hdmi1": "HDMI 2",
}

#: Which DRM connector a card's audio comes out of, so "nothing is plugged
#: in" can be said rather than discovered by the user.
CONNECTORS = {"vc4hdmi0": "HDMI-A-1", "vc4hdmi1": "HDMI-A-2"}
#: The other way: the sound card on each HDMI port (ADR-0141 D4).
CARD_FOR_CONNECTOR = {v: k for k, v in CONNECTORS.items()}

#: **George, 2026-09-23:** *"Offer all, but maybe it clears that the one
#: that is not connected looks disabled or has a note saying that nothing
#: is connected."* The suffix is display only - `resolve` matches on what
#: comes before it, so plugging a cable in does not orphan a stored choice.
UNPLUGGED = " — nothing connected"
#: What an option adds after the output's name - its state, and
#: UNPLUGGED - all display only: `resolve` matches on the name before it.
SEP = " — "


#: Formats a renderer actually produces. A card offering none of them
#: cannot be written to without conversion.
PCM_FORMATS = frozenset(
    {"S16_LE", "S16_BE", "S24_LE", "S24_BE", "S24_3LE", "S32_LE", "S32_BE", "U8"}
)

_needs_plug: dict[str, bool] = {}


#: What each card said it takes, from `needs_plug`'s question (`widens`).
_formats: dict[str, frozenset[str]] = {}
#: Its lowest and highest rate, from the same question (`squeezelite_options`).
_rates: dict[str, tuple[int, int]] = {}
#: The rates themselves when the card lists them one by one rather than as a
#: range (`takes_rate`).
_rate_list: dict[str, tuple[int, ...]] = {}
#: Which device gave those answers (`_device`), by card id.
_asked_of: dict[str, tuple | None] = {}

#: **The highest PCM rate Lyrion hands Squeezelite as it is** (ADR-0143;
#: measured 2026-10-12 on an SMSL USB DAC, which takes 768 kHz): FLAC and WAV
#: up to 384 kHz reached the card unchanged, 705.6 and 768 kHz WAV opened it
#: at 44.1 kHz - played some sixteen times too slow.
LYRION_MAX_RATE = 384000
#: The rates told to Squeezelite for a card above that, so Lyrion converts a
#: file beyond them rather than sending what plays wrong.
SQUEEZELITE_RATES = (44100, 48000, 88200, 96000, 176400, 192000, 352800, 384000)
SQUEEZELITE_ENV = Path("/etc/gexis/squeezelite.env")


#: **Native DSD, by the format the card takes it in** (ADR-0144), most
#: preferred first, with the name Squeezelite's `-D` gives it.
DSD_FORMATS = (("DSD_U32_BE", "u32be"), ("DSD_U32_LE", "u32le"), ("DSD_U16_BE", "u16be"),
               ("DSD_U16_LE", "u16le"), ("DSD_U8", "u8"))


def _device(card: str) -> tuple | None:
    """The device behind a card id, as far as it can change under a running
    core: for a USB card, where it sits and the number the bus gave it,
    which is new at every plug-in; None for any other card, which only a
    reboot changes."""
    found = _usb_device(card, SOUND, PROC_ASOUND)
    if found is None:
        return None
    usb = found[0]

    def read(name: str) -> str:
        try:
            return (usb / name).read_text().strip()
        except OSError:
            return ""

    return (str(usb), read("busnum"), read("devnum"))


def _current(card: str) -> None:
    """**What a card said holds only for the device that said it** (Finding
    125 #15, 2026-10-14). The answers were kept by card id for the life of
    the core, and a USB card's id comes from its product: a DAC unplugged
    and another with the same id plugged in inherited the first one's
    widening, rates and native DSD, and every renderer failed to open the
    chain until gexis-core restarted. Forgotten when the device changed, so
    the next `needs_plug` asks the new one; kept otherwise, because asking
    plays a second of zeroes on the card."""
    if card in _asked_of and _asked_of[card] != _device(card):
        for cache in (_needs_plug, _formats, _rates, _asked_of):
            cache.pop(card, None)


def native_dsd(card: str) -> str | None:
    """Squeezelite's name for the DSD format this card takes, or None for a
    card that takes no DSD (every I2S board: the Pi's I2S is PCM only)."""
    _current(card)
    formats = _formats.get(card, frozenset())
    return next((name for fmt, name in DSD_FORMATS if fmt in formats), None)


#: **ADR-0155: Squeezelite converts only the rates the card cannot take**,
#: upward to the card's highest rate. soxr's very high quality (`v`, 28-bit
#: precision, for 24-bit sources); `E`, only when the card lacks the track's
#: rate - every rate it takes still goes through untouched, bit-perfect; `X`,
#: to the card's highest rate rather than down to its own family (George,
#: 2026-10-20: *"1b"*, as Plexamp converts). Measured silence without it: a
#: USB-to-optical adapter with no 88.2 or 176.4 kHz (Finding 130).
SQUEEZELITE_RESAMPLE = "-R -u vEX"


def squeezelite_options(card: str, dsd: bool = False) -> str:
    """Squeezelite's extra options for this card: a list of rates up to
    `LYRION_MAX_RATE` for one that goes higher than Lyrion can hand over
    (ADR-0143; any other card Squeezelite asks itself), and the resampler for
    a rate the card lacks (ADR-0155). With `dsd` (ADR-0144: the volume Fixed
    and the card taking DSD), `-D` in the card's format instead of the
    resampler: Lyrion then sends DSD files as DSD and Squeezelite plays them
    natively, which a resampler in the path would turn into PCM."""
    options = []
    _current(card)
    low, high = _rates.get(card, (0, 0))
    if high > LYRION_MAX_RATE:
        options.append("-r " + ",".join(str(r) for r in SQUEEZELITE_RATES if r >= low))
    fmt = native_dsd(card) if dsd else None
    options.append(f"-D :{fmt}" if fmt else SQUEEZELITE_RESAMPLE)
    return " ".join(options)


def card_running(card: str, proc: Path = Path("/proc/asound")) -> bool:
    """Whether anything is playing on the card now (any playback substream
    RUNNING)."""
    try:
        return any("RUNNING" in p.read_text() for p in (proc / card).glob("pcm*p/sub*/status"))
    except OSError:
        return False


def write_squeezelite_env(card: str, path: Path = SQUEEZELITE_ENV, dsd: bool = False) -> bool:
    """`GEXIS_SQUEEZELITE_OPTIONS` for the unit; True if it changed. Read
    when Squeezelite starts, which the output switch does after this."""
    wanted = (
        "# Written by gexis-core for the chosen output (ADR-0143, ADR-0155). Do not edit.\n"
        f"GEXIS_SQUEEZELITE_OPTIONS={squeezelite_options(card, dsd)}\n")
    try:
        if path.read_text() == wanted:
            return False
    except OSError:
        pass
    try:
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(wanted)
        tmp.replace(path)
    except OSError as exc:
        logger.error("outputs: could not write %s: %s", path, exc)
        return False
    logger.info("outputs: squeezelite options for %s: %s", card, squeezelite_options(card, dsd) or "none")
    return True


def widens(card: str) -> bool:
    """**A card that takes 32-bit and not 16-bit gets its samples widened**
    (ADR-0143; George, 2026-10-12, an SMSL USB DAC: *"Agreed"*). Such a card
    refuses what Bluetooth sends (16-bit) and what a 24-bit source sends,
    and ADR-0009's no-`plug` chain had nothing to offer it but silence.
    `type linear` to S32_LE only *pads*: 16 and 24 bits are shifted into
    32, every sample's value kept (measured exact, 2026-10-12), 32 bits pass
    untouched, and the rate is never changed - a rate the card lacks still
    fails loudly. Asked after `needs_plug`, which reads the card."""
    _current(card)
    formats = _formats.get(card, frozenset())
    return "S32_LE" in formats and "S16_LE" not in formats


def needs_plug(card: str) -> bool | None:
    """Whether this card has to be written through a conversion layer.

    **Measured, not assumed** (2026-09-23, after George switched to HDMI 1
    and both renderers refused to play). `hw:vc4hdmi0` offers exactly one
    format — `IEC958_SUBFRAME_LE` — because the Pi's HDMI audio is carried
    as an IEC958 subframe. Every renderer sends `S16_LE` or wider, so
    `hw:` can never open it: *"unable to open audio device with any
    supported format"*, five seconds apart, for ever. The DAC offers
    `S16_LE S24_LE S32_LE` at 44100–192000 and needs nothing.

    **[ADR-0009](../../../docs/decisions/0009-logical-output-device.md)
    forbids `plug` in this chain** — *"it converts silently when formats do
    not match, which would defeat the bit-perfect claim without any
    error"* — and that prohibition is kept where it means something. An
    output that cannot accept PCM at all makes no bit-perfect claim to
    defeat: the choice there is conversion or silence.

    **A card we cannot ask keeps `hw:`.** ADR-0009 would rather fail
    loudly than convert quietly, so an unanswered question is not a licence
    to insert a converter.
    """
    _current(card)
    if card in _needs_plug:
        return _needs_plug[card]
    try:
        dump = subprocess.run(
            # **`-d 1`, and it is load-bearing.** `--dump-hw-params` is
            # meant to dump and exit, and on the HiFiBerry it does - but on
            # the Pi's own `bcm2835` card it went on to *play* the infinite
            # zeroes, timed out at eight seconds, and the switch then
            # refused to write a config it could not compute. `/dev/null`
            # instead of `/dev/zero` fixed the hang and broke the dump:
            # an empty file exits before the card is asked anything.
            # Bounding the playback keeps both (measured on all three
            # cards, 2026-09-23).
            ["aplay", "--dump-hw-params", "-D", f"hw:{card}", "-d", "1", "/dev/zero"],
            capture_output=True, text=True, timeout=8,
        ).stderr
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("outputs: could not ask %s what it takes: %s", card, exc)
        return None
    formats: set[str] = set()
    rates: tuple[int, int] | None = None
    listed: tuple[int, ...] | None = None
    for line in dump.splitlines():
        if line.startswith("FORMAT:") and not formats:
            formats = set(line.split(":", 1)[1].split())
        elif line.startswith("RATE:") and rates is None:
            found = [int(n) for n in re.findall(r"\d+", line)]
            rates = (min(found), max(found)) if found else None
            listed = tuple(found) if found and "[" not in line and "(" not in line else None
    if not formats:
        # **A busy card answers nothing, and nothing is not an answer.**
        # Caching it turned a transient "the old renderer still has this
        # open" into a permanent "this card needs no conversion", which is
        # how HDMI got written back into the config with no plug and no
        # hope (2026-09-23). Not cached, so the next ask is a real one.
        logger.warning("outputs: %s will not say what it takes while it is busy", card)
        return None
    answer = not (formats & PCM_FORMATS)
    _needs_plug[card] = answer
    _formats[card] = frozenset(formats)
    _rates.pop(card, None)
    _rate_list.pop(card, None)
    if rates is not None:
        _rates[card] = rates
        if listed is not None:
            _rate_list[card] = listed
    _asked_of[card] = _device(card)
    if answer:
        logger.info("outputs: %s takes only %s; it needs a conversion layer",
                    card, " ".join(sorted(formats)))
    return answer


def takes_rate(card: str, rate: int) -> bool | None:
    """**Whether the card plays this rate as it is** (ADR-0162, ADR-0155),
    from what it said it takes; None when it has not been asked. A card
    behind a conversion (HDMI) takes every rate."""
    if _needs_plug.get(card):
        return True
    if card in _rate_list:
        return rate in _rate_list[card]
    if card in _rates:
        low, high = _rates[card]
        return low <= rate <= high
    return None


def top_rate(card: str) -> int | None:
    """The highest rate the card said it takes, or None."""
    return _rates[card][1] if card in _rates else None


@dataclass(frozen=True)
class Output:
    card: str
    label: str
    #: The card's playback volume control, or None - which forces fixed
    #: output (ADR-0055 §4).
    control: str | None
    connected: bool = True
    #: The control's own scale (ADR-0117); None with no control.
    scale: mixer_scale.Scale | None = field(default=None, compare=False)
    #: ADR-0117 decision 2: Tested, Known or Detected; None for the Pi's
    #: own outputs.
    state: str | None = field(default=None, compare=False)
    #: What the card's driver calls it, when the list names the board
    #: otherwise - a choice stored under the old name still finds it.
    aka: str | None = field(default=None, compare=False)
    #: ADR-0124: the level set by the player's own software stage, not the
    #: card's control.
    software: bool = field(default=False, compare=False)
    #: A line under the name, from what a USB DAC reports of itself
    #: (`usb_details`); None for every other card.
    details: str | None = field(default=None, compare=False)

    #: A reported problem with this board, said under it (hardware_reports).
    problem: str | None = field(default=None, compare=False)
    #: `vendor:product` for a card on USB (ADR-0155); None for any other.
    usb_id: str | None = field(default=None, compare=False)

    @property
    def fixed_by_default(self) -> bool:
        """**Fixed in Hardware's place**, not Software (ADR-0155 decision 3):
        an output that feeds a device with its own volume - a USB-to-optical
        adapter into a DAC or receiver - plays at full level unless its owner
        chose Software."""
        return self.usb_id in FIXED_BY_DEFAULT_USB

    @property
    def option(self) -> str:
        """**The name alone** (2026-10-18; was "name - state"): whether it is
        tested is a tag beside it (`shown_tested`), as in every other list.
        A choice stored with the old word still resolves - `resolve` reads
        up to the dash - and is rewritten once (settings migration 10)."""
        return self.label if self.connected else self.label + UNPLUGGED

    @property
    def shown_tested(self) -> bool:
        """*Tested* beside it: tested here, or reported working by owners."""
        from gexis_core import hardware_reports
        return self.state in ("Tested", hardware_reports.REPORTED)


#: ADR-0124: the software stage's control, on the output's own card, and its
#: scale: -90 to 0 dB in 0.25 dB steps (361 values), finer than any card's
#: own and low enough that 0 % is silence. At 0 dB it passes every sample
#: unchanged (Finding 115).
#: The control ALSA makes is "Gexis Playback Volume" - a playback control by its
#: name; as a *simple* mixer control -
#: what amixer and the core's mixer calls address - it is "Gexis", the
#: "Volume" being its kind (2026-10-07: addressed as "Gexis Volume", every
#: write missed it and the level stayed at 0 dB).
SOFTVOL_ELEMENT = "Gexis Playback Volume"
SOFTVOL_CONTROL = "Gexis"
SOFTVOL_MIN_DB = -90.0
SOFTVOL_STEPS = 361
SOFTVOL_SCALE = mixer_scale.Scale(raw_min=0, raw_max=SOFTVOL_STEPS - 1, db_min=SOFTVOL_MIN_DB,
                                  db_step=-SOFTVOL_MIN_DB / (SOFTVOL_STEPS - 1))


#: The Pi's own outputs - not a sound card anybody added (ADR-0126).
BUILT_IN_CARDS = frozenset({"vc4hdmi0", "vc4hdmi1", "Headphones"})


def with_software_volume(output: Output) -> Output:
    """`output`, its level set by the player's software stage (ADR-0124): an
    output with no control of its own (HDMI) gains one."""
    return replace(output, control=SOFTVOL_CONTROL, scale=SOFTVOL_SCALE, software=True)


def create_softvol_control(pcm: str = "gexis_softvol") -> bool:
    """**Make the software stage's control exist without playing anything**
    (ADR-0124). ALSA creates a `softvol` control when its PCM is first
    opened, and creates it at 0 dB; the core sets the remembered level on it
    before any renderer opens the output. Open and close, non-blocking: a
    card someone is already playing to has the control already. True when
    the open succeeded or the card was busy.

    **The stage itself is opened, not `output`** (ADR-0162): with the
    equaliser on, `output` leads to the loopback and the software stage sits
    after CamillaDSP; `gexis_softvol` is the stage in both chains."""
    import ctypes
    try:
        lib = ctypes.CDLL("libasound.so.2")
    except OSError as exc:
        logger.warning("outputs: no libasound to open %s: %s", pcm, exc)
        return False
    lib.snd_pcm_open.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
    lib.snd_pcm_close.argtypes = [ctypes.c_void_p]
    handle = ctypes.c_void_p()
    # SND_PCM_STREAM_PLAYBACK = 0, SND_PCM_NONBLOCK = 1
    rc = lib.snd_pcm_open(ctypes.byref(handle), pcm.encode(), 0, 1)
    if rc < 0:
        busy = rc == -16       # EBUSY: someone holds it, so the control exists
        if not busy:
            logger.warning("outputs: could not open %s to create its volume control (%d)", pcm, rc)
        return busy
    lib.snd_pcm_close(handle)
    return True


def _softvol(name: str, slave: str, card: str) -> str:
    return f'''pcm.{name} {{
    type softvol
    slave.pcm {slave}
    control {{ name "{SOFTVOL_ELEMENT}" card {card} }}
    min_dB {SOFTVOL_MIN_DB}
    max_dB 0.0
    resolution {SOFTVOL_STEPS}
}}'''


def _run(*args: str) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("outputs: %s failed: %s", args[0], exc)
        return ""


def playback_control(card: str) -> tuple[str, mixer_scale.Scale] | tuple[None, None]:
    """The card's playback volume control and its scale, or (None, None).

    Read from `amixer contents` rather than `scontrols`, because the
    question is not what controls exist but whether one of them is a
    *playback volume* - `vc4hdmi0` has controls and none of them is.

    **Only a control that says its dB** (ADR-0117 decision 1, (a)): one
    that does not is passed over, and with none left the output is fixed.
    """
    controls = mixer_scale.playback_controls(_run("amixer", "-c", card, "contents"))
    # **Never our own software stage** (ADR-0124). It is a playback volume
    # with a dB scale on the card it plays to, so on HDMI - which has no
    # control of its own - it was taken for the card's: then parked at 0 dB
    # as the card's control is, under the level it had just been given
    # (guestpi, 2026-10-07).
    controls = [c for c in controls if c[0] != SOFTVOL_CONTROL]
    # **The list's name first** when a card has several (ADR-0117): the
    # IQaudio DAC+'s *Analogue* is a 0 / -6 dB gain switch, *Digital* the
    # volume.
    preferred = boards.mixer_for(card)
    controls.sort(key=lambda c: c[0] != preferred)
    for name, scale in controls:
        if scale is not None:
            return name, scale
        logger.warning("outputs: %s's %r gives no dB; not used for volume", card, name)
    return None, None


def _connected(card: str) -> bool:
    connector = CONNECTORS.get(card)
    if connector is None:
        return True
    for status in DRM.glob(f"card*-{connector}/status"):
        try:
            return status.read_text().strip() == "connected"
        except OSError:
            return True
    return True


#: Where the kernel lists its sound cards: a card arriving or leaving
#: changes it, and nothing else does.
CARDS = Path("/proc/asound/cards")
#: The last `discover` answer and what it was worked out from.
_DISCOVERED: dict = {}


def discover(chosen_board: str | None = None) -> list[Output]:
    """Every playback output the device actually has, ours excluded - each
    named, and given its state, as ADR-0117 says: by `chosen_board` (the
    *Sound card board* setting), the HAT's EEPROM, or the list.

    **Worked out once per change** (2026-10-05): every `GET /settings`
    lists the outputs, and `aplay` and an `amixer` per card cost 50 ms of
    it on the player. Asked again when the cards, an HDMI connection or the
    chosen board change - so a cable plugged in still shows without a
    restart (ADR-0055 §1).
    """
    product = boards.hat_product()
    if chosen_board is None:
        from gexis_core import board_apply
        written = board_apply.written()
        chosen_board = written.id if written else None
    try:
        cards = CARDS.read_text()
    except OSError:
        cards = None
    key = (cards, tuple(_connected(card) for card in CONNECTORS), chosen_board, product)
    if cards is not None and _DISCOVERED.get("key") == key:
        return list(_DISCOVERED["found"])
    found = _discover(chosen_board, product)
    _DISCOVERED.update(key=key, found=found)
    return list(found)


#: Where a card's device sits, and the USB device above it (`usb_name`).
SOUND = Path("/sys/class/sound")
PROC_ASOUND = Path("/proc/asound")
#: Product strings that name the kind of thing, not the thing: a DAC that
#: calls itself "SMSL USB AUDIO" is shown as "SMSL USB DAC".
GENERIC_PRODUCTS = frozenset({"", "USB AUDIO", "USB AUDIO DEVICE", "USB DAC", "USB AUDIO DAC", "AUDIO"})


def usb_name(card: str, sound: Path | None = None, proc: Path | None = None) -> str | None:
    """**A USB DAC by its maker** (George, 2026-10-12: *"you can see that it
    is an SMSL - why not show it in the output"*). The driver's description
    of a USB card is the class's - "USB Audio" for every one - but the
    device itself says who made it (`manufacturer`, `product` in sysfs).
    None for a card that is not on USB, or says nothing."""
    found = _usb_device(card, sound or SOUND, proc or PROC_ASOUND)
    if found is None:
        return None
    usb = found[0]

    def read(name: str) -> str:
        try:
            return " ".join((usb / name).read_text().split())
        except OSError:
            return ""

    maker, product = read("manufacturer"), read("product")
    if maker and product.upper().startswith(maker.upper()):
        product = product[len(maker):].strip()
    if product.upper() in GENERIC_PRODUCTS:
        return f"{maker} USB DAC" if maker else None
    return f"{maker} {product}" if maker else product


def _usb_device(card: str, sound: Path, proc: Path) -> tuple[Path, Path] | None:
    """(the USB device's sysfs directory, the card's /proc/asound directory),
    or None for a card that is not on USB."""
    try:
        number = (proc / card).readlink().name          # "card6"
        device = (sound / number / "device").resolve()
    except OSError:
        return None
    if "/usb" not in str(device):
        return None
    return device.parent, proc / number


#: **USB cards tested here** (ADR-0117 decision 2, ADR-0155), by
#: `vendor:product`: *Tested* beside them in Output, as a board on the list.
#: The Realtek USB-to-optical adapter: 44.1, 48, 96 and 192 kHz into the
#: SMSL's optical input, measured and heard (Finding 130).
TESTED_USB: dict[str, str] = {"0bda:4e27": "Realtek USB SPDIF Adapter (USB to optical)"}

#: ADR-0155 decision 3: the tested optical adapter only - a card is not known
#: to feed a device with its own volume until it has been tried.
FIXED_BY_DEFAULT_USB: frozenset[str] = frozenset({"0bda:4e27"})


def usb_id(card: str, sound: Path | None = None, proc: Path | None = None) -> str | None:
    """`vendor:product` of the USB device behind a card, as `lsusb` shows it;
    None for a card not on USB."""
    found = _usb_device(card, sound or SOUND, proc or PROC_ASOUND)
    if found is None:
        return None
    try:
        return ":".join((found[0] / name).read_text().strip().lower() for name in ("idVendor", "idProduct"))
    except OSError:
        return None


#: sysfs `speed` (Mbit/s) as the USB generation people know it by.
USB_SPEEDS = ((5000, "USB 3"), (480, "USB 2.0"), (0, "USB 1.1"))


def _khz(rate: int) -> str:
    return f"{rate / 1000:g} kHz"


def usb_details(card: str, sound: Path | None = None, proc: Path | None = None) -> str | None:
    """**What a USB DAC says it can do, as one line** (George, 2026-10-12:
    *"Add a second line with the details"*): the USB generation it is
    connected at, the highest rate and sample size it takes, and whether it
    takes DSD natively - read from sysfs and the driver's `stream0`, so it
    is what this DAC reports, never a model's datasheet. "USB 2.0 · up to
    768 kHz / 32-bit · native DSD" for sofapi's SMSL. None for a card not on
    USB."""
    found = _usb_device(card, sound or SOUND, proc or PROC_ASOUND)
    if found is None:
        return None
    usb, card_dir = found
    parts = []
    try:
        speed = float((usb / "speed").read_text().strip())
        parts.append(next(name for floor, name in USB_SPEEDS if speed >= floor))
    except (OSError, ValueError):
        pass
    try:
        stream = (card_dir / "stream0").read_text()
    except OSError:
        stream = ""
    # Only what the playback side offers: a DAC with a recording side lists
    # it after "Capture:".
    playback = stream.split("Capture:")[0]
    rates = [int(r) for line in re.findall(r"Rates:([^\n]*)", playback) for r in re.findall(r"\d+", line)]
    bits = [int(b) for b in re.findall(r"Bits: (\d+)", playback)]
    pcm = [f for f in re.findall(r"Format: ([^\n]*)", playback) if "DSD" not in f]
    if pcm and not bits:
        bits = [int(n) for f in pcm for n in re.findall(r"[SU](\d+)", f)]
    if rates:
        parts.append(f"up to {_khz(max(rates))}" + (f" / {max(bits)}-bit" if bits else ""))
    if re.search(r"Format: [^\n]*DSD_U", playback):
        parts.append("native DSD")
    return " · ".join(parts) or None


def hdmi_sound(card: str, proc: Path | None = None) -> tuple[str | None, str] | None:
    """**What is on an HDMI port, for sound** (George, 2026-10-13: *"add some
    information about what's on each HDMI, like we have in the video
    output"*): the name the connected device gives, and the highest rate and
    sample size it takes as PCM - from the port's ELD, which the device
    itself sends, so it is that receiver's or TV's own answer. "takes no
    sound" when it lists no PCM. None when nothing is connected, or the card
    is not an HDMI port.

    Only PCM: the Pi sends no one-bit DSD and no Dolby or DTS stream over
    HDMI, and plays two channels until Phase 15 (`ph-mpd`), so a receiver's
    other formats and its channel count would promise what does not play."""
    if card not in CONNECTORS:
        return None
    try:
        eld = next(iter(sorted((proc or PROC_ASOUND).joinpath(card).glob("eld#*")))).read_text()
    except (OSError, StopIteration):
        return None
    fields = dict(re.findall(r"^(\S+)\s+(.*)$", eld, re.M))
    if fields.get("eld_valid", "1").strip() == "0" or fields.get("monitor_present", "1").strip() == "0":
        return None
    name = fields.get("monitor_name", "").strip() or None
    rates, bits = [], []
    for i in range(int(fields.get("sad_count", "0") or 0)):
        if "LPCM" not in fields.get(f"sad{i}_coding_type", ""):
            continue
        listed = fields.get(f"sad{i}_rates", "").split("]", 1)[-1]
        rates += [int(r) for r in re.findall(r"\d+", listed)]
        listed = fields.get(f"sad{i}_bits", "").split("]", 1)[-1]
        bits += [int(b) for b in re.findall(r"\d+", listed)]
    if name is None and not rates:
        return None
    if not rates:
        return name, "takes no sound"
    return name, f"up to {_khz(max(rates))}" + (f" / {max(bits)}-bit" if bits else "")


def _discover(chosen_board: str | None, product) -> list[Output]:
    found: list[Output] = []
    # **The device's description, not the card's.** `aplay -l` gives both,
    # and the card's is the driver's module name - "snd_rpi_hifiberry_
    # dacplushd", which is what the first version put in the picker. The
    # device's is what the board calls itself: "HiFiBerry DAC+ HD HiFi
    # pcm179x-hifi-0", whose useful half is everything before " HiFi ".
    for card, description in re.findall(
        r"^card \d+: (\S+) \[[^\]]*\], device \d+: ([^\[]*)\[",
        _run("aplay", "-l"),
        re.M,
    ):
        if card in OURS or any(o.card == card for o in found):
            continue
        label = LABELS.get(card) or re.split(r" HiFi | hifi", description.strip())[0].strip() or card
        board, state = boards.identify(card, chosen=chosen_board, product=product)
        from gexis_core import hardware_reports
        problem = None if card in BUILT_IN_CARDS else hardware_reports.problem(
            hardware_reports.board(board.id if board else card))
        control, scale = playback_control(card)
        named = board.name if board else (None if card in BUILT_IN_CARDS else usb_name(card))
        on_usb = None if card in BUILT_IN_CARDS else usb_id(card)
        if on_usb in TESTED_USB:
            state = "Tested"
        found.append(
            Output(
                card=card,
                label=named or label,
                control=control,
                connected=_connected(card),
                scale=scale,
                state=state,
                aka=label if named else None,
                details=None if card in BUILT_IN_CARDS else usb_details(card),
                problem=problem,
                usb_id=on_usb,
            )
        )
    return found


#: The Pi's own headphone jack: what stands in for an HDMI output that has
#: nothing connected (ADR-0141 D5).
JACK = "Headphones"


def in_force(stored: str | None, available: list[Output] | None = None) -> tuple[Output | None, bool]:
    """**The output that plays, and whether the jack is standing in**
    (ADR-0141 D5; George, 2026-10-12: *"fallback to jack"*). The stored
    choice, as `resolve` gives it - unless that is an HDMI port with nothing
    connected (a receiver switched off), which cannot play at all (error 524,
    Finding 116): then the headphone jack, until the port comes back. The
    stored choice is never changed by this."""
    available = discover() if available is None else available
    chosen = resolve(stored, available)
    if chosen is not None and chosen.card in CONNECTORS and not chosen.connected:
        jack = next((o for o in available if o.card == JACK), None)
        if jack is not None:
            return jack, True
    return chosen, False


def configured(path: Path = CONF_PATH) -> str | None:
    """The card `output.conf` names right now, or None: `ctl.output`'s, which
    every variant has (with the equaliser on, the first slave is the
    loopback); the first slave's for a file written before that."""
    try:
        text = path.read_text()
    except OSError:
        return None
    match = re.search(r"ctl\.output\s*\{\s*type\s+hw\s+card\s+(\S+)", text)
    if match is None:
        match = re.search(r'(?:slave\.)?pcm\s+"hw:([^"]+)"', text)
    return match.group(1) if match else None


#: The missing outputs already reported, as (which, name): `resolve` runs every
#: 3 s from the stand-in watcher, and a USB DAC left unplugged would otherwise
#: be reported 28,800 times a day. Said again once it has been seen back.
_said_missing: set[tuple[str, str]] = set()


def resolve(
    stored: str | None,
    available: list[Output] | None = None,
    current: str | None = None,
) -> Output | None:
    """The output to use, given what is stored, what is configured and what
    exists. In that order, and the order is the whole of it.

    **Nothing stored means change nothing.** The first version fell
    straight through to "the first output with a volume control", which on
    this device is the Pi's own headphone jack - `aplay -l` lists card 4
    before the HiFiBerry's card 5 - so a daemon restart with no stored
    choice moved the device off the HAT and said so in the log afterwards.
    A rule for recovering from missing hardware must not fire when no
    hardware is missing.

    **ADR-0055 §3 (George: "Agreed"): never fall back to a silent one.**
    When the stored *and* configured cards are both gone, the answer is the
    first output that has a volume control, not the first output. A device
    that comes back able to play quietly is recoverable; one that comes
    back unable to play at all looks broken.
    """
    available = discover() if available is None else available
    if not available:
        return None
    current = configured() if current is None else current
    for wanted, why in ((stored, "stored"), (current, "configured")):
        if not wanted:
            continue
        wanted = wanted.split(SEP)[0]
        for output in available:
            if wanted in (output.label, output.card, output.aka):
                _said_missing.discard((why, wanted))
                return output
        if (why, wanted) not in _said_missing:
            _said_missing.add((why, wanted))
            logger.warning("outputs: the %s output %r is not here any more", why, wanted)
    for output in available:
        if output.control is not None:
            return output
    return available[0]


def _widened(card: str, wait: bool = False) -> str:
    """The card under a widening step to 32 bits (`widens`)."""
    hw = f"{{ type hw card {card} nonblock 0 }}" if wait else f'"hw:{card}"'
    return f"{{ type linear slave {{ pcm {hw} format S32_LE }} }}"


def _equalised(output: Output, plug: bool) -> tuple[str, str]:
    """**The chain with the equaliser in it** (ADR-0162 D1, D4, D8): the
    meter first, as ever, over the loopback that CamillaDSP captures; then
    CamillaDSP plays to `gexis_eq_out`, the rest of what the output's chain
    would have been - the software stage last (D8), a conversion for HDMI.

    The meter reads the music before the equaliser and its lowering, so the
    visualiser shows it as it arrives (D4), on every output: the loopback
    takes any format, so even HDMI, whose meter cannot sit over `plug`,
    keeps its levels here. One substream: whoever opens it holds it, as with
    a card, and `output_wait`'s open waits for it as for the card.

    **`output` takes integer samples only** (George, 2026-10-26: no
    visualiser with the equaliser on). The loopback takes float, and
    go-librespot asks for it first; the meter's 16-bit view has no float
    conversion, switches itself off, and the visualiser got nothing while
    Spotify played. Through `copy` and `linear`, as the software stage's
    chain does, float is refused and go-librespot plays S32_LE - what it
    plays under software volume already. `output_wait` stays as it was:
    Squeezelite, its only user, sends integers, and native DSD, which
    `linear` would refuse."""
    card = output.card
    if output.software:
        slave = f'{{ type plug slave.pcm "hw:{card}" }}' if plug else f'"hw:{card}"'
        out = f'{_softvol("gexis_softvol", slave, card)}\npcm.{EQ_OUT} "gexis_softvol"'
    elif plug:
        out = f'pcm.{EQ_OUT} {{\n    type plug\n    slave.pcm "hw:{card}"\n}}'
    else:
        out = f"pcm.{EQ_OUT} {{\n    type hw\n    card {card}\n}}"
    head = f'''pcm.output {{
    type meter
    slave.pcm {{ type copy slave.pcm {{ type linear slave {{ pcm "hw:{LOOPBACK},0,0" format S32_LE }} }} }}
    scopes.0 peppyalsa
}}

# ADR-0162: the equaliser is on for this output. CamillaDSP captures the
# loopback and plays the music, equalised, to this - the output's own chain.
{out}'''
    wait = f'''pcm.output_wait {{
    type meter
    slave.pcm {{ type hw card {LOOPBACK} device 0 subdevice 0 nonblock 0 }}
    scopes.0 peppyalsa
}}'''
    return head, wait


def render(output: Output, plug: bool, tuning: Tuning = Tuning(), widen: bool = False,
           dsd: bool = False, eq: bool = False) -> str:
    """`output.conf`, with this output's card in the two places it goes.

    The rest is verbatim from what the image ships - the comment earns its
    keep and `test_outputs.py` checks that this template and the image's
    file have not drifted apart.

    `plug` is passed in rather than asked for here, because asking means
    *opening the card*, and a caller that has not freed it first would get
    no answer and render something wrong. See `write`.

    With `eq` the renderers play into the equaliser's loopback instead
    (`_equalised`); off, the file is exactly what it was (ADR-0162 D5).
    """
    if eq:
        head, wait = _equalised(output, plug)
    elif output.software:
        # **ADR-0124: the meter first, then the software stage** (Finding
        # 115), so the visualiser shows the music as it arrives, as with the
        # card's own control. One control for both PCMs: the level is the
        # same whoever opened which.
        #
        # **On a converted chain (HDMI) too, since 2026-10-07** (ADR-0055 §6
        # as amended, Finding 116): the September failures below came from
        # the meter straight over `plug`; with `softvol` between them LMS and
        # Spotify play and the levels arrive. `plug` then converts for the
        # card, under the software stage (Finding 115).
        card = (f'{{ type plug slave.pcm "hw:{output.card}" }}' if plug
                else _widened(output.card) if widen else f'"hw:{output.card}"')
        card_wait = (f"{{ type plug slave.pcm {{ type hw card {output.card} nonblock 0 }} }}" if plug
                     else _widened(output.card, wait=True) if widen
                     else f"{{ type hw card {output.card} nonblock 0 }}")
        #
        # **A `copy` between the meter and the software stage** (Finding
        # 135): ALSA's meter reads the samples its slave holds, and a
        # `softvol` slave holds them already scaled - the visualiser saw the
        # volume's cut, and then the meter service's half of it again; at a
        # low volume the needles had nothing. `copy` keeps a buffer of its
        # own with the music as it arrives, byte for byte (Finding 135).
        head = f'''pcm.output {{
    type meter
    slave.pcm {{ type copy slave.pcm "gexis_softvol" }}
    scopes.0 peppyalsa
}}
{_softvol("gexis_softvol", card, output.card)}'''
        wait = f'''pcm.output_wait {{
    type meter
    slave.pcm {{ type copy slave.pcm "gexis_softvol_wait" }}
    scopes.0 peppyalsa
}}
{_softvol("gexis_softvol_wait", card_wait, output.card)}'''
    elif plug:
        # **No meter on a converted chain** (2026-09-23) - now only HDMI on
        # Fixed volume. With `plug` under it, ALSA's `type meter` and the peppyalsa scope come apart:
        # go-librespot dies on `pcm_meter.c:1222: snd_pcm_scope_s16_get_
        # channel_buffer: Assertion 's16->buf_areas' failed` - which is a
        # crash, not the "Spotify disconnects" it looks like from outside -
        # and squeezelite logs `_write_frames:615 mmap_commit error` ten
        # times a second and plays silence. Neither happens with the meter
        # straight over `hw:`, which is every other output.
        #
        # **The cost is the visualiser's levels on this output**, which is
        # stated rather than discovered: an output that already forfeits
        # the volume control and bit-perfect also forfeits the meters.
        # Cheaper than shipping a renderer that aborts.
        head = f'''pcm.output {{
    type plug
    slave.pcm "hw:{output.card}"
}}'''
        wait = f'''pcm.output_wait {{
    type plug
    slave.pcm {{ type hw card {output.card} nonblock 0 }}
}}'''
    elif widen:
        # ADR-0143: the meter over the widening step - measured to play and
        # meter 16, 24 and 32 bits on the SMSL, where the meter over `plug`
        # aborted (above).
        head = f'''pcm.output {{
    type meter
    slave.pcm {_widened(output.card)}
    scopes.0 peppyalsa
}}'''
        # ADR-0144: with native DSD, Squeezelite's chain goes straight to the
        # card - `type linear` takes PCM only, and Squeezelite sends 32-bit
        # PCM itself. The meter stays: peppyalsa draws nothing from DSD.
        wait_slave = (f"{{ type hw card {output.card} nonblock 0 }}" if dsd
                      else _widened(output.card, wait=True))
        wait = f'''pcm.output_wait {{
    type meter
    slave.pcm {wait_slave}
    scopes.0 peppyalsa
}}'''
    else:
        head = f'''pcm.output {{
    type meter
    slave.pcm "hw:{output.card}"
    scopes.0 peppyalsa
}}'''
        wait = f'''pcm.output_wait {{
    type meter
    slave.pcm {{ type hw card {output.card} nonblock 0 }}
    scopes.0 peppyalsa
}}'''
    return f'''{head}

# **ADR-0095: the same chain, with an open that waits.** alsa-lib opens a hw
# device non-blocking by default (`defaults.pcm.nonblock 1`) even when the
# application asked to block, so a busy DAC fails at once: squeezelite then
# sleeps a fixed 5 s, and go-librespot gives up on the track. `nonblock 0` on
# the slave lets the kernel hold the open until the renderer being released
# lets go. Only squeezelite uses this name (ADR-0095 as amended - one waiter
# cannot deadlock); `output` above is
# unchanged for everything else. `configured()` reads the card back from
# the ctl device below.
{wait}

# squeezelite's mixer resolution (-V <name>) goes through the ctl device
# matching the PCM name it was given (-O defaults to -o's value), not
# through the PCM's slave chain. Without this, "squeezelite -o output
# -V DAC" resolves against a ctl literally named "output", finds nothing,
# and silently falls back to software volume (ADR-0018) - not a squeezelite
# bug, an incomplete half of ADR-0009's indirection. This is the other half.
ctl.output {{
    type hw
    card {output.card}
}}

pcm_scope.peppyalsa {{
    type peppyalsa
    decay_ms {tuning.decay_ms}
    meter "/run/gexis/meter.fifo"
    meter_max 100
    meter_show 0
    spectrum "/run/gexis/spectrum.fifo"
    spectrum_max 100
    spectrum_size 30
    logarithmic_frequency 1
    logarithmic_amplitude 1
    smoothing_factor {tuning.smoothing_factor}
    window 3
}}

pcm_scope_type.peppyalsa {{
    lib /usr/lib/libpeppyalsa.so
}}
'''


#: **Whether the equaliser is in the path for a card** (ADR-0162): set by the
#: core from the equaliser's state, so every writer of this file agrees.
eq_in_path: Callable[[str], bool] = lambda card: False


def write(output: Output, path: Path = CONF_PATH, tuning: Tuning = Tuning(), fixed: bool = False) -> bool:
    """Put `output` in the config. True if the file changed.

    ALSA reads this when a PCM is *opened*, so writing it changes nothing
    for a renderer that already has one - which is why the caller restarts
    them (ADR-0055 §2, George: a switch may interrupt playback).
    """
    plug = needs_plug(output.card)
    if plug is None:
        # **Unknown is not False.** Asking means opening the card, and a
        # card someone else is holding answers nothing - which on
        # 2026-09-23 wrote HDMI back into the config with no conversion
        # layer, twice, because "no answer" had been folded into "needs
        # nothing". A config that cannot be computed is not written.
        logger.error(
            "outputs: leaving %s alone - cannot tell what hw:%s takes while it is in use",
            path, output.card,
        )
        return False
    # ADR-0144: native DSD only with the volume Fixed - DSD cannot be
    # attenuated by the software stage, nor read by it - on a card taking it.
    dsd = fixed and not output.software and not plug and native_dsd(output.card) is not None
    wanted = render(output, plug, tuning, widen=not plug and widens(output.card), dsd=dsd,
                    eq=eq_in_path(output.card))
    # ADR-0143: Squeezelite's rates follow the card; restarted with the
    # renderers after this, as the config is. The device's own file only.
    if path == CONF_PATH:
        write_squeezelite_env(output.card, dsd=dsd)
    try:
        if path.read_text() == wanted:
            logger.info("outputs: %s is already the output", output.label)
            return False
    except OSError:
        pass
    try:
        path.write_text(wanted)
    except OSError as exc:
        logger.error("outputs: could not write %s: %s", path, exc)
        return False
    logger.info("outputs: %s -> hw:%s (control %s)", path, output.card, output.control)
    return True
