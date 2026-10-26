# ADR-0164 — The phone remote

**Status:** **Accepted** — George, 2026-10-26: the design handed over
(`design/source/21`, Claude Design), build it, with his answers to the
questions it left (below). The decisions he left to Claude are listed
under *Claude's decisions* for his confirmation. Phase 21
(`ph-phone-controls`). Replaces [ADR-0101](0101-a-mini-player-on-the-phone.md)'s
mini player on the phone; keeps
[ADR-0121](0121-the-phone-as-the-panel-s-touchpad-and-keyboard.md)'s
touchpad and keyboard in a new place. Builds on
[ADR-0037](0037-transport-commands.md) (what a renderer declares),
[ADR-0135](0135-display-standby.md) (standby),
[ADR-0136](0136-switching-between-players-on-the-phone.md) (the players on the
network), [ADR-0161](0161-a-d-pad-on-the-panel.md) (the D-pad) and
[ADR-0162](0162-a-simple-equaliser.md) (the equaliser's quick change).

## Context

The phone page is Settings with a mini player pinned under it (ADR-0101):
the track and play/pause, the panel's row (*Screen off*, Home, Playing,
Lyrics, Meters, Room, Idle), the volume and, from Phase 20, the EQ button.
Swiped up, it opens the touchpad between the track and the row (ADR-0121).
A player without a screen gets the same page, its panel row included.
George added Phase 21 on 2026-10-26 for a redesign of the quick actions and
the touchpad, and handed over Claude Design's *phone remote* the same day.

## Decided (George, 2026-10-26)

1. **One remote, two pages** (`design/source/21/README.md`): a player
   picker and a Remote / Settings switch on top; the Remote page, and
   Settings as it is, without the mini player. The mini player goes from
   the phone.
2. **A player with a screen**: now playing (cover, title, artist, album,
   progress, transport), a touch area, quick actions and the volume row.
   The touch area has four corner buttons (Home, Lyrics, Back, Meters) and
   a switch between two pads.
3. **The two pads: Touchpad and D-pad.** George, asked whether the pointer
   goes: the design shows both, with a switch between them. **Touchpad is
   today's pointer** (ADR-0121: one finger moves it, a tap presses, two
   fingers scroll, a pinch zooms, the keyboard for a text field); the
   design's scroll strips are its edge lines. **D-pad sends ADR-0161's
   steps.** The design's Touchpad sent steps too (52 px of swipe a step);
   that is not built, as it was the D-pad again (`IMPLEMENTED-DIFFERENTLY`).
4. **Quick actions**: Standby (the screen, ADR-0135), Idle screen, Playing,
   Room.
5. **A player without a screen**: a large cover, a seek bar, larger
   transport and the volume row; no touch area and no quick actions.
6. **The volume row**: a bar with mute inside it, the level and the EQ
   setting's name, then the EQ button, which opens the EQ sheet. **Its
   touch sizes as drawn** (the bar 36 px tall, mute 32 x 32), under the
   44 px floor (the design's open point).
7. **Repeat cycles off, all, one**, as on the panel (the design's open
   point; it drew on and off).
8. **Sources as on the panel**: what a renderer does not declare is left
   out (ADR-0037): no shuffle or repeat with Spotify, and with Bluetooth no
   duration either, so no seeking.
9. **The Home Assistant card follows the redesign**
   ([ADR-0163](0163-a-gexis-player-card-for-dashboards.md)): Standby added
   and the views grouped as on the phone, in the integration's next release,
   after the phone. George sees it before it is released.

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
- **C3 — Fixed volume**: the bar's place says *Fixed output*, with the
  panel's padlock, and the EQ button stays (the design's open point).
- **C4 — Bluetooth has no cover**: the note glyph, as on the panel (the
  design's open point; it drew the sample cover).
- **C5 — The typing sheet** shows while a text field on the player's screen
  has focus (the panel's `focus` message, ADR-0121). With the D-pad the
  panel also says when its ring is on a text field (a new `ring` message on
  `/touchpad`), so OK there opens the phone's keyboard in the same touch,
  the one moment a browser allows it. **Done** puts the phone's keyboard
  away; what was typed stays in the field.
- **C6 — The EQ sheet's note is Phase 20's** (ADR-0162 C18: the volume
  gives the lowering back), not the design's earlier sentence. Its chips
  are Phase 20's settings; *Custom* joins them while it is the one in use.
  *Edit bands in Settings* opens Settings on the equaliser.
- **C7 — What the remote offers follows the player**, as the mini player
  did: Meters only with the visualiser, Room only with a dashboard set,
  Idle screen only with the idle screen switched on; Playing and Lyrics
  need something playing.
- **C8 — The pad the remote starts on is the one last used on that phone**
  (kept in the phone's browser), Touchpad the first time, rather than a
  setting. With *Phone touchpad* off the D-pad alone is offered and the
  switch is not shown.
- **C9 — The phone opens on Remote.** Setup, first use and *Personalise*
  still take the whole page while they run.
- **C10 — The page is the design's column** on a phone, at most 480 px wide
  and centred on a larger screen; nothing on it scrolls but Settings.
- **C11 — The volume bar waits for the finger's direction**, as the mini
  player's slider did (2026-10-12): a tap sets the level on lift, a
  sideways drag follows the finger, an up or down swipe sends nothing.

## Not in this record

- A remote for several players at once (multiroom, Phase 25).
- The pointer or the D-pad on a player without a screen.
