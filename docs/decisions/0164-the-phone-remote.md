# ADR-0164 — The phone remote

**Status:** **Built** 2026-10-27 on `ph-phone-controls` from the second
design (below, *Built (2026-10-27)*) and previewed on sofapi.
**Accepted, revised** — George, 2026-10-27: Claude Design's
second remote (`design/source/21`, `Phone Remote v3`) replaces the first;
build it, with his answers to the three points where it left the current
build (below). The decisions he left to Claude are listed under *Claude's
decisions* for his confirmation. Phase 21 (`ph-phone-controls`).
**First design** — accepted 2026-10-26, built on `ph-phone-controls` and
previewed on sofapi the same evening; George found that Claude Design had
got the remote wrong (its touchpad sent D-pad steps by swipes, where he had
asked for a touchpad and a D-pad), and fresh designs followed. What the
first build kept and dropped is under *From the first build*.

Replaces [ADR-0101](0101-a-mini-player-on-the-phone.md)'s mini player on
the phone; keeps [ADR-0121](0121-the-phone-as-the-panel-s-touchpad-and-keyboard.md)'s
touchpad and keyboard, now on the remote. Builds on
[ADR-0037](0037-transport-commands.md) (what a renderer declares),
[ADR-0135](0135-display-standby.md) (standby),
[ADR-0136](0136-switching-between-players-on-the-phone.md) (the players on the
network), [ADR-0161](0161-a-d-pad-on-the-panel.md) (the D-pad),
[ADR-0162](0162-a-simple-equaliser.md) (the equaliser's quick change) and
[ADR-0165](0165-mute-with-fixed-output.md) (mute with Fixed volume).

## Context

The phone page is Settings with a mini player pinned under it (ADR-0101):
the track and play/pause, the panel's row (*Screen off*, Home, Playing,
Lyrics, Meters, Room, Idle), the volume and, from Phase 20, the EQ button.
Swiped up, it opens the touchpad between the track and the row (ADR-0121).
A player without a screen gets the same page, its panel row included.
George added Phase 21 on 2026-10-26 for a redesign of the quick actions and
the touchpad.

## Decided (George, 2026-10-26 and 2026-10-27)

1. **One remote, two pages** (`design/source/21/README.md`): a player
   picker and a Remote / Settings switch on top; the Remote page, and
   Settings as it is, without the mini player. The mini player goes from
   the phone.
2. **A player with a screen**: now playing - a 136 px cover beside the
   title, the artist and previous / play / next, the progress under both -
   then a touch area, quick actions and the volume row. **No shuffle or
   repeat on the phone**, in either layout; the panel keeps them.
3. **Two pads, and a switch between them.** **Trackpad**: drives the
   panel's pointer, relative, as a laptop's touchpad, with ADR-0121's
   gestures (move, tap, two fingers to scroll, a pinch); nothing is drawn
   on the phone, the pointer on the player's screen is the feedback.
   Scroll strips along its right and bottom edges, drawn still: **each
   24 px of drag scrolls what is under the pointer by those 24 px**, scaled
   as two fingers are - the content follows the finger, as the old phone
   page's scroll lines did (George, 2026-10-27, asked). **D-pad**: the
   arrows and OK as buttons, driving the panel's ring (ADR-0161); no
   strips. Four corner buttons on both: Home, Lyrics, Back, Meters.
4. **Quick actions**: Standby (the screen, ADR-0135), Idle screen, Playing,
   Room.
5. **A player without a screen**: a large cover, a seek bar, larger
   transport and the volume row; no touch area and no quick actions.
6. **The volume row**: a bar with mute inside it, the level and the EQ
   setting's name, then the EQ button, which opens the EQ sheet. **Its
   touch sizes as drawn** (the bar 36 px tall, mute 32 x 32), under the
   44 px floor (George, 2026-10-26; the second design keeps it). **With
   Fixed volume** the bar becomes the panel's locked row - mute, the
   padlock, *Fixed output*, the EQ name - and mute works there
   (ADR-0165).
7. **Typing**: a trackpad tap on a text field on the player's screen, or
   OK with the ring on one, opens the phone's own keyboard. The remote has
   no keyboard, typing sheet or keyboard button of its own.
8. **Sources as on the panel**: what a renderer does not declare is left
   out (ADR-0037); no cover is the panel's *artwork pending* glyph, and no
   duration (Bluetooth) the inert rule and *live*.
9. **The panel's background**: the weave, the blurred cover where there is
   one, the veil.
10. **Size**: drawn at 410 x 780 (a Pixel 10 Pro in Chrome with the address
    bar showing), 360 to 412 wide. Taller, the touch area (or, without a
    screen, the cover, up to 380) takes the extra. **Shorter, they give way
    first**, down to a floor that keeps the D-pad whole, and only then does
    the page scroll (George, 2026-10-27, asked: the design never went below
    780, which many phones are).
11. **The Home Assistant card follows the redesign**
    ([ADR-0163](0163-a-gexis-player-card-for-dashboards.md)): Standby added
    and the views grouped as on the phone, in the integration's next
    release, after the phone. George sees it before it is released.

## Claude's decisions (for George's confirmation)

- **C1 — Another player opens its own page.** The picker lists `/players`
  (ADR-0136); picking one opens that player's address in the same tab, as
  the switcher does today. Each player serves the remote that matches its
  core.
- **C2 — Seeking is new.** `POST /transport/seek` with a position in
  seconds, sent to the renderer that holds the device; a renderer declares
  `seek` among its controls (ADR-0037). Lyrion seeks with `time`, Spotify
  with go-librespot's `POST /player/seek` (milliseconds, 0.10.5's API).
  Plexamp and Bluetooth do not declare it, and their bar does not respond,
  as Bluetooth's in the design. The plugin contract lists the new control.
- **C3 — The fixed row's mute** is there where ADR-0165 offers it; on an
  output with no control of its own the row is the padlock, *Fixed output*
  and the EQ name.
- **C4 — The cover is the panel's**: the renderer's, else the one the
  library enrichment found, else the *artwork pending* glyph - for any
  source, so Bluetooth's is the glyph, as drawn. The blurred background
  only with a cover. Nothing playing: the note glyph.
- **C5 — The keyboard opens inside the touch**, the one moment a browser
  allows it: the panel says in advance that its pointer is over a text
  field (`over`, ADR-0121) or that its ring is on one (`ring`, a message
  the first build added to `/touchpad`). The phone's own field is out of
  sight; Enter is sent as Enter; the keyboard goes when the panel's field
  loses its focus.
- **C6 — The EQ sheet's note is Phase 20's** (ADR-0162 C18: the volume
  gives the lowering back), not the design's sentence. Its chips are
  Phase 20's settings; *Custom* joins them while it is the one in use.
  *Edit bands in Settings* opens Settings on the equaliser.
- **C7 — What the remote offers follows the player**, as the mini player
  did: Meters only with the visualiser, Room only with a dashboard set,
  Idle screen only with the idle screen switched on; Playing and Lyrics
  need something playing.
- **C8 — The pad the remote starts on is the one last used on that phone**
  (kept in the phone's browser), Trackpad the first time as in the design;
  its `startPad` is the drawing's tweak, not a setting. With *Phone
  touchpad* off the touch area offers the D-pad alone, without the switch,
  and no typing (the socket that carries it is the setting's).
- **C9 — The phone opens on Remote.** Setup, first use and *Personalise*
  still take the whole page while they run.
- **C10 — The page is the design's column**, at most 412 px wide and
  centred on a larger screen. The touch area's floor is 312 px, where the
  D-pad clears the pad switch; without a screen the cover's is 140 px.
  Below them the Remote page scrolls under the top bar (a drag on the
  touch area stays the pad's).
- **C11 — A scroll strip's step** is ADR-0121's `scroll`, 24 px on its
  axis. The first build's step that scrolled the ring's list goes.
- **C12 — Pointer speed and Pointer style stay**, with the pointer; the
  first build's proposal to retire them is withdrawn.
- **C13 — The notes the phone shows stay**: a volume or a mute that failed,
  a character the player could not type (ADR-0157). They are errors, not
  the trackpad's feedback the design took away.

## From the first build

Kept: the seek route and control (C2), the `ring` message (C5), the relay's
fix that lets the panel's `untyped` reach the phone, the picker, the pages,
the quick actions, the EQ sheet, the volume bar and the layout without a
screen. Dropped: the swipe steps and their labels, the finger dot, the
scroll step for the ring's list, the typing sheet, shuffle and repeat, the
480 px column, and the proposal to retire Pointer speed and style.

## Built (2026-10-27)

On `ph-phone-controls`, `next` merged in:

- **The core**: ADR-0165's mute with Fixed volume (`fixed_mute` in
  `/state`, `VolumeBridge.write_fixed`); the first build's scroll step
  taken out of the touchpad's schema; *Phone touchpad*'s note describes the
  trackpad again. Core suite 2751 passed, 48 skipped.
- **The panel**: the fixed rows of the volume drawer and the bar's tray
  have mute, the volume buttons show it; `dpad.js` keeps `dpadring`, the
  ring's scroll step goes; first use's touchpad step describes the pointer.
- **The phone** (`ui/src/screens/remote/`): `RemoteScreen` with
  `RemoteCover` beside the title and `RemoteTransport` (previous, play,
  next), `TouchArea` with ADR-0121's gestures (moved from the mini player)
  and the still strips, the fixed row in `VolumeRow`, the blurred cover in
  `PhoneRemote`; `TypingSheet` deleted.
- **Checked from mocked data** (a mock core, a fake panel on the socket,
  nothing from a player) at 410 x 780 beside the design's board, within a
  pixel of its positions; at 360, 390 x 650, 412 x 915 and 800 wide; LMS,
  Spotify, Bluetooth, no cover, nothing playing, standby, Fixed with and
  without a control, muted; the panel's drawer and the bar's tray in Fixed.
  A 100 px drag arrived as 100 px of `move`, a tap as `tap` with the phone's
  field focused (the fake panel's `over`), 100 px down a strip as four
  24 px `scroll`s, two fingers as `scroll` after the 12 px decision; the
  D-pad's OK and Back as keys. The focus moved the whole remote up 8 px
  (the hidden field's caret); it is focused without scrolling now.
- **The documents**: the manual's section 7 and its pictures (the demo
  library), mute with Fixed in the manual and FAQ, the FAQ's trackpad
  answers, the technical guide (`ui.md`, `api.md`, `core-and-state.md`,
  `audio-path.md`), the README.

## Not in this record

- A remote for several players at once (multiroom, Phase 25).
- The pointer or the D-pad on a player without a screen.
