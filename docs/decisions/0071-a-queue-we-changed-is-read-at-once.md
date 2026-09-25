# ADR-0071 — A queue this daemon changed is read at once

**Status:** **Accepted and built**, 2026-09-25. George: *"The clear button
takes some time before it clears all the tracks."*
**Date:** 2026-09-25
**Relates to:** [ADR-0038](0038-library-and-radio-on-the-panel.md) §1 (the
rail), [ADR-0062](0062-the-queue-removes-by-swipe.md) (the swipe, whose
animation this changed), [Finding 029](../findings/029-what-lms-answers.md)
§1a (`playlist_timestamp` says when the queue is worth re-reading)

## Context

Tapping **Clear** emptied the rail about a second and a third after the tap.
Nothing in that second was work:

| | |
| --- | --- |
| the panel's request reaches the daemon | ~70 ms |
| **the daemon has cleared the queue and replied** | **~115 ms** |
| LMS can hand over all 467 rows when asked | 27 ms |
| the rail actually empties | **~1,350 ms** |

The rail learns that the queue changed from LMS's own push, and that push
arrives about **1.2 seconds** after the command it answers. So the panel was
waiting to be told something it had just done itself.

## Decision

**After this daemon changes the queue, it re-reads it immediately.**

`LmsLibrary` calls back after any command that changes the queue — a queue
action (play a position, remove, clear) and a play or add of an album,
artist, track or playlist — and the adapter reads the status and publishes
the new queue without waiting for the push.

- **Only for changes we made.** A change from a phone or the server still
  arrives by the push, which is the only way to hear about it.
- **A failed re-read is not a failed action.** The push brings it along a
  second later either way, so the callback's errors are logged and
  swallowed: the tap must not report an error for a command that worked.
- **The stamp still guards it.** `_report_queue_if_changed` compares
  `playlist_timestamp`, so the push that follows costs nothing.

| | before | after |
| --- | --- | --- |
| the daemon's own queue empties | 1,268 ms | **39 ms** |
| the rail empties | 1,345–1,354 ms | **162–167 ms** |

## What it broke, and how that was fixed

**The swipe's removal animation was timed against that lost second.** The
row collapsed its own height over 250 ms while the queue took 1.2 s to come
back, so the collapse always finished first. With the queue returning in
160 ms the node was destroyed mid-animation and **the list jumped 54 px in
one step**.

Shortening the collapse only narrowed the race. So the row no longer
collapses at all: it slides out and fades, and **the rows below it are moved
by `animate:flip`**, which is smooth whenever the update lands rather than
needing to arrive after it. Measured on the row below a removal: nine or ten
eased steps — 27, 10, 7, 7, 4, 4, 2, 1, 1 px — settling at 657–693 ms.

**The flip is gated.** A windowed list moves its rows on every scroll as the
spacer above them changes, and animating that would fight the scroll, so the
animation has a duration only in the second after a removal. Measured with
it present: the rail still scrolls at **59.2 frames a second, 0.00 %
dropped**, and a removal drops 0.0–0.98 %.

## Consequences

- **Every queue action feels immediate**, not just Clear: play-from-here,
  remove, and playing or adding an album.
- **One more round trip per action.** A status query is 22–27 ms against
  George's server, against a second of waiting.
- **Two routes to the same update.** Ours and the push. The stamp makes the
  second a no-op, and a change from elsewhere still only has the push.
