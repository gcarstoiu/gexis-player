# ADR-0069 — What a lookup cost is remembered, though its answer is not

**Status:** **Accepted and built**, 2026-09-25. George: *"If it can be fixed
it should as otherwise the fix turns into a 30 seconds wait which is worse
than before."*
**Date:** 2026-09-25
**Relates to:** [Finding 065](../findings/065-one-artist-stalls-a-batch-for-thirty-seconds.md)
(the measurement), [Finding 036](../findings/036-a-provider-that-could-not-be-asked-has-not-answered.md)
(the rule this bends and keeps),
[ADR-0068](0068-the-sweeps-portrait-is-asked-for-first.md) (which walks into
it)

## Context

[Finding 036](../findings/036-a-provider-that-could-not-be-asked-has-not-answered.md)
settled that **a provider that could not be asked has not said there is
nothing**, so nothing is written down. `artistinfo` follows it: a photo
lookup that never comes back sets an in-memory cooldown and stores nothing.

That is right, and it had a cost nobody had measured. One artist on George's
library — id **9934** — holds its lookup until `CALL_TIMEOUT_S`, thirty
seconds, and the lookups in a batch are gathered, so **that one artist holds
a batch of fifty for thirty seconds**. The cooldown keeps it from happening
twice in a process, and every restart is a new process.

Asking for the library's portraits therefore cost **31 seconds after every
restart of `gexis-core`**, measured three times: 30,327, 30,461 and 30,646
ms — and five of its six batches were instant.

[ADR-0068](0068-the-sweeps-portrait-is-asked-for-first.md) made that worse
by asking for the whole library up front, which is George's point: a fix
that turns into a thirty-second wait is not a fix.

## Decision

**Remember that asking cost us, and when. Never remember an answer.**

- A lookup that does not come back writes the clock into its own namespace,
  `artist-photo-slow`. **The photo namespace is untouched**, so nothing is
  recorded as "this artist has no picture" — Finding 036's rule is intact.
- On a cold start, an artist with no stored photo has that marker read back
  and turned into the same cooldown the process would have held.
- **It lives a day.** Long enough that nobody meets it twice in an evening;
  short enough that an artist whose picture the plugin later has is not
  written off. The in-process cooldown stays five minutes.
- **A rescan drops it**, with the photos, because a renumbered id is a
  different artist and what the old one cost says nothing about the new one
  ([Finding 029](../findings/029-what-lms-answers.md) §4).

| asking for all 917 portraits | before | after |
| --- | --- | --- |
| straight after a restart | 30,327–30,646 ms | **116–200 ms** |
| warm | 180 ms | 180 ms |

The store now holds exactly one such marker, for id 9934.

## Consequences

- **The thirty seconds is paid once**, when the artist is first met, and not
  again for a day. It was paid on every restart.
- **That artist keeps no picture.** This makes nothing appear; it stops the
  panel paying repeatedly to be told nothing.
- **A day is a guess.** It was not measured, because what it trades is the
  chance the plugin acquires a picture overnight against thirty seconds, and
  no evidence distinguishes 12 hours from 48.
- **The batch still stalls the first time.** Answering a batch with what it
  has and letting a straggler arrive later is a different design, not
  measured, and not built.
