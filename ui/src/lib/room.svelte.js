// SPDX-License-Identifier: GPL-3.0-or-later
//
// Room correction (ADR-0175; design/source/29): what every surface draws
// from, the requests that change it, and the chart's drawing.
//
// The summary is the core's (`/state`'s `room`): the switches, the last
// measurement's day, a run's step. The page's full picture - the microphone,
// the chart, a run's pending correction - is `GET /room-correction`, read
// when a page opens and again whenever the summary moves.
import { derived } from 'svelte/store';
import { playback } from './state.js';

/** Room correction for the output in use, or null (no output, an older core). */
export const room = derived(playback, ($s) => $s?.room ?? null);

async function call(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const parsed = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(parsed.error ?? `HTTP ${response.status}`);
  return parsed;
}

export const readRoom = () => call('GET', '/room-correction');
/** `on` and `without`, for the output in use. */
export const setRoom = (changes) => call('PUT', '/room-correction', changes);
/** The 90° calibration file, read on the phone. */
export const giveCalibration = (text, name) => call('POST', '/room-correction/calibration', { text, name });
/** `measure` begins a run; then the phone's buttons. */
export const runRoom = (action) => call('POST', '/room-correction/run', { action });

/** **The full picture, kept fresh**: read now, and again whenever the
 *  summary changes (a step, a switch) - and, while `poll` says so, every
 *  two seconds (the microphone is plugged in without anything else moving). */
export class RoomReader {
  full = $state(null);
  error = $state(null);
  #seen = undefined;
  #timer = null;

  follow(summary, poll) {
    const key = JSON.stringify(summary ?? null);
    if (key !== this.#seen) {
      this.#seen = key;
      this.read();
    }
    clearInterval(this.#timer);
    this.#timer = poll ? setInterval(() => this.read(), 2000) : null;
  }

  #reading = false;
  #again = false;

  //: One read at a time: asked again while one is out, the next follows it
  //: (sofapi, 2026-11-05: a dozen reads within a third of a second).
  async read() {
    if (this.#reading) {
      this.#again = true;
      return;
    }
    this.#reading = true;
    try {
      this.full = await readRoom();
      this.error = null;
    } catch (e) {
      this.error = e.message;
    } finally {
      this.#reading = false;
    }
    if (this.#again) {
      this.#again = false;
      this.read();
    }
  }

  stop() {
    clearInterval(this.#timer);
  }
}

// ---- words ---------------------------------------------------------------------

/** The output as the crumbs say it: *the DAC, HiFiBerry DAC2 HD*. */
export const outputPhrase = (o) => (o ? `the ${o.kind}, ${o.name}` : '');
export const outputShort = (o) => o?.kind ?? '';

/** A cut as the design writes it: *42 Hz*, *−6.5 dB*. */
export const cutFreq = (c) => `${Math.round(c.freq)} Hz`;
export const cutGain = (c) => `${c.gain < 0 ? '−' : '+'}${Math.abs(c.gain).toFixed(1)} dB`;

/** **The cuts as listed**: cuts at one frequency - a peak deeper than one
 *  cut takes, two stacked (George, 2026-11-05: as close to the target as
 *  it goes) - are one line, their gains added. */
export function cutRows(list) {
  const rows = [];
  for (const c of list ?? []) {
    const same = rows.find((r) => Math.round(r.freq) === Math.round(c.freq));
    if (same) same.gain = Math.round((same.gain + c.gain) * 10) / 10;
    else rows.push({ ...c });
  }
  return rows;
}

/** *Four cuts for each speaker*, or *Three cuts on the left, four on the right*. */
const NUMBERS = ['No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight'];
export function cutsHeading(cuts) {
  const l = cutRows(cuts?.L).length;
  const r = cutRows(cuts?.R).length;
  const word = (n) => NUMBERS[n] ?? String(n);
  if (l === r) return `${word(l)} ${l === 1 ? 'cut' : 'cuts'} for each speaker`;
  return `${word(l)} ${l === 1 ? 'cut' : 'cuts'} on the left, ${word(r).toLowerCase()} on the right`;
}

/** *Peaks down by up to 8 dB*. */
export const peaksDown = (db) => `Peaks down by up to ${Math.max(0, Math.round(db ?? 0))} dB`;

/** The result's line: no position worse, or which was and by how much. */
export function worseLine(worse) {
  if (!worse?.length) return 'No position is worse than before.';
  const [n, db] = worse[0];
  return worse.length === 1
    ? `Position ${n} is ${db.toFixed(1)} dB further from the target than before.`
    : `Positions ${worse.map((w) => w[0]).join(', ')} are further from the target than before.`;
}

/** **Where a run measures**: three positions (George, 2026-11-05, over the
 *  design's five). A measurement keeps its own number. */
export const POSITIONS = 3;
const COUNTS = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight'];
/** *three*, *five*: a number of positions in words. */
export const countWord = (n) => COUNTS[n] ?? String(n);
export const capitalised = (w) => w.charAt(0).toUpperCase() + w.slice(1);

/** **Where to move the microphone** (the design's R19-R20). */
export const MOVES = {
  2: 'About 40 cm to the left of where your head was',
  3: 'About 40 cm to the right of where your head was',
};
//: The seat drawing's places in its 340 x 196 box (1 is the head).
export const PLACES = [[170, 98], [122, 98], [218, 98]];

/** The dips the correction leaves, for the correction's tail: the lowest
 *  points below the target under the limit, two at most, low to high. */
export function dips(speaker, freqs) {
  if (!speaker) return [];
  const gap = speaker.before.map((b, i) => b - speaker.target[i]);
  const found = [];
  for (let i = 1; i < gap.length - 1; i++) {
    if (freqs[i] < 20 || freqs[i] > 250) continue;
    if (gap[i] < -3 && gap[i] <= gap[i - 1] && gap[i] <= gap[i + 1]) found.push([gap[i], Math.round(freqs[i])]);
  }
  return found.sort((a, b) => a[0] - b[0]).slice(0, 2).map((d) => d[1]).sort((a, b) => a - b);
}

/** The correction's tail, with the dips this room has. */
export function dipsLine(list) {
  const lead = 'Only cuts: ';
  const rest = 'The bass rise below 80 Hz is the target.';
  if (!list.length) return `${lead}nothing is raised, as more power does not fill a dip. ${rest}`;
  const at = list.length === 1 ? `the dip at ${list[0]} Hz stays` : `the dips at ${list[0]} and ${list[1]} Hz stay`;
  return `${lead}${at}, as more power does not fill them. ${rest}`;
}

// ---- the chart (the design's §5) ---------------------------------------------------

export const FMIN = 15;
export const FMAX = 300;
//: x as a share of the width for a frequency; y as a share of the height for
//: a level, ±`span` dB.
export const fx = (f) => Math.log(f / FMIN) / Math.log(FMAX / FMIN);
export const vy = (v, span = 15) => (span - Math.max(-span, Math.min(span, v))) / (2 * span);

/** **The chart's reach**: ±15 dB as the design draws it, wider in 5 dB
 *  steps when a curve of either speaker goes past it, so a peak is never
 *  cut flat by the chart's edge (sofapi, 2026-11-05: +18 dB at 45 Hz). */
export function chartSpan(chart) {
  let top = 0;
  for (const s of Object.values(chart?.speakers ?? {})) {
    for (const curve of [s.before, s.after, ...(s.positions ?? [])]) {
      for (const v of curve ?? []) top = Math.max(top, Math.abs(v));
    }
  }
  return Math.min(30, Math.max(15, Math.ceil(top / 5) * 5));
}

export function path(freqs, curve, w, h, span = 15) {
  let d = '';
  for (let i = 0; i < freqs.length; i++) d += `${i ? 'L' : 'M'}${(fx(freqs[i]) * w).toFixed(1)},${(vy(curve[i], span) * h).toFixed(1)}`;
  return d;
}

/** The area between `a` and `b` where `a` is above: what the cuts take away. */
export function between(freqs, a, b, w, h, span = 15) {
  let d = '';
  for (let i = 0; i < freqs.length; i++) d += `${i ? 'L' : 'M'}${(fx(freqs[i]) * w).toFixed(1)},${(vy(a[i], span) * h).toFixed(1)}`;
  for (let i = freqs.length - 1; i >= 0; i--) d += `L${(fx(freqs[i]) * w).toFixed(1)},${(vy(Math.min(a[i], b[i]), span) * h).toFixed(1)}`;
  return `${d}Z`;
}

/** The gridlines' places: 20, 30, 50, 100, 200 Hz and the 250 Hz limit. */
export const xAt = (f) => `${(fx(f) * 100).toFixed(1)}%`;
