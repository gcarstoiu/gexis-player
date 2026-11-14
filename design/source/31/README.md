# Phase 31: internet radio

Brief: `design/briefs/31-radio.md` (ADR-0180), drawn on what is built
(`design/IMPLEMENTED-DIFFERENTLY.md`): the waiting screen as ADR-0133 has it,
the bar's side column and rail, Phone Remote v3, the Phase 19 card, Phase
22's group mark.

Open the pages over HTTP from `design/` (`cd design && python3 -m http.server
8080`, then `/source/31/Radio%2031%20Panel.dc.html` and the others); in Claude
Design they are also at the project's root (the Pages menu). Each has **theme
tabs** at the top: Default, Bauhaus, Sage, Velvet, Ink, Gauge. The turn-1
options are in `Radio 31 Options.dc.html`. For building it, read `HANDOFF.md`.

## Picks (George)

**1b** favourites first, as numbered tiles, browsing below · **2a** the
library's row with a logo tile · **3b** no edit mode on the panel: Play, Up and
Down on the selected favourite · **4** search as proposed · **5a / 9a** a
Radio button beside Settings on the waiting screen · **6c** with Lyrion off,
Minimise comes back and returns to Radio · **7b** the heart beside the title,
the quality on its own line · **8a** the bar's category tiles, then two
sideways rows · **10** the bar's Now Playing as proposed · **11a** Remote ·
Radio · Settings on the phone · **12b** favourites first on the phone · **13**
the phone's flows as proposed.

Also decided by George: a station row reveals on the first tap and only Play
plays (as every leaf row); with Navigation Off the waiting screen leads to
Radio as with Lyrion off, without Lyrion's entry; the check of an added address
plays it out loud on the player; with nothing sent the station's name is the
title; the radio's accent is `#8fc4d8`.

## Files

| File | What it is |
|---|---|
| `Radio 31 Panel.dc.html` | P01–P31: the 10.1" panel at 1280 × 800. |
| `Radio 31 Bars.dc.html` | B01–B21 on the 11.9" bar (1850 × 400, drawn at 0.8), B31–B34 on the 7.9" (1280 × 400). |
| `Radio 31 Phone.dc.html` | H01–H24: the phone remote at 390 × 844, and the Radio page at 360 and 430. |
| `Radio 31 Card Setup Settings.dc.html` | C01–C06 the Home Assistant card, F01–F03 first use, S01–S04 Settings. |
| `Radio 31 Options.dc.html` | Turn 1: the options George picked from, default theme. |
| `HANDOFF.md` | The build spec for Claude Code: sizes, states, tokens, what is open. |
| `tokens-radio-31.css` | The new tokens, default and one block per theme. |
| `art/pd-monet.jpg` | The sample cover the artboards use. |
| `png/` | One picture per state, default theme, at real size, named by artboard id. |

Each page holds every theme: the default markup and one copy per theme made by
Phase 28's recolour (colour literals by family, the cover veil, weave angle,
mono, radii), with two families added for this phase (the radio accent and
the favourite). A light theme lightens the waiting screen's photo instead of
darkening it, so its dark type reads. The card is never recoloured: it
follows Home Assistant's theme.

Stations, logos, counts, addresses and the Lyrion server's address are
invented. Logo colours are the stations' own and are kept out of the recolour.

## Component boundaries

Marked in the markup with `data-component` (the card with `data-gexis-card`).

| Component | Where | Props / states | Notes |
|---|---|---|---|
| `StationRow` | panel lists, phone lists | `station`, `state` (none / selected / playing), `favourite`, `num`, `actions` | First tap selects (teal) and shows Play; in Favourites also Up and Down (3b). The heart acts at once. Removed: struck name, Undo in place of the heart. |
| `StationCard` | bar lists | as `StationRow` | 430 × 120 (440 in Favourites, with the number). Selected favourite: Play, Earlier, Later. |
| `PresetTile` | panel Radio screen | `station`, `num`, `state` | 160 px logo, number badge, name under it. Playing: accent ring and *PLAYING*. Selected: Play and the heart over the tile. |
| `StationLogo` | everywhere | `station.logo` (and its size), `size` | Fills its tile. A logo smaller than `--station-logo-native-max` (64 px) is drawn at its own size on the plate, never enlarged. None: the radio mark on the radio tint. |
| `HeartButton` | rows, cards, tiles, Now Playing | `favourite` | Outline in the second ink; filled in `--favourite`. |
| `CategoryCard` / `CategoryTile` / `CategoryChip` | panel / bar / phone | `category` | §8's tinted disc: Favourites heart, Popular here pin, By genre note, By country globe, By language speech, Search magnifier, Lyrion's radio Lyrion's mark. |
| `BranchRow` | genre, country, language lists | `name`, `count` | A tap navigates, nothing else. Countries: *Your country* first, then A to Z with the jump rail. |
| `SearchField` | panel header, bar, phone | `text`, `focused` | Results as you type; matched letters in the accent. |
| `DirectoryBanner` | Radio screen | `kind`: `kept` / `none` | Warn ground; *Try again*. With nothing kept, browsing is dimmed and inert; favourites still play. On the bar it sits in the side column. |
| `FavouritesEmpty` | every surface | | Dashed plate: *No favourites yet* and how to add one. |
| `ListEnd`, loading rows | lists | `text` | *End of Jazz · 1,240 stations*; *LOADING…* then skeleton rows. |
| `RadioCornerButton` | waiting screen | | 148 × 64, beside Settings, the radio mark and *Radio*. |
| Now Playing, station | panel, bar, phone | `lines`, `art`, `favourite`, `status` | Lines: title and artist, the whole line as title, or the station's name as title. Art: cover, else logo, else the radio mark. Quality line: codec · bitrate · country. Stop, not Pause. Prev / Next for favourites, dimmed at 0.4 otherwise. No seek: the inert rule. Status: *Reconnecting · try 2 of 3*, *The station is not answering* (Play tries again). |
| `MiniStrip` | panel Radio and lists, Lyrion off | Phase 19's strip | Shown only while something plays; a tap opens Now Playing. |
| `Toast` | phone | `text`, `action` | *Removed · Undo*; *… played, and is in your favourites*. |
| `GroupMark` | Now Playing | Phase 22, unchanged | Bar: the progress row moves up so the mark sits midway. |
| `AddStationSheet` | phone | `state`: form / checking / failed | Then the list with a toast. |
| `SettingsRadioSection`, `CountrySheet` | Settings | | *On*, and *Popular here* with the country. |
| card `views`, `favourites`, `favourite`, `favourites-empty` | Home Assistant card | | A *Now playing · Radio* switch under the player. A tap on a favourite plays it; the one playing has the accent ground and *Playing*. Compact: logo tiles sideways. Tablet: two columns. |

## Decided while drawing, to confirm

1. **Lyrion off, Radio while something plays shows the mini strip**: it is the
   way back to Now Playing from Radio (ADR-0079 took the strip away because its
   job was returning from the library). Back returns to where Radio was opened.
2. **The radio mark is a broadcast mark**, a dot between two pairs of arcs, in
   `--accent-radio`, also the fallback for a station with no logo. §8's Arcs fan
   reads as Wi-Fi at mark size.
3. **The panel's favourites row has *All N***, which opens the list where 3b's
   Up and Down live. The tiles themselves only play.
4. **On the bar the move buttons read Earlier and Later**: the cards run down
   then across, so up and down are not where they move.
5. **Popular here starts as the country of the time zone chosen at setup**;
   Settings → Sources → Internet radio changes it.
6. **Internet radio's section in Settings → Sources comes after Bluetooth**,
   with *Ready* beside its heading as Lyrion's has.
7. **First use**: Internet radio in every preset (as AirPlay, ADR-0167), its own
   *Radio* group in *My own mix*; on the panel the preview's loop gains a fifth
   source.
8. **The card's note** *Every other station is in Home Assistant's media
   browser.* points to where browsing lives.
9. **The phone's *Add by address*** sits beside *Edit* over the favourites.

## New words (to confirm)

*Radio* · *Favourites · 7* · *All 7* · *Browse* · *Popular here* · *By genre* ·
*By country* · *By language* · *Lyrion's radio* · *Search stations* · *Type a
station's name* · *With a keyboard, or on your phone. Results come as you
type.* · *No station is called “zzq”* · *Search looks at station names. Try
fewer letters, or look under By genre.* · *No favourites yet* · *Tap the heart
on any station to keep it here, in your own order. Next and Previous then step
through them, like a radio's presets.* · *Select one to play or move it* ·
*Can't reach the station directory. Lists show what was seen in the last day.*
· *Can't reach the station directory, and nothing from the last day is kept.
Your favourites still play.* · *Try again* · *Your country* · *Every country ·
A to Z* · *LOADING…* · *End of Jazz · 1,240 stations* · *Reconnecting · try 2
of 3* · *The station is not answering* · *Tried three times. Play tries
again.* · *Add a station* · *For a station the directory does not have. Living
Room plays it for a moment first, to check it works.* · *Check and add* ·
*Checking · playing it on Living Room* · *It did not play* · *Nothing came from
that address that the player can play. Check it, or try again.* · *Kiez Jazz
Nacht played, and is in your favourites* · *Now playing · Radio* · *Every other
station is in Home Assistant's media browser.* · *Add them with the heart on the
player's screen or its phone remote.* · Settings: *Stations from a public
directory, and your own favourites. Works with Lyrion off.* · *The country whose
stations Popular here lists. Set from the time zone at setup.* · *Whose
stations Popular here lists.* · *From your time zone*.

## Tokens

`tokens-radio-31.css`: `--accent-radio` and `--favourite` with a value per
theme (each a hue no other accent of that theme holds, 4.5:1 or more as text on
its base and panel), the logo sizes and plate, the preset tile, the selected
row and its actions, remove, the directory banner, the empty plate, the
skeleton, the waiting screen's Radio button.

| Theme | `--accent-radio` | `--favourite` |
|---|---|---|
| Default | `#8fc4d8` | `#e8a0b4` |
| Bauhaus | `#0d6475` | `#a8205f` |
| Sage | `#1b5f6b` | `#93284f` |
| Velvet | `#8ccfc7` | `#e7a3d4` |
| Ink | `#62dbd6` | `#f2a7e8` |
| Gauge | `#8fb4ff` | `#ff6f7d` |

## Not drawn

- The 7" and 13.3" panels (the 10.1" only, as the brief's states are drawn).
- The D-pad focus on the new controls (Phase 19's rules apply as built).
- What plays after an address has passed its check: the toast says it played;
  whether it keeps playing or the earlier music returns is open.
