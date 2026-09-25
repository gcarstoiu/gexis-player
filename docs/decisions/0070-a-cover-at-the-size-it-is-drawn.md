# ADR-0070 — A cover is published at the size it is drawn

**Status:** **Accepted and built**, 2026-09-25. George: *"Check as well all
places where thumbnails are shown... Perform a thorough check and optimise
as much as possible."*
**Date:** 2026-09-25
**Relates to:** [Finding 066](../findings/066-every-picture-the-panel-draws.md)
(the survey), [ADR-0068](0068-the-sweeps-portrait-is-asked-for-first.md)
(the portraits' own route)

## Context

`TrackMetadata.artwork` is 500 px because now playing's well is 500 px. Two
other places draw the same cover at **64**: the mini strip, which is on
every library screen, and now playing's release tab.

A 500 px cover is 52,328 bytes and 250,000 pixels to decode. The same cover
at 100 px is 3,817 bytes and 10,000 pixels. The mini strip was paying the
first to draw the second, on every track, on every screen.

## Decision

**The adapter publishes the cover twice.** `artwork` stays 500 px;
`artwork_small` is the same cover at `ARTWORK_ROW` (100 px), which is
already the size queue rows ask for — so **one cached picture serves the
rows, the mini strip and the release tab**.

- **A renderer with only one size leaves it `None`** and the places that
  want it fall back to `artwork`. A stream's artwork is whatever the station
  published and has no second size, so it is `None` there.
- **100, not 64.** 64 would be a closer fit and a second cache entry per
  album. Sharing the rows' size is worth 1.6 KB.

## Consequences

- **The mini strip fetches 3.8 KB instead of 52 KB** and decodes 10,000
  pixels instead of 250,000, on every track change.
- **One more field on `TrackMetadata`**, which every renderer publishes and
  only LMS fills. The alternative — a second metadata shape for the small
  places — is worse for one string.
- **The panel does not rewrite URLs.** It was tempting to derive the small
  URL from the large one by string surgery; fanart's and LMS's URLs have
  different shapes and the daemon already knows which it built.
