// SPDX-License-Identifier: GPL-3.0-or-later
// What the phone's radio writes about a station (design/source/31, H01-H24).
import { stationMeta } from '../../../lib/radio.js';

const rate = (s) => (s?.bitrate ? `${s.bitrate} kb/s` : null);

/** A row's meta: *Germany · MP3 · 128 kb/s*; one added by its address has
 *  no country and says where it came from (H16). */
export function rowMeta(station) {
  if (station?.listed === false) return ['Added by address', station.codec, rate(station)].filter(Boolean).join(' · ');
  return stationMeta(station);
}

/** The remote's quality line without a screen (H20): *FLAC · 1411 kb/s*. */
export const quality = (station) => [station?.codec, rate(station)].filter(Boolean).join(' · ');

/** The directory's names come in lower case (*hip hop*); the design writes
 *  them as *Hip hop*. */
export const named = (text) => (text ? text.charAt(0).toUpperCase() + text.slice(1) : text);

/** A country's name for its two letters, in English, or the letters. */
export function countryName(code) {
  try {
    return new Intl.DisplayNames(['en-GB'], { type: 'region' }).of(code) ?? code;
  } catch {
    return code;
  }
}

/** Countries A to Z, a leading *The* left out of the order. */
export const byName = (a, b) =>
  a.name.replace(/^the\s+/i, '').localeCompare(b.name.replace(/^the\s+/i, ''), 'en');
