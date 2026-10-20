// SPDX-License-Identifier: GPL-3.0-or-later
// The four SVG weather icon sets (ADR-0154): Modern, Futuristic,
// Photographic and Atmospheric, drawn in a 100x100 box. Ported from the
// previews George chose from on 2026-10-19; Solid, Duotone and Neon stay
// the design's DOM shapes in WeatherIcon.svelte.
//
// Every drawing is a string of SVG. `c` is the drawing's context: `id(name)`
// makes an id unique to this icon (gradients and filters are looked up by
// id, and many icons share a page), `phase` and `left` place the moon's lit
// part (ADR-0153).

import { litPath } from './moon.js';
import sunPhoto from '../assets/weather/sun-sdo.webp';
import moonPhoto from '../assets/weather/moon-lro.webp';

/** One cloud outline, its base on y = 74. */
const CLOUD = 'M30 74 H74 A12.5 12.5 0 0 0 76.5 49.3 A19 19 0 0 0 40.5 43.5 A15.5 15.5 0 0 0 30 74 Z';

const moonD = (c, r, x) => litPath(c.phase, r, x, x, c.left);

/* ---- Modern: frosted glass over colour ------------------------------------ */
const modern = {
  sun(c, small) {
    const g = c.id('sun'), r = small ? 15 : 21, x = small ? 36 : 50;
    return `<defs><linearGradient id="${g}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffd25c"/><stop offset="1" stop-color="#ff7a3d"/></linearGradient></defs>
      <circle cx="${x}" cy="${x}" r="${r}" fill="url(#${g})" style="filter:drop-shadow(0 6px 10px rgba(255,122,61,.45))"/>
      <circle class="wxs-pulse" cx="${x}" cy="${x}" r="${r + 7}" fill="none" stroke="#ffb04a" stroke-opacity=".35" stroke-width="2"/>`;
  },
  moon(c, small) {
    const g = c.id('moon'), r = small ? 15 : 20, x = small ? 36 : 50;
    return `<defs><linearGradient id="${g}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#e9e4ff"/><stop offset="1" stop-color="#9d8cff"/></linearGradient></defs>
      <circle cx="${x}" cy="${x}" r="${r}" fill="#ffffff" opacity=".09"/>
      <path d="${moonD(c, r, x)}" fill="url(#${g})" style="filter:drop-shadow(0 6px 10px rgba(130,110,255,.45))"/>
      <circle class="wxs-pulse" cx="${x}" cy="${x}" r="${r + 7}" fill="none" stroke="#b5a8ff" stroke-opacity=".3" stroke-width="2"/>`;
  },
  cloud(c, { dark = false, t = '' } = {}) {
    const g = c.id('cloud');
    return `<g transform="${t}"><defs><linearGradient id="${g}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="${dark ? 0.55 : 0.85}"/><stop offset="1" stop-color="${dark ? '#8796ad' : '#dfe8f4'}" stop-opacity="${dark ? 0.75 : 0.6}"/></linearGradient></defs>
      <g class="wxs-drift"><path d="${CLOUD}" fill="url(#${g})" stroke="#fff" stroke-opacity=".75" stroke-width="1.4" style="filter:drop-shadow(0 6px 10px rgba(10,20,40,.35))"/></g></g>`;
  },
  rain(c, n) {
    const xs = n === 2 ? [43, 61] : [37, 52, 67];
    return xs.map((x, i) => `<g class="wxs-fall" style="animation-delay:${i * 0.3}s"><path d="M${x} 81 q-3.5 5 0 7.6 q3.5 -2.6 0 -7.6Z" fill="#53a8ff"/></g>`).join('');
  },
  snow() {
    return [37, 52, 67].map((x, i) => `<g class="wxs-fall-slow" style="animation-delay:${i * 0.7}s"><circle cx="${x}" cy="86" r="3.4" fill="#fff" opacity=".95"/></g>`).join('');
  },
  bolt() {
    return `<path class="wxs-flash" d="M54 66 L44 84 H52 L48 97 L62 78 H54 L58 66 Z" fill="#ffc94a" style="filter:drop-shadow(0 4px 8px rgba(255,170,40,.6))"/>`;
  },
  fog() {
    return [77, 85, 93].map((y, i) => `<g class="wxs-drift" style="animation-delay:${-i * 1.3}s"><rect x="${24 + i * 6}" y="${y}" width="${52 - i * 10}" height="4" rx="2" fill="#fff" opacity="${0.75 - i * 0.18}"/></g>`).join('');
  },
};

/* ---- Futuristic: a heads-up display ------------------------------------------ */
const hud = (g) => `<linearGradient id="${g}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#00f0ff"/><stop offset="1" stop-color="#ff3cac"/></linearGradient>`;
const futuristic = {
  sun(c, small) {
    const g = c.id('sun'), r = small ? 13 : 17, x = small ? 36 : 50;
    return `<defs>${hud(g)}</defs>
      <circle cx="${x}" cy="${x}" r="${r}" fill="none" stroke="url(#${g})" stroke-width="2"/>
      <circle class="wxs-pulse" cx="${x}" cy="${x}" r="${r * 0.38}" fill="#00f0ff"/>
      <circle class="wxs-spin" cx="${x}" cy="${x}" r="${r + 7}" fill="none" stroke="#00f0ff" stroke-width="2.4" stroke-dasharray="6 5"/>
      <circle class="wxs-spin-r" cx="${x}" cy="${x}" r="${r + 13}" fill="none" stroke="#ff3cac" stroke-width="1.2" stroke-dasharray="18 9 2 9" opacity=".8"/>`;
  },
  moon(c, small) {
    const g = c.id('moon'), r = small ? 14 : 19, x = small ? 36 : 50, d = moonD(c, r, x);
    const hatch = Array.from({ length: 14 }, (_, i) => `<line x1="${x - r}" y1="${x - r + i * (2 * r / 13)}" x2="${x + r}" y2="${x - r + i * (2 * r / 13)}"/>`).join('');
    return `<defs>${hud(g)}<clipPath id="${g}c"><path d="${d}"/></clipPath></defs>
      <circle cx="${x}" cy="${x}" r="${r}" fill="none" stroke="#00f0ff" stroke-opacity=".35" stroke-width="1.2" stroke-dasharray="2 3"/>
      <g class="wxs-pulse" clip-path="url(#${g}c)" stroke="#00f0ff" stroke-width="1.3">${hatch}</g>
      <path d="${d}" fill="none" stroke="url(#${g})" stroke-width="2"/>
      <circle class="wxs-spin" cx="${x}" cy="${x}" r="${r + 9}" fill="none" stroke="#ff3cac" stroke-width="1.2" stroke-dasharray="14 10" opacity=".8"/>`;
  },
  cloud(c, { dark = false, t = '' } = {}) {
    const g = c.id('cloud');
    const scan = Array.from({ length: 9 }, (_, i) => `<line x1="20" x2="90" y1="${44 + i * 3.6}" y2="${44 + i * 3.6}"/>`).join('');
    return `<g transform="${t}"><defs>${hud(g)}<clipPath id="${g}c"><path d="${CLOUD}"/></clipPath></defs>
      <g clip-path="url(#${g}c)" stroke="${dark ? '#ff3cac' : '#00f0ff'}" stroke-opacity=".28" stroke-width="1">${scan}</g>
      <g class="wxs-glitch"><path d="${CLOUD}" fill="none" stroke="url(#${g})" stroke-width="2"/></g>
      <circle cx="30" cy="74" r="1.6" fill="#00f0ff"/><circle cx="74" cy="74" r="1.6" fill="#ff3cac"/></g>`;
  },
  rain(c, n) {
    const xs = n === 2 ? [43, 61] : [37, 52, 67];
    return xs.map((x, i) => `<g class="wxs-fall" style="animation-delay:${i * 0.25}s"><path d="M${x} 79 v3 M${x} 85 v3 M${x} 91 v2" stroke="#00f0ff" stroke-width="1.8"/></g>`).join('');
  },
  snow() {
    return [37, 52, 67].map((x, i) => `<g class="wxs-fall-slow" style="animation-delay:${i * 0.7}s"><path transform="translate(${x} 86)" d="M0 -3.6 L3.1 -1.8 L3.1 1.8 L0 3.6 L-3.1 1.8 L-3.1 -1.8 Z" fill="none" stroke="#e7fbff" stroke-width="1.3"/></g>`).join('');
  },
  bolt() {
    return `<path class="wxs-flash" d="M55 66 L45 83 H53 L48 97 L62 78 H54 L59 66 Z" fill="none" stroke="#ff3cac" stroke-width="2" stroke-linejoin="round" style="filter:drop-shadow(0 0 4px #ff3cac)"/>`;
  },
  fog() {
    return [77, 84, 91].map((y, i) => `<g class="wxs-slide" style="animation-delay:${-i * 1.6}s"><line x1="${22 + i * 5}" x2="${78 - i * 5}" y1="${y}" y2="${y}" stroke="${i % 2 ? '#ff3cac' : '#00f0ff'}" stroke-width="1.6" stroke-dasharray="7 4"/></g>`).join('');
  },
};

/* ---- Photographic and Atmospheric: shared lit clouds, rain, snow, lightning, fog */
const PUFFS = [[34, 62, 13], [50, 52, 17], [66, 57, 14], [77, 66, 10], [43, 67, 11], [60, 68, 11], [28, 70, 8]];
const PUFF_BODY = PUFFS.map(([x, y, r]) => `<circle cx="${x}" cy="${y}" r="${r}"/>`).join('') + '<rect x="27" y="62" width="54" height="13" rx="6.5"/>';

/** A cloud of puffs, its edge roughened by fractal noise and lit from the
 * upper left by a lighting model; darker underneath. */
function litCloud(c, { dark = false, t = '', seed = 2 } = {}) {
  const g = c.id('cloud');
  const base = dark ? '#6f7b8a' : '#e9eef4', light = dark ? '#c7cfd9' : '#ffffff', shade = dark ? '#3c4552' : '#9eacbb';
  return `<g transform="${t}"><defs>
    <filter id="${g}" x="-30%" y="-30%" width="160%" height="160%" color-interpolation-filters="sRGB">
      <feTurbulence type="fractalNoise" baseFrequency="0.045" numOctaves="3" seed="${seed}" result="noise"/>
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="7" xChannelSelector="R" yChannelSelector="G" result="fluff"/>
      <feGaussianBlur in="fluff" stdDeviation="1.4" result="soft"/>
      <feGaussianBlur in="fluff" stdDeviation="4.5" result="round"/>
      <feComposite in="noise" in2="round" operator="arithmetic" k1="0.3" k2="0" k3="0.85" k4="0" result="bump"/>
      <feDiffuseLighting in="bump" surfaceScale="3.2" diffuseConstant="1.1" lighting-color="${light}" result="lit"><feDistantLight azimuth="245" elevation="52"/></feDiffuseLighting>
      <feFlood flood-color="${shade}" result="sh"/>
      <feBlend in="lit" in2="sh" mode="screen" result="tone"/>
      <feComposite in="tone" in2="soft" operator="in"/>
    </filter>
    <linearGradient id="${g}s" gradientUnits="userSpaceOnUse" x1="0" y1="40" x2="0" y2="78"><stop offset=".45" stop-color="#0a1420" stop-opacity="0"/><stop offset="1" stop-color="#0a1420" stop-opacity="${dark ? 0.5 : 0.3}"/></linearGradient>
    <mask id="${g}m"><g filter="url(#${g})" fill="#fff">${PUFF_BODY}</g></mask></defs>
    <g class="wxs-drift"><g filter="url(#${g})" fill="${base}">${PUFF_BODY}</g>
    <rect x="10" y="30" width="85" height="55" fill="url(#${g}s)" mask="url(#${g}m)"/></g></g>`;
}
const nature = {
  rain(c, n) {
    const g = c.id('rain'), xs = n === 2 ? [44, 62] : [38, 53, 68];
    return `<defs><linearGradient id="${g}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#cfe9ff" stop-opacity="0"/><stop offset="1" stop-color="#cfe9ff" stop-opacity=".95"/></linearGradient></defs>`
      + xs.map((x, i) => `<g class="wxs-streak" style="animation-delay:${i * 0.27}s"><line x1="${x}" y1="80" x2="${x - 3}" y2="94" stroke="url(#${g})" stroke-width="1.8" stroke-linecap="round"/></g>`).join('');
  },
  snow() {
    const crystal = (x, y, s) => {
      const arm = `<path d="M0 0 V-${s} M0 -${s * 0.55} l-${s * 0.3} -${s * 0.25} M0 -${s * 0.55} l${s * 0.3} -${s * 0.25}"/>`;
      return `<g transform="translate(${x} ${y})" stroke="#f6fbff" stroke-width="1.1" stroke-linecap="round" style="filter:drop-shadow(0 0 1.5px rgba(220,240,255,.9))">${[0, 60, 120, 180, 240, 300].map((a) => `<g transform="rotate(${a})">${arm}</g>`).join('')}</g>`;
    };
    return [[38, 86, 5], [54, 90, 4], [68, 85, 5.5]].map(([x, y, s], i) => `<g class="wxs-fall-slow" style="animation-delay:${i * 0.8}s">${crystal(x, y, s)}</g>`).join('');
  },
  bolt() {
    const d = 'M56 70 L51 79 L54 80 L47 91 L50 92 L45 100 M51 79 L45 84 M54 80 L60 87';
    return `<g class="wxs-strike"><path d="${d}" fill="none" stroke="#b9a8ff" stroke-width="5" stroke-linejoin="round" opacity=".55" style="filter:blur(2px)"/><path d="${d}" fill="none" stroke="#ffffff" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/></g>`;
  },
  fog(c) {
    const g = c.id('fog');
    return `<defs><filter id="${g}" x="-20%" y="-50%" width="140%" height="200%"><feTurbulence type="fractalNoise" baseFrequency="0.05 0.2" numOctaves="3" seed="5"/><feColorMatrix type="matrix" values="0 0 0 0 .9  0 0 0 0 .93  0 0 0 0 .96  0 0 0 1.2 -.35"/><feComposite in2="SourceGraphic" operator="in"/><feGaussianBlur stdDeviation=".8"/></filter></defs>`
      + [78, 87, 95].map((y, i) => `<g class="wxs-drift" style="animation-delay:${-i * 2}s"><rect x="${16 + i * 5}" y="${y - 4}" width="${68 - i * 10}" height="8" rx="4" fill="#fff" filter="url(#${g})" opacity="${0.95 - i * 0.2}"/></g>`).join('');
  },
};

const photographic = {
  sun(c, small) {
    const g = c.id('sun'), x = small ? 35 : 50, r = small ? 14 : 19;
    return `<defs><radialGradient id="${g}"><stop offset=".45" stop-color="#ffe9a8" stop-opacity=".75"/><stop offset=".75" stop-color="#ffb347" stop-opacity=".22"/><stop offset="1" stop-color="#ff9a2e" stop-opacity="0"/></radialGradient>
      <clipPath id="${g}c"><circle cx="${x}" cy="${x}" r="${r}"/></clipPath></defs>
      <circle class="wxs-glow" cx="${x}" cy="${x}" r="${r * 2.1}" fill="url(#${g})"/>
      <image href="${sunPhoto}" x="${x - r}" y="${x - r}" width="${2 * r}" height="${2 * r}" clip-path="url(#${g}c)" style="filter:saturate(.8) brightness(1.25)"/>
      <circle cx="${x}" cy="${x}" r="${r}" fill="none" stroke="#fff3c8" stroke-opacity=".6" stroke-width="1"/>`;
  },
  moon(c, small) {
    const g = c.id('moon'), x = small ? 35 : 50, r = small ? 14 : 20;
    return `<defs><clipPath id="${g}d"><circle cx="${x}" cy="${x}" r="${r}"/></clipPath><clipPath id="${g}l"><path d="${moonD(c, r, x)}"/></clipPath>
      <radialGradient id="${g}g"><stop offset=".5" stop-color="#dfe7f3" stop-opacity=".22"/><stop offset="1" stop-color="#dfe7f3" stop-opacity="0"/></radialGradient></defs>
      <circle cx="${x}" cy="${x}" r="${r * 1.8}" fill="url(#${g}g)"/>
      <image href="${moonPhoto}" x="${x - r}" y="${x - r}" width="${2 * r}" height="${2 * r}" clip-path="url(#${g}d)" opacity=".13"/>
      <image href="${moonPhoto}" x="${x - r}" y="${x - r}" width="${2 * r}" height="${2 * r}" clip-path="url(#${g}l)" style="filter:brightness(1.35) contrast(1.05) sepia(.12)"/>`;
  },
  cloud: (c, o) => litCloud(c, o),
  ...nature,
};

const atmospheric = {
  sun(c, small) {
    const g = c.id('sun'), x = small ? 35 : 50, r = small ? 9 : 12;
    return `<defs><radialGradient id="${g}"><stop offset="0" stop-color="#ffffff"/><stop offset=".22" stop-color="#fffbe8"/><stop offset=".4" stop-color="#ffe7a0" stop-opacity=".8"/><stop offset=".7" stop-color="#ffc35a" stop-opacity=".25"/><stop offset="1" stop-color="#ffa23a" stop-opacity="0"/></radialGradient>
      <linearGradient id="${g}f" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff6d8" stop-opacity=".7"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>
      <circle class="wxs-glow" cx="${x}" cy="${x}" r="${r * 3.4}" fill="url(#${g})"/>
      <g class="wxs-turn"><rect x="${x - r * 4}" y="${x - 0.7}" width="${r * 8}" height="1.4" fill="url(#${g}f)"/><rect x="${x - r * 3}" y="${x - 0.5}" width="${r * 6}" height="1" fill="url(#${g}f)" transform="rotate(62 ${x} ${x})"/><rect x="${x - r * 3}" y="${x - 0.5}" width="${r * 6}" height="1" fill="url(#${g}f)" transform="rotate(-58 ${x} ${x})"/></g>
      <circle cx="${x}" cy="${x}" r="${r}" fill="#fffef6"/>
      ${small ? '' : `<circle cx="${x + 22}" cy="${x + 18}" r="3.2" fill="#9fd4ff" opacity=".22"/><circle cx="${x + 30}" cy="${x + 25}" r="5.5" fill="none" stroke="#ffd59a" stroke-opacity=".22" stroke-width="1"/>`}`;
  },
  moon(c, small) {
    const g = c.id('moon'), x = small ? 35 : 50, r = small ? 14 : 20;
    return `<defs><filter id="${g}t" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.09" numOctaves="5" seed="11"/>
        <feColorMatrix type="matrix" values="0 0 0 0 .92  0 0 0 0 .9  0 0 0 0 .84  -1.3 0 0 0 .95"/><feComposite in2="SourceGraphic" operator="in"/></filter>
      <radialGradient id="${g}s" cx=".62" cy=".4" r=".7"><stop offset="0" stop-color="#fbf8ee"/><stop offset=".8" stop-color="#d9d3bf"/><stop offset="1" stop-color="#9c967f"/></radialGradient>
      <clipPath id="${g}l"><path d="${moonD(c, r, x)}"/></clipPath><radialGradient id="${g}g"><stop offset=".5" stop-color="#e2e9f5" stop-opacity=".2"/><stop offset="1" stop-color="#e2e9f5" stop-opacity="0"/></radialGradient></defs>
      <circle cx="${x}" cy="${x}" r="${r * 1.8}" fill="url(#${g}g)"/>
      <circle cx="${x}" cy="${x}" r="${r}" fill="#46505e" opacity=".35"/>
      <g clip-path="url(#${g}l)"><circle cx="${x}" cy="${x}" r="${r}" fill="url(#${g}s)"/><rect x="${x - r}" y="${x - r}" width="${2 * r}" height="${2 * r}" fill="#7d7766" filter="url(#${g}t)" opacity=".55"/></g>`;
  },
  cloud: (c, o) => litCloud(c, { ...o, seed: 7 }),
  ...nature,
};

export const SVG_SETS = { modern, futuristic, photographic, atmospheric };

/**
 * The drawing for one condition (WeatherIcon's names) in one set, by day or
 * at night. The conditions without a sun are the same at night.
 */
export function drawWeather(setName, condition, ctx) {
  const S = SVG_SETS[setName];
  const sky = (small) => (ctx.night ? S.moon(ctx, small) : S.sun(ctx, small));
  const behind = 'translate(5 3)', over = 'translate(0 -10)';
  switch (condition) {
    case 'clear': return sky(false);
    case 'mostly-clear':
    case 'partly-cloudy': return sky(true) + S.cloud(ctx, { t: behind });
    case 'overcast': return S.cloud(ctx, { dark: true, t: 'translate(-10 -9) scale(.85)', seed: 4 }) + S.cloud(ctx, { t: 'translate(3 1)' });
    case 'fog': return S.cloud(ctx, { t: 'translate(0 -13)' }) + S.fog(ctx);
    case 'drizzle':
    case 'freezing-drizzle': return S.cloud(ctx, { t: over }) + S.rain(ctx, 2);
    case 'rain':
    case 'heavy-rain':
    case 'freezing-rain': return S.cloud(ctx, { dark: true, t: over }) + S.rain(ctx, 3);
    case 'showers':
    case 'heavy-showers': return sky(true) + S.cloud(ctx, { t: 'translate(5 -6)' }) + S.rain(ctx, 2);
    case 'snow':
    case 'heavy-snow':
    case 'snow-grains': return S.cloud(ctx, { t: over }) + S.snow(ctx);
    case 'snow-showers': return sky(true) + S.cloud(ctx, { t: 'translate(5 -6)' }) + S.snow(ctx);
    case 'thunderstorm':
    case 'thunderstorm-hail': return S.cloud(ctx, { dark: true, t: over }) + S.bolt(ctx);
    default: return S.cloud(ctx, {});
  }
}
