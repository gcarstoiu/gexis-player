# Finding 144 — Room correction above the bass: one room measured

**Date:** 2026-11-10. **For:** Phase 30 (`ph-room-correction-full`), the
measurement before its ADR (George, 2026-11-07): how well a run sweeping to
20 kHz measures above the bass, whether three positions are enough, and what
a correction of at most 3 dB up or down, with broad filters, would do there.
Follows [Finding 141](141-room-correction-above-the-bass-what-is-known.md)
(the desk research).

## Scope

- **Device:** sofapi, a Raspberry Pi 4, on a throwaway preview of the phase
  branch (`ph30-research`, never released) that sweeps to 20 kHz and keeps a
  run's recordings on the player; the output an SMSL USB DAC, George's
  amplifier and speakers, George's living room.
- **Microphone:** a miniDSP UMIK-1 pointing at the ceiling, its 90° file
  given again that morning (615 points, 10 Hz to 20 kHz). Levels in dB SPL are
  approximate, as in ADR-0175 (the file's sensitivity read as REW reads it).
- **The run** (George, 10:12, one run from the phone): the three positions
  the phone asks for (the head, 40 cm to the left, 40 cm to the right); each
  speaker alone, then both together, two sweeps each (three where two did not
  agree); then the check with the bass correction on, the microphone placed
  again at each of the three. Sweeps 10 Hz to 20 kHz over 8 s, at 48 kHz.
- **Analysed on R2D2** from the recordings, with the core's own maths
  (`room_dsp`): deconvolution, a 1 s window, 1/6 octave, the calibration
  subtracted, the two sweeps that agree best power-averaged. From the same
  recordings it gives the cuts the player made and kept, to the decimal.
- **The check as a second placing:** its sweeps ran with the bass cuts on;
  the cuts' response (all below 250 Hz, the highest at 226 Hz) was taken back
  out of each speaker's curves before comparing. *Both* was left out of that
  comparison.
- **The designs above the bass are computed, not heard:** each was worked out
  from the run's three positions and applied, as a prediction, to the run's
  and to the check's curves. No filter above the bass played.
- **Not measured:** the three positions around the head that were planned
  (30 cm in front, 25 cm above and below) - George kept three positions and
  left whether more help to a later, separate check (2026-11-10); another
  room or other speakers; the stage's cost on the Pi.

## Results

**The level.** The room's noise read 20.5 dB SPL in the bass (20-500 Hz). The
sweeps played at their cap, peaks at −1.5 dBFS, which is −8.2 dBFS in the
bass band for a sweep to 20 kHz (−6 for Phase 29's to 1 kHz): 54 dB at the
seat, short of the 60 aimed for, and taken (above 45 dB and 15 dB over the
noise). A sweep to 20 kHz reaches about 2 dB less in the bass than Phase
29's at the same amplifier setting.

**The signal over the room's noise** (the lowest in each band, the first
sweep of each position, run and check alike):

| 250 Hz-1 kHz | 1-4 kHz | 4-10 kHz | 10-16 kHz | 16-20 kHz |
|---|---|---|---|---|
| 28-40 dB | 64-75 dB | 79-85 dB | 82-88 dB | 59-69 dB |

Below 250 Hz it is lower where a speaker's response has its deep dips (the
right speaker's at 85-113 Hz, as in ADR-0175), as in Phase 29.

**Two sweeps of one position** (the pair kept, 1/3 octave): within 0.4 dB of
each other from 250 Hz to 16 kHz in 16 of 18 cases (at position 1 in the
run, the left speaker's at 1.1 dB and both together at 0.8), and within
0.4 dB from 16 to 20 kHz in all. Below 250 Hz (1/6 octave) 0.4 to 1.4 dB, as in Phase 29.

**The microphone placed again.** The three positions' average from the check
came within 0.9 dB (left speaker; RMS 0.29) and 0.7 dB (right; RMS 0.24) of
the run's, from 250 Hz to 16 kHz at 1/3 octave.

**The three positions against each other** (1/3 octave, 250 Hz to 14 kHz):

| | spread, median | 90th percentile | largest | std, median |
|---|---|---|---|---|
| Left | 1.6 dB | 4.7 dB | 6.1 dB at 740 Hz | 0.67 dB |
| Right | 2.3 dB | 4.1 dB | 6.9 dB at 254 Hz | 0.94 dB |

**The room above the bass.** Both speakers are close to level: a straight
line fitted from 300 Hz to 10 kHz rises 0.4 dB an octave (left) and falls 0.4
(right). The largest gap from that line is the left speaker's dip around
315 Hz, 5.6 dB, at all three positions; the right's largest is 3.5 dB. Both
fall 2-5 dB from 16 to 20 kHz.

**Corrections tried** (designed from the run's three positions; the gap from
the line at 1/3 octave, RMS from 250 Hz to where the design stops, averaged
over the positions; *worst* is the most any one position got further from the
line at any frequency; the check's placing in brackets):

| Design | Left | Right | Worst |
|---|---|---|---|
| None | 2.0 | 2.0 | - |
| Each filter ±3 dB, eight, Q to 3, to 16 kHz | 1.34 | 1.19 | +1.9 |
| The total ±3 dB, six filters, Q 0.5-2, to 12 kHz | 1.35 (1.34) | 1.22 (1.16) | +2.1 (+1.8) |
| The same, cuts only | 2.00 (1.94) | 1.83 (1.68) | +1.5 (+1.4) |
| The same, raises to +1 dB | 1.62 (1.59) | 1.41 (1.29) | +1.4 (+1.6) |
| The same, raises to +2 dB | 1.43 (1.42) | 1.27 (1.18) | +1.5 (+1.5) |
| The same, 1 octave smoothing | 1.82 (1.82) | 1.37 (1.25) | +1.7 (+1.7) |
| **Chosen**: to 14 kHz, gaps under 1.5 dB left, less where the positions disagree, most positions deciding | **1.40 (1.38)** | **1.26 (1.19)** | **+1.4 (+1.4)** |

- **Each filter at ±3 dB** stacked two and three at one frequency: the left
  speaker's correction reached +8.8 dB at 278 Hz, and +3 dB at 16 kHz, fitting
  the tweeter's own fall. Held to ±3 dB on the total instead.
- **Four, six or eight filters,** Q up to 1, 1.5, 2 or 3, and stopping at 8,
  12, 14 or 16 kHz all gave within 0.1 dB of each other.
- **Every design did as well on the check's placing** as on the run's, which
  it was not made from.
- **The chosen design** uses five filters on the left (251 Hz +1.7 dB, 371 Hz
  +2.5, 495 Hz −3.0, 1.05 kHz −1.7, 2.37 kHz +1.8) and four on the right
  (300 Hz +2.5, 542 Hz −3.0, 1.99 kHz +2.7, 7.9 kHz −1.3), Q 1.3 to 2. Every
  position comes closer, in both placings: left 2.04, 1.72, 2.28 dB to 1.43,
  1.22, 1.55; right 1.61, 1.64, 2.64 to 0.79, 1.02, 1.97. The left's 315 Hz
  dip can only be raised by part of its depth, so the average stays up to
  3.5 dB from the line there (1.5 dB on the right).
- **Most positions deciding** (as the bass's cuts, ADR-0175) trims the
  left's raise at 251 Hz from +2.6 to +1.7 dB, where position 2's dip is
  shallower; it costs 0.08 dB RMS on the left and nothing on the right, and
  keeps any one position from getting more than 1.4 dB further anywhere (1.8
  without it).

**As built** (ADR-0177, `room_dsp.design` on the same curves, after the
trials above): the left gets five filters, the right four; every position
comes closer in both placings - the left 2.01 to 1.44 dB RMS (the check's
1.95 to 1.43), the right 1.97 to 1.30 (1.84 to 1.22) - and none gets more
than 1.6 dB further at any frequency. It differs from the chosen trial in
holding the correction near none where the positions disagree, and in the
filters' frequencies staying from 250 Hz to 14 kHz.

**Joining the bass at 250 Hz.** The line (its mean from 250 to 500 Hz) sits
above the level Phase 29 takes the bass target from (the average there): 2.9
dB on the left, pulled down there by the 315 Hz dip, and 1.4 dB on the
right. Taken from the line, the bass's cuts come out smaller:

| | Phase 29's level | The line's |
|---|---|---|
| Left | 46 Hz −8.9 and −7.4, 68 Hz −8.2, 121 Hz −11.1, 172 Hz −5.5, 216 Hz −6.0 | 45 Hz −7.7 and −6.7, 68 Hz −6.6, 121 Hz −8.8, 172 Hz −4.0, 216 Hz −3.9 |
| Right | 45 Hz −2.8, 47 Hz −12.0, 63 Hz −5.0, 226 Hz −2.7 | 47 Hz −12.0, 63 Hz −3.6, 226 Hz −1.1 |

**Times.** A sweep every 11 s (8 s of sweep), so a position took 65 to 76 s
with its six or seven sweeps; the run's sweeps about 4 minutes with two
moves, the check's about 4¼ - about a minute a position, against Phase 29's
45 s.

## What it means for Phase 30

- **Three positions measure this room above the bass well enough** for a
  correction this coarse: repeated sweeps agree within 0.4 dB, the microphone
  placed again moves the average less than 1 dB, and a correction from one
  placing does as well on the other. Whether more positions would help, in
  this room or in others, is not measured here.
- **Raises are what help here.** The gaps above the bass are mostly dips:
  cuts alone take the average from 2.0 to 1.9-2.0 dB, and a correction that
  may also raise by 3 dB takes it to about 1.3.
- **Four to six broad filters are enough**; more, narrower or further up
  buys nothing measurable. Above 14 kHz the curves show the tweeter's own
  fall, which the target is meant to keep.
- **The sweep to 20 kHz costs about 2 dB of level in the bass** at the same
  amplifier setting; in this quiet room that left 28 dB over the noise above
  250 Hz.
