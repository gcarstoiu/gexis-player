# ADR-0073 — An artist page does not wait for its covers, and the grid keeps its place

**Status:** **Accepted and built**, 2026-09-25. George: *"Opening an artist
from the artist grid is somewhat slow especially on cold cache... Also the
position in the artist grid should be remembered when navigating in and out
artists."*
**Date:** 2026-09-25
**Relates to:** [ADR-0067](0067-only-what-is-on-screen-is-built.md) (the
windowed grid this scrolls), [ADR-0068](0068-the-sweeps-portrait-is-asked-for-first.md)
(the portraits, which are fetched the same way for the same reason)

## Opening an artist

`loadArtistAlbums` awaited the first **twelve album covers** — downloaded
and decoded — before returning, so the page could "arrive whole". For an
artist nobody had opened, that was the whole wait:

```
artists/7529/albums   sent 87 ms, done 120 ms
the page appears      2,516 ms
```

**The discography arrives in 33 ms and the page took two and a half
seconds.** Warm, with every cover already in Chromium's cache, the same code
cost about 120 ms — which is why it looked harmless.

**The covers are now started and not waited for.** They are still asked for
in `loadArtistAlbums` rather than left to the page's `<img>` tags, so they
are in flight while the page is built.

| an artist nobody had opened | discography | the page appears |
| --- | --- | --- |
| Apocalyptica | 113 ms | **213 ms** |
| Tony Bennett feat. The Count Basie Orchestra | 126 ms | **172 ms** |
| Toni Braxton | 111 ms | **189 ms** |

The page now follows its data by 60–100 ms.

## The grid keeps its place

`use:fromTop` put every list back at the top whenever the page changed, so
going into an artist and back out again lost where you were.

- **The grid remembers where it was left**, saved from the scroller the
  component already watches rather than a second listener on it.
- **The library root forgets.** Opening Artists from the home screen is a
  different journey and starts at the top, where the A's are. Only going in
  and out of an artist holds the place — which is what was asked for.

Measured: scrolled to 730, opened an artist, came back — **730**. Home →
Artists — **0**.

## Consequences

- **A cold artist page draws its covers into empty wells** over the second
  that follows. That is the trade, and it is the same one ADR-0065 and
  ADR-0067 make: what is on screen is worth more than what is complete.
- **Only the artist grid remembers.** The browse panes and a playlist still
  open at the top; nobody has asked otherwise and each is a decision.
- **The memory is cleared at the root**, so it never outlives the reason for
  it, and a rescan cannot leave it pointing at a place that no longer means
  anything.
