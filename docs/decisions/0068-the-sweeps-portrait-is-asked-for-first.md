# ADR-0068 — The sweep's portrait is asked for first, and the whole list at once

**Status:** **Accepted**, 2026-09-24. George: *"Go for 1 and 2."*
**Date:** 2026-09-24
**Relates to:** [ADR-0059](0059-artist-portraits-in-the-list.md) (which said
fanart first and LMS as the fallback), [ADR-0040](0040-what-the-panel-shows-for-an-artist.md)
§1 (LMS's own plugin), [ADR-0067](0067-only-what-is-on-screen-is-built.md)
(the windowed grid this feeds)

## Context

ADR-0059 settled the order: **fanart first, LMS as the fallback.** The code
does it the other way round. `/library/artist-photos` asks
`artistinfo.photos()` for every id, and only then does `_portrait` replace
the answer with the sweep's fanart portrait — which it does for **625 of 917
album artists, 68 %**.

An artist the LMS plugin has not looked up costs it 500–900 ms upstream, and
a batch is asked concurrently, so **a batch of 20 the panel has never seen
takes 353 ms; one it has takes 5 ms.** Walking the whole library in the
panel's batches of 20 took **35 seconds**; the same ids a second time took
145 ms.

That is what George sees as portraits *"blinking into position"*: scroll
into a part of the alphabet nobody has visited and every screenful waits a
third of a second for work that two thirds of the time was not needed.

**And the panel asks only for what is about to be drawn**, twenty at a time,
discovered by an `IntersectionObserver` as cards come into view — so a card
is always drawn as initials first and becomes a picture afterwards, even
when the answer was already on the device.

## Decision

**1. The sweep's portrait is resolved before LMS is asked.**
`/library/artist-photos` looks each id up in the sweep's store first, and
asks `artistinfo.photos()` only for the ones it did not answer. The 68 %
cost a name lookup and a string; the rest are unchanged.

**2. The panel asks for the whole list at once, in the background.**
When the artist list arrives, the panel fetches every portrait URL it does
not already hold, in batches of 50, yielding between them. Warm, that is
145 ms for 917 artists. The grid then draws each card with its `src`
already, instead of initials that become a picture.

- **Batches of 50, not 80** — the daemon caps a request at `PHOTO_BATCH`
  (80), and 50 leaves room to raise the cap without changing the panel.
- **It yields between batches**, so filling the map never blocks a scroll.
- **It asks only for what it lacks**, so opening the grid again costs
  nothing.

## Consequences

- **A cold library still pays LMS**, for the ~288 artists fanart has no
  picture for: about 15 batches at a third of a second, in the background,
  once. It was 35 seconds on the critical path of scrolling.
- **The per-card observers stay.** With the grid windowed there are a few
  dozen, not 917, and they remain the route for an artist the prefetch has
  not covered — a new one, or one whose id LMS renumbered on a rescan
  ([Finding 029](../findings/029-what-lms-answers.md) §4).
- **This does not prefetch the images**, only their URLs. The bytes come
  from Chromium's own cache after the first sight of each — measured: a
  reopened grid makes **zero** network requests, because LMS serves the
  proxy with `Cache-Control: max-age=31536000`.
