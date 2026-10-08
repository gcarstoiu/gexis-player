# Finding 117 — What the spectrum bars measure, before and after ADR-0130

**Date:** 2026-10-08. **For:** George, *"Whenever I use a spectrum skin, I
rarely see any movement on the last 2 bars on the right."*

## Scope

- **Audio:** Beethoven, *Egmont* Overture, Op. 84 (Musopen Symphony, public
  domain, from Wikimedia Commons), resampled with ffmpeg to 44.1 and 96 kHz.
  The 96 kHz copy has no content above 24 kHz, as an upsampled master would
  have; a native hi-res recording would carry some ultrasonic noise. Plus
  sox pink noise, low-passed at 16 kHz.
- **Orchestral only.** No pop, rock or electronic recording was measured,
  and those carry more bass and treble than this.
- **What is counted:** the 30 bands folded to 20 bars by peak, as
  `meters.resample` does for a 20-bar skin. Per bar: the mean height (0-100),
  how much it moves (standard deviation) and how often it reads zero.
- **Three ways, each checked against the next:**
  1. a Python port of peppyalsa's `spectrum.c` (Blackman window, log
     frequency, log amplitude, smoothing 90, as `output.conf` sets them);
  2. the C code itself, compiled on the PC behind a harness that feeds a file
     as the ALSA meter would (rate / 50 frames per update). It reproduces the
     port to within a few tenths;
  3. on **guestpi** (Pi 4): the real arm64 libraries, old (`-1`) and new
     (`-2`), each loaded by `aplay` through a private `meter → null` chain
     with its own FIFO, paced at real time, 10 ms periods, 90 s per run.
     About 49 frames a second, as the player gives.
     - No sound card was opened, nothing was installed, and the
       visualiser's FIFOs were not touched.
     - `/proc/<aplay>/maps` was recorded for every run to show which library
       was loaded (see *How this went wrong first*).

## Results — on guestpi, the first 90 s, 20 bars

| | Last bar at zero | 2nd last at zero | Bars 1-5 cover | Loudest frame |
|---|---|---|---|---|
| Old, 44.1 kHz | 57 % (15-22 kHz) | 51 % | 86-600 Hz | 69 |
| Old, 96 kHz | **100 %** (33-48 kHz) | **100 %** (27-33 kHz) | 188-1500 Hz | 65 |
| New, 44.1 kHz | 0 % (10.9-16 kHz) | 0 % | 50-190 Hz | 73 |
| New, 96 kHz | 0 % | 0 % | 50-190 Hz | 73 |

- **Old:** the middle bars read zero 1-5 % of the time, and nothing below 86
  Hz was shown.
- **New:** the five bass bars read zero 13-28 % of the time in this opening,
  and move the most of any bars (standard deviation about 20, against 13-15
  for the middle).
- **44.1 and 96 kHz now give the same picture**, to within a point a bar.
- **No frame reached 100** in either version.

**CPU**, `aplay` with the library inside it, over 90 s:

| | Old | New |
|---|---|---|
| 44.1 kHz | 1.4 s | 2.4 s |
| 96 kHz | 1.6 s | 3.8 s |

About 1-2.5 % more of one core, in whichever renderer has the device open.

## The scaling, settled on the device

The first build divided band sums by `sqrt(FFT size / 512)` as well as by the
FFT size, which keeps a band of noise at its old level. On guestpi that held
bars 1-5 at zero 30-40 % of the time. A bass note is a single pitch: it lands
in one bin, and its level does not grow with the FFT, so the extra division
lowered it by about 9 points out of 100. Without it, the bass bars read zero
13-22 % of the time, the treble stays at 0 %, and the loudest frame goes from
69 to 73-75. The port reproduced the device to the bar, both ways.

## How this went wrong first

The first device run reported old and new **identical to the decimal**. Both
runs had loaded `/usr/lib/libpeppyalsa.so`:

- `pcm_scope_type.!peppyalsa { lib … }` in the test's own configuration lost
  to the system's `conf.d/output.conf`, which alsa-lib reads after it, through
  the hooks.
- Giving the test its own scope type, with `open _snd_pcm_scope_peppyalsa_open`,
  loaded the intended library, and the memory maps confirm it for every run
  above.

## Not measured

- Pop, rock, electronic or spoken material.
- A native hi-res file with real ultrasonic content.
- 192 kHz: the FFT is 16384 points there, so expect about twice the 96 kHz
  CPU cost.
- How the bars look on the panel, which is for George.
