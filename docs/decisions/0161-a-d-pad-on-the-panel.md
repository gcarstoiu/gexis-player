# ADR-0161 — A D-pad on the panel

**Status:** **Proposed** — 2026-10-25. Phase 19 (`ph-home-assistant`),
criterion 6. George asked for it the same day, after trying the integration:
moving around the panel with a D-pad, in both Simple and Extended navigation,
which the TV remote (HDMI-CEC) will need too. Nothing built.

## Context

- **The panel is made for touch.** Nothing in `ui/src` answers an arrow key
  (2026-10-25); a few controls answer Enter or Space. In Chromium, Tab moves
  between controls in page order and the arrows scroll.
- **Input today:** a finger; the phone's touchpad (ADR-0121), whose pointer
  and taps are made up inside the page; and, over a page from another site
  in a frame (the dashboard, ADR-0156), real taps and key presses from the
  core's virtual touchscreen and keyboard through `/dev/uinput` (ADR-0157,
  `POST /panel/input`, marked internal).
- **Asks through the live state** (`/panel/go`: Home, Now Playing, Lyrics;
  ADR-0101) are one numbered request, and the panel acts on the latest.
  Right for "go to Home"; presses close together would fold into one.
- **What a D-pad must reach:** Home (Simple navigation: the library's tiles;
  Extended: Lyrion's own menus as well, ADR-0118), the library's lists and
  grids, Now Playing and its tabs, Settings and its sheets, the volume
  drawer; on a bar, the rail, the tray, the library and Now Playing. Every
  screen shape, 7" to 13.3", bars and DSI.
- **HDMI-CEC, later:** Linux's CEC framework can pass a TV remote's keys on
  as key presses of an input device (the `rc-cec` keymap). Not tried on a Pi.

## Decisions (proposed)

**D1 — Real key presses, one handler.** A D-pad press becomes a key press on
the core's virtual keyboard (ADR-0157): an arrow, Enter or Escape. The page
listens for keys, so one handler answers Home Assistant, a USB keyboard and,
later, a TV remote over CEC. Over the dashboard's frame the keys reach Home
Assistant's own page, as the phone's typing does. *Rejected:* a request in
the live state - presses close together fold into one, it cannot reach into
the frame, and CEC would need a path of its own.

**D2 — Six keys, plus Home.**
- **Up, Down, Left, Right** move the focus (D3).
- **OK** presses the focused control, as a tap does.
- **Back** goes one step back: it closes the topmost sheet, drawer, tray or
  dialog; otherwise it goes up one level in the library or Lyrion's menus;
  otherwise, on Now Playing, it minimises back to where you were
  (ADR-0122). On Home it does nothing. Over the dashboard it takes the dashboard down.
- **Home** is the route that exists, `/panel/go/home`.

**D3 — The focus moves by position.** The next control in the pressed
direction, measured on the screen, within the topmost layer (sheet, drawer,
tray, dialog); the focused control is scrolled into view. One rule for every
screen and shape, and a new screen needs nothing added. Exceptions are per
control: on a slider, Left and Right change its value and Up and Down leave
it; on a bar, Up from the top row opens the tray, as pulling it down does.
*Rejected:* a focus order written for each screen - exact, but one per
screen and layout, kept up by hand.

**D4 — Where the focus starts, and when it shows.** Hidden until the first
press. That press shows it on the control focused last on this screen, or on
its main one: Play/Pause on Now Playing, the first item on Home and in a
list, the first row in a sheet. A touch hides it; the next press shows it
again where it was. While the visualiser, the idle screen or display standby
is up, a press only wakes the panel, as a first touch does.

**D5 — How the focus looks is designed** (George, in Claude Design): seen from
across the room, on every background and wallpaper, and on the bar. Built from
the design and checked against its picture.

**D6 — The API.** `POST /panel/key` with `{"key": "up" | "down" | "left" |
"right" | "ok" | "back"}`, marked stable, attention first as `/panel/go` is;
refused on a player without a screen. `/panel/input` stays internal. A player
without the route answers 404, and Home Assistant asks for the player to be
updated.

**D7 — Home Assistant: a remote.** One `remote` entity per player with a
screen. `remote.send_command` takes `up`, `down`, `left`, `right`, `ok`,
`back` and `home`, with the repeats and delay of Home Assistant's own
service; on while the screen is lit. The dashboard card (its own ADR) draws
the D-pad over it. *Rejected:* six buttons per player - six more entities
each, and one tile per key on a dashboard.

**D8 — Left out:** setup, first use and the update screens, which the phone
drives; a D-pad on the phone page.

## Settings (ADR-0022)

None proposed.

## To check before it is called done

- Every screen and sheet reached and left with the keys alone, at the
  panel's and both bars' sizes, in Simple and Extended navigation, with
  mocked data (criterion 6).
- Keys from the virtual keyboard reach the page when no touch has come first.
- What Home Assistant's page does with the arrows inside the frame.
- CEC, when its phase comes.
