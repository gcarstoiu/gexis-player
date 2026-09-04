# ADR-0014 — Now playing and the Peppy screen are distinct screens

**Status:** Accepted
**Date:** 2026-09-04

## Context

The Gelo5 1280x800 skins all carry `config.extend = True` with a full screen
layout: album art position and dimensions, title/artist/album text positions
with font weights, sample rate, remaining time, source-type badge, colours and
four font sizes.

Seeing that, it was briefly concluded that the Peppy screen and the now-playing
screen were the same screen and the requirements collapsed into one. **That was
wrong** and is recorded here so it is not re-derived.

## Decision

**Two screens, different roles, one state source.**

| | Now playing | Peppy screen |
|---|---|---|
| Role | interactive | display-only |
| Controls | transport, artist info, queue | none |
| Varies by renderer | yes — capability-driven | no — identical always |
| Entered from | navigation | button on now playing, or idle timeout |

**Now playing is capability-driven.** LMS gives full transport plus queue.
Spotify Connect gives transport, with the queue living in the phone app.
Bluetooth gives AVRCP with per-device command support. Controls that will not
work are hidden or greyed. A next button that silently does nothing is worse
than no next button.

**The Peppy screen is capability-blind.** Metadata plus levels, nothing else.

## What survives from the rejected merge

The load-bearing observation was correct and is retained: **the skin renderer
needs the playback model, not just level data.** A visualisation data service
alone is not sufficient. This is why the skin renderer lives in the presentation
layer, where the state WebSocket already exists, rather than being a second
client of the core in another language.

## The skin format defines the metadata contract

Across the 71 skins inspected, the `playinfo.*` keys require:

```
title  artist  album  artwork  sample rate  remaining time  source type
```

Album is optional — positioned in 44 of 71. That set is the minimum every
renderer adapter must supply.

**Where a field is absent, the skin renderer blanks that region, never the
screen.** Bluetooth supplies no artwork and unreliable duration, so this path is
exercised routinely rather than exceptionally.

## Consequence for phasing

The Peppy screen is the *simpler* of the two, because it is capability-blind. It
exercises the normalised playback model end to end without dragging in
per-renderer capability negotiation. It is therefore the better early target and
is scheduled before full now-playing controls.
