// SPDX-License-Identifier: GPL-3.0-or-later
//
// Room correction (ADR-0175, ADR-0177; design/source/29 and 30): what every
// surface draws from, the requests that change it, and the chart's drawing.
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
/** `on`, `without` and `reach` (`bass` or `full`), for the output in use. */
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

/** **The chart's tabs**: each speaker, and both together where the
 *  measurement has them (George, 2026-11-05: as heard, never corrected). */
export const BOTH = 'both';
export const sides = (chart) => ['L', 'R', ...(chart?.speakers?.[BOTH] ? [BOTH] : [])];
export const sideName = (k) => ({ L: 'Left', R: 'Right', both: 'Both' })[k] ?? k;

/** A frequency as the design writes it: *46 Hz*, *2.4 kHz*, *11 kHz*. */
export const freqWord = (f) => (f < 1000 ? `${Math.round(f)} Hz`
  : `${(f / 1000).toFixed(f < 10000 ? 1 : 0).replace(/\.0$/, '')} kHz`);
/** A correction as the design writes it: *42 Hz*, *−6.5 dB*, *+2.5 dB*. */
export const cutFreq = (c) => freqWord(c.freq);
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

const NUMBERS = ['No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten',
  'Eleven', 'Twelve', 'Thirteen', 'Fourteen'];
const number = (n) => NUMBERS[n] ?? String(n);

/** **The correction's heading** counts both kinds (the design's 1g):
 *  *Four cuts in the bass, four broad corrections above*, *…, nothing to
 *  correct above*, *Nothing to cut in the bass, …*, *Nothing to correct*. */
export function correctionsHeading(bass, above) {
  if (!bass && !above) return 'Nothing to correct';
  const low = bass ? `${number(bass)} ${bass === 1 ? 'cut' : 'cuts'} in the bass` : 'Nothing to cut in the bass';
  const high = above ? `${number(above).toLowerCase()} broad ${above === 1 ? 'correction' : 'corrections'} above`
    : 'nothing to correct above';
  return `${low}, ${high}`;
}

/** *Left speaker · 8 corrections* (the design's 1g). */
export function correctionsWho(k, bass, above) {
  if (k === BOTH) return 'Both speakers';
  const n = bass + above;
  return `${k === 'L' ? 'Left' : 'Right'} speaker${n ? ` · ${n} ${n === 1 ? 'correction' : 'corrections'}` : ''}`;
}

/** *Peaks down by up to 8 dB*. */
export const peaksDown = (db) => `Peaks down by up to ${Math.max(0, Math.round(db ?? 0))} dB`;
/** *1.5*, *2*: a figure of half decibels. */
const halfDb = (db) => String(Math.round((db ?? 0) * 2) / 2);

/** **The result's heading and line** (the design's §2, *Result words*), for
 *  the speaker shown: `speaker` from the chart, `both` its tab, `range` how
 *  far the measurement was made, `reach` how far it plays, `expected` not
 *  checked (`expectedMark`: say so in the heading). */
export function resultWords({ speaker, both = false, range = 'full', reach = 'full', expectedMark = false }) {
  const bothAfter = both && !!speaker?.after?.length;
  if (both && !bothAfter) {
    return ['Both speakers, before', 'The two together, as you hear them. Measure again and check it to see them after.'];
  }
  const cuts = (speaker?.cuts ?? []).length;
  const above = (speaker?.above ?? []).length;
  if (both) return [peaksDown(speaker?.peaks_down) + (expectedMark ? ', expected' : ''), 'The two together, as you hear them.'];
  const bassOnly = range !== 'full';
  if (!cuts && !above && !bassOnly) return ['Nothing to correct', 'Already near the target, in the bass and above it.'];
  const head = !cuts ? 'Nothing to cut in the bass' : peaksDown(speaker?.peaks_down) + (expectedMark ? ', expected' : '');
  let line;
  if (bassOnly) line = 'Measured for the bass only.';
  else if (reach === 'bass') line = 'Above the bass: left alone, as Bass is chosen.';
  else if (!above) line = `Above the bass: already within ${halfDb(speaker?.room_within)} dB of the speaker's own balance, so left as it is.`;
  else line = `Above the bass: within ${halfDb(speaker?.within)} dB of the speaker's own balance.`;
  return [head, line];
}

/** The result's warning: which position the check found worse, and by how much. */
export function worseLine(worse) {
  if (!worse?.length) return 'No position is worse than before.';
  const [n, db] = worse[0];
  return worse.length === 1
    ? `Position ${n} is ${db.toFixed(1)} dB further from the target than before.`
    : `Positions ${worse.map((w) => w[0]).join(', ')} are further from the target than before.`;
}

/** **The corrections in two groups** (the design's 1g): in the bass, narrow
 *  cuts; above it, broad, up or down - each empty one saying why. */
export function correctionGroups(k, speaker, { range = 'full', reach = 'full' } = {}) {
  if (k === BOTH) {
    return [{ name: 'Both together', kind: '', rows: [],
      empty: "Each speaker's corrections are on its own tab. Both shows the two as you hear them." }];
  }
  const bass = cutRows(speaker?.cuts);
  const above = range === 'full' && reach === 'full' ? cutRows(speaker?.above) : [];
  return [
    { name: 'In the bass', kind: bass.length ? 'narrow cuts' : '', rows: bass, empty: 'Nothing to cut: near the target already.' },
    { name: 'Above the bass', kind: above.length ? 'broad, up or down' : '', rows: above,
      empty: range !== 'full' ? 'Not measured: this measurement covers the bass only.'
        : reach === 'bass' ? 'Left alone: Bass is chosen.'
          : `Nothing to correct: within ${halfDb(speaker?.room_within)} dB of the speaker's own balance already.` },
  ];
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
    if (freqs[i] < 20 || freqs[i] > LIMIT) continue;
    if (gap[i] < -3 && gap[i] <= gap[i - 1] && gap[i] <= gap[i + 1]) found.push([gap[i], Math.round(freqs[i])]);
  }
  return found.sort((a, b) => a[0] - b[0]).slice(0, 2).map((d) => d[1]).sort((a, b) => a - b);
}

/** **The correction's tail** (the design's 1g): the dips the bass keeps,
 *  then what is done above it. */
export function correctionTail(list, speaker) {
  const lead = 'In the bass only cuts: ';
  let low = '';
  if (speaker?.cuts?.length) {
    if (!list.length) low = `${lead}nothing is raised, as more power does not fill a dip. `;
    else if (list.length === 1) low = `${lead}the dip at ${list[0]} Hz stays, as more power does not fill it. `;
    else low = `${lead}the dips at ${list[0]} and ${list[1]} Hz stay, as more power does not fill them. `;
  }
  const high = speaker?.above?.length
    ? 'Above it the corrections are broad and 3 dB at most, so the speaker keeps its own balance.'
    : `Above the bass the room is already within ${halfDb(speaker?.room_within)} dB of the speaker's own balance, so it is left as it is.`;
  return low + high;
}

/** *3 November 2026 · three positions · full range* (the design's 1a). */
export const rangeWord = (range) => (range === 'full' ? 'full range' : 'bass only');

// ---- the chart (the design's §2: one axis split at 250 Hz) ---------------------------

export const FMIN = 15;
export const FMAX = 20000;
export const LIMIT = 250;
/** The bass pane's share of the width: its share of the log axis, about 39 %. */
export const BASS_SHARE = Math.log(LIMIT / FMIN) / Math.log(FMAX / FMIN);
/** x as a share of a pane's width, for a frequency on its range. */
export const fx = (f, x0 = FMIN, x1 = FMAX) => Math.log(f / x0) / Math.log(x1 / x0);
/** y as a share of the height, for a level on ±`span` dB. */
export const vy = (v, span = 15) => (span - v) / (2 * span);

/** **The bass pane's reach**: ±15 dB as the design draws it, wider in 5 dB
 *  steps when a curve of either speaker goes past it below the limit, so a
 *  peak is never cut flat by the chart's edge (sofapi, 2026-11-05: +18 dB
 *  at 45 Hz). The same on every tab. */
export function chartSpan(chart) {
  let top = 0;
  const freqs = chart?.freqs ?? [];
  for (const s of Object.values(chart?.speakers ?? {})) {
    for (const curve of [s.before, s.after, ...(s.positions ?? [])]) {
      (curve ?? []).forEach((v, i) => {
        if (freqs[i] <= LIMIT) top = Math.max(top, Math.abs(v));
      });
    }
  }
  return Math.min(30, Math.max(15, Math.ceil(top / 5) * 5));
}

//: A point belongs on a pane within 4 % of its ends (so a line meets the
//: edge), and up to `upto` Hz.
const onPane = (f, pane, upto) => f >= pane.x0 / 1.04 && f <= pane.x1 * 1.04 && f <= upto;

/** A curve on a pane (`{x0, x1, span}`), `w` by `h`. */
export function path(freqs, curve, pane, w, h, upto = Infinity) {
  let d = '';
  let pen = false;
  for (let i = 0; i < freqs.length; i++) {
    if (curve[i] == null || !onPane(freqs[i], pane, upto)) {
      pen = false;
      continue;
    }
    d += `${pen ? 'L' : 'M'}${(fx(freqs[i], pane.x0, pane.x1) * w).toFixed(1)},${(vy(curve[i], pane.span) * h).toFixed(1)}`;
    pen = true;
  }
  return d;
}

/** The area where `a` is above `b`: what the cuts take away (before over
 *  after), or what is raised (after over before). */
export function fill(freqs, a, b, pane, w, h, upto = Infinity) {
  let d = '';
  let run = [];
  const flush = () => {
    if (run.length > 1) {
      d += run.map((p, k) => `${k ? 'L' : 'M'}${p[0]},${p[1]}`).join('');
      d += run.slice().reverse().map((p) => `L${p[0]},${p[2]}`).join('') + 'Z';
    }
    run = [];
  };
  for (let i = 0; i < freqs.length; i++) {
    if (a[i] == null || b[i] == null || !onPane(freqs[i], pane, upto) || a[i] - b[i] < 0.05) {
      flush();
      continue;
    }
    const x = (fx(freqs[i], pane.x0, pane.x1) * w).toFixed(1);
    run.push([x, (vy(a[i], pane.span) * h).toFixed(1), (vy(b[i], pane.span) * h).toFixed(1)]);
  }
  flush();
  return d;
}
