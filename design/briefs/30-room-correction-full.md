# Brief for Claude Design — Room correction for the full range (Phase 30)

Written 2026-11-07 for George to hand to Claude Design. It builds on room
correction for the bass, designed in [`source/29`](../source/29/) and built
with the changes in
[`IMPLEMENTED-DIFFERENTLY.md`](../IMPLEMENTED-DIFFERENTLY.md) (*Room
correction*): three positions, about 60 dB, the calibration file given from
the phone, the *Both* tab. Start from what is built, not from the bass's
brief. Background, if you want it: George's decisions of 2026-11-07 in
`docs/DEVELOPMENT.md` (Phase 30) and the research behind them,
[Finding 141](../../docs/findings/141-room-correction-above-the-bass-what-is-known.md).
A measurement in George's room comes before the build, so the figures here
(times, how many corrections) may still move. The screens should not.

---

**Gexis Player** is a music player for the Raspberry Pi 4, with its own
touchscreen (the panel, most often 1280 x 800, or a wide bar, 1480 x 320 or
1280 x 400) and a phone remote. Every source plays through the equaliser and
room correction. Please use the existing design, in the default theme and the
five others, and export as before: artboard HTML/CSS, a PNG per state, new
tokens as CSS custom properties, component boundaries.

## What changes

- **Room correction now reaches above the bass, to 20 kHz.** Below 250 Hz it
  stays as built: it cuts the room's peaks, never raises a dip, and aims for
  the gentle rise below 80 Hz.
- **Above 250 Hz it is gentle**: broad corrections of at most 3 dB, up or
  down. It raises a dip there too, since above the bass a dip is often the
  speaker's own.
- **Its aim above the bass is the speaker's own balance**: the slope the
  speaker already has in the room is kept, and only the room's broad bumps
  and dips are taken out. The speaker keeps its character, and the equaliser
  stays for taste.
- **The same measurement**: the same three positions at the main seat, the
  same steps and taps, the same check. The sweeps now rise into the treble.
  The time is about the same, to be confirmed.
- **A new choice for each output: *Bass* or *Full range*.** There is one
  switch as now, plus how far the correction reaches. A new measurement
  starts at *Full range*. A measurement made before this phase covers only
  the bass: it stays at *Bass*, and *Full range* asks to measure again.
- **Hear it without** compares with no correction at all, as now.
  Comparing *Bass* with *Full range* is done with the choice itself.
- **Grouped players**: nothing changes. The correction works in a group as
  the bass's does, and measuring still asks the player to leave the group.

## 1. Room correction's page, on the panel and the phone

- Where the *Bass* / *Full range* choice sits beside on/off and *Hear it
  without*, and how it reads as "how far it reaches", not as another on/off:
  yours to propose.
- The last measurement says whether it covers the full range or the bass
  only. A bass-only one offers *Measure again* to reach the full range.

## 2. The chart, now over the full range

- **The axis:** frequency on a log axis from 15 Hz to 20 kHz.
- **The lines:** as built - before (the average of the three positions), each
  position faintly, the target dotted, and the after, measured or expected -
  with *Left*, *Right* and *Both*. The target is the bass's rise joined to the
  speaker's own slope above it.
- **Two ranges of size in one chart:** the bass's swings reach ±15 dB or more,
  while the corrections above the bass are 3 dB at most. The chart has to
  make both readable, so that a 2 dB correction at 2 kHz is not lost under a
  15 dB peak at 45 Hz. How is yours to propose: a second view, a zoom, a
  scale.
- **With *Bass* chosen,** above 250 Hz is hatched and *left alone*, as now.
- It has to read on a 360 px phone and on the bars.

## 3. The correction and the result

- **The list of corrections** now holds two kinds: the bass's cuts (narrow,
  deep, as now) and the broad ones above it, up or down (for example,
  *+2.5 dB around 2.4 kHz, broad*). It shows the two apart.
- **The result's line** gets a second part for above the bass. Examples, with
  made-up numbers: *Peaks down by up to 12 dB* for the bass, and *Above the
  bass: within 1 dB of the speaker's own balance*. The words are yours.
- **Nothing to correct above the bass:** a room already within about 1 dB of
  the speaker's own balance.

## 4. The flow on the phone

The steps are unchanged. What the words have to say now:
- the page before measuring: what it does, in two sentences, now covering
  above the bass;
- while it measures: the sweeps rise to a high whistle, so the room should be
  quiet throughout.

## 5. Close to the music

The *Room* control in the panel's drawer, the phone's dock and the bar's
tray stays as built: *On* or *Without*. Whether it also shows *Bass* or *Full
range*: yours to propose. The drawer is meant to stay simple.

## States

- **The page:** *Full range* on; *Bass* on; *Bass* with a bass-only
  measurement (measure again for the full range); without; off; not checked;
  DSD playing.
- **The result:** both ranges corrected; nothing to correct above the bass;
  nothing to cut in the bass but something above it; a position worse than
  before.
- **The chart:** each tab with *Full range* and with *Bass*; the phone at
  360 px; the bars.

## Not in this design

- **Timing:** correction in time is Phase 34, which may not be built.
- **Seats:** corrections for other seats or the whole sofa (the main seat
  only).
- **Hardware:** subwoofers and more than two channels; microphones other than
  the UMIK-1.
- **The owner's own target:** the equaliser does that.
