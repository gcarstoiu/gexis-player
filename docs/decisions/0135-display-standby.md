# ADR-0135 — Display standby: the screen off on demand and at night

**Status:** **Accepted** — 2026-10-11. **Rows confirmed by George** the same
day (*"The 4 rows confirmed"*), with days of the week on each interval (*"Day
of the week would be good too"*) and at most six (*"6 is plenty"*). George chose the recommendations
(on-demand screen off and a night schedule; touch, music starting and the
phone button wake it; controls in Display and the phone's mini player), with
two changes: **Display standby is a section of its own**, and **a screen
woken during the night goes back to standby when unused, after 2 minutes by
default, at most 30**. The screen-off method was measured on the 10.1" the
same day (below); the bars and the 13.3" are checked when it is previewed on
them.
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
3. **On a schedule**: with *Scheduled standby* on, inside any of the
   owner's **standby times** the screen goes off whenever nothing is
   playing. **The owner sets the times, as many intervals as wanted**
   (George: *"The night window can be set by the user. It is not fixed.
   More intervals can be given"*), each a start and an end time; one may
   run past midnight (23:00-07:00), and overlapping ones simply join. **Woken
   inside one, it goes back after *Back to standby after* minutes without a
   touch and with nothing playing** (George: 2 by default, at most 30).
4. **What wakes it**: a touch on the panel, music starting on any source, the
   phone's button.
5. **Hidden with Headless**, like every row that needs a screen.

## Settings rows (for ADR-0022, on George's confirmation)

Section **Display standby** in Display, after *Panel*:

| Row | Type | Default |
|---|---|---|
| Turn the screen off | action | — |
| Scheduled standby | toggle | off |
| Standby times | **new: a list of intervals**, each *From - Until* as HH:MM **and the days of the week it applies to**, up to 6 | one, 23:00-07:00, every day |
| Back to standby after | number, 1-30 min | 2 min |

*Standby times* and *Back to standby after* show only with *Scheduled
standby* on; turning it off keeps the times. **The new row mechanic** (an
amendment to [ADR-0044](0044-settings-row-vocabulary.md)'s vocabulary): the
sheet lists each interval with its two times and a remove button, and *Add
standby time* below; a time is typed or picked as HH:MM, checked on the
player, and an interval whose start and end are the same is refused.

## To be measured before it is built

- **Does the backlight go dark** when the output is off, on each tested
  screen (10.1", 13.3", the 7.9" and 11.9" bars), or does it light a "No
  signal" box?
- **Does a touch still reach the player** with the output off? If not, the
  core reads the touch device itself to wake the screen.
- **What it saves**, in watts.

## Measured so far (2026-10-11, sofapi: Waveshare 10.1" HDMI LCD (B), 1280 x 800)

- **Touch reaches the panel's page with the output off.** `wlr-randr --output
  HDMI-A-1 --off` for 60 s: the touch controller (event4) sent 13.5 KB of
  events, and the page posted seven `/touch` to the core while dark. Wake on
  touch needs no reader of its own.
- **The backlight went dark, the screen lit its own "No signal" box after
  about 30 s, and the box went away about 10 s later**, dark from then on
  (George, at the screen; a second run of 3 minutes). So output off is
  standby on this screen, with one short flash of the box as it starts.
  Not yet known: the 13.3" and the bars. A screen that kept its box lit would
  need the alternative - a black page with the signal kept, the backlight
  lit.
