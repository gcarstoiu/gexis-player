# ADR-0127 — One Volume row: Hardware, Software or Fixed

**Status:** **Accepted** — George, 2026-10-07: *"it is getting confusing to see
output mode and software volume. My idea is that they all live under the same
sheet. Current variable is hardware volume while software volume stays the
same. When hardware volume is not available then it is grayed out and the next
to take its place is software volume."* The proposal below, including the
changed default on HDMI and the merged ADR-0022 row: *"Agreed. Go ahead and
build"*.
**Amends:** [ADR-0124](0124-software-volume.md) (its toggle becomes an option),
[ADR-0046](0046-fixed-output-hides-the-slider.md) and
[ADR-0055](0055-which-output-the-device-plays-to.md) §4-5 (an output with no
volume control no longer forces Fixed).

## Context

Two rows in *Audio* decided one thing, how the level is set: *Output mode*
(Variable or Fixed) and *Software volume* (on or off). They could contradict
each other - Fixed with Software volume on - and on HDMI the first was greyed
to Fixed while the second, if on, gave it a slider after all. George, testing
on guestpi, found it confusing.

## Decision

1. **One row, *Volume*, three options in this order:**
   - **Hardware** - the card's own volume control; bit-perfect at every level.
     This is what *Variable* was.
   - **Software** - the player scales the samples (ADR-0124's stage, unchanged:
     after the meter tap, the level remembered across restarts). Choosing it
     shows ADR-0124's warning: not bit-perfect below 100 %.
   - **Fixed** - full level, for an amplifier that sets the volume (ADR-0046,
     unchanged, still applied only once playback stops).
2. **Hardware is greyed out on an output with no control of its own** (HDMI),
   with the reason, as *Variable* was. **The next option takes its place:
   Software.** The stored choice is not overwritten (ADR-0055 §5): back on a
   card with a control, Hardware returns.
3. **The default is Hardware**, so a new device on HDMI plays through Software
   volume, starting at ADR-0124's quiet first level, where before it played
   Fixed at full level. Fixed on HDMI remains a choice.
4. **The key stays `output_mode`**; its values become `Hardware`, `Software`,
   `Fixed`. `software_volume` is dropped. A migration moves a device's choice:
   *Variable* becomes **Software** if Software volume was on, otherwise
   **Hardware**; *Fixed* stays **Fixed** (the software stage is meaningless at
   full level); a device that had only switched Software volume on becomes
   **Software**.
5. **Rows hidden while the output is fixed** (*Maximum volume*, *Volume curve*,
   *Starting volume*) are now shown for any option but Fixed.

## Consequences

- ADR-0022's *Output mode* and *Software volume* rows become one, *Volume*
  `output_mode` [R]; *Software volume* is marked as merged into it.
- Changing between Hardware and Software restarts the renderers (the output's
  ALSA chain changes, as ADR-0124 already did); changing to or from Fixed
  waits for playback to stop, as before.
- A device updated from 0.9.3 on HDMI with Variable stored (the greyed
  choice) comes up on Software rather than Fixed: quieter, never louder.
