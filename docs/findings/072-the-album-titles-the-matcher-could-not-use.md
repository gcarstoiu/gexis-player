# Finding 072 — The album titles the matcher could not use

**Date:** 2026-09-25
**Question:** George, 2026-09-25: *"not that many album arts are found. Might
be that the album name contains modifiers that could be excluded."* How many
of his albums carry one?
**Amended the same day**, on the device: the modifiers are the *smaller*
half. See §2.
**Scope:** every album LMS holds for George — **4,567** — read from
`slim.request ["albums","0","30000"]` on 2026-09-25 and put through `fold`
(what the cover provider asked with until today) and `match_title` (what it
asks with now, per [ADR-0080](../decisions/0080-a-cover-is-matched-on-a-title-both-catalogues-agree-on.md)).
**A count of titles, not of covers**: it measures the gap the matcher could
not reach, not how many covers exist behind it.

## 1. The modifiers George named

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

### Where the reduction over-reaches

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

## 2. The bigger half: the query was folded

**Found by testing the fix on the device, where it did not work.** The album
went into MusicBrainz as a *quoted phrase* built from `TrackKey.album`, which
is **folded** — that is what the field is for, a cache key two spellings
cannot split. The index holds the title's own characters. Asked directly:

| query | result |
|---|---|
| `artist:"Sting" AND releasegroup:"57th & 9th"` | **100**, exact |
| `artist:"sting" AND releasegroup:"57th 9th"` | **nothing** |
| `artist:"sting" AND releasegroup:(57th 9th)` | 100 (unquoted, so not a phrase) |

Folding removes the `&` and the phrase then matches nothing. And folding is
ASCII-only, so it does worse than remove punctuation:

```
'100 Jahre Strauß'      -> '100 jahre strau'      (the ß is dropped, not transliterated)
'1,039/Smoothed Out Slappy Hours' -> '1 039 smoothed out slappy hours'
'100%'                  -> '100'
```

| | albums | share |
|---|---|---|
| folding changes more than case | **1,423** | **31.2 %** |
| carries a modifier (§1) | 506 | 11.1 % |
| **one or the other** | **1,435** | **31.4 %** |

The two barely overlap. **The modifiers are 11 % and the folding is 31 %**,
and the folding was invisible because nobody had asked MusicBrainz what it
does with a phrase.

## 3. What it is worth: 40 albums, old query against new

A random sample of 40 artist/album pairs from the library (seeded, so it can
be repeated), each asked both ways against the live MusicBrainz and Cover Art
Archive.

| | found |
|---|---|
| old: one ask, both fields folded | **27 / 40** |
| new: raw, then trimmed and verified | **32 / 40** |

**Five gained, none lost.** The one album that came back `UNAVAILABLE` on the
new path — David Bowie's *Hours* — was a transient, and is `FOUND` on a
re-ask; it is counted here as found.

What was gained says which half did the work:

```
Above & Beyond           Common Ground                    ampersand in the artist
Nick Cave & The Bad Se…  The Good Son                     ampersand in the artist
Snap!                    Snap! Attack: The Best of Snap!… punctuation
blink-182                California                       hyphen in the artist
Black Sabbath            Sabotage (2021 - Remaster)       a modifier, George's own case
```

**Four of the five are the artist or the punctuation, not the modifier.**

## What this does not tell us

- **Whether 40 is enough.** It is a sample, seeded and repeatable, not the
  library. 5 of 40 is a wide interval; the direction is not in doubt and the
  size is.
- **Anything about the library sweep.** The sweep has had `match_title` since
  2026-09-24 and already matches this way; this finding is about the
  *enrichment* path, which is what a Bluetooth or Spotify track uses.
- **Whether the sweep's own numbers are current.** It has not been re-run
  since the raw-name and collaboration fixes, which placed 82 more artists —
  their albums would now find release groups. That is a separate run and a
  separate number.
