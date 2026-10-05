# Finding 111 — Lyrion's menus, measured for Phase 13f

**Date:** 2026-10-05
**Question:** [ADR-0118](../decisions/0118-lyrion-s-own-menus.md)'s *To measure
before the ADR is accepted*, after George's answers to A-F: how long a
streaming app's first pages take, what context menus hold, how the long lists
page - and, for decision A's tiles, exactly which top categories Lyrion's home
menu has and how My Music's entries can be told apart.

**Scope:**
- **One server:** George's Lyrion (LMS 9.x at 192.168.178.188:9000), player
  `gexis` (88:a2:9e:79:e1:32), over JSON-RPC (`slim.request`), from R2D2 on
  the same LAN. Apps installed: Qobuz, Spotty, YouTube, Radio Paradise,
  Sounds & Effects, and TIDAL (no account; not measured, at George's word:
  *"No tidal or Deezer"*).
- **Read only, by Finding 110's rules:** a list was opened only through a
  browse command (last word `items` or `browselibrary`); nothing was played,
  added, searched, set or run. Context menus were **listed**, never acted on.
  Scripts: `m13f_home.py`, `m13f_apps.py`, `m13f_cm.py` in that session's
  scratchpad.
- **"Cold" is mostly not cold.** By mistake, Finding 110's walker
  (`lmswalk.py`, the same read-only rules) **ran again just before the
  timings** - importing it from a new script started its walk. It opened
  every top entry two levels deep, the first 12 items of each list, so
  **an app's top list and the lists one level below were freshly opened**
  when they were timed. Those are reported as *first open* and *again*, not
  cold. Truly cold numbers are only the lists the walker never reached: an
  item past the 12th of a second-level list (*cold* below).
- One run each, at about 21:30 on a Monday; no repeats over time.

## The home menu (decision A's tiles)

`menu 0 500 direct:1`: **51 items** (Finding 110 had 44), by the node they
hang under:

| Node | Items | What |
|---|---|---|
| `home` | 6 | My Music (`myMusic`), Favourites (`favorites`), Radio (`radios`), My Apps (`opmlmyapps`), Search (`globalSearch`, an `input`), **Turn On gexis** (`playerpower`) |
| `myMusic` | 14 | see below |
| `radios` | 12 | RadioNet and Radio Now Playing, then TuneIn's ten (presets, local, music, news, sports, talk, location, language, podcasts, search) |
| `settings`, `settingsAudio`, `advancedSettings` | 13 | Don't Stop The Music, Repeat, Shuffle, Alarm Clock, Sleep, Synchronise, Squeezebox Name, Fixed Volume, Crossfade, Volume Adjustment, Albums Sort Method, Squeezebox Information, Audio |
| `""` (none) | 6 | **the apps**: Qobuz, Radio Paradise, Sounds & Effects, Spotty, TIDAL, YouTube - each `isApp: 1`, reached through My Apps (`myapps items`) |

- **A top category is an item with `node: home`.** Today: My Music,
  Favourites, Radio, My Apps, Search, and the power item. One an app adds -
  decision A's *a tile before Apps* - would arrive the same way.
- **Lyrion's global Search is a top category of its own** (`globalSearch`,
  `input`), beside My Music's own Search.
- **`playerpower` reads "Turn On gexis"**: Lyrion has the player powered
  off between uses. Not touched; it is the item ADR-0118 C leaves out.
- **Radio grew** RadioNet since Finding 110; it is Lyrion's Radio branch, not
  our Radio screen (F: ours stays).

### My Music, by id (decision C's filter)

| id | Text | weight | icon |
|---|---|---|---|
| `myMusicArtistsAlbumArtists` | Album Artists | 9 | `html/images/artists.png` |
| `myMusicArtistsAllArtists` | All Artists | 11 | `html/images/artists.png` |
| `myMusicArtistsComposers` | Composers | 12 | yes |
| `myMusicAlbums` | Albums | 20 | - |
| `myMusicAlbumsVariousArtists` | Compilations | 22 | yes |
| `myMusicGenres` | Genres | 30 | - |
| `myMusicWorks` | Works | 35 | `html/images/works.png` |
| `myMusicYears` | Years | 40 | - |
| `myMusicNewMusic` | New Music | 50 | - |
| `myMusicMusicFolder` | Music Folder | 70 | - |
| `myMusicPlaylists` | Playlists | 80 | - |
| `myMusicSearch` | Search | 90 | - |
| `opmlselectVirtualLibrary` | Library Views | 100 | - |
| `opmlselectRemoteLibrary` | Remote Music Libraries | 110 | - |

- **The two to leave out have stable ids**: `myMusicArtistsAlbumArtists` and
  `myMusicPlaylists` - filtered by id, never by title (titles follow
  Lyrion's language).
- **Works** is new since Finding 110 (LMS 9's classical works).
- **The order is `weight`**, ascending.

### Icons

- **Few items carry one**: 5 of 51 have `icon` (four My Music entries, the
  artists' and works' pictures); My Apps and each app carry
  `window.icon-id`, a plugin's own image (`plugins/Qobuz/html/images/qobuz.png`).
- **Inside the apps, most items have `icon`** - Lyrion's or the plugin's
  (`html/images/albums.png`, `plugins/Spotty/html/images/home.png`), or the
  cover for an album or playlist.
- So **the new tiles' icons and colours are ours to draw** (George: *"all
  tiles get icons and color"*); Lyrion supplies none for My Music, Favourites
  or Apps.

## The apps' first pages

| App | Top list (count) | First open / again | Second level | First open / again |
|---|---|---|---|---|
| Qobuz | 10 | 8 / 4 ms | My Purchases (1) | 245 / 7 ms |
| | | | My Favourites (2) | 221 / 10 ms |
| Spotty | 11 | 19 / 19 ms | Home (62) | **1,109** / 20 ms |
| | | | What's New (98) | 770 / 49 ms |
| YouTube | 15 | 4 / 4 ms | Video Categories (1) | 329 / 296 ms |
| | | | My Subscriptions (1) | 10 / 10 ms |
| Radio Paradise | 8 | 34 / 6 ms | Main Mix (4) | 15 / 7 ms |
| Sounds & Effects | 4 | 5 / 4 ms | Alarm Sounds (16) | 4 / 4 ms |

**Cold** - lists nobody had opened (an item past the 12th):

| Path | Cold | Again |
|---|---|---|
| Spotty / Home / Soft Pop Mix (50) | **667 ms** | 52 ms |
| Spotty / What's New / harte mackerinnen ep (18) | 219 ms | 71 ms |
| Qobuz / Bestsellers / the 26th album (13 items) | 13 ms | 12 ms |

- **An app's own menus are Lyrion's, and instant** (4-34 ms).
- **A page from the service is not**: Spotty's took 0.2-1.1 s the first
  time, even one opened by the walker minutes before - its cache is short.
  The panel has to show that a list is loading.
- **Qobuz fetches a list whole**: Bestsellers' first page of 100 took 495 ms,
  its second 12 ms; an album inside it opened in 13 ms, cold, the list's
  answer having carried it.
- **YouTube without OAuth** answers *"Oauth configuration missing"* as a
  text item; its categories are empty. Its 15 entries are 11 searches.

## Context menus

**A context menu is the list's base `more` action with the item's own
parameters** (named by `itemsParams`, here `params`) - and **only with
`xmlBrowseInterimCM:1` is it the menu** a remote shows. Without it (and with
`isContextMenu:1` alone) Qobuz answered with the release's own page and Spotty
with the playlist's tracks.

| Where | With `xmlBrowseInterimCM:1` |
|---|---|
| Qobuz, an album (Bestsellers' 26th) | **Add to End, Play Next, Play**; then the release's own page: its tracks, *Artist: …*, **"Add Release '…' to Qobuz favourites"**, Credits, genre, release type, duration, track count, volume adjustment, release date, label, copyright |
| Spotty, a playlist (Home / Daily Mix 1) | **Add to End, Play Next, Play, Save to Favourites**; then its tracks |
| My Music, an album (`albuminfo items`) | Add to End, Play Next, Play, Save to Favourites; Album Artist, Track Artist, Composers, Album, Year (each a playable container with its own `more`); **On Spotify: …** (Spotty adds itself to the library's menus); disc, duration, release type as text; Artist information |
| Radio Paradise, Sounds & Effects | no `more` of their own on the items read |

## Paging

| List | Count | Per page of 100 |
|---|---|---|
| Radio Now Playing | **955** | 32-43 ms (pages at 0, 100, 200, 800) |
| Qobuz Bestsellers | 189 | 495 ms the first, 12 ms the next |
| Spotty What's New | 98 | 770 ms first open (one page) |
| My Music Albums | 4,780 | 30 ms |

- **Pages are asked for by start and count** (`<cmd> <start> <n> … menu:1`),
  and `count` comes with the first: the panel's windowed lists (ADR-0067) can
  ask for the rows they show.

## What this means for 13f

- **Filter by id**: My Music's two left out are `myMusicArtistsAlbumArtists`
  and `myMusicPlaylists`; the player's settings are whole nodes (`settings`,
  `settingsAudio`, `advancedSettings`) plus `playerpower`.
- **Top categories are `node: home` items**; apps are `isApp: 1` and come
  from `myapps items`.
- **"Only browse commands" is not read-only.** Qobuz's *Add Release to Qobuz
  favourites* is a `qobuz items` command, opened with `go` like any folder,
  and it writes to the account. A walker or a test must not open an item it
  has not read the title of; on the panel, tapping it is the user's choice,
  but it is an action, not a folder - decision D (context menus later) does
  not keep it out, because it sits on the album's own page.
- **A loading state is needed**: 0.2-1.1 s for a service's page.

## Not seen, and why it matters

- **Truly cold top lists**: the walker had just opened them (above). The apps'
  own menus are Lyrion's and measured fast regardless; the service pages are
  where the time is, and those were measured cold only past the 12th item.
- **Searches**: none submitted, by the rules - so a search's time and the
  shape of its results are unmeasured. Search is the front door of Qobuz,
  Spotty and YouTube (Finding 110).
- **Context menus of Radio Paradise, Sounds & Effects and YouTube's results**:
  the items read had none, and YouTube lists nothing without OAuth.
- **TIDAL and Deezer**: not to be supported for now (George).
- **Over time**: one run, one evening; a busier server or a slower service
  could be slower.
