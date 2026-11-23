# ADR-0188 — The speakers aligned on their own: a check without the measurement, its own switch

**Status:** **Accepted** 2026-11-23 (George decided D1-D2 from mock-ups;
C1-C6 are Claude's). Phase 37 (`ph-room-measurement`).
**Amends:** [ADR-0187](0187-room-measurement-reworked-setup-check-five-positions-timing-mark.md)
D1 (the setup check, until now a step of the measurement only) and
[ADR-0185](0185-room-measurement-speakers-checked-and-aligned-fewer-repeats.md)
D2 (the delay kept with the measurement, heard only with room correction
on). **Relates to:** ADR-0175 (room correction's stage and *Hear it
without*).

## Context

George proposed on 20 November to split the measurement in two: the
speakers' distance, level and wiring measured on their own, and the room
afterwards. ADR-0187 D1 built the check as the measurement's own step
before the sweeps, so the delay and the level could only be had with a full
measurement, and were heard only with room correction on. George asked on
23 November why the check could not be run independently, and chose from a
sheet of mock-ups (made-up numbers) how it should sit on the room page.

## Decisions (George, 2026-11-23)

- **D1 — The alignment is its own (option A).** The room page gains a
  *Speakers* card with its own switch: the date checked, a ticked row for
  the wiring, the distance and the level, and *Check the speakers* (about
  two minutes with the microphone, at the head and then to its left). The
  delay and the level play whether room correction is on or off. The check
  on its own is three steps - the microphone, the level, the check - and
  ends on the list ADR-0187 decided, with *Discard*, *Check again* or
  *Keep*; *Keep* changes nothing in room correction. *Hear it without*
  takes out both room correction and the alignment. Over: the alignment as
  part of room correction, switched with it, with a second button beside
  *Measure again* (B).
- **D2 — A check that leaves the correction behind says so.** Kept after a
  measurement, a check whose delay or level differs from what the room was
  measured with says that room correction no longer fits exactly - in the
  bass the two speakers now add up differently - with *Discard*, *Keep* or
  *Keep and measure*. Kept, room correction's card carries an amber note and
  *Measure again* is lit until the room is measured again.

## Claude's choices

- **C1 — Kept per output, beside the measurement.** Each output keeps its
  alignment: on or off, the date, each speaker's delay and level, the
  distance's difference and what the check found of left and right. The
  measurement still keeps the delay and the level it was measured with,
  for D2. Keeping a measurement keeps its check as the alignment and
  switches it on: its sweeps were made with it. A measurement kept from
  before brings its delay and level across once, switched as room
  correction was, so nothing heard changes.
- **C2 — The stage.** The delay and the level come from the alignment while
  it is on, whatever room correction does; the stage is in the path when
  room correction is on or the alignment has something to delay or turn
  down. *Hear it without* can be set while either is on and sets all of it
  to nothing. The Settings row says *Speakers aligned* when only the
  alignment plays.
- **C3 — One run, two ways.** The check on its own is the measurement's
  run started for the speakers: the level, then ADR-0187's check, ending on
  its list. *Keep* stores the alignment and ends the run; *Keep and
  measure* stores it and goes on into the measurement - back to the head and
  the five positions - without checking again. No reading of the timing, no
  *Keep*.
- **C4 — When the correction no longer fits.** From the change in the
  delay between the speakers and in their levels against the measurement's:
  the most a pair adding in phase would move anywhere from 20 to 250 Hz.
  More than `WORSE_DB` (1 dB, the check's own guard for a place worse than
  before), D2 applies: the delay alone from about 0.6 ms (21 cm), the level
  alone from about 2 dB. A head placed again by eye moved the level reading
  by 0.9 dB (Finding 159), so a check repeated with nothing moved stays
  quiet. Switching the alignment off is not warned about: it is a choice,
  like *Hear it without*.
- **C5 — The check's two minutes.** The microphone's step and the level
  step as for a measurement; then the check as built (ADR-0187, *As built*,
  2026-11-23).
- **C6 — The panel and the bars** show the alignment once their screens
  are designed; until then they keep today's room page, with *Hear it
  without* live when either is on.

## Consequences

- `GET /room-correction` gains `speakers` (on, date, delay, level, distance,
  left and right) and `stale`; `PUT` takes `speakers`; `POST
  /room-correction/run` takes `speakers` to start the check alone, and
  `measure` as *Keep and measure*.
- The manual's room correction section, the FAQ, the README and the
  technical guide (`audio-path.md`, `api.md`, `ui.md`) follow.
- ADR-0022's inventory, after George confirms: the alignment's switch per
  output ([R]); C4's guard ([H]).
- Not covered: the panel's and the bars' screens (C6); the alignment for an
  output that plays to more than two speakers.

## As built (2026-11-23, `ph-room-measurement` d71d7110)

- **The store** (`room_correction.Alignment`, `OutputRoom.speakers`): on,
  the date, each speaker's delay and level, the distance, left and right,
  and the level as read; `Room.set_speakers`, `keep_speakers`, and `keep`
  taking the run's alignment. Stored before: brought across once when read,
  switched as room correction was.
- **Stale** (`OutputRoom.stale`, `pair_moves_db`, `STALE_DB` 1 dB): only
  where the measurement has cuts in the bass.
- **The run** (`room_run.Run(mode="speakers", measured=...)`): *ready*
  takes `keep`, `again` or `discard`; stale, `keep`, `keep_and_measure` or
  `discard`; nothing read, `again` or `discard`. *Keep* stores the alignment
  through `Host.align` at once; the run's progress is the check's own.
- **The routes:** `POST /room-correction/run {action: "speakers"}`, `PUT
  /room-correction {speakers}`; `GET` gives `speakers` and `stale`; the
  Settings row says *Speakers aligned* or *Off · speakers aligned*.
- **The phone** as drawn, without the mock-up's *New* badge and lit border,
  which marked the change on the sheet; the check opens on *Before* with
  *Check the speakers*, its steps 1-3 of 3; *far* offers *Carry on*. The
  panel's running screen says *Checking the speakers*, without positions.
