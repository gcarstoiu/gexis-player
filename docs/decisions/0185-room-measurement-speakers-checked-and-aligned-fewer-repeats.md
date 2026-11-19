# ADR-0185 — Room measurement: the speakers checked and aligned, fewer repeats

**Status:** **Proposed** 2026-11-19. George decided D1-D3 the same day, after
his full-range run on sofapi; C1-C4 are Claude's, for his approval.
**Amends:** [ADR-0175](0175-room-correction-for-the-bass.md) (the run) and
[ADR-0177](0177-room-correction-for-the-full-range.md) (its check and
chart). **Relates to:** ADR-0166 D7 (the delay after a member's client).

## Context

George's run on sofapi, 2026-11-19, full range, three positions (counts and
timings only):

- The room's noise 23 dB at the seat. The level reached 51 dB of the 60 aimed
  for (`AIM_DB`) with the output at its maximum and the sweeps at their cap
  (-8 dBFS in the band, their peaks at `SWEEP_PEAK_DBFS`): the player can go
  no louder.
- 27 sweeps repeated (`two sweeps disagree`): 5 while measuring (3 of the 9
  sets), 22 in the check, where every one of the 9 sets was repeated at least
  once and two reached `MAX_SWEEPS` (6). The run took 14 minutes.
- A set is repeated when its two closest sweeps differ by more than
  `AGREE_DB` (1.5 dB) at any one point from 20 to 250 Hz (`agree_db`). The
  limit was never checked against the microphone's own repeats, as its
  comment says. Where the room's noise is near the sweep (the deep bass, the
  speaker rolling off), noise alone can pass it (reasoned, not measured).
  The check's sweeps play lower by the corrections' highest raise
  (`_check_db`), which is likely why it repeated four times as often -
  likely, not shown: the sweeps' own noise was not logged.

George found, the same day:
1. The check's screen is a progress bar only: a repeated sweep is not said,
   so the same sweep seems to play again and again.
2. On the phone the two charts share one row, each as wide as its share of
   the axis, and the range above the bass is too compressed to read.
3. His speakers were connected left for right. Nothing in the run noticed.
4. Nothing says how far each speaker is, so a badly placed pair goes
   unnoticed.
5. Repeats should be rare, without giving up accuracy.

A speaker swapped left for right does not spoil a measurement - each
channel's correction is for whatever it drives - but swapping the cables
afterwards puts each speaker's corrections above the bass on the other (the
bass's cuts are the same on both, ADR-0175's amendment). So the check comes
before the corrections are kept.

## Decisions (George, 2026-11-19)

- **D1 — Left and right checked automatically at position 2**, about 40 cm
  to the left of the head: the left speaker must be heard nearer there than
  at position 1. Swapped, the run stops and says to swap the cables with the
  amplifier off, then measure again (position 1 was measured swapped).
- **D2 — The difference in distance measured before the sweeps, at
  position 1, shown and corrected**: the nearer speaker is delayed so both
  arrive together at the seat, a delay kept with the measurement. Beyond a
  limit (C2) the screen says the seat or a speaker looks out of place, and
  the run can go on. The two speakers' polarity is compared in the same
  recording; one with + and - swapped stops the run.
- **D3 — The player's own level only**: no step asking to turn the
  amplifier up. Fewer repeats come from C3.
- **D4 — The screens** (findings 1-2): the check's screen as the measuring
  one - a row per speaker, the sweep it is on, *A noise spoiled this sweep*
  when one is repeated; on the phone the two charts one under the other, each
  the full width. The panel and the bar keep the row.

## Claude's choices (for approval)

- **C1 — How the distance is measured.** One recording, so one playback and
  one capture and no start-up jitter between them (`Audio.play` starts
  `arecord` and `aplay` apart): a short sweep on the left, the right, then
  the left again, a fixed second apart. Each speaker's impulse response is
  found from its own sweep; the difference is where the right's lines up
  with the mean of the two lefts' (cross-correlation of the first
  milliseconds), which cancels the drift between the DAC's and the
  microphone's clocks to first order. At 48 kHz a sample is 7 mm. The sign
  of that correlation is the polarity. Measured twice; the two must agree
  within 1 cm, or it is measured again. Taken with the room's own delay
  (D2) out of the stage.
- **C2 — The delay and its limit.** A CamillaDSP `Delay` on the nearer
  channel, the difference over 343 m/s, in the stage with the cuts. The
  limit for the warning is 1 ms (34 cm): about where, in the literature,
  two speakers stop being heard as one image between them and the nearer
  takes it (summing localisation; Blauert, *Spatial Hearing*) - not
  measured here. A group's timing (ADR-0166 D7) goes by the undelayed
  channel: the delay belongs to the room, not to the chain.
- **C3 — Fewer repeats.** The quiet room is listened to longer (3 s for
  1.5) and its noise kept per 1/6 octave. Each sweep's signal over that noise
  is read at each point; **the repeat test looks only where it is 20 dB or
  more** - there noise alone moves a sweep by under 1 dB, so a gap over the
  limit is a disturbance (a door, a voice) and the sweep is repeated. Below
  20 dB a set is not repeated but averaged: every undisturbed sweep goes into
  the power average, not only the closest pair, and a point still under
  10 dB after it is left uncorrected (no cut or raise is fitted to noise).
  The check, playing lower, averages more sweeps for it. `MAX_SWEEPS` and the
  sweep's 8 s stay until the logs (C4) say otherwise.
- **C4 — Evidence first.** Every set logs, as numbers only, each pair's
  largest gap, where it was and the signal over noise there, so `AGREE_DB`
  and the 20 dB are settled from runs, not assumed. No recording is kept: a
  room's sound can hold voices.

## Consequences

- A run gains one short recording at position 1 and one at position 2,
  about 10 s in all; fewer repeats should more than give it back - to be
  seen in the logs.
- The measurement keeps a delay (ms, channel) beside its cuts; one kept
  from before has none. The chart and the result say the difference.
- What changes for users goes into the manual's room correction section;
  how it works into `docs/tech/audio-path.md`.
- Not covered: the actual distance to each speaker (it would need a timing
  reference the player does not have, or the user typing it in), and a
  difference in level between the speakers.
