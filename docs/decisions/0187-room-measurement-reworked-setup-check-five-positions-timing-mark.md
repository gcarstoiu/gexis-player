# ADR-0187 — Room measurement reworked: a setup check, five positions, a timing mark on every sweep

**Status:** **Accepted** 2026-11-20 (George approved C1-C10). Proposed
the same day; George decided D1-D9; C1-C10 are Claude's. Phase 37
(`ph-room-measurement`).
**Amends:** [ADR-0175](0175-room-correction-for-the-bass.md) (three
positions, equal weights, the bass fitted at 1/6 octave),
[ADR-0185](0185-room-measurement-speakers-checked-and-aligned-fewer-repeats.md)
(D1's check moves into the setup check) and
[ADR-0186](0186-room-chart-both-in-the-bass-only-shading-the-corrections.md)
D4 (the joint sweep, once D4 here is proven). **Builds on:**
[Finding 141](../findings/141-room-correction-above-the-bass-what-is-known.md),
[Finding 144](../findings/144-room-correction-above-the-bass-one-room-measured.md),
[Finding 151](../findings/151-room-correction-thins-the-voice-range.md).
**Relates to:** Phase 34 (the correction in time), which keeps its own
question. *Phase 34 closed 2026-11-21 without being built (George, on
[Finding 155](../findings/155-room-correction-in-time-what-research-shows.md)).*
**Measured:** [Finding 158](../findings/158-room-measurement-five-positions-on-sofapi.md)
(2026-11-23, George's run on the research build): D5 kept at half, C5 kept
with it; see *Measured* below.

## Context

George asked, after ADR-0186, for the correction to be looked at as a whole
against established practice: the bass, the range above it, how many
positions, phase, distance, and measuring the speakers apart or together.
Desk research followed on 2026-11-19 (five searches; sources named below
where used). A first proposal built on it reopened decisions of 3, 5 and 7
November without saying so; the strategy George decided from marked each
point as decided, measured or new.

**What the research added to Finding 141:**
- **Level:** the documented systems match the speakers' level with their
  timing at the main seat (Dirac: the first position sets gains and delays).
  In one listening study (Sengpiel, 25 listeners) 3 dB moved a centred image
  a quarter of the way to the louder side.
- **Positions:** Trinnov 3-5, Anthem 5 (up to 10), Audyssey 6-8, Dirac at
  least 5 (9-17); height varied (Anthem 15-30 cm, Dirac "a volume rather than
  a surface"); at least 30 cm apart (Dirac), within about 60 cm (Audyssey).
  No study gives an optimum for one seat.
- **Speakers designed together** are measured each alone with a timing
  reference and added in software (MSO requires it; Dirac's Bass Control); a
  sweep of all together is at most a check. With a microphone on its own
  clock: REW's acoustic timing reference, Dirac's closing sweep, Focus
  Fidelity's 1-2-1 - the last is ADR-0185 C1's method.
- **Bass resolution:** REW fits at 1/48 octave below 100 Hz. At ADR-0175's
  1/6 octave a +12 dB peak at 50 Hz with Q 15 reads +8.2 dB and nearly four
  times as wide (the core's own smoothing; arithmetic).
- **Ringing:** with music, decay is heard from about 0.5 s at 63 Hz to
  0.12 s at 250 Hz (Fazenda et al. 2015).
- **Main seat:** in Harman's test (Olive 2009) its curve predicted preference
  better than an average of seats; no study gives a weight.
- No two-channel product found that checks for swapped speakers, explains
  dips or advises placement.

**What stands, decided and measured:** cuts only (ADR-0175 D2, 3 Nov: the one
dip every position shared was 8-18 dB deep and moved - a cancellation);
the bass designed from both together (17 Nov, Finding 151); cuts as deep as
needed, stacked, most positions deciding (5 Nov); at most 3 dB above the
bass and the speaker's own slope (7 Nov; Finding 144: the benefit stops at
3 dB); filters to 14 kHz (10 Nov; 8-16 kHz within 0.1 dB); Full range after
a new measurement (7 Nov); *Left* and *Right* tabs (ADR-0186 D4).

## Decisions (George, 2026-11-20)

- **D1 — A setup check, its own step before the measurement** (George's
  proposal): left and right (ADR-0185 D1), polarity and the distance's
  difference (D2), and the level (D2 here). What it finds can be put right -
  a cable, a speaker moved - and the check run again before any measuring.
- **D2 — The level matched in full, no warning.** The louder speaker is
  turned down by the whole measured difference once two readings agree; the
  result says it, as it says the delay. Over: Dirac's ±0.2 dB tolerance
  (vendor advice, no data published); a warning from 3 dB; reporting only.
- **D3 — Five positions, around the head:** 1 the head; 2 40 cm left and
  15 cm up; 3 40 cm right and 15 cm down; 4 30 cm in front; 5 30 cm above
  the head. Replaces ADR-0175's three (5 Nov). Over: measuring the benefit
  on sofapi first; leaving it with Phase 34; wider (to 60 cm); sideways only.
  The distances are a guide, placed by eye: no user places a microphone
  precisely (George, 2026-11-20). So every change is judged on the check's
  positions, placed again.
- **D4 — A timing mark on every sweep; the together sweeps go once
  proven:** the pair added up by the player must match the pair played
  together, at every position on sofapi, as closely as two repeated sweeps
  agree. One played pair stays in the check, at the head. Over: keeping the
  together sweeps, with or without the mark.
- **D5 — The head counts more** (agreed 2026-11-20), **how much from
  data:** tried on sofapi at half the weight (as much as the other four
  together), kept if the check shows the head closer to the target and no
  other position worse beyond the guard. Over: half or double, fixed; equal.
- **D6 — Cuts only in the bass, confirmed** (ADR-0175 D2), over small boosts
  for broad dips, agreed earlier the same day without the 3 November data.
  Revisited only if the timing mark shows a dip to be correctable, and then
  measured first.
- **D7 — The bass's ringing checked** (agreed 2026-11-20), before and after;
  how it is shown is decided later.
- **D8 — The dips the correction leaves explained** (agreed 2026-11-20),
  with a hint where placement is the likely cause; George decides the words.
- **D9 — A phase of its own, now:** Phase 37. Phase 34 keeps the correction
  in time.

**Owed later:** the bass on each speaker's tab - cut for the pair, a speaker
alone can sit far from its target (on George's run of 19 Nov up to 8 dB over
and 18 dB under, the pair within −3.8/+1.8 dB) - decided when ADR-0186 D4's
chart is resumed; whether a noisy room may lengthen the run, after the logs.

## Claude's choices (approved 2026-11-20)

- **C1 — The setup check's flow.** At the head, ADR-0185's left-right-left
  recording gives the timing, the polarity and now the level; at position 2's
  spot, the left/right check. A swap or a reversed polarity stops it, as
  now, before any measuring sweep. The delay and the level are staged before
  the measurement's first sweep, as the delay is today. The measurement then
  starts at the head.
- **C2 — How the level is read.** From that recording: each arrival's level
  over 500 Hz-4 kHz (the timing sweeps cover 500 Hz-20 kHz), in a window of
  a few cycles after the arrival so the direct sound weighs more than the
  room (Trinnov's level window); the right against the mean of the two
  lefts. Two readings within 0.25 dB to start, settled from the logs as
  ADR-0185 C4 settles its limits; otherwise nothing is matched and the result
  says the level could not be read. A CamillaDSP `Gain` on the louder
  channel, in the stage with the delay, kept with the measurement; a cut, so
  no headroom is needed.
- **C3 — Five positions ship with D4**, so the run keeps about today's
  sweeps: two sets a position, 10 against today's 9; before it, five would
  take 15.
- **C4 — The timing mark** is REW's acoustic timing reference: each
  measuring sweep follows, in the same playback, a short sweep on the left
  speaker (the timing step's, 500 Hz-20 kHz) a fixed time before it, and
  each response is placed by it, so both speakers' responses at a position
  share one reference. The pair is the two added as waves at each position;
  positions are then power-averaged, as now. The proof (D4) runs on a
  research build on sofapi; afterwards the check's played pair at the head
  logs how far the added pair is from it.
- **C5 — The bass's cuts fitted on finer detail:** 1/48 octave below 100 Hz,
  widening to 1/24 at 250 Hz (REW's variable smoothing), on a finer grid
  there. Kept only if sofapi's check shows the peaks closer to the target
  and no position worse.
- **C6 — The ringing:** decay per third of an octave from 20 to 250 Hz, from
  the head's responses before and after, against Fazenda's thresholds;
  logged as numbers; shown as D7 decides.
- **C7 — A joint cut against the speakers alone:** each run logs how far
  each cut takes the two speakers' power sum - what bass that differs
  between the channels meets - below the target. On George's run of 19 Nov,
  2.8 dB at 46 Hz at most. No cap.
- **C8 — Repeats added as waves** (lined up, so the noise partly cancels)
  only if the logs of George's next run show bass left uncorrected for noise
  (ADR-0185 C4).
- **C9 — The dips' causes** (D8), with C4's responses: in the pair but not
  in the speakers' power sum - a cancellation between them; strongly
  different between positions - local; near a quarter wavelength of a
  speaker's distance to a wall - that wall.
- **C10 — A measurement kept from before** keeps its three positions, no
  level and its together curves, shown as now; measuring again brings the
  new.

## Consequences

- The run: the setup check adds about 10 s and a microphone move; with D4,
  two more positions to place and about today's sweeps.
- `GET /room-correction` gains the level (dB, channel) and five positions;
  the manual's room correction section and the technical guide
  (`audio-path.md`, `api.md`, `ui.md`) follow.
- The screens - the setup check, a guide to five positions with height -
  are designed before they are built.
- For ADR-0022's inventory, after George confirms: [H] five positions
  (replacing three); [H] the level matched in full; [H] the head's weight,
  after D5's trial.
- Not covered: each speaker's actual distance (it would need a reference the
  player does not have); boosts (D6); the correction in time (Phase 34).

## Measured (2026-11-23, Finding 158)

George's run on the research build: five positions and their check, 48 dB at
the seat (12 dB short of the aim). Each change judged at the check's places,
placed again by eye.
- **D5 kept at half:** the head counts as much as the other four together,
  in the power average and in the positions' vote. At the check's head: 0.50
  to 0.40 dB rms over the target, its highest point 2.2 to 1.8 dB; every
  other place closer; none more than 0.5 dB further under, within
  `WORSE_DB`. Applied above the bass too: there it halves the head's worst
  point (1.5 to 0.7 dB at one correction).
- **C5 kept with D5:** with the head's weight, the finer detail leaves no
  place worse on the fine curves and lowers the head's highest point to
  1.3 dB. At 1/6 octave the two are within 0.04 dB. The 50 Hz ringing is
  shorter at all five places and under Fazenda's threshold at each - today's
  design leaves it over at two. Alone, without the head's weight, it changed
  almost nothing.
- **C6:** what rings is 17-30 dB quieter at 200 ms in the 50 Hz band, but a
  band's decay time can lengthen where a cut takes out its strongest mode.
  The level at fixed times is logged beside the decay time; D7 is decided
  on both.
- **C7:** design D takes bass played by one speaker 4.5 dB under the target
  at 46 Hz (today's 3.3 dB). Logged, no cap.
- **C2:** the window is 6 ms (three cycles at 500 Hz): the right 0.60 and
  0.55 dB under the left at the head, the two readings 0.05 dB apart. 3 ms
  read 0.2 dB, 20 ms 1.8 dB. The playback's first tens of milliseconds are
  partly lost, so the timing signal is led by 0.25 s of silence.
- **C8 not needed:** the only bass left uncorrected for noise, in the
  design from both speakers, lay at 20-21 Hz, under the target.

**As built (2026-11-23, `ph-room-measurement`):** the head repeated so it is
half the set (`room_dsp.head_counts_more`), in the bass and above it; the
bass's cuts fitted on a 1/96-octave grid to 500 Hz against the target
carried over from the 1/24-octave one, a peak placed by that grid's own
step. On George's kept run the code gives at the check's places 0.38 dB rms
over the target at the head (today's design 0.50), no place's highest point
more than 0.1 dB higher, less over-cut than today's at every place, and a
50 Hz decay of 0.36-0.48 s (today's 0.46-0.67 s). The curves kept and drawn
stay the five as measured, on the 1/24-octave grid.
Also built the same day: **C4**, every measuring sweep after the timing
step's short sweep on the left, a second before it in the same playback
(`room_dsp.marked`, `mark_at`); deconvolved with the sweep where it plays,
the mark's trace lands seconds before the arrival, outside the window, and
the measured curve is unchanged (within 0.2 dB, 20 Hz-16 kHz, in the made-up
room). The together sweeps stay until D4 is proven on sofapi, on a second
research build that keeps each sweep's mark. And **C2's lead**: the
distance step's three short sweeps after 0.25 s of silence.

