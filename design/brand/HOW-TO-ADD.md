# Adding the gexis mark to the design system

Copy the files, make three edits. Nothing overwrites anything you already
have.

```
assets/fonts/BricolageGrotesque[opsz,wdth,wght].ttf   new   399 KB
assets/fonts/OFL.txt                                  new
tokens/brand.css                                      new
tokens/fonts-brand.css                                new
tokens/patterns-brand.css                             new
display/Logo.jsx  .d.ts  .prompt.md                   new
display/BootScreen.jsx  .d.ts  .prompt.md             new
guidelines/brand-logo.html                            new
guidelines/brand-boot.html                            new
```

### 1. Copy the files

Paths are relative to the design-system root.

### 2. Three edits to existing files

**`styles.css`** — three imports at the end. `fonts-brand.css` must come
before `brand.css`:

```css
@import url('./tokens/fonts-brand.css');
@import url('./tokens/brand.css');
@import url('./tokens/patterns-brand.css');
```

**`readme.md`** — the Iconography section currently says:

> **There is no gexis logo.** The sources contain none, so the device name is
> set in plain type wherever a mark would go. Do not draw one.

Suggested replacement:

> **The panel carries no logo.** Now Playing and Settings contain none, and
> they are locked — the device name stays in plain type wherever a mark would
> go. A mark does now exist (`display/Logo.jsx`,
> `guidelines/brand-logo.html`) for the surfaces outside the panel: boot, the
> favicon, an avatar, print and the website. Do not add it to a panel screen.

**`readme.md` Index table** — add `display/Logo`, `display/BootScreen`,
`guidelines/brand-logo`, `guidelines/brand-boot`.

### 3. Decide about the font

See *Fonts* below. It is one line either way and you should make the call
deliberately.

---

## Fonts

The mark is set in **Bricolage Grotesque**, which makes three families where
the system had two. This is the largest thing this package asks of you.

**Why a third family.** At tile size — a letter inside a rotated 120 px
square — Nunito Sans 700 goes soft and its double-storey `g` crowds the
corner. Bricolage has shorter extenders, wider apertures and a single-storey
`g` that fills a rotated square evenly. The difference is visible at 34 px
and unmissable at 120 px.

**What ships.** One variable file, upstream, three axes:

| axis | range | used |
|---|---|---|
| `wght` | 200 – 800 | 600 wordmark, 800 tiles |
| `opsz` | 12 – 96 | 96 (default — display sizes) |
| `wdth` | 75 – 100 | 100 (default) |

One file rather than two or three static cuts, which is why it is 399 KB.

**It is vendored, never fetched.** `tokens/fonts-brand.css` points at
`assets/fonts/`, same rule as your other four webfonts — the panel has no
network at runtime. `font-display: block`, not `swap`: the mark must not
flash a fallback letterform mid-boot.

**Convert to woff2 if your build can.** Roughly a third of the size, no other
change — the family name stays the same. The `.ttf` here is the upstream
file so you are not stuck with my conversion.

**Or waive it.** Set `--logo-face: var(--font-ui)` in `tokens/brand.css` and
the mark falls back to Nunito Sans everywhere. It is softer and the `g` is
wrong, but it costs nothing and it is one line.

**Licence.** Copyright 2022 The Bricolage Grotesque Project Authors
(`github.com/ateliertriay/bricolage`), SIL Open Font Licence 1.1.
Redistribution is permitted; keep `OFL.txt` next to the font. Raster output
(the Plymouth frames) carries no font data and has no attribution
requirement.

---

## What this adds, and what it costs

**No new hues, but six new values.** The four tiles reuse `--accent-lms`,
`--accent-warn`, `--accent-bluetooth` and `--accent-artist`. The mark does
add six values the system did not have, all declared in `tokens/brand.css`:

- `--logo-unlit` `#2c404f` and `--logo-unlit-ink` `#6e8595` — the resting
  tile. `--weave-a` alone is too light against the ground; this is it taken
  60% toward `--bg-base`. It is the most-seen colour in the cycle, so it is
  pinned as a literal rather than computed.
- `--logo-ink-g/e/i/s` — a glyph ink per accent. `--ink-on-accent` is one
  cold near-black, right for a chip of accent in a panel surface; at 120px
  filling a rotated square it reads as a hole punched in the tile. Each ink
  is its own accent taken down past 8.5:1.

It does give those four hues a **second job**. Today an accent identifies a
renderer, a settings group or a state — always something the panel is doing
right now. In the mark they identify a property of gexis. The two never
appear together, since the mark is not on the panel, but it is a real
widening of the rule and you should decide you want it.

**A second indefinite animation.** `motion.css` says the waiting-service
pulse is the only one. The boot pulse is a second — a 2 s loop that starts
only after the intro has finished. It is declared and argued in
`tokens/patterns-brand.css`: boot is not a running screen, so it never
competes with a surface that matters.

**Opacity and transform only.** Each tile is an unlit base with a lit overlay
stacked on it; the cycle animates the overlay's opacity and nothing else, so
no tile repaints. That constraint shaped the animation rather than being
applied to it afterwards.

---

## The property mapping

| Letter | Property | Covers | Flourish |
|---|---|---|---|
| `g` | gazette | writing, topical — politics, science, film, music | caret on a ruled line |
| `e` | engine room | homelab, infrastructure, what runs the rest | three status leds |
| `i` | inbox | mail | one unread arriving |
| `s` | sound | the player — this device | two wavefronts |

`x` is the diagonal gap between the tiles, not a tile. It is unclaimed, and
it is the slot a fifth property would use.

---

## The boot sequence

**Two ranges, not one loop.** An intro that plays once, then a pulse that
repeats until something else takes the screen:

| range | length | playback |
|---|---|---|
| intro | 2 s | once (`iteration-count: 1`, `fill-mode: forwards`) |
| pulse | 2 s | for ever (`infinite`, `delay: 2s`) |

```
intro   0 – 46 %   light crosses the tiles: g, e, i, s
        46 %       settles on the booting property's letter
        55 – 75 %  the wordmark rises
        68 – 86 %  the sub-label and the flourish fade in
pulse   12 %       a strong beat
        26 %       a softer second beat
        55 – 100 % rest, still until the wrap
```

An earlier version ran one 10 s loop, so the travel replayed every ten
seconds. It should not: the travel is an opening, and once the mark has
settled the only thing still moving is the pulse. This also narrows the
motion.css exception rather than widening it — the indefinite part is now a
2 s pulse on a few elements.

### Three invariants worth stating

**The intro rules are slots, not letters.** `iv-1`…`iv-4` are the times
10 %, 22 %, 34 %, 46 %. Tile g always takes slot 1, e slot 2, i slot 3, s
slot 4, and only the landing tile swaps to the `-h` variant that holds.
Naming them by letter once caused three of the four screens to travel in the
wrong order, because each swapped which tile got the holding rule — which
also swapped when that tile lit.

**The wordmark is larger than the mark.** `size` on `BootScreen` is the
MARK's width; the wordmark derives at about 2.7× it. The mark is the smaller
thing above the text, not a badge the text hangs off.

**Wavefronts launch clear of the tiles.** The mark's circumscribed radius is
`size × 0.465` and the ring box starts outside it. Resize the mark without
the rings following and each ring emerges from behind the tiles, leaving
four wedges flashing at the corners.

### On the device

The panel's browser is not up during boot, so the sound sequence ships as a
Plymouth PNG sequence, not as this component: 100 frames at 1280×800, 25 fps,
**intro 1–50 played once, pulse 51–100 looped**. The pulse wrap is
pixel-identical (measured 0/255) because the pulse ends in a genuine rest —
a continuously breathing loop cannot do better than an ordinary step. Every
frame's ground is exactly `#101a21`, so the handover to the UI is invisible
whichever frame is showing.

Same two ranges, same timings as the component. If the keyframes in
`patterns-brand.css` change, the frames must be re-rendered to match.

## Source

Designed in the `Unified Logo for DAC Player` project:

- `Gexis Logo.dc.html` — the mark, lockups, sizes, the property system
- `Gexis Boot Screens.dc.html` — all four boot sequences
- `plymouth/` — the device frame sequence and its own README
- `Gexis Logo Explorations.dc.html` — the rounds that led here

Those review files use Quicksand and DM Mono for their own chrome and write
hexes literally. The files in this folder are the retokenised version:
system colours, system type, system motion.
