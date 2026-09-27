# ADR-0094 — Every takeover shows the transition screen, for the length the user sets

**Status:** **Accepted** — George, 2026-09-26. **Supersedes
[ADR-0078](0078-the-transition-screen-waits-for-the-threshold.md)**, and retires
[ADR-0010](0010-arbitration-slot-model.md)'s list of pairs exempt from the
transition screen.
**Date:** 2026-09-26

## Decision

George: *"remove the Transition screen threshold setting. Basically then
handoff visualisation is to be shown at all times even when the takeover is
nearly instantaneous. The length of the visualisation is to be dictated by the
Transition screen length setting that the user can set by himself, for which the
default should stay as is now at 1.5 seconds. Nothing related to the start of
the playback or anything related to the actual takeover changes."*

- **Every takeover shows the screen, at once.** No threshold before it appears,
  and no pair is exempt for being fast - the exemption and the threshold both
  existed to suppress quick takeovers, which is exactly what this reverses.
- **It stays up for `handoff_duration`**, *Transition screen length*, default
  **1.5 s**. A takeover still in flight when that runs out keeps the screen up
  until it finishes, as before; otherwise it would vanish mid-takeover.
- **`show_transition` still turns it off altogether.**
- **Presentation only.** Arbitration, the release ladder and playback start are
  untouched.

## What was removed

- The `handoff_threshold` row (ADR-0022's inventory, ADR-0078). Its value stays
  in a settings database that already holds one; `Settings` reads the registry,
  so the stored value is inert.
- `handoff_exempt_pairs` - `Config`, the state payload and the panel's store.
  It was never set in any shipped `core.toml`.

## One number corrected

George gave the current default as 1.5 s. The registry said **1.4**, with a
0.5 s step the slider could not land on - so the row most likely displayed
1.5 while 1.4 was in force. The default is now 1.5, which is what he asked for
and what the slider shows.
