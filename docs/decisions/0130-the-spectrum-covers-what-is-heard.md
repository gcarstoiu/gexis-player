# ADR-0130 — The spectrum covers what is heard: 50 Hz to 16 kHz at every rate

**Status:** **Accepted** — George, 2026-10-08: *"Whenever I use a spectrum
skin, I rarely see any movement on the last 2 bars on the right."* On the
proposal: *"Use 16khz and for sure improve the bass detail"*, and on the
treble lift, *"add it"*.
**Amends:** [ADR-0011](0011-meter-data-three-transports.md) (what the 30
bands measure, not how they travel) and the peppyalsa build of
[ADR-0107](0107-our-parts-as-debian-packages.md) (a second patch).
**Evidence:** [Finding 117](../findings/117-what-the-spectrum-bars-measure.md).

## Context

peppyalsa measures 30 bands; a skin draws about 20 bars, each the peak of one
or two bands (`meters.resample`). Upstream spaces the bands logarithmically
from the second bin of a 512-point FFT to the Nyquist frequency, whatever the
sample rate. Finding 117 measured what that gives:

- at 44.1 kHz the last bar holds 15-22 kHz and the one before it 12.7-15.2
  kHz, which recordings barely reach. They read zero 36-40 % of the time,
  against 0-3 % for the middle bars;
- at 96 kHz the last two bars hold 27-48 kHz and **never move**;
- the bass has one bar: 512 points at 44.1 kHz are 86 Hz a bin, so the first
  bar is 86-172 Hz and nothing below 86 Hz is shown.

## Decision

1. **The bands span 50 Hz to 16 kHz, log-spaced, at every sample rate.** Below
   a 33.7 kHz rate the top comes down to 95 % of Nyquist.
2. **The FFT is sized to the rate, about 10.8 Hz a bin**: 4096 points at 44.1
   and 48 kHz, 8192 at 88.2 and 96 kHz, 16384 at 176.4 and 192 kHz. It runs
   over the newest samples, kept between updates, so a frame is still made
   at every meter update (50 a second), as before. A band narrower than a bin
   reads the bin it sits in.
3. **A lift of 3 dB per octave above 1 kHz**, nothing below. Recordings carry
   less energy the higher the pitch, and the lift brings the top bars to move
   as often as the middle ones without touching the bass.
4. **The level mapping is upstream's** (`log10(y) / 4.82`, smoothing 90), and
   band sums are divided by the FFT size as upstream's are. A single tone,
   such as a bass note, then reads the level it did before. The display
   overall sits a little higher (the loudest frame in the test went from 69
   to 75 out of 100), because a band of noise sums more bins than it did.
   First built dividing also by `sqrt(input_size / 512)`, which keeps noise
   where it was; on guestpi that held the bass bars at zero a third of the
   time, so it was dropped the same day (Finding 117).
5. **Fixed in the patch, not settings.** These are what a spectrum display
   means, not a preference; no ADR-0022 row.

## How

A second patch, `image/stage-gexis/00-alsa/files/peppyalsa-spectrum-bands.patch`,
applied after `peppyalsa-one-write-per-frame.patch`. `gexis-peppyalsa` goes to
revision `-2`, since its upstream version does not change (LESSONS 53). The
pipe still carries 30 bands, so nothing reading it changes.

## Limits

- The middle of the display moves slightly: the bars that were single 86 Hz
  bins now cover proper ranges, and noise-like sound reads a little higher.
- The CPU cost grows with the FFT; Finding 117 measures it on a Pi 4.
- A skin whose artwork prints frequencies under its bars would now be wrong.
  The corpus was not searched for one.
