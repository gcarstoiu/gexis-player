# ADR-0121 — The phone as the panel's touchpad and keyboard

**Status:** **Accepted** — George, 2026-10-05: the plan approved and its six
questions answered (*"A. Inside volume sheet. B. Only when controlling. No
movement or tapping for 5 seconds and it hides itself. C. When tapping
inside a text field then the phone's keyboard comes up. D. No gestures yet.
Let's have it working in a simple manner. E. You can record them both.
Third not. F. Yes. Same behaviour."*). Four measurements come before the
build (below, and their results under *Measured*); they confirm the mechanism, they do not reopen the decisions.
**Builds on:** [ADR-0118](0118-lyrion-s-own-menus.md)'s option section and
its question E (search), [ADR-0028](0028-ui-serving-and-command-channel.md)
(the API is open to the LAN by decision), [ADR-0022](0022-settings.md) (two
rows, below).
**Phase:** before [13f](../DEVELOPMENT.md), which needs typed text.

## Context

George, 2026-10-04: *"Can we use the phone as a mouse and keyboard for the
panel? ... Expand upwards the volume panel and add an area that would work
as a touchpad controlling the pointer on the display. When tapping inside a
search field then the phone's keyboard would pop up and allow text entry."*

Phase 13f's Lyrion menus put search at the front of the streaming apps
(Finding 110: YouTube's top level is 11 searches of 15 entries), and the
panel has no keyboard. The panel and the phone take the same input (the
project's standing rule); what a phone can add is a way to point and type on
the panel from across the room.

## Decision

### 1. Inside our own page

The phone sends finger movement over its existing connection to the core;
the core relays it to the panel, uninterpreted; the panel's page draws its
own pointer and turns a tap into a tap on what lies under it. **Not** a
system-level virtual mouse and keyboard (`wlrctl`): that would bring back the
system pointer the panel hides by design and reach windows the panel does
not need. Everything the panel shows is our page; the visualiser, a window
of its own, needs only taps to leave, which a tap anywhere already does.

### 2. In the volume sheet (A)

The phone's volume sheet extends upwards: a touchpad area above the slider.
One finger moves the pointer; a tap taps. **Relative, as a laptop's
touchpad** (George, 2026-10-05: *"the phone touch area moves the pointer in
the screen relative to its initial position. This way bars don't have a
problem"*): the touch area is not mapped onto the screen; a finger's
movement moves the pointer from where it is, by an amount *Pointer speed*
sets, so a 1280 x 400 bar and a 1920 x 1080 panel take the same touchpad. **Nothing else (D)**: no
two-finger volume, no swipes for tracks, no scrolling gesture - "working in
a simple manner" first. Scrolling a panel list from the phone is **not** in
this record; lists scroll by touch on the panel, as today.

### 3. The pointer (B)

Shown **only while a phone is controlling**: it appears with the first
movement and **hides after 5 seconds with no movement and no tap**. One
pointer whatever the number of phones; the latest touch moves it.

### 4. Typing (C)

**Tapping inside a text field brings up the phone's keyboard**, with no
extra tap. A browser opens the keyboard only in direct answer to a touch on
the phone itself, and the panel's answer to a tap arrives after that touch
has ended - so the panel tells the phone **in advance**: while the pointer
rests over a text field, the phone knows, and the tap that lands there
opens the keyboard within the same touch (a hidden field on the phone takes
focus). What is typed appears in the panel's field as it is typed - text is
inserted, not keys pressed, so any character and any keyboard language
works - and Enter submits. The keyboard closes when the panel's field loses
focus or the sheet closes.

### 5. Messages

Over **a socket of their own, `/touchpad`** (built 2026-10-05: `/state` stays
publish-only, as ADR-0028 decided - commands are requests), relayed by the
core between the panel (on loopback) and the phones (from the LAN), dropped
while *Phone touchpad* is off, and never turned into a Lyrion command:

- phone → panel: pointer movement (relative), tap, text inserted,
  backspace, enter;
- panel → phone: the pointer is over a text field / not; a text field has
  focus / not.

### 6. Same on a bar (F)

The same behaviour on the bar screens; the pointer's size and speed are the
panel's, measured in its own pixels.

### 7. Settings (E; ADR-0022, confirmed by George)

- **Phone touchpad** [N] - on/off, whether the volume sheet offers it.
- **Pointer speed** [N] - how far the pointer moves for a finger's
  movement.

### 8. Nothing newly exposed

Anyone on the LAN can already control the player and its settings from the
phone page (ADR-0028); pointing and typing on the panel adds no reach.

## To measure before building

- **The keyboard, on real phones**: George's Android and, if one is to hand,
  an iPhone - that a tap over a field the panel announced in advance opens
  the keyboard within the same touch (§4).
- **Latency**: from a finger's movement to the panel's pointer over gexis's
  Wi-Fi, against about 100 ms to feel direct, at about 60 movements a second.
- **Synthetic taps**: that a tap the page makes drives every control the
  panel has. The bar tray's swipe needed real touch events (LESSONS 57); a
  control that needs them is listed, and either answers a synthetic tap too
  or is reached otherwise.
- **Load**: what a steady stream of movements costs the core and the panel
  on the Pi.

## Measured (2026-10-05, gexis, preview 0.9.0+git19)

Scope: a headless Chromium on gexis as the panel (loopback, 1280 x 800, the
installed UI), a phone page in Brave headless on the LAN with touch
emulation (412 x 820), CDP touch events. Not a real phone; the kiosk took
the same stream (LESSONS 59).

- **The keyboard - still owed, on George's Android.** In emulation the
  hidden field takes focus within the tap and keeps it. It did not at
  first: the touch's own `mousedown`, 1 ms after, took focus back - the
  keyboard would have opened and closed. Fixed: the touchpad refuses it.
- **Latency**: 20 crossings of a field's edge, from the phone sending a
  move to the panel's "over" arriving back - median **31 ms**, most 88 ms,
  over gexis's Wi-Fi. Two hops, so one way is about half.
- **Synthetic taps**: a tap opened Settings from the home screen's card; a
  tap typed into a field (text, Backspace). Two failed and are fixed: a tap
  made as pointer 41 threw on every control that captures the pointer
  (volume, queue, bar tray, sideways rows) and left the volume slider held -
  taps are pointer 1, the mouse's, now; and a browser's own slider ignores
  made-up events - a tap on one now sets it where it landed (75 % -> 75,
  `change` sent). **Not reachable from the phone, by D**: anything that
  needs a drag - reordering the queue, scrolling lists and the bar's
  sideways rows. The bar tray's band answers a tap.
- **Load**, 60 moves a second for 30 s: the core 4-5 % of one core (0.5 %
  idle); the kiosk 16-23 % of one core (under 1 % idle) - of the Pi's 400 %.
  Nothing playing; not measured during playback.

## Consequences

- A touchpad in the phone's volume sheet, behind the *Phone touchpad* row.
- A pointer layer on the panel, hidden unless a phone is controlling.
- New message types relayed by the core, without meaning to it.
- 13f's search boxes, and every other text field on the panel, can be
  typed into from a phone.
