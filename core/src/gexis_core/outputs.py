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
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("gexis_core.outputs")

CONF_PATH = Path("/etc/alsa/conf.d/output.conf")
DRM = Path("/sys/class/drm")

#: Our own snd-dummy cards. They have a mixer and no audio path, which is
#: exactly the shape that would otherwise pass every test below.
OURS = frozenset({"gexislmsvol", "gexisbtvol"})

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

#: **George, 2026-09-23:** *"Offer all, but maybe it clears that the one
#: that is not connected looks disabled or has a note saying that nothing
#: is connected."* The suffix is display only - `resolve` matches on what
#: comes before it, so plugging a cable in does not orphan a stored choice.
UNPLUGGED = " — nothing connected"


#: Formats a renderer actually produces. A card offering none of them
#: cannot be written to without conversion.
PCM_FORMATS = frozenset(
    {"S16_LE", "S16_BE", "S24_LE", "S24_BE", "S24_3LE", "S32_LE", "S32_BE", "U8"}
)

_needs_plug: dict[str, bool] = {}


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
    for line in dump.splitlines():
        if line.startswith("FORMAT:"):
            formats = set(line.split(":", 1)[1].split())
            break
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
    if answer:
        logger.info("outputs: %s takes only %s; it needs a conversion layer",
                    card, " ".join(sorted(formats)))
    return answer


@dataclass(frozen=True)
class Output:
    card: str
    label: str
    #: The card's playback volume control, or None - which forces fixed
    #: output (ADR-0055 §4).
    control: str | None
    connected: bool = True

    @property
    def option(self) -> str:
        return self.label if self.connected else self.label + UNPLUGGED


def _run(*args: str) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("outputs: %s failed: %s", args[0], exc)
        return ""


def playback_control(card: str) -> str | None:
    """The card's playback volume control, or None if it has none.

    Read from `amixer contents` rather than `scontrols`, because the
    question is not what controls exist but whether one of them is a
    *playback volume* - `vc4hdmi0` has controls and none of them is.
    """
    contents = _run("amixer", "-c", card, "contents")
    for name, following in re.findall(
        r"name='([^']+) Playback Volume'\n([^\n]*)", contents
    ):
        if "type=INTEGER" in following:
            return name
    return None


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


def discover() -> list[Output]:
    """Every playback output the device actually has, ours excluded."""
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
        label = LABELS.get(card) or re.split(r" HiFi | hifi", description.strip())[0].strip()
        found.append(
            Output(
                card=card,
                label=label or card,
                control=playback_control(card),
                connected=_connected(card),
            )
        )
    return found


def configured(path: Path = CONF_PATH) -> str | None:
    """The card `output.conf` names right now, or None."""
    try:
        match = re.search(r'slave\.pcm\s+"hw:([^"]+)"', path.read_text())
    except OSError:
        return None
    return match.group(1) if match else None


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
        wanted = wanted.split(UNPLUGGED)[0]
        for output in available:
            if wanted in (output.label, output.card):
                return output
        logger.warning("outputs: the %s output %r is not here any more", why, wanted)
    for output in available:
        if output.control is not None:
            return output
    return available[0]


def render(output: Output, plug: bool) -> str:
    """`output.conf`, with this output's card in the two places it goes.

    The rest is verbatim from what the image ships - the comment earns its
    keep and `test_outputs.py` checks that this template and the image's
    file have not drifted apart.

    `plug` is passed in rather than asked for here, because asking means
    *opening the card*, and a caller that has not freed it first would get
    no answer and render something wrong. See `write`.
    """
    if plug:
        # **No meter on a converted chain** (2026-09-23). With `plug` under
        # it, ALSA's `type meter` and the peppyalsa scope come apart:
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
    else:
        head = f'''pcm.output {{
    type meter
    slave.pcm "hw:{output.card}"
    scopes.0 peppyalsa
}}'''
    return f'''{head}

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
    decay_ms 400
    meter "/run/gexis/meter.fifo"
    meter_max 100
    meter_show 0
    spectrum "/run/gexis/spectrum.fifo"
    spectrum_max 100
    spectrum_size 30
    logarithmic_frequency 1
    logarithmic_amplitude 1
    smoothing_factor 50
    window 3
}}

pcm_scope_type.peppyalsa {{
    lib /usr/lib/libpeppyalsa.so
}}
'''


def write(output: Output, path: Path = CONF_PATH) -> bool:
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
    wanted = render(output, plug)
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
