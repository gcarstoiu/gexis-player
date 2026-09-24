# Finding 063 — The panel builds every row before it draws one

**Date:** 2026-09-24
**Question:** George: *"What is still slow is loading the artist
navigation. A few seconds of dead time"*, and *"loading a playlist of 400
tracks was quite slow"*.
**Scope:** `gexis`, 2026-09-24, ADR-0060 and ADR-0061 both live, music
playing. Timings from the tap to the rows existing in the DOM, with
Chromium's own CPU profiler running. One library, one device. **Not
measured: a phone.**

## Neither of them is the daemon

| | the daemon answers in | the panel takes |
| --- | --- | --- |
| artist grid, 917 cards | **12.8 ms** | **1939 ms** |
| playlist, 467 tracks | **122 ms** | **1407 ms** |

Where the panel's time goes, by self time in the profile:

| artist grid | | playlist |
| --- | --- | --- |
| 952 ms | engine-side DOM and style | 851 ms |
| 408 ms | Svelte's render loop | — |
| 137 ms | tearing down the screen being left | 105 ms |
| 42 ms | `cloneNode` | 23 ms |
| — | waiting on the fetch | 336 ms |

**Both screens build every row before they draw any of them**, at roughly
two to three milliseconds a row. 917 cards is 1.9 seconds of it; 467 rows
is 1.4.

## What it is not

- **Not the artist photos.** `/library/artist-photos` answers a batch of 20
  in 4–11 ms, and 119 of 120 come from ADR-0059's sweep rather than from
  LMS. An earlier reading of the code predicted the LMS plugin would be
  asked first and block; it is not asked at all, because `artistinfo` has
  them in its own store.
- **Not scrolling.** Since ADR-0061 the grid scrolls at 60 frames a second
  with all 917 cards present ([Finding 062](062-the-two-changes-together.md)).
  Having the rows is cheap; **making** them is not.
- **Not the list being fetched twice.** `artistsCached` serves the
  remembered list and refreshes behind it.

## What it means

The cost is proportional to the number of rows, and the panel pays all of it
before the first pixel. Anything that draws a screenful first and the rest
afterwards turns 1.9 seconds of nothing into about a fifth of a second of
something — the remainder keeps costing what it costs, but off the critical
path.

**Two ways to do that, and they are not the same size.** Drawing in chunks
keeps every existing behaviour and changes when work happens. Virtualising
changes what exists in the DOM at all, and the A-Z rail's `jumpTo` reads the
DOM for the group it is jumping to.

## What this does not settle

- **Which fix.** That is ADR-0065 and George's call.
- **The teardown.** 105–137 ms of leaving a screen was measured and not
  investigated.
- **Where the playlist's 336 ms of waiting goes.** The daemon answers in
  122 ms, so roughly 200 ms is unaccounted for and was not chased.
