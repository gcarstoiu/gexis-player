# ADR-0189 — The room page as three steps, with a history to go back to

**Status:** **Accepted** 2026-11-25 (George decided D1-D2 from mock-ups;
C1-C7 are Claude's). Phase 37 (`ph-room-measurement`).
**Amends:** ADR-0175 (the room page), ADR-0188 C6 (the phone's page).
**Relates to:** ADR-0187 (the measurement, its check kept), ADR-0188 (the
speakers aligned on their own).

## Context

George found the room page unclear about what is there before a
measurement and what after (2026-11-25), and asked for a history of
measurements with a way back to any of them. From a canvas of mock-ups
(made-up numbers: A-C for the page in four states, H1-H3 for the history)
he chose B and H2. The mock-ups also showed that the phone skips the page
when nothing is measured, so the alignment and its switch never show and the
speaker check alone cannot be started from it.

## Decisions (George, 2026-11-25)

- **D1 — The page is three steps (B):** *Playing now* first - what plays,
  and *Hear it without* - then 1 *Speakers*, 2 *Room*, 3 *Checked* on one
  rail, each marked done, next or to do again, the next one lit. The
  alignment's switch, its rows and *Check the speakers* are in step 1;
  room correction's switch, its reach, its cuts and *Measure the room* (or
  *Measure again*) in step 2; the chart, the ringing and the dips in step 3.
  When a later check leaves the correction behind, step 2 turns amber with
  *Measure again* at its top. Over: what plays first (A); before and after
  side by side (C).
- **D2 — The history as the steps' timeline (H2):** under step 3,
  *Earlier*: every measurement and speaker check, newest first, a
  measurement as a node, a speaker check on its own as a smaller ring. A
  measurement opens in place with its chart as its check measured it and
  *Go back to this one*; going back asks first, saying what changes. Over:
  a section of its own (H1); a picker at the top (H3).

## Claude's choices

- **C1 — Always the page.** Never measured or speakers checked only, the
  phone shows the page (B1, B2), not the measurement's first screen; the
  microphone's and the calibration's checks stay on that screen.
- **C2 — What the history keeps:** per output, every measurement kept and
  every speaker check kept on its own, each with its date and time, newest
  first; a measurement whole (its check's curves included, ADR-0187
  2026-11-25) with the alignment it was measured with. Nothing is dropped;
  each entry its own file under the core's state, so the settings stay
  small. A measurement kept before the history begins is its first entry.
- **C3 — Going back** (H2c, H2d): its correction plays at once, the one it
  replaces moving into *Earlier*. Its alignment comes back with it when it
  is close to today's (the stale guard of ADR-0188 C4); when it is not, the
  dialog asks which: its own, or today's with the amber note until measured
  again (ADR-0188 D2).
- **C4 — A speaker check in *Earlier*** shows its delay and level; going
  back is for measurements, as drawn.
- **C5 — The steps** as B3 draws them; H2a's short steps stand for them on
  the sheet.
- **C6 — The API:** `GET /room-correction` gains `history` (each entry's
  summary); `GET /room-correction/history/{id}` gives one entry's chart;
  `POST /room-correction/restore` takes `id` and `alignment` (`its` or
  `today`).
- **C7 — Not covered:** the panel and the bars keep their screens; their
  history, if any, is for later.

## Consequences

- The manual's room correction section, the FAQ and the technical guide
  (`audio-path.md`, `api.md`, `ui.md`) follow.
- ADR-0022's inventory: to be proposed once built (the history kept whole,
  going back).
