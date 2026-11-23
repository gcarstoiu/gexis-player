# Finding 159 — Timing marks on sofapi: the added pair cuts the bass as the played pair, not above 2 kHz; the kept design confirmed at D3's heights

**Date:** 2026-11-23. **For:** ADR-0187 D4's proof, and D5/C5 again at
D3's heights, on George's second run of the day, with research build 2.
Also covered:
- the ringing (C6) and the joint cut (C7);
- the level reading (C2);
- the places the player's check named worse;
- ADR-0185's logs.

## Scope

- **Device:** sofapi, Raspberry Pi 4, on research build 2 (`ph37-research-2`,
  core 1.18.2+git25.520b018, never released). It is Phase 37's branch, with
  each sweep's response and its timing mark kept. It has the UMIK-1 with its
  90° file and the SMSL USB DAC. Just before, that DAC had fallen silent
  until its cable was plugged in again (Lesson 98); it played through the
  whole run.
- **The run:** five positions at D3's heights, as the drawing now shows
  them, placed by eye. Then the check at five places, placed again. **The
  check played the core's own design (D5 with C5)**, the one kept on
  Finding 158.
  - **Each position:** two sweeps per speaker and two together, each after
    its timing mark. One left set (position 5) was repeated for a
    disturbance.
  - **The check:** four of each, as it played 3 dB lower for the
    correction's largest raise (ADR-0185 C3). Two of the left's four at
    place 2 were set aside.
  - **Kept:** 91 responses and 4 timing readings, never a recording.
- **The level:** 52 dB at the seat, 8 dB short of the aim, with the room's
  noise at 22-24 dB. A first try read 37 dB and stopped as too quiet; the
  amplifier was turned up.
- **Method:** scripts outside the repository, on the kept responses, as for
  Finding 158.
  - **D4:** each response is moved so that its mark arrives at a fixed time,
    and repeats are averaged as waves. The left and the right are then added
    as waves and compared with the pair played together. The yardstick is
    the played pair's two repeats.
  - **The other designs (A-C):** judged at each check place as measured,
    with D's cuts taken back out and the design's own put in.
- **Not covered:**
  - one room and one run;
  - nothing heard;
  - the cause of the gap above 2 kHz (below), which was not tested.

## Results

**D4, the pair added against the pair played together:**
- **The marks:** found on all 91 sweeps. Repeats placed by their marks lie
  within 8 µs of each other at 1-4 kHz (one pair of 58 at 38 µs).
- **30-250 Hz** (1/6 octave), at all ten sets (five positions, run and
  check):
  - the added pair lies at most 0.23-0.52 dB from the played one (rms
    0.08-0.17);
  - the played pair's own repeats differ by at most 0.23-0.81 dB (rms
    0.06-0.19).
- **20-30 Hz:** up to 1.9 dB apart in the run and 2.5 dB in the check, the
  largest where the pair stands only 11-13 dB above the noise.
- **250 Hz-1.6 kHz** (1/3 octave): within 0.2 dB (position 3 in the run:
  0.3-0.5 dB at 0.8-1 kHz).
- **From 2 to 5 kHz, the added pair is louder at every set.** At 2-2.5 kHz
  it is 0.8-1.7 dB louder in the run and 0.9-3.1 dB in the check (up to 2.2
  at 3.15 kHz). Repeats agree within 0.6 dB at 1-4 kHz. Above 5 kHz it is
  mostly louder, by up to 1.6 dB; at check place 3 it is quieter, by up to
  1.9 dB.
  - **What is left over** (the added pair less the played one) has the
    room's shape, mostly in the first 50 ms. Fitted to each speaker's own
    response at 2-4 kHz, it is 7-17 % of it in the run and 20-29 % in the
    check, with 30-60 % of it left unexplained by that fit.
  - **It is not a timing error:** a fixed shift of the right does not remove
    it (the best shift ranges from −109 to +53 µs between sets), and it does
    not rise 6 dB an octave, as a shift's error would.
  - **The played pair does not follow the two powers added either.**
- **The bass's cuts from the added pair** (built as the core builds them,
  the head at half the weight, the finer grid):
  - added: 42.6 Hz −3.5 dB, 46.5 Hz −12.0 dB, 57.0 Hz −3.6 dB;
  - played: 42.6 Hz −3.6 dB, 46.4 Hz −12.0 dB, 57.0 Hz −3.4 dB;
  - at the check's places the two lie within 0.03 dB rms of each other.

**The bass at the check's places** (fine curves; places 1-5, 1 the head):
D as played, the others with D's cuts taken back out. A is today's design,
B the finer detail alone, C the head's weight alone, D both of them.

| Design | Over the target, rms (dB) | Highest over (dB) | Further under (dB) |
|---|---|---|---|
| No cuts | 3.65 3.35 3.44 2.87 3.63 | 14.5 13.7 14.0 12.5 14.5 | 0 0 0 0 0 |
| A | 0.62 0.29 0.65 0.48 0.59 | 3.3 1.9 3.9 3.7 3.2 | 1.3 1.5 2.0 3.6 1.3 |
| B | 0.52 0.31 0.56 0.48 0.51 | 2.2 1.8 3.9 3.7 2.1 | 1.4 1.5 1.4 3.0 1.4 |
| C | 0.48 0.19 0.58 0.48 0.46 | 2.8 1.5 3.9 3.7 2.8 | 1.6 1.8 2.7 4.2 1.6 |
| D, played | 0.34 0.22 0.51 0.48 0.35 | 1.8 1.4 3.9 3.7 1.7 | 1.7 2.0 1.6 3.5 1.7 |

The core's design, rebuilt from the kept responses, gives the kept cuts
exactly.

**The ringing at the five check places,** each place's four sweeps
averaged. "Level" is the level 200 ms after the arrival, against the
uncorrected first 50 ms.

| | No cuts | A | D, played |
|---|---|---|---|
| 50 Hz decay (s; Fazenda's threshold 0.64) | 0.59-0.66 | 0.63-0.87 | 0.26-0.39 |
| 50 Hz level at 200 ms (dB) | −18 to −19 | −29 to −32 | −43 to −52 |
| 63 Hz level at 200 ms (dB) | −24 to −30 | −25 to −32 | −32 to −41 |

- **40 Hz:** the decay lengthens (0.93-1.00 s to 1.21-1.39 s with D) while
  the level at 200 ms falls by 1-4 dB.

**The joint cut against each speaker alone (C7):** bass played by one
speaker goes at most 3.6 dB further below the target with D, at 46 Hz (A:
2.0 dB at 44 Hz).

**Above the bass (Phase 30's acceptance 2),** 300 Hz-14 kHz at 1/3 octave,
each speaker against its own target, at the check's places:

| Speaker | Average, rms | Each place, rms (1-5) |
|---|---|---|
| Left | 1.06 → 0.60 dB | 1.63→1.43, 1.73→1.04, 1.92→1.33, 1.60→1.39, **1.20→1.65** |
| Right | 1.34 → 0.69 dB | 1.68→0.94, 1.95→1.47, **1.12→1.25**, 1.96→1.77, 2.01→1.22 |

**The places the player's check named worse:** 3 (by 1.6 dB), 4 (1.7) and
5 (3.3). Each is split into the microphone's move (the check with every
correction taken back out, against the run) and the correction's own
doing:
- **Place 4, the cut at 57 Hz:** +1.4 dB, all of it the move.
- **The rest are corrections above the bass:**
  - the left's at 721 Hz (place 5: +3.3 dB, of which the cut +1.9) and
    at 1594 Hz (place 5: +2.0, the raise +1.7);
  - the right's at 849 Hz (place 3: +1.6, the cut +1.8) and at 1849 Hz
    (place 4: +1.7, the raise +2.3).
- **With every position equal above the bass:**
  - the averages are L 0.53 and R 0.78 dB rms, and the head 1.60 and 1.28
    (against 1.43 and 0.94 with the head at half the weight);
  - the same places go further, by about as much: L place 5 at 722 Hz
    +1.6, R place 3 at 853 Hz +1.8, place 4 at 1848 Hz +1.8.

**C2, the right against the left at the head, 500 Hz-4 kHz:**

| Window | 3 ms | 6 ms | 20 ms |
|---|---|---|---|
| This run, two readings (dB) | +0.34, +0.17 | −1.43, −1.57 | −2.27, −2.40 |
| The morning's run (Finding 158) | −0.20, −0.15 | −0.60, −0.55 | −1.81, −1.78 |

At position 2, 6 ms: −0.67 and −0.66 dB.

**ADR-0185 C4's logs:**
- **The run:** the closest two of each set were 0.1-0.8 dB apart. One set was
  disturbed (position 5, left: 1.7 dB at 202 Hz), repeated, then 0.6.
- **The check:** each four within 0.1-0.3 dB.
- **Points judged:** 58-71 of 88 in the run and 42-71 in the check.
- **C8, under 10 dB above the noise after averaging:**
  - the left: 16 points, 20-95 Hz;
  - the right and both together: 14 points each, 20-22 Hz.

## What it means

- **D4 holds where the pair is used.** From 30 Hz up, the added pair is as
  close to the played pair as the played pair is to its own repeat, and the
  bass's cuts made from it are the same within 0.2 dB. Below 30 Hz the noise
  decides, and the cuts do nothing there (cuts only).
- **It does not hold above 2 kHz.** At 2-5 kHz the speakers played together
  are 1-3 dB quieter than the two played alone and added, at every
  position.
  - **The likely cause is the measuring chain.** Sound in a room adds as
    waves, so physically the two should match; untested.
  - **Nothing uses the pair above the bass.** Each speaker is corrected on
    its own there, and ADR-0186 D4 has no *Both* tab.
  - **It could still matter there.** Those corrections are fitted on each
    speaker played alone. If music, which plays both speakers at once, is
    quieter at 2-4 kHz than the two alone, the corrections are fitted to
    something other than what plays.
  - **Open:** its cause. **George decided the same day** that D4's test
    counts where the pair is used, the bass, and the together sweeps go;
    the check keeps a played pair at the head, which logs the gap
    (ADR-0187, *Measured again*).
- **D5 and C5 are confirmed at D3's heights in the bass:**
  - **The head:** 0.62 → 0.34 dB rms over the target, its highest point 3.3
    → 1.8 dB.
  - **The other places:** every one closer or level.
  - **Further under:** D takes three places 0.4-0.5 dB further under than A
    does, inside the core's 1 dB guard (`WORSE_DB`).
  - **The 50 Hz ringing:** under Fazenda's threshold at all five places, and
    11-22 dB quieter at 200 ms than with A.
- **Above the bass, the head's weight is not why places were named worse.**
  - **With every position equal,** the same places go further by about as
    much, and the head comes less close.
  - **The cause is placement.** The corrections at 0.7-1.9 kHz follow where
    the microphone stood: places 15-30 cm away go up to 2.3 dB further while
    the average comes closer.
  - **Acceptance 2:** as on Finding 158, it is met on average, not at every
    place.
- **C2's reading is set by the placement, not by its two readings' gap.**
  The two readings agree within 0.15 dB, but the head placed again moved the
  6 ms reading by 0.9 dB (−0.6 dB this morning, −1.5 dB now). This is for
  the setup check's design (ADR-0187 D1/C2).
- **The level** was 52 dB at the seat, so every figure above the noise is
  about 8 dB worse than a run at the aim.
