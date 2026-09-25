# ADR-0079 — With LMS off, the panel is two screens

**Status:** Accepted
**Date:** 2026-09-25
**Relates to:** [ADR-0077](0077-a-source-that-is-off-is-not-running.md) (which
made `lms_enabled` real and left this open), ADR-0038 (the library is LMS's),
ADR-0022's inventory (`lms_enabled`, `home_strip`)

## Context

[ADR-0077](0077-a-source-that-is-off-is-not-running.md) wired `lms_enabled`
and left one thing explicitly unsettled: *"whether the Library, Browse and
Radio screens go with it. They are LMS's screens and they read the server
directly rather than through the renderer, so they keep working with LMS off —
a library you can browse and cannot play to."*

**George's answer, 2026-09-25, in three parts**, quoted because they are the
requirement:

1. *"Library, browse and radio go with it."*
2. *"The home screen is used only to signal that renderers are waiting for a
   connection — the current bottom bar when no renderer is connected. That bar
   scales the entire screen with the logos called to match visually in a decent
   way (not the entire height and width of the screen). The settings tile
   becomes a settings icon in the upper right corner."*
3. *"Now playing becomes the home screen. The home button is replaced by
   settings button. The mini strip is not used. Tapping in the artist does
   nothing."*

## Decision

**With `lms_enabled` off the panel has two screens and no library.**

- **Nothing playing → the waiting screen.** The `WaitingServices` footer,
  today 186 px at the bottom of the library root, becomes the whole screen: the
  same marks, rings, labels and ring delays the design specifies, scaled up and
  centred. **Scaled, not stretched** — the cluster grows and the screen keeps
  its air, rather than the row being stretched to 1280 × 800.
- **A settings icon in the top right corner**, replacing the Settings tile that
  went with the library grid. It is the only other thing on that screen.
- **Something playing → Now Playing, as the root.** Its Home button becomes a
  Settings button, because there is no home to go to. The artist line is inert.
  No mini strip: its job was returning to Now Playing from the library.

**The row, not availability, decides this.** `availability.lms` is also false
when the server is merely unreachable, and a panel that collapsed to two
screens because the network blipped — then grew a library back — would be worse
than one that said nothing. A row somebody set is a stable fact; reachability
is not.

`home_strip` and `home_strip_count` describe a strip on a screen that no longer
exists, so they hide with it (`onlyWhen: ['lms_enabled', true]`).

## Rationale

### The waiting bar was already the right picture

The footer exists because "nothing is playing and here is what could be" is the
library root's message when no renderer is connected. With no library, that is
the *whole* message, and the design already drew it. Promoting it costs one
prop rather than a new screen's worth of invention, and the marks, colours,
sizes and ring delays stay the design's.

It also already does the right thing about which sources to draw: it renders
only the ones the daemon reports available, so LMS removes itself from it by
ADR-0077's availability rule without this record saying anything about it.

### Inert, not hidden, for the artist line

"Tapping in the artist does nothing" is implemented as the line not being a
link — no press feedback, no pointer affordance — rather than as a button whose
handler returns early. A control that looks pressable and does nothing is the
defect ADR-0020 exists to prevent, and it reads as a fault rather than as a
device without a library.

### Rejected: keep the library, browse-only

Considered because the library screens work: they read the LMS server through
`library.rpc`, which knows nothing about squeezelite. Rejected on George's
answer, and it is the right one — every leaf in those screens ends in "play
this", and there is nothing to play it. A browsable library with no player is a
menu in a restaurant with no kitchen.

### Rejected: decide it from `availability.lms`

Considered because it needs no new signal in the panel and would also cover a
dead server. Rejected: availability flaps. An LMS restart, a Wi-Fi blip or a
server reboot would each tear the library out from under whoever was using it
and put it back, and the panel would be showing two different products a few
seconds apart.

## Consequences

- **Every source off is now a reachable state**, and it shows an empty waiting
  screen. The settings icon stays, and the screen says what is wrong, because
  the alternative is a panel with nothing on it and no way back.
- **The queue rail disappears on its own.** Only LMS reports a queue
  (ADR-0038 §5), so with LMS off the active renderer never has one.
- Turning LMS back on restores the library with no restart: the row is read
  where the panel draws, like every other.

**The scale is 1.8× and George accepted it**, 2026-09-25: *"Scale is fine."*
Two services come to 680 px of the width and about 300 px of the height on a
1280 × 800 panel — the reading of *"not the entire height and width of the
screen"*, now confirmed against the thing itself rather than the words.

## What this does not settle

- **The phone.** Settings on a phone is the same page and is unaffected, but
  nothing here says what the phone's own now-playing view should do. It is not
  the panel and it has no home button.
- **Whether the waiting screen should offer anything else** — a clock, the
  device name. George specified the marks and the settings icon; this record
  adds nothing to them.
