# Finding 054 — LMS does not know who an artist is on MusicBrainz

**Date:** 2026-09-23
**Question:** George: *"the artist navigation holds currently the LMS artist
portraits… I would like to change them with ones from fanart, having LMS as
fall back. I think we checked this in the past and the problem was getting
the link for musicbrainz to link back to the artist in fanart. I think LMS
might have that. Can you check?"*
**Scope:** George's own LMS 9.1.1 at `192.168.178.188:9000` — **7,296
contributors, 917 album artists, 4,567 albums, 61,225 songs** — and the
daemon on `gexis`, 2026-09-23. Ten tracks sampled for MusicBrainz tags, four
artists fetched cold through the daemon's own `/library/artist-info`, every
album counted for artwork, every album artist checked against the resolved
store. **Not tested:** whether any part of the library is Picard-tagged (ten
tracks is a sample, not a census); fanart's coverage beyond four artists;
whether LMS's existing album covers are any good; and whether MusicBrainz's
search picked the *right* artist where it scored 100.

## 1. LMS has no MusicBrainz id to give us — not for this library

- **The `artists` query exposes none.** Asked with every tag letter it
  accepts: `id`, `artist`, `textkey`, `favorites_url`. Nothing else.
- **`songinfo` returns 31 fields and none of them is a MusicBrainz id.**
  Sampled across ten track ids spread through the library: **0 of 10** carry
  one.

LMS's database *has* columns for it — `tracks.musicbrainz_id`,
`contributors.musicbrainz_id` — and fills them from the files' own tags.
George's files are not tagged that way, so the columns are empty and the API
has nothing to publish. A library tagged with Picard would be a different
answer.

**So the link has to be made by name**, and that is what the daemon already
does.

## 2. It is already built, and already remembering

`providers.ArtistIdentity` resolves a folded artist name to a MusicBrainz id
through the search endpoint, and stores it in `enrichment.db`'s `notes`
table under `mb-artist`. **822 of the 7,296 artists are already resolved**,
purely from ordinary browsing.

`FanartArtistImage` is keyed on that id, the fanart key is set, and **the
artist *page* has preferred fanart over LMS since 2026-09-18** on George's
own instruction. What still draws LMS's picture is the artist **list**
(`Library.svelte`'s two grids, `photos[entry.id]`).

## 3. What a cold artist costs

Through `/library/artist-info`, nothing cached, one at a time:

| artist | time | picture came from |
| --- | --- | --- |
| Isaac Hayes | **1,513 ms** | fanart |
| Head | **5,317 ms** | fanart |
| Headgirl | **4,824 ms** | LMS (Discogs) |
| Headstrong feat. Tiff Lacey | **5,018 ms** | LMS (last.fm) |

**1.5 to 5.3 seconds**, and the cost is MusicBrainz's, not fanart's: one
request per second per IP by rule, and Finding 036 measured its *search*
endpoint answering `503 "currently busy"` on 4 of 9 tries.

**Two of four got a fanart portrait.** Four artists is not a coverage
figure; it is enough to say the fallback is not decorative.

## 4. The pictures themselves cost us nothing

The image never passes through this daemon. What is stored is a URL, and it
is handed to **LMS's own image proxy**, which fetches, resizes and caches
it:

```
http://<lms>/imageproxy/https://assets.fanart.tv/…/artistthumb/…jpg
```

So a full sweep of 7,296 artists is **metadata, not gigabytes** — which is
the difference between Finding 030's worry about 246–826 KB per image and
what this would actually hold.

## 5. The list holds *album* artists, and there are 917 of them

George, correcting the question: *"I said artist when I should have said
album artist which we actually have in the list."* It changes the size of
the job by two orders of magnitude.

| | |
| --- | --- |
| contributors in the library | **7,296** |
| **album artists** (`role_id:ALBUMARTIST`) | **917** (870 once folded) |
| already asked about | **781** |
| **left to ask about** | **89** |

**Of the 822 stored, 688 came back with an id and 134 did not** — 16% that
MusicBrainz's name search cannot place. `Headstrong feat. Tiff Lacey` is
one of them, and its shape says why.

### "Resolved" is one of two steps, and the second has never run

George asked what the word meant, which was the right question — the first
version of this section used it to describe the whole job.

**It means only that the daemon has asked MusicBrainz who this artist is,
and written the answer down.** `enrichment.db`'s `notes` table, namespace
`mb-artist`, keyed on the folded name. 688 answers are an id and a score,
134 are a definite "no such artist". Nothing about a picture.

**The picture is a separate call, and for the list it has been made zero
times.** The other namespace, `artist-photo`, holds 630 rows — but they are
keyed on *LMS's* artist id and every value is an `imageproxy/mai/artist/…`
URL, which is LMS's own plugin. That is the cache behind the pictures the
list draws today. Checked against the 870 album artists: **0 of them have
any fanart answer cached**, because nothing has ever asked for one on their
behalf. The 86 fanart rows in the `enrichment` table are keyed per *track*
and come from the artist page and now playing.

### So the real cost of a first pass

A bare fanart call, timed on the device against three known ids:
**0.37 s, 0.46 s, 0.36 s**, all 200.

| step | count | each | total |
| --- | --- | --- | --- |
| MusicBrainz search, for the 89 never asked | 89 | ~3.4 s | **~5 min** |
| fanart, for every album artist | 870 | ~0.4 s | **~6 min** |

**Ten to fifteen minutes**, not the "two to eight" the first version said.
Still minutes rather than hours, so the recommendation does not change —
but it is two steps, not one.

**And fanart does not have a portrait for everyone.** One of those three
ids — `Headgirl`, which resolved with a score of 100 — came back with
**zero** `artistthumb` entries. Two of four in §3 and two of three here;
small samples, and enough to say the LMS fallback will be carrying a real
share of the list rather than covering an edge case.

## 6. The MusicBrainz search is 3.3 to 3.8 s of the 5

The four timings above split cleanly once the store is read back. Isaac
Hayes was already resolved before the test; the other three were resolved
*during* it, and their rows carry today's timestamp.

| artist | id known first? | time |
| --- | --- | --- |
| Isaac Hayes | yes | **1,513 ms** |
| Head | no, resolved in the call | 5,317 ms |
| Headgirl | no | 4,824 ms |
| Headstrong feat. Tiff Lacey | no, and none found | 5,018 ms |

**So knowing the id is worth about 3.4 seconds an artist**, and it is the
part that can 503. What is left is the fanart call and the rest of the
enrichment.

## 7. Album artwork: LMS already has it for 96.6%

| | |
| --- | --- |
| albums | **4,567** |
| with artwork LMS can serve | **4,412** |
| **without any** | **155 (3.4%)** |

The missing ones are mostly editions and live bootlegs — *"12 x 5 (2006,
Japan Mini LP)"*, *"2001-09-28: Higher Ground, Winooski, VT, USA"*.

`providers.CoverArtProvider` already covers this: it searches MusicBrainz
for a **release group** and asks the Cover Art Archive. That is a *second*
kind of search, per album, on the same one-per-second limiter — and Finding
036 measured CAA itself at 949–1,851 ms on top.

- **The 155 gaps:** about **9 minutes**.
- **Every album, to replace what LMS has:** 4,567 searches plus 4,567 CAA
  fetches, **four to seven hours**.

Nothing here says LMS's existing covers are poor; George did not say so.

## 8. If the files carried MusicBrainz ids

Every number above changes:

- **The 3.4 s search disappears**, and with it the 503s and the 1/s limit.
  An artist costs one fanart call.
- **The 134 unplaceable artists mostly stop being unplaceable** — a
  `feat.` suffix defeats a name search and not an id.
- **Ambiguous names stop being a risk.** `Head` resolved with a score of
  100; whether it is the *right* Head is not something the score can say.
- **Album art becomes cheap too**, if the release-group id is tagged: the
  four-to-seven hours becomes the CAA fetches alone.

**No LMS plugin writes them.** LMS *reads* MusicBrainz tags — its scanner
is being changed to prefer `MUSICBRAINZ_RELEASETRACKID` over
`MUSICBRAINZ_TRACKID`, which stopped being unique — but putting them in the
files is a tagging job done outside it: **Picard**, which can fingerprint
untagged files with AcoustID, then an LMS rescan. beets' `mbsync` refreshes
files that already have ids and cannot add them.

**The catch, and it is the reason not to do it casually:** those taggers
rewrite the whole tag set, not just the MusicBrainz fields. On a 61,225-file
library that somebody has curated, that is the risk, not the effort.

## 9. Album covers come free with the artist call

Measured 2026-09-24, after George asked for album artwork as its own sweep.
§7's four-to-seven-hour figure assumed a MusicBrainz *search* per album. It
is wrong, and the reason is worth keeping.

**One fanart call on the artist's id returns the albums too.**
`/v3/music/<artist-mbid>` for Isaac Hayes came back with `artistthumb`,
`artistbackground`, `musiclogo` **and `albums` — 17 release groups**, each
with its own `albumcover` and `cdart`. So fanart needs **no per-album
request at all**.

**And the release-group ids come from a lookup, not a search.**
`/ws/2/artist/<mbid>?inc=release-groups` answered in **145 ms** with all 25
of that artist's release groups and their titles — the endpoint Finding 036
measured at 4 of 4, against the *search* endpoint's 4 of 9. One call per
artist, matched to our albums by folded title.

So both sweeps are the same walk over 917 album artists:

| call | count | paced at | total |
| --- | --- | --- | --- |
| MusicBrainz search, for the 89 never resolved | 89 | 1/s | ~5 min |
| MusicBrainz artist lookup, `inc=release-groups` | 917 | 1/s | ~15 min |
| fanart, one per artist, carrying portraits *and* albums | 870 | paced | ~6 min |

**Twenty-five to thirty minutes for both**, against §7's estimate of four to
seven hours for album art alone.

## 10. LMS cannot be given the ids to hold

George: *"Can we store the musicbrainz IDs in LMS directly as a tag? That
would make it easier for the setup with multiple panels in one household."*

**No.** LMS's JSON-RPC and CLI cover playback, browsing, favourites,
playlists and rescans; there is no command that writes track metadata. The
two plugins in this space — `Custom Scan` and `Custom Tag Importer` —
**import** custom tags *from* the files; neither writes them, and Custom
Scan has been unmaintained since LMS 8.

LMS fills its `musicbrainz_id` columns from the files' own tags at scan
time, so the only way to put an id where every panel in a household can see
it is **to put it in the file**: Picard, then a rescan. That also buys
something of LMS's own — its `tracks_persistent` table (play counts,
ratings) survives a full rescan *"as long as you have musicbrainz tags or
haven't moved or renamed a music file"*.

**The same is true of artwork.** LMS serves what it found in the files or
the folder; there is no API to give it a different cover.

**Which leaves three honest options for a household**, and the sweep being
twenty-five minutes makes the third reasonable: tag the files and every
panel benefits; share one panel's `enrichment.db` with the others; or let
each panel do its own sweep once.

## 11. What the two sweeps actually did, and what the matcher was worth

Run end to end on George's library, 2026-09-24.

**Portraits: 917 of 917 in seven minutes, 525 found.** 759 distinct answers
stored, 492 with a picture — so **about 43% keep LMS's photo**. That is
fanart's coverage of this library, not a fault, and the grid will look
mixed.

**Covers, first run:** 2,114 of 4,567 albums (46%) got one, 492 (11%) were
asked about and fanart had none, and **1,961 (43%) never matched a release
group at all**. That last number was the matcher, not fanart: LMS shows what
the tagger wrote — `12 x 5 (2006, Japan Mini LP)`, `[1997] MTV Unplugged
[EP]`, `57th & 9th (Deluxe Edition)` — where MusicBrainz's release group is
`12 X 5`, `MTV Unplugged`, `57th & 9th`.

**Covers, after stripping brackets and edition phrases for the comparison:**

| | first run | after |
| --- | --- | --- |
| fanart cover | 2,114 (46%) | **2,289 (50%)** |
| asked, fanart had none | 492 (11%) | 1,793 (39%) |
| never matched a release group | 1,961 (43%) | **485 (11%)** |
| rows stored | 16,391 | **4,334** |

**The matcher did its job and the pictures barely moved.** Unmatched fell
from 43% to 11%, and only four points of that turned into covers — the rest
matched a release group fanart has no cover for. So **fanart's album
coverage for this library is about 50%**, which the first run's 46% had
looked like a ceiling of the matcher rather than of fanart.

**And the store stopped holding a catalogue.** The first run kept a cover
for every release group those 917 artists ever made — 16,391 rows for a
4,567-album library, ~12,000 of them never read. It now walks the albums
this library has and looks each one up in theirs: one row per album owned.

## 12. Where the misses went, and what three changes recovered

George: *"Can we do more to cover more artists from fanart with the same
level of confidence?"* Measured over **all 870** distinct album artists, not
a sample.

**Before** — and note the threshold was costing nothing, so there was
nothing to buy back by relaxing it:

| | of 870 |
| --- | --- |
| portrait | **492 (57%)** |
| MusicBrainz placed them, fanart had no portrait | 267 (31%) |
| MusicBrainz found nobody | 106 (12%) |
| never asked | 5 |
| **below the confidence threshold** | **0** |

### The 106 MusicBrainz could not place

Asked again, one candidate at a time, with the same quoted query:

| | of 106 |
| --- | --- |
| the **raw** name finds them - folding was losing them | **17** |
| the part before `feat.`/`presents`/`with`/`vs` | 8 |
| the part before `&`/`,`/`and` | 57 |
| still nobody | 24 |

**Folding the query was a defect.** Quoted, `artist:"b u g mafia"` answers
nobody where `artist:"B.U.G. Mafia"` answers exactly, and
`The B.B. King Blues Band` becomes `The BB King Blues Band` rather than
nothing. Folding belongs to the cache key, not to a catalogue that stores
punctuation deliberately.

**And the score is not what it looks like.** Asked *unquoted*, MusicBrainz
answers `Tina Dico` with **Tina Dickow at 100** and `DJ Project (2)` with
**ProjeKct Two at 100**. The score says how well the string matched the
index, not whether it is the right person. **What protects us is the
quoting**, which is strict enough that both return nobody; the confidence
threshold is a second line, not the first. This corrects what was said on
2026-09-23, that the threshold would guard against a wrong `Head`.

### The 267 fanart had no portrait for

Re-queried 25 of them for every image kind fanart publishes:

| | of 25 |
| --- | --- |
| **no image of any kind** | **18 (72%)** |
| `hdmusiclogo` | 5 |
| `artistbackground` | 3 |
| `musiclogo` | 1 |

**Drawn as the grid draws them**, ten of them circular and centre-cropped,
the split was obvious: fanart's *backgrounds* are photographs of the artist
and crop like any portrait, while the *logos* are wide wordmarks that a
square crop cuts to `TRIN`, `PI`, `TLO`, `BOU`. Fitted whole they read
perfectly and sit small and letterboxed among full-bleed faces - a different
grid. George, 2026-09-24: *"only with the backgrounds, no logos."*

### After all three

Re-run from a cleared store:

| | before | after |
| --- | --- | --- |
| picture | **492 (57%)** | **585 (67%)** |
| fanart has no picture | 267 (31%) | 256 (29%) |
| MusicBrainz found nobody | 106 (12%) | **24 (2.8%)** |

**MusicBrainz now places all but 24 of 870.** The remaining 256 are fanart's
own gap, and by the sample about three quarters of them have no image at
all - which is where LMS's picture stays whatever we do.

## What this does not settle

- **Nothing was looked at.** No portrait was compared with LMS's for
  quality; George's *"questionable quality"* is the premise, not a finding.
- **fanart's coverage of this library** — four artists.
- **Whether MusicBrainz's search picks the right artist** for common names.
  ADR-0012's confidence threshold reads the score; nothing here tested it
  on an ambiguous name.
