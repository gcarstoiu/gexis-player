# Phase 22: multiroom

Grouping players on the phone remote's player list, the panel's volume
drawer and the bar's tray, the grouped mark on Now Playing, and the group
volume. From `design/briefs/22-multiroom.md` and ADR-0166. George's picks,
2026-10-27: **1a** (Join and Remove on each row), **2a** (the volume drawer
and the bar's tray), **3a** (the mark centred midway between the progress bar
and the play control).

Open `Multiroom Board.dc.html` over HTTP from `design/`
(`cd design && python3 -m http.server 8080`, then
`/source/22/Multiroom%20Board.dc.html`). Every artboard is live: Join, Remove,
Leave, Undo group and the sliders work. The board is heavy; add
`#shot=1a-1,2a-3` to the URL to render only those artboards.

**High fidelity.** Every value below is taken from the two design files.
Tokens are under *Phase 22* at the end of `../../tokens.css`. One PNG per
state is in `png/`, named by artboard id.

## Production wins

The screens under these additions must stay as they are in production. The
panel and bar artboards are drawn over pictures of the design files
(`eq/backdrop-*.png`), and on the bars those pictures do not match
production (strip, transport, tray). **Do not change any production screen
to match them.** Build only what Phase 22 adds, onto production as it is:

- the grouped mark,
- the group in the panel's volume drawer and the bar's tray,
- the group on the phone's *Gexis players* list and its group volume.

Where a picture and production disagree, production wins. Place the
additions by the rules below (midway between, beside, under), not by the
pixel positions in the artboards.

`Now Playing.dc.html` and `Settings.dc.html` are unchanged, locked copies.

## Component boundaries

| Component | Where | Props / inputs | Notes |
|---|---|---|---|
| `GroupMark` | panel and bar Now Playing, phone Remote | `others: string[]` | Chip on panel and bar, plain line on the phone. Tap opens the group (drawer / tray band / player list). Hidden when not grouped. |
| `GroupGlyph` | everywhere | `size`, `ink` | Two speakers, 24 viewBox, stroke 2. In each design file as inline SVG. |
| `PlayerRow` | phone list, panel Add players, bar add band | `player`, `status`, `lead`, `current`, `action: join\|remove\|none` | Tap on the row switches the phone to that player, as today. The button is its own hit target. |
| `GroupBlock` | phone list | `group`, `nowPlaying`, `viewer` | Members (as `PlayerRow`), Leave (members only), Undo group. |
| `GroupVolume` | phone sheet, panel drawer, bar band | `members[]`, `level`, `muted` | *All* slider + one row per member (`MemberVolume`). |
| `MemberVolume` | inside `GroupVolume` | `player`, `level`, `muted`, `fixed`, `reachable`, `removable` | Variable: mute + slider + value. Fixed: mute + locked row. Off: dashed *Not reachable*. |
| `UndoConfirm` | every surface | `members`, `leader` | Asks first. |
| `TrayGroupButton` | bar tray | `grouped`, `count`, `open` | Pill beside the EQ pill; opens the second band. |

## Rules (decided here, not in ADR-0166)

- The leader can't be removed and has no Leave; it ends grouping with Undo
  group. Removing it would take the music from the others.
- **Undo group** keeps the music on the leader; the other players stop.
  It asks first.
- Mute on the *All* slider mutes every player; each member's own mute stays
  in its row. The *All* slider moves every variable member by the same step,
  so the balance between rooms stays. Its value is the mean of the variable
  members. Fixed members are not moved; their mute still works.
- Joining a player that plays something of its own stops it without asking
  (C1). Joining a player from another group takes it out of that group.
- Each member keeps its own equaliser (C5): the EQ button and name stay this
  player's.
- The leader going off: the others fall silent and stay grouped; the next
  music started on any of them leads. The panel shows Home, as it does when
  nothing plays.
- The mark and the group use the LMS accent `#7ed6bc` whatever the source.

## Words

Status line on a player row:
- `Playing · Lyrion` (leader, or a player on its own; the source name)
- `In this group` / `In this group · silent`
- `Joining · catching up` (accent)
- `In a group with Office and Garage · Plexamp`
- `Idle`, `Paused · Spotify`
- `Not reachable` (row at 0.45) / `Off · was leading the group`

Mark: `with Kitchen, Study`; past two names, `with Kitchen, Study + 3`.
Group head: `Grouped · 3 players`, `Grouped · silent`.
Undo: title *Undo the group?*, body *Living Room, Kitchen and Study each play
on their own again. The music stays on Living Room.*

## The grouped mark (3a)

Centred horizontally on the transport, **midway between the progress bar and
the play control**.
- **Panel:** chip 44 tall, radius 22, padding `0 18px 0 14px`, gap 10,
  ground `rgba(233,238,242,0.07)`, line 1px `rgba(233,238,242,0.14)`;
  glyph 20 in `#7ed6bc`; text 16/600 `#e9eef2`. Max width 680, ellipsis.
- **Bar:** same chip at 36 tall, radius 18.
- **Phone:** no chip. Glyph 16, gap 6, text 13/600 at
  `rgba(233,238,242,0.86)`. Screen layout: under the transport row, above
  the progress bar (margin-top 12). No-screen layout: under the times,
  above the transport (margin-top 8).

## Phone: Gexis players (1a)

The menu card as in Phase 21. Grouped, the top of the list is the group
block: margin `4px 8px 8px`, radius 14, ground `rgba(126,214,188,0.06)`,
line `rgba(126,214,188,0.22)`, padding `12px 0 10px`.
- Head: glyph 20, *Grouped · 3 players* 14/700 accent, what plays 13 at 0.72.
- Member rows; then Leave group (members) and Undo group (amber), 44 tall,
  radius 12, 15/700, side by side.
- Then *Other players* (mono 11, 0.2em, uppercase, 0.6) and the rest.

Rows: min 64, mark 30, gap 12. Name 16/700, up to two lines; *Leads* tag
inline (mono 10, 0.14em, padding `4px 6px`, radius 6, ground
`rgba(126,214,188,0.14)`, accent). Status 13 at 0.72. This player: check
22 and ground `rgba(233,238,242,0.05)`. Buttons 44, padding `0 14px`,
radius 12, 15/700: **Join** accent on `rgba(126,214,188,0.14)` /
0.45 line; **Remove** neutral on `rgba(233,238,242,0.07)` / 0.14.

## Phone: group volume

Grouped, the volume row's label reads `GROUP` and the count, and the slider
is the *All* slider. A 56 group button (radius 18, ground
`rgba(126,214,188,0.12)`, line 0.45, accent glyph 22) sits left of EQ and
opens the sheet. The sheet is built like the EQ sheet: title *Group volume*
19/700, sub `3 players · each keeps its own level` (mono 13).
- *All*: name column 104 (15/700 accent), slider 44, radius 12, line
  `rgba(126,214,188,0.35)`.
- Members: min 40, slider 36, mute 32 inside it (as the remote's volume
  bar). Fixed: the locked row (padlock, *Fixed output*), mute still works.
  Off: dashed *Not reachable*.
- Note under the rows, 14 at 0.6, naming Fixed members.

## Panel: the volume drawer (2a)

Width 820, padding `30px 40px 32px`, radius 28, ground `#16232c`, line
`rgba(126,214,188,0.22)`. Keep production's volume and EQ sections.
- **Not grouped:** under the volume, a row: glyph 26, *Other players*
  19/600, *Join players to this one to play the same music in sync.* 15 at
  0.6, and **+ Add players** (58, radius 15). It opens *Add players*: the
  same card, Back 56, title 25/700, the player rows (min 72, mark 34, name
  19/700, status 15, buttons 52 / padding 20 / radius 14 / 17).
- **Grouped:** the volume becomes *Group volume*: head (glyph 26, title,
  sub, + Add players 52), *All players* (200 name column, 17/700 accent)
  with the drawer's big slider (mute 58, track 14, knob 40, value 26 mono),
  then member rows: 64 min, name 200 (17/600, tag mono 11), mute 48, track
  10, knob 32, value 20 mono, Remove 48 circle. Five or more scroll at 256
  with a 48px fade. Leave group and Undo group (58) at the bottom right.

## Bar: the tray (2a)

Keep production's tray. Add a **Group** pill beside the EQ pill: 60 tall,
radius 30, padding `0 20px 0 18px`, gap 12, glyph 24, 19/700, chevron.
Grouped it reads *3 players* in the accent on `rgba(126,214,188,0.12)` /
0.45, and the tray's slider is the *All* slider with an `ALL` label (mono
14, 0.16em, accent). The pill opens a second band, 150 tall, as the
equaliser's does: member cards 330 × 116 (radius 18, ground
`rgba(255,255,255,0.04)`, line 0.1; name 18/700, tag mono 12, mute 48,
track 8, knob 32, value 20 mono, Remove 44 circle), scrolling sideways with
an 88px fade, and a 220 column with + Add players, Leave and Undo group
(53). Add players swaps the band for player cards with Join.

## Undo confirm

Panel 560 wide, bar 640, phone 16 from the sides; radius 22 (phone 20),
padding 26. Title 25/700, body 17 at 0.72. Cancel (neutral) and Undo group
(amber): 58 tall on the panel, 60 on the bar, 48 on the phone.

## Files

| File | What it is |
|---|---|
| `Multiroom Board.dc.html` | The final board: 1a, 2a, 3a and every state. |
| `Phone Remote Multiroom.dc.html` | Phone Remote v3 plus the group. Props `scene`, `open` (`none` / `menu` / `vol` / `undo`), `me`. |
| `Multiroom Panel.dc.html` | Panel and bar. Props `surface` (`panel` / `bar`), `scene`, `open` (`none` / `drawer` / `add` / `undo`), `me`. |
| `multiroom-data.js` | Sample players, scenes and the status words. |
| `Now Playing.dc.html`, `Settings.dc.html` | Locked, unchanged copies (Home in the leader-gone state; the phone's Settings page). |
| `eq/` | Pictures of the locked Now Playing at panel and bar size. |
| `png/` | One PNG per state, by artboard id. |
| `eq-data.js`, `support.js`, images | Runtime and samples. |

The options not chosen (1b, 2b, 3b, 3c) are not in this package.
