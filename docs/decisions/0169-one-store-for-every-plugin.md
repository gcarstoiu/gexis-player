# ADR-0169 — One store for every plugin

**Status:** **Accepted** 2026-10-30 (George: option B of the mock-ups, the
finished canvas approved, and both open questions as recommended). Phase 24
(`ph-plugin-catalogue`), step 6, before 1.10.0 (George). The shape was
chosen by George from mock-ups (a Claude Design canvas, *Plugins: one look
or one store*: option B, finished with the bar and Remove). Changes [ADR-0168](0168-a-plugin-catalogue.md)
decision 7 (*More plugins* built from the Plugins page's rows) and what
[ADR-0106](0106-plugins-you-install-and-update.md) and
[ADR-0100](0100-software-we-may-not-redistribute-is-fetched-on-the-device.md) say a row shows and
Remove deletes. Delivery and trust do not change: ours come with the release
(ADR-0106 decision 4), others' through the catalogue or a file.

## Context

By 1.10.0 a user would meet four kinds of plugin, told apart by notes on
their rows: ours that download their software (Plexamp, Beszel), ours with a
page of their own (the Beszel hub, the Lyrion Server), uploaded ones, and
the catalogue's behind *More plugins*. George found that confusing: a plugin
should be a plugin (2026-10-30). Volumio has one store for all its plugins,
its own included; Lyrion one list of its own and third-party plugins; moOde
none (ADR-0168, *Changed*).

## Decided (George, 2026-10-30)

1. **The Plugins page lists what is added to this player**, on or off, every
   plugin in the same row: its name, a tag for where it came from (*Gexis
   Player*, *Catalogue*, *Uploaded*), its version, one line on what it does,
   its switch, and *Update to …* and *Remove* where they apply. Rows no
   longer say *Not part of Gexis Player*: the tag says where it came from,
   and the notice before adding it says the rest.
2. **One page, *Add plugins*, lists everything that can be added**: ours not
   added yet beside the catalogue's, each a tile with its name, tag, what it
   does, its kind and author (ours: *in the player, updated with it*), what
   it asks for (ADR-0170), its source, and one button, **Add**. On a phone
   or computer it ends with *Upload a plugin*, from a file. Its row on the
   Plugins page comes first and counts the updates waiting.
3. **Switching off keeps a plugin on the Plugins page; Remove takes it off
   the player and back to *Add plugins*.** One dialog for every plugin:
   what is deleted (what it downloaded, or its package), and a switch,
   **Keep its settings and sign-in**, on unless turned off.
4. **Setup stays a set of questions.** What it chooses is added; its hints
   point to *Add plugins*. It offers only ours: the player reads the
   catalogue only once it is on the home network.
5. **The same on the phone, the panel and the bars** (the canvas's boards).

## Proposed (Claude)

6. **Added is a state of its own** for ours: `_plugins_added`, the ids added
   to this player, kept in the settings store (so a backup carries it).
   *Add* sets it and switches the plugin on (its manifest's `notice` first, and
   its download as today); *Remove* switches it off, runs the existing
   remove of what it downloaded (ADR-0100), and clears it. An uploaded or
   catalogue plugin is added while its package is installed, as now.
7. **The visualiser skins are one of ours in the store**: *Add* is the
   `visualiser_skins` switch and its pack for this screen; Remove deletes
   the pack.
8. **Keep its settings and sign-in**: on, Remove keeps the plugin's
   settings (`<id>.*`) and data (an uploaded or catalogue plugin's
   `/var/lib/private/gexis-uploaded/<id>`, ours as each manifest's `removes`
   says today), and adding it again finds them. Off, they go too: an
   uploaded or catalogue plugin as ADR-0106 does now, ours reset to their
   defaults and their data deleted.
9. **A tile's group** (the chips: *All*, then each group that has a tile)
   is the plugin's `area`, the Settings page its rows go to. A catalogue
   entry gains an optional `area`, which the listing check compares with the
   archive's manifest; absent, it is the kind's default (`sources` for a
   renderer, `system` for a service).
10. **The update after 1.10.0's install**: each of ours that is on, or has
    downloaded its software, is marked added; the rest start in *Add
    plugins*. Uploaded and catalogue plugins stay where they are.

## Also decided (George, 2026-10-30)

11. **Every optional plugin of ours is in the store**: AirPlay, Plexamp, the
    Lyrion Server, Beszel, the Beszel hub, the visualiser skins. The three
    sources the player is built around (the Lyrion client, Spotify,
    Bluetooth) stay switches on the Sources page.
12. **An update starts from what is in use**, as (10) proposes.

## Settings (ADR-0022)

None new for the user: *Keep its settings and sign-in* is a choice in the
dialog, not a setting. `_plugins_added` is the player's own record.

## Measured before it is called done

- Every board on the canvas, drawn by the built screens from mocked data:
  the phone at 360 and 412 px, the panel at 1280×800, a bar at 1850×400.
- On a test player: Add and Remove for one of ours that downloads
  (Plexamp), one that does not (AirPlay), the skins, a catalogue plugin and
  an uploaded one, with the switch on and off; an update from 1.9.1 puts
  each where (10) says.
