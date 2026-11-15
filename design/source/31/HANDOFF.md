# Handoff: internet radio — Phase 31, 2026-11-14

## Overview

Gexis plays internet radio, with Lyrion and without it. One **Radio** screen:
*Favourites*, *Popular here*, *By genre*, *By country*, *By language*,
*Search*, and *Lyrion's radio* while Lyrion is on. It reaches the panel, the
bars, the phone remote, the Home Assistant card, first use and Settings →
Sources.

Brief: `design/briefs/31-radio.md` (in this bundle). It points to ADR-0180,
which is not in the repo at the commit these designs were drawn against.

Drawn against `gcarstoiu/gexis-player` at `06123c8` (13 November 2026), on
what is built (`design/IMPLEMENTED-DIFFERENTLY.md`):

- the waiting screen as ADR-0133 has it;
- the bar's side column and rail;
- Phone Remote v3;
- the Phase 19 card;
- Phase 22's group mark;
- the library's station row and §8's category discs (`RadioGlyph.svelte`).

George picked, from `Radio 31 Options.dc.html`:

- **1b:** favourites first on the panel, as numbered tiles, browsing below;
- **2a:** the library's row with a logo tile;
- **3b:** no edit mode on the panel: Play, Up and Down on the selected
  favourite;
- **4:** search as proposed;
- **5a / 9a:** a Radio button beside Settings on the waiting screen (panel and
  bars);
- **6c:** with Lyrion off, Now Playing's Minimise comes back and returns to
  Radio;
- **7b:** the heart beside the title, the quality on a line of its own;
- **8a:** the bar's category tiles, then two sideways rows;
- **10:** the bar's Now Playing as proposed;
- **11a:** Remote · Radio · Settings on the phone;
- **12b:** favourites first on the phone;
- **13:** the phone's flows as proposed.

George also decided:

- a station row reveals on the first tap, and only Play plays (as every leaf
  row);
- with library navigation off (ADR-0149), the waiting screen leads to Radio
  as with Lyrion off, without *Lyrion's radio*;
- checking an added address plays it out loud on the player;
- when a station sends nothing, its name is the title;
- the radio's accent is `#8fc4d8`.

## About the design files

The `.dc.html` files are **design references built in HTML**, not production
code. Rebuild them in the repo's Svelte UI with its components and tokens; do
not copy the markup. Where they land, as far as the files show:

| Surface | Built today in |
|---|---|
| Radio screen, lists, favourites, search | `ui/src/screens/Library.svelte`, `LyrionSearch.svelte` |
| Category discs | `ui/src/lib/RadioGlyph.svelte` |
| Mini strip | `ui/src/screens/MiniStrip.svelte` |
| Waiting screen | `ui/src/screens/WaitingHome.svelte`, `WaitingServices.svelte` |
| Now Playing | `ui/src/screens/NowPlaying.svelte` |
| Bars | `ui/src/screens/bar/BarLibrary.svelte`, `BarNowPlaying.svelte`, `BarRail.svelte` |
| Phone remote | `ui/src/screens/remote/*` |
| First use | `ui/src/screens/FirstUsePage.svelte`, `personalise/PanelMini.svelte` |
| Settings | `ui/src/screens/Settings.svelte` |

The Home Assistant card ships in the integration
(`custom_components/gexis/frontend/gexis-player-card.js`, ADR-0163), which is
not in this repository; its regions are marked `data-gexis-card` as in Phase 19.

```
cd design && python3 -m http.server 8080
# /source/31/Radio%2031%20Panel.dc.html
# /source/31/Radio%2031%20Bars.dc.html
# /source/31/Radio%2031%20Phone.dc.html
# /source/31/Radio%2031%20Card%20Setup%20Settings.dc.html
```

The tabs at the top of each page switch the theme: Default, Bauhaus, Sage,
Velvet, Ink, Gauge. `png/` holds one picture per state, default theme only,
named by artboard id.

## Fidelity

**High** for what is new: the Radio screen, favourites, the station rows and
cards, search, the waiting screen's Radio button, Now Playing for a station,
the phone's Radio page and its flows, the card's Radio view, the first-use
and Settings rows, the copy.

Everything already built is drawn as built: the headers, the side column,
the rail, the mini strip, the player switcher, the touch area, the card's
shell, Now Playing's frame. **Where the repo and an artboard differ in
something that already exists, the repo wins.**

The following are invented:

- the stations, their logos and colours;
- the counts and addresses;
- the Lyrion server's address.

Logo colours are kept out of the theme recolour (written as `#rrggbbff`).

---

## 1. Radio on the panel (1b, P01–P07)

**Header:** as the library's, 96 tall: Back, *Radio*, and the search field
(430 × 56, radius 28) at the right. A tap on the field opens Search.

**Favourites** (1b):
- Kicker: *Favourites · 7*, mono 13 px, 0.2em, caps, at 0.6. At its right,
  **All 7 ›** (44 tall, radius 22), which opens the Favourites list.
- Up to seven tiles in one row, 44 px under the kicker, starting at x 32:
  - each tile is a 160 px logo, radius 22, in a 176 px wrapper with padding 8;
  - the wrappers sit 4 px apart;
  - the row fades out over its last 12 % when there are more than six.
- Number badge: top left, 30 tall (min-width 30), radius 10, on
  `--preset-badge-ground`, mono 15/600.
- Name: under the tile, 18/700.
- Playing: a 3 px accent ring, and *PLAYING* (mono 12) top right.
- Selected (first tap):
  - the wrapper takes `--row-selected`, radius 28, and the name turns accent;
  - Play (52, teal) sits bottom right, and the filled heart (48) bottom left.
  - The tiles only play. Reordering lives in the list (3b).

**Browse:**
- Kicker *Browse*, 278 px under the favourites kicker.
- Cards in one row, gap 12, 88 tall, radius 18. Each has a §8 disc (46) and
  its name (19/600).
- The cards: *Popular here* (pin, `--accent-bluetooth`) · *By genre* (note,
  `--accent-artist`) · *By country* (globe, `--accent-radio`) · *By language*
  (speech, `--accent-display`) · *Lyrion's radio* (Lyrion's mark, `--accent-lms`).
- *Lyrion's radio* shows only while Lyrion is on and library navigation is on.
- It opens Lyrion's tree, as today's Radio card does.

**No favourites:**
- A dashed plate (1.5 px at 0.22, radius 22), 196 tall, in place of the
  tiles.
- Inside: a favourite-tinted disc (72), *No favourites yet* (24/700), and
  the note (17, at 0.72).

**The station directory unreachable** (`DirectoryBanner`):
- A warn banner at the top of the content: 60 tall, radius 16, on
  `--directory-ground` with `--directory-line`.
- Cloud-off glyph (26), the message (17), and **Try again** (44 tall, warn
  line).
- Everything below moves down 76.
- *kept*: *Can't reach the station directory. Lists show what was seen in
  the last day.*
- *none*: *Can't reach the station directory, and nothing from the last day
  is kept. Your favourites still play.*
- With *none*, Browse sits at 0.4 and is inert; favourites play.

**Mini strip:** while something plays, the built strip (104 tall) sits at the
foot, with the radio mark (38) in `--accent-radio` and Stop. With Lyrion off it
is the way back to Now Playing (to confirm, below).

## 2. Lists, branches and search (2a, 3b, 4; P08–P20)

**Station row** (`StationRow`, 2a, the library's row):
- Padding 11 12 11 14, gap 14, radius 14.
- Logo 46, radius 13. Name 19/600.
- Meta in mono 13 at 0.62: *Germany · MP3 · 128 kb/s* (country · codec ·
  bitrate).
- Heart at the right: 48, an outline at 0.6; filled in `--favourite`.
- Playing: the meta becomes the visualiser glyph and *Playing · AAC · 96 kb/s*
  in the accent.
- First tap: the row takes `--row-selected` and its name turns accent, with
  Play (44, radius 12, `--row-act-ground` / `--row-act-line`).
- The heart acts at once, selected or not.

**Station logo** (`StationLogo`):
- Fills its tile.
- A logo smaller than `--station-logo-native-max` (64 px) is drawn at its own
  size, centred on `--station-logo-plate`. It is never enlarged.
- No logo: the radio mark on `--station-fallback-ground` with
  `--station-fallback-line`.

**Favourites list** (3b; P08–P10):
- Header *Favourites*, crumb *Radio*, with Home.
- Kicker *7 stations · in your order*; at its right, *Select one to play or
  move it*.
- Each row starts with its number (mono 13, 22 wide, right-aligned).
- Selected: Play, **Move up** and **Move down** (44 each). Move up is at 0.4
  on the first row, and Move down on the last.
- Removed (the heart tapped):
  - the name at `--row-removed-ink`, struck through;
  - **Undo** (44 tall, teal) in place of the heart.
- Twenty favourites: a 4 px scrollbar, 14 from the right.

**Branches** (`BranchRow`; P12–P14):
- Rows 60 tall, in two columns (gap 2 24).
- Name 19/600, count in mono 14 with a thousands separator, chevron 20.
- A tap navigates; there is nothing to select.
- *By genre*: kicker *18 genres · stations in each*.
- *By country*:
  - *Your country* first, then *Every country · A to Z*;
  - a jump rail (28 wide, 14 from the right) of # and A–Z in mono 13/600;
  - letters with no country sit at 0.28.
- *By language*: kicker *N languages, most stations first*, sorted by count.

**A long list** (P15–P17):
- A count kicker, *1,240 stations*.
- Loading:
  - *LOADING…* in mono 13, 0.2em;
  - then skeleton rows: a 46 tile at `--skeleton-tile`, and bars 14 and 10
    tall at `--skeleton-line-1` and `-2`.
- The end (`ListEnd`): *End of Jazz · 1,240 stations*, mono 14, 0.12em, caps,
  between two 1 px rules.

**Search** (4; P18–P20):
- The header becomes Back and a field 64 tall that fills the width.
- Focused: an accent line at 0.55 and a 2 px accent caret.
- Typing, empty:
  - a grey disc (72);
  - *Type a station's name* (28/700);
  - *With a keyboard, or on your phone. Results come as you type.* (19).
- Results:
  - kicker *Stations · 23*, with *Type with a keyboard, or on your phone* at
    its right;
  - station rows, with the matched letters in the accent.
- Nothing found:
  - *No station is called "zzq"* (30/700);
  - *Search looks at station names. Try fewer letters, or look under By
    genre.*

## 3. The waiting screen (5a, 9a; P21–P22, B14–B15, B34)

- **Radio** (`RadioCornerButton`) joins the corner, left of Settings, 14 apart:
  - 148 × 64, radius 18, on `rgba(16,26,33,0.6)` with a 0.14 line;
  - the radio mark (28) in `--accent-radio`, and *Radio* (20/700).
- Panel: the corner sits 26 from the top and right. Bars: 30.
- Nothing else on the screen changes.
- It shows whenever the waiting screen does:
  - with Lyrion off;
  - with library navigation off (ADR-0149).
- With library navigation off, Lyrion's mark stands among the sources:
  - 96 disc on `--accent-lms` at 0.14, line 0.45, one ring;
  - *Lyrion* · *STARTS ON PLAY*.
  - Radio opens without *Lyrion's radio*.

## 4. Now Playing for a station (6c, 7b, 10; P23–P31, B16–B21, B33)

**What is the same on every surface:**
- A 3 px rule across the top: `--radio-rule`.
- The radio mark, top right, in `--accent-radio`.
- **Lines:**
  - title and artist when the station sends *Artist - Title*;
  - the whole line as the title when it cannot be split;
  - the station's name as the title when nothing is sent.
  - The station's name goes on the album line.
- **Art:** the track's cover, else the station's logo on a plate, else the
  radio mark on the radio tint.
- **Quality line** (7b), on its own line: *FLAC · 1411 kb/s · Germany*
  (codec · bitrate · country).
- **Controls:**
  - Stop, not Pause.
  - Previous and Next step through the favourites. They sit at 0.4 and are
    inert for a station that is not one.
  - No seek: the inert rule, as Bluetooth's.
- **Status:**
  - *Reconnecting · try 2 of 3*: spinner, in warn; the play control shows a
    spinner.
  - *The station is not answering* / *Tried three times. Play tries again.*:
    the play control shows Play.
  - In both, the art sits at 0.45.
- **In a group:** Phase 22's mark, *with Kitchen, Study*, midway between the
  progress rule and the controls.
- **Lyrion off** (6c): the Minimise chevron stays and returns to Radio. Home
  is replaced by Settings, as built.

**Panel (1280 × 800):**
- Art 500, radius 20, at 56, 44.
- Tabs as built. *RELEASE* sits at 0.30 for a station; with nothing sent,
  *LYRICS*, *ARTIST* and *RELEASE* do.
- Title 54/700 from x 604, up to two lines, stopping 140 from the right.
- Heart 68 on the fill, 56 from the right and 124 from the top (7b).
- Second line: the artist (35, `--accent-artist`) and the station (30, at
  0.6).
- Quality line: mono 20, 0.04em, at 0.6, then a 1 px rule.
- Status in the lyrics area, 40 under that rule: 30/700, with its second part
  in mono 20 or 20 at 0.72.
- Inert rule at y 597.
- Group chip: 44 tall, centred at y 616, group glyph in `--accent-lms`,
  16/600.
- Controls row at y 668:
  - left: Home or Settings (64), then Visualiser (60);
  - centre: Previous (68), Stop (92), Next (68);
  - right: Volume (60).

**Bars (1850 × 400 and 1280 × 400):**
- Art 400 square at the left.
- Chevron (60) at 24, 24: *Minimise*, or with Lyrion off *Back to Radio*.
- Title 44/700 from x 436.
- Heart 60, 104 from the right; the radio mark 40 at the far right.
- Second line at y 94 (36 / 32).
- Quality line: mono 22 at y 150, or y 100 when there are no lines.
- Status 40 under the quality line: 24/700 and 18.
- Inert rule (10 tall) at y 236.
  - In a group, the rule moves up to y 204, and the group chip (36 tall)
    centres at y 224.
- Controls at y 276: 68 · 92 · 68. Lyrics (60) at the right.

## 5. The bars (8a; B01–B13, B31–B32)

- Side column 220 wide, as built: Back, Home, the title (26/700), and the
  crumb in mono 14.
- Rail 124 wide, as built.
  - With nothing playing, the rail shows the radio mark alone, at 0.5.
- **Radio** (`CategoryTile`):
  - tiles 196 × 300, radius 22, 20 apart, from x 252, y 50;
  - each tile on its tint at 0.13 with a 0.32 line;
  - a §8 disc (54), then the name (26/700, or 23 when longer than 11
    characters), and the meta (mono 14, in the tint at 0.9).
  - The tiles: *Favourites* (*7 stations*), *Popular here* (*Germany*), *By
    genre*, *By country*, *By language*, *Search*, *Lyrion's radio*.
  - A fade covers the last 110 px before the rail.
- **The directory unreachable:** the banner sits at the foot of the side
  column.
  - Text (15): *Directory unreachable. Lists from the last day.* /
    *Directory unreachable. Favourites still play.*
  - **Try again** (40 tall).
  - With nothing kept, the five directory tiles sit at 0.4.
- **Lists** (`StationCard`):
  - two rows of 430 × 120 cards, radius 20, flowing down then across, gap 16;
  - logo 72 (radius 16), name 21/700, meta in mono 14, heart 52;
  - selected adds Play (48).
- **Favourites:**
  - cards 440 wide, with the number (mono 14, 18 wide) and a 64 logo;
  - selected: Play, **Earlier**, **Later** (44 each) and the heart (48).
    Earlier sits at 0.4 on the first card.
  - Removed: the struck name, and **Undo** in place of the heart.
  - None: a dashed plate, 900 × 240.
- **Loading:** skeleton cards (430 × 120, a 72 tile, bars 16 and 11 tall).
- **Branches:** cards 330 × 80, radius 18, in columns of three. Name 21/700,
  count in mono 14.
- **Search:**
  - a field 760 × 60 at the top, with *23 stations · type with a keyboard, or
    on your phone*;
  - the results in two rows from y 116.
  - Nothing found: a grey disc (68), 28/700, and 19.
- 7.9" (1280 × 400): the same pieces, with the waiting screen's sources from
  x 470 instead of 640.

## 6. The phone (11a, 12b, 13; H01–H24)

**The top** (as built) gains a third segment: **Remote · Radio · Settings**
(56 × 46 each). Radio selected takes `--accent-radio` at 0.2 with the glyph in
`--accent-radio`; the others keep the LMS accent.

**Radio page** (12b):
- Search field: 50 tall, radius 25, at y 76.
- Category chips at y 140, scrolling sideways (`CategoryChip`):
  - 44 tall, radius 22, a 32 disc, 15/600;
  - *Popular here*, *By genre*, *By country*, *By language*, *Lyrion's
    radio*.
- Kicker *Favourites · 7* at y 204, with **Add by address** (36 tall, link
  glyph) and **Edit** (36) at its right.
- Rows from y 244:
  - number in mono 12, 14 wide; logo 44, radius 12;
  - name 17/600, meta in mono 12; heart 44;
  - selected adds Play (40, teal).
- The mini player (62 tall, at y 772) while something plays.
- The directory unreachable: a banner at y 140 (13 px text, **Retry** 34
  tall). The chips move down 66.
- No favourites: a dashed plate with a 56 disc, *No favourites yet* (19/700)
  and the note (15).
- Sub-pages (*Popular here*, *By genre*, a genre): Back (44), the title
  (20/800) and the crumb (mono 12). Branch rows are 54 tall.
- Widths: drawn at 390, 360 (H23) and 430 (H24).

**Favourites, Edit** (H11–H12):
- *Drag to reorder*, with **Done** (teal) at the top right.
- Each row: a grip (22) at the left, and remove (40, `--remove-ground` /
  `--remove-line`, a minus) at the right.
- The row being dragged:
  - lifts 10 px and scales to 1.02;
  - sits on the panel ground, with a shadow and a 0.45 accent ring.
- Removed: a toast, 56 tall, 96 from the bottom: *Removed **Nordlicht
  Folk*** with **Undo**.

**Add by address** (13; `AddStationSheet`, H13–H16):
- A bottom sheet: grabber 44 × 5, *Add a station* (24/800), and the note
  (15).
- Fields (50 tall, radius 14):
  - *Address*, in mono 14; focused, a 0.6 accent line;
  - *Name*, 17.
- Buttons, 52 tall: **Cancel** and **Check and add** (teal at 0.9, dark
  text).
- Checking:
  - *Checking · playing it on Living Room*, with a spinner, on the accent at
    0.1;
  - **Check and add** at 0.4.
  - The player plays it out loud (George).
- Did not play:
  - the Address field gets a warn line at 0.8;
  - an alert: *It did not play* / *Nothing came from that address that the
    player can play. Check it, or try again.*;
  - **Try again**.
- Added:
  - the list, with the station last and its meta *Added by address · MP3 ·
    128 kb/s*;
  - a toast with a check: ***Kiez Jazz Nacht** played, and is in your
    favourites*.

**Remote:**
- With a screen (H17–H19): as built.
  - Previous and Next sit at 0.4 when the station is not a favourite.
  - The heart (44) sits at the right of the transport.
  - In a group: *with Kitchen, Study* (13/600) with the group glyph, under the
    transport.
- With no screen (H20–H22): as built, with the heart (52) at the left of the
  transport.
  - Status line at y 578 (15/700, warn): *Reconnecting · try 2 of 3*, or *The
    station is not answering*.
  - The art sits at 0.45.

## 7. The Home Assistant card (C01–C06)

The card follows Home Assistant's theme and is never recoloured by Gexis
themes.

- **View switch** (`data-gexis-card="views"`), under the switcher:
  - *Now playing · Radio*, 40 tall (36 compact), as a segmented pill;
  - selected: `--accent-lms` at 0.18 with accent text, 14/600, and a 16
    glyph.
- **Radio view** (`favourites`, `favourite`):
  - label *Favourites · 7* in mono 12, 0.16em;
  - rows: min-height 56, logo 40 (radius 10), name 15/500, meta 12.
  - A tap plays.
  - The one playing: accent at 0.12, its name in the accent, *Playing* with
    the visualiser glyph.
- Sizes:
  - Phone 390, full (C01).
  - Dashboard column 300 (C03).
  - Wall tablet 760: two columns, gap 2 12 (C04).
  - Compact (C02): logo tiles 56, in 64 px columns, sideways.
    - The name is 11 px.
    - The one playing has a 2 px accent ring.
    - The row fades over its last 15 %.
- Under the list: *Every other station is in Home Assistant's media browser.*
  (13, at 0.6).
- **None yet** (`favourites-empty`):
  - a dashed plate with the heart and *No favourites yet* (16/600);
  - *Add them with the heart on the player's screen or its phone remote.*
- **Now playing, a station** (C06): as Phase 19.
  - Previous and Next sit at 0.38 when the station is not a favourite.
  - The heart (44) sits at the right of the transport row.

## 8. First use (F01–F03)

- *How will you listen?* (phone and panel): **Internet radio** joins every
  preset's chips, on by default (brief §7):
  - *My music + streaming*: Lyrion, Spotify, AirPlay, Bluetooth, Internet
    radio.
  - *Plex + streaming*: Plexamp, Spotify, AirPlay, Bluetooth, Internet radio.
  - *Streaming only*: Spotify, AirPlay, Bluetooth, Internet radio.
  - *My own mix*: all six.
  - Its chip carries the radio tint (0.14 ground, 0.45 line). The other chips
    are as built.
- *My own mix* (F02):
  - a **Radio** group after Streaming, with one row: *Internet radio* ·
    *Stations from a public directory. Works without Lyrion.*;
  - the row's switch is on.
- The panel's preview (F03): `PanelMini` shows the sources in turn, 3 s each
  (`ui/src/screens/personalise/PanelMini.svelte`). Internet radio becomes a
  fifth step, after Bluetooth:
  - a 78 disc on the radio tint (0.18, 2 px line at 0.6), with the mark (38);
  - *Internet radio* (16/700).
  - The 12 s cycle becomes 15 s.

## 9. Settings → Sources (S01–S04)

- **Internet radio** (`SettingsRadioSection`) comes after Bluetooth.
- Heading: *INTERNET RADIO* (mono 13, 0.2em, at 0.72), a rule, and *✓ Ready*
  in `--accent-lms`.
- **On**: *Stations from a public directory, and your own favourites. Works
  with Lyrion off.* A switch, 58 × 30.
- **Popular here** › *Germany*: *The country whose stations Popular here
  lists. Set from the time zone at setup.*
- **The country** (`CountrySheet`):
  - Panel: a dialog 760 wide, 60 from the top, radius 22, padding 26.
  - Phone: a bottom sheet from y 170.
  - Contents:
    - *Popular here* (25/700), with **Done**;
    - *Whose stations Popular here lists.*;
    - a *Search countries* field (52 tall);
    - radio rows (58 tall; 52 on the phone).
  - The current country:
    - shows *From your time zone* in mono 13, in the accent;
    - its row is on the accent at 0.12.
  - Counts in mono 13: *4,210 stations*.

## State, added to what is built

What the screens read, as drawn. The names are suggestions.

- `radio.enabled`: Settings' switch; on by default at first use.
- `radio.popularCountry`: from the time zone at setup; changed in Settings.
- `radio.directory`: `ok` | `kept` (the last day's lists) | `none`.
- `radio.favourites`: an ordered list of stations. Each has:
  - `id`, `name`, `logo` (and its size), `country`, `codec`, `bitrate`;
  - `address` for one added by address.
- Now Playing, for a station:
  - `lines`: `split` | `whole` | `none`;
  - `art`: `cover` | `logo` | `mark`;
  - `favourite`;
  - `status`: `playing` | `reconnecting` (try n of 3) | `notAnswering` |
    `stopped`.
- Add by address: `form` | `checking` | `failed` | `added`.

## Design tokens

`design/source/31/tokens-radio-31.css` holds the default and one block per
theme (`:root[data-theme="<id>"]`), made by the Phase 28 recolour, so the
values match the themed artboards.

- **New:**
  - accents: `--accent-radio`, `--favourite`, `--radio-rule`,
    `--radio-glyph-ground`, `--radio-glyph-line`;
  - logos: `--station-logo-row(-radius)`, `--station-logo-card-bar(-radius)`,
    `--station-logo-phone(-radius)`, `--station-logo-ha(-radius)`,
    `--station-logo-native-max`, `--station-logo-plate(-line)`,
    `--station-fallback-ground`, `--station-fallback-line`;
  - presets: `--preset-size`, `--preset-radius`, `--preset-badge-ground`;
  - rows: `--row-selected`, `--row-act-ground`, `--row-act-line`,
    `--row-removed-ink`, `--remove-ground`, `--remove-line`;
  - states: `--directory-ground`, `--directory-line`,
    `--favourites-empty-line`, `--skeleton-tile`, `--skeleton-line-1`,
    `--skeleton-line-2`;
  - `--radio-corner-button-width`.
- `--accent-radio` and `--favourite` per theme:

| Theme | `--accent-radio` | `--favourite` |
|---|---|---|
| Default | `#8fc4d8` | `#e8a0b4` |
| Bauhaus | `#0d6475` | `#a8205f` |
| Sage | `#1b5f6b` | `#93284f` |
| Velvet | `#8ccfc7` | `#e7a3d4` |
| Ink | `#62dbd6` | `#f2a7e8` |
| Gauge | `#8fb4ff` | `#ff6f7d` |

  Each is at least 5.9:1 as text on its theme's base and panel (WCAG
  contrast ratio, computed with the generator's `theme.py`).

Everything else is from `design/tokens.css` and the Phase 28 theme files.

## Open, for George

- The nine decisions in `design/source/31/README.md` (*Decided while drawing,
  to confirm*), and the new words listed there.
- What plays after an address passes its check: does the station keep
  playing, or does the earlier music come back?
- Three reconnect tries (*try 2 of 3*, *Tried three times*) are drawn, not
  decided.
- *By language*'s tint:
  - drawn in `--accent-display`, so that it differs from *Popular here*'s
    `--accent-bluetooth`;
  - `RadioGlyph.svelte` gives Lyrion's *By Language* `--accent-bluetooth`.
- Whether favourites belong to a player or to the house. They are drawn under
  the selected player (*Living Room*); ADR-0180 may say.

## Files

```
HANDOFF.md                                          this file (also in design/source/31/)
design/briefs/31-radio.md                           the brief
design/source/31/README.md                          picks, components, decisions to confirm, new words
design/source/31/Radio 31 Panel.dc.html             P01–P31, the 10.1" panel, theme tabs
design/source/31/Radio 31 Bars.dc.html              B01–B21 on the 11.9", B31–B34 on the 7.9"
design/source/31/Radio 31 Phone.dc.html             H01–H24, the phone remote at 390, 360, 430
design/source/31/Radio 31 Card Setup Settings.dc.html  C01–C06 card, F01–F03 first use, S01–S04 Settings
design/source/31/Radio 31 Options.dc.html           turn 1: the options George picked from (default theme)
design/source/31/tokens-radio-31.css                new tokens, six themes
design/source/31/art/pd-monet.jpg                   the sample cover the artboards use
design/source/31/png/*.png                          one per state, default theme
```

The pages also load, from the repo:

- `../30/support.js`;
- `../21/gexis-mark.svg`, `../icon-spotify.png`, `../icon-lyrion.svg`;
- `../19/wallpapers/calm/c148381086.webp`, `../28/<id>-bluetooth.svg`;
- `../../marks/bluetooth.svg`, `../../fonts/*`.

The theme monos load from Google Fonts.

Two zips, each under 30 MB. Unpack both at the repo root; their `design/`
goes over the repo's `design/`.

- **Part 1:** this file, the brief, every page, the tokens, the README, the
  cover, and the PNGs for the panel, card, first use and Settings (P, C, F, S).
- **Part 2:** the PNGs for the bars and the phone (B, H).
