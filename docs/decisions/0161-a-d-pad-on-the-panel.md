# ADR-0161 — A D-pad on the panel

**Status:** **Accepted** — George, 2026-10-25, as proposed the same day.
**Built** the same day on `ph-home-assistant`, the focus's look
from his design (`design/source/19/`: the teal ring, Jump); the choices
while building delegated to Claude, below. Checked by George on sofapi and
merged into `next` for 1.6.0 when Phase 19 closed (2026-10-25). Phase 19
(`ph-home-assistant`), criterion 6. George asked for it the same day, after
trying the integration: moving around the panel with a D-pad, in both Simple
and Extended navigation, which the TV remote (HDMI-CEC) will need too.

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

## Changed after George's test with a TV remote on sofapi (2026-10-31)

The first use with the CEC plugin (ADR-0170) on a TV at 1280 x 720 found
eight things; each was found again with mocked data and real key presses
before it was changed (branches `fix-dpad-reach`, `fix-album-title`,
`fix-visualiser-size`, in the 1.10.0 preview):

18. **Left and Right go first to a control level with the focused one**:
    across it by half the smaller of the two, and no more than three times
    its height. On the equaliser Right from Back went to the first band below
    rather than the switch on the same row, and the bands take Up and Down,
    so the switch could not be reached (the bar's full-height rail is not
    level with everything, hence the height limit).
19. **A control 1 px or less across is never a stop.** Left on a queue row
    reached its Remove, kept for a keyboard at 1 x 1; the inside form then
    asked for a negative width, the ring kept the row's old size at an odd
    place, and OK would have removed the track.
20. **A control taller than the list it scrolls in** (an opened biography):
    Up and Down scroll through it, three quarters of the list at a time,
    before they leave it, and the ring goes round the part in view - it had
    gone round the whole text, over the transport.
21. **A slider's ring takes in its knob's travel** (`data-dpad-knob`), the
    same width at every value; at either end the knob stuck out through the
    ring into its arrow. With the wider ring the arrows sat on the mute icon
    and against the level, and **the arrows go, on every slider** (George,
    the same day, offered also a knob kept between the slider's ends): this
    amends 7. His earlier answer that the arrows stop moving on a press is
    folded into it.
22. **On the A-Z rail the letter lights up, teal and larger, instead of the
    ring** (George's suggestion, confirmed): the ring filled a letter 19 px
    tall. `data-dpad-ring="none"` leaves a control's look to itself, and the
    control the ring is on carries `data-dpad-focus` while it shows.
23. **In the queue, Right on a row shows Remove** (George, the same day,
    over OK opening a menu or leaving removal to touch): the row slides
    aside as a swipe does, OK removes, Left goes back, and Up and Down pass
    it by (`data-dpad-aside`). OK on the row still plays it, as a tap does.
24. Found in the same test, outside this record: a long album title pushed
    *Add to queue* under the mini player (`design/IMPLEMENTED-DIFFERENTLY.md`),
    and the visualiser kept a window the TV's return at 640 x 480 had
    shrunk ([ADR-0147](0147-a-tv-as-the-screen.md)).

**After George's second test the same evening** (CEC worked; he asked for the
ring to be checked everywhere it might cover something, and made thinner):

25. **The band is 3 px, not 6** (George: too thick).
26. **The ring lies over no letters where it can help it**: one the rule puts
    inside goes outside when inside it would cover the control's own text and
    outside none, with room on the screen. It lay over the artist page's
    Popular rows' numbers and lengths, which reach the row's edges, and the
    two lines of an album row with a guest artist. Text an ellipsis or a
    clamp has cut off does not count. Checked with mocked data on every
    screen and sheet reachable without a Lyrion server, at the TV's, the 10"
    and 7" panels' and a bar's sizes: each control's ring placed as the
    module places it (the copy checked against the real ring over 1,359 key
    presses, one differing while a row still scrolled), and the text and
    small icons under its band listed. Left: none but a queue row's Remove,
    which the check sees without the row slid aside.
