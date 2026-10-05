# ADR-0118 — Lyrion's own menus, plugins included

**Status:** **Accepted in part** - 2026-10-05, George answered A-F (below,
*Decided*); three smaller questions and the measurements are still owed
(*Still open*). Drafted 2026-10-04 ahead of Phase 13f.
**Builds on:** [ADR-0030](0030-library-typed-radio-slimbrowse.md) (radio: the SlimBrowse walk, by
handle), [ADR-0028](0028-ui-serving-and-command-channel.md) (the API is open to the LAN by
decision), [ADR-0106](0106-plugins-you-install-and-update.md) (what a plugin
is today), [ADR-0022](0022-settings.md) (every setting inventoried). On
[Finding 110](../findings/110-what-lyrion-s-own-menus-hold.md).
**Phase:** 13f (`docs/DEVELOPMENT.md`).

## Context

George, 2026-10-04: *"can we make a plugin which extends the lyrion server
navigation. Basically have everything that lyrion has as navigation items,
including plugins."*

The panel's music screens are our own: Browse, Artists, Playlists, New
Music, each a query we chose, and Radio - the one place the panel walks
Lyrion's own menu tree (SlimBrowse, what iPeng and Material draw). The core
walks it and hands the panel an opaque **handle** per item; the panel never
sends a Lyrion command (ADR-0030). Everything Lyrion's plugins offer - the
streaming services, Radio Paradise, YouTube - lives in that same tree under
**My Apps**, and is out of reach today.

### What the tree holds (Finding 110)

- **The home menu:** 44 items on George's server - My Music (13), Radio
  (11), Favourites, My Apps, Search - and, **in the same tree, the player's
  own settings** (name, sleep, alarms, sync, crossfade, fixed volume…) and
  **Turn Off**.
- **My Apps**, with Qobuz, Spotty, YouTube, Radio Paradise and Sounds &
  Effects installed: lists of up to 200 albums and playlists; search as the
  front door of the streaming apps (YouTube: 11 of 15 entries); Spotty's
  **Transfer Playback**, which moves playback between devices.
- **The kinds of item:** folders (`go`, `link`, `outline`, `redirect`,
  `url`); playables (`audio`, `itemplay`); **playable containers**
  (`playlist`: open, or play / add whole); text; search inputs; one-off
  actions (`do`); context menus (`more`) on nearly every list; preset
  assignments (`set-preset-N`).

## Proposal (a starting point)

1. **Widen Radio's walker into a general one.** It enters at Lyrion's home
   menu instead of `radios`, keeps the handle model - the panel still never
   sends a command - and keeps ADR-0030's rule that an item's *resolved*
   command decides what it is (Finding 029: a station's inherited action
   plays).
2. **One generic list screen,** on the standard and bar families, drawing
   the kinds above with Lyrion's own icons: open, play, add, play next;
   two-line entries; a search box where an item asks for text.
3. **Reached from a tile of its own** - *Lyrion*, or *More* - beside our
   screens, which stay as they are.
4. **Built in, behind a setting**, rather than a new kind of plugin: ours
   run software (renderers, services) and none adds navigation.
5. **Whole branches left out by construction**, as Radio leaves out what it
   does not walk: the player's settings, Turn Off, alarms, sync.

## Decided (George, 2026-10-05)

- **A. More tiles on the home screen**, in this order: **My Music** (Lyrion's)
  before Browse; Browse, Artists, Playlists as today; **Favourites** after
  Playlists; Radio as today; **Apps** before Settings. A top-level category
  an app adds to Lyrion's home menu later gets a tile of its own, **just
  before Apps**.
- **B. Built in, behind a setting**: **Extended navigation**, in the Lyrion
  client's settings, **off by default** (ADR-0022's inventory, appended on
  his confirmation). Off, the home screen is as today.
- **C. Everything but the player's settings** - Alarm Clock, Synchronise,
  Turn Off and the rest of Lyrion's settings branches stay out. From My Music,
  **Album Artists and Playlists are left out**, since our own Artists and
  Playlists cover them; the rest of My Music stays (Music Folder, Genres,
  Years, Composers, Compilations, New Music, Albums, All Artists, Library
  Views, Remote Music Libraries, its Search).
- **D. Open, play, add to queue and play next only.** What is left for later
  is recorded below (*Not in this iteration*).
- **E. Search** is where Lyrion's search item is; text comes from the
  phone's keyboard (ADR-0121); past searches are not remembered.
- **F. Our Radio screen stays as it is.**
- **No TIDAL or Deezer**: neither is to be measured or supported for now.
- **The player's own style** (George): every new tile has an icon and a
  colour, as Browse, Artists, Playlists and Radio do; the lists look like
  ours, not Lyrion's.
- **A list or tiles switch** (George) on the screens this adds.

### Not in this iteration (D)

- **Context menus** (`more`): add to favourites, go to the artist or album,
  an app's own extras.
- **Spotty's Transfer Playback**, which moves playback to another device.
- **Preset assignment** (`set-preset-N`), which rewrites a Squeezebox's
  buttons.
- **Remembered searches.**
- **One-off actions** (`do`) other than playing - none met so far is music.

## Questions owed (to George, when 13f starts) - answered above


- **A. Where it lives.** A tile beside our screens (proposed), or in place
  of some of them - and on a bar, where the home row is already six tiles.
- **B. Plugin or built in.** A setting is proposed; if so, its row goes to
  ADR-0022's inventory once confirmed. Or a new plugin kind that adds
  navigation - a larger change to ADR-0106.
- **C. What is reachable.** Which branches stay out: the settings and Turn
  Off are proposed out; My Music duplicates our own screens (in, out, or
  in as an alternative view); Favourites and presets.
- **D. Actions that are not browsing.** Spotty's Transfer Playback moves
  playback; preset assignment rewrites a Squeezebox's buttons; context menus
  add favourites. Which are offered, and how they are confirmed.
- **E. Search.** The streaming apps need typed text; the panel's keyboard is
  the user's (settled). Where the box sits, and whether a search is
  remembered.
- **F. Our curated screens.** Whether Radio becomes a view of this, or stays
  its own.

## Option: the phone as the panel's touchpad and keyboard

George, 2026-10-04: *"Can we use the phone as a mouse and keyboard for the
panel? ... Expand upwards the volume panel and add an area that would work
as a touchpad controlling the pointer on the display. When tapping inside a
search field then the phone's keyboard would pop up and allow text entry.
We can also consider multi touch gestures - i.e. two fingers up or down
control volume etc."* Then *"Yes. Add it."* - as an option for question E,
not decided.

- **Inside our own page** (proposed, of two). The phone's touchpad sends
  finger movement over its existing connection to the core; the panel's
  page draws its own pointer and turns a tap into a tap on what lies under
  it. Everything the panel shows is our page (the visualiser, a separate
  window, needs only taps to leave). The other way - a system-level virtual
  mouse and keyboard, the image's `wlrctl` already speaks the protocols -
  reaches windows we do not need and brings back a pointer the panel hides
  by design.
- **Typing:** a tap that lands in a text field makes the phone show a text
  box, and what is typed appears on the panel as it is typed; any character
  works, since the page inserts text rather than key presses.
- **The catch:** a web page opens the phone's keyboard only in direct answer
  to a tap on the phone, and the panel's "that was a text field" arrives
  after that moment - strictly so on an iPhone. So **one extra tap**: a
  *Type* field the phone shows while the panel has a text field active, or a
  keyboard button on the touchpad. To be tried on both kinds of phone.
- **Gestures**, seen by the phone first and sent as commands the core
  already takes: two fingers up or down for volume, sideways for previous
  and next, a two-finger drag to scroll a list on the panel.
- **Where:** the phone's volume sheet, extended upwards - already its
  "control the player" place - with the touchpad above the slider.
- **Nothing newly exposed:** anyone on the LAN can already control the
  player and its settings from the phone page (ADR-0028).

It answers question E for every search box on the panel, Lyrion's and
ours; it may also stand on its own, as a small phase before 13f.

**Taken up as [ADR-0121](0121-the-phone-as-the-panel-s-touchpad-and-keyboard.md)**
(accepted 2026-10-05), which answers question E.

## To measure before the ADR is accepted

- **A cold first page** from a streaming service - Finding 110's timings were
  from Lyrion's cache.
- **TIDAL's menus**, with an account, and **Deezer's** if it is to be
  supported.
- **What the context menus hold**, for each app.
- **Paging**: lists of 200+ (and Radio Now Playing's 954) on the panel's
  windowed lists - with ADR-0067's windowing, and without the scroll
  anchoring that ran the queue away (LESSONS 58).
