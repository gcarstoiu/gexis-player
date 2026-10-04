# Finding 110 — What Lyrion's own menus hold

**Date:** 2026-10-04
**Question:** George: *"can we make a plugin which extends the lyrion server
navigation. Basically have everything that lyrion has as navigation items,
including plugins."* Before an ADR: what does a Lyrion server's own menu tree
(SlimBrowse, what iPeng and Material draw) actually contain, and what kinds
of item would a generic browser have to draw?

**Scope:**
- **One server:** George's Lyrion, LMS 9.x, as player `gexis`. First walk:
  its My Apps held one app (Sounds & Effects). **Second walk**, the same
  day: Qobuz, Spotty, TIDAL (no account), YouTube and Radio Paradise
  installed.
- **Read only.** A walker (`lmswalk.py`, that session's scratchpad)
  followed an item's own *go* action only when its command was a browse
  (last word `items` or `browselibrary`), never `play`, `add` or `playlist`,
  never a setting; it skipped anything asking for typed text.
- **Two levels** below each top entry (three in My Apps, second walk), the first 12 items of each list, the
  first 100 of each page - a sample of the shapes, not a census.

## The home menu

`menu 0 500 direct:1` for the player: **44 items**, grouped by the node they
hang under.

| Node | Items | What |
|---|---|---|
| `home` | 6 | My Music, Favourites, My Apps, Radio, Search, **Turn Off gexis** |
| `myMusic` | 13 | Library Views, Remote Music Libraries, Music Folder, Genres, All Artists, Album Artists, Composers, Years, New Music, Compilations, Playlists, Albums, Search |
| `radios` | 11 | Radio Now Playing, My Presets, Local Radio, Music, News, Sports, Talk, By Location, By Language, Search TuneIn, Podcasts |
| `settings`, `settingsAudio`, `advancedSettings` | 13 | Don't Stop The Music, Repeat, Shuffle, Alarm Clock, Sleep, Synchronise, Squeezebox Name, Fixed Volume, Crossfade, Volume Adjustment, Albums Sort Method, Squeezebox Information, Audio |

**The player's own settings live in the same tree** as the music - naming
the player, sleep, alarms, sync, crossfade, fixed volume - and so does
**Turn Off** (an action, `do`, not a browse).

## The kinds of item met

| Kind | Where | What a browser must do |
|---|---|---|
| Folder (`actions=go`, or `type=link`) | everywhere | open the next level |
| Playable (`type=audio`, `style=itemplay`) | radio, podcasts | play / add / play next |
| Text (`type=text`, `style=itemNoAction`) | empty Favourites, Presets | show, inert |
| Redirect (`type=redirect`) | My Apps | open where it points |
| Search (`type=search`, `input`) | Radio Now Playing's first item, Search TuneIn, the Searches | ask for text - **not followed** |
| Action (`do`) | Turn Off | run once - **not followed** |

Lists run from one item to **954** (Radio Now Playing). My Music's entries
are `browselibrary items mode:…` - the library our own Browse, Artists,
Playlists and New Music screens already draw.

## My Apps, with streaming plugins (walked again, the same day)

George then installed **Qobuz**, **Spotty** (Spotify), **TIDAL** (no
account, so it lists nothing), **YouTube** and **Radio Paradise**. The same
read-only rules, three levels deep:

| App | Top level | What lies below |
|---|---|---|
| Qobuz | 10 entries: Search, My Purchases, My Favourites, My Playlists, Qobuz Playlists, Bestsellers, New Releases, In the Press, Qobuz Selection, Genres | lists of up to **200** albums and playlists (`type=playlist`), the account's own 98 playlists; Search is an input |
| Spotty | 11: Home, Search, What's New, Top Tracks, Genres and Moods, Popular Playlists, Albums, Artists, Playlists, Podcasts, **Transfer Playback** | playlists and albums by the hundred, tracks (`style=itemplay`), artists with no actions of their own; Transfer Playback lists the account's devices - choosing one would **move playback** |
| Radio Paradise | 8: six mixes (`type=outline`), two streams | each mix offers its streams in several qualities (FLAC first) |
| YouTube | 15: categories, and **11 searches** (video, music, channel…) | search-led; categories empty here |
| TIDAL | nothing without an account | - |
| Sounds & Effects | 4 groups | short audio clips |

**New kinds of item**, beyond the first walk:

| Kind | Seen in | What a browser must do |
|---|---|---|
| Playable container (`type=playlist`) | Qobuz, Spotty | open it, **or** play / add it whole |
| `type=outline` | Radio Paradise | a folder |
| `type=url` | YouTube | open a URL-backed list |
| Item with no actions, the list's `base` deciding | Spotty's artists | resolve the action from the list, as Radio already does |
| Two-line text (`Title\nArtist`) | Qobuz, Spotty | a title and a subtitle |
| `more` (context menu) on nearly every list | all apps | an item's menu: favourites, artist, album… |
| `set-preset-0`…`9` | Radio Paradise, Spotty, Sounds | assign a preset button (a Squeezebox's) |

**Search is central** for the streaming apps (Qobuz, Spotty, YouTube): a
browser without typed input reaches only their curated lists.

**Speed:** the apps' top lists answered in 5-19 ms; Qobuz's Bestsellers and
Spotty's Home, in about 20 ms - **just after the walk had opened them**, so
from Lyrion's cache. A first opening cold, from the service, was not
measured and will be slower.

## Not seen, and why it matters

- **TIDAL's and Deezer's menus**: TIDAL had no account, Deezer was not
  installed.
- **A cold first page** from a streaming service.
- **Context menus** (`more` actions: add to favourites, artist info) - the
  walker did not open them.
- **Settings items' kinds** (checkbox, choice, slider) - not opened, by
  design.
