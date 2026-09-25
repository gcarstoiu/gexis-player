# Finding 073 — The cover that never reached the meter

**Date:** 2026-09-25
**Question:** George, 2026-09-25: *"the Bluetooth the album art is not loaded
into peppy once available."* Where does it stop?
**Scope:** `gexis`, core rsynced from `phase-8-plan`. The track is
**synthetic** — a throwaway hook in the deployed daemon published a coverless
track as if Bluetooth had sent it, because a phone cannot be scripted. It
drives the real chain from `set_metadata` onwards: the real subscribers, the
real providers, the real MusicBrainz, the real `nowplaying.json`. **The
Bluetooth adapter itself is not exercised.**

## Where it stopped

`state.metadata.artwork` is `null` for a Bluetooth track and stays `null`.
The cover is found — Now Playing shows it — because **Now Playing resolves it
in the browser**:

```js
const supplied = metadata?.artwork;
if (supplied && supplied !== failedArtwork) return supplied;
const found = artistInfo.enrichment?.album_art;
```

`/enrichment` is a route the panel pulls, deliberately not part of `/state`.
So the answer existed only inside one Chromium page. `nowplaying.json` is
written from the published state, so PeppyMeter drew nothing; the
moOde-compatible file was blank for the same reason.

## What the fix had to learn on the device

**The first attempt published nothing, and the journal said why:**

```
12:30:37  enrichment: coverart is still going; answering without it
```

`for_track` answers with what it has after its own wait and lets a slow
provider finish behind it, caching the result. The daemon asked once, got
nothing, and never asked again — so the cover was sitting in this device's
cache within seconds and the meter still drew none. **The panel already looks
back twice for exactly this reason** (`enrichment.js`); the daemon now does
too — three looks, six seconds apart.

Without that, the fix would have been the panel's fallback all over again,
one layer down.

## After

Synthetic Bluetooth track, *Sting / 57th & 9th (Deluxe Edition) / Petrol Head*:

```
+10s  artwork: http://coverartarchive.org/release/116c4bbb-…/31140729592-500.jpg
+20s  artwork: …same
+30s  artwork: …same
+40s  artwork: …same

12:36:09  state: found a cover for Petrol Head - http://coverartarchive.org/…
```

`nowplaying.json` carries it, which is what PeppyMeter reads.

## What this did not test

- **A real Bluetooth track.** The adapter's own path from AVRCP to
  `set_metadata` is unchanged by this work and untested here.
- **PeppyMeter drawing it.** The file is what the daemon owes it; whether the
  meter picks a changed `artwork` up mid-track is the driver's business and
  was not watched on screen.
- **The daemon looking one up with no panel running.** The panel was up
  throughout, and its own `/enrichment` request warmed the same cache. What is
  shown above is that the daemon *publishes* it; that it would also *find* it
  alone rests on the look-back, which was observed working but not isolated.
- **Timing on a cold cache.** One track, one lookup.
