# Handoff: gexis panel UI — revision 2026-10-01 (Phase 13b round 2)

## Overview

The interface for the gexis network audio player, a Raspberry Pi 4 with its
own touch panel. It covers:

- the 1280×800 panel: Now Playing, the mini strip, the library (home, Browse,
  Artists, artist page, album, Playlists, Radio), the queue rail, the volume
  drawer, the idle screen, the handoff transition, Bluetooth pairing, the
  waiting home with LMS off, and the panel's setup screens;
- the phone: Settings (responsive, also shown on the panel), the mini player
  under it, and first-time Setup;
- **Phase 13b, other screens**: two layout families, Standard (aspect 1.5–1.8)
  and Bar (aspect 3–5), derived from the panel by stated rules, plus the Screen
  step in Setup and the Attached screen / Screen rotation rows in Settings;
- **Phase 13b round 2 (2026-10-01)**: the answer to `design/briefs/13b-bar-gaps.md`
  and `design/briefs/13b-corrections.md` (see *Round 2* below).

Target repo: `gcarstoiu/gexis-player`, a Svelte 5 UI over a Python core. The
designs were synced against branch `phase-13` at commit `403d582330`.
`github.md` and `repo-context.md` record which repo files each screen maps to.

## About the design files

**The HTML in this bundle is a design reference, not production code.** The
`.dc.html` files are interactive prototypes: they open in a browser, run their
own state, and exist to show intended look and behaviour exactly. Do not ship
them or copy their markup. **Recreate them in the repo's own environment**:
Svelte 5 components in `ui/src/screens/`, the project's state in
`ui/src/lib/state.js`, its tokens.

`design/` is the package the repo keeps at `design/` — unpack this bundle's
`design/` over the repo's. `design/now-playing.html` is a plain HTML/CSS
transcription of one screen, written so values can be read without running the
prototype; read it as a specification.

## Fidelity

**High.** Colours, type, spacing, states and behaviour are final unless a line
says otherwise. Recreate them exactly. `design/tokens.css` holds every value.

Not final, and marked so: the QR codes (placeholders), the setup password
(a sample), the turntable and tape skin names (picked from the meter corpus by
name; the animated skins are not in the repo), and the screen models in the
Screen step's list (samples from `foonerd/pi_screen_setup`, Finding 100).

## Round 2 — what changed on 2026-10-01

Open `13b/Screen Families Round 2.dc.html`. Its width buttons put every bar
board at 1200, 1280, 1850 or 2000. Where it differs from the round-1 section
further down, round 2 wins.

**Bars** (`Bar Frame`, `Bar Panels`, new `Bar States`):
- **Forecast:** `days = floor((W − 1112) / 136)`, clamped 0–3. None below 1248,
  one from 1248, two from 1384, three from 1520. Same rule in both files.
- **Idle:** padding 48 and drift ±24 each side; clock 523; separator and gaps
  81; today 360 (icon 100, gap 20, condition max 240, two lines, clamped);
  then 40, and 100 + 36 per day. The clock group drifts sideways only.
- **Queue:** the panel rail's header with **Clear** (44 tall) and the 66 px
  **Playing from** row; three 60 px rows plus part of a fourth, scrolling.
- **Targets ≥ 44:** tray volume is a 60 px mute button; slider knob 44; the
  slider takes touches across the tray's height; the handle's drag zone is a
  full-width 44 px band at the strip's top edge (the tray's bottom 44 when
  open). Tray slider fill is the source accent, not ink.
- **Tray:** fixed output shows the panel's padlock row in place of mute and
  slider; muted is amber (cone crossed, fill 0, *Mute*); no meters hides the
  visualiser button; LMS off turns Home into Settings; a volume change from
  elsewhere brings the tray down over any screen, including the library.
- **Strip:** artwork pending (panel placeholder); Bluetooth has no progress,
  times, shuffle, repeat or queue; long title ellipsised, artist ≤ 62% of its
  line, album the rest, year kept; Spotify / Bluetooth marks at 30, a plugin's
  initial in a ring; lyrics loading (three skeleton lines), plain (static, no
  highlight), synced, with the credit *From LMS* 13px mono; no lyrics hides the
  switch (instrumental is the same as none).
- **Library:** rail with nothing playing (empty slot, no mark, no progress,
  play at 0.3 and inert); Artists jump strip of 13 two-letter steps, each ≥ 44
  wide, 52 tall; playlist detail like the album page; radio folders and
  stations in one grid (folders with a chevron); toast at the bottom centre of
  the content area; a sheet on a bar is full height less 12 px, and Attached
  screen shows makers and models side by side with no search box.
- **Moments:** pairing outcomes (tick or cross, *Paired* / *Not paired* /
  *Request expired*); a request with no code shows the device name at 48;
  LMS off with 4+ renderers stands them in 200 px columns, gap 48, names
  under the marks; a long transition name wraps to two lines at 52 (64 from
  1500) in a 340 (520) box, the line keeping ≥ 120; idle clock off = weather
  alone, centred; weather off = clock alone; External URL fills W × 400.
- **Setup:** starting, phone connected, open the page, carry on on your phone,
  done with the Lyrion card, could not join (keeps network and password),
  setup network did not start, and over Ethernet (the page's code only).
- **Ends:** strip, idle, library home and pairing checked at 1200 and 2000.
  Home tiles step their type down when a tile is under 190 px wide (W < 1436).

**Standard** (`13b/Now Playing Height Study.dc.html`, `Panel Setup.dc.html`):
- Heights shown: 711 (aspect 1.8), **720** (16:9, the 13.3″), **768** (the 7″),
  800, 853.
- The repo's three fixes are in the design: home cards
  `max(200 × k, 164)`; artist and album columns as wide as their picture;
  Panel Setup's QR code 260 below 800 logical, 340 from 800 (prop `h`).
- The artist page's extra height goes to the albums.
- Corrected claims (Chosen): touch floor 44 px; smallest type 11–12 px mono;
  rule 1b written out.

**New: Keep this screen?** (`13b/Keep This Screen.dc.html`, props `family`,
`w`, `h`, `left`, `untested`, `model`). Shown on the panel after a screen or
rotation is chosen and the player has restarted on it. Title 72/800 (56 on a
bar); model line; **Keep** 96 tall (110 on a bar), `#7ed6bc` on `#0d151c`
ink, radius 24; **Go back now** 74; *Going back to {previous} in {n} s* 20px
mono; an 8 px bar along the bottom drains over 30 s; at 0 the player reverts.
Until Keep, the setup network keeps its fixed password (ADR-0109 decision 5).

**Setup Screen step** (`Setup.dc.html`): *Is this your screen?* / *What the
screen reports matches this model*, a **Tested** tag, and *Suggested from
what the screen and its touch controller report*; Choose another opens the
full list (no reported block, no filter); in the uncertain state models
matching the reported resolution come first, then every maker; every row is
Tested or Untested; an untested pick says so; any pick says the player
restarts on it and asks Keep this screen?; Headless shows its warning.

**Settings** (`Settings.dc.html`; rows in `design/settings.md`, *Changed
2026-10-01*): System → **Updates** (Release, Check now, Update now, Updates
Manual/Automatic, Update channel Stable/Testing) then **Maintenance**;
Plugins → **Upload a plugin** (`noPanel`: hidden when embedded on the panel);
Attached screen is the Time zone two-step picker (maker → model, Tested /
Untested); Screen rotation 0° / 180°; Visualization → **Skin size**.

**Not done:** the Settings sheet's 82% cap on short screens (drawn full height
on bars, not changed in `Settings.dc.html`); skin sets as rows on the Plugins
screen. Copy written without a repo source, to confirm: the Headless warning,
the Testing warning, the Updates rows' notes.

## First task: run verify.html

`design/verify.html` checks the plain slice against the prototype. It needs an
HTTP server; `file://` blocks the iframe read:

```
cd design && python3 -m http.server 8080
# open http://localhost:8080/verify.html
```

**It has not been run against this revision.** The slice was re-extracted by
hand for the changes listed below, and no landmark moved, so `geometry.json`
is unchanged. **A failure means the export drifted from the prototype: fix
`now-playing.css` / `.html`, never the baseline and never `source/`.** If group
6 reports *could not run*, the prototype did not hydrate within 8 s; re-run.
`design/README.md` → *Verifying an export* explains each group.

## Where to start

| Read | For |
|---|---|
| `design/README.md` | How the package works, constraints, and every change by date. Read **Changed 2026-09-30** first. |
| `design/tokens.css` | Every colour, type size, radius, shadow and tracking value. |
| `design/screens.md` | Every panel screen, one section each, plus **Changed 2026-09-30**. |
| `design/settings.md` | Settings' row vocabulary. `source/Settings.dc.html` is the inventory; it follows `settings_registry.json` row for row. |
| `design/data-contract.md` | Fields per screen, mapped to `/state`; `NEW` marks what the backend does not publish. **Changed 2026-09-30** lists LMS-off, queue remove, setup and 13b fields. |
| `design/IMPLEMENTED-DIFFERENTLY.md` | The repo's own record of where the panel departs from the design, taken as the point of truth. |
| `design/source/13b/Screen Families Round 2.dc.html` | Phase 13b round 2 (2026-10-01): the answer to `13b-bar-gaps.md` and `13b-corrections.md`. |
| `design/source/13b/Screen Families Chosen.dc.html` | Phase 13b round 1, the chosen designs, one page. |

## What changed since the last handoff (2026-09-22)

Each item is in `source/` and documented in `design/`. In implementation order:

1. **Now Playing (plain slice updated).**
   - The source mark does not pulse (Finding 056).
   - Home is 64px with a 24px four-tile glyph, 4px gaps, tiles radius 3,
     `rgba(233,238,242,0.85)`.
   - Shuffle and repeat: 60px, ground `rgba(233,238,242,0.07)`, 1px border
     `rgba(233,238,242,0.12)`, glyph ink `rgba(233,238,242,0.66)`; active uses
     `rgba(126,214,188,0.16)` ground, `0.42` border and `#7ed6bc` ink.
   - Volume glyph 30px: a 15×26 cone and arcs of 16 / 24 / 30 at 2.5px, lit at
     `0.85` past 0 / 34 / 67 percent, unlit at `0.18`. Fixed output shows a
     padlock in its place (ADR-0046).
   - The right group's gap is 14px.
2. **LMS off (ADR-0079).** No library. Nothing playing shows the waiting marks
   full screen (180px rings, 162px discs, Spotify 68px, Bluetooth 74px, 310px
   columns 60px apart, name 27/700, status 15px mono uppercase from the
   manifest: *Listening*, *Pairable*) and a 64px Settings button 26px from top
   and right. Every source off: **No sources** / *"Every source is switched off.
   Settings, top right."* While playing, Home shows a 22×16 sliders glyph and
   opens Settings; the artist line is inert.
3. **Queue rail: swipe to remove**, no X (`QueueRail.svelte`, ADR-0062). Past
   96px releases a removal; under 12px the axis is undecided and vertical wins
   the list. *Remove* (13px mono, `#f2a48f` on `rgba(242,164,143,0.16)`) sits
   behind the row. Drag has no transition; release eases 190ms
   `cubic-bezier(0.2,0.8,0.2,1)`; removal slides 130ms `cubic-bezier(0.4,0,1,1)`
   and fades 120ms. One-time hint: row 1 opens to −70px at 480ms, closes at
   1500ms, once per run, when the rail opens with ≥ 2 rows. A click within
   320ms of a swipe is not a tap. Row press is opacity 0.62.
4. **Idle** gains `idle_clock`: off, the panel is a picture frame with its
   credits line. The credits read *"Gasca Zurli · Weather data by
   Open-Meteo.com"* (artist, then licence credit). `weather_key` is gone.
5. **Settings** follows `settings_registry.json` (phase-13). New: **Attached
   screen** and **Screen rotation** at the top of Display → Panel (below).
6. **Setup (phone)** from `SetupPage.svelte`: the blurred weave; the amber
   *Keep mobile data off* card on Welcome (not over LAN); Music as three
   Lyrion choices (*Find my Lyrion server*, *Enter an address*, *I don't use
   Lyrion*) with Continue disabled until one is picked; Review's Library line;
   Change on Review returns to Review. **Phase 13b: the Screen step** (below).
7. **Panel Setup** from `SetupScreen.svelte`: one step at a time, nothing to
   read under 30px; the done screen's Lyrion card.
8. **Pictures:** album art, artist photo and the Bluetooth mark are the repo's
   current public-domain / gexis files (`design/assets/SOURCES.md`).

## Phase 13b — other screens

**Round 2, 2026-10-01:** `design/source/13b/Screen Families Round 2.dc.html`
supersedes the numbers below where they differ: touch floor 44 px; forecast
days = floor((W − 1112) / 136), 0 to 3; tray mute 60, knob 44, slider fill in
the source accent; rotation 0° / 180°. The rest of this section is round 1.

Answer to `design/briefs/13b-screen-families.md`. Everything is on
`design/source/13b/Screen Families Chosen.dc.html`; open it in a browser. A switch at the top
shows every bar board at 1280 × 400 or 1480 × 320. Settled by George on
2026-09-30: Settings stays a tile on bars; Attached screen and Screen rotation
are in the inventory; the copy is accepted as drawn.

### Family choice

By aspect, not resolution: **Standard** 1.5–1.8 (800×480, 1280×800, 1920×1080
and between), **Bar** 3–5 (1280×400, 1480×320). One token set for both.

### Standard: the hero absorbs the height

- Lay out at a **logical width of 1280**; scale = screen width ÷ 1280 (0.625
  on 800×480, 1 on 1280×800, 1.5 on 1920×1080). Logical height H =
  screen height ÷ scale, **711 (aspect 1.8) to 853 (1.5)**; 16:9 (the 13.3″)
  is **720** and the 7″ 800×480 is **768**.
- One element per screen takes H − 800; margins, gaps, type and controls keep
  their 800 values:
  - Now Playing: artwork = **H − 300** (411 / 500 / 553), square; grid rows
    `art 1fr auto`, columns `art 1fr`; the meta column takes the width.
  - Library home: cards (200) and New Music tiles (176) × **k = (H − 424) /
    376** (0.76 / 1 / 1.14).
  - Artist photo 262 × H / 800; album cover 264 × H / 800.
  - Lists (Browse, Artists, Playlists, Radio, queue, Settings): more or fewer
    rows.
  - Idle, transition, pairing, volume drawer: nothing; centred.
- **Type is uniform**: it scales with the screen, 1.5× on 1920×1080. Nothing
  is capped.
- **Touch floor 44 logical px; nothing grows** (ADR-0109 decision 4). 44 px
  is 5.2 mm on the 7″ 800×480, 7.5 mm on 10.1″ 1280×800, 10 mm on the 13.3″.
  Physical size is taken from the published panel width, never EDID
  (Finding 100).
- `13b/Now Playing Height Study.dc.html` is the panel prototype with this rule
  applied (`view`, `h` props) — a study copy; `source/Now Playing.dc.html` is
  unchanged.

### Bar: a reduced panel of strips

- Lay out at a **logical height of 400**; logical width = aspect × 400 (1280
  on 1280×400; 1850 on 1480×320, shown at 0.8). One region per strip takes
  the width.
- Touch: 44 px = 6.6 mm on 7.9″ 1280×400, 7.0 mm on 11.9″ 1480×320.
- **Now Playing strip** (`Bar Frame`, `variant="strip" sr="main" pull="down"`):
  padding 32 40; artwork 336 radius 20, gap 36; title 42/700 one line; artist
  28/600 `#f2a48f`, album 24 at 0.6, year 21 mono; source mark 30 (four-bar
  LMS reduction); a 60px lyrics switch (three bars; on: coral 16% ground, 45%
  border, `#f2a48f` ink). Progress: 10px track, times 16px mono either side,
  gap 16. Transport centred on a `1fr auto 1fr` grid, gap 22: shuffle 60,
  previous 68, play 92, next 68, repeat 60; queue 60 at the right. **Width
  goes to** the progress bar.
  - **Lyrics on:** title 24/700 and artist 20/600 on one line, then three lines
    at 26px / 1.3: the current one 700 coral, the neighbours 500 at 0.85 ink
    and 0.42 opacity. No tabs; no artist or release info on a bar.
  - **Pull-down tray:** a handle 88×6, radius 3, `rgba(233,238,242,0.42)`,
    centred 12px from the top. The tray is 136 tall from the top edge,
    `#16232c`, radius `0 0 24px 24px`, shadow `0 18px 44px rgba(0,0,0,0.5)`,
    padding `0 40px 14px`, gap 20, its own handle 10px from its bottom, over a
    `rgba(8,12,16,0.55)` scrim: Home 64, visualiser 60, a 1×44 divider, the
    volume glyph, a slider (10px track, 40px knob, fill `#e9eef2`), the value
    26px mono 700. Drag down to open; drag up or tap the strip to close. A
    volume change from elsewhere opens it by itself and it hides after
    `drawer_autohide` (3 s). **Width goes to** the slider.
  - **Queue:** the panel's rail at 470px over the strip, rows 60, swipe to
    remove.
- **Browse** (`Bar Frame variant="home2" layout="c"`, `Bar Library`):
  - A 124px rail on the right: cover 84 radius 12, the renderer's mark 26
    centred, play 64; progress as a 3px line on its inner (left) edge, filling
    **from the bottom**, accent at 0.8.
  - Library home: the panel's cards, six across (Browse, Artists, Playlists,
    New Music, Radio, Settings), gap 20, height 220, padding `0 36px`. The
    home strip becomes a tile like Radio, named by `home_strip`. Below 1500
    logical width the tile title is 21px, sub-line 12px, padding `20px 14px`.
  - Every library screen: a 220px left column (padding 28 24; Back 60, and
    Home 60 two levels in; title 26/700; count 15px mono at 0.6), the content,
    the rail. New Music: 250px tiles, gap 22, one sideways row. Artists: 220px
    circles, gap 30. Browse: three panes, Artists / Albums / Tracks at
    1 : 1.25 : 1.1, gap 12, padding 24, 40px headers, 52px rows. Playlists:
    250px cards radius 24. Radio: two columns of 120px cards, gap 16.
    Settings: the panel's Settings in the content area.
  - **Artist page** (`screen="artist2"`): no left column; the photo 400×400
    full height with a top 45% and bottom 88% `#0d151c` gradient, Back and
    Home over it at 24/24, the name 34/800 and tags 15px mono over its foot;
    then Play / Shuffle (58 tall, radius 16) and the albums as 200px tiles.
  - **Album** (`screen="album2"`): the cover the same way with the title and
    `GASCA ZURLI · 2014`-style meta over it; *Play album* and *Add to queue*
    above the track list (52px rows, the playing one tinted).
- **Full-screen moments** (`Bar Panels`):
  - Transition (`t2`): scrim `rgba(13,21,27,0.95)`; the right 62% washes to the
    new accent at 0.2; the old source small left (mark 44, label 26/600,
    opacity 0.55), a line, then the new source in a 176px circle (3px accent
    border, 14% ground, glow) with *Handing off to* (15px mono, 0.34em) over
    its name at 64/800 in the accent. **Width goes to** the line.
  - Pairing (`p2`): grid `minmax(0,1fr) auto auto`; device left (mark 56, name
    30/700); the code centred, 110px mono 700 at 0.12em `#9fb4e8` (88px below
    1500 wide); Reject and Accept right, 74 tall, radius 18; the countdown is a
    6px bar along the bottom edge in `#9fb4e8`.
  - Idle (`idle`, `idle-black`, `idle-frame`): clock 150px mono 300 with
    seconds 64 in the accent; date 26px mono 0.2em uppercase; a 1×220 divider;
    weather icon 124, temperature 100/300, max 40/700 coral, min 30
    `#9fb4e8`, condition 30/600 accent; the forecast: one day below 1500 wide,
    four at 1850 (day 24px mono, icon 80, max 36, min 28). The clock drifts
    sideways only. Credits 11px mono 8px from the bottom.
  - Setup (`s-new`, `s-lost`, `s-fail`, `s-joining`): header mark 32 and crumb
    15px mono at the top. One QR code, 300px, dark on light; network and
    password (labels 18px mono, values 44px mono 700); title 40/800; *"Scan to
    join, then open 10.42.0.1:8090"* at 24; the amber mobile-data box.
    *Could not join*: a 110px triangle, the title 44/800, the reason at 24.
    *Joining*: the panel's 176px circle and a 64/800 title.
  - LMS off (`Bar Frame wait`, `wait-none`): 150px rings, 136px discs, marks
    56 / 62, name 27, status 15px mono; 96px apart (160 at 1850); Settings 64
    radius 18 at 26/26.
- **Dropped on a bar:** the meta tabs (lyrics remain as a switch); artist and
  release info; the artist page's biography, top tracks and similar artists;
  the mini player's title and artist (the rail shows cover and mark);
  setup's second QR code (the address is text); forecast days beyond one at
  1280.

### Visualiser, both families

Entry, exit and content stay as ADR-0019 and ADR-0036 set them: in by the
button (in the tray on a bar) or five minutes of unattended playback; the skin
and nothing else; out on any touch or a renderer change, to Now Playing.
**A screen uses the skins drawn for its exact size; with none, the largest set
that fits inside it, centred at 1:1, opaque black around it** (as
`05-peppy/files/letterbox.py` already does for the 720 packs). The picker
offers only the current screen's set.

### Screen step and Settings rows (merged into the prototypes)

- `source/Setup.dc.html`, step 6 **Screen** (prop `screen`: `recognised`,
  `uncertain`, `none`):
  - *Recognised*: the model, its resolution and family, *"Read from the screen
    and its touch controller"*, with **This is right** / **Choose another**.
  - *Seen, not certain*: what the screen reported (maker, resolution, touch
    USB ID), a search field and the list grouped by maker.
  - *Nothing on the screen yet*: the list, then, once one is picked, the amber
    note that the player restarts and tries it and what to do if it stays
    dark.
  - **Headless** is the last choice on all three. Continue waits for a choice
    unless the screen was recognised. Review reads *Screen* with the model.
- `source/Settings.dc.html`, Display → Panel, first two rows, both [N] (new;
  R in ADR-0022 means *recorded*), both restarting the player: **Attached
  screen** (a two-step picker, maker then model, tested marked; sets the
  family and the skin set) and **Screen rotation** (0° / 180°). Named apart
  from the idle *Screen* row and the turntable *Rotation* row.
- `design/data-contract.md` lists the new fields: the model, what the screen
  reported (EDID maker, name, modes; USB touch ID), `rotation`, confirmation,
  and the skin set with whether it is exact.

## Interactions and behaviour (cross-cutting)

- Touch only; every target ≥ 44×44 logical px on every screen. Several targets get their size from padding plus a negative margin;
  re-measure if restructured.
- No long press, no on-screen keyboard, no creating playlists on the device.
- Unsupported controls are removed, not disabled (Spotify and Bluetooth have
  no shuffle, repeat or queue; Bluetooth has no artwork or position).
- Paused is shown by the play control's shape alone: no label, no dimming.
- Motion budget is a Pi 4: transform and opacity only, no `backdrop-filter`.
- Null handling: the region blanks, never the screen (`design/README.md`).

## State management

`design/data-contract.md` is the authority. Progress is interpolated
client-side and re-anchored on every `/state` message (`now-playing.js`).
Volume is percent, never dB. `sample_rate` and `codec` are never displayed.

## Design tokens

`design/tokens.css`: colours (base `#101a21`, panel `#16232c`, ink `#e9eef2`
and its alphas, accents LMS `#7ed6bc`, Spotify `#8fd9a8`, Bluetooth `#9fb4e8`,
artist/play `#f2a48f`, warn `#e0a758`, display `#c8a2d8`), the type scale,
tracking, radii (8 / 12 / 16 / 22 / 24 / pill / circle), shadows and spacing.
Fonts: Nunito Sans (variable 300–800) and IBM Plex Mono (400 / 600 / 700),
vendored in `design/fonts/` (SIL OFL).

## Assets

- `album-art.webp`, `artist-photo.webp`: samples (public domain;
  `design/assets/SOURCES.md`).
- `icon-lyrion.svg`, `icon-spotify.png`, `icon-bluetooth.png` (gexis's own
  square mark), `gexis-mark.svg`.
- `brand/`: the gexis brand package. Known gap: the Plymouth boot frames
  predate the lettered mark and need re-rendering.
- No icon font; every other glyph is CSS geometry.

## Files

```
README.md                    this file
github.md                    repo, branch, sync receipts, screen-to-file map
repo-context.md              repo notes from the sync
Now Playing.dc.html          panel prototype (Now Playing, library, queue, drawer, idle,
                             pairing, handoff, waiting home) — open in a browser
Settings.dc.html             Settings, responsive, with Attached screen / Screen rotation
Setup.dc.html                phone setup, with the Screen step
Panel Setup.dc.html          the panel during setup, one step at a time
support.js                   prototype runtime, required by every .dc.html
*.webp / *.png / *.svg       images the prototypes load
design/source/13b/           Phase 13b — open Screen Families Round 2.dc.html
  Screen Families Round 2.dc.html  round 2, 2026-10-01
  Bar States / Keep This Screen .dc.html   round 2 boards
  Screen Families Chosen.dc.html   round 1, the chosen designs, one page
  Now Playing Height Study.dc.html Standard family study copy of the panel
  Bar Frame / Bar Library / Bar Panels .dc.html   the bar strips
  Settings Screen Row.dc.html      Settings opened on Display
  (+ copies of Setup, Settings, support.js and images so it opens on its own)
design/                      the package the repo keeps at design/
  README.md                  read first; Changed 2026-09-30
  tokens.css, fonts.css, fonts/
  screens.md, settings.md, data-contract.md, IMPLEMENTED-DIFFERENTLY.md
  now-playing.html/.css/.js  one screen as plain HTML/CSS, six states
  geometry.json, verify.html
  source/                    self-contained prototypes for verify.html, and source/13b/
  assets/, marks/, briefs/, implemented/
brand/                       brand package
```

## Checklist for Claude Code

1. Unpack `design/` over the repo's `design/`; commit.
2. Run `design/verify.html` over HTTP. Fix any failure in the export only.
3. Port the changes listed under *What changed since the last handoff*,
   checking each against `IMPLEMENTED-DIFFERENTLY.md` first: several are the
   panel's own behaviour taken back into the design.
4. Add `screen` and `rotation` to `settings_registry.json` (George confirmed
   them 2026-09-30) and the Screen step to `SetupPage.svelte`.
5. Port round 2 (above), then write Phase 13b's ADR from `design/source/13b/Screen Families Round 2.dc.html`, `Screen Families Chosen.dc.html` and this
   README's 13b section, then build the families.
