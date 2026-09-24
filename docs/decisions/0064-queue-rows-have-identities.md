# ADR-0064 — A queue row is identified by its track, not its position

**Status:** **Accepted**, 2026-09-24, after three failed attempts at the
symptom. George: *"it is choppy when the rest of the tracks go up by one"*.
**Date:** 2026-09-24
**Relates to:** [ADR-0062](0062-the-queue-removes-by-swipe.md) (the swipe
this broke), [ADR-0063](0063-the-queue-is-as-long-as-lms-says.md),
[LESSONS](../LESSONS.md) case 31

## Context

The rail's rows were keyed by their position in the queue:

```svelte
{#each rows as item, offset (index + offset)}
```

A position is not an identity. Remove the track at 7 and the old 8 *becomes*
7, so every key still exists and Svelte keeps every node, handing each one a
different track's contents. One removal from a 190-track queue rewrote about
180 titles, artists and cover images — which is the chop.

**And the swiped row was never destroyed.** It was handed the next track,
while still carrying the swipe's state, so clearing that state transitioned
it from `translateX(-100%)` back to 0: the removed track appeared to slide
back in before vanishing.

**Three attempts treated this as a timing problem** — when to clear the
swiped state — and all three failed. The third read and wrote the same state
inside one `$effect`, which made the effect its own trigger and left the
panel not answering at all.

## Decision

**`TrackMetadata` carries `track_id`, and the rail keys on it.**

- **LMS supplies it** per row of `playlist_loop`, alongside the tags already
  asked for. The other two renderers have no queue.
- **A queue may hold the same track twice**, and two rows may not share a
  key, so the key is `<track id>#<nth occurrence>`. That makes a duplicate's
  key depend on how many come before it, which is wrong only for duplicates
  and only when an earlier one is removed.
- **A row with no id falls back to its position**, which is what the whole
  queue did before this.

## Consequences

- **A removal removes one node.** The rest keep their contents and their
  DOM, so the list closes up instead of being rewritten.
- **The swiped row is destroyed rather than recycled**, so there is nothing
  to animate home. The `is-snapping` workaround built for that is gone, and
  so is the effect that froze the panel.
- **`track_id` is on `TrackMetadata`, which every renderer publishes.** It
  is `None` everywhere but an LMS queue row. The alternative — a queue-only
  row type — is a second shape for the panel to know about, for one field.
