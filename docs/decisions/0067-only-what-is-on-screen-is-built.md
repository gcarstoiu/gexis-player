# ADR-0067 — The long lists build only what is on screen

**Status:** **Accepted**, 2026-09-24. George: *"Can you do a proper thorough
investigation on what is happening and how to get those loading times down.
Right now the user experience is not yet there. The artists and browse
should be nearly instantaneous."*
**Date:** 2026-09-24
**Relates to:** [Finding 064](../findings/064-the-count-is-the-cost.md) (the
measurement that chose this), [ADR-0065](0065-long-lists-are-built-a-screenful-at-a-time.md)
(which this replaces for these two lists),
[ADR-0038](0038-library-and-radio-on-the-panel.md) §1a (the letter groups)

## Context

[ADR-0065](0065-long-lists-are-built-a-screenful-at-a-time.md) moved the
building behind the first paint, which took the artist grid from 1939 ms of
nothing to 270 ms. **The work did not go away.** Opening the grid still
blocks the main thread for **1255–1358 ms**, in six tasks of 300–443 ms
each, and a person using the panel in that second feels every one of them.

[Finding 064](../findings/064-the-count-is-the-cost.md) took a card apart:
with its photo gone, its tint gone and all 917 `IntersectionObserver`s gone,
it costs the same. **The cost is the elements existing** — about 1.3 ms
each, to create, style and lay out.

The grid's own CSS has carried the answer since 2026-09-18: *"All 917 cards
are laid out; if that proves too slow, the answer is rendering only the rows
on screen."*

## Decision

**Render the rows in the viewport and a screen either side of it; hold the
rest open with a spacer.**

- **The artist grid windows by letter group**, not by card. A group's height
  is arithmetic — its header, plus `ceil(artists / 6)` rows of cards and the
  26 px between them — so the whole scroll height is known without building
  anything. A viewport shows one or two of 27 groups.
- **The heights are measured, not assumed.** One header and one card are
  read from the DOM after the first render, because a card's height depends
  on the panel's width through `aspect-ratio: 1` in a six-column grid.
- **The browse screen's artist pane windows by row**, which is the simple
  case: one height, 917 of them, a 250 px window.
- **The A-Z rail no longer reads the DOM.** `jumpTo` had to finish building
  the grid before it could find the group to scroll to
  ([ADR-0065](0065-long-lists-are-built-a-screenful-at-a-time.md)); with the
  layout known it is arithmetic, and lands on a group that does not exist
  yet.
- **A passive scroll listener, throttled to one read per frame**, and the
  rendered range only changes when the window moves past a group. The scroll
  itself stays composited (ADR-0061).

## What it did

| opening the artist grid | before | **windowed** |
| --- | --- | --- |
| screen swapped | 145–206 ms | 134–177 ms |
| painted | 268–375 ms | **202–243 ms** |
| settled | ~1900 ms | **505–545 ms** |
| **main thread blocked** | **1255–1358 ms** | **0–62 ms** |
| longest single task | 295–443 ms | **0–62 ms** |
| cards built | 918 | **69** |

| the browse pane | before | **windowed** |
| --- | --- | --- |
| painted | 188–226 ms | **176–207 ms** |
| main thread blocked | 273–523 ms | **0–63 ms** |
| rows built | 917 | **24** |

**And the scrolls kept their frames**: 59.7 drawn a second on the grid,
58.2 on the browse pane, 59.0 on the queue rail, 0.00 % dropped — the same
as [Finding 062](../findings/062-the-two-changes-together.md) measured
before any of this. The scroll listener costs nothing measurable.

**Checked, because a windowed list can be fast and wrong:**

- The grid's scroll height computes to **39,801 px** against the 39,751 the
  full list measured — 0.13 % out.
- **Every A-Z jump lands** with the group's header within 7 px of the top,
  on a group that does not exist until the jump.
- The end is exactly the end: `scrollTop` 39,176 plus a 600 px window is the
  39,776 scroll height.
- The pane computes **43,110 px** against 43,108. It was 894 px short until
  the row *pitch* was measured rather than the row height: `.pane__list` is
  a flex column with a 1 px gap, so 917 rows are 917 px taller than 917 row
  heights.

## What this costs

- **A scroll listener on a panel that just got its frames back.** It is
  passive, reads two numbers, and is coalesced into one
  `requestAnimationFrame` per frame. **Measured, not assumed: the scrolls
  are unchanged.**
- **A wrong height is a broken scrollbar.** The measurement happens once per
  layout; a resize re-reads it. The panel is a fixed 1280×800, so this is
  one shape in practice and the risk is in the code rather than in use.
- **Two mechanisms for long lists** until the rest catch up: these two are
  windowed, a playlist still builds a screenful at a time
  ([ADR-0065](0065-long-lists-are-built-a-screenful-at-a-time.md)) and paints
  in 104 ms, and the queue rail builds everything.

## Alternatives

- **Keep ADR-0065 and make cards cheaper** — measured and rejected: five
  variants, none moved it (Finding 064).
- **Grow on scroll instead of windowing** — simpler, and the A-Z rail
  defeats it: jumping to W would build everything up to W.
