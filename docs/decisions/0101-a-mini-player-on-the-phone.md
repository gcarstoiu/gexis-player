# ADR-0101 — A mini player on the phone: volume, visualiser, idle screen

**Status:** **Accepted** — George, 2026-09-28: *"Option C - mini player. Only for
phone. Idle screen should toggle the idle screen on or off. Timers would
restart from that point. [Same] with the visualization."*
**Date:** 2026-09-28
**Raised by:** George, once Plexamp kept its own volume (Finding 095
revised): *"the user might need a basic control from
inside the settings page - i.e. volume bar, toggle visualization, toggle idle
screen. These would be always visible when navigating the settings."*
**Amends:** [ADR-0032](0032-one-page-two-surfaces.md) (a remote browser
gets Settings only - now Settings and this bar),
[ADR-0033](0033-idle-and-home.md) (idle is "not playing and not touched" - now
also "asked for").

## Context

With Plexamp, the app's volume slider no longer moves the DAC. On a
phone, the only way to reach the DAC's level was the panel. The visualiser can
already be shown from outside (`POST /peppy/show|hide`). The idle screen cannot:
the panel decides it on its own timer, and nothing outside the panel knows
whether it is up.

George chose the third of three layouts, a mini player. The other two were a
bare bar pinned to the bottom, and a strip in the Settings header.

## Decision

1. **A mini player, pinned to the bottom of Settings, on a phone only.** It
   shows the source's mark and the track title, the volume slider with its
   percentage, and two toggles: visualiser and idle screen. Tapping the title
   opens a sheet with a larger slider and the toggles labelled. The panel's
   own Settings does not get it: the panel has volume on its other screens,
   and a visualiser toggle inside the panel's Settings would take the user out
   of Settings.
2. **The slider is the panel's slider.** It posts to `POST /volume`, so it
   moves what the panel's slider moves: the DAC, and for Spotify and LMS their
   own level too (ADR-0054). With nothing playing it still moves the DAC.
3. **The toggles act on the panel and say what the panel shows.**
   - *Visualiser on/off* is `POST /peppy/show|hide`, which already restarts
     the unattended timer (`PeppyController.request`). The core now publishes
     whether the visualiser is up.
   - *Idle screen on/off* is new: `POST /panel/idle/show|hide`. The core
     passes the request to the panel through the state it already
     broadcasts, and the panel reports back when its idle screen comes up
     or goes away, so the toggle shows the truth even when the panel's own
     timer or a touch changed it.
   - **Timers restart from the toggle** (George). Turning either off is
     attention, exactly like a touch on the panel. Turning the idle screen off
     restarts its countdown from that moment.
4. **Rules George did not state, proposed by Claude and easy to change:**
   - **The idle screen shown on request stays up while music plays**, until it
     is turned off or the panel is touched. The request is explicit, which
     is why it overrides ADR-0033's "not playing".
   - **The two are exclusive.** Showing the visualiser takes the idle screen
     down, and showing the idle screen takes the visualiser down. The panel
     has one screen.
   - **A toggle does nothing on a headless device.** The visualiser toggle is
     hidden when the output feeds no levels, as the panel's button is
     (ADR-0055 §6).
5. **No setting.** Nothing here takes a value, so there is no ADR-0022 row.

## Amended 2026-10-05: Home, Now playing and Lyrics

George, 2026-10-05, trying the phone touchpad (ADR-0121): *"Add to the same
volume sheet: a go to home button, a go to now playing screen, a lyrics
toggle (on standard screens it goes to now playing - lyrics tab, on bar
screens, the lyrics on now playing) which on disable it goes to the track
tab in now playing."* His answers to the two questions it raised:

- **N1: not behind *Phone touchpad*.** Like the visualiser and idle
  toggles, these act on the panel and need no pointer, so they are there
  whatever that row says.
- **N2: Now playing and Lyrics are greyed while nothing plays** - the panel
  has a Now Playing screen only while a source is active. Home always works.

The same path as the idle toggle: `POST /panel/go/{home|now|lyrics|track}`
counts as attention (the visualiser steps aside, timers restart), and the
core publishes a numbered `panel.view_request` the panel applies once.
**Home** is the library's root, or the root screen with LMS off (ADR-0079);
**Now playing** closes what covers it; **Lyrics** is Now playing on its
Lyrics tab - on a bar, with its lyrics on - and turning it off is the Track
tab, lyrics off. The panel reports `panel.lyrics`, true only while lyrics
are what the glass shows, so the toggle says what is there whatever changed
it. Now playing, Lyrics and Track are refused while nothing is active.

## Consequences

- The phone can put music on and turn it down without going to the panel,
  which is what Plexamp needs.
- One new command channel from the core to the panel (the idle request) and
  one report back (the idle state). Both ride the existing state WebSocket
  and a POST, as the panel's touch report already does (ADR-0036).
- The panel has to be running for the idle toggle to mean anything. With
  the kiosk down, the request is kept and applied when it connects.

## Verified (2026-09-28)

- **On the panel, through the same calls the phone makes** (Claude):
  - idle on, then off;
  - visualiser on, then off;
  - one screen at a time, both ways (idle then visualiser; visualiser then
    idle);
  - each change reported back in `panel`, which is what the toggles draw.
- **On George's phone:** *"Phone mini player works as expected."*
- **Not tried:** an idle screen asked for while music plays.

