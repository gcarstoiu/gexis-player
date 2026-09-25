# Finding 056 — A pulsing badge is why a still panel is never idle

**Date:** 2026-09-24
**Question:** [Finding 055](055-what-the-panel-presents-now.md) left the idle
control at **3.43% dropped** against a 2% target — small beside Finding 034's
void 71%, and still over. Criterion 0 step 3 begins by attributing it.
**Scope:** `gexis`, 2026-09-24, image `v0.2.1-455`, music playing,
`tools/panel-frames.py`. Each figure is the median of 12–20 runs. The
pulse was turned off by **injecting a stylesheet into the live page**, not
by changing the code, so nothing shipped moved during the measurement and
it was put back afterwards. **Not tested:** any screen without the mini
strip, and whether the same holds on a phone.

## Three candidates eliminated first

| | idle control, dropped |
| --- | --- |
| peppy running (as it ships) | 0.57% |
| **peppy stopped** | **0.57%** |

**Not the visualiser.** PeppyMeter renders behind the kiosk at 25–30 fps and
it costs the panel nothing measurable.

**Not the daemon.** `/state` delivered **1 message in 12 seconds** while
playing: the panel derives the playhead locally and is not being pushed at.

**Not wear.** Idle was measured on a freshly restarted kiosk, then again on
the same kiosk after **40 artist-grid scrolls**: 2.25% before, 2.38% after.
The panel does not degrade with use, which a first look at the spread had
suggested.

## What it is

**A still artist grid drops more than a still now playing** — 8.14% against
2.30%, with both asking for the same ~86 frames a run. A screen nobody is
touching should ask for none.

Asked what was animating, the page answered with one thing:

```
running animations: 1
   pulse on SPAN.badge
```

`.badge.is-playing { animation: pulse 2.4s ease-in-out infinite; }` — an
opacity pulse on the source badge, in **both** `MiniStrip.svelte` and
`NowPlaying.svelte`, running whenever the transport is playing. The mini
strip is on every library screen, so **every screen is being composited at
60 fps while music plays.**

## What it costs

| scene | pulse on | pulse off |
| --- | --- | --- |
| **artist grid, still** | **15.29%** | **2.67%** |
| now playing, still | ~2.30% | 1.18% |
| **artist grid, scrolling** | 49.23% | 50.75% |

**On a still screen it is most of the drops**, and it costs far more on the
artist grid than on now playing: a continuously composited frame over 917
tiles is not the same frame as one over an album cover.

**During a scroll it costs nothing at all.** 49.2% against 50.8% is the same
number twice. So the 49% that makes the artist grid the worst thing on the
panel is the list, and none of it is the pulse.

## What it means for the target

- **A still panel can be brought inside 2%** by not animating a decoration
  on it. It is one line of CSS and the only cost is the badge stops
  breathing.
- **It does not help any scroll**, so it changes nothing about criterion 0's
  main work.
- **It is a product decision, not a defect.** The pulse says *this renderer
  is playing*, which is real information; whether it is worth a panel that
  is never idle is George's.

## What this does not settle

- **Why a still artist grid still drops 2.67% with the pulse off**, when a
  still now playing drops 1.18%. Something else on that screen asks for
  frames; nothing here says what.
- **The spread.** Across nine samples the idle median ranged 0.00–5.95% with
  maxima to 37%. The pulse explains the level, not the variance.
- **Nothing was attributed on the scrolls**, which is the rest of step 3.
