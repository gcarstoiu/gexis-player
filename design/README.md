# design/ — gexis panel handoff

Design reference for the panel UI. Authored as HTML, **not production code**:
port it into Svelte 5 components using the project's own patterns. The
`.dc.html` files in `source/` stay the source of truth between iterations —
when the design changes, it changes there first.

**Fidelity: high.** Colours, type, spacing, states and interaction behaviour
are all final unless a row below says otherwise. Recreate them exactly.

---

## What is in here

| Path | What it is |
|---|---|
| `tokens.css` | Every design value as a CSS variable. Start here. |
| `fonts.css` | `@font-face` declarations, resolving against `fonts/` — see Fonts. |
| `now-playing.html` + `.css` + `.js` | **First slice.** Six states of the Now Playing screen, plain HTML/CSS. |
| `data-contract.md` | Every field each screen needs, mapped to `/state`. Fields the backend does not publish yet are marked NEW. |
| `settings.md` | Settings row-type vocabulary and the full row inventory. Provisional. |
| `screens.md` | The other eight screens, described for later phases. |
| `source/*.dc.html` | The full interactive design. Open in a browser. |
| `assets/` | Service marks and the two sample images. |

---

## Constraints honoured

- No Svelte, no Tailwind, no CSS framework, no CDN. Plain HTML, CSS variables,
  and vanilla JS only where an interaction needs it.
- No network at runtime. Everything resolves relative to `design/`.
- Modern CSS used deliberately: container queries in Settings, `color-mix()`
  for accent tints, `:has()` nowhere yet (it was not needed).
- Nested CSS is **not** used, so the files also open in older browsers while
  being reviewed.

### Fonts

The design uses **Nunito Sans** (300–800, variable) and **IBM Plex Mono**
(400/600/700). Both are SIL Open Font License and safe to vendor.

**The four files are here as of 2026-09-19**, in `design/fonts/`, with both
licences beside them:

    fonts/NunitoSans-Variable.woff2     Nunito Sans, variable wght 200-1000
    fonts/IBMPlexMono-Regular.woff2     400
    fonts/IBMPlexMono-SemiBold.woff2    600
    fonts/IBMPlexMono-Bold.woff2        700

They are not lookalikes from a font site: they are the exact files the
shipped panel renders with, taken from the `@fontsource` packages `ui/`
builds against, so this package and the device draw the same outlines.

**They are the latin subsets**, which is also what the panel bundles.
Accented and Cyrillic text falls back; the UI's bundle carries latin-ext and
cyrillic if a mockup ever needs them.

One naming detail, harmless but worth knowing: `ui/src/styles/tokens.css`
asks for `'Nunito Sans Variable'` first - fontsource's own name for the
variable face - then `'Nunito Sans'`, while `fonts.css` here declares plain
`'Nunito Sans'` over 300-800. The file covers 200-1000, so both resolve to
the same outlines.

Before this, the CSS fell back to `system-ui` and `Courier New`, which
changes metrics: mono columns lose their alignment and the 58px title wraps
differently. That warning no longer applies to anyone using this package as
it stands.

No icon font exists. Every glyph is either CSS geometry or a file in
`assets/` — nothing to vendor.

---

## Two things to reconcile before building

**1. `sample_rate` and `codec` are displayed.** The brief says they were
dropped from the design. They were not: the Now Playing screen carries a
format tier badge built from both — `FLAC · 16/44.1 · Lossless`, with three
tiers (Lossy / Lossless / Hi-Res) and a four-segment quality meter. Colour
follows tier: Hi-Res uses `--accent-artist`, Lossless `--accent-lms`, Lossy
stays neutral.

It is **not** in the first slice, so nothing is blocked. But the fields are
needed eventually. See `data-contract.md`, Now Playing.

**2. Volume is shown in percent, never dB.** `volume.percent` is the only
volume field any screen reads. `raw` and `db` are unused. Settings shows dB
for the boot and floor levels because those are engineering values, and that
is the one exception.

---

## Paused

Paused is shown one way: **the play control becomes pause-shaped.** The
artwork does not dim and no label appears — both were tried and removed.

---

## Null handling

Every field in `/state` can be null. The rule throughout: **the region blanks,
never the screen.**

- `title` null — the line hides and keeps its height. The screen does not
  reflow. A source is playing something; the panel just cannot name it.
- `artist`, `album`, `year` null — same, each independently.
- `artwork` null — the well stays at 500×500 and shows the pending glyph.
  Bluetooth is always in this state; treat it as normal, not as an error.
- `position`/`duration` null — the progress track becomes an inert rule and
  the times hide. Layout is unchanged.
- `active` null — nothing holds the device. **This is normal.** The panel shows
  the library root, and the mini strip is absent. See `screens.md`.

The Now Playing metadata block reserves 238px, so a two-line title, a
one-line title and an entirely empty block are all the same height.

---

## Progress interpolation

`position` arrives at a rate that differs by source and cannot be relied on.
The client advances the bar itself and re-anchors on every `/state` message —
`now-playing.js` shows the shape. Two notes:

- Only a CSS custom property and two text nodes change per tick. No layout,
  no transform, no filter. A Pi 4 handles this at 2 Hz without dropping the
  transition.
- The fill carries `transition: width 400ms linear`, so a re-anchor from a
  late message glides instead of jumping.

---

## Source differences

| | LMS | Spotify Connect | Bluetooth |
|---|---|---|---|
| accent | `--accent-lms` | `--accent-spotify` | `--accent-bluetooth` |
| artwork | yes | yes | **never** |
| position / duration | yes | yes | **never** |
| shuffle / repeat | yes | **absent** | **absent** |
| queue | yes | **absent** | **absent** |

Unsupported controls are **removed, not disabled**. A greyed button invites a
press; an absent one asks no question. The transport row re-centres itself.

---

## First slice — Phase 4 step 4c

In `now-playing.html`. Display only.

**In scope:** title, artist, album, year, artwork with its no-artwork state,
source indicator, elapsed and remaining time, paused state. All three
sources, long text, missing text, Bluetooth without art.

**Rendered but inert:** transport buttons, volume, queue, the four meta tabs
(Lyrics / Artist / Release are Phase 8), Home and Visualization. They carry
`disabled` and do nothing. They are present because removing them would
misrepresent the layout — the transport row's height sets the screen's
proportions.

**Not in this package's first slice at all:** the idle screen, the handoff
transition, library, radio, playlists, settings.

---

## Verifying an export

`verify.html` checks this package against the design. Serve the directory
over HTTP and open it — `file://` blocks the iframe read:

    cd design && python3 -m http.server 8080
    # then open http://localhost:8080/verify.html

Thirty-seven checks in six groups:

1. **Geometry vs baseline** — landmark positions and sizes, and the screen
   grid's row heights, against `geometry.json`, which was measured from
   `source/Now Playing.dc.html`. ±3px, which absorbs font-fallback drift.
2. **Touch targets** — every control at least 44×44.
3. **Contrast** — all text at 24px or under clears 4.5:1 over `--bg-base`,
   computed properly with the alpha composited, not eyeballed.
4. **Tokens and assets** — no colour outside `tokens.css`, every `var()`
   resolves, images load, source-pill masks resolve.
5. **State coverage** — all three sources present, paused shown, no-artwork
   and no-position shown, Bluetooth never showing artwork or position,
   LMS-only controls absent off LMS.
6. **Computed-style diff against the design itself** — loads
   `source/Now Playing.dc.html` in a second frame and compares live computed
   values for the artwork well, play control, progress rail and track, source
   pill, top accent rule, tab type and time type. This is the group that does
   not depend on anyone remembering to write a check: a colour, gradient,
   radius or shadow that drifts fails on its own.

   Group 6 waits for the design to hydrate before comparing, because many of
   its colours come from template holes and an unhydrated element looks
   exactly like drift. If it cannot hydrate within 8s the group reports
   **could not run** rather than passing — re-run instead of trusting it.

**A failure means the export drifted from the design, not that the design
changed.** Fix the export. If the design genuinely moved, re-baseline:

1. open `source/Now Playing.dc.html` at 1280×800,
2. measure the landmarks in `geometry.json` relative to the screen's top-left,
3. write the new numbers in, and update `_measured`.

Never edit a baseline number to make a check pass — that is the failure mode
this file exists to prevent.

### What these checks already caught

All real, all invisible to review:

- The progress bar sat 55px high: the export made it its own grid child,
  where the design wraps progress and transport in one footer with an empty
  spacer above.
- Meta tabs measured 42px instead of 44px, because their height came from
  font metrics and the real faces are not vendored yet.
- The play control was wired to the source accent. It is fixed coral in the
  design, and its shadow is a specific two-layer value.
- The source pill's ground is neutral white at 8%; only its border carries
  the accent.
- The top hairline is a gradient from the source accent into coral, not a
  flat accent.
- The LMS mark was being drawn from the SVG at 18px, where the ten-bar figure
  antialiases to a smear. The design substitutes a four-bar reduction below
  40px.
- The no-position separator lost its end fades, so it read as a progress bar
  stuck at zero.
- A stray unscoped `.progress__track` rule was overriding the track colour on
  every screen — orphaned from its selector by a careless edit.
- `source/` shipped without `support.js` or its images, so the design copy
  rendered blank. Group 6 cannot run at all in that state, which is how it
  was found.

Every one of these came from writing the export from memory instead of
extracting values from the design. Group 6 exists so that method failure
cannot reach you again: extract, then diff against the source, then hand over.

### Worth adding when the ports exist

- Run group 2, 3 and 4 against the **Svelte** build too. They are
  framework-agnostic — point the iframe at the built route.
- Settings needs its own geometry baseline at two widths (≥720px and 412px).
  It is not covered here.

---

## Canvas

Every screen except Settings is a fixed **1280×800** artboard. Touch only, no
hover states that matter, no text inputs, nothing scrolls at the screen level.
Do not make these responsive.

Settings is the sole exception: two-pane at ≥720px, drill-down below. It is
the phone's only screen.

All 93 interactive elements on the panel measure at least 44px in both
directions. This was audited, not estimated — several controls get their size
from padding plus a negative margin so the target grows without moving the
ink. If you restructure a control, re-measure it.
