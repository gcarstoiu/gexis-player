# Finding 054 — LMS does not know who an artist is on MusicBrainz

**Date:** 2026-09-23
**Question:** George: *"the artist navigation holds currently the LMS artist
portraits… I would like to change them with ones from fanart, having LMS as
fall back. I think we checked this in the past and the problem was getting
the link for musicbrainz to link back to the artist in fanart. I think LMS
might have that. Can you check?"*
**Scope:** George's own LMS 9.1.1 at `192.168.178.188:9000` — **7,296
artists, 4,567 albums, 61,225 songs** — and the daemon on `gexis`, 2026-09-23.
Ten tracks sampled for MusicBrainz tags, four artists fetched cold through
the daemon's own `/library/artist-info`. **Not tested:** whether any part of
the library is Picard-tagged (ten tracks is a sample, not a census), and
fanart's coverage beyond four artists.

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

## 5. What that makes the sweep cost

6,474 artists still unresolved, at the measured 1.5–5.3 s each, is
**three to nine hours** of wall clock, whatever shape the work takes. That
number is the whole of the design question, and it is
[ADR-0059](../decisions/0059-artist-portraits-in-the-list.md)'s.

## What this does not settle

- **Nothing was looked at.** No portrait was compared with LMS's for
  quality; George's *"questionable quality"* is the premise, not a finding.
- **fanart's coverage of this library** — four artists.
- **Whether MusicBrainz's search picks the right artist** for common names.
  ADR-0012's confidence threshold reads the score; nothing here tested it
  on an ambiguous name.
