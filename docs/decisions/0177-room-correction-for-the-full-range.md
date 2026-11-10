# ADR-0177 — Room correction for the full range

**Status:** **Proposed** 2026-11-10 (Claude), Phase 30
(`ph-room-correction-full`). George asked the same day for the build to go
ahead on it; decisions 1-4 below are his to confirm, and the build follows
the recommendations until he does. **Builds on:**
[ADR-0175](0175-room-correction-for-the-bass.md) (the bass, as built),
[ADR-0162](0162-a-simple-equaliser.md) (the stage and its headroom),
[Finding 141](../findings/141-room-correction-above-the-bass-what-is-known.md)
(the desk research) and
[Finding 144](../findings/144-room-correction-above-the-bass-one-room-measured.md)
(sofapi's room measured to 20 kHz). **The design:** `design/source/30/`
(Claude Design, 2026-11-08).

## Context

**What George set** (`docs/DEVELOPMENT.md`, Phase 30, 2026-11-07): the main
seat, from Phase 29's three positions with the sweeps to 20 kHz; the whole
range; the target above the bass the speaker's own slope in the room; at most
3 dB up or down, broad filters only; *Bass* or *Full range* for each output,
a new measurement starting at Full range and one from before held at Bass;
the level only (correction in time is Phase 34); in a group as the bass's
correction is.

**The design** (George's picks, 2026-11-08): the *Reaches* chips; the chart
split at 250 Hz; the corrections in two groups; *Without · Bass · Full range*
in the volume drawer. Its state: for each output the reach, the
measurement's range, and for each speaker the bass's cuts and the broad
corrections above. One dotted target throughout, the bass's rise joined at
250 Hz to the speaker's slope, which "the engine supplies".

**What the measurement found** (Finding 144, one room): repeated sweeps agree
within 0.4 dB above the bass and the microphone placed again moves the
three positions' average by less than 1 dB; the gaps above the bass are
mostly dips, so cuts alone do almost nothing and raises of up to 3 dB take
the gap from 2.0 to about 1.3 dB RMS; four to six broad filters are enough;
above 14 kHz the curves show the tweeter's own fall.

**Three positions** (George, 2026-11-10): kept, without the planned three
around the head; whether more positions help is checked separately later,
probably with the next room-correction phase (34).

## Proposed (Claude)

1. **The measurement** is Phase 29's run, step for step, with the sweeps
   from 10 Hz to 20 kHz over 8 s (built for Finding 144):
   - the level still read in the bass (20-500 Hz), the sweeps capped by
     their peaks at −1.5 dBFS;
   - every curve on one grid, 1/24 octave from 15 Hz to 20 kHz;
   - the calibration file kept whole; one kept by Phase 29 to 2 kHz is asked
     for again (George, 2026-11-08).
2. **The target above the bass is a straight line** on a logarithmic axis,
   fitted by least squares to the three positions' power average, smoothed
   to 1/3 octave, from 300 Hz to 10 kHz: the speaker's own slope (Finding
   144: +0.4 and −0.4 dB an octave in sofapi's room).
3. **One target throughout** (decision 1): from this phase on, the bass's
   target takes its level from that line (where it meets 250 Hz), not from
   the average from 250 to 500 Hz, so the two meet and the bass's cuts are
   the same list whatever the reach (the design's state).
4. **The corrections above the bass** are Peaking filters, for each speaker:
   - up to six, between 250 Hz and 14 kHz, each and all together within
     ±3 dB, Q 0.5 to 2 (0.7 to 2.5 octaves wide), at least a third of an
     octave apart;
   - fitted to the gap between the 1/3-octave average and the line: one at
     a time at the largest gap left, then all together by damped least
     squares, as the bass's cuts are;
   - a gap under 1.5 dB is left; when nothing above the bass is more than
     1.5 dB from the line, nothing is corrected there (*already within 1.5 dB
     of the speaker's own balance*);
   - **less where the positions disagree**: where the three positions'
     standard deviation is above 1.5 dB the gap counts for less, and not at
     all from 3 dB (in sofapi's room its median is 0.7-0.9 dB);
   - **most positions decide**, as for the bass's cuts: a filter that would
     leave more than half the positions more than 1 dB further from the
     target at its frequency is made smaller.
5. **Nothing is corrected above 14 kHz** (decision 2); the measurement and
   the chart go to 20 kHz.
6. **In the stage**: six more Peaking filters for each speaker, after the
   bass's eight (`room_l_9` to `room_l_14`), in the pipeline whenever it
   runs, at 0 dB when unused - so the reach, *Hear it without* and a new
   measurement change gains, never the pipeline's shape, and are heard at
   once. *Bass* sets the six to 0 dB; *Without* sets all fourteen.
7. **Headroom** (decision 3): the room's filters join the curve ADR-0162 D3
   lowers by, given back by the volume - the equaliser's bands and the
   room's corrections as measured, all of them, whatever the reach and
   *Without*, so *Bass*, *Full range* and *Without* compare at one level
   (under *Fixed* volume all three play that much quieter). The lowering is
   never less than the highest point of what plays.
8. **The check** plays the correction a new measurement starts with, Full
   range, at every position, and reports a position more than 1 dB further
   from the target at any cut's or filter's frequency (*Position 3 is 1.4 dB
   further from the target than before.*). What *Bass* would give is worked
   out from it: the filters' response taken out of the measured after, exact
   for filters in series.
9. **A measurement from before this phase** keeps its cuts, its curves to
   500 Hz and its range, *bass*: held at Bass, Full range locked until the
   room is measured again (the design's dashed chip and *Measure again for
   the full range*).
10. **The result's figures**, as the design works them out: *Peaks down by up
    to N dB* below 250 Hz; *within N dB of the speaker's own balance* the
    corrected average's largest gap from the line, 300 Hz to 14 kHz, at 1/3
    octave, rounded up to 0.5 dB, the larger of the two speakers; *already
    within 1.5 dB* from the room's own curve.
11. **The API**: `PUT /room-correction` takes `reach` (`bass` or `full`);
    the summary on `/state` and `GET /room-correction` give the reach and the
    measurement's range, and the page the corrections in two groups.
    Documented as the bass's was (ADR-0175 item 11).
12. **What it costs a Pi 4**: twelve more filters a stream, 48 filter
    channels in all against the ten bands' 20 that Finding 138 measured at
    2.3 % of one core at 44.1 kHz and 4.9 % at 192 kHz - at most about
    12 % at 192 kHz if the cost grew in proportion. An estimate: measured on
    sofapi in the preview at 44.1, 96 and 192 kHz, beside Phase 29's own
    measurement still owed.
13. **Groups**: as the bass's correction - the filters add no delay; a
    player in a group does not measure.

### Decisions for George

- **Decision 1, the bass's level.** (a) **From the line, for both reaches**,
  *recommended*: one target, one list of cuts, as the design draws them; in
  sofapi's room the left speaker's bass cuts come out 1.2 to 2.3 dB smaller
  than Phase 29's way, as its 315 Hz dip no longer pulls the level down
  (Finding 144). (b) *Bass* keeps Phase 29's level and *Full range* takes
  the line's: two lists, the bass's cuts changing with the reach, and a step
  in the target at 250 Hz under *Bass*. Claude said (b) on 2026-11-10 before
  reading the design's state, which has one list.
- **Decision 2, the top.** (a) **The filters stop at 14 kHz**, the chip
  stays as drawn (*Full range · 15 Hz to 20 kHz*, what is measured and
  shown), *recommended*: above it the curves are the tweeter's own fall and
  the positions disagree most (Finding 144); (b) to 20 kHz, which would raise
  the top octave by up to 3 dB.
- **Decision 3, the comparison's level.** (a) **One headroom** for Bass,
  Full range and Without, *recommended*: the comparison is the correction
  alone; (b) each its own, *Without* and *Bass* then up to 3 dB louder under
  *Fixed* volume or at the top of the slider.
- **Decision 4, the times** (the design left them for this measurement):
  *About five minutes* before a run (four now), *about four minutes more*
  for the check (three now), and *about a minute a position* (45 seconds
  now), from Finding 144's timings.

## Settings (ADR-0022)

Confirmed by George on 2026-11-07, to append with this ADR:
- **[N]** Bass or Full range, for each output.
- **[H]** Up to 20 kHz.
- **[H]** At most 3 dB up or down above the bass.
- **[H]** The speaker's own slope as the target above the bass.
- **[H]** The same three positions.

Proposed, to append only once George confirms:
- **[H]** Up to six broad filters above the bass, from 250 Hz to 14 kHz, Q 0.5
  to 2; a gap under 1.5 dB left.
- **[H]** The bass's target level taken from the line (decision 1).

## While building

On `ph-room-correction-full`, 2026-11-10; what differs from the proposal:

- **The bass's level is the line's value at 250 Hz** (item 3), not its mean
  from 250 to 500 Hz: the two then meet exactly. The mean is within 0.2 dB
  of it at the slopes Finding 144 measured.
- **No headroom while a run measures** (items 7-8): the stage would lower
  the run's own level by the raise, and at the run's maximum level the
  volume cannot give it back. The check's sweeps play lower by the broad
  corrections' highest point instead; the response is the recording over
  what was played, so its level is the room's.
- **Where the positions disagree the correction is held near none** (item
  4): the gap there counts for less, and the fit still weighs those
  frequencies, so a neighbouring filter's skirt is pulled out of them too.
  On a made-up room with one position dipping 9 dB at 3 kHz, the
  correction there is −0.2 dB; with all three dipping, +1.6 dB.
- **The curves are kept to a hundredth of a decibel**, not a tenth: on the
  ±5 dB pane a tenth showed as steps.
- **The equaliser's note keeps saying its own lowering**; room correction's
  share of the headroom is not shown anywhere (the design draws none).
- **The Settings row says the reach**, as the design's Audio page does:
  *Full range · measured 3 November*, *Bass · measured for the bass only*,
  *Without · comparing, no correction*.
- **The design as built on sofapi's run** (Finding 144's curves): left, five
  filters (252 Hz +2.7 dB, 389 Hz +2.7, 497 Hz −3.0, 1.05 kHz −1.7,
  2.39 kHz +1.8); right, four (318 Hz +2.1, 541 Hz −3.0, 1.99 kHz +2.7,
  7.87 kHz −1.3). Every position comes closer in both placings: the left
  2.01 to 1.44 dB RMS (the check's 1.95 to 1.43), the right 1.97 to 1.30
  (1.84 to 1.22); none more than 1.6 dB further at any frequency.

## Measured before it is called done

- DEVELOPMENT.md's acceptance 1-3; for 2, a finding on a measurement with
  the check run at Full range.
- The stage's cost at 44.1, 96 and 192 kHz, Full range on (item 12).
- The headroom given back, and the three choices at one level (item 7).

## Not in this phase

- Correction in time: Phase 34.
- More positions, or the whole sofa: checked separately, probably with
  Phase 34 (George, 2026-11-10).
