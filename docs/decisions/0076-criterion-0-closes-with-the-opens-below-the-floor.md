# ADR-0076 — Criterion 0 closes with the screen opens below the floor

**Status:** **Accepted**, 2026-09-25. George: *"As of now I would close
criterion 0 and have more time of actual usage to see whether further
optimisation is needed. The panel feels fast based on current interaction."*
**Date:** 2026-09-25
**Revisit:** **before Phase 13 is implemented** — see below.
**Relates to:** [Finding 067](../findings/067-what-the-panel-presents-at-the-end-of-criterion-0.md)
(the measurement this closes on), Phase 7a criterion 4 (the target),
[ADR-0067](0067-only-what-is-on-screen-is-built.md) and
[ADR-0060](0060-the-panel-background-gets-a-layer-of-its-own.md) (what got
it here)

## Context

Phase 7a set the floor: **under 2 % of frames dropped on every interaction,
no interaction below 55 fps, and George's own go-ahead.** Phase 9 criterion 0
is reaching it.

**The scrolls reach it and then some.** Every list on the panel now draws
56.9–59.5 frames a second and drops nothing, from a baseline where the
artist grid managed 25.5 and dropped 32 %.

**The screen opens do not.** Every one of them draws 30–53 frames a second
and drops 2.5–5.6 %. In use each is a single 200–400 ms transition, so the
shortfall is a frame or two per screen change; the panel reads as fast
rather than smooth at that moment.

## Decision

**Criterion 0 closes with the opens explicitly below the floor**, on
George's judgement from using the panel rather than on the numbers meeting
the target.

This is the same shape as Phase 7a, which *"closed with criterion 4 unmet,
deliberately"* — and it is recorded here so that it is a decision somebody
made and not a target quietly forgotten.

**What was weighed:**

- **What is felt continuously is done.** Scrolling is the panel's dominant
  motion and it is at the ceiling with nothing dropped.
- **What falls short is momentary.** A screen change is one transition; 5 %
  of it is one or two frames.
- **The remaining lever carries risk.** Roughly 190 ms of a ~280 ms
  transition is the home screen's own cards and covers being torn down
  ([Finding 067](../findings/067-what-the-panel-presents-at-the-end-of-criterion-0.md)).
  Keeping it mounted is the fix and can slow every other layout; it is not
  worth that risk on a panel George calls fast.
- **Use is better evidence than one evening's measurements.** Nobody has
  lived with this panel yet.

## When this is revisited

**Before Phase 13 is implemented** — first boot without a network, the setup
phase.

**Why there.** Phase 13 is the gate on *"anyone else owning one"*
(`DEVELOPMENT.md`): it is the point at which the panel stops being George's
and starts being a stranger's, set up by somebody who did not build it. A
first impression is made of screen changes, and a floor waived on the
judgement of the person who knows what the device is doing should not
survive that transition unexamined.

**What to do then:**

1. Retake [Finding 067](../findings/067-what-the-panel-presents-at-the-end-of-criterion-0.md)'s
   table. It is the comparison, and it was taken with one library on one
   device.
2. Bring George's lived verdict after months of use, which is the evidence
   this decision defers to.
3. If the opens still fall short and still matter, the measured lever is
   home's teardown.

## Consequences

- **The floor stands as written.** Nothing about Phase 7a's target changes;
  one phase is closing without meeting part of it, in writing.
- **`tools/panel-frames.py` is the instrument either way**, so the
  comparison will be like for like — with the corrections it has taken
  since (LESSONS 27, 30, 32, 35).
