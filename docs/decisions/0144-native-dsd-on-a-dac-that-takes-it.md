# ADR-0144 — Native DSD on a DAC that takes it

**Status:** **Accepted** — 2026-10-12. George, reopening
[ADR-0117](0117-dacs-beyond-the-two-on-the-bench.md) decision 4 (*"D2. Now.
Before"* - before the first public release).
**Amends:** ADR-0117 decision 4 (DSD postponed), ADR-0143 (the chain to a
32-bit-only card), ADR-0127 (what the volume type decides).

## Context

ADR-0117 postponed DSD: the Pi's I2S carries PCM only, so a HAT can take DSD
only as DoP, and no board on the bench decoded it. An SMSL USB DAC on sofapi
(Finding 120) takes **native DSD** - `DSD_U32_BE`, DSD64 to DSD512 - and
sofapi's Squeezelite is built with `-D`. Measured the same day:

- straight to `hw:`, native DSD opens the card at the rate given;
- through the player's chain it **aborted**: the visualiser's scope read
  alsa-lib's 16-bit copy of the stream, which alsa-lib leaves unset for a
  format it cannot convert (`pcm_meter.c`, `s16->buf_areas`);
- the widening step (ADR-0143) takes PCM only, and the software stage cannot
  attenuate DSD.

## Decision

1. **Native DSD is used when the volume is Fixed and the card reports a DSD
   format** (`DSD_U32_BE`, `_U32_LE`, `_U16_BE`, `_U16_LE`, `_U8`, in that
   order of preference). Squeezelite then runs with `-D :<format>`, through
   `GEXIS_SQUEEZELITE_OPTIONS` (ADR-0143): Lyrion sends DSD files as DSD and
   Squeezelite plays them unconverted. In every other case - Software or
   Hardware volume, a HAT, HDMI - nothing changes: a DSD file is converted to
   PCM as before.
2. **Squeezelite's chain (`output_wait`) goes straight to the card when DSD
   is on**: no widening step, no software stage (Fixed has none). Squeezelite
   sends 32-bit PCM itself. The chain every other source uses (`output`)
   keeps the widening, so Bluetooth still plays.
3. **The meter stays in both chains, and peppyalsa draws nothing from DSD**
   (`peppyalsa-skip-non-pcm.patch`, package `-4`): it reads levels only for
   the formats alsa-lib's 16-bit copy converts - its own list, because
   `snd_pcm_format_linear()` calls DSD linear (DSD formats count as unsigned),
   which let a first version of the guard through to the same abort.
4. **A change of volume type writes the output again** - Hardware to Fixed
   included, which used to restart the renderers only - so the options and
   the chain follow it.

## Consequences

- DSD plays bit-perfect on such a DAC, at full level (Fixed): the amplifier
  sets the volume, as Fixed already says. The visualiser is still during DSD.
- With a DAC above 384 kHz, Squeezelite is told rates up to 384 kHz
  (ADR-0143), which covers DSD64 to DSD256 in `u32` (88.2 to 352.8 kHz);
  DSD512 (705.6 kHz) is converted.
- No setting: whether DSD is native follows the volume type and the card. The
  Volume row's Fixed note says so where the card takes DSD.

## Unverified

A DSD file from a Lyrion *library* (measured: generated DSF files streamed
over HTTP, DSD64 to DSD256, Finding 120 result 7); Hardware volume in DSD on a card with a control of its own (excluded: not
measured); DoP for I2S boards (still postponed).
