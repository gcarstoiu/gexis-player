# Handoff: gexis panel UI

## Overview

The complete interface for the gexis network audio player: a 1280×800
touch-only panel, plus two screens the user's phone sees (Settings and
first-run Setup). Thirteen screens in all — Now Playing, the mini strip, the
library root, Browse, the artist grid, an artist page, an album page, Radio,
the idle screen, pairing confirmation, the handoff transition, Settings and
Setup.

The target is `gcarstoiu/gexis-player` — a Svelte 5 UI over a Python core.
`repo-context.md` in this folder records the branch, the last sync, and which
repo files each screen maps to.

## About the design files

**The HTML in this bundle is a design reference, not production code.** The
`.dc.html` files are interactive prototypes: they open in a browser, they run
their own state, and they exist to show intended look and behaviour exactly.
They are not written to be copied into the app.

The job is to **recreate these designs in the target codebase's own
environment** — Svelte 5 components, the project's existing patterns, its own
state store. Where the repo has no equivalent yet (`ui/src/App.svelte` is a
deliberate skeleton that says in its own comment it gets replaced), build it
in the framework already chosen for the project rather than introducing
another.

`design/now-playing.html` is the one exception in spirit: it is a plain
HTML/CSS transcription of one screen, written so the values can be read
without running the prototype. Read it as a specification, not as a file to
ship.

## Fidelity

**High.** Colours, type, spacing, states and interaction behaviour are all
final unless a line in `design/README.md` says otherwise. Recreate them
exactly. `design/tokens.css` holds every value as a CSS variable; start
there.

Two things are explicitly *not* final and are marked as such in the
documents: the skin picker's previews (no render exists for any of the 84
skins yet) and the idle screen's wallpaper sources (no service chosen, no
on-device path agreed).

## Where to start

| Read | For |
|---|---|
| `design/README.md` | How the package is put together, the constraints it honours, what changed and when. **Read this first.** |
| `design/tokens.css` | Every colour, type size, radius, shadow and tracking value. |
| `design/screens.md` | All thirteen screens, one section each. |
| `design/settings.md` | Settings' row-type vocabulary and its full row inventory. |
| `design/data-contract.md` | Every field each screen needs, mapped to `/state`. Fields the backend does not publish yet are marked NEW. |
| `design/now-playing.html` + `.css` + `.js` | Now Playing as plain HTML/CSS, six states. |
| `design/verify.html` | 38 checks in 6 groups, including a live computed-style diff against the prototype. |
| `*.dc.html` at this folder's root | The prototypes. Open in a browser. |

## Screens

Every screen is described in `design/screens.md` with its layout, its
components and its exact values — that file is the screen-by-screen
specification this section would otherwise duplicate. What follows is only
what a developer needs before opening it.

- **Now Playing** — artwork 500×500 left, metadata right, progress and
  transport below. Four meta tabs switch the right column between Track,
  Lyrics, Artist and Release. The source mark sits top-right at 32px with no
  word, no ground and no border.
- **Mini strip** — 104px, on every screen except Now Playing, absent when
  nothing is playing.
- **Idle screen** — clock and weather over a photo, with no plate behind any
  text. Two forecast layouts, `3 days` and `None`, which are different
  layouts rather than one with a row hidden.
- **Settings** — the only responsive screen and the only one the phone sees:
  two-pane at ≥720px, drill-down below. 49 settable rows under 7 group
  headers; 6 are wired today.
- **Setup** — runs once on an unconfigured device, over the device's own
  access point, so it is a phone screen first. Seven steps, each with its own
  accent.

## Interactions & behaviour

`design/screens.md` carries these per screen. The cross-cutting rules:

- **Touch only.** No hover state matters. Every interactive element is at
  least 44×44; several get their size from padding plus a negative margin, so
  re-measure if you restructure one.
- **No long press anywhere.** Row actions are revealed by selection.
- **No on-screen keyboard.** Text entry is native to the device the page is
  open on.
- **Unsupported controls are removed, not disabled.** Spotify Connect and
  Bluetooth have no shuffle, repeat or queue, so those controls are absent and
  the transport row re-centres.
- **Paused is shown one way:** the play control becomes pause-shaped. The
  artwork does not dim and no label appears — both were tried and removed.
- **Motion budget is a Pi 4:** transform and opacity only, one region at a
  time. No `backdrop-filter` anywhere (24.5ms a frame against a 16.7ms
  budget). Screen swaps are not animated.
- **Null handling:** the region blanks, never the screen. Every field in
  `/state` can be null; `design/README.md` lists the behaviour field by
  field.

## State management

`design/data-contract.md` is the authority: it lists every field each screen
reads, its type, whether the backend publishes it today, and what the screen
does when it is null.

Two notes that catch people out, both in `design/README.md`:

1. `sample_rate` and `codec` are **not displayed** anywhere. An earlier
   revision claimed a format badge built from them; it never shipped.
2. Volume is shown in percent, never dB. `volume.percent` is the only volume
   field any screen reads. Settings shows dB for boot and floor levels
   because those are engineering values.

Progress is interpolated client-side and re-anchored on every `/state`
message — `design/now-playing.js` shows the shape.

## Design tokens

All of them, with comments, in `design/tokens.css`: colours, the panel type
scale, tracking, radii, shadows and spacing. Nothing in the export uses a
colour that is not a token — `design/verify.html` group 4 asserts it.

## Assets

- `album-art.webp`, `artist-photo.webp` — sample images only. Real artwork
  comes from the library.
- `icon-lyrion.svg`, `icon-spotify.png`, `icon-bluetooth.png` — service
  marks.
- `design/fonts/` — four vendored woff2 files, Nunito Sans and IBM Plex Mono,
  both SIL Open Font License. `design/fonts/README.md` covers them.
- `brand/` — the gexis brand package: the mark as `display/Logo.jsx`, the
  boot screen, Bricolage Grotesque, and three token sheets. `Setup.dc.html`
  loads the mark from here. `brand/HOW-TO-ADD.md` is the brand package's own
  instructions.
- **No icon font.** Every other glyph is CSS geometry.

Known gap: the Plymouth boot frames predate the lettered mark and still show
flat tiles. They need re-rendering against `brand/tokens/patterns-brand.css`.

## Files

```
Now Playing.dc.html     the panel prototype: Now Playing, library, idle, pairing, handoff
Settings.dc.html        Settings, responsive
Setup.dc.html           first-run setup, responsive (loads brand/ and design/tokens.css)
support.js              the prototype runtime — required by all three
brand/                  brand package (mark, boot screen, Bricolage Grotesque, tokens)
design/
  README.md             how the package works and what changed; read first
  tokens.css            every design value
  fonts.css + fonts/    @font-face and the four woff2 files
  screens.md            all thirteen screens
  settings.md           Settings' vocabulary and row inventory
  data-contract.md      fields per screen, mapped to /state
  now-playing.html/.css/.js   one screen as plain HTML/CSS, six states
  geometry.json         landmark baseline, measured from the prototype
  verify.html           38 checks, including a live diff against the prototype
  source/               self-contained copies of the two panel prototypes, for verify.html
  assets/               service marks and sample images
repo-context.md         repo, branch, last sync, screen-to-file map
```

## Verifying before you start

`design/verify.html` needs an HTTP server — `file://` blocks the iframe read:

```
cd design && python3 -m http.server 8080
# then open http://localhost:8080/verify.html
```

**It has not been run against this revision.** Group 1's baseline is current
(re-measured 2026-09-22); group 6 compares live against `source/`, so it
picks up changes on its own. A failure means the export drifted from the
prototype — fix the export, never the baseline. `design/README.md` explains
why that rule exists and lists what these checks have already caught.
