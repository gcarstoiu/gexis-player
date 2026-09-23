# Finding 051 — The spectrum pipe and the bars have to agree

**Date:** 2026-09-23
**Question:** George, on the panel: *"really jumpy spectrums… the spectrum
is almost flashing because it's too fast. The bars go up and down way too
fast"*, and after the first two attempts at slowing it down: *"spectrum
looks the same as before."*
**Scope:** `gexis`, 2026-09-23, with LMS playing one track at a digital
level nothing attenuates. Measured by reading `/run/gexis/spectrum-peppy.fifo`
the way PeppySpectrum reads it, with PeppySpectrum stopped, at two frame
sizes, twice each, alternating. **Not tested:** other resolutions, and
whether the remaining movement at any smoothing setting looks *good* —
that is George's.

## It was not speed

**I caused it**, the same day, with
[Finding 049](049-the-spectrum-draws-more-bars-than-it-has-room-for.md)'s
fix: the driver started writing a per-skin bar count, 20 to 22, where the
global `size` had been 30.

peppyalsa measures **30** bands and the relay writes them as one 120-byte
record per frame. PeppySpectrum reads `4 * size` bytes at a time and keeps
a read only if it returned exactly that many:

```python
tmp_data = os.read(self.pipe, self.config[PIPE_SIZE])
if len(tmp_data) == self.config[PIPE_SIZE]:
    data = tmp_data
```

**A FIFO carries bytes, not messages.** At `size = 22` that is 88 bytes out
of a stream of 120-byte records, so the kept frame starts 0, 88, 56, 24…
bytes into a record depending on how many had queued since the last
refresh — and **which band each bar is showing changes from one refresh to
the next.**

That is why smoothing did nothing. The bands themselves were already calm:
raising peppyalsa's `smoothing_factor` from 50 to 90 cut their
frame-to-frame movement from **4.8** to **1.0** points out of 100, and 97
took it to 0.3. The bars were not showing the bands.

## Measured

Reading the live pipe exactly as PeppySpectrum does, mean absolute change
per bar between kept frames (0–100 scale):

| frame size | run 1 | run 2 |
| --- | --- | --- |
| 30 bands — matches the record | **0.4** | **0.4** |
| 22 bands — the driver's count | **2.6** | **2.7** |

Six times the movement, from framing alone, on the same audio. The 90th
percentile goes from 1 to 9.

## The fix

**The relay folds its 30 bands down to the number the engine is about to
draw** ([ADR-0056](../decisions/0056-the-spectrum-frame-follows-its-reader.md)),
read from the engine's own `config.txt` — the same file the driver writes
the count into. Each bar gets the **peak** of its group, because a bar on
a spectrum display stands for the loudest thing in its range and averaging
would make the display quieter than the music.

**After, on the same measurement:** reading at 22 gives **0.3 and 0.4** —
the aligned figure.

## What this does not settle

- **How fast the spectrum should feel.** `smoothing_factor` is left at
  **90**, which is a guess at a middle.

  **The time constants first given here were wrong by about a factor of
  two**, and are corrected: they assumed peppyalsa emits a frame per
  512-sample FFT, 11.6 ms at 44.1 kHz. It emits one per ALSA period, and
  `spectrum.c` `break`s out of the sample loop after the first FFT of each,
  discarding the rest. **Counted on the device: 48.6 frames a second, one
  every 20.6 ms.** The filter keeps `f` percent of each band's previous
  value per block, so:

  | `smoothing_factor` | time constant |
  | --- | --- |
  | 50, as shipped | 30 ms |
  | 90, today | 200 ms |
  | 97 | 0.7 s |
  | 99 | 2 s |

  Which is why 97 read as over-smoothed and 99 was nearly frozen. George has now seen 50 aligned, and
  90 and 97 scrambled, so he has not yet seen a correctly framed spectrum
  at any setting but the original.
- **The vertical staircase.** A bar's height is quantised into the
  section's `steps` levels, 12 to 30 over its height. That is the skin
  author's choice and nothing here changes it.
- **Whether the levels should follow the volume**, which George asked about
  in the same message. Not answered here.
