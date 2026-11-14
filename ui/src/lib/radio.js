// SPDX-License-Identifier: GPL-3.0-or-later
//
// **Internet radio** (ADR-0180; design/source/31): the player's own radio,
// with or without Lyrion. Every surface - the panel, the bars, the phone -
// reads it through this module: the core's `/stations` routes, and the
// `radio` part of `/state`.
//
// Not Lyrion's radio (`browseRadio` in library.js), which stays as it is and
// opens from Radio as *Lyrion's radio*.
//
// A station is what the core gives: `{id, name, url, logo, country,
// countrycode, codec, bitrate, hls, listed, favourite?}`. Its `logo` is the
// player's own address for it (`/stations/logo/<key>`), never a station's
// site (George, 2026-11-14), or null.
import { derived, writable } from 'svelte/store';
import { playback } from './state.js';

async function call(path, init) {
  const response = await fetch(path, init);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body.error ?? `HTTP ${response.status}`);
    error.status = response.status;
    //: 503 from a list: the directory cannot be reached and nothing from the
    //: last day is kept (the design's `DirectoryBanner`, kind `none`).
    error.unreachable = response.status === 503 && body.reachable === false;
    throw error;
  }
  return body;
}

const json = (method, body) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});
const q = (params) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== null && v !== undefined && v !== '') s.set(k, String(v));
  const text = s.toString();
  return text ? `?${text}` : '';
};

/** The Radio screen's top: `{enabled, country, reachable, favourites}`.
 *  Answers with the directory down. */
export const loadOverview = () => call('/stations');
/** A page of stations: `{stations, offset, end, reachable}`. */
export const loadPopular = (offset = 0) => call(`/stations/popular${q({ offset })}`);
export const loadStations = ({ genre, country, language, offset = 0 }) =>
  call(`/stations/list${q({ genre, country, language, offset })}`);
export const searchStations = (text, offset = 0) => call(`/stations/search${q({ q: text, offset })}`);
/** `{genres: [{name, stations}]}`, `{countries: [{code, name, stations}]}`,
 *  `{languages: [{name, code, stations}]}`. */
export const loadGenres = () => call('/stations/genres');
export const loadCountries = () => call('/stations/countries');
export const loadLanguages = () => call('/stations/languages');

/** Play a station a list gave, or a favourite by its id. The radio takes the
 *  output as any takeover; how it goes arrives in `/state`'s `radio`. */
export const playStation = (station) => call('/stations/play', json('POST', { station }));
export const playFavourite = (id) => call('/stations/play', json('POST', { favourite: id }));

export const loadFavourites = () => call('/stations/favourites');
export const addFavourite = (station) => call('/stations/favourites', json('POST', { station }));
export const removeFavourite = (id) => call(`/stations/favourites/${encodeURIComponent(id)}`, { method: 'DELETE' });
/** Every favourite's id, once, in the new order. */
export const orderFavourites = (ids) => call('/stations/favourites', json('PUT', { ids }));
/** Played on the player first; kept only if it sounds (decision 4). Answers
 *  when that is known: `{ok, station}`, or an error with status 422 when it
 *  did not play. */
export const addByAddress = (url, name) => call('/stations/favourites/address', json('POST', { url, name }));

/** The radio's own state from `/state`: `{station, state, attempt, tries,
 *  lines, favourites}` or null before a station was played. `state` is
 *  connecting, playing, reconnecting, stopped or not_answering; `lines` is
 *  split, whole or none; `favourites` a revision raised on every change. */
export const radio = derived(playback, ($s) => $s?.radio ?? null);

/** **The favourites, kept current on every surface**: read once, and again
 *  whenever the core says they changed (the revision in `radio`). */
export const favourites = writable(null);
let seenRevision = null;
let reading = null;
let favouritesWanted = false;
export function refreshFavourites() {
  reading ??= loadFavourites()
    .then((body) => favourites.set(body.favourites ?? []))
    .catch(() => {})
    .finally(() => (reading = null));
  return reading;
}
radio.subscribe(($r) => {
  const revision = $r?.favourites ?? null;
  if (revision === seenRevision) return;
  seenRevision = revision;
  // Only once somebody reads them: the first subscriber below loads them.
  if (favouritesWanted) refreshFavourites();
});
/** Call from a screen that shows favourites: loads them on first use. */
export function wantFavourites() {
  if (!favouritesWanted) {
    favouritesWanted = true;
    refreshFavourites();
  }
}

/** A station row's meta (2a): *Germany · MP3 · 128 kb/s*. */
export function stationMeta(station) {
  return [station?.country, station?.codec, station?.bitrate ? `${station.bitrate} kb/s` : null]
    .filter(Boolean)
    .join(' · ');
}

/** Now Playing's quality line (7b): *FLAC · 1411 kb/s · Germany*. */
export function qualityLine(station) {
  return [station?.codec, station?.bitrate ? `${station.bitrate} kb/s` : null, station?.country]
    .filter(Boolean)
    .join(' · ');
}

/** Whether the station playing now is the radio's and is a favourite -
 *  Next and Previous then step through the favourites (decision 6). */
export const isRadio = (active) => active === 'radio';

/** A count with a thousands separator, as the design writes them (1,240). */
export const count = (n) => (typeof n === 'number' ? n.toLocaleString('en-GB') : '');
