# SPDX-License-Identifier: GPL-3.0-or-later
"""**Room correction's numbers** (ADR-0175, Phase 29; ADR-0177, Phase 30):
the sweep and what a recording of it says about the room, the average of the
positions, the target, the cuts in the bass and the broad corrections above
it worked out from them.

Pure numpy, no device: `room_run.py` plays and records, this works on the
samples. Everything is in dB on one grid, 1/24 octave from 15 Hz (item 10)
to 20 kHz (Phase 30: the sweeps to 20 kHz, George 2026-11-07), smoothed to
1/6 octave (item 5).

**The cuts are Peaking filters** (item 1), the RBJ cookbook's, as
CamillaDSP computes them (`equaliser.band_db` for one); a cut's response here
is the one the stage plays. So are the broad corrections above the bass
(ADR-0177 item 4), up or down.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

#: The microphone's own rate (Finding 124): the sweeps are played and
#: recorded at it.
FS = 48000
#: The band looked at, and the grid on it (item 10: 1/24 octave).
F_LO, F_HI = 15.0, 20000.0
STEPS_PER_OCTAVE = 24
GRID = F_LO * 2 ** (np.arange(int(STEPS_PER_OCTAVE * math.log2(F_HI / F_LO)) + 1) / STEPS_PER_OCTAVE)
#: The bass limit (decision 3) and the lowest a cut is fitted from: below
#: 20 Hz the speakers roll off, which is no room's doing.
LIMIT = 250.0
FIT_LO = 20.0
#: What the chart shows (the design: 15-300 Hz).
CHART_HI = 300.0

#: The sweep (item 4): logarithmic, 10 Hz to 20 kHz (Phase 30). 8 s keeps
#: the bass's time in each octave, so its signal over the room's noise, as
#: Phase 29's 5 s to 1 kHz had it (0.73 s an octave against 0.75); the time
#: is settled after the measurement of George's room.
SWEEP_LO, SWEEP_HI, SWEEP_S = 10.0, 20000.0, 8.0
#: Where the level is read - the noise's and a sweep's alike: the bass, so
#: about 60 dB at the seat means what it did in Phase 29.
LEVEL_BAND = (20.0, 500.0)
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

#: **Above the bass** (ADR-0177). The speaker's own slope (item 2): a straight
#: line on a log axis, fitted to the positions' average at 1/3 octave from
#: 300 Hz to 10 kHz.
SLOPE_FIT = (300.0, 10000.0)
SMOOTH_ABOVE = 1 / 3
#: The broad corrections (item 4): up to six, from the limit to 14 kHz
#: (decision 2), each and all together within 3 dB up or down (George,
#: 2026-11-07), Q 0.5 to 2, a third of an octave apart; a gap under 1.5 dB
#: is left.
ABOVE_HI = 14000.0
MAX_ABOVE = 6
ABOVE_DB = 3.0
ABOVE_Q_MIN, ABOVE_Q_MAX = 0.5, 2.0
ABOVE_APART = 1 / 3
ABOVE_LEAVE_DB = 1.5
#: Less where the positions disagree (item 4): from this standard deviation
#: of theirs at 1/3 octave a gap counts for less, and from this not at all.
SPREAD_DB = (1.5, 3.0)
#: Where *within N dB of the speaker's own balance* is read (the design).
WITHIN = (300.0, 14000.0)


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


def pink_noise(seconds: float, fs: int = FS, lo: float = LEVEL_BAND[0], hi: float = LEVEL_BAND[1],
               seed: int = 0) -> np.ndarray:
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


def band_level_db(x, fs: int = FS, lo: float = LEVEL_BAND[0], hi: float = LEVEL_BAND[1]) -> float:
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
class Broad:
    """A broad correction above the bass (ADR-0177 item 4): up or down."""
    freq: float
    gain: float     # dB, within ±ABOVE_DB
    q: float

    def as_dict(self) -> dict:
        return {"freq": round(self.freq, 1), "gain": round(self.gain, 1), "q": round(self.q, 2)}


@dataclass(frozen=True)
class Design:
    """What one channel's measurement gives: the cuts in the bass, the broad
    corrections above it, and the curves the screens draw - all on `GRID`,
    relative to `offset` (the target's level at the limit)."""
    cuts: tuple[Cut, ...]
    offset: float
    before: np.ndarray          # the positions' average
    target: np.ndarray
    after: np.ndarray           # expected: the positions corrected, averaged
    positions: np.ndarray       # (3, len(GRID))
    broad: tuple[Broad, ...] = ()
    #: Expected with the bass's cuts alone (*Bass*).
    after_bass: np.ndarray | None = None
    #: *Within N dB of the speaker's own balance* (`within_db`): the room's
    #: own, and the after; None for *Both*.
    room_within: float | None = None
    within: float | None = None

    @property
    def nothing_to_cut(self) -> bool:
        return not self.cuts

    @property
    def nothing_to_correct(self) -> bool:
        return not self.cuts and not self.broad


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


# ---- above the bass (ADR-0177) -----------------------------------------------------


def smooth(curve, octave: float = SMOOTH_ABOVE) -> np.ndarray:
    """A grid curve's power averaged over ±`octave`/2 around each point."""
    p = 10 ** (np.asarray(curve, dtype=float) / 10)
    k = max(1, int(round(STEPS_PER_OCTAVE * octave / 2)))
    cum = np.concatenate(([0.0], np.cumsum(p)))
    i = np.arange(len(p))
    lo, hi = np.maximum(i - k, 0), np.minimum(i + k + 1, len(p))
    return 10 * np.log10((cum[hi] - cum[lo]) / (hi - lo))


def slope(before, grid=GRID) -> np.ndarray:
    """**The speaker's own slope** (item 2): the straight line, on a log
    axis, through the average at 1/3 octave from 300 Hz to 10 kHz."""
    grid = np.asarray(grid, dtype=float)
    fit = (grid >= SLOPE_FIT[0]) & (grid <= SLOPE_FIT[1])
    a, b = np.polyfit(np.log2(grid[fit]), smooth(before)[fit], 1)
    return a * np.log2(grid) + b


def full_target(line, grid=GRID) -> tuple[np.ndarray, float]:
    """**One target throughout** (item 3): the bass's rise on the line's
    level where they meet, at the limit, and the line above it. The level,
    with it."""
    grid = np.asarray(grid, dtype=float)
    level = float(np.interp(math.log(LIMIT), np.log(grid), line))
    return target_db(grid) + np.where(grid <= LIMIT, level, line), level


def within_db(curve, target, grid=GRID) -> float:
    """*Within N dB of the speaker's own balance* (the design): the largest
    gap from the target from 300 Hz to 14 kHz at 1/3 octave, rounded up to
    0.5 dB."""
    grid = np.asarray(grid)
    inside = (grid >= WITHIN[0]) & (grid <= WITHIN[1])
    gap = float(np.max(np.abs(smooth(curve) - np.asarray(target))[inside]))
    return math.ceil(gap * 2 - 1e-9) / 2


def spread_weight(positions) -> np.ndarray:
    """**Less where the positions disagree** (item 4): 1 up to a standard
    deviation of `SPREAD_DB[0]` among them at 1/3 octave, 0 from
    `SPREAD_DB[1]`."""
    std = np.std(np.array([smooth(p) for p in positions]), axis=0)
    lo, hi = SPREAD_DB
    return np.clip((hi - std) / (hi - lo), 0.0, 1.0)


def _apart(freq: float, others) -> bool:
    return all(abs(math.log2(freq / f)) >= ABOVE_APART for f in others)


def _broad_fit(gap, inside, grid) -> list[Broad]:
    """One at a time at the largest gap left, as wide as the gap is at half
    its height; then all together by damped least squares, the total held
    within ±3 dB. `gap` is already less where the positions disagree, so
    there the correction is held near none."""
    x = np.log2(grid)
    filters: list[Broad] = []
    passed: list[float] = []
    while len(filters) < MAX_ABOVE:
        residual = gap + cuts_db(filters, grid)
        masked = np.where(inside, residual, 0.0)
        for f in [b.freq for b in filters] + passed:
            masked[np.abs(x - math.log2(f)) < ABOVE_APART] = 0.0
        i = int(np.argmax(np.abs(masked)))
        height = float(masked[i])
        if abs(height) <= ABOVE_LEAVE_DB:
            break
        lo = hi = i
        while lo > 0 and inside[lo - 1] and abs(residual[lo - 1]) > abs(height) / 2 \
                and np.sign(residual[lo - 1]) == np.sign(height):
            lo -= 1
        while hi < len(grid) - 1 and inside[hi + 1] and abs(residual[hi + 1]) > abs(height) / 2 \
                and np.sign(residual[hi + 1]) == np.sign(height):
            hi += 1
        width = max(math.log2(grid[hi] / grid[lo]), 1 / 6)
        q = min(max(1 / (2 * math.sinh(math.log(2) / 2 * width)), ABOVE_Q_MIN), ABOVE_Q_MAX)
        gain = float(np.clip(-height, -ABOVE_DB, ABOVE_DB))
        if abs(gain) < CUT_MIN_DB:
            passed.append(float(grid[i]))
            continue
        filters.append(Broad(float(grid[i]), gain, q))
    if not filters:
        return filters
    k = len(filters)
    f0 = np.array([math.log2(b.freq) for b in filters])
    params = np.concatenate([[b.gain for b in filters], [math.log(b.q) for b in filters], f0])
    lo_b = np.concatenate([np.full(k, -ABOVE_DB), np.full(k, math.log(ABOVE_Q_MIN)),
                           np.maximum(f0 - ABOVE_APART / 2, math.log2(LIMIT))])
    hi_b = np.concatenate([np.full(k, ABOVE_DB), np.full(k, math.log(ABOVE_Q_MAX)),
                           np.minimum(f0 + ABOVE_APART / 2, math.log2(ABOVE_HI))])
    w = inside.astype(float)

    def residual(p):
        total = np.zeros(len(grid))
        for j in range(k):
            total += peaking_db(2 ** p[2 * k + j], p[j], math.exp(p[k + j]), grid)
        over = np.maximum(total - ABOVE_DB, 0) + np.maximum(-ABOVE_DB - total, 0)
        return np.concatenate([(gap + total) * w, 30 * over])

    lam = 1e-2
    r = residual(params)
    cost = float(r @ r)
    for _ in range(80):
        jac = np.empty((len(r), 3 * k))
        for j in range(3 * k):
            p = params.copy()
            p[j] += 1e-4
            jac[:, j] = (residual(p) - r) / 1e-4
        a = jac.T @ jac
        g = jac.T @ r
        improved = False
        for _ in range(8):
            delta = np.linalg.solve(a + lam * np.diag(np.diag(a) + 1e-9), -g)
            trial = np.clip(params + delta, lo_b, hi_b)
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
    return [Broad(float(2 ** params[2 * k + j]), float(params[j]), float(math.exp(params[k + j])))
            for j in range(k)]


def _broad_majority(filters: list[Broad], positions, target, grid) -> list[Broad]:
    """**Most positions decide** (item 4), as for the bass's cuts: a filter
    that would leave more than half the positions more than `WORSE_DB`
    further from the target at its frequency is made smaller."""
    curves = [smooth(p) for p in positions]
    filters = list(filters)
    for _ in range(60):
        changed = False
        for idx, b in enumerate(filters):
            j = int(np.argmin(np.abs(np.log(grid) - math.log(b.freq))))
            total = float(cuts_db(filters, grid[j:j + 1])[0])
            worse = sum(1 for c in curves if abs(c[j] + total - target[j]) - abs(c[j] - target[j]) > WORSE_DB)
            if worse * 2 > len(curves):
                filters[idx] = Broad(b.freq, b.gain * 0.8, b.q)
                changed = True
        filters = [b for b in filters if abs(b.gain) >= CUT_MIN_DB]
        if not changed:
            break
    return filters


def _broad(positions, bass, target, grid) -> tuple[list[Broad], float]:
    """**The broad corrections above the bass** for one channel (item 4),
    with the bass's cuts in place, and the room's own figure: none when the
    room is within 1.5 dB of the target already."""
    room_within = within_db(power_average(positions), target, grid)
    if room_within <= ABOVE_LEAVE_DB:
        return [], room_within
    inside = (grid >= LIMIT) & (grid <= ABOVE_HI)
    gap = (smooth(power_average(positions + bass)) - target) * spread_weight(positions)
    filters = _broad_fit(gap, inside, grid)
    filters = [b for b in filters if abs(b.gain) >= CUT_MIN_DB]
    filters = _broad_majority(filters, positions + bass, target, grid)
    return sorted(filters, key=lambda b: b.freq), room_within


# ---- one channel -----------------------------------------------------------------


def design(positions, grid=GRID) -> Design:
    """**The correction for one channel** from its positions' curves:

    - the target: the speaker's own slope above the limit, the bass's rise
      below it on the slope's level there (ADR-0177 items 2-3);
    - in the bass, cuts only (ADR-0175 item 6): the highest peak above the
      target gets a Peaking cut fitted to its height and width, again while
      one stands more than 1 dB above, up to eight; then the cuts are fitted
      together, aiming the peaks at the target and leaving the dips and
      everything above the limit as they are; and a cut that would make most
      positions worse is made smaller;
    - above it, broad corrections up or down (`_broad`)."""
    grid = np.asarray(grid, dtype=float)
    positions = np.asarray(positions, dtype=float)
    before = power_average(positions)
    target, offset = full_target(slope(before, grid), grid)
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
    bass = cuts_db(cuts, grid)
    broad, room_within = _broad(positions, bass, target, grid)
    after = power_average(positions + bass + cuts_db(broad, grid))
    after_bass = power_average(positions + bass)
    return Design(tuple(cuts), offset, before - offset, target - offset, after - offset, positions - offset,
                  tuple(broad), after_bass - offset, room_within, within_db(after, target, grid))


def as_heard(positions, grid=GRID) -> Design:
    """**Both speakers together**, as the positions heard them: their
    average and the target on its level, as `design` gives them, with no
    correction of their own - the after is measured in the check, or none."""
    grid = np.asarray(grid, dtype=float)
    positions = np.asarray(positions, dtype=float)
    before = power_average(positions)
    target, offset = full_target(slope(before, grid), grid)
    return Design((), offset, before - offset, target - offset, np.array([]), positions - offset)


def peaks_down_db(before, after, grid=GRID) -> float:
    """*Peaks down by up to N dB*: the most the correction takes off, below
    the limit."""
    inside = np.asarray(grid) <= LIMIT
    return float(max(0.0, np.max((np.asarray(before) - np.asarray(after))[inside])))


def worse_positions(before_positions, after_positions, target, filters, grid=GRID) -> list[tuple[int, float]]:
    """Positions the measured check finds further from the target at a cut's
    or a broad correction's frequency than they were, by more than
    `WORSE_DB`: (position, by how much), position 1 first. Empty is *No
    position is worse than before*. Above the bass the curves are read at
    1/3 octave, as the corrections were made."""
    grid = np.asarray(grid)
    found = []
    for n, (b, a) in enumerate(zip(before_positions, after_positions), start=1):
        worst = 0.0
        sb, sa = smooth(b), smooth(a)
        for f in filters:
            x = math.log(f.freq)
            t = float(np.interp(x, np.log(grid), target))
            bb, aa = (b, a) if f.freq <= LIMIT else (sb, sa)
            worst = max(worst, abs(float(np.interp(x, np.log(grid), aa)) - t)
                        - abs(float(np.interp(x, np.log(grid), bb)) - t))
        if worst > WORSE_DB:
            found.append((n, round(worst, 1)))
    return found
