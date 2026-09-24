# ADR-0065 — A long list is built a screenful at a time

**Status:** **Accepted and built**, 2026-09-24. George: *"Do 1."*
**Date:** 2026-09-24
**Relates to:** [Finding 063](../findings/063-the-panel-builds-every-row-before-it-draws-one.md)
(the measurement), [ADR-0061](0061-the-kiosk-does-not-render-subpixel-text.md)
(which made having the rows cheap),
[ADR-0063](0063-the-queue-is-as-long-as-lms-says.md) (a queue that can now
be 2500 rows)

## Context

The artist grid took **1939 ms** to appear and a 467-track playlist
**1407 ms**, while the daemon answered both in 12.8 ms and 122 ms. The panel
built every row before drawing any of them, at two to three milliseconds a
row.

**The rows are not the problem; the moment is.** Since ADR-0061 the grid
scrolls all 917 cards at sixty frames a second. Having them costs nothing.
Making them, all at once, before the first pixel, costs two seconds.

## Decision

**Draw a screenful, then keep building in the background.**

`lib/chunks.svelte.js` holds one small thing: a count that starts at **140**
rows and grows by **160** per animation frame until it reaches the list's
length. Three lists use it — the artist grid, the browse screen's artist
pane (the same 917 album artists) and a playlist's tracks.

| | before | after |
| --- | --- | --- |
| artist grid, first row | 1939 ms | **264 ms** |
| artist grid, all 917 | — | 1798 ms, behind the first paint |
| playlist, first row | 1407 ms | **312 ms** |
| playlist, all 467 | — | 887 ms |
| a three-row screen, for the floor | — | 147 ms |

- **The count is per list and reset by its length changing**, so opening a
  different playlist starts again at a screenful.
- **The A-Z rail finishes the grid before it jumps.** `jumpTo` reads the DOM
  for the group it is scrolling to, and cannot scroll to a group that has
  not been built. Measured: 350 ms after opening, the grid holds 460 cards
  up to "K"; tapping a late letter completes all 917 and lands correctly.
- **The grid and the browse pane share one count.** They draw the same list
  and are never on screen together, so the second to open is already whole.
- **It reads the total and nothing else.** An effect that also read its own
  count would wake itself — LESSONS 31, where exactly that stopped the panel
  answering — so the growing count is mirrored in a plain variable and the
  reactive state is only ever written.

## Consequences

- **A list is briefly shorter than it will be**, so its scroller grows for
  the first second or so. Dragging it immediately works; dragging it to the
  very end within that second arrives at a moving floor.
- **This does not make a list cheaper**, only later. A 2500-track queue
  would still cost what ADR-0063 warns it costs — it would simply be
  spread out. **The rail is not chunked**: nobody has loaded a queue long
  enough to need it, and it is the one list where the rows carry artwork
  that LMS must serve.
- **Virtualisation is the other answer and remains unbuilt.** It would make
  the cost constant rather than deferred, and it would have to be taught
  about the A-Z rail, scroll restoration and the per-tile photo observers.
  This was chosen because it keeps every behaviour the panel already has.
