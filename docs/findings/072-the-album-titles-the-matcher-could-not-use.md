# Finding 072 — The album titles the matcher could not use

**Date:** 2026-09-25
**Question:** George, 2026-09-25: *"not that many album arts are found. Might
be that the album name contains modifiers that could be excluded."* How many
of his albums carry one?
**Scope:** every album LMS holds for George — **4,567** — read from
`slim.request ["albums","0","30000"]` on 2026-09-25 and put through `fold`
(what the cover provider asked with until today) and `match_title` (what it
asks with now, per [ADR-0080](../decisions/0080-a-cover-is-matched-on-a-title-both-catalogues-agree-on.md)).
**A count of titles, not of covers**: it measures the gap the matcher could
not reach, not how many covers exist behind it.

## Result

| | albums | share |
|---|---|---|
| total | 4,567 | |
| **the reduction changes the query** | **506** | **11.1 %** |
| fold to nothing at all (`+`, `÷`, `=`) | 3 | 0.07 % |

A sample of what changes:

```
'11 (Deluxe Edition)'                    -> '11'
'12 x 5 (2006, Japan Mini LP)'           -> '12 x 5'
'13 Voices (Japanese Deluxe Edition)'    -> '13 voices'
'[1997] MTV Unplugged [EP]'              -> 'mtv unplugged'
'21 Reasons (feat. Ella Henderson)'      -> '21 reasons'
'44/876 (Deluxe)'                        -> '44 876'
'57th & 9th (Deluxe Edition)'            -> '57th 9th'
'A Boy from Tupelo - CD 1'               -> 'a boy from tupelo'
'18 Til I Die (Live At The Royal Albert Hall 2024) - CD 2' -> '18 til i die'
```

**Folding was never going to reach these.** `fold` removes punctuation, so
`57th & 9th (Deluxe Edition)` became `57th 9th deluxe edition` — the brackets
went and every modifier word stayed, and that is what was sent to MusicBrainz
as a quoted phrase.

## Where the reduction over-reaches

`_EDITION` cuts from the first edition word to the end of the title, which is
right for `Nevermind Deluxe Edition` and wrong here:

```
"50th Anniversary Collector's Edition"   -> '50th'
'25e anniversaire, Volume 2'             -> '25e anniversaire'
'10 Years: Limited Edition'              -> '10 years limited'
```

`'50th'` is not a useful query. **It is survivable because of the order and
the check** ADR-0080 sets: the full title is asked first, so an album that
resolves exactly never reaches the reduction; and a reduced answer is accepted
only if the release group's own title reduces to the same string, which
`50th Anniversary Collector's Edition` would.

**149 reduced keys are shared by more than one album title**, almost all of
them discs of one release (`A Boy from Tupelo - CD 1/2/3`), case variants, or
an edition beside its plain issue. Those collide onto the same cover, which is
the right cover.

## What this does not tell us

- **How many more covers this finds.** That needs the lookups run, and
  MusicBrainz is rate-limited to one request a second. 11.1 % is the share of
  titles that were being asked about wrongly — the ceiling, not the yield.
- **Anything about the library sweep.** The sweep has had `match_title` since
  2026-09-24 and already matches this way; this finding is about the
  *enrichment* path, which is what a Bluetooth or Spotify track uses.
- **Whether the sweep's own numbers are current.** It has not been re-run
  since the raw-name and collaboration fixes, which placed 82 more artists —
  their albums would now find release groups. That is a separate run and a
  separate number.
