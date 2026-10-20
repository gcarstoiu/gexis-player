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
   --off` in the kiosk's labwc session, `--on` to wake). The connector is the
   port the screen is on, from `screen.env`; with none named there, the port
   a screen is connected to (amended 2026-10-12, ADR-0109; it was always
   HDMI-A-1). The player, its
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

## Built (2026-10-11, on `phase-13d`, in four steps)

1. The screen off and on (`standby.py`), the panel's black cover, the wakes
   (touch, music, the phone's new *Screen* button), the visualiser held off.
   Tried by George on sofapi: all four worked.
2. The *Display standby* section: *Turn the screen off* (asks once, "Turn
   off"), *Scheduled standby*, *Back to standby after*.
3. *Standby times*: the `intervals` row (ADR-0044 amended).
4. The schedule (`Schedule`), every 15 s.

## Amended 2026-10-11: after George tried it on his phone

- **No *Turn the screen off* row**: the phone's *Screen* button is enough
  (George). The route stays for it.
- **Standby times**: our own time grid (hours, then quarters) in place of the
  browser's list (*"really old school"*); changes drawn at once and written
  400 ms after the last one, or as the sheet closes (a day chip waiting for
  the player *"is slow to react"*); the remove button in the card's corner.

## Amended 2026-10-12 (final code review)

- **A Bluetooth pairing request wakes the screen.** One that came in standby
  was drawn under the black cover and expired unseen.
- **After a core restart during standby, the first touch brings the picture
  back**, and music starting wakes it as before. The output's state lives in
  the kiosk's session, which outlives the core; the core now treats an
  output it has not switched on since it started as possibly dark.
- **`POST /touch` is the panel's only**: a phone's would wake the screen and
  count as attention.

## Amendment, 2026-10-20 — a tap seen in the kernel; the real screen at start

George, on ShelvesPi (the 11.9" bar): *"The screen is blank and doesn't wake
up on tap"*; approved the two fixes (*"Ok with both. Go for it"*), then
rejected the first way of doing the first (*"3 seconds is too much"*).

- **What happened.** Standby was asked for at 22:50 and switched the output
  off (`wlr-randr --off`). The bar's touchscreen is tied to that output
  (`<touch mapToOutput>`, ADR-0109: the bars are portrait panels used
  sideways), so with the output gone the compositor dropped its taps: none
  reached the page after 22:50 (the core's log). At 03:45 the nightly update
  restarted the core, which then called the screen on; the phone offered
  nothing to wake it. The 10.1" measurement above (a touch reaches the page
  with the output off) does not hold for a screen whose touch is mapped.
- **Tried and dropped: powering the display down instead** (`wlopm --off`,
  output kept). Every tap arrived (measured, 3 of 3), and one tap woke the
  player's own standby - but the picture took about 3 s to come back, against
  almost instant with the output switched on (George: *"too much"*).
- **Kept: the output switched off, and the core listens to the touchscreens
  in the kernel while it is off** (`standby.TouchWatch`: the event devices
  that report BTN_TOUCH, read without taking them from the compositor; a
  finger coming down wakes the screen). On ShelvesPi the kernel saw every tap
  with the output off, in both rounds of the test. The tap wakes the screen
  and presses nothing underneath - the page never sees it.
- **At start the core reads the real screen** (`wlr-randr --json`'s
  `enabled`). Dark inside a standby time, it is the schedule's standby, said
  as such - the phone offers to wake it, a touch wakes it (the watch runs),
  the schedule wakes it when the time ends. Dark outside one, it is woken.
  Lit, it is known to be on.
- Not yet measured: the 10.1" with the watch (its taps reached the page
  anyway); a USB touchscreen unplugged while the watch reads it.
