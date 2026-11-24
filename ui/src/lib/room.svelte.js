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

/** **The chart's tabs**: each speaker's own (George, 2026-11-19, ADR-0186
 *  D4). `BOTH`: the two swept together, which the bass's cuts come from. */
export const BOTH = 'both';
export const sides = () => ['L', 'R'];
export const sideName = (k) => ({ L: 'Left', R: 'Right' })[k] ?? k;

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
  const n = bass + above;
  return `${k === 'L' ? 'Left' : 'Right'} speaker${n ? ` · ${n} ${n === 1 ? 'correction' : 'corrections'}` : ''}`;
}

/** *Peaks down by up to 8 dB*. */
export const peaksDown = (db) => `Peaks down by up to ${Math.max(0, Math.round(db ?? 0))} dB`;
/** *1.5*, *2*: a figure of half decibels. */
const halfDb = (db) => String(Math.round((db ?? 0) * 2) / 2);

/** **The result's heading and line** (the design's §2, *Result words*), for
 *  the speaker shown: `speaker` from the chart, `range` how far the
 *  measurement was made, `reach` how far it plays, `expected` not checked
 *  (`expectedMark`: say so in the heading). */
export function resultWords({ speaker, range = 'full', reach = 'full', expectedMark = false }) {
  const cuts = (speaker?.cuts ?? []).length;
  const above = (speaker?.above ?? []).length;
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
export function correctionGroups(speaker, { range = 'full', reach = 'full' } = {}) {
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

/** **Where a run measures**: five positions around the head (ADR-0187 D3,
 *  George, 2026-11-20). A measurement keeps its own number. */
export const POSITIONS = 5;
const COUNTS = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight'];
/** *three*, *five*: a number of positions in words. */
export const countWord = (n) => COUNTS[n] ?? String(n);
export const capitalised = (w) => w.charAt(0).toUpperCase() + w.slice(1);

/** **Where to move the microphone** (the design's R19-R20). */
export const MOVES = {
  2: 'About 40 cm to the left of where your head was and 15 cm higher',
  3: 'About 40 cm to the right of where your head was and 15 cm lower',
  4: 'About 30 cm in front of where your head was, at its height',
  5: 'About 30 cm straight above where your head was',
};
//: The seat drawing's places in its 340 x 196 box (1 is the head; 5 is
//: above it, drawn as a badge lifted off it - George, 2026-11-23, plan C).
export const PLACES = [[170, 98], [122, 98], [218, 98], [170, 46], [151, 79]];
//: Each position's height against the ear, in cm (ADR-0187 D3): marked on
//: the drawing and on its scale (George, 2026-11-23: with only the words,
//: positions 2 and 3 were placed at ear height).
export const HEIGHTS = [0, 15, -15, 0, 30];

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
export function correctionTail(list, speaker, { dipCard = false } = {}) {
  const lead = 'In the bass only cuts: ';
  let low = '';
  //: ADR-0187 D8: with the dips in a card of their own, only what is done
  //: above the bass.
  if (dipCard) {
    return speaker?.above?.length
      ? 'Above the bass the corrections are broad and 3 dB at most, so the speaker keeps its own balance.'
      : `Above the bass the room is already within ${halfDb(speaker?.room_within)} dB of the speaker's own balance, so it is left as it is.`;
  }
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

/** **The speakers' timing** (ADR-0185 D2), in a sentence: `distance` is how
 *  much further the right speaker is than the left (cm; null: not timed),
 *  `delay` each speaker's (ms, or none yet). Null when there is nothing to
 *  say. */
export function alignedLine(distance, delay) {
  if (distance == null) return null;
  const cm = Math.round(Math.abs(distance));
  if (cm < 1) return 'Both speakers are the same distance from your seat.';
  const [further, nearer] = distance > 0 ? ['right', 'left'] : ['left', 'right'];
  //: The delay as kept, or (while measuring) as the distance makes it.
  const ms = delay ? Math.max(...delay) : Math.abs(distance) / 34.3;
  return `The ${further} speaker is ${cm} cm further away, so the ${nearer} one plays ${ms.toFixed(ms < 1 ? 2 : 1)} ms later and both reach your seat together.`;
}

/** **The speakers' level as kept** (ADR-0187 D2): which one is turned down,
 *  by how much, from `level_db` ([left, right], cuts); null when none. */
export function levelLine(level) {
  if (!level) return null;
  const [l, r] = level;
  if (Math.max(-l, -r) < 0.05) return null;
  const [down, other, db] = l < r ? ['left', 'right', -l] : ['right', 'left', -r];
  return `The ${down} speaker is turned down ${db.toFixed(1)} dB to match the ${other}.`;
}

/** **The speaker check's list** (ADR-0187; George's choice A, 2026-11-23):
 *  a row for each thing checked, as `{ kind, name, sub }` - ok or warn -
 *  from the run's state: `distance_cm`, `right_db` (how much louder the
 *  right was; null: not read), `sides` ('right', 'unsure' or null).
 *  `was`: the kept measurement's `delay_ms` and `level_db`, said against
 *  when the check leaves it behind, its first two rows then one (ADR-0188
 *  D2, the screen George chose 2026-11-23). */
export function checkRows(run, was = null) {
  if (run?.distance_cm == null) {
    return [{ kind: 'warn', name: "The speakers' timing could not be read",
      sub: 'Nothing is delayed or matched. A quieter moment may help: check again.' }];
  }
  const rows = [];
  if (run.sides === 'right' && was) {
    rows.push({ kind: 'ok', name: 'Left and right, wired the same way', sub: 'The right way round, + to + on both.' });
  } else {
    if (run.sides === 'right') rows.push({ kind: 'ok', name: 'Left and right', sub: 'The right way round.' });
    else rows.push({ kind: 'warn', name: 'Left and right not told apart',
      sub: 'From position 2 neither sounded clearly nearer. Check that the microphone went to the left of your head.' });
    rows.push({ kind: 'ok', name: 'Wired the same way', sub: '+ to + on both.' });
  }
  const cm = Math.round(Math.abs(run.distance_cm));
  //: The left's delay against the right's, now and then (ms).
  const late = run.distance_cm / 34.3;
  const then = was?.delay_ms ? was.delay_ms[0] - was.delay_ms[1] : null;
  if (cm < 1) {
    rows.push({ kind: 'ok', name: 'The same distance away', sub: 'Nothing to delay.' });
  } else {
    const [further, nearer] = run.distance_cm > 0 ? ['right', 'left'] : ['left', 'right'];
    const ms = Math.abs(late);
    const moved = then == null ? null : (late - then) * Math.sign(late);
    rows.push({ kind: 'ok', name: `The ${further} is ${cm} cm further away`,
      sub: moved == null ? `The ${nearer} plays ${ms.toFixed(ms < 1 ? 2 : 1)} ms later, so both reach your seat together.`
        : `The ${nearer} plays ${ms.toFixed(ms < 1 ? 2 : 1)} ms later: ${Math.abs(moved) < 0.005 ? 'as'
          : `${Math.abs(moved).toFixed(2)} ms ${moved > 0 ? 'more' : 'less'} than`} when the room was measured.` });
  }
  const db = run.right_db;
  if (db == null) {
    rows.push({ kind: 'warn', name: 'The level could not be read',
      sub: 'Two readings did not agree, so both play as they are. A quieter moment may help: check again.' });
  } else if (Math.abs(db) < 0.05) {
    rows.push({ kind: 'ok', name: 'As loud as each other', sub: 'Nothing to match.' });
  } else {
    const down = db > 0 ? 'right' : 'left';
    const cut = Math.abs(db);
    const cutThen = was?.level_db ? -was.level_db[down === 'left' ? 0 : 1] : null;
    const more = cutThen == null ? null : cut - cutThen;
    rows.push({ kind: 'ok', name: `The right is ${cut.toFixed(1)} dB ${db > 0 ? 'louder' : 'quieter'}`,
      sub: more == null ? `The ${down} is turned down ${cut.toFixed(1)} dB to match.`
        : `The ${down} is turned down ${cut.toFixed(1)} dB: ${Math.abs(more) < 0.05 ? 'as'
          : `${Math.abs(more).toFixed(1)} dB ${more > 0 ? 'more' : 'less'} than`} then.` });
  }
  return rows;
}

/** **The Speakers card** (ADR-0188 D1, the room page George chose
 *  2026-11-23): its line and its ticked rows, from the alignment kept
 *  (`speakers`: on, day, distance_cm, delay_ms, right_db, sides); one row
 *  each for the wiring, the distance and the level. */
export function speakersLine(a) {
  if (!a) return 'Not checked yet.';
  if (!a.on) return `Checked ${a.day}. Off: both play as they are.`;
  if (a.distance_cm == null) return `Checked ${a.day}.`;
  return `Checked ${a.day}. Both reach your seat together${a.right_db == null ? '' : ' and equally loud'}.`;
}
export function speakersRows(a) {
  if (!a) return [];
  const rows = [];
  if (a.sides === 'right') rows.push({ kind: 'ok', text: 'Left and right the right way round, wired the same way.' });
  else if (a.sides === 'unsure') rows.push({ kind: 'warn', text: 'Left and right not told apart; wired the same way.' });
  else rows.push({ kind: 'ok', text: 'Wired the same way.' });
  if (a.distance_cm == null) {
    rows.push({ kind: 'warn', text: "The speakers' timing could not be read: nothing is delayed." });
  } else if (Math.round(Math.abs(a.distance_cm)) < 1) {
    rows.push({ kind: 'ok', text: 'Both the same distance away: nothing to delay.' });
  } else {
    const [further, nearer] = a.distance_cm > 0 ? ['right', 'left'] : ['left', 'right'];
    const ms = Math.max(...(a.delay_ms ?? [Math.abs(a.distance_cm) / 34.3]));
    rows.push({ kind: 'ok', text: `The ${further} is ${Math.round(Math.abs(a.distance_cm))} cm further away: the ${nearer} plays ${ms.toFixed(ms < 1 ? 2 : 1)} ms later.` });
  }
  const db = a.right_db;
  if (db == null) rows.push({ kind: 'warn', text: 'The level was not read: both play as they are.' });
  else if (Math.abs(db) < 0.05) rows.push({ kind: 'ok', text: 'As loud as each other: nothing to match.' });
  else rows.push({ kind: 'ok', text: `The right is ${Math.abs(db).toFixed(1)} dB ${db > 0 ? 'louder' : 'quieter'}: the ${db > 0 ? 'right' : 'left'} is turned down ${Math.abs(db).toFixed(1)} dB.` });
  return rows;
}

/** **The alignment in a few characters** (ADR-0188 C6, the panel and the
 *  bar George chose 2026-11-24): the nearer speaker's delay and the louder's
 *  cut, *0.36 ms · −1.5 dB*. */
export function speakersShort(a) {
  if (!a) return '';
  const parts = [];
  const ms = Math.max(...(a.delay_ms ?? [0]));
  const db = -Math.min(...(a.level_db ?? [0]));
  if (ms >= 0.005) parts.push(`${ms.toFixed(2)} ms`);
  if (db >= 0.05) parts.push(`−${db.toFixed(1)} dB`);
  return parts.join(' · ') || 'Nothing to align';
}

/** **The ringing card** (ADR-0187 D7, George's choice B, 2026-11-23): the
 *  four bands that rang most before, low to high, each `{ hz, before,
 *  after }` - dB at 0.2 s against the first 50 ms. */
export function ringBands(speaker, n = 4) {
  return (speaker?.ringing ?? []).slice().sort((a, b) => b.before - a.before).slice(0, n)
    .sort((a, b) => a.hz - b.hz);
}
/** A bar's length: nothing left at −50 dB, all of it at −15 dB. */
export const ringWidth = (db) => `${Math.max(4, Math.min(100, Math.round(((db + 50) / 35) * 100)))}%`;
export const ringDb = (db) => (db == null ? '—' : `${db < 0 ? '−' : '+'}${Math.abs(Math.round(db))} dB`);
export const bandWord = (hz) => `${Number.isInteger(hz) ? hz : hz.toFixed(1)} Hz`;

/** **A card per dip** (ADR-0187 D8, George's choice B, 2026-11-23; the
 *  words the mock-up's): each dip the bass keeps, `{ freq, depth, tag,
 *  tone, text }`, low to high. A wall's dip says *a wall or the floor*: the
 *  player cannot tell which surface sends the sound back. */
export function dipRows(dips) {
  const whose = { L: "the left speaker's", R: "the right speaker's", both: "both speakers'" };
  const which = { L: 'the left speaker', R: 'the right speaker', both: 'the speakers' };
  return (dips ?? []).slice().sort((a, b) => a.freq - b.freq).map((d) => {
    const row = { freq: freqWord(d.freq), depth: `−${Math.round(d.depth)} dB`, tag: null, tone: 'none',
      text: 'What causes it is not clear from the measurement.' };
    if (d.cause === 'cancel') {
      Object.assign(row, { tag: 'The two speakers cancel', tone: 'blue',
        text: 'Each alone has no dip here. Placing both the same distance from the wall behind them may lessen it.' });
    } else if (d.cause === 'wall') {
      Object.assign(row, { tag: `A wall or the floor about ${d.distance_m.toFixed(1)} m away`, tone: 'amber',
        text: `It sends ${whose[d.speaker] ?? "the speaker's"} sound back out of step. Moving ${which[d.speaker] ?? 'the speaker'} closer to it or further from it moves the dip.` });
    } else if (d.cause === 'local') {
      Object.assign(row, { tag: 'Only at some places', tone: 'grey',
        text: 'It changes from place to place around your head: moving the seat a little moves it.' });
    }
    return row;
  });
}

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
