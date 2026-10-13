# Finding 122 — The top spectrum bars read noise-like treble far too high

**Date:** 2026-10-13. **Asked by:** George (*"It feels like the higher
frequencies are not correctly represented. I was listening to a normal song
with no high frequency, but the top part of the bar spectrum was all the way
up ... Please have a thorough check on it."*).

## Scope

- **What was measured:** peppyalsa's spectrum as patched by ADR-0130
  (`gexis-peppyalsa` `-4`), with `output.conf`'s settings: Blackman window,
  log frequency, log amplitude, 30 bands, smoothing 90. The 30 bands were
  then folded to 20 bars by peak, as `meters.resample` does for a 20-bar
  skin.
- **Three ways:**
  1. A numpy port of `spectrum.c`, checked line by line against the source.
  2. **On sofapi**, while nothing else was playing: a 25 s excerpt of a
     16/44.1 track, played with `aplay -D output` once as S16 and once as
     S32. Frames were read from `/run/gexis/spectrum.fifo` (about 1,165
     each). The device read within 0-5 points a bar of the port, a little
     lower, and S16 and S32 matched to the point.
  3. Known signals:
     - pink noise, alone and with an extra −3, −6 or −12 dB/octave slope
       above 1 kHz;
     - white noise;
     - 60 Hz and 1 kHz tones;
     - 16-bit dither.
- **Music:** eight tracks from George's Lyrion library, one per genre
  (blues, bossa nova, Britpop, classic rock, classical vocal, dance, EDM,
  death metal), 60 s from 1:00 of each, decoded to 16/44.1. Also the track
  from the device test, which has almost nothing above 10 kHz (−85 to −91
  dBFS).
- **Not measured:**
  - which track, player or source George was listening to;
  - rates other than 44.1 kHz (ADR-0130 sizes the FFT to keep about 10.8
    Hz a bin, so the bands hold the same bins);
  - how the bars look on the panel.

## Results

1. **The engine, the core and the drawing are each doing what they say.**
   The device matches the port, and the core's fold is a peak per group.
   PeppySpectrum draws value × bar height / 100, rounded up to its step.
   Nothing past peppyalsa raises the top bars.

2. **A band's level is the sum of its bins' magnitudes.** The top band
   (13.2-16 kHz) holds about 265 bins at 4096 points, the bottom one 1.
   - A **tone** puts its energy in a few bins, so it reads about the same
     level in any band.
   - **Noise-like sound** - cymbals, breath, sibilance, reverb, which is
     what treble mostly is - adds up across all of a band's bins. Its
     reading grows with the band's width: about 3 dB an octave on top of
     the real level.
   - The lift ADR-0130 added is another 3 dB an octave above 1 kHz.

   Average bar heights (0-100), 30 bands:

   | Signal | Bass | Middle | Top band |
   |---|---|---|---|
   | Pink noise (flat per octave) | 44 | 54-57 | **81** |
   | Pink, −6 dB/oct above 1 kHz (audibly dull) | 41 | 54 | **57** (flat) |
   | Pink, −12 dB/oct above 1 kHz (48 dB down at 16 kHz) | 45 | 55 | **35** |
   | 16-bit dither alone | 0 | 0 | **14** |

3. **On music, the last bars are the tallest on the display.** 20 bars, mean
   height of the first three bars, the middle and the last two:

   | Genre | Today: bass / middle / last two | Band power, lift kept |
   |---|---|---|
   | Britpop | 48-59 / 61-67 / **80, 77** | 53-62 / 58-64 / 64, 60 |
   | Dance | 55-61 / 56-62 / **76, 76** | 60-64 / 54-58 / 60, 59 |
   | EDM | 60-65 / 59-69 / **78, 76** | 62-70 / 60-65 / 61, 59 |
   | Blues | 42-61 / 51-63 / **76, 74** | 47-64 / 50-60 / 60, 57 |
   | Classic rock | 43-59 / 52-57 / 61, 58 | 48-62 / 51-57 / 45, 40 |
   | Classical vocal | 45-51 / 55-60 / 59, 60 | 50-55 / 48-59 / 43, 42 |
   | Bossa nova | 29-48 / 53-60 / 60, 58 | 34-50 / 50-59 / 45, 42 |
   | Death metal | 5-41 / 36-52 / 49, 47 | 10-44 / 33-52 / 33, 31 |
   | The dark track | 17-37 / 44-52 / 9, 11 | 22-39 / 45-51 / 1, 0 |

4. **The error, in dB:** the top octave and a half (10.9-16 kHz) against the
   voice range (415-609 Hz), two bands of equal width in octaves. The bars
   are turned into dB at 0.963 dB a unit.

   | Genre | In the recording | Today's bars | Band power, lift kept |
   |---|---|---|---|
   | Dance | −9.8 | +14.9 | +1.6 |
   | Britpop | −12.6 | +15.7 | +1.5 |
   | Blues | −13.5 | +14.2 | +1.0 |
   | EDM | −13.6 | +10.5 | −3.4 |
   | Death metal | −18.8 | +10.3 | −4.4 |
   | Classic rock | −24.4 | +2.9 | −11.1 |
   | Classical vocal | −26.4 | +1.8 | −12.9 |
   | Bossa nova | −29.2 | +0.9 | −12.8 |

   - **Today:** a treble 10-14 dB *below* the voice is drawn 10-16 dB
     *above* it. That is 24-28 dB over the recording. About 11 dB of it is
     the lift at that height, which is intended; the other 13-17 dB is the
     summing.
   - **Band power** (the square root of the band's summed bin power, as a
     real-time analyser measures a band) puts the bars 11-16 dB over the
     recording. That is the lift and little else.

5. **Band power, scaled by 1.815** (a steady tone's sum of magnitudes over
   its root-sum-square, Blackman window), keeps a tone where it is. A 1 kHz
   tone read 76 both ways.
   - The narrowest bass bands, a single bin each, rise 5 points when the
     same scale is applied to them. Today a tone reads about 5 dB lower in
     a one-bin band than in a wider one; the scale makes it read the same
     in every band.
   - This is a different thing from Finding 117's extra division. That one
     lowered every band, the bass included; band power changes only what
     several bins add up to.

## What it means

**The display is wrong.** Most recordings carry treble 10-30 dB below the
midrange: cymbals and breath, quiet but present. Today's sum turns that into
the tallest bars on the screen, which is what George saw. A recording with
truly nothing up there (the dark track) does draw low top bars today; it
would draw none with band power.

**ADR-0130 named the effect but not its size.** It records that noise-like
sound "reads a little higher". That was measured on one orchestral piece,
where it was not visible. On pop, rock and electronic material it is 13-17
dB.
