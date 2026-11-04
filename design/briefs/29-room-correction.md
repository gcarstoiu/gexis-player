# Brief for Claude Design — Room correction for the bass (Phase 29)

Written 2026-11-04 for George to hand to Claude Design, with the rough
mock-up of the flow that settled its steps with him (one HTML page, made-up
curves; its order, steps and words are agreed, its look is not). Background,
if you want it: [ADR-0175](../../docs/decisions/0175-room-correction-for-the-bass.md)
(George's decisions of 2026-11-03 and 2026-11-04) and the equaliser's brief,
[`20-equaliser.md`](20-equaliser.md), which this sits beside. What is built
and differs from the earlier designs is in
[`IMPLEMENTED-DIFFERENTLY.md`](../IMPLEMENTED-DIFFERENTLY.md).

---

**Gexis Player** is a music player for the Raspberry Pi 4. It usually has its
own touchscreen (the "panel": 7" to 13.3", most often a 10.1" 1280 x 800, or a
wide *bar*, 11.9" 1480 x 320 or 7.9" 1280 x 400), and every player has a phone
remote. It plays from a **Lyrion Music Server** and is also a **Spotify
Connect** speaker, a **Plexamp** player, a **Bluetooth** speaker, an
**AirPlay** receiver, a **Roon** endpoint, and whatever source plugins add.
Every source plays through the equaliser, and now through room correction.

Please use the existing design (its tokens, type and components: Settings on
the panel and the phone, the equaliser's page, the panel's volume drawer, the
phone's pull-up tray, the bar's tray), in the default theme and the five
others, and export as before: the artboard HTML/CSS, a PNG per state, new
tokens as CSS custom properties, and component boundaries.

## What room correction is

- **The player measures the room** through a USB measurement microphone, the
  miniDSP **UMIK-1**, at the listening seat, and **cuts the peaks the room
  adds to the bass**, below 250 Hz. Only cuts, never boosts: a dip stays as
  it is, since more power does not fill it.
- **Towards a gentle rise** below about 80 Hz (+3 dB), not flat. The target
  and the 250 Hz limit are fixed; the owner does not choose them.
- **Each speaker on its own, at five positions** around the seat: the first
  where the head is, the others within about half a metre of it. About five
  minutes. The sweeps are loud, a few seconds each, about 75 dB at the seat,
  never above the output's maximum level.
- **The microphone is found by itself** when plugged into the player, and its
  calibration file is downloaded from miniDSP by its serial. If the serial
  cannot be read or miniDSP has no file for it, the owner types the serial.
- **Measuring stops what plays**, on every source, and nothing can play until
  it ends or is cancelled.
- **Started and followed on the phone**, which the owner holds while moving
  the microphone. The panel and the bars only show that it is running.
- **For each output**, beside the equaliser (the DAC, HDMI and optical each
  have their own), with:
  - **on / off**. Off with the equaliser also off, the sound is untouched
    (bit-perfect);
  - **A/B, *Hear it without***: a switch, heard at once with no gap. It stays
    where it is put and is saved, like on / off. *Without* sets the cuts to
    0 dB to compare; *off* takes the correction out. Two switches that both
    silence it: the design has to make plain which is the comparison;
  - **the last measurement**: its date and curves, and *Not checked* if its
    check was skipped.
- **Native DSD plays uncorrected** and says so, as the equaliser does.

## 1. The flow on the phone

Agreed with George on the mock-up; the steps and their words as there:

1. **Settings → Audio**: a *Room correction* row under *Equaliser*, with its
   state (*Not measured yet*, *On*, *Off*, *Without*).
2. **Room correction, before**: what it does in two sentences; three checks
   (microphone found with its serial, calibration downloaded, a quiet room,
   about five minutes, music stops); *Measure*.
3. **Place the microphone**: a top-down drawing of the seat, the two speakers
   and the five positions; on a stand at ear height, pointing at the ceiling;
   *Start*.
4. **Finding the level**: soft noise getting louder until the seat hears
   about 75 dB; the level in dB.
5. **Measuring a position**: which position, which speaker plays, two sweeps
   each; nothing for the owner to do (about 25 s).
6. **Move the microphone**: where to (*About 40 cm to the left of where your
   head was*), on the drawing. **It waits for a tap** on *Measure here*, then
   **counts down 3 seconds** before the sweeps; it never carries on by
   itself.
7. **The correction**: left and right, each a chart (below) and its list of
   cuts (frequency, dB), *Check it* or *Discard*.
8. **Checking**: the five positions measured again with the correction on,
   about a minute. **Skip is offered.**
9. **The result**: the measured after; *Keep it* or *Discard*.
10. **The result, not checked** (after *Skip*): the same, with the expected
    after and a *Not checked* mark.
11. **Room correction, on**: the page below.

*Cancel* on every step of the run; *Discard* leaves the output as it was.

## 2. Room correction's page, on the panel and the phone

On / off, *Hear it without*, the last measurement (date, five positions,
*Not checked* if so), the chart with left and right, *Measure again*. On the
panel (1280 x 800 and its family) and the bars (1480 x 320, 1280 x 400, laid
out at 1850 x 400 CSS px, drawn at 0.8), measuring itself is on the phone:
how the panel sends the owner there is yours to propose.

## 3. While it measures, on the panel and the bars

The screen says the room is being measured, to keep quiet, the position and
the speaker (*Position 2 of 5 · Right speaker*), a progress bar, and to
follow it on the phone.

## 4. Close to the music

Beside the equaliser's control in the **panel's volume drawer**, the
**phone's pull-up tray** and the **bar's tray**: a *Room* control showing
*On* or *Without*; a tap switches between the two (the A/B, kept as set).
When the output is off or never measured: yours to propose.

## The chart

- Frequency on a log axis, 15-300 Hz, with the 250 Hz limit marked; level in
  dB, about ±15.
- **Before** (the average of the five positions), **each position** (faint),
  **the target** (the rise below 80 Hz), and **after**, measured or expected.
- Left and right one at a time.
- It has to read on a 360 px phone and in every theme, with the lines told
  apart by more than colour. A line in words carries the result too (*Peaks
  down by up to 8 dB*; *No position is worse than before*).

## States

- **The microphone**: not plugged in; another microphone (*not supported
  yet*); the calibration downloading; no file for the serial (type it);
  typed.
- **Before**: a source playing (it will stop); DSD playing.
- **The level**: rising; too quiet (the level reached, at the output's
  maximum: turn the amplifier up).
- **During**: a sweep (which speaker, 1 or 2 of 2); a noise spoiled a sweep
  (it is repeated); waiting for the tap; the countdown; cancelled; the phone
  page closed and opened again mid-run (it shows where it is).
- **The result**: measured; not checked; nothing to cut (the room's bass
  already near the target).
- **The page**: never measured; on; without; off; not checked; DSD playing.
- A player without a screen (the phone only).

## Not in this design

The full range, correction in time and a target over the whole range
(Phase 30); subwoofers and more than two channels; microphones other than
the UMIK-1.
