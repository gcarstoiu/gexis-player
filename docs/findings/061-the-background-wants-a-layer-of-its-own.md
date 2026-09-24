# Finding 061 — The background wants a layer of its own, and the metric was hiding it

**Date:** 2026-09-24
**Question:** George asked for `kNotOpaqueForTextAndLCDText` to be tested,
and asked why the blurred background could not simply be photographed and
served until the track changes.
**Scope:** `gexis`, 2026-09-24, music playing except where noted, the same
170 px gesture, medians of 10 runs. **Corrects
[Finding 059](059-what-the-panel-pays-for-its-blur.md) and one thing said to
George on the strength of it.**

## The answer is one line, and it is invisible

```css
.bg { will-change: transform; }
```

| artist grid | dropped | fps | frames drawn/s |
| --- | --- | --- | --- |
| as it ships | 29.32% | 27.8 | 27.8 |
| **`.bg { will-change: transform }`** | **4.06%** | **52.9** | 52.8 |
| `.bg { transform: translateZ(0) }` | 3.10% | 49.1 | 51.5 |
| `.bg { contain: paint }` | 31.34% | 26.6 | 27.6 |
| both blurs hidden (reference) | 2.44% | 51.6 | 52.8 |
| the background served as a picture | 3.94% | 50.7 | 51.5 |

**As good as deleting the background, and it changes nothing on the glass.**
Photographed paused, so the track could not change between captures:
`will-change` against as-it-ships is **max difference 2 of 255, with 0.00 %
of pixels differing by more than 4**. Hiding the blurs changes 73 % of them.

The blur is rastered once into its own layer and then reused, instead of
being redrawn inside whatever the scroll damages. `contain: paint` does not
do it — it clips, it does not promote.

## Why Finding 059 said the opposite

**A selector that matches nothing measures the page unchanged, under a
variant's name.** Those three rows used `[aria-hidden='true'] .bg`, and
`.bg` *is* the element carrying `aria-hidden`:

```html
<div class="bg" aria-hidden="true">
```

So the descendant combinator had nothing to find, three variants were the
control three more times, and "layer promotion does nothing" followed — as
did a tidy explanation of *why* a cached layer could not help, which was
reasoning from an artefact. `.weave` and `.bleed` **are** inside `.bg`, so
every blur measurement in 059 applied and stands.

**It was caught by a guard, not by a re-read.** The probe for George's
snapshot idea checked that the picture had actually applied before
measuring, printed `applied: None`, and refused to produce a number. The
same guard would have voided those three rows a day earlier.

## George's snapshot idea

**It works: 50.7 fps against 27.8.** Photograph the background once, serve
the photograph, and no filter is evaluated per frame — the look is the
current one exactly, because it *is* the current one. A quarter-scale
capture loses nothing, since the subject is already a 70 px blur.

It is beaten only by the one-line change, which needs no capture, no cache
and no invalidation on track change. **Worth keeping in the drawer**: it is
the fallback if `will-change` ever costs memory that the Pi cannot spare, a
layer of that size being roughly 4 MB.

## `--disable-lcd-text`, and a frame counter that lied

**Confirmed: `kNotOpaqueForTextAndLCDText` is why every list scrolls on the
main thread.** Started with the flag, `scroll_state` reads
`SCROLL_COMPOSITOR_THREAD` on the artist grid and the queue rail.

**And the first reading of it was wrong.** `PipelineReporter` said the
artist grid had gone from 25.6 fps to 11.7, which was reported to George as
"the cure is worse than the disease". It is the compositor's own
bookkeeping, and a scroll the compositor drives produces fewer of those
reporters. `DrawToScheduleOverlay` — one per frame drawn, from viz — says
otherwise:

| artist grid | PipelineReporter fps | frames drawn/s |
| --- | --- | --- |
| as it ships | 25.4 | 25.5 |
| `--disable-lcd-text` | 10.4 | **58.2** |

| queue rail | | |
| --- | --- | --- |
| as it ships | 37.2 | 39.1 |
| `--disable-lcd-text` | 15.1 | **57.9** |

**The two agree to within a frame when the scroll is on the main thread,
and diverge threefold when it is not.** That is what makes the second one
trustworthy here and the first one not. `panel-frames.py` now reports both.

So the flag takes both screens to roughly the 60 Hz ceiling — more than any
CSS change — and under it the background fix stops mattering at all (13.8
against 12.8 fps by the old metric, both at the ceiling by the new one),
because a composited scroll never re-rasters the blur.

**What it costs is subpixel text.** On the shipped panel, the now-playing
title over a near-neutral backdrop has a maximum edge chroma of 18 of 255,
which is greyscale antialiasing — **this text does not appear to be getting
subpixel rendering in the first place**, while the panel pays main-thread
scrolling to keep the option. At 3× magnification the two look the same. A
numeric comparison of the two captures was **not** valid — they were taken
on different tracks and the second backdrop was strongly coloured — so this
is one capture read carefully, not a measured difference.

## What this does not settle

- **Whether the flag is worth taking** once `will-change` is in. The one
  line reaches ~53 frames a second drawn; the flag reaches ~58, on every
  screen including the rail, and makes Findings 059 and 060's paint costs
  irrelevant during a scroll. Both together are untested.
- **Whether subpixel text is in use anywhere else** on the panel. One
  element was examined.
- **Memory.** A promoted full-panel layer is roughly 4 MB and was not
  measured.
- **The rail's remove button and shadow** ([Finding 060](060-the-queue-rails-own-cost.md))
  are untouched by any of this, unless the flag is taken.
