# ADR-0072 — A toggle reads its own state back

**Status:** **Accepted and built**, 2026-09-25. George: *"Check as well the
shuffle button as the green fill upon tapping comes somewhat late."*
**Date:** 2026-09-25
**Relates to:** [ADR-0071](0071-a-queue-we-changed-is-read-at-once.md) (the
same shape of delay, on the queue), [ADR-0066](0066-a-home-card-says-it-was-pressed.md)
(feedback that does not wait for anything)

## Context

Shuffle draws its own state: the button is filled when the daemon reports
`shuffle: true`. The daemon answers the tap in **17–25 ms** and the reported
state changes at **558–576 ms**, because it waits for LMS's push — the same
delay [ADR-0071](0071-a-queue-we-changed-is-read-at-once.md) found on the
queue, in a different place.

The adapter's `_command` says why, deliberately: *"it reports nothing
itself: the CometD watch sees the result, so there is one path by which
state changes, whoever caused them."* That is a good rule and it costs half
a second on a control whose only job is to show its own state.

## Decision

**Shuffle and repeat read the status back, once, through the same path the
push uses.**

`_command` takes `read_back=True` for those two. It is **not an optimistic
guess**: the daemon asks LMS what the state now is and reports that through
`_report_metadata`, exactly as the push would. The push that follows says
the same thing.

**Not for play, pause, next or previous.** A status read straight after a
skip can catch LMS between tracks, and none of them has been measured as
late. The rule stands everywhere it has not been shown to cost something.

| | before | after |
| --- | --- | --- |
| the reported shuffle state changes | 558–576 ms | **51–59 ms** |
| the daemon's own reply | 17–25 ms | 34–41 ms |

## Consequences

- **The fill follows the finger**, within a frame or two of the command.
- **One more status query per toggle**, 20-odd ms, on a control tapped
  occasionally.
- **Play, pause and the skips are unmeasured**, and left alone. If any of
  them is late, this is the shape of the answer.
