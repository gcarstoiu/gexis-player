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

Four measured facts shape it (Finding 054):

- **LMS cannot tell us who the artist is on MusicBrainz.** His files carry
  no MusicBrainz tags, so the columns LMS has for it are empty. The id has
  to come from MusicBrainz's *search*, by name.
- **The list holds *album* artists, and there are 917.** George corrected
  the question after the first version of this record: *"I said artist when
  I should have said album artist which we actually have in the list."*
  **781 are already resolved; 89 are not.**
- **A first pass is two steps, and only the first has ever run.** 781 album
  artists have had their MusicBrainz id looked up; **none of the 870 has
  ever had a fanart call made for it**, because nothing in the list asks.
  89 searches at ~3.4 s plus 870 fanart calls at ~0.4 s is **ten to fifteen
  minutes** — not the three to nine hours this record first computed for all
  7,296 contributors, and not the "two to eight minutes" that followed it,
  which counted the searches alone.
- **fanart does not have a portrait for every artist.** Of three ids tried
  directly, one came back with none. The LMS fallback carries a real share
  of the list, not an edge case.
- **The pictures cost nothing to keep.** Only the URL is stored; LMS's image
  proxy fetches, resizes and caches the file.

**Which changes the answer.** The options below were written for a job
measured in hours. At eight minutes the scheduling question mostly
evaporates.

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

**A — one background sweep — now that it is 89 artists.** It runs once,
takes minutes, needs no queue, no cancellation on scroll and no priority
scheme, and afterwards the list is simply right. New album artists are a
handful at a time and can ride the same job after a library rescan.

C and D were written for a job measured in hours and are no longer worth
their complexity. **B is still wrong** on its own: a 1.5–5.3 s wait per tile
is the one thing a navigation list must not have.

**And, whichever is chosen: LMS's picture draws immediately and fanart
replaces it when it arrives.** Never an empty tile, never a spinner — the
list is a navigation surface and must not wait on the network. That is
[ADR-0012](0012-enrichment-additive-only.md)'s additive rule applied to a
picture.

## Album artwork

George, in the same message: *"Can we also get album artwork? What would
that cost."* It is a different question with a different price, because
album art is keyed on a MusicBrainz **release group** and needs its own
search per album.

- **LMS already has a cover for 4,412 of 4,567 albums.** 155 have none —
  3.4%, mostly editions and live bootlegs.
- **Filling those 155: about nine minutes.** `providers.CoverArtProvider`
  already does it, so this is scheduling, not building.
- **Replacing all 4,567 with fanart's or the Cover Art Archive's: four to
  seven hours**, and nothing measured says the covers LMS has are worse.

**Recommended: fill the 155, leave the rest.** The same background sweep can
carry it.

## Open

- **Which option**, and whether album art is the 155 or all 4,567. George's.
- **What "no picture anywhere" looks like.** LMS has *something* for most
  artists; the grid's existing `failed` set already handles a broken URL.
- **Whether the sweep is a setting or a button.** A row that says how many
  artists are resolved, with a "look up the rest" action, is one shape; a
  silent background job is another. Not decided.
- **Ambiguous names.** MusicBrainz search returns a score and ADR-0012 has a
  confidence threshold; nothing has tested it on `Head`, which is exactly
  the kind of name that goes wrong. Worth a check before a sweep asks it
  6,474 times.
