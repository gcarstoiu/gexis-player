# ADR-0118 — Lyrion's own menus, plugins included

**Status:** **Draft** — 2026-10-04, written ahead of Phase 13f at George's
request (*"Draft it now but there will be more decisions and questions to be
asked around it when the time comes"*). Nothing here is decided; the
questions below are where it starts, not where it ends.
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

## Questions owed (to George, when 13f starts)

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

## To measure before the ADR is accepted

- **A cold first page** from a streaming service - Finding 110's timings were
  from Lyrion's cache.
- **TIDAL's menus**, with an account, and **Deezer's** if it is to be
  supported.
- **What the context menus hold**, for each app.
- **Paging**: lists of 200+ (and Radio Now Playing's 954) on the panel's
  windowed lists - with ADR-0067's windowing, and without the scroll
  anchoring that ran the queue away (LESSONS 58).
