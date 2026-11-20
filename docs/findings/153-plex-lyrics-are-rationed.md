# Finding 153 — Plex's lyrics: Plexamp's request works, about five lyrics per ten minutes for the whole server, and LRCLIB already has more of them synced

**Date:** 2026-11-17. **For:** Phase 32's acceptance 6 (find how Plexamp
gets lyrics before building a provider), and
[Finding 086](086-what-the-plex-server-could-answer.md)'s open question.
Measured on George's library with his consent (2026-11-16), counts only: no
title, name or lyric was printed or kept.

## Scope

- **Device:** sofapi, the library lent by gexis-plexamp 0.6.0 over the local
  connection, the server's own token (Plexamp's, `@Plexamp:resources`).
- **Read:** Plexamp 4.13.2's code (`LyricPlayerStore.loadLyric`); the
  server's lyric streams on random samples of 80 and 40 tracks; fetches of
  them Plexamp's way and Finding 086's way, in rounds, then one a minute for
  up to 45 minutes; the 436 LRCLIB answers in the core's enrichment cache,
  against the same tracks' lyric streams in Plex (metadata only).
- **Not tested:** how long the window is exactly, and whether it is rolling
  or fixed; whether Plexamp's own lyrics draw on the same allowance (a
  client identifier of our own did not get one of its own); local lyric
  files, beyond the one stream seen; another server or account.

## How Plexamp asks

`<stream key>?format=xml&includeInlineAttribution=1` (JSON for a cloud
provider's items), choosing a local stream first, else a timed one, else the
first. **It fetches a licensed (LyricFind) lyric only when the lyrics are
shown**: on a track change it hides them rather than fetching ahead.
Plexamp's menu item for lyrics is flagged `premium`.

## Results

| | |
|---|---|
| Tracks with lyric streams | 37 of 80 sampled; 58 LyricFind streams, 1 local; 27 `lrc`, 32 `txt`; 26 timed |
| Plexamp's request, 30 tracks in a row | **5 served (median 3,243 bytes, 4 with timed lines), 25 refused (404)** |
| The bare key (Finding 086's request), straight after | 404 for all 30 - inside the spent window, so this does not show that it fails |
| Plexamp's request again, the same 30 | 404 for all |
| One a minute after that | 404 for ten minutes; at 10.1 min served, **then 4 more, then 404** |
| A client identifier of our own, inside the spent window | 404, as without one |
| `/library/streams/<id>/levels` (Finding 086: 404) | **200 for 10 of 10** |

**So the server serves about five lyrics, then none for about ten
minutes**, whoever asks with that token. Finding 086's "once, then never"
fits this if its attempts fell inside spent windows; that was not shown,
and its bare-key fetch did serve once. Its waveform 404s are not explained;
they answer now.

| The 92 tracks already played here that Plex holds (album and title by name) | LRCLIB synced | plain | instrumental | none |
|---|---|---|---|---|
| Plex timed (33) | 32 | 1 | - | - |
| Plex plain (20) | 11 | 4 | - | 5 |
| Plex none (39) | 23 | 4 | 6 | 6 |

Of the 436 tracks the core asked LRCLIB for, 344 were not found in Plex by
album and title: mostly music played from elsewhere (Spotify, radio,
AirPlay), which Plex could not answer for anyway.

## What this means

- **There is a way, and it is rationed**: enough for one track at a time as
  music plays (about three tracks per ten minutes), not for skipping through
  an album or a sweep, and most likely shared with Plexamp: a client
  identifier of our own got no allowance of its own, but Plexamp itself was
  not tested (corrected 2026-11-18; it said *shared* outright).
- **LRCLIB is the better source on this library**: synced for 66 of the 92,
  Plex timed for 33. Behind LRCLIB, Plex would add lyrics to 5 of them and
  timing to 1. Ahead of it, the merge would take Plex's plain lyrics over
  LRCLIB's synced ones for 11.
- **A 404 here does not mean "no lyrics"** when the track lists a lyric
  stream; a provider would have to read it as *could not ask*, or it would
  store "nothing" for a track that has some.
