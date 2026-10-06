// SPDX-License-Identifier: GPL-3.0-or-later
//
// ADR-0118: the shape and tint of every entry in Lyrion's menus, from
// Claude Design's handover (design/source/13f/lyrion-data.js). My Music's
// entries by Lyrion's own ids - the labels are Lyrion's and follow its
// language; the designer's keyword table for every app level; Lyrion's hint
// next; a folder last.

export const T = {
  mint: '#7ed6bc',
  blue: '#9fb4e8',
  coral: '#f2a48f',
  amber: '#e0a758',
  lilac: '#c8a2d8',
  sky: '#8fc4d8',
  slate: '#b0bcc4',
  pink: '#e8a0b4',
  green: '#8fd9a8',
  ink: '#e9eef2',
};

//: My Music's five groups (the handover's §2): their header tint, and the
//: column each takes on the standard screen.
export const MY_MUSIC_GROUPS = [
  { key: 'artists', name: 'Artists', ink: T.blue, column: 0 },
  { key: 'albums', name: 'Albums', ink: T.mint, column: 1 },
  { key: 'category', name: 'By category', ink: T.coral, column: 2 },
  { key: 'tracks', name: 'Tracks', ink: T.green, column: 3 },
  { key: 'more', name: 'More', ink: T.lilac, column: 3 },
];

//: Lyrion's id -> [group, glyph, tint, what it opens to].
export const MY_MUSIC = {
  myMusicArtistsAllArtists: ['artists', 'Person', T.blue, 'artists'],
  myMusicArtistsComposers: ['artists', 'Score', T.lilac, 'artists'],
  myMusicArtistsJazzComposers: ['artists', 'Score', T.coral, 'artists'],
  myMusicArtistsConductors: ['artists', 'Person', T.slate, 'artists'],
  myMusicTopArtists: ['artists', 'Podium', T.amber, 'ranked'],
  myMusicNewArtists: ['artists', 'Spark', T.green, 'artists'],
  myMusicRecentlyPlayedArtists: ['artists', 'Clock', T.sky, 'artists'],
  myMusicAlbums: ['albums', 'Sleeve', T.mint, 'covers'],
  myMusicNewMusic: ['albums', 'Stack', T.coral, 'covers'],
  myMusicRandomAlbums: ['albums', 'Dice', T.pink, 'covers'],
  myMusicPopularAlbums: ['albums', 'Crown', T.amber, 'covers'],
  myMusicRecentlyChangeAlbums: ['albums', 'Refresh', T.sky, 'covers'],
  myMusicAlbumsVariousArtists: ['albums', 'Fan', T.blue, 'covers'],
  myMusicWorks: ['albums', 'Pillar', T.lilac, 'covers'],
  myMusicGenres: ['category', 'Tag', T.coral, 'genres'],
  myMusicYears: ['category', 'Calendar', T.amber, 'years'],
  myMusicMusicFolder: ['category', 'Folder', T.mint, 'folder'],
  myMusicFileSystem: ['category', 'Disk', T.slate, 'folder'],
  myMusicTopTracks: ['tracks', 'Up', T.green, 'tracks'],
  myMusicFlopTracks: ['tracks', 'Down', T.slate, 'tracks'],
  myMusicSearch: ['more', 'Search', T.ink, 'search'],
  opmlselectVirtualLibrary: ['more', 'Layers', T.lilac, 'rows'],
  opmlselectRemoteLibrary: ['more', 'Servers', T.sky, 'rows'],
};

//: An app level's entries by their label (the designer's table, one for
//: every app), then Lyrion's hint, then a folder.
const KEYWORDS = [
  [/search/i, 'Search', T.ink],
  [/purchase/i, 'Bag', T.blue],
  [/favou?rite/i, 'Heart', T.pink],
  [/^my playlists|^playlists/i, 'Lines', T.coral],
  [/playlists/i, 'Lines', T.sky],
  [/bestseller|popular|top /i, 'Crown', T.amber],
  [/new|what's new/i, 'Spark', T.green],
  [/press/i, 'Press', T.slate],
  [/selection|editor|pick/i, 'Star', T.lilac],
  [/genre|mood/i, 'Tag', T.mint],
  [/^home$/i, 'House', T.mint],
  [/album/i, 'Sleeve', T.mint],
  [/artist/i, 'Person', T.blue],
  [/podcast/i, 'Mic', T.lilac],
  [/alarm/i, 'Clock', T.amber],
  [/musical/i, 'Note', T.coral],
  [/natural/i, 'Leaf', T.green],
  [/effect/i, 'Spark', T.sky],
];
const HINTS = {
  genre: ['Tag', T.coral],
  year: ['Calendar', T.amber],
  folder: ['Folder', T.mint],
  artist: ['Person', T.blue],
  album: ['Sleeve', T.mint],
  work: ['Pillar', T.lilac],
  app: ['Dots', T.lilac],
};

export function shapeFor(label, hint) {
  for (const [pattern, glyph, tint] of KEYWORDS) if (pattern.test(label || '')) return [glyph, tint];
  if (hint && HINTS[hint]) return HINTS[hint];
  return ['Folder', T.sky];
}

/** Initials for an artist with no picture (the handover's rows). */
export function initials(name) {
  return (name || '')
    .replace(/[^\p{L}\p{N} ]/gu, '')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase();
}

/** The rail's letter for a label: A-Z with accents folded, # otherwise. */
export function railLetter(label) {
  const first = (label || '').trim()[0];
  if (!first) return '#';
  const base = first.normalize('NFKD').replace(/[̀-ͯ]/g, '').toUpperCase();
  return /^[A-Z]$/.test(base) ? base : ({ Ł: 'L', Ø: 'O', Æ: 'A', Œ: 'O', Đ: 'D', Ð: 'D' })[first.toUpperCase()] ?? '#';
}

//: "Sogno (189)" on Top Tracks (the handover's note 5).
export function playCount(label) {
  const m = /^(.*\S)\s*\((\d+)\)$/.exec(label || '');
  return m ? { label: m[1], plays: Number(m[2]) } : { label, plays: null };
}

/** "Genre: Metal" -> ["Genre", "Metal"]; a line with no colon -> [line, '']. */
export function fact(text) {
  const at = (text || '').indexOf(': ');
  return at > 0 ? [text.slice(0, at), text.slice(at + 2)] : [text || '', ''];
}

/** A cover, not a plugin's stock icon (those are served from /html/). */
export const hasCover = (r) => !!r?.image && !/\/html\//.test(r.image);

/** **The shape a level takes**, from its entries and what opened them (the
 *  handover's "Interactions": covers -> grid, play -> leaf rows, folder ->
 *  rows or cards, search -> field). LyrionLevel draws it; the bar's head
 *  column asks it too, for Play all. */
export function levelLayout(page, ctx = {}, { loading = false, failed = null } = {}) {
  if (failed) return 'unreachable';
  if (loading || !page) return 'loading';
  if (page.node === 'myMusic') return 'groups';
  if (ctx.apps) return 'apps';
  const nonText = (page.items ?? []).filter((r) => r.kind !== 'text');
  const share = (test) => (nonText.length ? nonText.filter(test).length / nonText.length : 0);
  if (!nonText.length) return ctx.favourites ? 'favEmpty' : 'nothing';
  if (ctx.appTop && nonText.length === 1 && !nonText[0].label) return 'notSignedIn';
  if (ctx.favourites) return 'favourites';
  if (ctx.appTop) return 'cards';
  if (share((r) => r.hint === 'year') >= 0.6) return 'years';
  if (share((r) => (r.kind === 'container' || r.kind === 'folder') && hasCover(r)) >= 0.6) return 'covers';
  if (share((r) => r.hint === 'genre') >= 0.6) return 'genres';
  if (share((r) => r.hint === 'artist') >= 0.6) return ctx.opens === 'ranked' ? 'ranked' : 'artists';
  if (share((r) => r.kind === 'play') >= 0.6) {
    return ctx.from && hasCover(ctx.from) && ctx.from.kind === 'container' ? 'album' : 'tracks';
  }
  if (nonText.some((r) => r.kind === 'play')) return 'folder';
  return 'cards';
}
