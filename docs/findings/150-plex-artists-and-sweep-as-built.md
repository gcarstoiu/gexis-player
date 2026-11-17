# Finding 150 — Plex's artists and the sweep as built: its picture and biography for every artist it holds by name, popular rows where the names agree, Plex's picture on 556 of 948 artists after one sweep

**Date:** 2026-11-17. **For:** [ADR-0184](../decisions/0184-plex-information-through-plexamps-claim.md)'s
second step, after it was built. Measured on George's library with his
consent (2026-11-16), counts and timings only: no names, lists or pictures
were printed or kept.

## Scope

- **Device:** sofapi, Raspberry Pi 4, preview `gexis-core 1.17.0+git31.6079681`
  (gexis-system unchanged at `1.17.0+git22.f0bee53`) with gexis-plexamp
  0.6.0; Plexamp claimed, the library lent over the local connection (HTTP).
- **Read:** the core's log since its restart; LMS's artist list; the core's
  `/library/artist-info` for two samples of 40 artists, each asked twice;
  the server's own answer for the same artists through the core's
  `PlexLibrary`, in a separate process; *Find portraits and covers* (ADR-0059's
  sweep, the first run on this player) to its end; what it stored, by
  source, in the enrichment cache's notes; `/library/artist-photos` for all
  the album artists; `/library/artists/<id>/albums` for 60 of them. Names
  were held in memory only.
- **Not tested:** the now-playing screen (nothing was playing); the panel's
  own screens (only the routes they read); *Information from Plex* turned
  off after the sweep; another server; a server that is asleep.

## Results

| | |
|---|---|
| The core's index | 3,568 album titles and 507 artist names in 6.3 s (the server holds 509 artists) |
| LMS's artists the server holds | **1,719 of 8,421**: 542 by the same name, 1,177 by the lead artist only |
| 40 artists across all of LMS's | 8 held by the server; all 8 with its picture and biography |
| 40 artists the server holds | its picture 40, its biography 39, similar artists 40; ten popular titles from the server for 40 |
| *Popular* rows on the page, same name | 12 of 13 artists; 96 of the server's 110 titles matched a track of the artist (98 with edition words dropped) |
| *Popular* rows on the page, lead artist | 3 of 27 artists; 3 of 236 titles matched |
| The page's answer | 1.8 s median (5.5 s at most) the first time; 0.17 s (1.8 s) again |
| The sweep | 948 artists in 69 min; 864 portraits; 5,114 albums, 3,784 covers |
| Portraits stored, by name | Plex 513, fanart/TheAudioDB 771, both 466, either 818 |
| Covers stored, by name | Plex 3,409, fanart/TheAudioDB 2,691, both 2,327, either 3,773 |
| The artist list after it (948) | Plex's picture 556, fanart/TheAudioDB 352, none 40 |
| Album grids of 60 artists (270 albums) | Plex's cover 169, LMS's own 82, fanart/TheAudioDB 15, none 4 |
| The token or the server's address in the logs | in none of 10,173 lines; no errors |

## What it means

1. **For an artist the server holds by name, the page is the server's**:
   picture, biography and similar artists, and *Popular* rows for all but
   one sampled. The server's titles match the library's own tracks as they
   are folded; dropping edition words adds 2 of 110.
2. **Two thirds of the matches are by the lead artist.** LMS lists
   collaborations (*A feat. B*, *A & B*) as artists of their own; the server
   answers for them with A's record, so their page shows A's picture and
   biography, and *Popular* stays mostly empty, since A's popular tracks are
   seldom the collaboration's. The internet sources did the same before
   Plex: of the 1,166 collaborations (by folded name), 80 had a MusicBrainz
   id stored, and where the lead's was stored too it was the lead's for 68
   of 70; for the 51 among the album artists, all had one, the lead's for
   41 of 41. Wikipedia and ListenBrainz answer by that id. Whether a
   collaboration's page takes the lead artist's biography is a decision
   owed (George).
3. **The sweep reads Plex first, and both are kept.** Plex alone has 513
   portraits and 3,409 covers; fanart and TheAudioDB add 305 portraits and
   364 covers it has none for, and it adds 47 and 1,082 they have none for.
   Both are asked by design (ADR-0184, second step, 4), so the run is no
   shorter with Plex; its time was not split by source.
4. **The row counts LMS's artists, the stores names.** 948 artists stored
   901 names from Plex: names that fold the same share one entry, which is
   why the row's 864 portraits and 3,784 covers are above the stores' 818
   and 3,773.
