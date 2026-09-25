# ADR-0063 — The queue is as long as LMS says it may be

**Status:** **Accepted**, 2026-09-24. George: *"Increase the queue to
whatever is set in Lms. This is a setting there that we should follow."*
**Date:** 2026-09-24
**Relates to:** [ADR-0038](0038-library-and-radio-on-the-panel.md) §1 (the
rail), [ADR-0064](0064-queue-rows-have-identities.md) (which this made
necessary), [Finding 029](../findings/029-what-lms-answers.md) (how the
queue is read)

## Context

The adapter read `QUEUE_LIMIT = 100` rows of the queue, on the reasoning
that *"the design shows what is coming up, not a whole 500-track load"*.

That is a guess at what its owner wants, and its owner has already said:
LMS has `maxPlaylistLength` under Settings → Advanced → Performance. It is
**2500** on George's server, and his queue was 190 tracks — so the rail was
showing him half of it.

**And the window was not merely short, it was wrong.** Removing a track from
a queue longer than the window refills the window from beyond itself, so
its length does not change — which the panel used as its signal that the
removal had happened. The row stayed swiped open over its own *Remove*
while the list shifted up behind it.

## Decision

**Read `maxPlaylistLength` from the server and use it.**

- **Once per run.** It is a preference someone sets and forgets, and the
  queue is re-read on every change. A restart re-reads it, which is the
  cadence of the rest of the adapter's setup.
- **`0` means unlimited in LMS**, and unlimited is not a number to put in a
  request, so it becomes `QUEUE_CEILING` — 2500 — as does anything above it.
- **A server that will not answer keeps the old 100.** An older LMS, or one
  that refuses the preference, still gets a rail. The fallback is logged.

## Consequences

- **The rail renders every row it is given.** At 190 that is nothing; at
  2500 it is the artist grid's problem, which
  [Finding 063](../findings/063-the-panel-builds-every-row-before-it-draws-one.md)
  measures at 2–3 ms a row. **Nobody has loaded a 2500-track queue on this
  device**, and if the rail ever feels slow to open, that is this and the
  fix is ADR-0065's.
- **A longer queue is a bigger state push.** The queue is republished
  whenever LMS says it moved, not on a timer, so this costs on queue
  changes rather than continuously. Not measured at 2500.
