# ADR-0135 — Display standby: the screen off on demand and at night

**Status:** **Proposed** — 2026-10-11. George chose the recommendations
(on-demand screen off and a night schedule; touch, music starting and the
phone button wake it; controls in Display and the phone's mini player), with
two changes: **Display standby is a section of its own**, and **a screen
woken during the night goes back to standby when unused, after 2 minutes by
default, at most 30**. Waits on the screen-off test below and on George
confirming the settings rows (ADR-0022).
**Amends:** [ADR-0019](0019-peppy-screen-lifecycle.md) §*The panel does not
sleep* ("No blanking, no backlight timeout").

## Context

The panel has never slept: ADR-0019 left the night to an external power
trigger. *Headless* turns the screen off for good, as a setup choice. The Pi
4 has no suspend-to-RAM and cannot be woken over the network once halted, so
a real standby of the whole device is not on offer; the screen is what can
be put to rest, with the player still playing and still reachable.

## Proposal

1. **Screen off is the HDMI output off** (`wlr-randr --output <connector>
   --off` in the kiosk's labwc session, `--on` to wake). The player, its
   renderers and the phone page keep running: a cast from Spotify or Lyrion
   still plays. The visualiser and the idle screen stop while it is off.
2. **On demand**: *Turn the screen off* in Display standby, and a screen
   button in the phone's mini player. It stays off until woken.
3. **At night**: with *Night standby* on, from *From* to *Until* the screen
   goes off whenever nothing is playing. **Woken during that window, it goes
   back after *Back to standby after* minutes without a touch and with
   nothing playing** (George: 2 by default, at most 30).
4. **What wakes it**: a touch on the panel, music starting on any source, the
   phone's button.
5. **Hidden with Headless**, like every row that needs a screen.

## Settings rows (for ADR-0022, on George's confirmation)

Section **Display standby** in Display, after *Panel*:

| Row | Type | Default |
|---|---|---|
| Turn the screen off | action | — |
| Night standby | toggle | off |
| From | choice, hourly 00:00-23:00 | 23:00 |
| Until | choice, hourly 00:00-23:00 | 07:00 |
| Back to standby after | number, 1-30 min | 2 min |

*From*, *Until* and *Back to standby after* show only with *Night standby*
on.

## To be measured before it is built

- **Does the backlight go dark** when the output is off, on each tested
  screen (10.1", 13.3", the 7.9" and 11.9" bars), or does it light a "No
  signal" box?
- **Does a touch still reach the player** with the output off? If not, the
  core reads the touch device itself to wake the screen.
- **What it saves**, in watts.
