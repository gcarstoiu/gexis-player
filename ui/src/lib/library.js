// SPDX-License-Identifier: GPL-3.0-or-later
//
// Library reads (ADR-0038 §5): the core runs LMS's typed queries and
// answers with the fields a screen draws. The panel never talks to LMS,
// except to load artwork, whose URLs point straight at it (ADR-0020).

async function get(path) {
  const response = await fetch(`/library/${path}`);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error ?? `HTTP ${response.status}`);
  return body;
}

/** `{albums, artists, playlists}` for the root's cards. */
export const libraryCounts = () => get('counts');

/** The ten most recently added albums, for the New Music strip. */
export const newMusic = () => get('new');
