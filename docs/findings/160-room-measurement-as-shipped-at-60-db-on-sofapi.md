# Finding 160 — The reworked measurement at 60 dB on sofapi: the bass as on 23 November, the check more than half the run, three places further above the bass

**Date:** 2026-11-25. **For:** ADR-0187 as built (D1-D8, the together
sweeps gone), on George's third full run: the first on a preview build
rather than a research build, and the first at the aim. It led to ADR-0187's
amendment of 2026-11-25 and to D11-D12.

## Scope

- **Device:** sofapi, Raspberry Pi 4, on the preview of 2026-11-24 (core
  1.18.2+git30.d71d711, player and UI git31.3d65d70; never released). It
  has the UMIK-1 with its 90° file and the SMSL USB DAC, whose PCM filter
  was *Sharp roll-off* (off for 23 November's runs).
- **The run:** the speaker check, then five positions placed by eye as the
  drawing then showed them, then the check at five places placed again, with
  the correction on. Kept.
  - **Each position:** two sweeps per speaker, each after its timing mark.
  - **The check:** four per speaker, as it played 3 dB lower for the
    corrections' largest raise (ADR-0185 C3); at the head, four of both
    speakers together too (D4's log).
- **The level:** 60 dB at the seat, the aim, with the room's noise at 20 dB.
- **Sources:** the core's log lines for the run and the measurement as kept
  (its curves, cuts, corrections, ringing and dips). Per-sweep responses
  were not kept on this build, and nor were the check's curves at each
  place (kept since 01b0c582).
- **Not covered:**
  - one room and one run;
  - nothing heard;
  - which correction made each place further (logged since 01b0c582), and
    so what D11 would have taken out of this run;
  - any cause for the change in D4's gap above 2 kHz (below).

## Results

**Time** (from the core's log; 22 min 4 s from taking the device to *Keep
it*):

| Part | From - to | Time | Sweeps |
|---|---|---|---|
| The level | 11:20:52 - 11:21:18 | 26 s | - |
| The speaker check | to 11:22:21 | 1 min 3 s | timing sweeps at 2 places |
| Five positions | 11:22:21 - 11:29:58 | 7 min 37 s | 20 |
| The check, from the correction's screen | 11:30:00 - 11:42:50 | 12 min 50 s | 44 |

A sweep with its timing mark took about 12.5 s: 25 s for a set of two, 50 s
for a set of four.

**The level and the noise:**
- 60 dB at the seat with the level step's noise at −24 dBFS, reached in
  17 s.
- Points judged ([ADR-0185](../decisions/0185-room-measurement-speakers-checked-and-aligned-fewer-repeats.md)
  C4, of 88):
  - the run: 83 on the left and 85 on the right at every position;
  - the check: 80-83 on the left and 81-83 on the right, apart from the
    right at place 5 (66, with one of its four sweeps set aside);
  - Finding 159, at 52 dB: 58-71 in the run and 42-71 in the check.
- The closest two sweeps of each set: 0.1-0.5 dB apart in the run and
  0.1-0.3 dB in the check, every one at 22-32 Hz apart from one at 170 Hz.
  No set in the run was repeated.

**The speaker check:**
- **At the head:** the right 4.4 cm further than the left, its two readings
  0.0 cm apart; the same polarity (0.76 alike). The right was 1.56 dB
  quieter (both readings −1.56), so the left was delayed 0.13 ms and turned
  down 1.6 dB.
- **At position 2:** the right 32.8 cm further, so left and right were the
  right way round. Its level, with the stage's match taken back out, read
  the right 1.7 dB louder. That reading is logged only, not used; why the
  nearer speaker read quieter there was not looked into.
- **Earlier delays:** 0.23 ms in the measurement kept on 23 November, and
  0.17 ms (5.8 cm, 1.8 dB) from *Check the speakers* on 24 November.

**The bass:**
- **Cuts, the same on both speakers:** 43 Hz −3.4 dB, 46 Hz −12.0 dB,
  57 Hz −4.1 dB. Finding 159's design: 42.6 Hz −3.5, 46.5 Hz −12.0,
  57.0 Hz −3.6.
- **Both speakers, from 30 to 250 Hz** (the average of the check's places
  against that of the run's): the highest point over the target fell from
  12.7 to 0.9 dB, and the rms over it from 4.05 to 0.18 dB.
- **Each speaker alone**, from 30 to 250 Hz: the left's highest point over
  the target fell from 10.9 to 1.4 dB, and the right's from 11.5 to
  4.9 dB. The cuts are made for the pair, as
  [ADR-0186](../decisions/0186-room-chart-both-in-the-bass-only-shading-the-corrections.md)
  D5 notes.
- **C7:** the joint cuts take the speakers' power sum at most 3.1 dB further
  under the target, at 46 Hz (Finding 159: 3.6 dB at 46 Hz).

**The ringing at the head** (each speaker's head sweeps averaged as waves;
the level 0.2 s after the arrival against the first 50 ms, before → after
as checked):

| Band | Left | Right |
|---|---|---|
| 40 Hz | −25.5 → −40.7 dB | −24.6 → −25.3 dB |
| 50 Hz | −21.8 → −52.3 dB | −18.8 → −45.4 dB |
| 63 Hz | −31.4 → −33.1 dB | −29.9 → −29.7 dB |

- **The 50 Hz decay:** 0.60 → 0.31 s on the left and 0.57 → 0.49 s on the
  right, both under Fazenda's 0.64 s.
- **The 40 Hz decay lengthens** (0.86 → 1.20 s left, 0.80 → 1.09 s right),
  as in Finding 159, while the level at 0.2 s falls or holds.

**Above the bass, from 300 Hz to 14 kHz** (each speaker against its own
target, at 1/3 octave; the run's average before, the check's after):

| Speaker | Corrections (Hz, dB) | Within (the design's) | rms |
|---|---|---|---|
| Left | 252 +3.0, 349 −2.6, 480 +2.0, 744 −2.7, 1351 +1.7 | 2.5 → 2.0 dB | 0.77 → 0.67 dB |
| Right | 250 +2.7, 334 −2.9, 529 +3.0, 840 −3.0, 1645 +2.0 | 3.0 → 1.5 dB | 1.20 → 0.63 dB |

- **Each position before**, rms: the left 1.11-1.80 dB, the right
  1.33-1.99 dB.
- **The check named three places further from the target** at a
  correction's frequency: 2 by 2.0 dB, 3 by 1.9 and 4 by 2.3. Which
  correction was not logged.
- **The corrections near 0.7-1.9 kHz recur:** this run's cuts at 744 and
  840 Hz and raises at 1351 and 1645 Hz lie near the four that Finding 159
  traced its worse places to (721 and 1594 Hz on the left, 849 and 1849 Hz
  on the right).

**The dips left** (D8): 147 Hz, 6.6 dB under, a wall (the right speaker,
0.58 m); 220 Hz, 6.4 dB, local; 190 Hz, 3.8 dB, no cause named.

**D4 at the check's head**, the two speakers added against the two played
together:

| Range | Most apart | rms |
|---|---|---|
| 30-250 Hz | 0.20 dB | 0.08 dB |
| 250 Hz-1.6 kHz | 0.21 dB | 0.06 dB |
| 2-5 kHz | 0.79 dB | 0.40 dB |

Finding 159, at all ten sets: 0.9-3.1 dB apart at 2-2.5 kHz in the check.

## What it means

- **The bass came out as on 23 November.** The three cuts are within
  0.5 dB of Finding 159's, from a different placement two days later, and
  the pair's highest point lies within 1 dB of the target. The 50 Hz
  ringing falls by about 30 dB on the left and 27 dB on the right at 0.2 s.
- **At the aim, nearly every point is judged:** 80-85 of 88 (one set 66),
  against 42-71 at 52 dB. A point is judged only when far enough over the
  noise, and the sweeps stood about 10 dB further over it: 8 dB louder,
  with the room's noise 2-4 dB lower (22-24 dB on 23 November).
- **The check took more than half the run:** 44 sweeps against the run's
  20, as it played 3 dB lower. That led to ADR-0187's amendment of
  2026-11-25 (01b0c582): the check plays lower only where its sweeps lack
  room. On this run they stood about 16 dB under their cap, so it would
  have played two sweeps a set. That is 22 fewer, about 4½ minutes at
  12.5 s each; an estimate, not measured.
- **Above the bass, the average came closer while three places went
  further**, as in Finding 159, and again near 0.7-1.9 kHz, where the
  response follows the microphone's place. George decided the same day
  that the check takes out a correction that does this (ADR-0187 D11).
  George's next run is the first to show which ones go.
- **D4's gap above 2 kHz was 0.8 dB at the head**, against 1-3 dB on
  23 November. The level and the DAC's filter both changed, and only the
  head was measured, so the cause is still open. Nothing uses the pair
  above the bass.
- **The speaker check's distance moves with the placement.** Its delay was
  0.23, 0.17 and then 0.13 ms (about 8, 6 and 4 cm) over three days. This
  run's two readings agreed to 0.0 cm, so the spread is most likely where
  the microphone stood, placed by eye.
