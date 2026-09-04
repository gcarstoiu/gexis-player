# ADR-0012 — Enrichment is renderer-agnostic and additive only

**Status:** Accepted
**Date:** 2026-09-04

## Context

Now playing, artist info and track info must work for every renderer. Metadata
richness is not uniform and never will be: LMS gives full metadata, Spotify
gives artwork but no artist biography, Bluetooth gives AVRCP title/artist/album
with often no artwork and unreliable duration.

Bluetooth is the thinnest input, which is why it forces the design honest. But
this is not a Bluetooth feature — LMS and Spotify need artist biographies too.

## Decision

**One enrichment service, keyed on (artist, album, title, duration), serving
every renderer.**

Rules, each with the UX reason it exists:

- **Never block the now-playing render on network.** Renderer-supplied text
  appears immediately; artwork and biography arrive later. The layout reserves
  artwork space so late arrival does not reflow the screen.
- **Additive only. Never overwrite renderer-supplied text.** A fuzzy match on
  messy AVRCP strings will sometimes be wrong. If matched text replaced supplied
  text, a mismatch would make the screen lie about what is playing.
- **Confidence threshold; below it, show nothing.** A confidently wrong artist
  biography is worse than a blank panel.
- **Cache negative results.** Otherwise every play of an unmatched track
  re-queries.

## Rate limiting

MusicBrainz permits on average **one request per second per IP**, and exceeding
it means all requests receive HTTP 503 until the rate drops — not partial
throttling. A meaningful User-Agent identifying the application is required, and
polling for metadata changes is explicitly discouraged.

Therefore: **a single shared token bucket across the whole service**, a
persistent on-disk cache, and a real User-Agent string. Not per-adapter rate
limiting, which would multiply the request rate by the number of renderers.

## Design consequence for the UI

**Design the now-playing screen for the poorest source, not the richest.**
Artwork, biography and lyrics are progressive enhancement. If the screen is
designed for LMS and degrades, the Bluetooth screen will look broken.

## Sources

MusicBrainz and ListenBrainz Labs for factual artist metadata and relationships.
Structured API lookups are faster and more accurate than a language model for
this, and need no GPU. A local model is reserved for presentation, input
normalisation, translation and multi-source merging.

Spotify's related-artists and audio-features endpoints were deprecated in
November 2024 and are unavailable to new applications, so they are not an option.

## Out of scope

Audio-similarity via local embedding models (LAION-CLAP, MERT, MuQ-MuLan) needs
a batch pass over audio files. Local library is out of scope and the files live
on the LMS server, not the Pi. That work is a separate product operating on the
LMS library, not a feature of the player.
