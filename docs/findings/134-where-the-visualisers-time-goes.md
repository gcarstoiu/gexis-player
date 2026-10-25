# Finding 134 — Where the visualiser's time goes: the present, a third of it; turntables a third cheaper after

**Date:** 2026-10-21/22. **For:** George, after Finding 133 (*"Then let's do
a first"* - close the gap in our own engine before anything of Glass's).

## Scope

- **Device:** ShelvesPi (Pi 4, 1480 × 320), gexis-player `1.3.1+git25`
  (before) and the preview `1.3.1+git31` / gexis-system `1.3.1+git29` (after:
  `peppy-cheaper` merged into `preview-1021`), CPU pinned at 1.8 GHz for the
  measurements, real music through Lyrion at volume 5 with the meter's volume
  cut held at 0 dB (as in Finding 133; restored afterwards).
- **Profiled** with py-spy 0.4.2 (sampling, 200 Hz, 30 s, from a throwaway
  folder), five skins. **Measured** before and after with the harness of
  Finding 133: 60 s a skin, the driver's own process as % of one core.
- **Checked:** the visualiser's tests with the device's pygame (125 pass,
  among them every turned frame equal to the whole turn pixel for pixel at
  every step); the skin check, all five sizes, no problem; screenshots of the
  preview on the bar.
- **Not measured:** sofapi and the other sizes after the change; the
  `ondemand` governor after; memory on a turntable skin at 1280 × 800.

## Results

### 1. The profile (before)

| Skin | `display.update` (SDL's present) | Next |
|---|---|---|
| Accuphase | 44 % | PeppyMeter's needle redraw (background and foreground blits) 18 % |
| Marschal (spectrum) | 30 % | PeppySpectrum's bar drawing 40 % |
| Thorens, stepped | 40 % | the tonearm rotated again (`placed`) 11 %, repaint blits 12 % |
| Thorens, smooth | 39 % | the same, more often |
| Akai 77 | 39 % | repaint blits 15 %, reel draws 11 % |

**SDL's present costs about 1.75 ms of processor for any rectangle**
(measured on ShelvesPi: a 40 × 40 box 1.75 ms, the whole window 3.8 ms, three
calls 5.1 ms against 3.2 ms for one call with the same three boxes). The
driver presented separately for the meters, the ticker, the turning parts
and the spectrum: 52-55 presents a second on Thorens and Marschal S+M.
SDL's renderer API with a streaming texture was no cheaper (1.24 ms for a
small box, 9.4 ms for the whole window).

### 2. The changes (`peppy-cheaper`)

- **One present a frame:** the copy to the window is made at once, the
  present waits for the frame's end, the rectangles merged.
- **The tonearm's last turn kept** instead of made again in every repaint of
  every box it crosses.
- **A record or a reel boxed by its reach** - the farthest visible pixel from
  its centre - instead of its picture's diagonal (a round 200-pixel record:
  206 pixels square instead of 288), its sixty turned frames kept cut to it.

### 3. Before and after (same harness, same skins)

| Skin | Before | After | Change |
|---|---|---|---|
| Accuphase | 13.7 % | 13.1 % | −4 % |
| Marschal (spectrum) | 19.4 % | 19.6 % | none |
| Marschal S+M | 22.0 % | 16.3 % | −26 % |
| Thorens | 26.8 % | 18.0 % | −33 % |
| Pioneer Gold | 17.8 % | 13.3 % | −25 % |
| Akai 77 | 16.8 % | 13.5 % | −20 % |
| Thorens, *Smooth* | 45.2 % | 24.6 % | −46 % |
| Pioneer Gold, *Smooth* | 36.1 % | 19.8 % | −45 % |
| Akai 77, *Smooth* | 30.3 % | 21.9 % | −28 % |

The compositor and the GPU work less too (Thorens: labwc 7.5 → 3.4 %, GPU
19 → 10 %). Presents a second now one a frame at most: Thorens 52.8 → 30.2,
Marschal S+M 55.3 → 30.2, Akai 33.4 → 26.5. Against Glass (Finding 133,
with its tap): Thorens 18.0 against 8.9 %, Akai 13.5 against 7.8 %, the
needle meter 13.1 against 6.6 %.

### 4. Memory

- Our driver held 150 MB hidden and 238-278 MB shown on ShelvesPi. The
  first show of a needle skin adds the skin's needle pictures: PeppyMeter
  rotates the needle in advance for every quarter degree of its swing (392
  pictures for Accuphase, 36 MB measured on their own). Its cross-skin cache
  is off in our configuration (`use.cache = False`), so they are the current
  skin's (and, with rotation on, the next one prepared).
- Run-length-encoding them (SDL's RLE) was tried on the device: memory went
  up (+44 MB against +36), and blended pixels differed by one level in every
  picture, so it was not taken.
- About 55 MB of the total is Mesa's libraries mapped for SDL's renderer
  (shared, read-only file pages).
- Turning frames now take their reach rather than the diagonal (less memory
  on turntables; not measured after on the 1280 × 800 skins that grew to
  500 MB in Finding 133).

## What is left

- **Needle and spectrum skins are where the gap to Glass remains** (about
  twice its cost): one present a frame (about 1.75-3.8 ms each, up to 30 a
  second) and the engines' own drawing - PeppyMeter's needle redraw blits the
  background and the foreground for every needle step, PeppySpectrum draws
  its bars. Both are in the vendored engines.
- **Our black box over Marschal S+M's spectrum** (Finding 133, Open) is
  there before and after.
