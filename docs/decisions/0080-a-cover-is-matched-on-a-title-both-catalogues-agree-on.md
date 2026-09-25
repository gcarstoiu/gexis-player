# ADR-0080 — A cover is matched on a title both catalogues agree on

**Status:** Accepted
**Date:** 2026-09-25
**Relates to:** [ADR-0040](0040-enrichment-providers.md) §2 (the cover
providers), [ADR-0012](0012-enrichment-additive-only.md) (a wrong cover is worse
than none), [ADR-0059](0059-artist-portraits-in-the-list.md) and
[Finding 054](../findings/054-what-lms-knows-about-artist-identity.md) §9 (where
`match_title` came from), Phase 9 criterion 3

## Context

George, 2026-09-25, reviewing the panel: *"not that many album arts are found.
Might be that the album name contains modifiers that could be excluded."*

He is right, and **this project has already solved it once**. The artwork
sweep matches LMS's album titles against fanart's release groups, and
comparing them as they stand **matched nothing for 43 % of his albums**
(measured 2026-09-24, Finding 054 §9): LMS shows what the tagger wrote —
`12 x 5 (2006, Japan Mini LP)`, `[1997] MTV Unplugged [EP]`,
`57th & 9th (Deluxe Edition)` — where the catalogue says `12 X 5`,
`MTV Unplugged`, `57th & 9th`. `artwork_sweep.match_title` strips the brackets
and the trailing edition phrase and fixed it.

**`CoverArtProvider` never got it.** It asks MusicBrainz for
`releasegroup:"<album>"` with the album *folded* — and folding only removes
punctuation, so `57th & 9th (Deluxe Edition)` becomes
`57th 9th deluxe edition` and the modifier words are still in the query. That
is the enrichment path, which is the one that matters for Bluetooth and
Spotify, where the renderer supplies no cover at all.

## Decision

**Ask for the title as it is; if that finds nothing, ask for the title
reduced, and check the answer reduces to the same thing.**

1. **`match_title` moves to `enrichment.py`, beside `fold`.** One normaliser
   with two callers, rather than a second copy drifting from the first. The
   sweep keeps using it unchanged.
2. **`TrackKey` gains `raw_album`**, `compare=False`, exactly as it already
   carries `raw_title` and for the stated reason: brackets are invisible once
   folded, and they are what has to come off before a catalogue recognises a
   title.
3. **`CoverArtProvider` asks twice at most.** The folded album first — an
   exact hit is the best evidence there is. Only if that finds nothing, and
   only if reducing actually changes the title, it asks again with the reduced
   one.
4. **The second answer is verified on the title, not only on the score.** The
   release group's own title is put through `match_title` and must equal ours.

## Rationale

### Why not simply always ask with the reduced title

Because reducing loses information, and the loss is not always harmless.
`Greatest Hits Volume 2` reduces to `greatest hits` — `vol(ume)? \d+` is one
of the edition phrases — and a global search for `greatest hits` by that
artist will happily return the first volume's cover. Asking with the full
title first means an album that can be found exactly *is*, and reduction only
rescues the ones that miss today.

The cost is one extra request, and only on albums that already fail. Those
answers are cached like every other.

### Why verify the reduced answer both ways

Reduction is applied to *our* title; MusicBrainz's index is not reduced. So a
reduced query is a looser query, and the score alone is not enough to say the
looser query landed on the right thing — MusicBrainz will score a confident
match on a release group whose title merely contains the words.

Putting the returned title through the same function and requiring equality is
what the sweep already does, on both sides of its comparison. It does not make
reduction lossless — `Greatest Hits Volume 2` and `Greatest Hits` still reduce
alike — but combined with asking exactly first, the case that survives both is
narrow.

**ADR-0012's rule is the constraint here**: a wrong cover on a screen nobody
can correct is worse than the design's pending glyph. This adds a check where
there was none; it does not relax one.

### Rejected: strip modifiers when the metadata arrives

Considered, because then every consumer benefits and there is one place to fix.
Rejected: the title LMS holds is the title the user tagged and the one the
panel must display and look up by. Reduction is *for matching only* — the
sweep's own docstring says so, and it is the reason the sweep stores what it
finds under the library's title rather than the catalogue's.

## Consequences

- An album that already resolves is unaffected: it is found on the first ask,
  exactly as before.
- An album that misses costs one further request before it is recorded as a
  miss, and misses are cached.
- `RecordingArtProvider` is untouched. It has no album by definition — it is
  the radio case, where the station's name sits where an album would be.

## What this does not settle

- **The hit rate.** This record says the matcher was asking the wrong
  question; it does not predict how many more covers the right question finds.
  That needs a measurement against George's own library.
