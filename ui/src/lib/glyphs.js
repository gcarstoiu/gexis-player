// SPDX-License-Identifier: GPL-3.0-or-later
//
// ADR-0118: the glyphs of Lyrion's menus, from Claude Design's handover
// (design/source/13f/glyphs.js, the source of truth for their geometry):
// the ten of Radio (design/screens.md §8) and 36 more, each drawn in CSS in
// a 26 px box in one ink - no icon font, no SVG. Copied verbatim below the
// helpers; Glyph.svelte draws one.
//
// A part is [left, top, width, height, style]; 'I' in a style is the ink.
const GROUND = '#101a21';
function b(l, t, w, h, r, x) { return [l, t, w, h, Object.assign({ borderRadius: r || 0, background: 'I' }, x || {})]; }
function o(l, t, w, h, r, hide, x, bw) {
  var s = { borderRadius: r || 0, border: (bw || 2.5) + 'px solid I', boxSizing: 'border-box' };
  (hide || []).forEach(function (k) { s['border' + k[0].toUpperCase() + k.slice(1) + 'Color'] = 'transparent'; });
  return [l, t, w, h, Object.assign(s, x || {})];
}
function cp(l, t, w, h, poly, x) { return [l, t, w, h, Object.assign({ background: 'I', clipPath: poly }, x || {})]; }
const R = function (d) { return { transform: 'rotate(' + d + 'deg)' }; };
const G = { background: GROUND };

const S = {
  // --- Radio, §8 (unchanged) ---
  Arcs: [b(10.5, 19, 5, 5, '50%'), o(7, 15.5, 12, 12, '50%', ['bottom']), o(2, 10.5, 22, 22, '50%', ['bottom'])],
  Star: [cp(2, 3, 22, 21, 'polygon(50% 0,61% 35%,98% 35%,68% 57%,79% 92%,50% 70%,21% 92%,32% 57%,2% 35%,39% 35%)')],
  Pin: [b(4, 2.5, 18, 18, '50% 50% 50% 0', R(-45)), b(10, 8.5, 6, 6, '50%', G), b(11.5, 18, 3, 6)],
  Note: [b(3, 14, 10, 10, '50%'), b(10.5, 2, 2.5, 18), b(10.5, 2, 9, 2.5)],
  Ball: [o(2, 2, 22, 22, '50%'), o(8.5, 2, 9, 22, '50%')],
  Lines: [b(3, 5, 20, 2.5, 2), b(3, 11.5, 20, 2.5, 2), b(3, 18, 13, 2.5, 2)],
  Mic: [b(9, 2, 8, 13, 999), o(4, 6, 18, 18, '50%', ['top', 'left', 'right']), b(11.5, 19, 3, 5)],
  Globe: [o(2, 2, 22, 22, '50%'), b(2, 11.75, 22, 2.5), o(7.5, 2, 11, 22, '50%')],
  Speech: [b(2, 3, 22, 16, 5), cp(6, 18, 7, 7, 'polygon(0 0,100% 0,0 100%)')],
  Rss: [b(3, 18, 5, 5, '50%'), o(-2.5, 12.5, 16, 16, '50%', ['left', 'bottom']), o(-7.5, 7.5, 26, 26, '50%', ['left', 'bottom'])],
  // --- 13f ---
  Person: [b(8.5, 2, 9, 9, '50%'), b(3, 14, 20, 10, '10px 10px 3px 3px')],
  Score: [b(2, 6, 22, 2, 1, { opacity: 0.55 }), b(2, 12, 22, 2, 1, { opacity: 0.55 }), b(2, 18, 22, 2, 1, { opacity: 0.55 }), b(7, 14, 10, 8, '50%', R(-20)), b(14.5, 2, 2.5, 16)],
  Podium: [b(2, 13, 6.5, 11, 2), b(9.75, 4, 6.5, 20, 2), b(17.5, 9, 6.5, 15, 2)],
  Spark: [cp(2, 2, 22, 22, 'polygon(50% 0,61% 39%,100% 50%,61% 61%,50% 100%,39% 61%,0 50%,39% 39%)')],
  Clock: [o(2, 2, 22, 22, '50%'), b(11.75, 6, 2.5, 8, 1), b(11.75, 11.75, 7, 2.5, 1)],
  Sleeve: [o(2, 2, 22, 22, 4), o(7, 7, 12, 12, '50%'), b(11.5, 11.5, 3, 3, '50%')],
  Stack: [o(2, 10, 14, 14, 3, null, { opacity: 0.45 }), o(6, 6, 14, 14, 3, null, Object.assign({ opacity: 0.7 }, G)), b(10, 2, 14, 14, 3)],
  Dice: [o(2, 2, 22, 22, 6), b(6.5, 6.5, 4, 4, '50%'), b(11, 11, 4, 4, '50%'), b(15.5, 15.5, 4, 4, '50%')],
  Fan: [o(8, 3, 10, 20, 3, null, Object.assign({ transform: 'rotate(-22deg)', transformOrigin: '50% 100%', opacity: 0.5 }, G)), o(8, 3, 10, 20, 3, null, Object.assign({ transform: 'rotate(22deg)', transformOrigin: '50% 100%', opacity: 0.75 }, G)), b(8, 3, 10, 20, 3)],
  Pillar: [b(2, 2, 22, 3.5, 1), b(4, 7.5, 3.5, 12, 1), b(11.25, 7.5, 3.5, 12, 1), b(18.5, 7.5, 3.5, 12, 1), b(2, 21, 22, 3.5, 1)],
  Refresh: [o(3, 4, 20, 20, '50%', ['top']), cp(13, 0, 9, 9, 'polygon(0 0,100% 50%,0 100%)')],
  Crown: [cp(2, 4, 22, 18, 'polygon(0 18%,26% 52%,50% 0,74% 52%,100% 18%,90% 100%,10% 100%)')],
  Up: [b(1, 13, 21, 3, 2, R(-42)), cp(13, 2, 11, 11, 'polygon(0 0,100% 0,100% 100%)')],
  Down: [b(1, 10, 21, 3, 2, R(42)), cp(13, 13, 11, 11, 'polygon(100% 0,100% 100%,0 100%)')],
  Tag: [cp(2, 2, 22, 22, 'polygon(0 0,58% 0,100% 42%,42% 100%,0 58%)'), b(5.5, 5.5, 5, 5, '50%', G)],
  Calendar: [o(2, 4, 22, 20, 4), b(2, 4, 22, 7, '4px 4px 0 0'), b(7, 1, 2.5, 6, 1), b(16.5, 1, 2.5, 6, 1)],
  Folder: [b(2, 4, 10, 5, '3px 3px 0 0'), b(2, 7, 22, 16, 3)],
  Disk: [o(2, 6, 22, 14, 4), b(17, 11.5, 3, 3, '50%'), b(6, 12, 7, 2, 1)],
  Search: [o(2, 2, 16, 16, '50%', null, null, 3), b(14, 17.5, 11, 3.5, 2, R(45))],
  Layers: [cp(2, 10, 22, 13, 'polygon(50% 0,100% 50%,50% 100%,0 50%)', { opacity: 0.5 }), cp(2, 3, 22, 13, 'polygon(50% 0,100% 50%,50% 100%,0 50%)')],
  Servers: [o(3, 3, 20, 8, 3), o(3, 15, 20, 8, 3), b(6.5, 6, 2.5, 2.5, '50%'), b(6.5, 18, 2.5, 2.5, '50%')],
  Heart: [b(3, 4, 12, 12, '50%'), b(11, 4, 12, 12, '50%'), b(6.6, 8.6, 12.8, 12.8, 2, R(45))],
  Dots: [3, 10.5, 18].reduce(function (a, y) { return a.concat([3, 10.5, 18].map(function (x) { return b(x, y, 5, 5, '50%'); })); }, []),
  Shelf: [o(9, 4, 17, 17, '50%'), b(15.5, 10.5, 4, 4, '50%'), b(0, 5, 15, 15, 3)],
  Bag: [b(3, 9, 20, 15, 3), o(8, 2, 10, 11, '5px 5px 0 0', ['bottom'])],
  Press: [o(2, 3, 22, 20, 3), b(6, 7.5, 7, 6, 1), b(15, 7.5, 5, 2, 1), b(15, 11.5, 5, 2, 1), b(6, 16.5, 14, 2, 1)],
  Video: [o(2, 5, 22, 16, 4), cp(10, 9, 8, 8, 'polygon(0 0,100% 50%,0 100%)')],
  Link: [o(1, 9, 14, 8, 4), o(11, 9, 14, 8, 4)],
  House: [cp(2, 2, 22, 22, 'polygon(50% 0,100% 45%,88% 45%,88% 100%,12% 100%,12% 45%,0 45%)')],
  Leaf: [b(4, 4, 18, 18, '0 100% 0 100%')],
  Wave: [b(2, 10, 3, 6, 2), b(7, 6, 3, 14, 2), b(12, 2, 3, 22, 2), b(17, 7, 3, 12, 2), b(22, 10, 3, 6, 2)],
  Phone: [o(7, 1, 12, 24, 3), b(11, 20, 4, 2, 1)],
  Cloud: [b(3, 12, 20, 10, 5), b(7, 6, 11, 11, '50%')],
  Disc: [o(2, 2, 22, 22, '50%'), b(10, 10, 6, 6, '50%')]
};


export const SHAPES = S;

/** A tint as rgba at `a` - the disc's 14 % ground and 30 % border. */
export function rgba(hex, a) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`;
}
