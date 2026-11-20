# Finding 152 — Matching LMS to Plex by MusicBrainz ids: LMS gives none, the core's own artist ids add 34 artists and 125 albums to the names, and never contradict an artist the names found

**Date:** 2026-11-17. **For:** Phase 32's acceptance 3 (matching stated and
measured) and [ADR-0184](../decisions/0184-plex-information-through-plexamps-claim.md)'s
third step. Measured on George's library with his consent (2026-11-16),
counts only: no names were printed or kept.

## Scope

- **Device:** sofapi, Raspberry Pi 4, the core and player at
  `1.17.0+git47.faf38e6`, gexis-plexamp 0.6.0, the library lent over the
  local connection. Its LMS is another machine's (the player's own is off).
- **Read:** the Plex server's artists (type 8) and albums (type 9) with
  `includeGuids=1`; LMS's album artists (`role_id:ALBUMARTIST`) and albums
  through its CLI; the MusicBrainz artist ids the core had already resolved
  and stored (`mb-artist` in the enrichment cache's notes, 1,154 of them,
  most from ADR-0059's sweep); the core's own `PlexLibrary` name index for
  the match by name. Names were held in memory only.
- **Not tested:** the match as built (this is the case for building it);
  the confidence threshold (every stored id was used, whatever its score);
  which side is right where the two disagree; another library.

## What each side carries

- **LMS's CLI gives no MusicBrainz id.** Its database has the column
  (`albums.musicbrainz_id`, `tracks.musicbrainz_id`), but the tag map in
  `Slim/Control/Queries.pm` leaves `musicbrainz_id` out for tracks, and the
  albums and artists queries have no tag for it. A player reaches only the
  CLI (on sofapi the server is another machine), so *"MusicBrainz ids
  where both sides carry them"* has no LMS side.
- **The core's side is the artist id it already resolves**: every provider
  that needs MusicBrainz asks for the artist's id by name once
  (`ArtistIdentity`), and keeps it. Albums have no such id here.
- **Plex carries them nearly everywhere**: 502 of its 509 artists and 3,799
  of its 3,914 albums have an `mbid://` guid (no other scheme appeared).

## Results

| LMS's 948 album artists | |
|---|---|
| Found by name (the core's index, the name or the lead artist) | **558** |
| The core holds an id for the artist | 912 (36 more asked, MusicBrainz had nobody) |
| Plex holds an artist with that id | 579 |
| - the name found the same artist | 545 |
| - the name found another artist | **0** |
| - **found by the id only** | **34** |
| Found by the name, Plex has no artist with that id | 4 |
| **By the name, then the id** | **592 (62.4 %, from 58.9 %)** |

| LMS's 4,823 albums | |
|---|---|
| Found by name (title and artist) | **3,539** |
| - the artist's id agrees: the album is that artist's in Plex | 3,472 |
| - the artist's id points to another Plex artist | 5 |
| **Not found by name, found by the artist's id and the title** | **125** |
| The artist in Plex by id, no album of that title | 687 |
| The artist not in Plex by id, or no id | 472 |
| **By the name, then the artist's id and the title** | **3,664 (76.0 %, from 73.4 %)** |

## What this means

- **The id adds, it does not correct.** No artist found by name was another
  artist by id; for albums, 5 of 3,477 checked disagree, and which side is
  right there was not looked at. So the name stays first and the id is the
  fallback: nothing found today changes.
- **What is left is mostly not in Plex.** 356 album artists are found
  neither way; Plex holds 509 artists to LMS's 948 album artists, and 3,914
  albums to LMS's 4,823. For the 687 albums whose artist Plex has, the
  title is spelled differently or the album is not there; an album-level id
  would need LMS's, which the CLI does not give.
- **The fallback costs an internet lookup only for an artist the core has
  not resolved before**; most are resolved already (912 of 948 here), and
  the internet providers behind Plex ask for the same id anyway.

## As built (2026-11-18)

The installed preview (`1.17.0+git49.c9059db`) on sofapi, walked as the
artwork sweep walks: LMS's album artists, then each one's album titles; the
core's own `PlexLibrary` and `ArtistIdentity`, the stored ids read without
writing, MusicBrainz not asked, at the player's confidence threshold (90).
After the install the core forgot 39 earlier Plex misses, once.

| | By name | By the id after a miss | Neither |
|---|---|---|---|
| 948 album artists | 558 | **34** | 356 (329 with an id Plex has not, 27 nobody) |
| 5,114 album titles (per album artist) | 3,612 | **127** | 1,375 |

- **The artists are as measured above**: 592, the same 34 gained. No
  artist missed by name had an id below the threshold.
- **The albums are counted per album artist**, as the sweep counts them
  (5,114, not LMS's 4,823 albums), so the totals differ from the table
  above; the gain is 127 against 125. By name, then the id: 3,739 of 5,114
  (73.1 %).
