# Phase 21: the phone remote

The phone's remote for every gexis player on the network. One screen with two
pages, **Remote** and **Settings**, and a player picker above both. What the
Remote page shows depends on the player: one with a screen attached gets a
touch area to drive that screen; one without a screen gets a large cover and
larger transport.

Open `Phone Remote Board.dc.html` over HTTP from `design/`
(`cd design && python3 -m http.server 8080`, then
`/source/21/Phone Remote Board.dc.html`). The board shows the two final
phones side by side: **Living Room** (screen) and **Kitchen** (no screen).
Both are live. Switch players from the picker on either phone. The board's
tweaks set the pad each phone starts on (touchpad / D-pad) and the source
(LMS / Spotify / Bluetooth).

**High fidelity.** Every value below is extracted from
`Phone Remote v2.dc.html`. Tokens are at the end of `../../tokens.css` under
*Phase 21*. The artboard is 412 × 915; the layout is a column that takes the
phone's height, and the touch area (screen) or the cover (no screen) absorbs
the difference.

| File | What it is |
|---|---|
| `Phone Remote v2.dc.html` | The remote. Props `player` (`living` / `kitchen` / `study`), `startPad` (`touchpad` / `dpad`), `source` (`lms` / `spotify` / `bluetooth`), `eqStart` (a preset key; the board does not set it). |
| `Phone Remote Board.dc.html` | The two final phones. |
| `Settings.dc.html` | The locked Settings, an unchanged copy, embedded as the second page. |
| `eq-data.js` | Phase 20's presets and headroom rule, used by the EQ sheet. |
| `support.js`, `*.webp`, `*.svg` | Prototype runtime and images. |

`Now Playing.dc.html` and `Settings.dc.html` are unchanged.

---

## Frame

- Ground `#101a21`. Over it the blurred weave:
  `repeating-linear-gradient(38deg, #3f5a6d 0 48px, #2e4453 48px 96px)`,
  `blur(70px)`, `scale(1.14)`, inset −90px; then
  `radial-gradient(130% 105% at 20% 42%, rgba(20,33,42,0.72), rgba(13,21,28,0.96))`.
- Type: Nunito Sans; numbers and small labels IBM Plex Mono.
- No text selection, no tap highlight.

## Top bar (both layouts)

Row, padding `10px 16px 12px`, gap 10.

**Player picker** (flex 1): 54 tall, radius 16, ground
`rgba(255,255,255,0.04)`, border 1px `rgba(233,238,242,0.1)`, padding
`0 8px 0 10px`, gap 10. Pressed ground `rgba(255,255,255,0.07)`.
- `gexis-mark.svg` at 30.
- Name 16/700, one line, ellipsis.
- State 12px at `rgba(233,238,242,0.72)`: *Playing · Lyrion*, *Paused ·
  Spotify*, *Idle*. The second word is the source: Lyrion, Spotify,
  Bluetooth.
- Chevron 22 at 0.72; turns 180° while the menu is open (160ms ease).

**Player menu**: scrim `rgba(4,8,10,0.45)`; card 16 from each side, 72 from
the top, `#16232c`, border 1px `rgba(233,238,242,0.14)`, radius 18, shadow
`0 18px 48px rgba(0,0,0,0.55)`, padding `8px 0`.
- Header *Gexis players*: 11px mono, 0.2em, uppercase, 0.6, padding
  `8px 18px 6px`.
- Rows ≥ 64 tall, padding `0 18px`, gap 12: mark 30, name 16/700, state
  13px at 0.72, a 22px check in `#7ed6bc` on the current one, whose row is
  `rgba(233,238,242,0.05)`.
- Picking a player closes the menu, the EQ sheet and the typing sheet.

**Remote / Settings switch**: 54 tall, padding 3, radius 16, ground
`rgba(22,35,44,0.9)`, border 1px `rgba(233,238,242,0.12)`. Two 56-wide
icon-only segments (aria-labels *Remote*, *Settings*), glyphs 22.
- The indicator is 56 × 46, radius 13, `rgba(126,214,188,0.16)`. It slides
  56px in 300ms `cubic-bezier(0.32,0.72,0,1)`.
- Ink `#7ed6bc` selected, `rgba(233,238,242,0.72)` not; colour 200ms.
- The two pages sit side by side and the pair slides a full page in 340ms on
  the same curve.

**Settings page**: the locked Settings, mounted on the first visit, without
its bottom mini-player tray (the remote already plays). The prototype hides
the tray by making the page taller by the tray's measured height; build it as
Settings with the tray off.

---

## Remote page: a player with a screen

Column, padding `0 16px 16px`. Top to bottom: now playing, touch area, quick
actions, volume.

### Now playing (gap 12)

- **Cover** 168 × 168, radius 20, shadow `0 12px 32px rgba(0,0,0,0.4)`,
  ground `rgba(233,238,242,0.07)`. Nothing playing: a 48px note glyph at 0.5.
- **Text** beside it (gap 16), bottom-aligned, gap 4, padding-bottom 4:
  - title 22/700, line-height 1.2, up to 3 lines (nothing playing:
    *Nothing playing* at 0.6);
  - artist 16 at 0.72, up to 2 lines;
  - album 14 at 0.6, up to 2 lines.
- **Progress**: track 4 tall, radius 2, `rgba(233,238,242,0.14)`, fill
  `#7ed6bc`; times under it (gap 6), 12px mono at 0.6, elapsed left, total
  right. Display only on this layout. Hidden when nothing is playing.
- **Transport**, centred, gap 24, press `scale(0.95)`:
  - shuffle and repeat 44, circles, glyph 22. Off: ground
    `rgba(233,238,242,0.07)`, border 1px `rgba(233,238,242,0.12)`, ink
    `rgba(233,238,242,0.66)`. On: `rgba(126,214,188,0.16)`, border
    `rgba(126,214,188,0.42)`, ink `#7ed6bc`.
  - previous and next 56, ground `rgba(233,238,242,0.09)`, glyph 34.
  - play / pause 72, `#f2a48f`, ink `#16232c`, shadow
    `0 0 22px rgba(242,164,143,0.22), 0 12px 30px rgba(242,164,143,0.35)`;
    pause glyph 36, play glyph 38. Paused is the play shape alone.
  - Previous restarts the track past 3 s, otherwise goes back one.
  - Nothing playing: the row at opacity 0.38, inert.

### Touch area (margin-top 14, takes the remaining height)

Radius 26, ground `rgba(233,238,242,0.04)`, border 1px
`rgba(233,238,242,0.12)`.

**Corner buttons**, 48 circles, 10 from the edges: **Home** top left,
**Lyrics** top right, **Back** bottom left, **Meters** bottom right.
- Ground `rgba(22,35,44,0.9)`, border 1px `rgba(233,238,242,0.14)`, glyph 22,
  press `scale(0.94)`.
- Home, Lyrics and Meters turn `#7ed6bc` while the player's screen shows that
  view; otherwise `#e9eef2`.
- A press on a corner button never reaches the pad.

**Pad switch**, centred, 12 from the top: padding 3, radius 14, the same
ground and border as the Remote / Settings switch.
- Two segments 44 × 36, radius 11, glyphs 19 (aria-labels *Touchpad*,
  *D-pad*).
- The indicator is 44 × 36, radius 11, `rgba(126,214,188,0.16)`. It slides
  44px in 300ms `cubic-bezier(0.32,0.72,0,1)`.
- The pad itself swaps without animation.

**Touchpad**
- Hint, centred: *Swipe to move* / *Tap to choose*, 15px at 0.6, gap 6. It
  fades out (200ms) while a finger is down or a label is showing.
- Finger dot: 68 circle, `rgba(126,214,188,0.16)`, border 1.5px
  `rgba(126,214,188,0.6)`, under the finger; fades 160ms.
- Gesture: every **52px** of travel on the dominant axis sends one step (Up,
  Down, Left, Right) and re-anchors. A release that never stepped is a tap
  (**OK**) if it moved under 12px, otherwise one step in its direction.
- Label for what was sent: 13px mono, 0.14em, uppercase, `#7ed6bc`, centred,
  46 from the bottom, 64 in from each side. Repeats count up: *Up × 3*. It
  shows for 1 s, then fades over 220ms. Back shows its label too.

**Scroll strips** (touchpad only; hidden with the D-pad)
- Right strip: centred on the right corner buttons (right 20, width 28), from
  28% to 72% of the height. Bottom strip: centred on the bottom corner buttons
  (bottom 20, height 28), from 28% to 72% of the width.
- Each is a 1px line `rgba(233,238,242,0.07)` with a 3 × 24 thumb, radius 2,
  `rgba(233,238,242,0.18)`, centred at rest.
- While dragged the thumb follows the finger (clamped to 12–88%) and turns
  `#7ed6bc` (120ms). Every **24px** sends one scroll step on that axis.
- No label is shown.

**D-pad**
- A 216 circle, ground `rgba(233,238,242,0.06)`, border 1px
  `rgba(233,238,242,0.12)`, centred 20px below the middle (clear of the
  switch).
- Arrows (glyph 32) in zones 36% × 28%, radius 14, 3% from the rim; press
  ground `rgba(126,214,188,0.18)`.
- OK in the middle: 36% circle, `#16232c`, border 1px
  `rgba(233,238,242,0.16)`, *OK* 16/700 at 0.04em, press `scale(0.95)`.
- D-pad presses show no label.

### Quick actions (margin-top 14)

Row, gap 8. Buttons 56 × 56, radius 18, glyph 22 (stroke 2, round), no text,
press `scale(0.97)`.
- Left: **Standby** (crescent moon), then **Idle screen** (clock).
- Right, pushed over by the free space: **Playing**, **Room** (bulb).
- Off: ground `rgba(233,238,242,0.07)`, border 1px `rgba(233,238,242,0.1)`,
  ink `#e9eef2`. On (the screen's current view, or standby engaged):
  `rgba(126,214,188,0.16)`, border `rgba(126,214,188,0.55)`, ink `#7ed6bc`.
- Standby puts the player's **screen** to sleep; it does not turn the player
  off. While it is on, the view buttons drop to 0.45. Any view button, corner
  button or pad input wakes the screen.
- Aria-labels: *Standby* (*Screen on* while in standby), *Idle screen*,
  *Playing*, *Room*.

### Volume (margin-top 12, at the bottom)

Row, gap 10: the bar (flex 1), then the EQ button.

**Bar**: 36 tall, radius 12, ground `rgba(233,238,242,0.08)`.
- Fill `#7ed6bc` from the left to the level; muted, the fill drops to 0.35.
- Tap or drag anywhere on it sets the level (0–100 from the x position) and
  unmutes.
- **Mute** inside, 4 from the left: 32 × 32, radius 10, speaker glyph 24
  (crossed when muted). Ink `#0d151c` while the fill covers it (level > 14,
  not muted), otherwise `#e9eef2`.
- **Level** 16 from the right: 16px mono 600; *Off* when muted. Ink
  `#0d151c` past 86, otherwise `#e9eef2`.
- **EQ name** centred between 44 (left) and 52 (right): *EQ* 11px mono at
  0.14em, then the preset name 13/700, gap 6, one line, ellipsis.
  - Ink `#7ed6bc` with the EQ on; `rgba(233,238,242,0.72)` and the word
    *Off* with it off.
  - A second copy in `#0d151c` sits on top, clipped to the fill
    (`clip-path: inset(0 calc(100% − level%) 0 0)`), so the part over the
    fill reads dark. Muted, the dark copy is hidden.
  - The name is a label. A touch on it sets the volume like the rest of the
    bar.

**EQ button**: 56 × 56, radius 18, three-slider glyph 22. Opens the EQ sheet.
- On: ground `rgba(126,214,188,0.12)`, border 1px `rgba(126,214,188,0.45)`,
  ink `#7ed6bc`.
- Off: ground `rgba(233,238,242,0.07)`, border `rgba(233,238,242,0.14)`, ink
  `rgba(233,238,242,0.82)`.

---

## Remote page: a player without a screen

No touch area and no quick actions: there is no screen to drive. Same top
bar, same volume row and EQ button.

- **Cover**, centred in the space between the top bar and the title: that
  space is flex 1 with margin `6px 0 18px`. The cover is square, the space's
  height up to 380, never wider than the column, radius 24, shadow
  `0 18px 48px rgba(0,0,0,0.5)`.
- **Title** 26/700, −0.01em, centred; under it (gap 4) artist · album, 17px
  at 0.72, on one line.
- **Seek bar** (margin-top 14): a 28-tall touch band; track 6 tall, radius
  3, fill `#7ed6bc`; knob 18, `#e9eef2`, shadow `0 1px 4px rgba(0,0,0,0.4)`.
  Drag or tap to seek. Times below, 12px mono at 0.6.
- **Transport** (margin-top 10), centred, gap 18: shuffle and repeat 48 (glyph
  24), previous and next 64 (glyph 38), play 84 (pause glyph 40, play 42).
  Colours as above.
- **Volume row** (margin-top 16): as above.

---

## Sources

As on the panel (`design/README.md`, *Source differences*): unsupported
controls are removed, not disabled.
- **LMS**: everything.
- **Spotify**: no shuffle or repeat; the transport re-centres.
- **Bluetooth**: no shuffle or repeat, and no duration. The progress track
  becomes the inert rule
  `linear-gradient(90deg, rgba(233,238,242,0), rgba(233,238,242,0.15) 16%, rgba(233,238,242,0.15) 84%, rgba(233,238,242,0))`,
  the seek knob is hidden and the bar does not respond. The end time reads
  *live*.

**Nothing playing** (the board's *Study* player): state *Idle*; the cover's
note glyph; *Nothing playing* at 0.6; no progress; transport at 0.38, inert.

---

## Sheets

**EQ sheet**
- Scrim `rgba(4,8,10,0.55)`, fades 260ms. The sheet is `#16232c`, border-top
  1px `rgba(233,238,242,0.16)`, radius `24px 24px 0 0`, padding
  `10px 16px 22px`, gap 14, shadow `0 -10px 32px rgba(0,0,0,0.6)`. It slides
  up in 300ms `cubic-bezier(0.32,0.72,0,1)`.
- Handle 36 × 4, radius 2, `rgba(233,238,242,0.24)`; a tap on it or the scrim
  closes the sheet.
- *Equaliser* 19/700. Under it, 13px mono at 0.06em, 0.72: *{name} · preset*,
  *{name} · yours*, or *Off · bit-perfect*.
- On/off switch, in a 48-tall box (padding `0 10px`, radius 14, ground
  `rgba(255,255,255,0.05)`, border `rgba(233,238,242,0.1)`): track 56 × 32.
  - On: `rgba(126,214,188,0.32)`, border `rgba(126,214,188,0.5)`, knob 24
    `#7ed6bc` at 27.
  - Off: `rgba(233,238,242,0.08)`, border `rgba(233,238,242,0.16)`, knob at
    0.6 at 3.
  - Both move in 140ms.
- Settings as chips that scroll sideways, edges faded (mask 16px left, 40px
  right): 44 tall, radius 12, 15/600, gap 6.
  - Selected: `rgba(126,214,188,0.16)`, border `rgba(126,214,188,0.55)`, ink
    `#7ed6bc`. Others: ground 0.07, border 0.12.
  - The ten presets first, a 1px divider, then the owner's own.
  - Off: the chips at 0.4, inert.
  - A tap applies the setting at once.
- Note, 14px / 1.4 at 0.6:
  - EQ off: *Off. The sound is untouched, bit-perfect.*
  - On with headroom: *Lowered by {x} so the boost cannot clip.* (Phase 20's
    headroom rule, `eq-data.js`).
  - On with no boost: *No boost, so nothing is lowered.*
- *Edit bands in Settings*: 48 tall, radius 14, ground
  `rgba(233,238,242,0.07)`, border `rgba(233,238,242,0.14)`, 16/600, with a
  chevron. It closes the sheet and moves to the Settings page.

**Typing sheet**
- Appears when a text field is focused on the player's screen. The phone's
  own keyboard types straight into that field; the sheet carries no field of
  its own.
- `#16232c`, border-top `rgba(233,238,242,0.16)`, radius `20px 20px 0 0`,
  padding `14px 16px 18px`, shadow `0 -10px 32px rgba(0,0,0,0.6)`; slides
  260ms on the same curve.
- *Typing on the player's screen*: 11px mono, 0.2em, uppercase, 0.6.
- **Done**: 50 tall, padding `0 20px`, radius 14, `#7ed6bc`, ink `#0d151c`,
  16/700.
- The prototype has no trigger for it; it is drawn closed.

---

## State and data

Per player: `has_screen`, name, status (playing / paused / idle), source,
track (title, artist, album, artwork, position, duration), volume percent,
muted, EQ on, EQ setting. For a player with a screen, also: the screen's
current view (home, playing, lyrics, meters, room, idle) and standby.

Remote-local: page (remote / settings), current player, pad (touchpad /
D-pad; the first one comes from the `startPad` setting), menu and sheets open.

Commands: step up / down / left / right, ok, back; scroll step vertical /
horizontal; go to view; standby on / off; volume set, mute; EQ on / off,
choose setting; transport. Check each against `../../data-contract.md` and
add what is missing there, marked NEW.

---

## Open

- **Touch floor.** The volume bar is 36 tall and the mute button inside it
  32 × 32, both under the 44 px floor. Drawn this way on request; confirm.
- **Bluetooth artwork.** The prototype still shows the sample cover with
  Bluetooth. Follow the panel: Bluetooth has no artwork (the pending glyph).
- **Repeat.** The remote toggles repeat on and off; the panel cycles off →
  all → one. Not decided for the phone.
- **Fixed volume.** The panel replaces the slider with its padlock row; not
  drawn on the remote.
- **Typing sheet trigger** needs a field-focus event from the player.

Sample data in the prototype (tracks, players, owner settings) is
illustrative.
