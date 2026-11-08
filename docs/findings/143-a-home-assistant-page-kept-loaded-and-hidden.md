# Finding 143 — A Home Assistant page kept loaded and hidden

**Date:** 2026-11-07. **For:** Phase 35 (`ph-ha-page`): before amending
ADR-0176 to keep one page loaded, so that showing it is at once (George,
2026-11-07: measured first). What a hidden, idle Home Assistant page costs a
Pi 4 beside the panel, and what the page inside can tell.

## Scope

- **Device:** sofapi, a Raspberry Pi 4 Model B (Rev 1.5, 4 GB), the Phase 35
  preview (1.14.0+git25), Chromium 156 under labwc, on Wi-Fi. Nothing
  playing: the DAC closed throughout.
- **The page:** the Home Assistant view made for this player, idle as it
  would be kept: a dim clock on black, updated once a second, no camera
  connection and no video (the Home Assistant side's description; the video
  elements were counted, see below). One websocket to Home Assistant.
- **How it was framed:** an iframe added to the panel through DevTools, with
  Phase 35's sandbox (`allow-scripts allow-same-origin`), at the screen's
  size, hidden in one of two ways: `display: none`, or `visibility: hidden`.
  Not the built feature.
- **Two runs:**
  1. The panel as it was after the kiosk's restart (1.5 minutes), the page
     hidden with `display: none` (3 minutes), switched to `visibility:
     hidden` (2 minutes), revealed in place (30 s), removed (1 minute). The
     idle screen came up by itself during the second phase, so this run's
     processor figures after that point compare different screens.
  2. The idle screen put up first and kept up throughout: 1 minute without
     the page, `visibility: hidden` (2.5 minutes), `display: none` (2.5
     minutes), removed (1 minute).
- **Read:** `/proc/stat` every second, per process, Chromium's grouped by
  process type; free memory and Chromium's proportional set size (PSS) by
  process type every 10 s; temperature and throttling every 10 s. Inside the
  frame, at the start and end of each phase: `document.visibilityState`,
  animation frames in 2 s, `performance.timeOrigin` (a reload changes it),
  the JS heap, the viewport's size, and how many video elements there are and
  play. Numbers and states only: no text from the page, no screenshots.
- **Not tested:** music playing beside it; a page that is not idle (a hidden
  page that plays video); hours rather than minutes; a crash of the frame; a
  bar or another Pi.

## Results

1. **Memory: about 60-90 MB.** Chromium's PSS, without the page → hidden:

   | Run | Without | Hidden | Removed |
   |---|---|---|---|
   | 1 | 462 MB | 537-541 MB | 493 MB |
   | 2 (idle screen) | 499 MB | 560-564 MB | 508 MB |

   Free memory fell by 90 MB (run 1) and 45-50 MB (run 2), from about
   2.4 GB. The page's own JS heap read 21-26 MB.

2. **The processor: nothing measurable on the whole.** Run 2, all four cores,
   with the idle screen up throughout: 18.3 % without the page, 18.1 %
   `visibility: hidden`, 17.7 % `display: none`, 17.9 % removed. Chromium's
   renderers together: 16.0 % of one core without, 18.7 % and 17.4 % hidden,
   15.5 % removed, so the page is a few percent of one core, inside the
   run-to-run spread. Run 1, against a quiet screen, read 3.7 % → 7.3 % of
   all cores (renderers 1.0 → 7.0 % of one core) over its first 3 minutes,
   which include the page settling after its load. The temperature did not
   move (58.9-62.3 °C).

3. **Hidden, it draws nothing: no animation frames** (0 in 2 s, both ways of
   hiding, in both runs). Revealed, 102 frames in its first 2 s and 120 in
   2 s thirty seconds later.

4. **The page cannot tell it is hidden.** `document.visibilityState` read
   `visible` and `document.hidden` false in every phase, hidden or not: the
   state follows the browser's tab, not the frame.

5. **Revealed in place, it is not reloaded:** `performance.timeOrigin` was the
   same from the first probe to the last, through both ways of hiding and the
   reveal.

6. **`display: none` lays it out at nothing.** Framed hidden that way from
   the start, its viewport was 0 x 0 (run 1), so a reveal has the page lay
   itself out first; `visibility: hidden` kept it at 1280 x 800. A frame
   switched to `display: none` after being laid out kept its last size
   (run 2).

7. **No video.** No video element in any phase: the idle page opened no
   stream, as described.

## What it means for Phase 35

- Keeping one idle page loaded costs memory, not processor: about 60-90 MB on
  a 4 GB Pi 4 with about 2.4 GB free. On a 2 GB Pi it would be a larger
  share; not measured.
- `visibility: hidden` is the way to hide it: as cheap as `display: none`
  here, and laid out at the screen's size, so a reveal has nothing to do.
- The player cannot make the page stop its work: a hidden page that plays
  video goes on decoding it, since the page still reads itself as visible.
  Stopping is the page's own business, from Home Assistant's state (the
  Home Assistant side's camera view idles unless Home Assistant says the
  screen is showing it).
- Whether a frame that crashes while hidden can be seen from the panel was
  not tested.
