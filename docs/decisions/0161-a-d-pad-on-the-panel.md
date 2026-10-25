# ADR-0161 — A D-pad on the panel

**Status:** **Accepted** — George, 2026-10-25, as proposed the same day.
**Built** the same day on `ph-home-assistant` (not merged), the focus's look
from his design (`design/source/19/`: the teal ring, Jump); the choices
while building delegated to Claude, below. Phase 19 (`ph-home-assistant`),
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

## Decisions

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

## Decisions taken while building (Claude, delegated by George, 2026-10-25)

**The page (`ui/src/lib/dpad.js`)**
1. **The first press shows, and does not move**: an arrow or OK with the
   ring hidden only shows it. Back acts at once - closing what is open is
   what it is pressed for.
2. **The topmost layer** is the last one shown of `role="dialog"` and
   `data-dpad-layer` (the volume drawer, the bar's tray, the queue, the
   library's playlist sheet, the dashboard); a layer closing or closed -
   still fading - counts for nothing.
3. **The next control by position**: in the pressed direction, the smallest
   gap along it plus three times the gap across it (0 when they overlap),
   centres as the tie-break. Controls out of sight count only inside a
   list that scrolls, which is then scrolled to keep 24 px clear.
4. **Where a screen starts**: the control used last in that layer; else its
   `data-dpad-main` (Play/Pause on Now Playing and the bar, the drawer's
   slider, the tray's Home); else the first in reading order inside its
   `data-dpad-start` (the library's content, the bar library's, Settings'
   body); else the first on the screen. After OK opened a screen, the ring
   appears on its start by itself.
5. **Back returns to what opened**: the control OK pressed, when the screen
   changed under it, is remembered by its name; Back looks for it on the
   screen it comes back to (screens are drawn anew).
6. **Back's target**: the layer's own `dpadback` handler (drawer, tray,
   queue, sheets, dashboard), else the last shown `data-dpad-back` (a
   screen's Back, Now Playing's Minimise, a confirmation's Cancel).
7. **The ring's two forms**, as the design: outside, round staying round;
   inside on rows and wherever a neighbour is under 12 px or the ring would
   leave the screen; `data-dpad-ring` sets it where the rule would not. A
   slider is ringed whole with its two arrows;
   the bar tray's, whose touch area is taller than it draws, round its rail
   and knob (`data-dpad-box`).
8. **Sliders**: Left and Right step - the volume 2 %, as the phone's
   touchpad does; a Settings slider its own step, saved once the presses
   stop (400 ms).
9. **What a press counts as**: attention, as a touch; on the idle screen or
   a dark screen it only wakes. Untrusted (made-up) key events are ignored,
   so the phone's own typing over the dashboard is not taken for OK.
10. **The dashboard's frame takes the keyboard**: the first press over it
    moves the keyboard into Home Assistant's page and draws no ring there.
11. **Left out (D8)**: setup, settling, the update screens and the factory
    reset carry `data-dpad-off`.

**The core**
12. **Only a screen known to be off swallows a press**: after a restart the
    output's state is unknown, and a lit screen must not lose the first one.

## Changed after George's check on sofapi (2026-10-25)

He found the ring drawn over the idle screen, left behind for a moment by a
volume drawer that had already faded, and kept by a tap on the phone's
touchpad. Each was found again with mocked data and real key presses, and
fixed:

13. **A screen over everything hides the ring** (`data-dpad-cover`: the idle
    screen, a takeover's). A press there only takes it down; the next shows
    the ring.
14. **A layer that closes takes the ring at once**: the page is watched as it
    changes, not only four times a second, and the ring lands on the control
    beneath 150 ms later. Measured on the volume drawer: gone on the next
    frame, back at 167 ms, the drawer's fade ending at about 210 ms; before,
    the ring stayed until 233 ms.
15. **The phone's touchpad hides the ring**, a move as well as a tap: its
    pointer is then the one in use.
16. **A dashboard that comes up by itself** takes the ring away too, as a
    press over it does (10).
17. **The D-pad does not move inside the Home Assistant dashboard** (George,
    2026-10-25, asked whether it should): Back takes the dashboard down; the
    arrows and OK go to Home Assistant's page as they are. Turning the
    arrows into Tab was offered and not taken - Home Assistant's order, not
    the direction pressed, and its own thin outline.

