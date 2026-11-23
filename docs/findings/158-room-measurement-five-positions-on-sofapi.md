# Finding 158 — Five positions on sofapi: the head's weight and finer bass detail kept, the ringing quieter, the level read

**Date:** 2026-11-23. **For:** ADR-0187's first step, on George's run of
the same day with the research build:
- the finer bass detail (C5) and the head's weight (D5);
- the ringing (C6) and the joint cut's over-cut (C7);
- the level reading (C2);
- the logs ADR-0185 C4 and C8 wait on;
- Phase 29's open sweep agreement and Phase 30's acceptance 2.

## Scope

- **Device:** sofapi, Raspberry Pi 4, on the research build `ph37-research`
  (core 1.18.0+git22.af7d113, never released). It has the UMIK-1 with its
  90° file and room correction at *Full range*. The cables were the right
  way: at position 2 the right speaker read 16 cm further than at the head,
  as it should.
- **The run:** five positions placed by eye (D3), then the check at five
  places placed again, with the correction on. Each position had two sweeps
  per speaker and two together; one together at position 3 was repeated
  for a disturbance. The check had four of each, as it plays 3 dB lower
  (ADR-0185 C3). The player kept 91 responses, never a recording. A run
  started a minute earlier was cancelled after its first sweep. It is used
  only for its level and timing.
- **The level:** **48 dB at the seat, 12 dB short of the 60 aimed for**
  (room noise 20 dB). The cancelled run had reached 60 dB at the same
  digital level, so the amplifier was lower. Every signal-to-noise figure
  here is about 12 dB worse than a run at the aim.
- **Method:** scripts outside the repository, on the kept responses.
  - Curves at 1/6 octave, as the player makes them. Rebuilt here, they give
    the player's own three cuts.
  - The same curves at C5's detail: 1/48 octave below 100 Hz, 1/24 at
    250 Hz.
  - Four bass designs from both speakers together:
    - **A**, today's;
    - **B**, finer detail;
    - **C**, the head at half the weight (four shares of eight);
    - **D**, both of these.
  - **How each design is judged:** at each check place, the measured
    response less A's cuts (the stage plays what the core designs, Finding
    156), with that design's cuts added. Over 20-250 Hz: the rms above the
    target, the highest point above it, and the most it takes a point
    further below.
- **Not covered:**
  - one room and one run;
  - no timing mark (D4 needs a research build of its own);
  - designs B-D only computed, never played;
  - nothing heard.

## Results

**The bass at the check's five places** (fine curves; positions 1-5, 1 the
head):

| Design | Cuts | Over the target, rms (dB) | Highest over (dB) | Further under (dB) |
|---|---|---|---|---|
| A, today | 3 | 0.50 0.48 0.75 0.19 0.41 | 2.2 2.8 2.3 1.3 1.5 | 1.8 1.9 1.7 2.4 1.9 |
| B, finer | 3 | 0.47 0.49 0.70 0.17 0.38 | 1.9 2.8 2.3 1.1 1.5 | 1.5 1.6 1.5 1.8 1.6 |
| C, head half | 3 | 0.40 0.42 0.65 0.12 0.34 | 1.8 2.8 2.3 0.9 1.5 | 1.9 2.0 1.9 2.9 2.0 |
| D, both | 3 | 0.38 0.42 0.60 0.08 0.32 | 1.3 2.8 2.3 0.7 1.5 | 1.7 1.8 1.6 2.3 1.8 |

- **Repeats:** the four check sweeps of a place give each figure within
  ±0.02 dB.
- **Judged at 1/6 octave:** D against C is mixed, within 0.04 dB rms
  (position 2: 0.19 against 0.15).
- **Sensitive to the weight:** a trial with the head at five shares of nine
  fitted four cuts, not three, and scored about as D does. Small changes to
  the weights change the fit's shape.

**The ringing in the 50 Hz third octave, at the five check places.** Each
place's four sweeps are averaged, with each design put in place of A's
cuts. The "level" columns are the level 200 ms after the arrival, against
the uncorrected first 50 ms.

| | No cuts | A | C | D |
|---|---|---|---|---|
| Decay time (s; Fazenda's threshold 0.64) | 0.55 0.60 0.51 0.60 0.59 | 0.67 0.67 0.46 0.56 0.59 | 0.72 0.72 0.49 0.56 0.58 | 0.42 0.42 0.46 0.47 0.38 |
| Level at 200 ms (dB) | −19 −19 −19 −19 −19 | −37 −36 −39 −37 −36 | −37 −36 −39 −37 −36 | −44 −40 −49 −45 −43 |

- **The method checks out:** at the head, A as measured matches A
  simulated on the run's sweeps (decay 0.71 against 0.73 s at 50 Hz).
- **40 Hz:** every design lengthens the decay (0.70-0.86 s to 1.06-1.13 s),
  but the level 100 ms after the arrival falls by 10-11 dB.
- **63 Hz:** mixed.
- **127-202 Hz:** decays of 0.5-0.57 s, untouched by any cut. That is the
  room's reverberation, over Fazenda's thresholds, which are for modes.
- **20-25 Hz:** under 35 dB above the noise, so not read.

**The joint cut against the speakers alone (C7):** bass played by one
speaker meets the joint cuts. The two speakers' power sum is taken at most:
- **with A,** 3.3 dB further below the target, at 46 Hz (2.8 dB on 19 Nov);
- **with D,** 4.5 dB further below, at 46 Hz.

**The level (C2), the right against the left, 500 Hz-4 kHz, at the head:**

| Window after the arrival | 3 ms | 6 ms | 20 ms | The run's sweeps, 1 s |
|---|---|---|---|---|
| Right − left (dB), two readings | −0.20, −0.15 | −0.60, −0.55 | −1.81, −1.78 | −2.7 |

- **The two readings agree within 0.05 dB,** inside C2's 0.25 dB.
- **The window decides most of it:** the direct sound is within 0.7 dB,
  and the room adds more on the left by 20 ms.
- **The playback's first tens of milliseconds are partly lost:**
  - the first left sweep's 500-630 Hz read 0.4-1.4 dB under the second
    left's (once 8.7 dB), while above 800 Hz they agree within 0.4 dB;
  - this moves the reading by 0.1-0.15 dB;
  - the measuring sweeps start at 10 Hz, so they are not affected.

**ADR-0185 C4, the sweeps' agreement:**
- **The run:** where judged, the closest two of each set were 0.1-0.5 dB
  apart. The exception was position 3 together: 1.8 dB at 33 Hz, 22 dB
  above the noise, repeated, then 0.3 dB.
- **The check:** each four within 0.1-0.3 dB, and all four averaged every
  time.
- **Points judged:** 59-72 of 88 in the run and 49-67 in the check. The
  check plays lower, and its cuts lower it further.

**C8, bass left uncorrected for noise** (under 10 dB above it after
averaging):
- both speakers together: 12 points, 20-21 Hz;
- the right: 12 points, 20-21 Hz;
- the left: 15 points, 20-95 Hz.

The bass is designed from both together. There these points lie 13-20 dB
below the target, where cuts-only does nothing.

**Above the bass (Phase 30's acceptance 2),** 300 Hz-14 kHz at 1/3 octave,
at the check's places, against each speaker's own target:

| Speaker | Average, rms before → after | Highest | Each place, rms | Further at a correction's own frequency |
|---|---|---|---|---|
| Left | 1.57 → 0.77 dB | 3.2 → 2.0 | all five closer | places 2 and 3: 1.6 and 1.3 dB at 7.9 kHz |
| Right | 1.47 → 0.84 dB | 3.9 → 2.3 | all five closer | the head 1.5 dB and place 2 1.2 dB at 906 Hz; places 4 and 5 1.5 and 1.6 dB at 7.8 kHz |

- **At 906 Hz,** the head was already below the target, while the other
  places were above it.
- **At 7.8-7.9 kHz,** both speakers' check places read about 1 dB lower
  than the run's positions, even before the correction.
- **The player's own check** listed the head (2.2 dB) and position 2
  (1.2 dB) as worse. That is the right speaker at 906 Hz, comparing the
  run's positions with the check's, so the moved placement is in it.
- **With the head at half the weight above the bass too:** the right
  speaker's average goes to 0.70 dB rms (highest 1.7), and the head is
  0.7 dB further at 906 Hz instead of 1.5. Places 4 and 5 stay 1.2-1.3 dB
  further at 7.9 kHz.

## What it means

- **D5 is kept at half:** the head counts as much as the other four
  together, in the average and in the positions' vote. With it:
  - the head comes closer: 0.50 to 0.40 dB rms, its peak 2.2 to 1.8 dB;
  - every other place comes closer in rms;
  - no place goes more than 0.5 dB further under the target, inside the
    core's 1 dB guard (`WORSE_DB`).

  Above the bass it halves the head's worst point.
- **C5 is kept with it, design D:**
  - on the fine curves, no place is worse and the head's peak is lower
    (1.3 against 1.8 dB);
  - on the 1/6-octave curves the two are within 0.04 dB;
  - at 50 Hz the ringing is shorter at all five places and under Fazenda's
    threshold at each. A leaves it over the threshold at two places, where
    without cuts it was under at all five.
- **The ringing is quieter with every design:**
  - **The level at a fixed time is the reading to keep,** for D7 (how the
    ringing is shown): 17-30 dB lower at 200 ms at 50 Hz.
  - **The decay time alone misleads:** where a cut takes out the strongest
    mode, the band's decay can lengthen while what rings is 10-24 dB
    quieter.
- **C7 stays logged with no cap:** D takes bass played by one speaker
  4.5 dB below the target at 46 Hz.
- **C2's window is 6 ms** (three cycles at 500 Hz), and the timing signal
  is led by silence so its first sweep is whole. On sofapi that turns the
  left speaker down by about 0.6 dB.
- **A sound level meter would show about 2 dB more on the left here,**
  from the room's later sound rather than the speakers' own. That matters
  for Phase 37's acceptance 5.
- **ADR-0185's limits stay:**
  - `AGREE_DB` is 1.5 dB, three times the largest gap between undisturbed
    sweeps, and it caught the one disturbance;
  - `JUDGE_SNR_DB` stays at 20 dB;
  - C8 is not needed, so the repeats stay power-averaged.
- **Phase 29's sweep agreement:** at 48 dB, the noisier case, it is
  0.1-0.5 dB, which answers the item left open at 60 dB.
- **Phase 30's acceptance 2 is met on average and at every place in rms,
  but not point by point:**
  - At 7.8-7.9 kHz, a microphone placed again by eye reads about 1 dB
    differently, so a correction there can take a place further away.
  - That point is open for the next run.
- **The next run should be at 60 dB:** the amplifier was lower this time.
