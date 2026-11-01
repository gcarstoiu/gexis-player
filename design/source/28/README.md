# Phase 28 — themes (2026-10-28)

Brief: `uploads/brief_file-1793222831015-z1r1.md` (28-themes.md).
Open `Themes Sampler.dc.html`: five themes, 1a–1e, each on the panel's Now
Playing (1280 × 800), the bar (1280 × 400) and the phone remote, with contrast
figures at the track title.

| id | name | kind | mono (OFL) |
|---|---|---|---|
| 1a | Amber | dark | Share Tech Mono |
| 1b | Phosphor | dark | VT323 (sizes × 1.32: it runs small) |
| 1c | Night | dark | DM Mono |
| 1d | Bauhaus | light | Space Mono |
| 1e | Console | light | Overpass Mono |
| 2a | Sage | light | Martian Mono (× 0.9) |
| 2b | Riso | light | Azeret Mono |
| 2c | Velvet | dark | Red Hat Mono |
| 2d | Ink | dark | JetBrains Mono |
| 3a | Gauge | dark | Chivo Mono |

Kept (George, 2026-10-28): 1d Bauhaus, 2a Sage, 2c Velvet, 2d Ink, 3a Gauge.
Turn 2 asked for two more light and two more dark; turn 3 for one
industrial, measuring-instrument theme.

## Full set: `Theme Spec.dc.html`

One theme at a time (tabs at the top, or `?theme=<id>`). Per theme: the
tokens file, its colour tokens, its contrast table, and every artboard the
brief asks for at real size: panel Now Playing (dark and bright cover),
library home, volume drawer, Settings, waiting screen; bar Now Playing and
tray; phone remote (dark and bright cover) and its Settings. The tokens list
and the contrast figures are read from `design/themes/tokens-<id>.css` at load.

The bright cover is `album-art-bright.png`: the same public-domain Kandinsky,
inverted, so a near-white cover with the same composition.

Artboard states come from the URL of one copy per screen (`build.js`
explains): `?prop=value` sets a prop, `?s_key=value` an initial state,
`?call=openSettings` calls a method, `?cover=bright` swaps the cover.
Settings is `<id>-settings.dc.html`, imported by that theme's Now Playing
and phone. Our Bluetooth mark is `<id>-bluetooth.svg`, drawn from
`design/marks/bluetooth.svg` in the theme's --accent-bluetooth.

Contrast: every text token passes its floor on base, panel, well, and a white
and a black cover at the title, in all five.

## How the copies are made

`themes.js` holds each theme's values. `build.js` copies the locked sources
(`22/Now Playing`, `19/Bar Frame`, `22/Phone Remote Multiroom`) and changes
only: colour literals (by family: ink, each accent, grounds, weave), the
cover veil, the weave angle, the mono family, px corner radii (× the theme's
factor). It also writes `design/themes/tokens-<id>.css` by the same substitution over
`design/tokens.css`. The locked files are never written.

The phone copy opens with its player menu closed (default `open` is none).

## New token

`--cover-veil`: the cover's darkening (lightening, on a light theme) on Now
Playing, today a literal in code. Each theme's is strong enough that every
text token holds its floor over a white and a black cover at the title.

## Still to do for a kept theme

- Ship each mono's woff2 in `design/fonts` (all OFL 1.1: Space Mono, Martian
  Mono, Red Hat Mono, JetBrains Mono, Chivo Mono). These designs load them
  from Google Fonts; the player never fetches a font.
- Type scale, control sizes and motion are today's in all five; the brief
  allows a theme to change them.
- Not drawn: the visualiser skins, boot splash and weather icons (separate
  pieces per the brief) and the Home Assistant card (it follows its own
  tokens block, which the substitution recolours).
