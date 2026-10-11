# Finding 118 — The hidden library over an hour: nothing; the idle screen: half a core, from its weather icons

**Date:** 2026-10-10. **For:** ADR-0122's owed measurement - *"how a hidden
library behaves on a Pi 4 over an hour"* - and Phase 13f's closing (George:
run it on the bar, then on sofapi, as the bar might still have undervoltage).

## Scope

- **Devices:** the bar player (Pi 4, 11.9" bar at 1480 × 320) and `sofapi`
  (Pi 4, 10.1" at 1280 × 800). Both: gexis-core 0.9.8, gexis-ui
  0.9.7+git62 (a preview build; the hidden library is unchanged since), the
  idle screen *Built in*, background *Wallpapers online*, clock and weather on,
  idle timeout 5 minutes.
- **Method:** a shell sampler on each Pi, every 30 s for 70 minutes: the
  summed resident memory and CPU time of all `chromium` processes, the core's
  CPU time, the SoC temperature, the load, whether any ALSA stream ran, and
  on sofapi `vcgencmd get_throttled`. After 10 minutes it asked the panel for
  the library (`/panel/go/home`) and, 20 s later, for Now Playing over it
  (`/panel/go/track`): the library mounted and hidden, ADR-0122's case.
- **Nothing played** during either run. Lyrion was the active source,
  stopped (on sofapi after a play-and-stop of about 1.5 s, with George's
  permission, so that Now Playing existed).
- **Not measured:** the hidden library while music plays (Now Playing then
  moves every second, and the two would not separate); the page's own JS
  heap (the kiosk exposes no debugging port); a phone.

## Results

| | bar | sofapi |
|---|---|---|
| Browser CPU, library hidden under a still Now Playing (5 min) | **0-1.4 %** of one core | **0-1.4 %** |
| Browser CPU, idle screen (108 samples of 30 s, 54 minutes) | **52-67 %**, 61 % mean | **46-56 %**, 51 % mean |
| Core CPU | 3-6 % | 5-6 % |
| Browser memory, start → end of the hour | 1,112 → 1,124 MB | 1,137 → 1,148 MB |
| Highest SoC temperature | 67.7 °C | 66.7 °C |
| Undervoltage | none (register 0x0 after, no kernel warning) | none (0x0 on all 119 samples) |

1. **A hidden library costs nothing measurable.** Its timers and effects keep
   running (ADR-0122, Consequences), and with Now Playing still over it the
   browser's CPU time did not move for five minutes on either Pi.
2. **No growth over the hour.** Memory is flat to within 12 MB on both; the
   ~90 MB spikes are an eleventh browser process that comes and goes.
3. **The idle screen holds half a core or more for as long as it is up** -
   the same before the library was opened and after - and keeps the Pi at
   about 66 °C. The idle timeout (5 minutes) brought it back at 924 s on both,
   and the CPU jumped in that sample. Nothing in it animates continuously: a
   one-second clock tick, a clock block that moves once a minute, a picture
   every few minutes, under a static `blur(38px)` copy of the picture.
   The cause, measured the next night, is below: the weather icons'
   animations.

## The cause: the weather icons (2026-10-11, the bar player)

**Scope:** the bar player, the idle screen up (four weather icons: today's and
three days; no blurred halo on that picture), the kiosk's DevTools port
switched on for the test and off again after (`/etc/gexis/kiosk.env`
restored, checksum matched). Each condition a CSS rule injected into the
running page, 10 s to settle, then the browser's CPU over 45 s from `/proc`.
Three runs; the same condition varies by about ±5 points between them.

| Condition | Browser CPU, one core |
|---|---|
| As it is (11 animations running in 4 icons) | 47-57 % |
| **Weather animations paused** | **4-6 %** |
| Forecast icons paused, today's icon animating | 42 % |
| **One animation running** (a cloud's drift) | **49 %** |
| Animations stepped (`steps(4)`) | 28 % |
| `will-change` on the animated parts | 57 % |
| The blurred halo hidden / no filter on the picture | 47 % / 63 % |

1. **The weather icons' animations are the cost**: paused, the idle screen
   is at 4-6 %.
2. **It is not per animation.** One drifting cloud costs what all eleven do:
   while anything animates, Chromium on the Pi 4 composites a frame on every
   refresh, and that is the half a core. The animations are already the cheap
   kind (`transform` and `opacity` only); layer hints do not help.
3. **The blur and the picture's filters are not involved.**

## What follows

- **Phase 13f's owed measurement is done:** the hidden library is fine.
- **The idle screen's cost is new**, not recorded before, and the screen is
  what a player shows most of the day. Since one animation costs as much as
  all of them, the remedy is less time animating, not fewer animations: a
  decision for George (the icons' motion is the design's).
- Memory summed over Chromium's processes counts shared pages more than once;
  it is a trend, not the browser's real footprint.
