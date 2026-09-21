# Finding 044 — What LMS knows about what was played, and what the home strip can therefore be

**Date:** 2026-09-21
**Question:** Phase 9 subphase 9h builds the home strip, which the design
makes three things: **New music**, **Most played artists**, **Recently
played artists**. Two of those need play statistics. Does the server have
them?
**Status:** measurement, for a decision George has not taken. **Nothing is
decided here.**

**Scope, stated up front:**

- **Measured against George's own server** (LMS 9.1.1, 61,225 tracks, 4,567
  albums, 917 artists) on 2026-09-21, over the JSON-RPC CLI — the same
  interface the daemon uses. Not against a stock install, and not against
  any other version.
- **What was tried:** every documented sort on `albums`, the whole tag
  alphabet on `titles`, `songinfo` for a single track, the plugin list, and
  a hand-aggregation of play counts over two albums.
- **Not tried:** SQL against the LMS database directly, and any plugin not
  installed. Both are answers this does not evaluate.

## Result

**One of the three strips is buildable from what the server exposes. The
other two are not.**

| strip | what it needs | what the server gives |
|---|---|---|
| **New music** | albums by date added | `albums sort:new` — **works, and is already built** |
| **Most played artists** | plays per artist | `playcount` **per track, one call at a time** |
| **Recently played artists** | when each artist last played | **nothing** |

### Play counts exist, but only one track at a time

`songinfo` returns a `playcount` field for a single track. **`titles` does
not**: asked with the entire tag alphabet
(`aAbcCdefgiIjJkKlmMnopPqrRsStuvwxyY`), it answers 30 fields and play count
is not among them. So aggregating plays by artist means **one `songinfo`
call per track — 61,225 of them** for this library.

### `sort:playcount` is not a play-count sort

`albums sort:playcount` is accepted and returns an order that is neither
alphabetical nor `sort:new`, so it is doing *something*. It is not this.
Summing the play counts of the first twelve tracks of each of its top three
albums:

| position | album | plays |
|---|---|---|
| 1st | Il mare calmo della sera | 201 |
| 2nd | Pac's Life | **251** |
| 3rd | Eyes Open | 12 |

**The second has more plays than the first**, so whatever the sort orders
by, it is not the number this strip would need. A caption reading "most
played" over that order would be a confident lie.

### Nothing records when a track was last played

`songinfo`'s full field list for a track is: `id, title, artist, work,
coverid, duration, album_id, filesize, genre, coverart, artwork_track_id,
comment, album, modificationTime, type, genre_id, bitrate, artist_id,
tracknum, tagversion, remote, year, compilation, addedTime, dlna_profile,
channels, playcount, lossless, samplerate, lastUpdated, release_type`.

There is `addedTime`, `modificationTime` and `lastUpdated` — all about the
**file**. There is no last-played anywhere, and `titles sort:lastplayed` is
accepted and ignored (it returns alphabetical order). **No statistics
plugin is installed**: the plugin list is empty of anything matching
*stat*, *track*, *play* or *rating*.

So the design's caption for that strip — *"2 hours ago", "Last week"* —
describes a fact this server does not hold.

## Three ways forward (not decided)

1. **Build New music only**, and record the other two as blocked on data.
   Costs nothing and leaves `home_strip` a choice with one real option,
   which is not a choice.
2. **Count plays ourselves.** The daemon already sees every track that
   starts, on every renderer — including Bluetooth and Spotify, which LMS
   knows nothing about. A small table beside the enrichment cache (artist,
   plays, last played) makes both strips *our* data: accurate from the day
   it starts, complete across renderers, and empty at first. It also
   answers a question LMS cannot: what this **device** has played, which is
   what a strip on its home screen is about.
3. **Ask the server for it** — install a statistics plugin on LMS. Changes
   George's server rather than this device, and leaves the strips empty for
   anyone whose server has no such plugin.

**Option 2 is the one that fits what this product is**, and it is the only
one that covers the other two renderers. It is also the only one that has
to be built rather than queried.
