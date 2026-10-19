// SPDX-License-Identifier: GPL-3.0-or-later
// The moon at night (ADR-0153): whether it is night, and how much of the
// moon is lit. Worked out here from the date, with no service asked.

/** A mean synodic month, in days. */
const SYNODIC = 29.530588853;
/** A new moon: 6 January 2000, 18:14 UTC. */
const NEW_MOON = Date.UTC(2000, 0, 6, 18, 14);

/**
 * Where the moon is in its month at `ms`: 0 new, 0.25 first quarter, 0.5
 * full, 0.75 last quarter. Off by at most about a day from the real phase,
 * which no icon this size can show.
 */
export function moonPhase(ms) {
  const days = (ms - NEW_MOON) / 86400000;
  return (((days % SYNODIC) + SYNODIC) % SYNODIC) / SYNODIC;
}

/** The fraction of the disc that is lit, 0 to 1. */
export function moonLit(phase) {
  return (1 - Math.cos(2 * Math.PI * phase)) / 2;
}

/**
 * Night: before today's sunrise or after today's sunset, by the screen's own
 * clock against the moments the core sends (`sun.rise_at`, `sun.sets_at`,
 * seconds). Without them it is day - a sun is never wrong for long.
 */
export function isNight(sun, ms) {
  const rise = sun?.rise_at, set = sun?.sets_at;
  if (typeof rise !== 'number' || typeof set !== 'number') return false;
  const s = ms / 1000;
  return s < rise || s >= set;
}

/**
 * The lit part as an SVG path, in a 100x100 box with a disc of radius `r` at
 * its centre, lit on the right (waxing, seen from the north). The caller
 * mirrors it for a waning moon, and again south of the equator.
 */
export function litPath(phase, r, cx = 50, cy = 50, left = false) {
  const k = moonLit(phase);
  const rx = Math.abs(1 - 2 * k) * r;
  const top = cy - r, bottom = cy + r;
  // A crescent's terminator bows towards the lit side; a gibbous one away.
  // `left` draws it lit on the left without mirroring what lies under it
  // (the Photographic set's moon is a photograph, and must not be flipped).
  const sweep = (k > 0.5) !== left ? 1 : 0;
  return `M ${cx} ${top} A ${r} ${r} 0 0 ${left ? 0 : 1} ${cx} ${bottom} A ${rx.toFixed(2)} ${r} 0 0 ${sweep} ${cx} ${top} Z`;
}
