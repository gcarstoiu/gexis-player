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

## What this does not settle

- **Nothing was looked at.** No portrait was compared with LMS's for
  quality; George's *"questionable quality"* is the premise, not a finding.
- **fanart's coverage of this library** — four artists.
- **Whether MusicBrainz's search picks the right artist** for common names.
  ADR-0012's confidence threshold reads the score; nothing here tested it
  on an ambiguous name.
