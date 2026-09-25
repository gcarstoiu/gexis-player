# ADR-0074 — The artist page holds the discography's place while About loads

**Status:** **Accepted and built**, 2026-09-25. George: *"since we know the
height of the right side with the biography, most Popular songs and
discography can't we hold it into place until information is populated?
Otherwise it moves content down once the artist info arrives."*
**Date:** 2026-09-25
**Relates to:** [ADR-0040](0040-what-the-panel-shows-for-an-artist.md) §2
(About and Similar), [ADR-0073](0073-an-artist-page-does-not-wait-for-its-covers.md)
(which made the page arrive before its biography, and so made this visible)

## Context

The artist page draws its discography at once and its About section — the
biography, its licence credit, and Popular — about 1.8 seconds later, when
the lookup returns. Until then the discography sat high and then **was
shoved down 373 px**, measured on five artists:

```
Alan Menken       discography at 105 → 478   (+373)   bio 407, no Popular
ATB               discography at 105 → 478   (+373)   bio 119, Popular 238
```

**The same 373 px for both**, and for every artist tried, because `fitAbout`
clamps the biography to whatever Popular leaves: the region above the
discography has a designed height, not an accidental one.

## Decision

**Reserve that height while About is loading.**

The number is not guessed and not hardcoded: it is the one `fitAbout`
already aims at — the first album card at
`clientHeight - cardHeight * ALBUM_PEEK` — and the discography is on the
page from the first frame, so the shortfall can be measured against it.

A spacer holds the difference, and it exists only while `artistInfo.state`
is `loading`. **If nothing arrives, the page closes up**, which is what
George asked for: *"in the likelihood the info doesn't come then it can
compress, but that is a less likely event."*

| | before | after |
| --- | --- | --- |
| the discography moves | **+373 px down** | **14 px up** |

## The fourteen pixels

**It settles up by 14 px and I could not close that.** Three attempts
failed for the same reason: the reserve is measured *from* the loading
layout and then changes it, so anything added to that layout raises the
measured position and shrinks the reserve by exactly as much. Giving the
licence credit an empty box of its own changed nothing. Recording where the
discography actually came to rest and aiming at that changed nothing either.

The loaded position is settled by `fitAbout` through a rounded `aboutMax`
with a ±4 px tolerance; the reserved one by this arithmetic. They agree to
14 px on a 550 px column and were not made to agree exactly.

**It is consistent** — 14 px on every artist measured, with biographies from
119 to 407 px and Popular from nothing to five tracks — so it is a property
of the layout rather than of the content.

## Consequences

- **The discography stops moving under a finger**, which is the point:
  before, an album tapped at 1.7 s was a different album at 1.9 s.
- **A page whose lookup fails still compresses.** The reserve goes with the
  loading state.
- **One transient frame remains** where the biography renders before
  `fitAbout` clamps it, and the discography is briefly far down the column.
  It predates this and was not changed.
