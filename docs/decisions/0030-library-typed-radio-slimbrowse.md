# ADR-0030 — Library by typed query, radio by SlimBrowse rooted at `radios`

**Status:** Accepted
**Date:** 2026-09-14
**Raised by:** George — *"why did we select slimbrowse and not build everything
based on LMS capabilities so that we are in control of what we display?"*
**Supersedes:** [0020](0020-library-browse-tree.md)'s "SlimBrowse is the
internal browse protocol — adopted as-is, pass-through"
**Amends:** `docs/DEVELOPMENT.md` Phase 7 acceptance criteria

## What ADR-0020 did not consider

ADR-0020 took the architecture's premise — *"the browse tree is data rather
than screens"* — and verified that SlimBrowse could drive a generic browser.
It never wrote up the alternative: that LMS also exposes a conventional typed
query API, and that we could build our own screens on it.

That omission is the gap this record closes. The challenge was fair and the
answer is not the one ADR-0020 assumed.

## The two mechanisms, measured

Against George's LMS 9.1.1, player `gexis`, 2026-09-14.

**SlimBrowse** — `browselibrary items mode:albums`:

```json
{"text": "+\nEd Sheeran", "icon": "music/94366386/cover",
 "commonParams": {"album_id": "1162"}, "type": "playlist"}
```

The server chose the label format, the icon and the tap behaviour. We render
what we are given.

**Typed query** — `albums 0 3 tags:jlyaS`:

```json
{"album": "+", "artist": "Ed Sheeran", "year": 2011,
 "artwork_track_id": "94366386", "artist_id": 403, "id": 1162}
```

Structured fields. We choose the layout, the sort and the artwork size.

## Decision

**The local music database is browsed with typed queries and our own screens.
Everything whose content model belongs to a plugin is browsed with SlimBrowse.**

The boundary is *"does LMS have a typed API for this"*, not *"is it library or
radio"*. That distinction matters: **Favourites** is not radio but is menu-only,
and **Random Mix** is library-shaped but is a plugin. The rule sorts both
correctly; "library vs radio" does not.

### Typed — our own screens

All verified against the live server, with counts as measured:

| Screen | Query | Count |
|---|---|---|
| Albums | `albums` | 4554 |
| All Artists | `artists` | 7292 |
| Album Artists | `artists role_id:ALBUMARTIST` | 916 |
| Composers | `artists role_id:COMPOSER` | 3589 |
| Genres | `genres` | 320 |
| Years | `years` | 81 |
| Compilations | `albums compilation:1` | 105 |
| New Music | `albums sort:new` | 100 |
| Songs | `titles` | 60974 |
| Playlists | `playlists` | 1 |
| Music Folder | `musicfolder` | ✓ |
| Works | `works` | valid command, 0 in this library |

Artwork is `artwork_track_id` → `/music/<id>/cover`, the same URL SlimBrowse
returns.

### SlimBrowse — one generic browser, rooted at `radios`

**The entry point is `["radios", "menu:radio"]`, not `home`.** Verified to
return a standalone SlimBrowse `item_loop` without traversing the home menu.

This is an entry-point choice, not a filter. Everything unwanted is not
filtered out — it is never reachable:

- LMS's own `settings` node, and with it the contradictions that node carries:
  **Fixed Volume** and **Volume Adjustment** against [0018](0018-volume-and-output-modes.md),
  **Squeezebox Name** against [0022](0022-settings.md)'s one-device-name rule,
  and **Synchronise**, which is out of scope
- `My Apps` — Qobuz, SpotOn, Sounds & Effects
- Global Search and `myMusic → Search`, which are typed-query screens now
- Radio Paradise, which sits at the app level (`["radioparadise","items"]`),
  *not* under `radios` — **George, 2026-09-14: not wanted**

**Podcasts is excluded explicitly.** It is inside the `radios` node
(`["podcast","items"]`, id `opmlpodcast`) so it would otherwise come for free.
George, 2026-09-14: not wanted. This is the one id we exclude by name.

The resulting radio surface is nine items: Radio Now Playing, My Presets,
Local Radio, Music, Sports, News, Talk, By Location, By Language.

### Text-input items are dropped wherever they appear

Today that is exactly one — **Search TuneIn**, inside `radios`. The rule is
kept general anyway: the TuneIn subtree is plugin-driven and can change under
us on an LMS update, so a rule costs nothing where a hardcoded exception would
rot.

Detection is mechanical, from the payload: an `input` block, or
`__TAGGEDINPUT__` / `__INPUT__` in the action params. No curated list, so it
keeps working as plugins change.

This is [0020](0020-library-browse-tree.md)'s first branch applied literally —
*if the capability does not exist, hide it* — and it is consistent with
[0029](0029-text-entry-on-every-surface.md): the designs carry no text-entry
widget, so the capability does not exist in our UI on any surface.

## Presentation

**Two separate areas, Library and Radio, both styled from the provided
designs** (George, 2026-09-14).

So the split is visible in navigation but not in appearance: server-supplied
radio items render into *our* components, not into a second visual language.
With the surface reduced to nine items and their children, the shapes involved
are a label, an icon and a `go` action — tractable for our own list row.

## What this costs

**Two navigation models in one browser.** Real complexity, but each half is
simpler than the single generic browser ADR-0020 assumed, and the typed half —
where nearly all use lives — gains full control of paging, sorting and artwork.

**We give up automatic plugin support.** A plugin installed on the server no
longer appears by itself. That is the point, not a regression, but it is a
standing cost: adding a streaming service later becomes our work.

## Unverified — do not treat as settled

- **Playback from a typed id.** The mechanism is
  `playlistcontrol cmd:load album_id:<id>`, and it is the load-bearing
  assumption of the typed half. **Not executed**, because running it would
  start music on George's system unannounced. Verify at the device before
  building on it.
- **`libraries` (Library Views)** returned `{}`, indistinguishable from an
  unknown command, because no virtual libraries are defined on this server.
  Unresolved, not covered.
- **`Radio Now Playing`** is a plugin display rather than a browse node. Left
  in the nine for now; whether it belongs in a browse list is open.
- **Deeper radio levels.** Only the top of the `radios` subtree was walked.
  Child item shapes under Music / By Location and similar are not characterised.
