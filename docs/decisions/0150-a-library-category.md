# ADR-0150 — A Library category

**Status:** **Accepted** — 2026-10-18, George: *"Since this is now more of a
library, let's create a Library category in the settings and add lyrion server
there. Once MPD will be done, then it will also live there."* Amends ADR-0115
(the Lyrion server's rows were under Sources) and the plugin contract's areas
(ADR-0086, ADR-0088).

## Context

The Lyrion Server's rows grew from a switch and its shares to a library of
their own: the *Library* read-out (ADR-0115 decision 28), the Music folder,
USB drives and folders, network shares. They sat under *Sources* beside the
players' clients (Lyrion Client, Spotify, Bluetooth), which play music rather
than hold it. Phase 15 (`ph-mpd`) brings a second library.

## Decision

1. **Settings gains a Library category**, after Sources. The Lyrion Server's
   rows move there, its *Library* read-out first; MPD's will join it.
2. **A plugin may declare `"area": "library"`**, beside `sources`,
   `system` and the rest: its rows go to the Library category, and on the
   Plugins page it is listed under *Library*, as Beszel is under *System*
   (George: *"we need to extend also there and have a Library type, just
   like we have system for Beszel"*). The Lyrion server's manifest declares
   it.
3. **The category says where the rest is**: a read-only row, *More for your
   library*, with *Everything else about the library is on the Lyrion
   server's own page* and links to it and to three apps that control
   Lyrion - Squeezer (Android, Google Play), Lyrion (Android, F-Droid) and
   LyrPlay (iPhone, App Store), as Lyrion's own list of applications gives
   them (lyrion.org/extensions/applications, read 2026-10-18). George chose
   these three, not iPeng. Shown only while the server is on, and the links
   on the phone only: on the panel they would lead nowhere.
4. **Rows may carry links** (`links`: label and address) for this; a link
   opens in a new tab.

## Consequences

- The plugin contract and the plugin manual list `library` among the areas.
- A plugin that names an area this release does not know still falls back by
  its kind, as before.
