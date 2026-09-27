# ADR-0097 — What the visualiser shows beyond the title, and how it moves

**Status:** **Accepted** — George, 2026-09-27, on three proposals: the scrolling
ticker and smooth rotation *"agreed with your recommendation"*; the extra fields
*"fine also with the recommended"*, and then: *"You can do the later ones now
too, but keep in mind the distinction I just made."* **Amends
[ADR-0096](0096-turntable-and-cassette-skins.md) decision 3**, which deferred all
of this. **Built; smooth rotation's setting owed to George.**
**Date:** 2026-09-27
**Raised by:** ADR-0096's first cut, which drew the motion and what the renderer
already drew (title, artist, album, artwork, badge, time remaining) and left the
rest of each animated skin's room empty.

## The distinction George made

> *"For us the visualisation is just that - it provides info and a nice skin,
> but the user cannot take action directly from it as any tap would dismiss the
> visualization itself, plus it is not its purpose to be actionable."*

**Everything below is display.** A volume knob, a shuffle icon, a play button
drawn by a skin shows the state it names and does nothing when touched: a tap
anywhere dismisses the visualiser, as it always has (ADR-0019's touch-to-exit,
kept by [ADR-0026](0026-peppymeter-native-process-integration.md)). No hit areas, no
gestures, no state changed from here. A skin that draws a control is read as
a picture of one.

## What the skins ask for

Only the 90 animated skins (ADR-0096) use these keys; the 99 others use none.
Counted over the packs as pinned:

| Field | Skins | Keys |
|---|---|---|
| progress | 83 | `progress.*` - a bar, or an arc (5), or a knob (3); a head picture on 30; markers on 30 |
| volume | 71 | `volume.*` - a slider (with a tip picture on 23) or a knob (6) |
| mute | 75 | `mute.icon`: on and off pictures |
| play state | 64 | `playstate.icon`: stop, pause, play |
| elapsed and total time | 66 | `time.elapsed.*`, `time.total.*` |
| repeat | 58 | `repeat.icon`: off, all, single |
| shuffle | 46 | `shuffle.icon`: off, on, infinity |
| next track | 32 | `playinfo.next.title/artist/album` |
| ticker | 27 | `playinfo.ticker.*`, drawn still since ADR-0096 as amended |

## Decision

1. **The ticker scrolls**, at each skin's own speed and direction, in its own
   box. **The next track is appended where the source reports one** - LMS,
   whose queue the core already holds for now playing's queue rail
   ([ADR-0038](0038-library-and-radio-on-the-panel.md))
   - and left off otherwise: Spotify, Plexamp, AirPlay and Bluetooth hand over a
   stream, not a queue. A skin that also has `playinfo.title.pos` keeps drawing
   its title there; the ticker line is drawn only where it is the skin's title
   (ADR-0096 as amended).
2. **Smooth rotation is built, measured on `gexis` against the stepped rotation,
   and proposed to George as a setting with the numbers** - a row in
   *Visualisation tweaks*, marked [N], added only on his confirmation
   (ADR-0022).
3. **Every field above is drawn**, from state the core already has:
   - progress, elapsed and total: `position` and `duration`, advanced between
     writes the way the time remaining already is;
   - volume and mute: the core's volume state (percent, muted) - the level
     playing, whichever renderer set it;
   - shuffle and repeat: the active renderer's, where it declares them
     ([ADR-0037](0037-transport-commands.md)); a renderer without them draws the
     off picture, as upstream does for a source that has none;
   - play state: `transport`;
   - next track: LMS's queue, the item after the one playing; nothing drawn
     where there is no next item or no queue.

   `nowplaying.json` carries the new values; it stays a projection of state,
   written on change, never a second record.

## Not decided here

- **Sample rate and codec stay undrawn** ([ADR-0036](0036-peppy-entry-and-no-rate-or-codec.md)).
  The skins keep their positions; nothing fills them.
- Which of the rotation settings ships is decision 2's measurement.

## How (as built, 2026-09-27)

- **`nowplaying.json`** gains `volume` (none on fixed output), `muted`,
  `shuffle`, `repeat` (the active renderer's, where declared) and `next` (LMS's
  queue item after the one playing).
- **Ticker:** a `Ticker` in `MetadataLayer` - the line rendered once with the
  skin's end gap, twice side by side, a box-wide window sliding at the skin's
  speed (leftward for `ltr`) and wrapping without a seam; a line that fits
  stands still (upstream draws three copies there). Its box is composed each
  frame it moves a whole pixel, so what turns beneath stays whole. The text is
  George's order, Title • Artist • Album, with the skin's separator and
  spacing, then "Next: artist - title" where LMS has one.
- **Next track, elapsed and total:** drawn like the fields already there;
  elapsed and total in the digi face at the skin's size (the fonts the skins
  name are not in the packs; upstream falls back to the same face), and no
  total for a stream.
- **Progress, volume and the icons:** `gexis_peppy_gauges.py`, reimplementing
  upstream's `SliderIndicator` (bar, tip on a travel, knob, anti-aliased arc,
  markers, head) and `IconIndicator` (picture per state, glow). Progress is a
  whole percentage, as upstream truncates it. The mute pictures were looked at:
  `m_on` is the speaker sounding, so upstream's order stands. `progress.border`
  is parsed by upstream and never drawn; it is not drawn here either.
- **Smooth rotation:** built, off, not a setting. Measured on `gexis`, one 20 s
  window per skin while LMS played, % of one core, stepped → smooth: Vertere
  44 → 87, SME60 40 → 80, Revox B77 40 → 74, TDK 40 → 74, Pioneer Cassette
  18 → 32, ReelTape 22 → 25; the whole machine about 15 → 28 % busy, the SoC
  75 °C, no throttling. The ticker alone added about 10 points on the skins
  that carry one (30-32 → 40-44 stepped). **Proposed to George as a setting;
  not added until he confirms.**

## Reversal conditions

A field whose redraw costs more than the panel can spare - the ticker redraws its
box every frame - is drawn less often (a lower scroll rate) before it is dropped.
