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
export async function libraryAction(kind, id, action = 'play') {
  const response = await fetch('/library/action', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kind, id, action }),
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
