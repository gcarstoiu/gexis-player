# Finding 058 — What the scrolls are not, and two numbers that were wrong

**Date:** 2026-09-24
**Question:** Criterion 0 step 3, on the scrolls.
[Finding 055](055-what-the-panel-presents-now.md) made the artist grid the
worst thing on the panel; this set out to say why.
**Scope:** `gexis`, 2026-09-24, music playing, medians of 12–15 runs each.
Every candidate was suppressed **in the live page** and put back. **Not
settled: the cause.** Eight candidates are eliminated and none of them is
it.

## Two numbers in Finding 055 were wrong, and one claim with them

### The metric counted frames nobody could see

The compositor marks each dropped frame `affects_smoothness`, and
Chromium's own *percent dropped frames* counts only those. This tool counted
every `STATE_DROPPED`. On one artist-grid scroll: **19 of 36 dropped frames
affected smoothness and 17 did not.**

| | as reported | counted Chromium's way |
| --- | --- | --- |
| artist-grid-scroll | 49.6% | **≈28%** |
| queue-rail-scroll | 11.4% | **0.00%** |

**Every dropped-frame figure this tool has ever printed was high**, by
roughly a factor of two.

### The queue rail was not scrolling

And then the corrected queue-rail number — 0.00% dropped, 44 fps — turned
out to be a gesture on a queue of **sixteen tracks that fits the screen**.
It **moved 0 px**. A swipe that moves nothing drops nothing.

Given a real queue of **198 tracks**, the same scene reads:

```
queue-rail-scroll   fps median 36.5   dropped median 20.79 %   scroll on the MAIN THREAD
```

**So the rail is not a counter-example; it is another instance.** And
`albums-scroll` moved **191 px** against the grid's 574, so those two were
never comparable either.

### What that costs a claim

Finding 055 said ADR-0041's scrim removal took the queue rail from Finding
034's *13.9 fps / 75.2% dropped* to *50.0 / 11.4%*, and called it confirmed.
**It is not confirmed by that comparison.** 034 measured a rail with a real
queue; 055 measured one with nothing to scroll. ADR-0041's own measurement
in [Finding 037](037-why-a-blurred-scrim-costs-the-panel.md) —
`backdrop-filter` at 24.5 ms a frame against a 16.7 ms budget — still
stands on its own evidence. What does not stand is this table's version of
it.

## Eight things the artist grid's scroll is not

Each suppressed in the page, twelve to fifteen runs, against ~29% dropped
and ~23 fps as it ships:

| suppressed | dropped | fps |
| --- | --- | --- |
| nothing (as it ships) | 29.7% | 23.2 |
| the photo in every tile | 50.8%* | 22.7 |
| the circular mask | 49.3%* | 20.9 |
| the 1px inner ring | 50.0%* | 23.0 |
| the per-artist tint | 51.7%* | 23.1 |
| all four together | 49.2%* | 25.3 |
| `content-visibility: auto` on tiles | 52.2%* | 23.0 |
| the same on the letter groups | 52.4%* | 23.2 |
| the list's length: 39,751 px → **6,013 px** | 30.9% | 23.1 |
| the photo request per tile entering view | 27.6% | 23.1 |
| **all 917 `IntersectionObserver`s** | 29.0% | 23.3 |

\* taken before the metric was corrected; comparable with each other and
with the 49.6% they sit beside, not with the corrected figures.

**Not one of them moves it.** Not what is in the tile, not whether
off-screen tiles are rendered, not how long the list is, not the fetching,
not the observers. The grid scrolls at 23 fps with an empty tile and a short
list exactly as it does as it ships.

## What is established

- **Every list scroll on this panel needs main-thread work per frame.** The
  frame reporter says `scroll_state: SCROLL_MAIN_THREAD` on the grid, the
  album pane *and* the rail once it has something to scroll. The scroll
  *input* is handled by the compositor — `InputHandlerProxy::HandleGestureScrollUpdate`
  appears on both — so this is the main thread being needed for the
  **update**, not for the gesture.
- **The cost is not proportional to anything in the list.** Sixth of the
  content, same number. That is the strongest hint available and it points
  away from the list and at whatever the panel does per frame while any
  scroll is in progress.

## What this does not settle

- **The cause.** Eight candidates are gone and the ninth is not named.
- **Whether the still-screen fixes changed the scrolls.** They did not:
  removing the badge pulse and the `width` transition left every scroll
  where it was.
- **Finding 055's table needs re-taking** with the corrected metric and with
  a queue and an album pane that actually scroll. Its *relative* ordering of
  the scrolls may not survive it.
