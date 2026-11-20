"""A room made up for room correction's tests (ADR-0175, ADR-0177): a speaker
that rolls off below 30 Hz, modes - peaks and dips - that move a little from
one position to the next and differ between the speakers, and broad bumps and
dips above the bass."""
import math

import asyncio

import numpy as np

from gexis_core import room_dsp as rd

#: (frequency, dB at the mode, Q): peaks and two dips, as the design's room.
MODES = ((42, 8.0, 6.0), (65, -8.0, 8.0), (87, 10.0, 7.0), (110, -5.0, 7.0), (126, 4.0, 6.0), (170, 6.0, 6.0))
#: Above the bass (ADR-0177): broad, as a speaker in a room has them - a dip
#: and two bumps, each about an octave or more wide.
BROAD = ((450, -5.0, 1.4), (1800, 4.0, 1.2), (6000, -3.5, 1.0))


def response(f, modes=MODES, seed: int = 0, spread: float = 0.03, delay_s: float = 0.003,
             broad=BROAD) -> np.ndarray:
    """The room's complex response at `f` for one speaker at one position."""
    rng = np.random.default_rng(seed)
    f = np.asarray(f, dtype=float)
    s = 1j * f
    # The speaker: a second-order high-pass at 30 Hz.
    hp = (s / 30) ** 2 / ((s / 30) ** 2 + s / (30 * 0.707) + 1)
    total = np.ones_like(f, dtype=complex)
    for fm, db, q in modes:
        fm = fm * (1 + (rng.random() - 0.5) * 2 * spread)
        db = db * (0.8 + 0.4 * rng.random())
        g = 10 ** (db / 20) - 1
        band = (s / (q * fm)) / (1 + s / (q * fm) + (s / fm) ** 2)
        total += g * band
    for fm, db, q in broad:
        # Peaking filters, a little different at each position.
        db = db * (0.9 + 0.2 * rng.random())
        a = 10 ** (db / 40)
        x = s / fm
        total *= (x * x + x * a / q + 1) / (x * x + x / (a * q) + 1)
    return hp * total * np.exp(-2j * np.pi * f * delay_s)


def impulse(seed: int = 0, fs: int = rd.FS, seconds: float = 1.4, modes=MODES, gain: float = 1.0,
            broad=BROAD, delay_s: float = 0.003) -> np.ndarray:
    n = 1 << int(math.ceil(math.log2(seconds * fs)))
    f = np.fft.rfftfreq(n, 1 / fs)
    h = response(f, modes, seed, broad=broad, delay_s=delay_s)
    h[0] = 0
    return gain * np.fft.irfft(h, n)


def record(played, seed: int = 0, gain: float = 1.0, noise_db: float = -90.0, lead_s: float = 0.3,
           tail_s: float = 1.5, burst: tuple[float, float] | None = None, modes=MODES,
           fs: int = rd.FS, broad=BROAD, delay_s: float = 0.003, length: int | None = None,
           noise_seed: int | None = None) -> np.ndarray:
    """What a microphone would record of `played` through the room: a lead
    of silence, the room's answer and its tail, the floor's noise, and a
    burst (start s, dB of full scale) if asked."""
    played = np.asarray(played, dtype=float)
    ir = impulse(seed, fs, modes=modes, gain=gain, broad=broad, delay_s=delay_s)
    n = length or len(played) + int((lead_s + tail_s) * fs)
    out = np.zeros(n)
    size = 1 << int(math.ceil(math.log2(len(played) + len(ir))))
    wet = np.fft.irfft(np.fft.rfft(played, size) * np.fft.rfft(ir, size), size)[: n - int(lead_s * fs)]
    out[int(lead_s * fs): int(lead_s * fs) + len(wet)] += wet
    rng = np.random.default_rng(seed + 1000 if noise_seed is None else noise_seed)
    out += rng.standard_normal(n) * 10 ** (noise_db / 20)
    if burst is not None:
        # A thump - a door, a footstep: its power below 300 Hz, at `db`.
        start, db = burst
        i = int(start * fs)
        m = min(int(0.25 * fs), n - i)
        noise = np.fft.rfft(rng.standard_normal(m))
        noise[np.fft.rfftfreq(m, 1 / fs) > 300] = 0
        thump = np.fft.irfft(noise, m)
        out[i:i + m] += thump / np.sqrt(np.mean(thump ** 2)) * 10 ** (db / 20)
    return out


def positions(n: int = 3, channel: int = 0, modes=MODES) -> list[int]:
    """Seeds for `n` positions of one speaker."""
    return [channel * 100 + k + 1 for k in range(n)]


def curve(seed: int, modes=MODES, grid=rd.GRID, broad=BROAD) -> np.ndarray:
    """The 1/6-octave curve a measurement at this seed should come to."""
    fs = rd.FS
    n = 1 << 18
    f = np.fft.rfftfreq(n, 1 / fs)
    h = response(f, modes, seed, broad=broad)
    return rd.response_db(np.fft.irfft(h, n)[: int(rd.WINDOW_S * fs)], fs, grid)


#: Speakers at ±30° about 2.7 m away: 40 cm to the left (position 2) the
#: left is about 20 cm nearer and the right 20 cm further; to the right
#: (position 3) the other way; 30 cm in front (4) both about 26 cm nearer,
#: 30 cm above (5) both about 2 cm further (ADR-0187 D3).
SIDES = {1: (0.0080, 0.0080), 2: (0.0074, 0.0086), 3: (0.0086, 0.0074), 4: (0.0072, 0.0072),
         5: (0.00805, 0.00805)}


class Audio:
    """The microphone in a made-up room: where it is, how loud the system
    plays, and a noise when asked for."""

    def __init__(self, offset=120.0, modes=MODES, bursts=(), noise_db=-110.0, gain=1.0, broad=BROAD,
                 jitter_s=0.0):
        self.offset = offset
        #: ADR-0185: each speaker's distance as its sound's delay, by position
        #: (the same everywhere unless a test sets `SIDES`), and its polarity;
        #: `swapped` plays the left channel from the right speaker.
        self.delays = {n: (0.003, 0.003) for n in range(1, 6)}
        self.polarity = (1.0, 1.0)
        self.swapped = False
        #: How far apart the recording and the playback start, at random up
        #: to this, each time (`Audio.play` starts `arecord` and `aplay` apart).
        self.jitter_s = jitter_s
        self._rng = np.random.default_rng(7)
        self.calls = 0
        self.noise_db = noise_db
        self.gain = gain
        self.modes = modes
        self.broad = broad
        self.peaks = []     # each sweep's highest sample, as played
        self.position = 1
        self.plays = []
        self.bursts = list(bursts)    # the n-th sweep (1-based) gets a thump
        self.sweeps = 0
        self.stage = None

    def spl_offset(self, cal):
        return self.offset

    def _speaker(self, c: int) -> int:
        return 1 - c if self.swapped else c

    async def play(self, signal, channel, tail_s=1.1):
        """`channel`: a speaker, a tuple of them (a sweep through both), or
        None (the level step's noise, which the left speaker stands for).
        `signal` as (samples, 2) frames plays each column to its speaker
        (ADR-0185's timing), `channel` then unused."""
        signal = np.asarray(signal, dtype=float)
        frames = signal.ndim == 2
        self.plays.append(("frames" if frames else channel, self.position))
        self.calls += 1
        # The sweeps counted and their peaks kept: the timing's are not
        # (ADR-0185), so `bursts` names a sweep as before.
        if channel is not None and not frames:
            self.sweeps += 1
            self.peaks.append(float(np.max(np.abs(signal))))
        burst = (0.5, -20) if (channel is not None and not frames and self.sweeps in self.bursts) else None
        if frames:
            parts = [(c, signal[:, c]) for c in (0, 1) if np.any(signal[:, c])]
        else:
            speakers = (0,) if channel is None else (channel,) if isinstance(channel, int) else tuple(channel)
            parts = [(c, signal) for c in speakers]
        lead = 0.3 + (self._rng.random() * self.jitter_s if self.jitter_s else 0.0)
        length = len(signal) + int((lead + tail_s) * rd.FS)
        recording = None
        for k, (c, played) in enumerate(parts):
            heard = self._speaker(c)
            # The room's noise and a thump once, however many speakers play.
            part = record(played, seed=heard * 100 + self.position, modes=self.modes,
                          noise_db=self.noise_db if k == 0 else -300.0, burst=burst if k == 0 else None,
                          tail_s=tail_s, gain=self.gain * self.polarity[heard], broad=self.broad,
                          delay_s=self.delays[self.position][heard], lead_s=lead, length=length,
                          noise_seed=self.calls + 5000)
            if self.stage is not None and channel is not None and not frames:
                # The stage's filters, as CamillaDSP would play them.
                cuts = [rd.Cut(f, g, q) for f, g, q in tuple(self.stage.cuts[c]) + tuple(self.stage.above[c])]
                n = 1 << int(math.ceil(math.log2(len(part))))
                spec = np.fft.rfft(part, n)
                f = np.fft.rfftfreq(n, 1 / rd.FS)
                spec *= 10 ** (rd.cuts_db(cuts, np.maximum(f, 1e-3)) / 20)
                part = np.fft.irfft(spec, n)[: len(part)]
            if self.stage is not None and getattr(self.stage, "delay", None):
                # The stage's delay on this channel (ADR-0185 D2).
                shift = int(round(self.stage.delay[c] / 1000 * rd.FS))
                if shift:
                    part = np.concatenate((np.zeros(shift), part[:-shift]))
            recording = part if recording is None else recording + part
        await asyncio.sleep(0)
        return recording
