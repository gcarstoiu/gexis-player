// SPDX-License-Identifier: GPL-3.0-or-later
//
// ADR-0118: Lyrion's own menus, behind Extended navigation. As with Radio
// (ADR-0038 §5), the panel holds handles the core issued and never a Lyrion
// command: it asks for a list by handle, and for an item to be played,
// added or played next by handle.
import { writable } from 'svelte/store';

async function call(path, init) {
  const response = await fetch(path, init);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error ?? `HTTP ${response.status}`);
  return body;
}

const post = (path, body) =>
  call(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

/** The tiles Extended navigation adds: `[{key, id, label, handle}]`, empty
 *  while it is off. Kept between openings of Home, as the library's root is,
 *  so the cards do not arrive after the screen. */
export const menuTiles = writable([]);

export async function loadMenuTiles() {
  try {
    const body = await call('/menus');
    menuTiles.set(body.on ? body.tiles ?? [] : []);
  } catch {
    menuTiles.set([]);
  }
}

/** One page of a list: `{title, count, start, items}`. */
export const browseMenu = (handle, start = 0, count = 100) =>
  call(`/menus/browse?at=${encodeURIComponent(handle)}&start=${start}&count=${count}`);

/** `play`, `add` or `next`, for an item Lyrion said can. */
export const menuAct = (handle, action) => post('/menus/act', { handle, action });

/** A search item, answered with typed text: its results, with their own
 *  `handle` to page and come back to. */
export const menuSearch = (handle, text) => post('/menus/search', { handle, text });

//: **Each list remembers list or tiles, on this device** (ADR-0118 I). Keyed
//: by where the list is - the labels that lead to it - since handles are
//: new each time.
const VIEW_KEY = 'gexis.menus.view';

function views() {
  try {
    return JSON.parse(localStorage.getItem(VIEW_KEY) ?? '{}') ?? {};
  } catch {
    return {};
  }
}

/** The view a list was last left in, or its default: tiles for a list of
 *  albums and playlists **with their covers**, a list otherwise. Genres can
 *  be played whole too, and as tiles they were grey shapes (2026-10-05). */
export function viewFor(where, items) {
  const kept = views()[where];
  if (kept === 'list' || kept === 'tiles') return kept;
  const covered = items.filter((i) => i.kind === 'container' && i.image).length;
  return items.length && covered / items.length >= 0.6 ? 'tiles' : 'list';
}

export function keepView(where, view) {
  try {
    localStorage.setItem(VIEW_KEY, JSON.stringify({ ...views(), [where]: view }));
  } catch {
    // A panel without storage starts each list in its default view.
  }
}
