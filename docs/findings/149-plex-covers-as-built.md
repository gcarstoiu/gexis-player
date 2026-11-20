# Finding 149 — Plex covers as built: 73 % of the library's albums matched by name, a cover in 54-81 ms, a server that does not answer costs 2 s

**Date:** 2026-11-17. **For:** [ADR-0184](../decisions/0184-plex-information-through-plexamps-claim.md)
and Phase 32's acceptance 3-5, after its first step (covers) was built.
Measured on George's library with his consent (2026-11-16), counts and
timings only: no names, lists or pictures were printed or kept.

## Scope

- **Device:** sofapi, Raspberry Pi 4, preview `gexis-core 1.17.0+git22.f0bee53`
  with gexis-plexamp 0.6.0 (installed by the core's own installer); Plexamp
  claimed.
- **Server:** the one Plexamp on sofapi is set to, over the local connection
  the plugin lent (HTTP); awake throughout.
- **Read:** the server's music sections through the core's own `PlexLibrary`,
  in a separate process with the plugin's own reading of Plexamp's files; the
  albums LMS lists to this player; the album-cover answers in the core's
  enrichment cache; the live core's `/plex/cover` route; the core's and the
  plugin's logs since their restart. Names were held in memory only.
- **Not tested:** a server that is really asleep (two stand-ins below); a
  server that requires HTTPS; a Plex cover on the panel or in the visualiser
  during playback (nothing was playing); MusicBrainz ids; artist
  information; lyrics.

## Results

| | |
|---|---|
| Albums in the server's music sections | 3,914; 3,902 with a cover of the server's own |
| The album index | 3,568 titles, made in 6.3 s; 0 ms when kept |
| One lookup in it | 60 µs median, 0.2 ms at most |
| LMS's albums matched by name | **3,539 of 4,823 (73.4 %)**; none unavailable |
| LMS's albums with no cover of their own | 38; Plex has one for 20 |
| Albums played whose cover came from the internet | 28; Plex has 7 by their folded names (a lower bound: the cache keeps names folded) |
| A cover through the core, 600 px | 46,391 bytes in 69 ms (81 ms asked of Plex directly) |
| A cover through the core, 300 px | 18,802 bytes in 54 ms: Plex's scaler took the token in a header |
| A host that does not answer | *unavailable* after 2.0 s |
| The server's host up, nothing on the port | *unavailable* after 0.1 s |
| The token or the server's address in the logs | in none of 194 lines |

## What it means

1. **Matching by name reaches most of what the two libraries share.** LMS
   lists 909 more albums than the server holds, so most of the 1,284
   unmatched are albums the server does not have. What a better rule
   (MusicBrainz ids, acceptance 3) could still win is at most about 375,
   if each of the server's albums is one of LMS's.
2. **The library's own screens barely change.** LMS has its own cover for
   all but 38 albums. The sweep acceptance 5 names (*Update album covers*,
   [ADR-0059](../decisions/0059-artist-portraits-in-the-list.md)) asks
   fanart first and falls back to LMS's own cover; this build does not ask
   Plex there. Whether it should, and in which place, is a decision still
   owed.
3. **On the now-playing screen Plex answers where a renderer sends no
   cover.** Here that was 28 albums since the cache last forgot.
4. **A server that does not answer costs one 2 s wait** (the connection
   wait), and then the enrichment service's 15-minute backoff sends lookups
   to the internet providers - acceptance 4's number, with a stand-in for
   a sleeping server: an address in a private range that nothing answered.
