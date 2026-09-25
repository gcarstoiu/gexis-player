# ADR-0081 — The daemon owns the cover it found

**Status:** Accepted
**Date:** 2026-09-25
**Relates to:** [ADR-0012](0012-enrichment-additive-only.md) (a found cover
fills a hole, it never replaces), [ADR-0014](0014-nowplaying-and-peppy-are-distinct.md) (how
the meter is told what is playing), [ADR-0040](0040-enrichment-providers.md)
§2 (the cover providers),
[ADR-0080](0080-a-cover-is-matched-on-a-title-both-catalogues-agree-on.md)
(finding more of them), Phase 9 criterion 3

## Context

George, 2026-09-25, reviewing the panel: *"the Bluetooth the album art is not
loaded into peppy once available."*

A Bluetooth track arrives over AVRCP with an artist, an album and a title, and
**no cover**. The cover providers find one. Now Playing shows it. PeppyMeter
does not, ever, however long it plays.

The reason is where the fallback lives. **Now Playing does it in the browser:**

```js
const supplied = metadata?.artwork;
if (supplied && supplied !== failedArtwork) return supplied;
const found = artistInfo.enrichment?.album_art;
```

Enrichment is a route the panel pulls (`GET /enrichment`, deliberately not
part of `/state`), and the panel resolves the two in its own head. Nothing
else in the system ever learns the answer: `state.metadata.artwork` stays
`null`, so `nowplaying.json` carries `null`, so the meter draws nothing. The
moOde-compatible file (`metadata_file.py`) is blank for the same reason.

## Decision

**When a renderer supplies no cover and one is found, the daemon publishes it
as that track's artwork.**

- `StateStore` gains a found-artwork slot per renderer, applied in the `state`
  property **only where `metadata.artwork` is `None`**, and **only for the
  track it was found for** — matched on artist, album and title, so a cover
  never outlives the track it belongs to.
- The daemon asks for it itself, on the state change, rather than waiting for
  a panel to ask. One lookup per track that has no cover, through the same
  `EnrichmentService` and the same cache the panel's route uses, so the
  panel's own request is answered from the cache rather than repeating it.
- The renderer's own artwork always wins, and a renderer that later supplies
  one replaces the found one. **ADR-0012 unchanged**: this fills a hole.

Now Playing keeps its client-side fallback. It is redundant for this case once
the daemon publishes, and it still covers the one the daemon cannot see — an
artwork URL that fails to *load* in the browser.

## Rationale

### The panel is the wrong owner

PeppyMeter is a separate process with no client for `/state` — that is why
ADR-0014 exists and why the daemon writes it a file. Making its artwork depend
on a Chromium page being alive, un-occluded and un-throttled inverts that: the
meter is raised *over* the panel, which is exactly when the browser is most
likely to be treated as hidden.

And it is not only the meter. Anything reading the published state — the moOde
file, a phone, a future client — sees `artwork: null` for a track whose cover
this device has in hand. **One answer, in the state, is what "the daemon
publishes what is playing" means.**

### Asked on the state change, not on the panel's request

The alternative was to have `/enrichment` write back what it found: no new
lookups, a handful of lines. Rejected because it keeps the dependency and only
hides it — the meter would get a cover exactly when a panel happened to ask,
which is not a behaviour anybody could describe.

Asking directly costs one lookup per coverless track, which is what
`artwork_lookup` already sanctions (George, 2026-09-24: *"automatic way for
sure"*). The providers are behind the same gates and the same cache; a track
played twice costs nothing the second time.

### Matched on the track, not just the renderer

A found cover held per renderer and applied blind would attach to the *next*
Bluetooth track for as long as it took the next lookup to answer — a wrong
cover on screen, which ADR-0012 ranks as worse than none. Keyed on the track,
a stale entry simply does not apply.

## Consequences

- PeppyMeter, the moOde file, the phone and the panel all show the same cover,
  and stop disagreeing about whether one exists.
- A Bluetooth track's cover appears a second or two after the track starts —
  the lookup's latency. It cannot be otherwise: nothing knows it at track
  start.
- `state.metadata.artwork` is no longer strictly "what the renderer said". It
  is "the cover for this track", which is what every reader already treated it
  as.

## What this does not settle

- **The artist image.** The same argument applies to `artist_image` and the
  same machinery would carry it, but PeppyMeter draws a cover, not a portrait,
  and nothing has asked for it. Not done on speculation.
- **How long the lookup takes in practice.** Measured per track, not here.
