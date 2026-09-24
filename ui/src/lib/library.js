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
import { playback } from './state.js';

async function get(path) {
  const response = await fetch(`/library/${path}`);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error ?? `HTTP ${response.status}`);
  return body;
}

/** `{counts, albums}`, or nulls until the first load finishes. */
export const libraryRoot = writable({ counts: null, albums: [], strip: null });

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
/** Two spellings of one artist name, compared. Curly quotes, accents and
 *  punctuation all differ between what a renderer reports and what the
 *  library holds; none of them mean a different artist. */
export const foldedName = (name) =>
  (name ?? '')
    .normalize('NFKD')
    .replace(/[\u2018\u2019'`\u00b4]/g, '')
    .replace(/[^a-zA-Z0-9]+/g, ' ')
    .trim()
    .toLowerCase();

export const loadArtists = () => get('artists');

/** An artist's discography, newest first, covers decoded first so the page
 *  arrives whole. */
/** The artist's genres, for the tag pills under their name. LMS answers this
 *  from its own tables, so it needs no provider and no network lookup - and
 *  an artist with none simply has no pills. */
export const loadArtistGenres = (id) => get(`artists/${id}/genres`);

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

//: Same signal `lib/settings.js` refetches on: the daemon bumps it on every
//: write, and the strip is a read of two settings.
let seenRevision;
playback.subscribe(($state) => {
  const revision = $state?.settings_revision;
  if (revision === undefined || revision === seenRevision) return;
  const first = seenRevision === undefined;
  seenRevision = revision;
  if (!first) reloadStrip();
});

//: **The library's pictures changed under us** (ADR-0059): the artwork sweep
//: has finished and the faces we are holding are the ones it replaced. This
//: store is only ever filled - `loadArtistPhotos` skips an id it already has
//: - so after a sweep the panel kept showing LMS's photos for the whole
//: session, and a reboot was the only cure (George, 2026-09-24: "the artist
//: navigation is not loading the new art").
//:
//: Its own signal, not `settings_revision`: that one fires on every write,
//: and throwing away every face to ask again is right once and ruinous 917
//: times.
let seenPictures;
playback.subscribe(($state) => {
  const revision = $state?.pictures_revision;
  if (revision === undefined || revision === seenPictures) return;
  const first = seenPictures === undefined;
  seenPictures = revision;
  if (!first) artistPhotos.set({});
});

/** Read the root's counts and its strip, decode any covers, then publish
 *  both together. Concurrent calls share one read.
 *
 *  **The strip is whichever shape `home_strip` names** (9h): the daemon
 *  reads the setting and answers with one of three, because two of them
 *  cost an LMS browse plus a count per artist and nobody sees the other
 *  two. Albums arrive with artwork to decode; artists arrive with a name
 *  and an album count, and their pictures follow the same route the artist
 *  grid uses. */
export function loadLibraryRoot() {
  if (inFlight) return inFlight;
  inFlight = (async () => {
    try {
      const [counts, strip] = await Promise.all([get('counts'), get('strip')]);
      const albums = strip.albums ?? [];
      await Promise.all(albums.map((album) => decoded(album.artwork)));
      libraryRoot.set({ counts, albums, strip });
    } catch (err) {
      console.info('library:', err.message);
    } finally {
      inFlight = null;
    }
  })();
  return inFlight;
}

/** Read the strip again, for when `home_strip` or `home_strip_count`
 *  changes. The counts have not moved, so they are not re-read.
 *
 *  **Driven by `settings_revision`, not by a component effect.** The first
 *  attempt watched the settings store from inside `Library.svelte` and
 *  never re-ran: the panel refetched `/settings` and left the strip alone,
 *  which looked exactly like the daemon being wrong (it was not - it was
 *  already serving the new shape). This is the mechanism `settings.js`
 *  itself uses, and it is one the device has proven. */
export async function reloadStrip() {
  try {
    const strip = await get('strip');
    await Promise.all((strip.albums ?? []).map((album) => decoded(album.artwork)));
    libraryRoot.update((root) => ({ ...root, albums: strip.albums ?? [], strip }));
  } catch (err) {
    console.info('library:', err.message);
  }
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

//: **How many ids one request carries.** The daemon caps a request at 80
//: (`PHOTO_BATCH`); 50 leaves room to raise that cap without changing this.
const PREFETCH_BATCH = 50;

let prefetching = null;

/** Every portrait the grid will want, before it wants them (ADR-0068).
 *
 *  **The grid used to discover them as cards came into view**, twenty at a
 *  time, so a card was always drawn as initials and became a picture
 *  afterwards - and a batch of twenty nobody had opened took 353 ms, because
 *  the daemon asked LMS's plugin for every one of them. With the sweep
 *  answered first the whole library is 145 ms warm, so the panel asks for
 *  all of it and every card is drawn with its picture already.
 *
 *  Asks only for what it lacks, so opening the grid again costs nothing, and
 *  yields between batches so filling the map never holds up a scroll. */
export function prefetchArtistPhotos(ids, size = 200) {
  if (prefetching) return prefetching;
  prefetching = (async () => {
    try {
      let known = {};
      artistPhotos.subscribe((value) => (known = value))();
      const suffix = size === 200 ? '' : `@${size}`;
      const missing = ids.filter((id) => known[`${id}${suffix}`] === undefined);
      for (let at = 0; at < missing.length; at += PREFETCH_BATCH) {
        await loadArtistPhotos(missing.slice(at, at + PREFETCH_BATCH), size);
        await new Promise((settle) => setTimeout(settle, 0));
      }
    } finally {
      prefetching = null;
    }
  })();
  return prefetching;
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

/** Lists the panel has already been given, kept across the library screen
 *  being closed and opened again.
 *
 *  Same reason as `artistPhotos`: the screen is mounted only while it is
 *  open, so anything it holds is thrown away each time. The daemon answers
 *  these from its own cache in milliseconds, but the panel still had to
 *  wait for a round trip and rebuild 917 cards before drawing a grid it had
 *  drawn a moment earlier.
 *
 *  **Shown at once, then refreshed behind.** LMS renumbers every id on a
 *  full rescan (Finding 029 §4), so a remembered list is a head start and
 *  never the last word: what comes back replaces it. */
export const artistList = writable(null);
export const playlistList = writable(null);

async function stale(store, load) {
  let shown = null;
  store.subscribe((value) => (shown = value))();
  const fresh = load().then((value) => {
    store.set(value);
    return value;
  });
  // Nothing remembered: the caller waits, as it always did.
  return shown ?? (await fresh);
}

/** Album artists, from memory first if they are there. */
export const artistsCached = () => stale(artistList, async () => (await loadArtists()).items);

/** The library's playlists, from memory first if they are there. */
export const playlistsCached = () => stale(playlistList, loadPlaylists);
