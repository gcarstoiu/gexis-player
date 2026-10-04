# Finding 110 — What Lyrion's own menus hold

**Date:** 2026-10-04
**Question:** George: *"can we make a plugin which extends the lyrion server
navigation. Basically have everything that lyrion has as navigation items,
including plugins."* Before an ADR: what does a Lyrion server's own menu tree
(SlimBrowse, what iPeng and Material draw) actually contain, and what kinds
of item would a generic browser have to draw?

**Scope:**
- **One server:** George's Lyrion at 192.168.178.188, LMS 9.x, as player
  `gexis`. Its **My Apps holds one app** (Sounds & Effects): no streaming
  service plugin was installed, so their menus were **not** seen.
- **Read only.** A walker (`lmswalk.py`, that session's scratchpad)
  followed an item's own *go* action only when its command was a browse
  (last word `items` or `browselibrary`), never `play`, `add` or `playlist`,
  never a setting; it skipped anything asking for typed text.
- **Two levels** below each top entry, the first 12 items of each list, the
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

## Not seen, and why it matters

- **A streaming plugin's menus** (Spotty, TIDAL, Qobuz, Deezer…): none was
  installed. They publish in this format, but they commonly add input
  items (search), context menus (`more`), and slow first pages from a
  remote service. A server with one installed is needed before the ADR
  settles their item kinds.
- **Context menus** (`more` actions: add to favourites, artist info) - the
  walker did not open them.
- **Settings items' kinds** (checkbox, choice, slider) - not opened, by
  design.
