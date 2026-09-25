# ADR-0075 — The sweep's portraits serve every renderer

**Status:** **Accepted and built**, 2026-09-25. George, on being told the
artist tab looks a portrait up online once per artist although the sweep
already holds it: *"Agreed to the improvement. Go for it."*
**Date:** 2026-09-25
**Relates to:** [ADR-0059](0059-artist-portraits-in-the-list.md) (the sweep
that gathered them), [ADR-0068](0068-the-sweeps-portrait-is-asked-for-first.md)
(the same correction, for the library's grid),
[Finding 030](../findings/030-what-fanart-answers.md) (fanart's own request
that it not be asked twice),
[Finding 036](../findings/036-a-provider-that-could-not-be-asked-has-not-answered.md)
(why "could not ask" is never cached)

## Context

Two stores held the same fact:

| | rows |
| --- | --- |
| the sweep — `notes`, `fanart-artist`, keyed by **folded artist name** | 845 |
| the enrichment cache — `enrichment`, provider `fanart`, keyed by track | 252 |

The library's grid reads the first (ADR-0068). **Now playing's artist tab
and the artist page read the second**, and filled it one artist at a time as
somebody happened to look at them: **864–1,432 ms** the first time each
artist was seen, and 5–59 ms after.

They agreed on the answer — 40 artists checked, 40 the same picture — so
this was duplicated work rather than an inconsistency. And the sweep's key is
a *name*, which every renderer has, while the enrichment cache's route to a
portrait runs through a MusicBrainz id the library resolves.

## Decision

**One lookup, `swept_portrait_of(name, size)`, and every caller uses it.**

- **The artist tab and the artist page take the sweep's portrait** when it
  has one, over both LMS's plugin and fanart's own answer.
- **What is playing does too**, whatever is playing it. The key is the
  folded artist name, so a Spotify or Bluetooth track by an artist the sweep
  has been over shows its picture from this device.
- **And fanart is not asked at all** when the sweep can answer:
  `for_track(..., omit=("fanart",))`. `FanartArtistImage` contributes
  nothing but the portrait, so there is nothing left to want from it — and
  Finding 030 records fanart asking not to be asked twice.

| first view of an artist nobody had looked at | median | fastest |
| --- | --- | --- |
| **the sweep has them** | **1,013 ms** | 25 ms |
| the sweep does not | 1,850 ms | 1,024 ms |

## What this does not fix

**The artist tab is still about a second on its first view**, because the
*biography* waits on Wikipedia and ListenBrainz. Only the picture became
local. Making the tab itself fast would mean delivering the portrait
separately from the text, the way the artist page already asks for its own
portrait through `/library/artist-photos`. Not done.

**And one artist stays slow on every view.** Kraftwerk answered in 4,007 ms
and then **2,348 ms again**, because a provider that could not be asked is
never cached (Finding 036) and so is asked every time. That is the same
shape as [ADR-0069](0069-what-a-lookup-cost-is-remembered.md)'s thirty
seconds, in the providers rather than in LMS's plugin, and it is not
addressed here.

## Consequences

- **Three callers, one function.** The grid, the artist page and what is
  playing all answer from the same store through the same lookup.
- **A renderer with no LMS library still gets portraits** for artists the
  library happens to know. A Spotify artist who is not in the library is
  unchanged: fanart is asked, once, and cached.
- **The sweep is now worth more than it was.** It was gathered for the
  grid; it answers everywhere.
