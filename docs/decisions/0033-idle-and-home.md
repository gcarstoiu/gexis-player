# ADR-0033 — Idle is "not playing and not touched"; Home is the no-renderer screen

**Status:** Accepted
**Date:** 2026-09-15
**Raised by:** George
**Amends:** [0019](0019-peppy-screen-lifecycle.md) — what triggers the idle
screen and where it returns to

## Decision

**Home is the screen for "no renderer connected"** (`active: null`). In the
design it is the library root. It is not the idle screen.

**Idle is a device state, the same everywhere** (George, 2026-09-15: *"Idle is
idle unimportant of where it happens"*):

- **Activity** is a touch on the panel, or music playing.
- **Idle** is everything else: no renderer; a renderer connected but paused or
  stopped. A phone changing volume or track while playback is paused or
  stopped is **not** activity.
- **After 5 minutes idle, on any screen, the idle screen takes over.** One
  timeout, not one per screen.
- **Touching the idle screen returns to wherever the panel was** when it went
  idle — Home, now playing, or anything else.

## What changes in ADR-0019

- ADR-0019 had "nothing playing" belong to the idle screen directly. It now
  belongs to Home, and the idle screen comes only after the timeout.
- ADR-0019's five-minute grace after playback stops is the same rule seen from
  now playing and the Peppy screen: stopped is idle, five minutes later the
  idle screen appears. Not a second timer.
- "Idle timeout while playing" as the Peppy screen's implicit entry can no
  longer be called *idle*, because playing is activity. The implicit entry
  itself is not touched here; its name and timer belong to Phase 5.

## Unresolved

- **Playback starting while the idle screen is shown.** Playing is activity,
  so the idle screen leaves. Assumed: back to where the panel was, then the
  normal renderer rules apply (a renderer arriving shows now playing).
  Unconfirmed.
- **A renderer disconnecting** — assumed to show Home. Unconfirmed.
- ~~What the idle screen shows.~~ **Resolved 2026-09-15 (George):** the
  external page, per ADR-0019. The design's drifting clock is the **fallback**
  when that page does not load — unreachable, unconfigured, or refusing to be
  framed.
- **Settings.** The 5-minute value is configurable per ADR-0019; ADR-0022's
  inventory only lists the Peppy-screen timeout. Proposed as an inventory row,
  not yet appended.
