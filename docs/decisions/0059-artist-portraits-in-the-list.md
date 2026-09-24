# ADR-0059 — Where the artist list's portraits come from

**Status:** **Accepted**, 2026-09-24. George chose neither a sweep nor
scrolling but **a button**: *"there should be a trigger in settings
enrichment for a user to trigger an automatic update of album artists
portraits, with a progress bar and completion status."* Phase 9 subphase
**9k**.
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

## Decision

**A button in Settings → Enrichment, and a second one beside it for album
covers.** Not a background sweep, not on scroll: the user asks, and watches
it happen.

### What the buttons do

| | |
| --- | --- |
| **Update artist portraits** | Every album artist, fanart first, LMS's picture as the fallback |
| **Update album covers** | Every album, fanart first, LMS's own cover as the fallback |

- **Every one, every time.** George: *"Check everything again."* A press
  re-asks the lot, so an artist fanart had nothing for last month is picked
  up when it does. Nothing is skipped for being answered before.
- **A 503 is never an answer.** Finding 036's line, and it matters more here
  than anywhere: a sweep that stored "could not ask" as "no picture" would
  poison 870 artists in one press.
- **Honest progress**, in George's own words: *"X out of Y processed
  (searched for), Z artist portraits found."* It does not end at 100%
  meaning everyone was upgraded, because fanart has nothing for a real
  share of them.
- **Paced**, so it neither disturbs playback nor earns a throttle.
  MusicBrainz is one request per second by rule; fanart's limit we have
  never been able to read (Finding 030), so it is spaced rather than
  hammered.
- **One at a time.** They share the same two APIs, so the second waits for
  the first. Left to me, and the reason is Finding 054 §9: they are largely
  the same walk, so running them in series costs almost nothing over running
  one.

### What it costs, and why album covers are cheap

Finding 054 §9 measured what the first version of this record assumed
wrongly. **fanart returns an artist's albums in the artist call** — 17
release groups for Isaac Hayes, each with its cover — so there is no
per-album fanart request. And the release-group ids come from
`artist/<mbid>?inc=release-groups`, a **145 ms lookup** on the endpoint that
answers reliably, not the search endpoint that 503s.

| call | count | total |
| --- | --- | --- |
| MusicBrainz search, the 89 never resolved | 89 | ~5 min |
| MusicBrainz artist lookup with release groups | 917 | ~15 min |
| fanart, one per artist, portraits *and* albums | 870 | ~6 min |

**Twenty-five to thirty minutes for both buttons**, against the four to
seven hours album art was first estimated at alone.

### Where the pictures are used

- **The artist grid** and the **home-screen strips** (most-played, recently
  played) — today's LMS-only surfaces, and the reason for the work.
- **Now playing's Artist tab** and the **artist page** — already fanart-first
  since 2026-09-18; they need nothing.
- **New artists are done as they arrive**, on the path that already exists.

### The rules that go with it

- **Keyed on the folded artist name, never on LMS's id.** Finding 030's
  rule, from Finding 029: a full rescan renumbers every artist and album id.
  Today's LMS photo cache *is* id-keyed and silently goes stale; this one
  will not.
- **The confidence threshold decides.** `Head` resolved with a score of 100
  and there is no way to know it is the right Head. A match below the
  threshold keeps LMS's picture. George: *"Use the confidence level for
  sure"* — and the row moves into this group so it is next to what it
  governs, though it still governs all enrichment.
- **LMS cannot hold the ids for us** (Finding 054 §10). There is no write
  path in its API, and the plugins in this space import tags rather than
  write them. A household that wants this shared tags its files with Picard;
  otherwise each panel presses the button once, which is now half an hour.

## Also in 9k: the rest of Enrichment

George: *"wire the rest of the enrichment entries which are not wired as of
now."* Four rows in that section have no code behind them at all —
`enrichment` (the master toggle), `confidence`, `lyrics` and
`artwork_lookup`. They join this subphase.

## Open

- **Whether `artwork_lookup` survives.** *"Look up missing artwork"* as a
  background behaviour overlaps the new button, which does every album
  rather than the missing ones. It may become the *automatic* half — new
  albums as they arrive — or it may be redundant.
- **What a household does.** Three options in Finding 054 §10; none chosen,
  and at half an hour a panel it may not need choosing.
