# SPDX-License-Identifier: GPL-3.0-or-later
"""**A simple equaliser** (ADR-0162, Phase 20): ten bands an octave apart,
each −12 to +12 dB, the presets, up to ten of the owner's own, and the
choice kept for each output.

What is here touches no device: the bands and presets (the design's
`eq-data.js`, ported as-is), the state for each output and the owner's
list, the operations on them, the headroom (D3) and CamillaDSP's
configuration. `eq_engine.py` runs it on the loopback.

**The bands are ten Peaking filters**, not CamillaDSP's GraphicEqualizer
(Finding 138): the GraphicEqualizer rebuilds its filters on every change,
which clicks, and cannot place a 16 kHz band at 44.1 kHz. A Peaking filter
whose gain changes keeps its state; all ten stay in the pipeline at 0 dB so
that moving a band never changes the pipeline's shape.
"""
from __future__ import annotations

import functools
import math
from dataclasses import dataclass, field, replace

#: The bands' labels, low to high, and their centres (31.25 × 2ⁿ Hz).
BANDS = ("31", "63", "125", "250", "500", "1k", "2k", "4k", "8k", "16k")
CENTRES = tuple(31.25 * 2 ** i for i in range(len(BANDS)))
#: One octave wide: the RBJ cookbook's Q for a bandwidth of one octave.
Q = math.sqrt(2)
GAIN_MIN, GAIN_MAX = -12, 12
#: The owner's own settings: one list for every output (decision 3).
OWN_MAX = 10
NAME_MAX = 40

FLAT = (0,) * len(BANDS)


@dataclass(frozen=True)
class Preset:
    key: str
    name: str
    gains: tuple[int, ...]


#: ADR-0162's starting values, low band to high; tuned by ear before the
#: phase closes.
PRESETS = (
    Preset("flat", "Flat", FLAT),
    Preset("rock", "Rock", (4, 3, 2, 0, -1, -1, 0, 2, 3, 4)),
    Preset("pop", "Pop", (-1, 0, 2, 3, 2, 0, -1, -1, 0, 1)),
    Preset("jazz", "Jazz", (3, 2, 1, 2, -1, -1, 0, 1, 2, 3)),
    Preset("classical", "Classical", (3, 2, 1, 0, 0, 0, 0, -1, -1, -2)),
    Preset("electronic", "Electronic", (4, 4, 1, 0, -2, 1, 0, 1, 3, 4)),
    Preset("hiphop", "Hip-hop", (5, 4, 1, 2, -1, -1, 1, -1, 2, 3)),
    Preset("acoustic", "Acoustic", (3, 3, 2, 1, 1, 1, 2, 3, 2, 1)),
    Preset("vocal", "Vocal", (-2, -1, -1, 0, 2, 3, 3, 2, 0, -1)),
    Preset("late", "Late night", (5, 4, 2, 0, 0, 0, 0, 1, 2, 3)),
)
PRESET = {p.key: p for p in PRESETS}

CUSTOM = "custom"
OWN_PREFIX = "own-"


class EqualiserError(ValueError):
    """A request the equaliser refuses; its message is for the person."""


def gains_from(value) -> tuple[int, ...]:
    """Ten whole decibels, each within ±12, or EqualiserError."""
    if not isinstance(value, (list, tuple)) or len(value) != len(BANDS):
        raise EqualiserError(f"Ten bands are needed, low to high.")
    out = []
    for g in value:
        if isinstance(g, bool) or not isinstance(g, (int, float)) or g != g:
            raise EqualiserError("Each band is a number of decibels.")
        if not GAIN_MIN <= g <= GAIN_MAX:
            raise EqualiserError(f"Each band is from {GAIN_MIN} to +{GAIN_MAX} dB.")
        out.append(int(round(g)))
    return tuple(out)


# ---- the curve and the headroom (D3) ---------------------------------------

#: The headroom is the worse of the two lowest rates, so the figure shown is
#: one number whatever plays (decision, 2026-10-25). The higher rates come
#: within 0.01 dB of them for every preset: the peak is in the bass and
#: middle, where the rate changes nothing; near half the rate the top band
#: narrows, which only lowers it.
RATES = (44100, 48000)
#: As the design samples it: 241 points from half an octave below the first
#: band to 20 kHz.
_POINTS = 241
_OCT_END = math.log2(20000 / CENTRES[0])


def band_db(f0: float, gain: float, f: float, fs: float) -> float:
    """One Peaking filter's response in dB at `f` (RBJ cookbook)."""
    if not gain:
        return 0.0
    a = 10 ** (gain / 40)
    w0 = 2 * math.pi * f0 / fs
    alpha = math.sin(w0) / (2 * Q)
    c = math.cos(w0)
    b0, b1, b2 = 1 + alpha * a, -2 * c, 1 - alpha * a
    a0, a1, a2 = 1 + alpha / a, -2 * c, 1 - alpha / a
    w = 2 * math.pi * f / fs
    cw, sw, c2, s2 = math.cos(w), math.sin(w), math.cos(2 * w), math.sin(2 * w)
    nr, ni = b0 + b1 * cw + b2 * c2, -(b1 * sw + b2 * s2)
    dr, di = a0 + a1 * cw + a2 * c2, -(a1 * sw + a2 * s2)
    return 10 * math.log10((nr * nr + ni * ni) / (dr * dr + di * di))


def response_db(gains, f: float, fs: float = 48000) -> float:
    """The ten filters together, in dB at `f`: neighbouring boosts add up."""
    return sum(band_db(c, g, f, fs) for c, g in zip(CENTRES, gains))


def peak_db(gains, fs: float = 48000) -> float:
    peak = 0.0
    for j in range(_POINTS):
        octave = -0.5 + (_OCT_END + 0.5) * j / (_POINTS - 1)
        f = CENTRES[0] * 2 ** octave
        if f < fs / 2:
            peak = max(peak, response_db(gains, f, fs))
    return peak


@functools.lru_cache(maxsize=256)
def headroom_db(gains: tuple[int, ...]) -> float:
    """**How far the signal is lowered before the bands** (ADR-0162 D3):
    the combined curve's highest point at the worst rate, rounded up to
    0.5 dB; nothing when the curve does not rise. Rounded strictly up, so
    the lowering is never less than the boost (the design's drawing allows
    0.05 dB the other way)."""
    peak = max(peak_db(gains, fs) for fs in RATES)
    if peak <= 0.05:
        return 0.0
    return math.ceil(peak * 2 - 1e-9) / 2


# ---- the state ---------------------------------------------------------------


@dataclass(frozen=True)
class Own:
    """One of the owner's settings."""
    key: str
    name: str
    gains: tuple[int, ...]

    def as_dict(self) -> dict:
        return {"key": self.key, "name": self.name, "gains": list(self.gains)}


@dataclass(frozen=True)
class OutputEq:
    """What one output keeps (decision 3): whether the equaliser is on, the
    setting in use, and the bands. `sel` is a preset's key, an own setting's
    key or `custom`; `source` is what Custom was moved from."""
    on: bool = False
    sel: str = "flat"
    source: str | None = None
    gains: tuple[int, ...] = FLAT

    def as_dict(self) -> dict:
        return {"on": self.on, "sel": self.sel, "from": self.source, "gains": list(self.gains)}


@dataclass(frozen=True)
class Equaliser:
    outputs: dict = field(default_factory=dict)   # output key -> OutputEq
    own: tuple[Own, ...] = ()

    def output(self, key: str) -> OutputEq:
        return self.outputs.get(key, OutputEq())

    def own_by_key(self, key: str) -> Own | None:
        return next((o for o in self.own if o.key == key), None)

    def name_of(self, sel: str | None) -> str | None:
        if sel is None:
            return None
        if sel in PRESET:
            return PRESET[sel].name
        own = self.own_by_key(sel)
        return own.name if own else None

    def _with(self, key: str, eq: OutputEq) -> Equaliser:
        outputs = dict(self.outputs)
        outputs[key] = eq
        return replace(self, outputs=outputs)

    # -- the operations; each returns a new Equaliser --

    def set_on(self, key: str, on: bool) -> Equaliser:
        return self._with(key, replace(self.output(key), on=bool(on)))

    def choose(self, key: str, sel: str) -> Equaliser:
        """A preset or one of the owner's, for this output. Custom is not
        chosen: it is where moving a band leads."""
        if sel in PRESET:
            gains = PRESET[sel].gains
        else:
            own = self.own_by_key(sel)
            if own is None:
                raise EqualiserError("That setting is not there any more.")
            gains = own.gains
        return self._with(key, replace(self.output(key), sel=sel, source=None, gains=gains))

    def set_gains(self, key: str, gains) -> Equaliser:
        """The bands as set by hand: Custom, from what was in use. Bands
        that match the setting in use leave it chosen."""
        gains = gains_from(gains)
        eq = self.output(key)
        if gains == eq.gains:
            return self
        if eq.sel == CUSTOM:
            source = eq.source
        else:
            source = eq.sel
        if source is not None and self._gains_of(source) == gains:
            return self._with(key, replace(eq, sel=source, source=None, gains=gains))
        return self._with(key, replace(eq, sel=CUSTOM, source=source, gains=gains))

    def set_band(self, key: str, band: int, gain) -> Equaliser:
        if not isinstance(band, int) or isinstance(band, bool) or not 0 <= band < len(BANDS):
            raise EqualiserError("There are ten bands, 0 to 9.")
        gains = list(self.output(key).gains)
        gains[band] = gain
        return self.set_gains(key, gains)

    def _gains_of(self, sel: str):
        if sel in PRESET:
            return PRESET[sel].gains
        own = self.own_by_key(sel)
        return own.gains if own else None

    def _clean_name(self, name, keep: str | None = None) -> str:
        if not isinstance(name, str) or not " ".join(name.split()):
            raise EqualiserError("Give it a name.")
        name = " ".join(name.split())
        if len(name) > NAME_MAX:
            raise EqualiserError(f"A name is at most {NAME_MAX} characters.")
        taken = {o.name.casefold() for o in self.own if o.key != keep}
        taken |= {p.name.casefold() for p in PRESETS}
        if name.casefold() in taken:
            raise EqualiserError(f"There is a setting called {name} already.")
        return name

    def save_as(self, key: str, name) -> tuple[Equaliser, Own]:
        """The bands as set on this output, saved as one of the owner's; the
        output then uses it."""
        if len(self.own) >= OWN_MAX:
            raise EqualiserError(f"Ten saved already. Delete one to save another.")
        name = self._clean_name(name)
        used = {o.key for o in self.own}
        n = next(i for i in range(1, OWN_MAX * 10) if f"{OWN_PREFIX}{i}" not in used)
        own = Own(f"{OWN_PREFIX}{n}", name, self.output(key).gains)
        eq = replace(self.output(key), sel=own.key, source=None)
        return replace(self, own=self.own + (own,))._with(key, eq), own

    def rename(self, own_key: str, name) -> Equaliser:
        if self.own_by_key(own_key) is None:
            raise EqualiserError("That setting is not there any more.")
        name = self._clean_name(name, keep=own_key)
        return replace(self, own=tuple(replace(o, name=name) if o.key == own_key else o
                                       for o in self.own))

    def delete(self, own_key: str) -> Equaliser:
        """**An output that uses it goes back to Flat** (decision,
        2026-10-25: the design's open point); Custom moved from it keeps its
        bands and forgets where they came from."""
        if self.own_by_key(own_key) is None:
            raise EqualiserError("That setting is not there any more.")
        outputs = {}
        for k, eq in self.outputs.items():
            if eq.sel == own_key:
                eq = replace(eq, sel="flat", source=None, gains=FLAT)
            elif eq.source == own_key:
                eq = replace(eq, source=None)
            outputs[k] = eq
        return replace(self, outputs=outputs, own=tuple(o for o in self.own if o.key != own_key))

    # -- stored as settings --

    def to_settings(self) -> dict:
        return {
            "outputs": {k: v.as_dict() for k, v in sorted(self.outputs.items())},
            "own": [o.as_dict() for o in self.own],
        }

    @classmethod
    def from_settings(cls, value) -> Equaliser:
        """Whatever is stored, read leniently: a bad entry is dropped, not
        fatal, so a hand-edited file cannot stop the core."""
        value = value if isinstance(value, dict) else {}
        own = []
        for item in value.get("own") or []:
            try:
                key, name = item["key"], item["name"]
                if not (isinstance(key, str) and key.startswith(OWN_PREFIX) and isinstance(name, str)):
                    continue
                if any(o.key == key for o in own):
                    continue
                own.append(Own(key, name[:NAME_MAX], gains_from(item["gains"])))
            except (KeyError, TypeError, EqualiserError):
                continue
        own = own[:OWN_MAX]
        keys = {o.key for o in own}
        outputs = {}
        for k, item in (value.get("outputs") or {}).items():
            try:
                gains = gains_from(item.get("gains", FLAT))
                sel = item.get("sel", "flat")
                source = item.get("from")
                if sel not in PRESET and sel not in keys and sel != CUSTOM:
                    sel, gains = "flat", FLAT
                if source not in PRESET and source not in keys:
                    source = None
                outputs[str(k)] = OutputEq(bool(item.get("on", False)), sel, source, gains)
            except (AttributeError, TypeError, EqualiserError):
                continue
        return cls(outputs, tuple(own))


# ---- CamillaDSP ---------------------------------------------------------------

#: The fader the headroom rides on: Aux1, so the lowering ramps instead of
#: stepping (Finding 138: a stepped gain left −53 dBFS).
HEADROOM_FADER = 1
HEADROOM_RAMP_MS = 200

#: ALSA's sample formats, as the loopback reports them, to CamillaDSP's.
FORMATS = {
    "S16_LE": "S16_LE",
    "S24_LE": "S24_4_RJ_LE",
    "S24_3LE": "S24_3_LE",
    "S32_LE": "S32_LE",
    "FLOAT_LE": "F32_LE",
    "FLOAT64_LE": "F64_LE",
}


def chunksize(rate: int) -> int:
    """About 23 ms a chunk, CamillaDSP's suggestion for each rate."""
    return 1024 if rate <= 48000 else 2048 if rate <= 96000 else 4096


def filter_name(band: int) -> str:
    return f"band_{BANDS[band]}"


def camilla_config(rate: int, fmt: str, channels: int, gains, playback: str) -> dict:
    """**CamillaDSP's configuration for one stream**: captured from the
    loopback at the stream's own rate, format and channels (the renderer
    opened it first and set them), lowered on the headroom fader, then the
    ten bands, played to `playback` (the rest of the output's chain).

    Rate adjust tunes the loopback's clock to the card's (*PCM Rate Shift*),
    which passes the samples through unchanged; `stop_on_inactive` lets the
    loopback go when the stream ends, so the next one can open at its own
    rate (Finding 138)."""
    if fmt not in FORMATS:
        raise EqualiserError(f"CamillaDSP does not take {fmt}.")
    gains = gains_from(gains)
    filters = {"headroom": {"type": "Volume",
                            "parameters": {"ramp_time": HEADROOM_RAMP_MS, "fader": f"Aux{HEADROOM_FADER}"}}}
    for i, (centre, gain) in enumerate(zip(CENTRES, gains)):
        filters[filter_name(i)] = {"type": "Biquad",
                                   "parameters": {"type": "Peaking", "freq": centre, "gain": gain, "q": Q}}
    return {
        "title": "Gexis Player equaliser",
        "devices": {
            "samplerate": rate,
            "chunksize": chunksize(rate),
            "enable_rate_adjust": True,
            "capture": {"type": "Alsa", "channels": channels, "device": "hw:Loopback,1,0",
                        "format": FORMATS[fmt], "stop_on_inactive": True},
            "playback": {"type": "Alsa", "channels": channels, "device": playback},
        },
        "filters": filters,
        "pipeline": [{"type": "Filter", "names": ["headroom"] + [filter_name(i) for i in range(len(BANDS))]}],
    }
