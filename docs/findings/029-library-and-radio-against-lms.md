# Finding 029 — Library and radio against George's LMS: queries, filing, artwork, radio actions, and playback from a typed id

**Date:** 2026-09-17
**Question:** Phase 7 step 1 — ADR-0038's "Unverified" list, and ADR-0030's
load-bearing assumption that playback from a typed id works. What does each
designed screen cost, how does LMS file and group, what does radio look like
below its first level, and what happens on `gexis` when the library starts
playback?
**System:** LMS 9.1.1 at `192.168.178.188`, player `gexis`
(`88:a2:9e:79:e1:32`), device on the Phase 6 image
`v0.2.1-202-gf3674f3`. JSON-RPC `slim.request` sent from R2D2. **No product
code involved:** nothing was sent to the panel or the core's routes; the core
was only observed, through its journal and `/state`.

**Scope, stated up front:**

- **One server, one library:** 60,974 songs, 4,554 albums, 916 album artists
  before the rescan below; 61,225 / 4,567 / 917 after. Timings are from R2D2
  over the LAN, three runs each for reads; they are not panel latencies.
- **Playback was observed through LMS status and the core's log, sampled
  0.5–7 s after each command.** Whether the speakers were on was not
  recorded; what George heard is not part of this finding except where noted.
- **A library rescan ran in the middle** (below). Read-only results before
  15:26 use pre-rescan ids; everything from 15:54 on uses post-rescan ids.
- **Commands were issued the way an LMS app issues them**, not through any
  gexis route (George asked for that explicitly). The panel's own route does
  not exist yet.
- **Raw replies** are kept on R2D2 at `~/gexis-findings/029-raw/`, not in the
  repository: they contain George's library listing, playlist names and a
  TuneIn serial. Whether any become test fixtures, and anonymised how, is a
  step 3 question for George.

## Result

**Playback from a typed id works on all four kinds, including from a
powered-off player and over a Spotify session.** Two defects were found in
the core, both outside the library code: a takeover restores a stale position
onto new content, and radio publishes the station name and a placeholder
image instead of the song's title and art.

### 1. Typed reads are cheap

| Read | Time (ms, 3 runs) | Reply |
|---|---|---|
| `albums 0 50 tags:jlaS` | 18, 11, 9 | 12 KB |
| `albums 4500 50` (deep page) | 16, 16, 16 | 13 KB |
| `artists 0 60 role_id:ALBUMARTIST tags:s` | 8, 9, 8 | 6 KB |
| `artists 880 60 role_id:ALBUMARTIST` | 9, 9, 10 | 4 KB |
| **all 916 album artists in one request** | 23, 22, 23 | 98 KB |
| `artists 7200 60` (all artists, deep) | 26, 23, 21 | 7 KB |
| `albums 0 10 sort:new` | 8, 8, 7 | 3 KB |
| album by id + its tracks (`titles album_id: sort:tracknum tags:dtaluJ`) | 9 + 8 | — |

The album page is two requests; tracks carry `duration` in seconds.
The album-artist list needs no paging at this size.

### 2. Filing and grouping

- **Order is by LMS's sort name.** 174 of 916 album artists sit under a letter
  other than their displayed name's first (David Bowie under B, Louis
  Armstrong under A). Leading articles are ignored (`ignoredarticles` =
  "The El La Los Las Le Les"; "The Beatles" under B, "THE ANXIETY" under A).
- **`textkey` is the letter.** Digits are their own keys (`0`, `2`, `3`, `4`,
  `5`). Two keys are accented, `Ç` and `Í`, although the list order places
  those artists inside C and I (the key sequence reads `…C Ç C…` and
  `…I Í I…`).
- **`release_type` is present on every album** (`tags:W`), as combined
  values: ALBUM 3,968, ALBUM COMPILATION 293, ALBUM LIVE 95, ALBUM SOUNDTRACK
  88, SINGLE 38, EP 34, ALBUM REMIX 9, ALBUM COMPILATION SOUNDTRACK 8, ALBUM
  COMPILATION DJ MIX 7, EP LIVE 3, and single-digit others.

George, 2026-09-17: follow LMS in both (ADR-0038 §1a).

### 3. Playlists

- **All 98 playlists before the test were Qobuz** (`qobuz://` URLs). No
  library playlists existed, because **LMS had no playlist folder**
  (`pref playlistdir` empty). `playlists new` against that state dropped the
  connection rather than returning an error.
- `playlists 0 0` returns `{}` (no count). `search:` returns `{}` for
  playlists. The core has to list them all and filter.
- George set a folder (`/playlist`). **Setting it started a full rescan**
  (15:25–15:54): Qobuz playlists, database optimise, discovery, 61,240 files,
  Qobuz playlists again. `playlists new` issued at the start of it timed out
  after 20 s and created nothing.
- After the scan, three test playlists were created (George: keep them):
  `gexis-test-album` (122541, 5 tracks), `gexis-test-mixed` (122543, 4 tracks
  from 4 artists), `gexis-test-empty` (122544). **Library playlists are
  `file:///playlist/<name>.m3u`** — the `file:` scheme is what tells them
  from a plugin's.
- **Adding to a playlist is one track URL per call:**
  `playlists edit cmd:add playlist_id:<id> url:<track url>`, milliseconds
  each. `album_id:` and `track_id:` in the same command are silently ignored
  (no error, nothing added). `url:db:album.id=<id>` adds **one entry that
  refers to the whole album** (`db:album.title=…&contributor.name=…`), not its
  tracks; whether such an entry plays was not tested, and it was removed.
  `cmd:delete index:` removes an entry.

### 4. A full rescan renumbers the library

After the 15:54 rescan: **all 916 album artists had new ids** (Holograf
2681 → 9974), El Mocambo 1977 moved from album 3999 to 8566, and the
`sort:new` list was entirely different (the scan reset what LMS considers
new). `serverstatus` `lastscan` changed (1789386928 → 1789653231).

Consequences: any id the core holds — cache entries, radio handles, a
remembered queue origin — is invalid after a full rescan, and `lastscan` is
the signal to drop them. The New Music strip reflects scan order after a full
rescan, not what was recently added.

**Artwork was lost too:** albums with an `artwork_track_id` went from 4,521 of
4,554 before the rescan to 4,412 of 4,567 after (counted 19:14). El Mocambo
1977 had one before and none after. Not investigated; the library routes
return no artwork for those albums, which the panel shows as pending.

### 5. Artwork

20 random albums, one request each:

| URL | Type | Median | Largest |
|---|---|---|---|
| `cover` (original) | JPEG | 77 KB | 358 KB |
| `cover_300x300` | **PNG for 5 of 20**, JPEG otherwise | 27 KB | 245 KB |
| `cover_300x300_o.jpg` | JPEG, all 20 | 22 KB | 53 KB |
| `cover_150x150_o.jpg` | JPEG | 8 KB | 15 KB |
| `cover_500x500_o.jpg` | JPEG | 52 KB | 141 KB |

4,521 of 4,554 albums have an `artwork_track_id`.

### 6. Radio

- **Top level** (`radios 0 20 menu:radio`): 11 items, **no `id` on any**;
  Podcasts is identifiable only by `actions.go.cmd = ["podcast","items"]`;
  Search TuneIn carries `input`.
- **Walked four levels, three branches per node** (24 requests, 15 ms to
  1.7 s each): Radio Now Playing has 950 entries at its first level; Local
  Radio › Stations has 194.
- **Item shapes vary.** Folder items carry their own `actions.go`. Station
  items carry **no `actions`**: they have `goAction` (`play` or
  `playControl`), `type: audio`, `presetParams` (with the station's
  `favorites_url`), and depend on the list's `base.actions`.
- **The inherited action can be a play.** In the walk, the station lists'
  `base.actions.go` was `["radionowplaying","playlist","play"]` or
  `["local","playlist","play"]` with `nextWindow: nowPlaying`. **A walker
  that treated `base.actions.go` as "open" started playback** (below).
- **The shape depends on the request.** The same Stations list fetched
  without `menu:1` returned a `base.actions` with `play`, `playControl`
  (`local items`, `itemsParams: playControlParams`), `more`, `add-hold` and
  `set-preset-0…9`; its items had `goAction: playControl`. With the walk's
  parameters, `base.actions.go` itself was the play command.
- **Item ids are per browse session:** Stations was `2b4da216.0`, then
  `20fac368.0`, `a8d16f76.0`, `02bf5e1f.0` on later fetches. A handle cannot
  be an LMS `item_id` kept for long.
- **Item text is two lines** for stations: `"<station> (<genre>)\n<now playing>"`.
- `playlist play <presetParams.favorites_url>` plays a station directly.

### 7. Playback from a typed id

| Test | Command | Result |
|---|---|---|
| 1a album | `playlistcontrol cmd:load album_id:8566` | reply `count 23`; playing at the first sample (0.5 s); position counting by 2 s |
| 1b album artist | `cmd:load artist_id:9974` | 140 tracks (all Holograf), playing at 0.5 s |
| 1c track | `cmd:load track_id:116293` | queue of 1, playing at 0.5 s |
| 2 playlist | `cmd:load playlist_id:122543` | 4 tracks; **status carries `playlist_name`, `playlist_id`, `playlist_modified: 0`** |
| 3 add to queue | `cmd:add album_id:8566` | 4 → 27 tracks, playback uninterrupted; name and id kept, **`playlist_modified: 1`** |
| 1d from powered off | `stop`, `power 0`, then `cmd:load album_id:8566` | **LMS powered itself on**: `power 1, mode play` at 0.5 s; core `player powered on (acquisition)` and `lms takes the device (was nobody)` 0.68 s after the command. No `power 1` sent |
| 5 over Spotify | Spotify playing from George's phone; `cmd:load album_id:8566` | LMS on at 0.5 s; core: `lms takes the device (was spotify)` 1.73 s after the command; Spotify released in 0.2 s. **Then the defect below** |

After an album, artist or track load, `playlist_name` and `playlist_id` are
absent. Test 1a started with LMS already on and stopped (it had been switched
on at 18:13:43, not by this test).

## Defects found

### A. A takeover restores a stale position onto new content (live today)

Test 5, core log:

```
18:46:04.117 lms: paused and powered off at 192.6s (will resume playing: True)
18:46:23.032 lms: player powered on (acquisition)
18:46:23.328 lms: position was 0.0s, seeked back to the 192.6s it was released at
```

The 192.6 s belonged to the **radio station** Spotify had taken over from.
The new album's first track (216.5 s long) was seeked to 192.6 s; LMS status
read 205.7 s about 17 s later. `lms.py:596-633` restores the position (and
the play state) whenever one was recorded, without checking that LMS still
holds the same content. This is the ADR-0027 / Finding 018 resume, correct
for returning to the same content and wrong for a fresh load.

**Fixed 2026-09-17 (Phase 7 step 1a), rule A:** restore only if
`playlist_timestamp` is unchanged. See the addendum below and ADR-0027's
amendment.

**It is not library-specific:** test 5 used the same JSON-RPC an LMS app
uses, so starting anything from the Lyrion app after a Spotify or Bluetooth
session hits it on the current image. Agreed with George, 2026-09-17: fixed
as its own step before any other Phase 7 code (DEVELOPMENT Phase 7 plan).

### B. Radio: the song's title and artwork are dropped (criterion 9)

Test 4, station "100% Deutsch" via TuneIn. LMS reported
`current_title: "SCHLAGERPLANET RADIO Deutsch"` and `remoteMeta`
`{title: "Hand in Hand", artist: "Julian le Play", artwork_url:
"/imageproxy/…lastfm…jpg/image.jpg"}`. The core published:

| field | published | should be available |
|---|---|---|
| title | "SCHLAGERPLANET RADIO Deutsch" (the station) | "Hand in Hand" |
| artist | "Julian le Play" | same |
| artwork | `/music/-94298681189064/cover.jpg` | `remoteMeta.artwork_url` |

The published artwork URL returns LMS's **generic grey radio-tower
placeholder** (512×512 PNG); George saw exactly that on the panel. The
`artwork_url` redirects (301) to a 640×640 JPEG of the song. The adapter
builds artwork only from `coverid` (`lms.py:227-245`).

This is a second shape of criterion 9: Phase 6's KissFM case sent
`current_title` as a single space. Where the station name and the song title
each go on the screen is a step 2 question.

### Also observed: a one-track library queue looks like radio

Test 1c left a queue of one. ADR-0037's LMS rule disables Next, Previous and
Shuffle for a one-item playlist — written for a radio station. A single track
played from the library gets the same treatment. Not a defect by itself;
noted for the step that builds track play-now.

## How this finding started playback unintentionally

At 15:08:36 the radio walk sent nine `… playlist play` commands, by treating
`base.actions.go` as a browse. `gexis` powered on and played a TuneIn station
at LMS volume 22 for 45 s (core: `lms takes the device (was nobody)`, then
`relinquish` at 15:09:21 after it was stopped and powered off). No other
renderer was active. It replaced George's LMS queue on `gexis` (10 tracks);
George chose not to restore it. The mechanism is recorded in §6 because the
radio browser must not repeat it.

## Addendum, 2026-09-17 — step 1a: what changes `playlist_timestamp`

Same system, same session, all commands from R2D2 to player `gexis`, each
read 2.5 s after the command with `status`:

| change | `playlist_timestamp` |
|---|---|
| pause, resume | unchanged |
| next (`button jump_fwd`), previous (`button jump_rew`) | unchanged |
| repeat all, repeat off | unchanged |
| `pause` → `power 0` → `power 1` → `play` (the takeover cycle) | **unchanged** |
| shuffle on; shuffle off | **changed, each time** |
| `playlistcontrol cmd:add album_id:` | **changed** |
| `cmd:load` of the album already loaded | **changed** |
| `cmd:load` of a different album | **changed** |

The field is in the untagged `status - 1` the adapter already makes, as a
float. George chose rule A (restore only if unchanged) over "same current
track" (which would seek into a reload that starts on the same track) and
over both combined (no different outcome in these cases).

**Checked on `gexis` after hand-installing the fix** (`lms.py` into the
venv's site-packages; previous core at `/opt/gexis-core.7-1a-backup`):

- **New content over Spotify:** LMS released at 202.9 s; album loaded while
  Spotify played. Core: `queue changed since it was released
  (playlist_timestamp 1789664149.74079 -> 1789664609.64016), not restoring the
  old position or play state`. LMS at 1.75 s into track 1 seven seconds later.
- **Same content after Spotify:** George played the album past 30 s, started
  Spotify, then pressed play on `gexis` in the Lyrion app. LMS released at
  73.3 s; on return: `position was 0.0s, seeked back to the 73.3s it was
  released at`; 97 s at 19:05:30.

George reported "test done" for both; what was heard was not itemised.

**Seen on both takeovers, not investigated:** for about 4 s after LMS powers
on while Spotify still holds the device, `status` reports `time` equal to the
track's duration (216.5 s), then the real position. Probably LMS's value while
squeezelite waits for the device. The panel's progress bar may show it
briefly.
