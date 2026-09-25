# ADR-0074 — The artist page holds the discography's place while About loads

**Status:** **Accepted and built**, 2026-09-25. George: *"since we know the
height of the right side with the biography, most Popular songs and
discography can't we hold it into place until information is populated?
Otherwise it moves content down once the artist info arrives."*
**Date:** 2026-09-25
**Relates to:** [ADR-0040](0040-enrichment-providers.md) §2
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

**The About region is given the height it will have, and keeps it.**

The number is not guessed and not hardcoded: it is the one `fitAbout`
already aims at — the first album card at
`clientHeight - cardHeight * ALBUM_PEEK` — measured while About is still a
skeleton, and the discography is on the page from the first frame to measure
against.

It is a `min-height` on the region itself, not a spacer after it. **What
arrives fills a box that is already the right size**, so nothing moves.

**If nothing arrives, the page closes up**: the height is held while the
lookup is in flight and while what came back has a biography, and dropped
otherwise — which is what George asked for, *"in the likelihood the info
doesn't come then it can compress, but that is a less likely event."*

| | before | after |
| --- | --- | --- |
| the discography moves | **+373 px down** | **it does not** |

Measured on four artists: the discography appears at 478 and stays there,
with no intermediate position at all.

## And the biography fills what is left

Holding the region had a cost that took a third pass to see: `fitAbout`
sized About by measuring the slack between where the first album row sat and
where it should sit — and with the region held, that slack is always zero.
So an artist with **three** popular tracks instead of five got the same
short biography as one with five, and a hole under Popular where the other
two tracks would have been.

**The biography now takes the space itself**, with `flex: 1 1 0` inside the
held region, so the text fills what Popular leaves instead of the space
sitting empty:

| | popular tracks | biography |
| --- | --- | --- |
| Adele | 5 | 119 px |
| Aqua | 5 | 119 px |
| Bausa | **3** | **215 px** |

`fitAbout` no longer measures anything geometric. What remains of it is the
one question geometry cannot answer: **is there more text than the box
shows**, and so should the fade be drawn. `aboutMax` is gone.

## When the metadata does not come

All four forced in the page and photographed. **Every one of them closes the
page up** — the space is held only while an answer is coming, and afterwards
only if what came can fill it:

| | About shows | region | discography sits at |
| --- | --- | --- | --- |
| the network failed | *"Artist details unavailable offline. Your library is unaffected."* + Retry | 88 px | 102 |
| nothing found | *"Nothing found for this artist."* | 52 px | 66 |
| a one-line biography, no Popular | the line | 121 px | 135 |
| Popular but no biography | the message, then Popular | 196 px | 210 |

**The hold is conditional on the biography being able to fill it.** A
one-line life story stretched down 400 px of nothing is the same fault as a
short Popular list leaving a hole, so the question is asked once per artist
— *is there as much text as there is space?* — and the answer decides
whether the space is kept.

**The cost is a compression when the answer is no**: about 400 px, once, at
around 1.3 s, on an artist whose biography cannot fill the page. One of five
in a sample. George, 2026-09-25: *"in the likelihood the info doesn't come
then it can compress, but that is a less likely event."*

## Three wrong answers first, and what they were hiding

**A spacer after the region left 14 px.** Reserving the *gap* between About
and the discography means the gap has to shrink as About fills, and the two
are measured a frame apart. I reported that 14 px as a property of the
layout and stopped. George: *"Are you sure the change is in the panel?
Seeing pretty much the same behaviour."* He was right and the reasoning was
wrong: a residual that reproduces exactly is a clue, not a floor.

**And the thing he was actually seeing was worse than 14 px.** The
biography's clamp was gated on `bioClipped`, which is what `fitAbout`
concludes *after* measuring — so a biography rendered at its **full natural
height**, 1,500 px and more, until the next frame. The discography was flung
down the column and back, for 10–65 ms. It depended on the artist opened
before, which is why one never opened before was worse. The clamp now
applies from the first frame the biography exists; `bioClipped` still
decides the fade, which is a question about the text rather than the space.

## Three more traps in the measuring

- **`fills` starting false compressed the region the instant the lookup
  returned**, so the biography was then measured against the *compressed*
  box — where any text fills it, and so everything held. The region stays
  held until the question has been asked.
- **A box never reports a `scrollHeight` smaller than itself.** Asking
  whether the text is shorter than its box that way always answered no. The
  paragraphs' own height is what is being asked about.
- **`flex: 1 1 0` with nothing to fill collapses to its floor.** Once the
  region stopped being held, the biography kept flexing and was cut to
  64 px. The flex belongs to the held state and is scoped to it.

## Consequences

- **The discography stops moving under a finger.** Before, an album tapped
  at 1.7 s was a different album at 1.9 s.
- **One flex item more in the column**, carrying the column's own 14 px gap
  inside it so nothing looks different.
- **A page whose lookup fails still compresses**, and one with no biography
  at all never holds the space.
