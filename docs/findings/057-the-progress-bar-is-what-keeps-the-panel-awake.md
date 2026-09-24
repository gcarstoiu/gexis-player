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

## The fix is not obvious, and is not made here

`width` cannot be animated without layout. The usual answer, `transform:
scaleX()`, would distort the bar's rounded caps - it is a pill four pixels
tall, and scaling it horizontally squashes both ends. Translating a
full-width fill inside a clipping parent keeps the caps and costs nothing,
but it is a change to a **designed** component, so it is George's rather
than mine.

**What is certain is the size of the prize:** a still panel that asks for
five frames a run instead of seventy-five, on every screen that carries the
mini strip.

## What this does not settle

- **The scrolls.** The progress bar is neutral there; the artist grid's
  ~49% is the list, as Finding 056 already showed for the pulse.
- **Whether any other transition animates a layout property.** Only
  `.progress__fill` was looked for.
