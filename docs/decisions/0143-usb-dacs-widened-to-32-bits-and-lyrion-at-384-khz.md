# ADR-0143 — USB DACs: widened to 32 bits, and Lyrion at 384 kHz

**Status:** **Accepted** — 2026-10-12. George, on the widening (*"D1.
Agreed"*); the 384 kHz limit is a correction of a measured fault.
**Amends:** [ADR-0009](0009-logical-output-device.md) (no `plug` in the
chain), [ADR-0055](0055-which-output-the-device-plays-to.md) (what an
output's chain is).

## Context

An SMSL USB DAC on sofapi, 2026-10-12 (Finding 120):

- **It takes 32-bit samples only** (`S32_LE`), at every rate from 44.1 to
  768 kHz. 16-bit, 24-bit and packed 24-bit were refused. Squeezelite and
  go-librespot send 32 bits themselves; Bluetooth sends 16 bits and cannot
  convert, and the chain had nothing for it: ADR-0009 allows `plug` only for
  an output that takes no PCM at all (HDMI).
- **Lyrion hands PCM to Squeezelite unchanged up to 384 kHz** (FLAC 44.1 to
  384 kHz, WAV 384 kHz), and **not above**: 705.6 and 768 kHz WAV opened the
  card at 44.1 kHz, played some sixteen times too slow.

Measured the same day on that DAC: ALSA's `type linear` to `S32_LE`, under
the meter and under the software stage, played 16, 24 and 32 bits with no
fault (where the meter over `plug` once aborted, 2026-09-23); and it is exact
- 96,000 random samples at 16 bits and at 24 bits came out as the input
shifted left, none different.

## Decision

1. **A card that takes `S32_LE` and not `S16_LE` gets a widening step**:
   `type linear`, slave format `S32_LE`, between the chain and `hw:`. It pads
   16 and 24 bits to 32, passes 32 untouched and never changes the rate; a
   rate the card lacks still fails loudly. Every other card is as before.
   This is not `plug`, and keeps ADR-0009's reason for refusing it: nothing
   is converted that changes a sample's value.
2. **For a card above 384 kHz, Squeezelite is told the rates Lyrion can
   hand over** - 44.1 to 384 kHz, from the card's lowest - through
   `GEXIS_SQUEEZELITE_OPTIONS` in `/etc/gexis/squeezelite.env`, written by
   the core with `output.conf`. Lyrion then no longer sends a file beyond
   them as something that plays wrong (it refused one served over HTTP;
   Consequences). A card at or below 384 kHz gets no
   option: Squeezelite asks it, as before.

## Consequences

- Bluetooth, and any source sending 16 or 24 bits, plays on a 32-bit-only
  DAC, bit-perfect in value.
- A 705.6 or 768 kHz file from Lyrion no longer plays at the wrong speed:
  measured on files served over HTTP, Lyrion now stops instead of sending it
  (Finding 120, result 6). Whether it converts such a file from its own
  library was not measured. Other sources (Spotify, Plexamp) are not affected
  by this limit.
- The rule reads what the card reports, so it applies to any DAC of the kind,
  USB or not.

## Unverified

Whether Lyrion converts a library file above the told rates. (Bluetooth on
the SMSL: measured, Finding 120 result 8.)
