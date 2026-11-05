"""A room made up for room correction's tests (ADR-0175): a speaker that
rolls off below 30 Hz, and modes - peaks and dips - that move a little from
one position to the next and differ between the speakers."""
import math

import asyncio

import numpy as np

from gexis_core import room_dsp as rd

#: (frequency, dB at the mode, Q): peaks and two dips, as the design's room.
MODES = ((42, 8.0, 6.0), (65, -8.0, 8.0), (87, 10.0, 7.0), (110, -5.0, 7.0), (126, 4.0, 6.0), (170, 6.0, 6.0))


def response(f, modes=MODES, seed: int = 0, spread: float = 0.03, delay_s: float = 0.003) -> np.ndarray:
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
    return hp * total * np.exp(-2j * np.pi * f * delay_s)


def impulse(seed: int = 0, fs: int = rd.FS, seconds: float = 1.4, modes=MODES, gain: float = 1.0) -> np.ndarray:
    n = 1 << int(math.ceil(math.log2(seconds * fs)))
    f = np.fft.rfftfreq(n, 1 / fs)
    h = response(f, modes, seed)
    h[0] = 0
    return gain * np.fft.irfft(h, n)


def record(played, seed: int = 0, gain: float = 1.0, noise_db: float = -90.0, lead_s: float = 0.3,
           tail_s: float = 1.5, burst: tuple[float, float] | None = None, modes=MODES,
           fs: int = rd.FS) -> np.ndarray:
    """What a microphone would record of `played` through the room: a lead
    of silence, the room's answer and its tail, the floor's noise, and a
    burst (start s, dB of full scale) if asked."""
    played = np.asarray(played, dtype=float)
    ir = impulse(seed, fs, modes=modes, gain=gain)
    n = len(played) + int((lead_s + tail_s) * fs)
    out = np.zeros(n)
    size = 1 << int(math.ceil(math.log2(len(played) + len(ir))))
    wet = np.fft.irfft(np.fft.rfft(played, size) * np.fft.rfft(ir, size), size)[: n - int(lead_s * fs)]
    out[int(lead_s * fs): int(lead_s * fs) + len(wet)] += wet
    rng = np.random.default_rng(seed + 1000)
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


def positions(n: int = 5, channel: int = 0, modes=MODES) -> list[int]:
    """Seeds for `n` positions of one speaker."""
    return [channel * 100 + k + 1 for k in range(n)]


def curve(seed: int, modes=MODES, grid=rd.GRID) -> np.ndarray:
    """The 1/6-octave curve a measurement at this seed should come to."""
    fs = rd.FS
    n = 1 << 18
    f = np.fft.rfftfreq(n, 1 / fs)
    h = response(f, modes, seed)
    return rd.response_db(np.fft.irfft(h, n)[: int(rd.WINDOW_S * fs)], fs, grid)


class Audio:
    """The microphone in a made-up room: where it is, how loud the system
    plays, and a noise when asked for."""

    def __init__(self, offset=120.0, modes=MODES, bursts=()):
        self.offset = offset
        self.modes = modes
        self.position = 1
        self.plays = []
        self.bursts = list(bursts)    # the n-th sweep (1-based) gets a thump
        self.sweeps = 0
        self.stage = None

    def spl_offset(self, cal):
        return self.offset

    async def play(self, signal, channel):
        self.plays.append((channel, self.position))
        seed = (channel or 0) * 100 + self.position
        if channel is not None:
            self.sweeps += 1
        burst = (0.5, -20) if (channel is not None and self.sweeps in self.bursts) else None
        modes = self.modes
        recording = record(signal, seed=seed, modes=modes, noise_db=-110, burst=burst, tail_s=1.1)
        if self.stage is not None and channel is not None:
            # The stage's cuts, as CamillaDSP would play them.
            cuts = [rd.Cut(f, g, q) for f, g, q in self.stage[channel]]
            n = 1 << int(math.ceil(math.log2(len(recording))))
            spec = np.fft.rfft(recording, n)
            f = np.fft.rfftfreq(n, 1 / rd.FS)
            spec *= 10 ** (rd.cuts_db(cuts, np.maximum(f, 1e-3)) / 20)
            recording = np.fft.irfft(spec, n)[: len(recording)]
        await asyncio.sleep(0)
        return recording
