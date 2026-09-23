# ADR-0059 — Where the artist list's portraits come from

**Status:** **Proposed**, 2026-09-23 — George asked for options before a
decision: *"can you give me options on how to do this? One larger prefetch
working in the background, on the go when scrolling (although this might
make it slow) or any other option that could work."*
**Date:** 2026-09-23
**Raised by:** George: *"the artist navigation holds currently the LMS
artist portraits. Those are though of questionable quality so I would like
to change them with ones from fanart, having LMS as fall back."*
**Measured in:** [Finding 054](../findings/054-what-lms-knows-about-artist-identity.md)
**Relates to:** [ADR-0012](0012-enrichment-additive-only.md) (enrichment is
additive and caches its misses), [ADR-0040](0040-enrichment-providers.md)
(the providers), [ADR-0038](0038-library-and-radio-on-the-panel.md) §7 (the
picture ladder)

## Context

**The decision itself is already taken.** George chose fanart over LMS for
artist pictures on 2026-09-18, and the artist *page* has done it since. This
record is only about the **list** — the two grids in Library — which still
draws LMS's own photo.

Three measured facts shape it (Finding 054):

- **LMS cannot tell us who the artist is on MusicBrainz.** His files carry
  no MusicBrainz tags, so the columns LMS has for it are empty. The id has
  to come from MusicBrainz's *search*, by name.
- **A cold artist costs 1.5–5.3 s**, almost all of it MusicBrainz's one
  request per second and its 503s. **822 of 7,296** are already resolved
  from ordinary browsing; **6,474 are not**, which is **three to nine hours**
  of wall clock however the work is arranged.
- **The pictures cost nothing to keep.** Only the URL is stored; LMS's image
  proxy fetches, resizes and caches the file.

## The options

**A — one background sweep.** Walk all 7,296 once, at MusicBrainz's pace,
and stop. *For:* the list is complete and instant afterwards, and it is a
single job with a progress line. *Against:* three to nine hours on first
run; asks MusicBrainz about thousands of artists nobody will look at; the
sweep must survive restarts and must not treat a 503 as "no such artist"
(Finding 036's most important line).

**B — on the go, as the list scrolls.** Resolve only what is drawn. *For:*
no wasted work, nothing to schedule. *Against:* 1.5–5.3 s per artist means
the portrait lands long after the tile does — and a fast scroll queues
hundreds of requests for rows nobody stopped on. Needs the queue cancelled
on scroll, which is real work.

**C — both: on-screen first, the rest in the gaps.** What is visible jumps
the queue; a slow sweep fills the remainder while nothing else is asking.
*For:* the artists George actually browses are right within seconds, and the
library completes itself over a few evenings without a long blocking job.
*Against:* two producers on one rate limiter, which is the part that has to
be got right.

**D — only the artists he plays.** Seed from LMS's most-played and
recently-played, sweep those, leave the long tail on LMS. *For:* perhaps a
few hundred artists, so under an hour; the pictures that get looked at are
the ones that get fixed. *Against:* the tail stays visibly mixed, and
"most played" is a different set from "browsed".

**E — leave the list alone.** fanart on the artist page, LMS in the list.
*For:* it is today, and it costs nothing. *Against:* it is what George asked
to change.

## Recommendation

**C, ordered by D.** On-screen artists resolve first; a background sweep
works through the rest **most-played first**, so the list improves where he
looks before it improves everywhere. One shared rate limiter with the screen
having priority.

**And, whichever is chosen: LMS's picture draws immediately and fanart
replaces it when it arrives.** Never an empty tile, never a spinner — the
list is a navigation surface and must not wait on the network. That is
[ADR-0012](0012-enrichment-additive-only.md)'s additive rule applied to a
picture.

## Open

- **Which option.** George's.
- **What "no picture anywhere" looks like.** LMS has *something* for most
  artists; the grid's existing `failed` set already handles a broken URL.
- **Whether the sweep is a setting or a button.** A row that says how many
  artists are resolved, with a "look up the rest" action, is one shape; a
  silent background job is another. Not decided.
- **Ambiguous names.** MusicBrainz search returns a score and ADR-0012 has a
  confidence threshold; nothing has tested it on `Head`, which is exactly
  the kind of name that goes wrong. Worth a check before a sweep asks it
  6,474 times.
