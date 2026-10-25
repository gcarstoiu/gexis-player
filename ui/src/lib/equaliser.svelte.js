// SPDX-License-Identifier: GPL-3.0-or-later
//
// The equaliser (ADR-0162; design/source/20, look 3a "Ridge"): what every
// surface draws from, the requests that change it, and the drawing itself -
// the line through the knobs, the colours, the glide between settings.
//
// The state is the core's (`/state`'s `equaliser`): this module keeps only
// what is drawn while a finger moves a band or a setting glides in.
import { derived } from 'svelte/store';
import { playback } from './state.js';

/** The equaliser for the output in use, or null with no output (or an older core). */
export const equaliser = derived(playback, ($s) => $s?.equaliser ?? null);

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

/** `on`, `sel`, `gains` or `band` with `gain`, for the output in use. */
export const setEqualiser = (changes) => call('PUT', '/equaliser', changes);
export const saveEqualiser = (name) => call('POST', '/equaliser/settings', { name });
export const renameEqualiser = (key, name) =>
  call('PUT', `/equaliser/settings/${encodeURIComponent(key)}`, { name });
export const deleteEqualiser = (key) => call('DELETE', `/equaliser/settings/${encodeURIComponent(key)}`);

/** **The bands while a finger moves them**: one request in flight, and only
 *  the latest after it, as the volume slider sends - so a drag is heard as
 *  it happens and never queues up behind itself. */
export class BandSender {
  #inFlight = false;
  #queued = null;
  #onerror;

  constructor(onerror = () => {}) {
    this.#onerror = onerror;
  }

  send(gains) {
    this.#queued = gains.slice();
    if (!this.#inFlight) this.#next();
  }

  async #next() {
    const gains = this.#queued;
    if (gains == null) return;
    this.#queued = null;
    this.#inFlight = true;
    try {
      await setEqualiser({ gains });
    } catch (error) {
      this.#onerror(error);
    } finally {
      this.#inFlight = false;
    }
    if (this.#queued != null) this.#next();
  }
}

// ---- the drawing -------------------------------------------------------------

export const MIN = -12;
export const MAX = 12;
export const clamp = (g) => Math.max(MIN, Math.min(MAX, Math.round(g)));

/** A gain as the design writes it: +4, −1 (a real minus), 0. */
export function fmt(value) {
  const v = Math.round(value);
  return v > 0 ? `+${v}` : v < 0 ? `−${Math.abs(v)}` : '0';
}

/** A headroom in dB: 5 dB, 2.5 dB. */
export const dbText = (h) => `${h % 1 ? h.toFixed(1) : String(h)} dB`;

const BOOST_LOW = [239, 143, 122];
const BOOST_HIGH = [242, 179, 94];
const CUT_LOW = [127, 176, 220];
const CUT_HIGH = [164, 140, 232];
const ZERO = 'rgba(233, 238, 242, 0.6)';
const mix = (a, b, t) => a.map((v, j) => Math.round(v + (b[j] - v) * t));

/** **A band's value colour** (the design's): a boost warms from coral to
 *  amber, a cut deepens from blue to violet, by |g| / 12; 0 is pale. */
export function valueInk(value) {
  const g = Math.round(value);
  const t = Math.min(1, Math.abs(g) / 12);
  if (g > 0) return `rgb(${mix(BOOST_LOW, BOOST_HIGH, t).join(',')})`;
  if (g < 0) return `rgb(${mix(CUT_LOW, CUT_HIGH, t).join(',')})`;
  return ZERO;
}

/** **The line through the knobs**, in a 1000 × 240 box where 0 dB is the
 *  middle and each band sits at the centre of its tenth: a monotone cubic
 *  (Fritsch-Carlson), so it never dips or overshoots between two bands;
 *  flat out to both edges. `area` closes it on 0 dB, for the fill. */
export function ridge(gains, height = 240) {
  const n = gains.length;
  const h = 1000 / n;
  const mid = height / 2;
  const perDb = mid / 12;
  const y = gains.map((v) => mid - v * perDb);
  const d = [];
  for (let i = 0; i < n - 1; i++) d.push((y[i + 1] - y[i]) / h);
  const m = y.map((_, i) => (i === 0 || i === n - 1 || d[i - 1] * d[i] <= 0) ? 0 : (2 * d[i - 1] * d[i]) / (d[i - 1] + d[i]));
  const f = (v) => v.toFixed(1);
  let line = `M0 ${f(y[0])} L${f(h / 2)} ${f(y[0])}`;
  for (let i = 0; i < n - 1; i++) {
    const x0 = i * h + h / 2;
    const x1 = x0 + h;
    line += ` C${f(x0 + h / 3)} ${f(y[i] + (m[i] * h) / 3)} ${f(x1 - h / 3)} ${f(y[i + 1] - (m[i + 1] * h) / 3)} ${f(x1)} ${f(y[i + 1])}`;
  }
  line += ` L1000 ${f(y[n - 1])}`;
  return { line, area: `${line} L1000 ${mid} L0 ${mid} Z` };
}

/** **The glide between settings** (the design's): each band eases from where
 *  it is drawn to its new level over 380 ms, ease-out cubic, band i starting
 *  32 ms × i after the lowest. Only the drawing moves; the setting is chosen
 *  at once. `drawn` is null when nothing glides. */
export class Glide {
  drawn = $state(null);
  #raf = 0;

  static DURATION = 380;
  static STEP = 32;

  to(from, target) {
    cancelAnimationFrame(this.#raf);
    const start = this.drawn ?? from;
    if (!start || start.every((v, i) => v === target[i])) {
      this.drawn = null;
      return;
    }
    // The first frame draws the old levels, not the new ones.
    this.drawn = start.slice();
    const t0 = performance.now();
    const ease = (x) => 1 - Math.pow(1 - x, 3);
    const end = (target.length - 1) * Glide.STEP + Glide.DURATION;
    const tick = (now) => {
      const elapsed = now - t0;
      if (elapsed >= end) {
        this.drawn = null;
        return;
      }
      this.drawn = target.map((v, i) => {
        const k = Math.max(0, Math.min(1, (elapsed - i * Glide.STEP) / Glide.DURATION));
        return start[i] + (v - start[i]) * ease(k);
      });
      this.#raf = requestAnimationFrame(tick);
    };
    this.#raf = requestAnimationFrame(tick);
  }

  stop() {
    cancelAnimationFrame(this.#raf);
    this.drawn = null;
  }
}

const NOUN = { DAC: 'DAC', Optical: 'optical output', Headphones: 'headphone jack', 'USB DAC': 'USB DAC' };

/** What the output is called in the crumbs: *the DAC, HiFiBerry DAC+ HD*;
 *  HDMI by its own name, *HDMI 1*. */
export function outputPhrase(output) {
  if (!output) return '';
  const { kind, name } = output;
  if (kind === 'HDMI') return name;
  const noun = NOUN[kind] ?? kind;
  return name.toLowerCase() === noun.toLowerCase() ? `the ${noun}` : `the ${noun}, ${name}`;
}

/** The output in a word, for the bar's crumb: *DAC*, *HDMI*, *Optical*. */
export const outputShort = (output) => (output ? (output.kind === 'Headphones' ? 'Jack' : output.kind) : '');

/** **The headroom note** (ADR-0162 D3), and what stands in its place:
 *  `{ badge, text, amber }`. */
export function note(eq) {
  if (!eq.on) return { badge: 'Off', text: 'Off. The sound is untouched, bit-perfect.', amber: false };
  if (eq.dsd) {
    return { badge: 'DSD', text: 'DSD plays untouched. The equaliser stands aside for this track and is back for the next PCM one.', amber: false };
  }
  const h = eq.headroom_db;
  if (h > 0 && eq.fixed) {
    return {
      badge: `−${dbText(h)}`,
      text: `Lowered by ${dbText(h)} so the boost cannot clip. With Fixed volume the music plays ${dbText(h)} quieter: turn the amplifier up to match.`,
      amber: true,
    };
  }
  if (h > 0) return { badge: `−${dbText(h)}`, text: `Lowered by ${dbText(h)} so the boost cannot clip.`, amber: false };
  return { badge: '0 dB', text: 'No boost, so nothing is lowered.', amber: false };
}

/** The setting in use as the quick change names it: *Rock · preset*. */
export function stateLine(eq) {
  if (!eq.on) return { text: 'Off · bit-perfect', amber: false };
  if (eq.dsd) return { text: `${eq.name ?? 'Flat'} · stands aside while DSD plays`, amber: false };
  if (eq.sel === 'custom') return { text: 'Custom · not saved', amber: true };
  const own = eq.own.some((o) => o.key === eq.sel);
  return { text: `${eq.name ?? 'Flat'} · ${own ? 'yours' : 'preset'}`, amber: false };
}

/** The quick change's shorter note: nothing when there is nothing to say. */
export function quickNote(eq) {
  if (!eq.on) return { text: '', amber: false };
  if (eq.dsd) return { text: 'DSD plays untouched. The equaliser is back for the next PCM track.', amber: false };
  const h = eq.headroom_db;
  if (h > 0 && eq.fixed) {
    return { text: `Lowered by ${dbText(h)} so the boost cannot clip. With Fixed volume, turn the amplifier up ${dbText(h)} to match.`, amber: true };
  }
  if (h > 0) return { text: `Lowered by ${dbText(h)} so the boost cannot clip.`, amber: false };
  return { text: '', amber: false };
}
