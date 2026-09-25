# Finding 060 — The queue rail's own cost is two decorations

**Date:** 2026-09-24
**Question:** [Finding 059](059-what-the-panel-pays-for-its-blur.md) left the
queue rail immune to the background's blur — it sits on an opaque plate that
occludes it — and still dropping 17.9 % of its frames. This is that.
**Scope:** `gexis`, 2026-09-24, music playing, a 100-track queue, the same
170 px gesture. **Eight interleaved rounds**, one run of every variant per
round, so drift shows as drift. Each candidate suppressed in the live page
and put back. **Not settled: one result, below, which reproduces and has no
explanation.**

## The answer

| queue rail | dropped | fps | fps range |
| --- | --- | --- | --- |
| as it ships | 16.67% | 38.2 | 23.1–41.3 |
| no `box-shadow` | 7.36% | 46.1 | 37.1–48.6 |
| no shadow, no artwork | 4.96% | 50.0 | 43.1–55.7 |
| **no shadow, no remove button** | **0.00%** | **53.5** | 44.0–58.1 |
| no shadow, rows empty | 0.77% | 49.7 | 46.5–58.2 |

**Two decorations, about eight frames each.**

1. **`.rail`'s `box-shadow: -30px 0 80px rgba(0, 0, 0, 0.5)`.** An 80 px
   blur, which Finding 059 has already shown is dear wherever it is: 38.2 →
   46.1 fps.
2. **`.qrow__remove`, on every one of the rows.** A 44 × 44 box with a 12 px
   radius, a 1 px border and two 15 × 2.5 px bars at ±45°: 46.1 → **53.5 fps
   and 0.00 % dropped**, with the artwork and the text still drawn.

The rail's artwork costs about four frames (46.1 → 50.0) and is the one
thing here that is content rather than ornament.

**Nothing else moved it.** Rounded rows, `contain: content` on the list, and
the plate's `border-left` each changed nothing.

## The result that does not make sense

`.qrow__text { visibility: hidden }` — hiding the title and artist —
measures **17.48 % at 37.1 fps**, *worse* than the 7.36 % / 46.1 fps of the
same variant without it, in **all eight rounds**. Hiding text should not
cost frames.

It was found because a first pass, run block by block, put two variants
below a floor they contained. That looked like drift, and the device had
been measuring for hours at 74.5 °C — `vcgencmd get_throttled` reports
`0xd0000`, meaning under-voltage, frequency capping and the soft temperature
limit have **all occurred during this uptime**, though none was current.
Interleaving was meant to expose drift and did: the other five variants are
stable across the rounds and this one is stably wrong.

**It is recorded, not explained.** It is also not in the way: nothing
proposed here hides that text.

## What this does not settle

- **Why every list scrolls on the main thread.** `scroll_state` reads
  `SCROLL_MAIN_THREAD` on every scroller including this one, while the input
  pipeline shows the compositor handling the gesture. The leading
  explanation is Chromium's `kNotOpaqueForTextAndLCDText`, which would be
  settled by starting the kiosk with `--disable-lcd-text` — **untested, and
  it needs a change to `/usr/local/bin/gexis-kiosk-start` on the device that
  this session was not permitted to make.** If composited scrolling is
  reachable, every paint cost in this finding and in 059 stops mattering
  during a scroll, so it is worth one test.
- **The panel's power supply.** The under-voltage bit is historical and
  unexplained, and is a hardware observation, not a measurement of the UI.
- **Anything about a phone.** One panel, one device.
