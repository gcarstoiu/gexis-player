// SPDX-License-Identifier: GPL-3.0-or-later
//
// Library reads (ADR-0038 §5): the core runs LMS's typed queries and
// answers with the fields a screen draws. The panel never talks to LMS,
// except to load artwork, whose URLs point straight at it (ADR-0020).
//
// The root's data is loaded once when the panel starts, not when Home
// opens, and its covers are decoded before it is published: otherwise the
// New Music tiles arrive visibly after the cards above them (George,
// 2026-09-17). Reopening Home then costs nothing, and a later reload only
// replaces what is already on screen.
import { writable } from 'svelte/store';

async function get(path) {
  const response = await fetch(`/library/${path}`);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error ?? `HTTP ${response.status}`);
  return body;
}

/** `{counts, albums}`, or nulls until the first load finishes. */
export const libraryRoot = writable({ counts: null, albums: [] });

/** Artist photo URLs the panel has already been told about, keyed by
 *  `<id>` for the grid and `<id>@300` for the artist page.
 *
 *  **Module state, not component state.** The library screen is mounted only
 *  while it is open (Phase 7's fix for the black screen it left behind), so
 *  anything it holds is thrown away every time it closes - and every artist
 *  was asked about again on the way back in (George, 2026-09-18). The
 *  daemon answers those from its own cache, but the panel still waited on a
 *  round trip per screenful before drawing a face it had already drawn. */
export const artistPhotos = writable({});

/** Waits for the image, but never on it: a cover that 404s or hangs must
 *  not hold up the rest of the strip. The screen falls back to an empty
 *  well for it, as it does for an album with no artwork at all. */
function decoded(url, timeoutMs = 4000) {
  if (!url) return Promise.resolve();
  return new Promise((resolve) => {
    const image = new Image();
    const done = () => resolve();
    image.onload = done;
    image.onerror = done;
    image.src = url;
    setTimeout(done, timeoutMs);
  });
}

/** One album with its tracks, covers decoded first so the page arrives
 *  whole rather than filling in (ADR-0038 §1). */
export async function loadAlbum(id) {
  const album = await get(`albums/${id}`);
  await decoded(album.artwork);
  return album;
}

/** Play something, or add it to the queue (ADR-0038 §3, §5). A 200 means
 *  the command was sent; the result arrives on /state. */
export async function libraryAction(kind, id, action = 'play', playlistId = null) {
  const response = await fetch('/library/action', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kind, id, action, playlist_id: playlistId }),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error ?? `HTTP ${response.status}`);
  return body;
}

/** Every album artist in one read: 917 of them come back in a single
 *  98 KB reply in about 23 ms (Finding 029 §1), so there is nothing to page. */
export const loadArtists = () => get('artists');

/** An artist's discography, newest first, covers decoded first so the page
 *  arrives whole. */
export async function loadArtistAlbums(id) {
  const albums = await get(`artists/${id}/albums`);
  await Promise.all(albums.slice(0, 12).map((album) => decoded(album.artwork)));
  return albums;
}

/** The album's own record, with its tracks. */
export const loadAlbumTracks = (id) => get(`albums/${id}`);

/** The library's own playlists, with their track counts, for the chooser. */
export const loadPlaylists = () => get('playlists');

/** One playlist with its tracks. */
export const loadPlaylist = (id) => get(`playlists/${id}`);

/** One level of the radio tree. The panel holds handles the core issued,
 *  never an LMS command (ADR-0038 §5). */
export async function browseRadio(handle = null) {
  const response = await fetch(`/radio${handle ? `?at=${encodeURIComponent(handle)}` : ''}`);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error ?? `HTTP ${response.status}`);
  return body;
}

/** Play a station, or add it to the queue, by its handle. */
export async function radioPlay(handle, action = 'play') {
  const response = await fetch('/radio/play', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ handle, action }),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error ?? `HTTP ${response.status}`);
  return body;
}

let inFlight = null;

/** Read the root's counts and New Music, decode the covers, then publish
 *  both together. Concurrent calls share one read. */
export function loadLibraryRoot() {
  if (inFlight) return inFlight;
  inFlight = (async () => {
    try {
      const [counts, albums] = await Promise.all([get('counts'), get('new')]);
      await Promise.all(albums.map((album) => decoded(album.artwork)));
      libraryRoot.set({ counts, albums });
    } catch (err) {
      console.info('library:', err.message);
    } finally {
      inFlight = null;
    }
  })();
  return inFlight;
}

/** Artist photos from LMS's own plugin, for the artists about to be drawn
 *  (ADR-0040 §1). Asked in batches rather than for the library: 40 took
 *  212 ms against George's server, 917 would be neither necessary nor kind
 *  (Finding 035). A server without the plugin answers null for every id,
 *  which is not an error - the circle keeps its initials. */
export async function loadArtistPhotos(ids, size = 200) {
  if (!ids.length) return {};
  try {
    const response = await fetch(`/library/artist-photos?ids=${ids.join(',')}&size=${size}`);
    if (!response.ok) return {};
    const found = await response.json();
    const suffix = size === 200 ? '' : `@${size}`;
    artistPhotos.update((known) => {
      const next = { ...known };
      // Misses are remembered too, so a face that has none is not asked
      // about on every pass of the observer.
      for (const id of ids) next[`${id}${suffix}`] = found[id] ?? null;
      return next;
    });
    return found;
  } catch {
    return {};
  }
}

/** What the artist page draws below its discography: the biography with the
 *  credit its licence requires, and similar artists (ADR-0038 §2, filled by
 *  Phase 8). LMS's own plugin answers first where the server has it. */
export async function loadArtistInfo(id, name) {
  try {
    const response = await fetch(
      `/library/artist-info?id=${encodeURIComponent(id)}&name=${encodeURIComponent(name)}`,
    );
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (err) {
    console.info('artist-info:', err.message);
    return null;
  }
}
