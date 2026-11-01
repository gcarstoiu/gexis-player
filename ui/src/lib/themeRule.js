// SPDX-License-Identifier: GPL-3.0-or-later
//: **Themes** (ADR-0171): the design's own rule, from
//: design/source/28/build.js, which made each theme's token set from
//: today's values. A colour is recoloured by its family (the ink, each
//: accent, the grounds, the weave); on a light theme the ink's alphas are
//: raised and black shadows lightened; a corner of 4 px or more is scaled
//: by the theme's factor. ui/scripts/themes.mjs writes styles/themes.css
//: with it, and checks the result against design/themes/; `tone()` gives a
//: colour a script hands to a style the same treatment.

//: The five themes George kept (2026-10-28), as design/source/28/themes.js
//: has them (themes.mjs checks that they are the same). Deep Teal, today's,
//: is the absence of one.
export const THEMES = [
  { id: 'bauhaus', name: 'Bauhaus', light: true, base: '#f2efe8', panel: '#fbfaf6', well: '#e4e0d6', desk: '#dcd7cc',
    weaveA: '#e9e0cb', weaveB: '#d8ceb7', weaveAngle: 90, ink: '#141414', onAccent: '#ffffff', lms: '#1a47c4',
    artist: '#d1261c', spotify: '#0a6b36', bluetooth: '#5f35b3', warn: '#964800', display: '#725700',
    veil: [0.88, 0.97], radius: 0.75, mono: "'Space Mono'", monoScale: 0.96 },
  { id: 'sage', name: 'Sage', light: true, base: '#ece8dc', panel: '#f6f3ea', well: '#dcd7c8', desk: '#d3cdbd',
    weaveA: '#dfe0cc', weaveB: '#cbcdb4', weaveAngle: 60, ink: '#1b241e', onAccent: '#ffffff', lms: '#245a3d',
    artist: '#a8401f', spotify: '#4d5f12', bluetooth: '#2f5578', warn: '#8a4a00', display: '#6b3d78',
    veil: [0.88, 0.97], radius: 1.1, mono: "'Martian Mono'", monoScale: 0.9 },
  { id: 'velvet', name: 'Velvet', light: false, base: '#150a0b', panel: '#21110f', well: '#251412', desk: '#0b0506',
    weaveA: '#4a1c1f', weaveB: '#2a0f12', weaveAngle: 38, ink: '#f2e0d2', onAccent: '#1a0b0b', lms: '#d9b45c',
    artist: '#f2939a', spotify: '#a3d18e', bluetooth: '#a9b9f2', warn: '#ff9a55', display: '#c9a3ea',
    veil: [0.8, 0.96], radius: 1, mono: "'Red Hat Mono'", monoScale: 1 },
  { id: 'ink', name: 'Ink', light: false, base: '#090e1d', panel: '#111a30', well: '#131d35', desk: '#05080f',
    weaveA: '#1d2d5c', weaveB: '#111b3a', weaveAngle: 150, ink: '#e6ecf7', onAccent: '#0a1020', lms: '#7fc8ff',
    artist: '#ff8fa8', spotify: '#8fe0a0', bluetooth: '#b9a3ff', warn: '#ffc24d', display: '#f0b37a',
    veil: [0.8, 0.96], radius: 1, mono: "'JetBrains Mono'", monoScale: 0.95 },
  { id: 'gauge', name: 'Gauge', light: false, base: '#111315', panel: '#1b1e21', well: '#1f2326', desk: '#08090a',
    weaveA: '#2c3136', weaveB: '#1a1d20', weaveAngle: 90, ink: '#e7e9e4', onAccent: '#111315', lms: '#3fd3e6',
    artist: '#ffd21f', spotify: '#7ee06f', bluetooth: '#f27ad9', warn: '#ff7a2e', display: '#b3a4ff',
    veil: [0.8, 0.96], radius: 0.45, mono: "'Chivo Mono'", monoScale: 1 },
];

//: The setting's value (a name, as Settings shows it) to the theme, or
//: null for Deep Teal and anything unknown.
export function themeNamed(name) {
  return THEMES.find((t) => t.name === name) ?? null;
}

const hex2 = (h) => {
  h = h.replace('#', '');
  if (h.length === 3) h = h.split('').map((c) => c + c).join('');
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
};
const toHex = (c) => '#' + c.map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('');
const mix = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);
const lum = (c) => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];

const FAMILY = {
  '233,238,242': 'ink', '238,243,247': 'ink', '244,248,251': 'ink',
  '126,214,188': 'lms', '168,229,211': 'lmsHi', '242,164,143': 'artist', '248,196,180': 'artistHi',
  '159,180,232': 'bluetooth', '143,217,168': 'spotify', '224,167,88': 'warn', '200,162,216': 'display',
  '63,90,109': 'weaveA', '46,68,83': 'weaveB', '55,80,95': 'weaveM', '13,21,28': 'ground', '13,21,27': 'ground',
};

//: build.js's makeMap: today's [r, g, b] and alpha to the theme's, or null
//: for a colour the theme leaves as it is.
export function colourMap(T) {
  const C = {};
  for (const k of ['ink', 'lms', 'artist', 'bluetooth', 'spotify', 'warn', 'display', 'weaveA', 'weaveB', 'base', 'panel', 'well', 'desk', 'onAccent']) C[k] = hex2(T[k]);
  C.lmsHi = mix(C.lms, T.light ? [0, 0, 0] : [255, 255, 255], 0.3);
  C.artistHi = mix(C.artist, T.light ? [0, 0, 0] : [255, 255, 255], 0.3);
  C.weaveM = mix(C.weaveA, C.weaveB, 0.5);
  const textA = (a) => (T.light ? (a >= 0.45 ? Math.min(1, 0.35 + 0.65 * a) : a * 1.1) : a);
  return (rgb, a, isHex) => {
    const k = rgb.join(',');
    if (isHex) {
      const h = toHex(rgb);
      if (h === '#0d151c') return [C.onAccent, 1];
      if (h === '#101a21') return [C.base, 1];
      if (h === '#0c1014') return [C.desk, 1];
      if (h === '#16232c' || h === '#0b1218') return [C.panel, 1];
      if (h === '#17242d') return [C.well, 1];
    }
    if (FAMILY[k]) {
      const f = FAMILY[k];
      if (f === 'ground') return [C.panel, a];
      return [C[f], (f === 'ink' || f === 'artist' || f === 'lms') && a < 1 ? +textA(a).toFixed(3) : a];
    }
    if (k === '255,255,255' && a < 1) return [C.ink, +(T.light ? a * 1.1 : a).toFixed(3)];
    if (k === '0,0,0' && a < 1) return [rgb, +(T.light ? a * 0.35 : a).toFixed(3)];
    if (Math.max(...rgb) < 75 && rgb[2] >= rgb[0] && rgb[2] > 8) return [lum(rgb) <= lum([16, 26, 33]) ? C.base : C.panel, a];
    return null;
  };
}

const fmt = (c, a) => `rgba(${c.map(Math.round).join(',')},${a})`;
const RGBA = /rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)/g;
const HEX = /#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-fA-F\w])/g;

//: build.js's colour substitutions over a piece of CSS (or a script's
//: string): rgb()/rgba(), hex, and quoted 'r, g, b' triplets.
export function recolour(text, T) {
  const map = colourMap(T);
  text = text.replace(RGBA, (m, r, g, b, a) => {
    const res = map([+r, +g, +b], a === undefined ? 1 : +a, false);
    return res ? (res[1] === 1 && a === undefined ? toHex(res[0]) : fmt(res[0], res[1])) : m;
  });
  text = text.replace(HEX, (m, h) => {
    const res = map(hex2(h), 1, true);
    return res ? (res[1] === 1 ? toHex(res[0]) : fmt(res[0], res[1])) : m;
  });
  return text.replace(/(['"])(\d{1,3}),\s?(\d{1,3}),\s?(\d{1,3})\1/g, (m, q, r, g, b) => {
    const res = map([+r, +g, +b], 1, false);
    return res ? q + res[0].map(Math.round).join(',') + q : m;
  });
}

//: A colour a script hands to a style - a hex, an rgba() or an 'r, g, b'
//: triplet - as the theme has it. Deep Teal (no theme) leaves it alone.
export function tone(colour, T) {
  if (!T || typeof colour !== 'string') return colour;
  if (/^\d{1,3},\s?\d{1,3},\s?\d{1,3}$/.test(colour)) return recolour(`'${colour}'`, T).slice(1, -1);
  return recolour(colour, T);
}

//: A corner, as build.js scales one: from 4 px by the theme's factor, never
//: under 2 px; a pill (900 px and over) stays round.
export function corner(px, T) {
  return px < 4 || px >= 900 ? px : Math.max(2, Math.round(px * T.radius));
}
