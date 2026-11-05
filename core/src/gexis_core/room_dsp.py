# SPDX-License-Identifier: GPL-3.0-or-later
"""**Room correction's numbers** (ADR-0175, Phase 29): the sweep and what a
recording of it says about the room, the average of the positions, the
target, and the cuts worked out from them.

Pure numpy, no device: `room_run.py` plays and records, this works on the
samples. Everything is in dB on one grid, 1/24 octave from 15 to 500 Hz
(item 10), smoothed to 1/6 octave (item 5).

**The cuts are Peaking filters** (item 1), the RBJ cookbook's, as
CamillaDSP computes them (`equaliser.band_db` for one); a cut's response here
is the one the stage plays.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

#: The microphone's own rate (Finding 124): the sweeps are played and
#: recorded at it.
FS = 48000
#: The band looked at, and the grid on it (item 10: 1/24 octave).
F_LO, F_HI = 15.0, 500.0
STEPS_PER_OCTAVE = 24
GRID = F_LO * 2 ** (np.arange(int(STEPS_PER_OCTAVE * math.log2(F_HI / F_LO)) + 1) / STEPS_PER_OCTAVE)
#: The bass limit (decision 3) and the lowest a cut is fitted from: below
#: 20 Hz the speakers roll off, which is no room's doing.
LIMIT = 250.0
FIT_LO = 20.0
#: What the chart shows (the design: 15-300 Hz).
CHART_HI = 300.0

#: The sweep (item 4): logarithmic, 10 Hz to 1 kHz, about 5 s.
SWEEP_LO, SWEEP_HI, SWEEP_S = 10.0, 1000.0, 5.0
#: How much of the room's answer is kept: a second holds the bass's decay
#: and resolves 1 Hz; the harmonics' copies land before the arrival and are
#: left out with what comes before it.
WINDOW_S = 1.0
PRE_S = 0.005

#: The design's limits (item 6, decision 2): cuts only, up to eight per
#: channel, at most 12 dB, Q from 1 to 15; a peak under 1 dB is left.
MAX_CUTS = 8
MAX_CUT_DB = 12.0
Q_MIN, Q_MAX = 1.0, 15.0
PEAK_MIN_DB = 1.0
#: A cut smaller than this is dropped rather than kept as nothing.
CUT_MIN_DB = 0.5
#: Item 6, criterion 2: a position made worse by more than this at a cut
#: counts against it; most positions against it hold it back (George,
#: 2026-11-05: on sofapi one position of five held every cut at the room's
#: main peak to 1-2 dB).
WORSE_DB = 1.0
#: Item 4: two sweeps of a position that differ by more than this somewhere
#: below the limit were disturbed (a door, a voice), and are repeated. To be
#: checked against the microphone's own repeats in a quiet room.
AGREE_DB = 1.5


def target_db(f) -> np.ndarray:
    """**The target** (decision 1): a gentle rise below about 80 Hz, +3 dB
    at the bottom, on a level the room sets (`Design.offset`)."""
    f = np.asarray(f, dtype=float)
    return 3.0 / (1.0 + (f / 70.0) ** 4)


# ---- the sweep -------------------------------------------------------------------


def log_sweep(fs: int = FS, f1: float = SWEEP_LO, f2: float = SWEEP_HI, seconds: float = SWEEP_S) -> np.ndarray:
    """An exponential sine sweep at full scale, faded in and out so it
    starts and ends without a click."""
    n = int(round(seconds * fs))
    t = np.arange(n) / fs
    k = math.log(f2 / f1)
    x = np.sin(2 * math.pi * f1 * seconds / k * (np.exp(t * k / seconds) - 1))
    fade_in, fade_out = int(0.1 * fs), int(0.02 * fs)
    x[:fade_in] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(fade_in) / fade_in)
    x[-fade_out:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(fade_out) / fade_out)
    return x


def transfer(recording, played, fs: int = FS, band=(SWEEP_LO, SWEEP_HI)) -> np.ndarray:
    """**The room's impulse response** from a recording of `played`: the
    recording's spectrum over the sweep's, regularised outside the sweep's
    band, so its level is the room's own whatever the sweep's was. Starts
    at the arrival, `WINDOW_S` long, its end faded."""
    recording = np.asarray(recording, dtype=float)
    played = np.asarray(played, dtype=float)
    n = 1 << int(math.ceil(math.log2(len(recording) + len(played))))
    R = np.fft.rfft(recording, n)
    X = np.fft.rfft(played, n)
    f = np.fft.rfftfreq(n, 1 / fs)
    power = np.abs(X) ** 2
    inside = (f >= band[0]) & (f <= band[1])
    eps = 1e-3 * (np.mean(power[inside]) if inside.any() else 1.0)
    H = R * np.conj(X) / (power + eps)
    H[~inside] *= 0.0
    ir = np.fft.irfft(H, n)
    # The direct sound arrives in the first half (the recording started
    # before the sweep); later than that is the circular wrap.
    peak = int(np.argmax(np.abs(ir[: n // 2])))
    start = max(0, peak - int(PRE_S * fs))
    length = int(WINDOW_S * fs)
    out = ir[start:start + length].copy()
    tail = len(out) // 5
    if tail:
        out[-tail:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(tail) / tail)
    return out


def response_db(ir, fs: int = FS, grid=GRID, fraction: int = 6) -> np.ndarray:
    """**The level at each grid point**, smoothed to 1/`fraction` octave: the
    power within ±1/(2·fraction) octave around it, averaged (item 5)."""
    ir = np.asarray(ir, dtype=float)
    n = max(1 << 18, 1 << int(math.ceil(math.log2(len(ir)))))
    spectrum = np.abs(np.fft.rfft(ir, n)) ** 2
    f = np.fft.rfftfreq(n, 1 / fs)
    half = 2 ** (1 / (2 * fraction))
    # Cumulative power, so each band is a difference of two lookups.
    cum = np.concatenate(([0.0], np.cumsum(spectrum)))
    lo = np.searchsorted(f, np.asarray(grid) / half)
    hi = np.searchsorted(f, np.asarray(grid) * half, side="right")
    hi = np.maximum(hi, lo + 1)
    mean = (cum[hi] - cum[lo]) / (hi - lo)
    return 10 * np.log10(np.maximum(mean, 1e-30))


def power_average(curves) -> np.ndarray:
    """The positions together (item 5): their power averaged, in dB."""
    curves = np.asarray(curves, dtype=float)
    return 10 * np.log10(np.mean(10 ** (curves / 10), axis=0))


def agree_db(a, b, grid=GRID, lo: float = FIT_LO, hi: float = LIMIT) -> float:
    """How far two sweeps of one position differ where it matters: the
    largest gap between their curves from 20 Hz to the limit."""
    grid = np.asarray(grid)
    inside = (grid >= lo) & (grid <= hi)
    return float(np.max(np.abs(np.asarray(a)[inside] - np.asarray(b)[inside])))


# ---- the level -----------------------------------------------------------------------


def pink_noise(seconds: float, fs: int = FS, lo: float = 20.0, hi: float = F_HI, seed: int = 0) -> np.ndarray:
    """Pink noise in the band measured, at an RMS of 1 (the level is set by
    the caller), faded in and out."""
    n = int(round(seconds * fs))
    rng = np.random.default_rng(seed)
    spectrum = rng.standard_normal(n // 2 + 1) + 1j * rng.standard_normal(n // 2 + 1)
    f = np.fft.rfftfreq(n, 1 / fs)
    shape = np.zeros_like(f)
    inside = (f >= lo) & (f <= hi)
    shape[inside] = 1 / np.sqrt(f[inside])
    x = np.fft.irfft(spectrum * shape, n)
    x /= np.sqrt(np.mean(x ** 2))
    fade = int(0.05 * fs)
    ramp = 0.5 - 0.5 * np.cos(np.pi * np.arange(fade) / fade)
    x[:fade] *= ramp
    x[-fade:] *= ramp[::-1]
    return x


def band_level_db(x, fs: int = FS, lo: float = 20.0, hi: float = F_HI) -> float:
    """The RMS of `x` within the band, in dB of full scale (a full-scale
    sine reads -3)."""
    x = np.asarray(x, dtype=float)
    if not len(x):
        return -200.0
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    inside = (f >= lo) & (f <= hi)
    # Parseval: the band's share of the mean square.
    power = 2 * np.sum(np.abs(X[inside]) ** 2) / len(x) ** 2
    return 10 * math.log10(max(power, 1e-30))


# ---- the cuts --------------------------------------------------------------------


@dataclass(frozen=True)
class Cut:
    freq: float
    gain: float     # dB, below zero
    q: float

    def as_dict(self) -> dict:
        return {"freq": round(self.freq, 1), "gain": round(self.gain, 1), "q": round(self.q, 2)}


def peaking_db(freq: float, gain: float, q: float, f, fs: int = FS) -> np.ndarray:
    """One Peaking filter's response in dB at `f` (RBJ cookbook)."""
    f = np.asarray(f, dtype=float)
    if not gain:
        return np.zeros_like(f)
    a = 10 ** (gain / 40)
    w0 = 2 * math.pi * freq / fs
    alpha = math.sin(w0) / (2 * q)
    c = math.cos(w0)
    b0, b1, b2 = 1 + alpha * a, -2 * c, 1 - alpha * a
    a0, a1, a2 = 1 + alpha / a, -2 * c, 1 - alpha / a
    z = np.exp(-1j * 2 * np.pi * f / fs)
    h = (b0 + b1 * z + b2 * z * z) / (a0 + a1 * z + a2 * z * z)
    return 20 * np.log10(np.abs(h))


def cuts_db(cuts, f, fs: int = FS) -> np.ndarray:
    total = np.zeros(np.shape(f), dtype=float)
    for c in cuts:
        total += peaking_db(c.freq, c.gain, c.q, f, fs)
    return total


@dataclass(frozen=True)
class Design:
    """What one channel's measurement gives: the cuts, and the curves the
    screens draw - all on `GRID`, relative to `offset` (the target's 0)."""
    cuts: tuple[Cut, ...]
    offset: float
    before: np.ndarray          # the positions' average
    target: np.ndarray
    after: np.ndarray           # expected: the positions with the cuts, averaged
    positions: np.ndarray       # (5, len(GRID))

    @property
    def nothing_to_cut(self) -> bool:
        return not self.cuts


def _fit_range(grid) -> np.ndarray:
    grid = np.asarray(grid)
    return (grid >= FIT_LO) & (grid <= LIMIT)


def _peak(residual, grid, inside) -> tuple[float, float, float] | None:
    """The highest point of `residual` inside the fit range above
    `PEAK_MIN_DB`: (frequency, height, Q from where it falls to half)."""
    masked = np.where(inside, residual, -np.inf)
    i = int(np.argmax(masked))
    height = float(masked[i])
    if height <= PEAK_MIN_DB:
        return None
    half = height / 2
    lo = i
    while lo > 0 and inside[lo - 1] and residual[lo - 1] > half:
        lo -= 1
    hi = i
    while hi < len(grid) - 1 and inside[hi + 1] and residual[hi + 1] > half:
        hi += 1
    # Between grid points where it crosses half, on a log axis.
    def cross(j, k):
        a, b = residual[j], residual[k]
        t = 0.5 if a == b else (half - a) / (b - a)
        t = min(max(t, 0.0), 1.0)
        return math.exp(math.log(grid[j]) + t * (math.log(grid[k]) - math.log(grid[j])))
    f_lo = cross(lo - 1, lo) if lo > 0 else grid[lo] / 2 ** (1 / 48)
    f_hi = cross(hi, hi + 1) if hi < len(grid) - 1 else grid[hi] * 2 ** (1 / 48)
    # The top between its neighbours, on a log axis.
    f0 = float(grid[i])
    if 0 < i < len(grid) - 1:
        y0, y1, y2 = residual[i - 1], residual[i], residual[i + 1]
        den = y0 - 2 * y1 + y2
        if den < 0:
            shift = 0.5 * (y0 - y2) / den
            f0 = float(math.exp(math.log(grid[i]) + shift * math.log(2) / STEPS_PER_OCTAVE))
    q = f0 / max(f_hi - f_lo, 1e-6)
    return f0, min(height, MAX_CUT_DB), min(max(q, Q_MIN), Q_MAX)


def _refine(cuts: list[Cut], before, desired, grid, weight) -> list[Cut]:
    """**The cuts fitted together** (item 6): their gains and widths by
    damped least squares on the gap to `desired`, held inside the limits."""
    if not cuts:
        return cuts
    freqs = np.array([c.freq for c in cuts])
    params = np.concatenate([[c.gain for c in cuts], [math.log(c.q) for c in cuts]])
    k = len(cuts)
    lo = np.concatenate([np.full(k, -MAX_CUT_DB), np.full(k, math.log(Q_MIN))])
    hi = np.concatenate([np.zeros(k), np.full(k, math.log(Q_MAX))])

    def residual(p):
        total = np.zeros(len(grid))
        for j in range(k):
            total += peaking_db(freqs[j], p[j], math.exp(p[k + j]), grid)
        return (before + total - desired) * weight

    lam = 1e-2
    r = residual(params)
    cost = float(r @ r)
    for _ in range(40):
        jac = np.empty((len(grid), 2 * k))
        for j in range(2 * k):
            step = 1e-4 if j < k else 1e-4
            p = params.copy()
            p[j] += step
            jac[:, j] = (residual(p) - r) / step
        a = jac.T @ jac
        g = jac.T @ r
        improved = False
        for _ in range(8):
            delta = np.linalg.solve(a + lam * np.diag(np.diag(a) + 1e-9), -g)
            trial = np.clip(params + delta, lo, hi)
            rt = residual(trial)
            ct = float(rt @ rt)
            if ct < cost:
                params, r, cost = trial, rt, ct
                lam = max(lam / 3, 1e-6)
                improved = True
                break
            lam *= 4
        if not improved or float(np.max(np.abs(delta))) < 1e-4:
            break
    return [Cut(float(freqs[j]), float(params[j]), float(math.exp(params[k + j]))) for j in range(k)]


def _no_position_worse(cuts: list[Cut], positions, target, grid) -> list[Cut]:
    """**Most positions not made worse** (item 6, criterion 2): a cut that
    leaves more than half the positions more than `WORSE_DB` further from
    the target at its frequency is made smaller until it does not; one that
    comes to nothing is dropped. A single position in a dip the others do
    not share is outvoted."""
    cuts = list(cuts)
    for _ in range(60):
        changed = False
        for idx, cut in enumerate(cuts):
            at = np.array([cut.freq])
            t = float(np.interp(math.log(cut.freq), np.log(grid), target))
            total = float(cuts_db(cuts, at)[0])
            worse = 0
            for pos in positions:
                p = float(np.interp(math.log(cut.freq), np.log(grid), pos))
                if abs(p + total - t) - abs(p - t) > WORSE_DB:
                    worse += 1
            if worse * 2 > len(positions):
                cuts[idx] = Cut(cut.freq, cut.gain * 0.8, cut.q)
                changed = True
        cuts = [c for c in cuts if c.gain <= -CUT_MIN_DB]
        if not changed:
            break
    return cuts


def design(positions, grid=GRID) -> Design:
    """**The cuts for one channel** from its positions' curves (item 6):

    - the average's level an octave above the limit sets the target's, so
      the correction blends into what is left as it is;
    - the highest peak above the target gets a Peaking cut fitted to its
      height and width, again while one stands more than 1 dB above, up to
      eight;
    - then the cuts are fitted together, aiming the peaks at the target and
      leaving the dips and everything above the limit as they are;
    - and a cut that would make most positions worse is made smaller."""
    grid = np.asarray(grid, dtype=float)
    positions = np.asarray(positions, dtype=float)
    before = power_average(positions)
    above = (grid > LIMIT) & (grid <= 2 * LIMIT)
    offset = float(np.mean(before[above])) if above.any() else float(np.mean(before))
    target = target_db(grid) + offset
    inside = _fit_range(grid)
    # Peaks are brought to the target; dips and everything outside are
    # what they were, so a cut that digs into either costs.
    desired = np.where(inside, np.minimum(before, target), before)
    weight = np.where(grid <= 2 * LIMIT, 1.0, 0.0)

    cuts: list[Cut] = []
    for _ in range(MAX_CUTS):
        residual = before + cuts_db(cuts, grid) - target
        found = _peak(residual, grid, inside)
        if found is None:
            break
        f0, height, q = found
        cuts.append(Cut(f0, -height, q))
    cuts = _refine(cuts, before, desired, grid, weight)
    cuts = [c for c in cuts if c.gain <= -CUT_MIN_DB]
    cuts = _no_position_worse(cuts, positions, target, grid)
    cuts.sort(key=lambda c: c.freq)
    total = cuts_db(cuts, grid)
    after = power_average(positions + total)
    return Design(tuple(cuts), offset, before - offset, target - offset, after - offset, positions - offset)


def as_heard(positions, grid=GRID) -> Design:
    """**Both speakers together**, as the positions heard them: their
    average and the target on its level, as `design` gives them, with no
    cuts of their own - the after is measured in the check, or none."""
    grid = np.asarray(grid, dtype=float)
    positions = np.asarray(positions, dtype=float)
    before = power_average(positions)
    above = (grid > LIMIT) & (grid <= 2 * LIMIT)
    offset = float(np.mean(before[above])) if above.any() else float(np.mean(before))
    target = target_db(grid)
    return Design((), offset, before - offset, target, np.array([]), positions - offset)


def peaks_down_db(before, after, grid=GRID) -> float:
    """*Peaks down by up to N dB*: the most the correction takes off, below
    the limit."""
    inside = np.asarray(grid) <= LIMIT
    return float(max(0.0, np.max((np.asarray(before) - np.asarray(after))[inside])))


def worse_positions(before_positions, after_positions, target, cuts, grid=GRID) -> list[tuple[int, float]]:
    """Positions the measured check finds further from the target at a cut's
    frequency than they were, by more than `WORSE_DB`: (position, by how
    much), position 1 first. Empty is *No position is worse than before*."""
    grid = np.asarray(grid)
    found = []
    for n, (b, a) in enumerate(zip(before_positions, after_positions), start=1):
        worst = 0.0
        for cut in cuts:
            x = math.log(cut.freq)
            t = float(np.interp(x, np.log(grid), target))
            worst = max(worst, abs(float(np.interp(x, np.log(grid), a)) - t)
                        - abs(float(np.interp(x, np.log(grid), b)) - t))
        if worst > WORSE_DB:
            found.append((n, round(worst, 1)))
    return found
