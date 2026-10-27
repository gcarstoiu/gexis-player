# Phase 21: the phone remote

The phone's remote for every gexis player on the network. One screen with two
pages, **Remote** and **Settings**, and a player picker above both. What the
Remote page shows depends on the player: one with a screen attached gets a
trackpad (or D-pad) to drive that screen; one without a screen gets a large
cover and larger transport.

Open `Phone Remote Board.dc.html` over HTTP from `design/`
(`cd design && python3 -m http.server 8080`, then
`/source/21/Phone Remote Board.dc.html`). The board shows the two phones in
Pixel 10 Pro frames: **Living Room** (screen) and **Kitchen** (no screen).
Both are live. Switch players from the picker on either phone. The board's
tweaks set the starting pad (touchpad / D-pad), the volume mode (variable /
fixed), the source (LMS / Spotify / Bluetooth).

**High fidelity.** Every value below is extracted from
`Phone Remote v3.dc.html`. Tokens are at the end of `../../tokens.css` under
*Phase 21*.

| File | What it is |
|---|---|
| `Phone Remote v3.dc.html` | The remote. Props `player` (`living` / `kitchen` / `study`), `startPad` (`touchpad` / `dpad`), `source` (`lms` / `spotify` / `bluetooth`), `volume` (`variable` / `fixed`), `eqStart` (a preset key; the board does not set it). |
| `Phone Remote Board.dc.html` | The two phones in Pixel 10 Pro frames. |
| `Settings.dc.html` | The locked Settings, an unchanged copy, embedded as the second page. |
| `eq-data.js` | Phase 20's presets and headroom rule, used by the EQ sheet. |
| `support.js`, `*.webp`, `*.svg` | Prototype runtime and images. |

`Now Playing.dc.html` and `Settings.dc.html` are unchanged. One panel
behaviour change is decided but not made, because the panel is locked: see
*Fixed volume*.

---

## Size

- **Target:** Pixel 10 Pro in Chrome with the address bar showing. The
  screen is 410 × 914 CSS px; the status bar (52), the address bar (58) and
  the gesture bar (24) leave **410 × 780**. Everything must fit in 780.
- **Taller:** the remote fills the height it gets, never less than 780. On a
  player with a screen the touch area takes the extra; without a screen the
  cover takes it, up to its 380 cap.
- **Width:** up to 412, down to **360**. On a player with a screen the cover
  shrinks (to 96 at the least) before anything else; the transport keeps
  44 / 56 / 44. Everything else fits at 360 as drawn.

## Frame

The panel's background, layer for layer:
- Ground `#101a21`.
- The weave: `repeating-linear-gradient(38deg, #3f5a6d 0 48px, #2e4453 48px 96px)`,
  `blur(70px)`, `scale(1.14)`, inset −90px.
- With artwork: the cover image, inset −120px, `blur(72px) saturate(1.7)`,
  `scale(1.12)`. Bluetooth and nothing playing: no image, the plain weave.
- Veil: `radial-gradient(130% 105% at 20% 42%, rgba(22,36,46,0.3), rgba(14,23,30,0.86))`.
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
  Spotify*, *Idle*. The second word is the source.
- Chevron 22 at 0.72; turns 180° while the menu is open (160ms ease).

**Player menu**: scrim `rgba(4,8,10,0.45)`; card 16 from each side, 72 from
the top, `#16232c`, border 1px `rgba(233,238,242,0.14)`, radius 18, shadow
`0 18px 48px rgba(0,0,0,0.55)`, padding `8px 0`.
- Header *Gexis players*: 11px mono, 0.2em, uppercase, 0.6, padding
  `8px 18px 6px`.
- Rows ≥ 64 tall, padding `0 18px`, gap 12: mark 30, name 16/700, state
  13px at 0.72, a 22px check in `#7ed6bc` on the current one, whose row is
  `rgba(233,238,242,0.05)`.
- Picking a player closes the menu and the EQ sheet.

**Remote / Settings switch**: 54 tall, padding 3, radius 16, ground
`rgba(22,35,44,0.9)`, border 1px `rgba(233,238,242,0.12)`. Two 56-wide
icon-only segments (aria-labels *Remote*, *Settings*), glyphs 22.
- Indicator 56 × 46, radius 13, `rgba(126,214,188,0.16)`; slides 56px in
  300ms `cubic-bezier(0.32,0.72,0,1)`.
- Ink `#7ed6bc` selected, `rgba(233,238,242,0.72)` not; colour 200ms.
- The two pages sit side by side; the pair slides a full page in 340ms on
  the same curve.

**Settings page**: the locked Settings, mounted on the first visit, without
its bottom mini-player tray. The prototype hides the tray by making the page
taller by the tray's measured height; build it as Settings with the tray off.

---

## Remote page: a player with a screen

Column, padding `0 16px 16px`. Top to bottom: now playing, progress, touch
area, quick actions, volume. Shuffle and repeat are not on the phone.

### Now playing (row, gap 16)

**Cover**: 136 square (shrinks to 96 on narrow phones), radius 18, shadow
`0 12px 32px rgba(0,0,0,0.4)`, ground `rgba(233,238,242,0.07)`, inner ring
1px `rgba(255,255,255,0.08)`.
- Bluetooth: the panel's *artwork pending* glyph, scaled: ground
  `linear-gradient(160deg, rgba(126,214,188,0.07), rgba(242,164,143,0.06))`
  over `#17242d`; a 48 ring, border 2px `rgba(126,214,188,0.4)`, with a 12
  dot `rgba(126,214,188,0.45)`; *artwork pending* 10px mono, 0.12em,
  uppercase, 0.6; gap 10.
- Nothing playing: a 44px note glyph at 0.5.

**Beside the cover** (flex `1 0 168px`, never under 168): a column, top and
bottom pinned (space-between), gap 10, padding `2px 0`.
- Title 20/700, line-height 1.2, up to 2 lines. Nothing playing: *Nothing
  playing* at 0.6.
- Artist 15px at 0.72, one line, ellipsis. Hidden when nothing is playing.
- **Transport**, at the bottom, centred, gap 12, press `scale(0.95)`:
  - previous and next 44, ground `rgba(233,238,242,0.09)`, glyph 26;
  - play / pause 56, `#f2a48f`, ink `#16232c`, shadow
    `0 0 22px rgba(242,164,143,0.22), 0 12px 30px rgba(242,164,143,0.35)`;
    pause glyph 28, play glyph 30. Paused is the play shape alone.
  - Previous restarts the track past 3 s, otherwise goes back one.
  - Nothing playing: opacity 0.38, inert.

### Progress (margin-top 12, gap 6)

Track 4 tall, radius 2, `rgba(233,238,242,0.14)`, fill `#7ed6bc`. Times
under it, 12px mono, line-height 16, at 0.6: elapsed left, total right.
Display only. Nothing playing: at 0.38, *0:00 / 0:00*.

### Touch area (margin-top 12, flex 1)

Radius 26, ground `rgba(233,238,242,0.04)`, border 1px
`rgba(233,238,242,0.12)`.

**Trackpad** (default)
- Drives a **pointer** on the player's screen, **relative**, like a laptop
  trackpad: the pointer moves by the finger's travel, from wherever it is.
- Gestures (tap, and the rest) are the ones the panel already defines.
- **No feedback on the phone**: no finger dot, no sent label, no hint text.
  The pointer on the player's screen is the feedback.

**Scroll strips** (trackpad only)
- Right strip: right 20, width 28, from 28% to 72% of the height. Bottom
  strip: bottom 20, height 28, from 28% to 72% of the width.
- Each is a 1px line `rgba(233,238,242,0.07)` with a 3 × 24 mark, radius 2,
  `rgba(233,238,242,0.18)`, centred.
- **Static**: nothing moves or changes colour while dragging. Every 24px of
  drag along a strip sends one scroll step on that axis.

**D-pad** (the other mode)
- A 216 circle, ground `rgba(233,238,242,0.06)`, border 1px
  `rgba(233,238,242,0.12)`, centred 20px below the middle (clear of the
  switch).
- Arrows (glyph 32) in zones 36% × 28%, radius 14, 3% from the rim; press
  ground `rgba(126,214,188,0.18)`.
- OK in the middle: 36% circle, `#16232c`, border 1px
  `rgba(233,238,242,0.16)`, *OK* 16/700 at 0.04em, press `scale(0.95)`.
- No strips in this mode.

**Corner buttons** (both modes), 48 circles, 10 from the edges: **Home** top
left, **Lyrics** top right, **Back** bottom left, **Meters** bottom right.
- Ground `rgba(22,35,44,0.9)`, border 1px `rgba(233,238,242,0.14)`, glyph 22,
  press `scale(0.94)`.
- Home, Lyrics and Meters turn `#7ed6bc` while the player's screen shows that
  view; otherwise `#e9eef2`.

**Pad switch**, centred, 12 from the top: padding 3, radius 14, ground and
border as the Remote / Settings switch. Two segments 44 × 36, radius 11,
glyphs 19 (aria-labels *Trackpad*, *D-pad*). Indicator 44 × 36, radius 11,
`rgba(126,214,188,0.16)`, slides 44px in 300ms. The pad itself swaps
without animation.

### Quick actions (margin-top 12)

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
  - A second copy in `#0d151c` sits on top, clipped to the fill, so the part
    over the fill reads dark. Muted, the dark copy is hidden.
- The bar (36) and mute (32) are under the 44 px floor. Confirmed: keep.

**EQ button**: 56 × 56, radius 18, three-slider glyph 22. Opens the EQ sheet.
- On: ground `rgba(126,214,188,0.12)`, border 1px `rgba(126,214,188,0.45)`,
  ink `#7ed6bc`.
- Off: ground `rgba(233,238,242,0.07)`, border `rgba(233,238,242,0.14)`, ink
  `rgba(233,238,242,0.82)`.

---

## Remote page: a player without a screen

No touch area and no quick actions. Same top bar, volume row and EQ button.
Shuffle and repeat are not on the phone.

- **Cover**, centred in the space between the top bar and the title (flex 1,
  margin `6px 0 18px`): square, the space's height up to 380, never wider
  than the column, radius 24, shadow `0 18px 48px rgba(0,0,0,0.5)`, inner
  ring as above. Bluetooth: the panel's pending glyph at full size (110 ring,
  26 dot, label 13px at 0.16em, gap 20). Nothing playing: a 72px note at 0.5.
- **Title** 26/700, −0.01em, centred; under it (gap 4) artist · album, 17px
  at 0.72. Hidden when nothing is playing.
- **Seek bar** (margin-top 14): a 28-tall touch band; track 6 tall, radius
  3, fill `#7ed6bc`; knob 18, `#e9eef2`, shadow `0 1px 4px rgba(0,0,0,0.4)`.
  Drag or tap to seek. Times below, 12px mono at 0.6.
- **Transport** (margin-top 10), centred, gap 24: previous and next 64 (glyph
  38), play 84 (pause glyph 40, play 42). Colours as above.
- **Volume row** (margin-top 16): as above.
- Nothing playing: seek, times and transport at 0.38, inert.

---

## Fixed volume

When the player's output is fixed (the level is set on the amplifier), the
bar becomes a locked row, as on the panel:
- 36 tall, radius 12, ground `rgba(233,238,242,0.05)`, border 1px
  `rgba(233,238,242,0.12)`, padding `0 15px 0 44px`, gap 9.
- **Mute** stays, 32 × 32 at 3 from the left, ink `#e9eef2`, glyph crossed
  when muted.
- Padlock 14 × 16 at `rgba(233,238,242,0.7)` (shackle 10 × 8, border 2px;
  body 14 × 9, radius 2.5).
- *Fixed output* 14/600, one line, ellipsis.
- Right: the EQ name in the bar's style (*EQ* 11px mono, name 13/700),
  `#7ed6bc` with the EQ on, 0.72 and *Off* with it off.

**Mute works in fixed mode.** It silences the output. This is new for the
panel too: today the panel ignores mute when the output is fixed. The panel
must follow; `Now Playing.dc.html` is locked, so this is a build change,
not drawn there.

## Sources

As on the panel: unsupported controls are removed, not disabled.
- **LMS** and **Spotify**: everything on the phone.
- **Bluetooth**: no artwork (the pending glyph; the background is the plain
  weave) and no duration. The progress track becomes the inert rule
  `linear-gradient(90deg, rgba(233,238,242,0), rgba(233,238,242,0.15) 16%, rgba(233,238,242,0.15) 84%, rgba(233,238,242,0))`,
  the seek knob is hidden and the bar does not respond. The end time reads
  *live*.

**Nothing playing** (the board's *Study* player): state *Idle*; the cover's
note glyph; *Nothing playing* at 0.6; transport at 0.38, inert.

## Typing

A tap on the trackpad (or OK on the D-pad) that lands in a text field on the
player's screen opens the phone's own keyboard (Android or iOS), as the
current implementation already does. Keep that behaviour. The remote has no
keyboard, typing sheet or keyboard button of its own.

## EQ sheet

- Scrim `rgba(4,8,10,0.55)`, fades 260ms. Sheet `#16232c`, border-top 1px
  `rgba(233,238,242,0.16)`, radius `24px 24px 0 0`, padding `10px 16px 22px`,
  gap 14, shadow `0 -10px 32px rgba(0,0,0,0.6)`; slides up in 300ms
  `cubic-bezier(0.32,0.72,0,1)`.
- Handle 36 × 4, radius 2, `rgba(233,238,242,0.24)`; a tap on it or the scrim
  closes the sheet.
- *Equaliser* 19/700. Under it, 13px mono at 0.06em, 0.72: *{name} · preset*,
  *{name} · yours*, or *Off · bit-perfect*.
- On/off switch in a 48-tall box (padding `0 10px`, radius 14, ground
  `rgba(255,255,255,0.05)`, border `rgba(233,238,242,0.1)`): track 56 × 32.
  On: `rgba(126,214,188,0.32)`, border `rgba(126,214,188,0.5)`, knob 24
  `#7ed6bc` at 27. Off: `rgba(233,238,242,0.08)`, border
  `rgba(233,238,242,0.16)`, knob at 0.6 at 3. Both move in 140ms.
- Settings as chips that scroll sideways, edges faded (mask 16px left, 40px
  right): 44 tall, radius 12, 15/600, gap 6. Selected:
  `rgba(126,214,188,0.16)`, border `rgba(126,214,188,0.55)`, ink `#7ed6bc`.
  Others: ground 0.07, border 0.12. The ten presets first, a 1px divider,
  then the owner's own. EQ off: the chips at 0.4, inert. A tap applies the
  setting at once.
- Note, 14px / 1.4 at 0.6: *Off. The sound is untouched, bit-perfect.* /
  *Lowered by {x} so the boost cannot clip.* (Phase 20's headroom rule,
  `eq-data.js`) / *No boost, so nothing is lowered.*
- *Edit bands in Settings*: 48 tall, radius 14, ground
  `rgba(233,238,242,0.07)`, border `rgba(233,238,242,0.14)`, 16/600, with a
  chevron. Closes the sheet and moves to the Settings page.

---

## State and data

Per player: `has_screen`, name, status (playing / paused / idle), source,
track (title, artist, album, artwork, position, duration), volume percent,
muted, volume mode (variable / fixed), EQ on, EQ setting. For a player with
a screen, also: the screen's current view (home, playing, lyrics, meters,
room, idle) and standby.

Remote-local: page (remote / settings), current player, pad (trackpad /
D-pad; the first comes from `startPad`), menu and EQ sheet open.

Commands: pointer move (relative dx, dy) and the panel's trackpad gestures;
D-pad up / down / left / right, ok, back; scroll step vertical / horizontal;
go to view; standby on / off; volume set; mute (also in fixed mode); EQ on /
off, choose setting; transport; text input to the focused field. Check each
against `../../data-contract.md` and add what is missing there, marked NEW.

## Open for the build

- **Panel mute in fixed mode**: the panel's behaviour changes to match; the
  locked design file is not edited.

Sample data in the prototype (tracks, players, owner settings) is
illustrative.
