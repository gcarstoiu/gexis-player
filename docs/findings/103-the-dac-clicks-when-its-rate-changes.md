# Finding 103 — The DAC clicks when its sample rate changes

**Date:** 2026-09-30
**Question:** George heard a pop at the start of a track when skipping between
tracks of different resolutions, through an uploaded streaming renderer. Is
it the renderer, or the device?
**Scope:** the Pi 4 on the second card (`sofa-pi`), HiFiBerry DAC+ HD, full
KMS image 755-era with `phase-13ac` deployed. **Silence only**: `aplay -D
output -f S32_LE -c 2 /dev/zero` at each rate, nothing else holding the card,
0.15 s between runs, as a skip leaves. Listened to by George at the speakers;
nothing was recorded or measured electrically. **Not tested:** another DAC,
music rather than silence, LMS or Spotify changing rate (they reopen the card
the same way, so the same is expected, not heard), whether the driver can mute
across a clock change.

## What the renderer did

At every rate change the renderer stopped the PCM mid-signal and reopened
`output` about 130 ms later at the new rate (88.2 → 44.1 → 96 → 44.1 →
192 kHz, 10:19:01-10:19:31). Same-rate skips reuse the format.

## Silence clicks too

| Run | Sequence (2 s / 4 s each) | Heard |
|---|---|---|
| 1 | 44.1 → 96 → 192 → 44.1 → 88.2 → 44.1 | pops (not counted) |
| 2 | 44.1 → **44.1** → 96 → **96** → 192 → 44.1 | **three** |

Run 2 has five reopens after the first open: two at the same rate, three at a
new rate. Three pops is what a click **per rate change** gives; a click per
reopen would have given five. The count does not say *which* three - that is
inference, and a run of only same-rate reopens would confirm it.

## What it bears on

- **Not the renderer.** Pure silence clicks, so it is the card's reaction to
  a clock change, not a waveform cut or a start without a ramp.
- **It comes with bit-perfect playback** (ADR-0009, ADR-0085): each track
  opens the card at its own rate. A fixed output rate would avoid the clock
  change by resampling, which the player does not do.
- **A driver-level mute** across the clock change is the remaining lever,
  uninvestigated. George, 2026-09-30: *"Record it and let's move on."*
