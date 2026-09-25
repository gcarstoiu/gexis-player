# Finding 057 — The progress bar is what keeps the panel awake

**Date:** 2026-09-24
**Question:** [Finding 056](056-why-a-still-panel-is-never-idle.md) removed
the badge pulse and left *"why does a still artist grid still drop 2.67%
when a still now playing drops 1.18%"* open. Criterion 0 step 3.
**Scope:** `gexis`, 2026-09-24, music playing, `tools/panel-frames.py`,
medians of 15–20 runs. The transition was suppressed by **injecting a
stylesheet into the live page** and put back afterwards; nothing shipped
moved during the measurement. **Not tested:** what the same change does on
a phone, and whether any other `width` transition is hiding elsewhere.

## The pulse is gone, and now playing is clean

George, 2026-09-24: *"Remove the pulse on both the mini strip and now
playing."* Done, and measured on the shipped build:

| | before | after |
| --- | --- | --- |
| now playing, still | ~2.30% dropped | **0.00%** |
| artist grid, still | 15.29% | 6.6–9.3% |

**Now playing is inside the 2% target.** The artist grid is not.

## What was left

With the pulse gone, the grid reports **zero running animations**, 917 tiles
in the DOM, 20 images, none of them still loading — and still asks for
**75 frames a run** on a screen nobody is touching.

The one thing left moving is in the mini strip, which is on every library
screen:

```css
.progress__fill { width: var(--pos, 0%); transition: width 400ms linear; }
```

and the playhead ticks every **500 ms**. So a `width` transition is running
for **400 of every 500 ms — 80% of the time** — and `width` is layout, not
compositing.

## What it costs

| artist grid, still | frames a run | dropped |
| --- | --- | --- |
| as it ships | 75 | **9.33%** |
| transition suppressed | **5** | **0 in 15 runs** |

**That is the whole of it.** With the progress bar's transition suppressed a
still artist grid asks for five frames a run and drops none. Everything the
"idle" panel was doing was this.

## And a warning about the metric

The same suppression on a *scroll* reported **75.00% dropped against
49.23%** — worse. It is not worse. The scroll asked for 41 frames instead of
67, because the free frames the progress bar was adding are gone, and a
dropped-frame *percentage* moves when its denominator does. fps barely
changed: 20.8 against 25.1.

**So for the scrolls, fps is the number to trust and the percentage is
not.** Nothing in Finding 055's table is wrong, but two scenes there cannot
be compared with each other on percentage alone unless they asked for a
similar number of frames.

## Fixed, 2026-09-24

George: *"If the rounded corners would be the only thing we would lose, go
for the change as it is barely visible."* They were not the only option, and
nothing was lost: **`.progress__track` already has `border-radius` and
`overflow: hidden`**, so a full-width fill translated left is clipped to the
track's own pill. `transform: translateX(calc(var(--pos) - 100%))` with a
`transform` transition, on both surfaces.

Measured on the shipped build:

| still screen | before | after |
| --- | --- | --- |
| now playing | ~2.30% dropped | **0.00%** |
| artist grid | 9.33% | **0.00%** |

**Both still screens are now inside the 2% target**, and the only running
animation on the panel is a `transform`, which the compositor does alone.
The bar was checked in place: at a position of 97.46% the fill is visible
from 0 to 1137px of a 1168px track, with its caps intact.

## The fix that was not needed

`scaleX` was offered and accepted, and is not what was done: it squashes
the caps of a four-pixel pill, and the track's own clipping made that
unnecessary. Recorded because the cheaper-looking answer was the worse one.

## What this does not settle

- **The scrolls.** The progress bar is neutral there; the artist grid's
  ~49% is the list, as Finding 056 already showed for the pulse.
- **Whether any other transition animates a layout property.** Only
  `.progress__fill` was looked for.
