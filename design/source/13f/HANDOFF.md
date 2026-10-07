# Handoff: Phase 13f — Lyrion's own menus on the panel

For Claude Code, working in `gcarstoiu/gexis-player`. Brief: `design/briefs/13f-lyrion-menus.md` (main, 2026-10-06). Background: ADR-0118, Findings 110 and 111, ADR-0121 (phone as keyboard).

## Overview

Phase 13f puts Lyrion's own tree on the panel behind the *Extended navigation* setting (off by default): My Music's 21 library views, Favourites, and the apps (Qobuz, Spotty, YouTube, Radio Paradise, Sounds & Effects, TIDAL). The tree is already built and working. This package replaces the first-pass look with the designed one, for the **Standard family** (1280 logical wide, 711–853 tall) and the **Bar family** (logical height 400; 1280 × 400, and 1480 × 320 laid out at 1850 × 400 and shown at 0.8).

One rule carries every level: **what an entry opens decides its shape.**

- **Branches** (folder, category, genre, year, app entry) are a CSS glyph in a tinted disc, as Radio's are (`screens.md` §8). A tap navigates. They have no actions.
- **Containers with covers** (albums, playlists) are always a cover grid.
- **Leaves** (tracks, stations, files) are rows. The first tap selects the row and reveals Play · Play next · Add; the second tap plays.
- **Search entries** become a text field. Text is typed on the phone (ADR-0121).
- **Text items** are inert lines, or are folded into a page (see the app album page).

## About the design files

The files in `design/source/13f/` are **design references made in HTML**, not production code. Recreate them in the panel's own stack (`ui/src`, Svelte), using its existing patterns and `design/tokens.css`. Do not ship the `.dc.html` files.

Open `design/source/13f/Lyrion Menus.dc.html` over a local server (`python3 -m http.server` from `design/source/13f/`). It is the board: all 11 brief items, Standard and Bar side by side, plus the decision notes. Each screen is also reachable on its own:

- `Lyrion Standard.dc.html` — prop `screen` (26 values, listed below).
- `Lyrion Bar.dc.html` — props `screen` (18 values) and `w` (1280 or 1850).
- `glyphs.js` — the 46 glyphs (ten from Radio unchanged, 36 new), each drawn in CSS in a 26 px box. This is the source of truth for glyph geometry: port it as a Svelte component.
- `lyrion-data.js` — the shape and tint of every My Music entry, the **keyword table** that picks shapes for any app level, and the sample data.

## Fidelity

**High fidelity.** Colours, type, sizes, radii and spacing are final, and every value is in `tokens.css` terms. Match them exactly. Values below are CSS px at logical size.

## Keep (from the brief, unchanged)

- The design system as it is: `tokens.css`, Nunito Sans and IBM Plex Mono, the blurred-weave backdrop, the source accents.
- Navigation (`screens.md`, *Navigation*). Back is always in the header. Home sits beside it below the first level. The mini strip leads back to Now Playing.
- Row actions (`screens.md`, *Row actions*). There is no long press anywhere. Leaf rows reveal their actions on the first tap and play on the second. Branch rows have no actions.
- No on-screen keyboard. The panel shows a field and the phone types into it.
- Pi 4 budget: transform and opacity only, one region animating at a time, no cross-fades between screens. Press feedback is `scale(0.95)` on controls and `scale(0.975)` on Home cards.
- Out of scope, unchanged: Browse, Artists, Playlists, the album and artist pages, Radio, Settings, and context menus.

---

## Shared parts

### Frame — Standard
- Ground `--bg-base`. Backdrop: `repeating-linear-gradient(38deg, #3f5a6d 0 48px, #2e4453 48px 96px)`, `blur(70px)`, `scale(1.14)`, inset −90. Over it the now-playing artwork, `blur(72px) saturate(1.7)`, inset −120, then `radial-gradient(130% 105% at 20% 42%, rgba(20,33,42,.62), rgba(13,21,28,.93))`.
- **Header** 96 px, padding 0 40, gap 20, hairline below at `rgba(233,238,242,.09)`.
  - Back: 60 px circle, `--ink-fill`.
  - Home (2 × 2 squares glyph): 60 px, shown only below the first level.
  - Title: 26/700, letter-spacing −0.01em, never truncated.
  - Crumb: mono 15, letter-spacing 0.08em, `--ink-quiet`, truncates with an ellipsis.
  - App screens put the app's logo (36 px, radius 9) before the title.
- **Content** flexes. Padding 22 40 24 unless noted.
- **Mini strip** 104 px, exactly as `screens.md` §2: hairline progress line along the top, 64 px art, title 20/700, artist 16 in coral, the 38 px source mark, elapsed time in mono 16, 56 px volume button, 64 px play/pause in `--play-fill`.
- **Height:** the header and strip are fixed and the content absorbs 711–853. Lists show more or fewer rows. My Music's cards stretch between 54 and 76 px.

### Frame — Bar (logical 400 tall)
- Ground: `#37505f` under the same radial gradient.
- **Head column** 220 px on the left, padding 28 24 26, hairline on its right edge. It holds Back and Home (60 px each, gap 10), the title (26/700) and the crumb (mono 15, 0.06em, `--ink-quiet`). Track lists also put Play all (56 px, flex) and Shuffle (56 × 56) at its foot.
- **Mini-player rail** 124 px on the right, the 13b 5c rail: 84 px art, level bars, 64 px play/pause.
- Content fills the space between: 936 px at 1280 wide, 1506 px at 1850.
- **Letter-pair strip** (Genres, All Artists, Albums) at the foot of the content:
  - 13 tiles, A–B … Y–Z, flex 1 each, min-width 44, height 52, radius 12, gap 6, padding 0 28 24.
  - Font: mono 16/600, letter-spacing 0.06em.
  - Resting tile: ground `rgba(233,238,242,.05)`, border `rgba(233,238,242,.1)`, ink `rgba(233,238,242,.78)`.
  - Current tile: ground at the list's tint 18%, border at the tint 50%, ink in the tint.
  - Copied from 13b `Bar States.dc.html`. **See note 7: check that it reads as buttons.**

### Disc (branch marker)
- 46 px on rows, 54 px on cards, 42 px on bars, 92 px on state screens.
- Ground: the tint at 14%. Border: 1 px of the tint at 30%. Glyph: the tint at full strength.
- This is §8's disc, unchanged.

### Rows
- **Standard:**
  - Height 60 px for one line, 64 px for two. Radius 14, padding 0 12 0 8, gap 16.
  - Label 20/600, truncates. Subtitle 15 in `rgba(233,238,242,.62)`. Meta in mono 16 at the same ink, right-aligned.
  - Leads, any one of: disc 46, cover thumb 46 (radius 9), initials circle 46, or rank number (mono 15, 34 px wide, right-aligned).
  - Initials circle: `#9fb4e8` at 14% / 30%, text 16/700 `#9fb4e8`.
- **Bar:** height 52 (60 for two lines), radius 12, label 19/600, leads at 42 px.
- **Selected leaf row:**
  - Ground `rgba(126,214,188,.16)`, label `#7ed6bc`. The meta hides and the three actions take its place.
  - Each action: height 48 (46 on bars), radius 14, padding 0 18, gap 8 between them.
  - **Play**: mint 14% ground with a 36% border, 12 px mint triangle, "Play".
  - **Play next**: `--ink-fill`-level ground (`rgba(233,238,242,.06)`) with a 0.14 border, a triangle plus bar, "Play next".
  - **Add**: same ground as Play next, a 14 px plus, "Add".
  - All labels 17/700, no wrapping. On the bar album page they shorten to a ▶ square, "Next" and "Add".
- **Section header** inside a list: mono 14/700, letter-spacing 0.18em, in the group's tint, then a flex hairline at `rgba(233,238,242,.1)`, then a mono 12 count. 14 px above, 8 px below.
- **Play all bar** (top of track and folder lists): Play all is 56 px tall, radius 15, padding 0 26, mint 14% with a 36% border. Shuffle is 62 × 56. Then a flex hairline and a mono 13 uppercase count.
- **Letter rail** (Standard, alphabetical lists only): 58 px wide, `#` and A–Z in mono 13/700. Letters the list has are at 0.72, letters it lacks at 0.28 and inert, the current letter mint. Hairline on its left.

### Cards (Radio's)
- Three across, rows 96 px, gap 16, radius 18.
- Ground `rgba(255,255,255,.05)`, border `rgba(233,238,242,.1)`, padding 0 22 0 20.
- 54 px disc, label 21/700, optional sub in mono 13 at 0.62.
- Bars: 300 px columns flowing sideways, two rows of 96–104 px.

### Search field
- Standard: replaces the header's title. Height 64, radius 18, ground `rgba(233,238,242,.07)`, padding 0 20.
  - Focused: 1.5 px `#7ed6bc` border, query 24/600, a 2 × 30 px mint caret.
  - At the right: the phone glyph and "TYPING ON PHONE" in mono 13, 0.2em, mint 90%.
- Field-button (on an app level): height 72, radius 18, 1 px 0.16 border, magnifier glyph, label 21/600 at 0.72, and at the right "TYPE ON YOUR PHONE" in mono 13 at 0.62.
- Bar: 60 px tall, radius 16, at the top of the content area.

### Chips (search kinds, YouTube kinds)
- Height 52 (48 on bars), pill radius, padding 0 20.
- Label 18/700 with an optional mono 14 count.
- Selected: mint 16% ground, 40% border, mint label. Otherwise ground 0.06, border 0.14.
- A kind with 0 results has its label at 0.62.

### State block
- Centred: 92 px disc, title 30/700 (no wrap), body 19/1.5 at 0.72, 560 px wide.
- Optional **Retry**: height 56, pill, `#9fb4e8` at 14% / 36%, label 19/700.
- Bar: the disc on the left and the text on the right, title 28, body 18, Retry 52.
- **The region blanks, never the screen.** The header, the mini strip and the rail stay.

---

## Screens

The value in brackets is the `screen` prop. S is Standard, B is Bar.

### 1. Home (`home`, S + B)
- Card order: **My Music** · Browse · Artists · Playlists · **Favourites** · Radio · *(app-added category)* · **Apps** · Settings.
- Cards keep today's size: 219 × 236, radius 24, padding 26 24, gap 26. The row starts 40 px from the left and scrolls sideways with a 72 px fade at the right. New Music below keeps its height.
- Each card: a 44 px icon area, name 30/700 with letter-spacing −0.015em, sub in mono 14 with letter-spacing 0.06em at the tint 90%. Card ground is the tint at 10%, border at 30%.
- New cards:
  - **My Music**: tint `#8fc4d8`, glyph `Shelf` (a disc leaving its sleeve) at 44 px, sub "21 views".
  - **Favourites**: tint `#e8a0b4`, `Heart` at 40, sub "*n* items" or "Empty".
  - **Apps**: tint `#c8a2d8`, `Dots` (3 × 3) at 40, sub "*n* apps".
  - **App-added category** (generic): tint `#b0bcc4` with a **dashed** border at 40%, `Folder` at 40, the name from Lyrion, sub "From Lyrion". It sits just before Apps.
- Browse, Artists, Playlists, Radio and Settings are unchanged.
- Bar: tiles 196 × 300, padding 24 18, gap 20, sideways row. The head column is hidden; the rail stays.
- *Extended navigation* off: Home is exactly as today.

### 2. My Music (`mymusic`, S + B)
- Five groups, keeping Lyrion's labels. Shapes and tints are below; also in `lyrion-data.js` → `MY_MUSIC`.

| Group (header tint) | Entry | Glyph | Tint | Opens as |
|---|---|---|---|---|
| Artists `#9fb4e8` | All Artists | Person | `#9fb4e8` | artist rows, rail |
| | Composers | Score | `#c8a2d8` | artist rows, rail |
| | Popular Artists | Podium | `#e0a758` | ranked rows |
| | New Artists | Spark | `#8fd9a8` | artist rows |
| | Recently Played Artists | Clock | `#8fc4d8` | artist rows |
| Albums `#7ed6bc` | Albums | Sleeve | `#7ed6bc` | cover grid, rail |
| | New Music | Stack | `#f2a48f` | cover grid |
| | Random Albums | Dice | `#e8a0b4` | cover grid |
| | Popular Albums | Crown | `#e0a758` | cover grid |
| | Recently Updated Albums | Refresh | `#8fc4d8` | cover grid |
| | Compilations | Fan | `#9fb4e8` | cover grid |
| | Works | Pillar | `#c8a2d8` | cover grid |
| By category `#f2a48f` | Genres | Tag | `#f2a48f` | genre rows |
| | Years | Calendar | `#e0a758` | decade chips |
| | Music Folder | Folder | `#7ed6bc` | folder rows |
| | Disks and folders | Disk | `#b0bcc4` | folder rows |
| Tracks `#8fd9a8` | Top Tracks | Up | `#8fd9a8` | track rows |
| | Flop Tracks | Down | `#b0bcc4` | track rows |
| More `#c8a2d8` | Search | Search | `#e9eef2` | search field |
| | Library Views | Layers | `#c8a2d8` | rows |
| | Remote Music Libraries | Servers | `#8fc4d8` | rows |

- **Standard:** four columns, gap 24: Artists | Albums | By category | Tracks + More. Group header: mono 13/700, 0.2em, uppercase, in the group tint, then a hairline.
  - Entry card: radius 18, ground 0.05, border 0.1, 46 px disc, label 19/700 on one line. Height flexes 54–76 px so all 21 fit without scrolling from 711 to 853.
- **Bar:** groups run sideways, each a grid of five 56 px rows in 250 px columns (Albums takes two columns). Label 17/700.

### 3. Lists without pictures (`genres`, `years`, `folder`, S + B)
- **Genres:** three columns (five at 1850 on bars). Every row has the `Tag` disc in coral, with letter headers. Standard adds the rail; bars add the letter strip.
  - The **unnamed** entries (11 on George's server) are gathered at the end under a slate header, "No name — Lyrion gives these no label". They show as one row: "No name", italic, at 0.62, with a slate Tag disc and the count as meta.
- **Years:** grouped by decade. A 132 px label column (Calendar disc plus the decade in mono 17/700 `#e0a758`), then year chips ten across: 64 px tall, radius 14, mono 21/600.
  - Bars: decades run sideways, each a five-row grid of 112 × 56 chips.
- **Folder:** "Play folder" bar on top, then `Folder` branch rows (mint) and `Note` leaf rows (coral). Only leaf rows reveal actions.

### 4. Artist lists, no pictures (`artists`, `ranked`, S + B)
- Name rows with an initials circle, three across (five at 1850).
- **Alphabetical lists** (All Artists, Composers, New Artists sorted A–Z) get letter headers, plus the rail on Standard and the letter strip on bars.
- **Lists ordered by plays or recency** get no rail. Popular Artists is two columns: rank (top three in `#e0a758`), initials, name, "*n* plays".
- *(Portraits were tried and reverted at George's request. Do not add pictures.)*

### 5. Covers (`albums`, `albumsFew`, S + B)
- Standard: a grid six across, gap 26 × 22, square covers at radius 16 with the 1 px inset highlight. Title 17/600, sub 15 at 0.62. thousands of albums get the rail.
- A list of two is just two covers, left-aligned.
- Bars: one sideways row of 200 px covers above the letter strip.
- No list / tiles switch (note 2).

### 6. Track lists (`tracks`, `flop`, S + B)
- Two-line leaf rows: rank, 46 px thumb, title, "artist – album", "*n* plays". Selecting a row reveals the actions.
- **Top Tracks:** the trailing "(189)" is taken out of the label and shown as "189 plays" (note 5).
- **Flop Tracks** (tens of thousands): the total is in the crumb. A foot line reads "1–100 of tens of thousands · more as you scroll" (mono 13). No rail, because the list is not alphabetical.
- Play all and Shuffle head every track list. Bars: one column at 1280, two at 1850; Play all and Shuffle sit in the head column.

### 7. An app's album page (`appAlbum`, S + B)
- Built on §7. Lyrion gives no header, so cover, title and artist come from the item that opened the page (label, subtitle, image).
- **Left column**, 264 px:
  - Cover 264.
  - Title 24/700.
  - Artist 17/600 in coral, which is the Artist link. Then "· year" in mono 15.
  - Play album (58 px, mint) and Add to queue (58 px, neutral) at the foot.
- **Right side**:
  - "TRACKS" header with "10 · 46 min".
  - 60 px track rows (number, title, duration; actions when selected).
  - A **Release** block. Plain facts five across: label in mono 12 uppercase, value 19/600 (Genre, Release type, Duration, Tracks, Released).
  - The **links** as pills: height 52, mono 12 key, 18/700 value, chevron. They are Artist, Music label, Credits and Copyright, and each opens its own page.
- Bar: 180 px cover column, a track column, and a facts column (250 px; 420 at 1850) with the link pills.

### 8. An app's first level, and Apps (`qobuz`, `youtube`, `paradise`, `paradiseMix`, `apps`, S + B)
- Cards, with each entry's shape from `shapeFor(label, hint)` in `lyrion-data.js`, one table for every app. The order of lookups:
  1. The label matched against the keyword table.
  2. Lyrion's `hint` (genre → Tag, year → Calendar, folder → Folder, artist → Person, album → Sleeve, work → Pillar, app → Dots).
  3. Otherwise `Folder` in `#8fc4d8`.
- A **search** entry becomes the field-button at the top of the level.
- A level that is **mostly searches** (three or more `search` items, as YouTube has) becomes one field-button plus a chip per kind. The selected kind shows in the field ("Search YouTube · Video"). The level's non-search entries follow as cards under a "LISTS" header.
- **Radio Paradise:**
  - Mixes are cards: `Arcs`, each a different tint, sub "FLAC · 4 qualities".
  - Streams are `Rss` cards.
  - Inside a mix, the four qualities are two-line leaf rows with FLAC first ("Lossless · recommended").
- **Apps:** cards with the app's own logo (60 px, radius 14) in place of a disc, name 21/700, sub in mono 13. Logos are Lyrion's square PNGs. The lettered squares in the mocks are stand-ins.

### 9. Search (`search`, `searchResults`, `searchNone`, S + B)
- Tapping a search entry puts the field in the header, focused. Back still leads the row.
- **Waiting:** a Phone disc, "Type on your phone", "The panel has no keyboard. Your phone types into this field; results arrive as you type, across all five searches."
- **Results:** all five Lyrion searches run together (note 4). Chips: All · Artists · Albums · Works · Songs · Playlists, each with its count. Results follow in two columns, grouped under section headers.
- **None:** a slate Search disc, "Nothing for “query”", "No artist, album, work, song or playlist matches. Check the spelling on your phone."
- Bar: the field sits at the top of the content, chips under it.

### 10. List / tiles switch
- Removed (note 2).

### 11. States and Favourites (`loading`, `unreachable`, `favourites`, `favouritesEmpty`, `nothing`, `notSignedIn`, S + B)
- **Loading:** skeletons in the shape that is coming (covers or rows), fading in opacity from first to last. Pulse with opacity only, staggered as on the artist page.
  - The crumb reads "Loading…". After one second a line under the skeletons reads "WAITING FOR QOBUZ" (mono 13, with a mint dot).
- **Unreachable:** a coral Cloud disc, "Qobuz isn’t answering", "Lyrion could not reach the service. Your library and the other apps are unaffected.", and Retry. Retry returns the region to Loading.
- **Favourites, empty** (Lyrion answers "Empty"): a pink Heart disc, "No favourites yet", "Favourites you add in Lyrion, from any app or the library, appear here."
- **Favourites, full:** two columns of two-line rows, each kind in its own lead:
  - station: `Arcs` in sky.
  - album or track: cover thumb.
  - playlist: `Lines` in coral.
  - folder: `Folder` in mint.
  - Stations and tracks are leaves; the rest are branches.
- **Nothing here** (a branch with no items): a slate Folder disc, "Nothing here", "Lyrion has no entries under *name*."
- **Not signed in** (an app whose only item is unnamed, such as TIDAL): a slate Person disc, "TIDAL isn’t signed in", "Sign in to TIDAL in Lyrion’s own settings. Its menus appear here once it is."

---

## Interactions and behaviour

- **Navigation:** one generic screen walks Lyrion's tree one level at a time. The layout is chosen from the items' `kind` and `hint`:
  - all items have an `image` and kind container → cover grid;
  - kind play → leaf rows;
  - kind folder → disc rows (or cards at an app's first level);
  - any kind search → field.
- **Leaf row:** the first tap selects it and reveals its actions (only one row in the screen at a time); a tap on another row moves the selection; a second tap on the selected row plays it. Play, Play next and Add call Lyrion's actions for that item.
- **Branch row or card:** a tap navigates. The row has no selected state.
- **Paging:** items arrive 100 at a time as the list scrolls, and the total comes with the first page. Letter jumps (rail or strip) need Lyrion's letter index (note 6).
- **Motion:** no animated screen swaps. Press is `scale(0.95)` at `--dur-fast` with `--ease`. Skeletons pulse in opacity only.
- **Text input:** the field shows what the phone sends. Results update when typing pauses.

## Decisions changed — for George (also on the board)

1. **Home peek: today’s card size leaves only a 15 px peek.** At 219 px with 26 px gaps, five cards fill 1,199 of the 1,240 px available, so the sixth shows 15 px. Today’s size is drawn as decided, with a fade. For a peek that reads, cards at 200 px show about 110 px of the sixth. George's call.
2. **Drop the list / tiles switch (brief item 10).** Shape follows content: covers → grid, no picture → rows, tracks → rows. This removes a control from every header and the per-list memory behind it.
3. **My Music regrouped, and two entries hidden when empty.** Groups: Artists 5, Albums 7, By category 4, Tracks 2, More 3. Lyrion’s own names are kept, so nothing needs translating. Proposed: hide Remote Music Libraries when it has 0 entries and Library Views when it has only 1.
4. **One search field for Lyrion’s five searches.** My Music › Search opens the field straight away and runs Artists, Albums, Works, Songs and Playlists together; chips filter. The same idea folds YouTube’s eleven searches into one field with kind chips. This needs five parallel queries each time typing pauses.
5. **Top Tracks: take the count out of the title.** “Sogno (189)” is drawn as Sogno with 189 plays at the right. This needs a parse of a trailing “(n)” on that list only.
6. **Letter jumps need Lyrion’s letter index.** Paging 100 at a time cannot jump to M without knowing where M starts. If Lyrion cannot return the index for a list, that list gets no rail on Standard and no letter strip on bars. Bars keep today’s letter-pair strip (A–B … Y–Z).
7. **For Claude Code: the letter-pair strip may not read as buttons.** George’s concern is that the bar strip (52 px tiles on a 5% ground with a hairline, copied from 13b Bar States) may look like a label row, not 13 controls.
   - Check it on the panel at arm’s length.
   - If it does not read as tappable, raise the resting ground to the row-action level (`rgba(233,238,242,.06)` with a 0.14 hairline) and press to `scale(0.95)` like every other control.
   - Report back before changing anything else.
8. **Row actions are 48 px, labelled.** Today’s 40 px icon actions (Browse, §8) are under the 44 px floor. 13f uses 48 px with words, because “Play next” and “Add” have no shape anyone reads at arm’s length. Browse and Radio are out of scope and unchanged.
9. **Radio Paradise: open a mix, or play it?** It is drawn as Lyrion has it: a mix opens to its four qualities. Alternative: treat a mix as a leaf that plays FLAC on the second tap, keeping the qualities one level in.
10. **Copy written without a source.** Favourites empty, Nothing here, Not signed in, Unreachable and the search prompt are the designer's words. The six YouTube kinds after URL, its three lists and the Radio Paradise names are samples. Use what Lyrion returns.

Where a note is still open, build what is drawn and flag it in the PR.

## Design tokens used

All from `design/tokens.css`.

- **Ground:** `--bg-base #101a21`, `--bg-panel #16232c`, `--bg-well #17242d`, scrim `rgba(8,12,16,.62)`, weave `#3f5a6d` / `#2e4453`.
- **Ink:** `--ink #e9eef2`, 0.88 / 0.82 / 0.72 / 0.62 / 0.60. Fills only (never text) at 0.18 / 0.10 / 0.07 / 0.06 / 0.05.
- **Tints:**
  - `#7ed6bc` mint (LMS, affirm)
  - `#9fb4e8` blue
  - `#f2a48f` coral
  - `#e0a758` amber
  - `#c8a2d8` lilac
  - `#8fc4d8` sky
  - `#b0bcc4` slate
  - `#e8a0b4` pink
  - `#8fd9a8` green
- Disc ground = tint at 14%, border at 30%. Selected row = mint 16%. Chip selected = mint 16% ground, 40% border. Primary button = mint 14% ground, 36% border.
- **Type:** Nunito Sans 30/700 (card title), 26/700 (screen title), 24 (album title, field), 21/700 (card label), 20/600 (row label), 19/700 (buttons, My Music), 17/700 (actions), 15 (subtitle). IBM Plex Mono 13–16 for crumbs, labels, counts and meta. Uppercase labels use 0.18–0.22em letter-spacing.
- **Radii:** 9 (thumb), 12–14 (rows, actions, chips grid), 16 (covers), 18 (cards, field), 24 (Home cards), pill, circle.
- **Touch:** nothing under 44 px. Actions are 48 (46 on bars); strip tiles 52 × ≥44.

## Assets

- `album-art.webp` and `artist-photo.webp` are public-domain sample images (`design/assets/SOURCES.md`).
- `icon-spotify.png` and `icon-lyrion.svg` are from `design/assets/`.
- App logos come from Lyrion at runtime (square PNGs). Stock grey Lyrion icons are replaced by the glyphs.

## Files

```
design/source/13f/
  Lyrion Menus.dc.html     board: 11 items, Standard + Bar, decision notes
  Lyrion Standard.dc.html  26 screens; prop screen
  Lyrion Bar.dc.html       18 screens; props screen, w (1280 | 1850)
  glyphs.js                46 CSS glyphs + disc()
  lyrion-data.js           MY_MUSIC shapes/tints, shapeFor() keyword table, sample data
  support.js               DC runtime (review only)
  album-art.webp, artist-photo.webp, icon-spotify.png, icon-lyrion.svg
```

Standard `screen` values: home, mymusic, genres, years, folder, artists, ranked, albums, albumsFew, tracks, flop, appAlbum, qobuz, youtube, paradise, paradiseMix, search, searchResults, searchNone, favourites, favouritesEmpty, apps, loading, unreachable, nothing, notSignedIn.

Bar `screen` values: home, mymusic, genres, years, artists, albums, tracks, appAlbum, qobuz, youtube, paradise, search, searchResults, favourites, favouritesEmpty, apps, loading, unreachable.

## Suggested order of work

1. Port `glyphs.js` and the disc as one component. Port `shapeFor` and `MY_MUSIC` as data.
2. Generic level screen: choose the layout from kind and hint (rows, cards, covers, field, page).
3. Leaf-row selection and actions. Remove the always-visible actions from the current build.
4. Home tiles and the sideways row.
5. Search through the phone, the app album page, then the states.
6. Bar family, using the same components with the head column, rail and letter strip.
7. Check every screen at 711, 800 and 853 tall, and at 1280 × 400 and 1850 × 400 (shown at 0.8).
