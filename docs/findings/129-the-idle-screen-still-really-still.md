# Finding 129 — The idle screen with Static icons: half a core until what it covered was paused too; Photographic costs what Solid does

**Date:** 2026-10-19. **For:** ADR-0154 decision 5 - measure Photographic's
lit clouds on a Pi before building the four new icon sets out - and Finding
118's open point: *Weather icon motion: Static* was expected at 4-6 % of a
core but had never been measured with the setting itself.

## Scope

- **Device:** sofapi (Pi 4, Waveshare 10.1" at 1280 × 800), the idle screen
  *Built in*, its picture online, clock and weather on, *3 days*, at night
  (the moon drawn, ADR-0153). Nothing played; nobody touched the panel.
- **Builds:** gexis-ui `1.2.0+git22` (the four sets, before the fixes) and
  `1.2.0+git23` (after), from branch `weather-sets`.
- **Method:** the summed CPU time of every `chromium` and `labwc` process from
  `/proc`, over 30 s, as a share of one core; the setting changed through
  `PUT /settings/...`, 10 s to settle, the idle screen asked for again. One
  run per condition; Finding 118 saw about ±5 points between runs of the same
  condition.
- **Not measured:** Atmospheric, Modern and Futuristic alone (Atmospheric
  shares Photographic's clouds; Modern and Futuristic use no lighting
  filter); the bar player; temperatures; a day picture (the sun).

## Results

| Build | Weather icons | Motion | Browser CPU |
|---|---|---|---|
| +git22 | Photographic | Animated | 55 % |
| +git22 | Photographic | Static | **45 %** |
| +git22 | Solid | Static | **58 %** |
| +git23 | Solid | Static | **7.9 %** |
| +git23 | Solid | Animated | 55 % |
| +git23 | Photographic | Animated | 54 % |
| +git23 | Photographic | Static | **4.4 %** |

1. **Static did not make the idle screen still.** With the icons' own
   animations stopped, other animations ran on: the waiting screen's rings
   around the service marks (eight, `WaitingServices.svelte`) kept pulsing
   underneath the idle screen, out of sight. Finding 118 found that one
   running animation costs what all of them do; these cost the half core.
   Listed with `document.getAnimations()` on the stand-in.
2. **The moon's phase rebuilt the SVG icons every second.** It was worked
   out from the clock, which ticks every second; each change rebuilt the new
   sets' SVG and redrew their lighting filters. Seen as icon rebuilds on the
   stand-in; on the Pi it is part of the 45 %.
3. **Fixed in +git23**: while the idle screen is up, every animation under
   it is paused (`html.idle-up`), and the phase changes once a minute. Static
   is then at **4-8 %**, as Finding 118 expected.
4. **Photographic, animated, costs what Solid does** - 54 % against 55 %. Its
   lighting filters are drawn once; what costs is that anything moves at all
   (Finding 118, point 2). **No pictures need drawing ahead** (ADR-0154
   decision 5's fallback is not needed).
