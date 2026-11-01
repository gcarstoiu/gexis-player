# Handoff: gexis themes — Phase 28, 2026-10-29

## Overview

Five themes for the panel, the bars and the phone remote, from
`design/briefs/28-themes.md`. A theme is a complete set of values for the
named tokens in `design/tokens.css`, applied at once to all three. It
changes how the existing screens look, never what is on them or where.

George kept, 2026-10-28:

| id | name | kind | character | mono (OFL 1.1) |
|---|---|---|---|---|
| 1d | Bauhaus | light | a printed poster: warm white paper, black type, red, blue and ochre, flat | Space Mono |
| 2a | Sage | light | a garden notebook: oat paper, deep green ink, forest green and terracotta, soft corners | Martian Mono (sizes × 0.9) |
| 2c | Velvet | dark | a listening lounge: oxblood and near-black, cream type, brass and rose | Red Hat Mono |
| 2d | Ink | dark | navy at midnight: deep blue, cool white type, sky blue and coral pink | JetBrains Mono |
| 3a | Gauge | dark | a test bench instrument: graphite, safety-yellow play key, oscilloscope channel colours, hard corners | Chivo Mono |

Today's dark theme stays as it is and is not one of the five.

Target repo: `gcarstoiu/gexis-player` (Svelte 5 UI over a Python core).

## Production wins — read this first

**No layout, size, copy or behaviour changes.** Every artboard is the locked
design with token values swapped. Build a theme as a token set only. If
production and an artboard differ in anything but token values, production
wins.

How themes ship and how one is chosen in Settings are not part of this
handoff. Phase 28's ADR decides them.

## About the design files

The `.dc.html` files are **design references built in HTML**, not production
code. Implement each theme as values for the repo's existing tokens. Do not
copy markup from the references.

```
cd design && python3 -m http.server 8080
# http://localhost:8080/source/28/Theme%20Spec.dc.html?theme=bauhaus
# theme = bauhaus | sage | velvet | ink | gauge
```

## Fidelity

**High** for every token value. Each theme's colours, mono font, corners and
cover darkening are final.

## What to build

1. **The five token sets.** `design/themes/tokens-<id>.css` uses the same
   names as `design/tokens.css` with new values. All 223 declarations are
   there: the root set and the Phase 19, 21 and 22 blocks.
2. **One new token, `--cover-veil`.** Today the cover's darkening behind Now
   Playing is a literal in code:
   `radial-gradient(130% 105% at 20% 42%, rgba(22,36,46,0.3), rgba(14,23,30,0.86))`.
   Make it a token. Each theme draws it in its own `--bg-base`, at its own
   inner and outer alpha. On a light theme it lightens the cover. Add it
   to today's theme with today's literal, so today's theme stays exactly as
   it is.
3. **Our Bluetooth mark as a drawn mark.** The brief allows recolouring it,
   and each theme draws it in its `--accent-bluetooth`. Use the vector in
   `design/marks/bluetooth.svg` (in the repo) with its stroke set from the
   token. `source/28/<id>-bluetooth.svg` shows the result. The Spotify and
   Lyrion marks and Plexamp's and AirPlay's colours stay unchanged.
4. **The mono fonts.** Each theme uses a different mono and keeps Nunito
   Sans for the UI. Ship the woff2 for each in `design/fonts/`. The player
   never fetches a font, and this bundle doesn't include them (the
   references load them from Google Fonts). All five are SIL OFL 1.1.
   Martian Mono runs large, so Sage sets mono sizes at 0.9 × today's.

## What changes per theme

Only these, by the rules in `design/source/28/build.js`:

- **Colours**, by family: grounds, the diagonal weave (its angle too), ink
  levels, each accent, play fill, focus ring, on-accent ink.
- **Light themes:** ink alphas ≥ 0.45 become `0.35 + 0.65 × a`, and lower
  ones `× 1.1`. Black shadows drop to 0.35 × their alpha.
- **Corner radii:** today's px radii × the theme's factor, minimum 2 px.
  Bauhaus × 0.75, Sage × 1.1, Velvet × 1, Ink × 1, Gauge × 0.45. Round
  controls and pills stay round, and radii under 4 px are unchanged.
- **Cover veil:** alpha at centre and edge. Bauhaus 0.88 / 0.97, Sage
  0.88 / 0.97, Velvet 0.8 / 0.96, Ink 0.8 / 0.96, Gauge 0.8 / 0.96.

These keep today's values in every theme: type scale, control sizes,
motion, layout and copy.

## Contrast

`Theme Spec.dc.html` shows each text token on each ground: base, panel,
well, and a white and a black cover under the veil, measured at the track
title.

- **Floors:** 4.5 : 1 for text 15 px and under, 3 : 1 for larger text (the
  17 px unselected tab, the 35 px artist line).
- **Results:** every text token in all five themes passes. On-accent ink
  over the play button and the active fill clears 3 : 1 in each.
- **Check:** the figures are read from the token files when the page loads.
  Re-check them after implementing.

## Files

```
HANDOFF.md                                   this file
design/themes/tokens-<id>.css                one complete token set per theme
design/tokens.css                            today's tokens, unchanged (the names)
design/fonts/                                Nunito Sans, IBM Plex Mono (today's)
design/source/28/README.md                   the spec, how the copies are made
design/source/28/Theme Spec.dc.html          every artboard + contrast, per theme
design/source/28/themes.js                   each theme's values
design/source/28/build.js                    the substitution rules
design/source/28/<id>-np|bar|phone|settings.dc.html   themed copies of the locked designs
design/source/28/<id>-bluetooth.svg          our Bluetooth mark per theme
design/source/28/album-art-bright.png        bright test cover (the Kandinsky, inverted)
design/source/28/support.js, *.webp, *.svg, *.png, *-data.js   runtime, samples
```

The artboards in `Theme Spec` cover the panel's Now Playing (dark and bright
cover), library home, volume drawer, Settings and waiting screen. They also
cover the bar's Now Playing and tray, and the phone remote (dark and bright
cover) and its Settings.

Not drawn, per the brief: the visualiser skins, boot splash, weather icons
and the Home Assistant dashboard.

`design/verify.html` passed all six groups on 2026-10-29. The locked
`Now Playing.dc.html` and `Settings.dc.html` are unchanged.

Unpack `design/` over the repo's `design/`.
