# Finding 113 — The panel on a 1920 × 1080 screen

**Date:** 2026-10-07. **Asked by:** George: *"also run the performance check
in the larger screen"*.

## Scope

- **Measured:** `tools/panel-frames.py`, 12 runs of each of the 16 scenes,
  `--playback playing` - the same tool, runs and scenes as Finding 112's last
  measurement on `gexis`.
- **Device:** a second Pi 4 (4 GB), fresh from the 0.9.2 image, then the
  preview `0.9.2+git60` (core, UI, player) with `gexis-system` `+git174` -
  which carries Finding 112's fix (the hidden visualiser does not draw). An
  IQaudio DAC+, Wi-Fi.
- **Screen:** the Waveshare 13.3" (H), 1920 × 1080, so Chromium runs at scale
  1.5: the page is 1280 × 720 CSS px drawn on 2.25 times the pixels of
  `gexis`'s 10.1" (1280 × 800, scale 1).
- **Playing:** Lyrion's random mix on that player, at 20 % volume, so the
  queue outlasted the run. The CPU clock stayed at 1.8 GHz under load, 68-72 °C,
  no throttling (`data/113/guestpi-clock.log`).
- **Not compared:** the two devices' libraries are the same server's, but
  the queues differ (`gexis`'s was an album, this one a random mix), so the
  queue rail's scroll is not comparable - here the queue was too short to
  scroll at all.

## Result

Scrolling is the same on both screens: every scroll scene dropped a median
0 %. **Opening a screen drops more frames on the larger screen**, Home most:

| Opening | `gexis`, 10.1" 1280 × 800 (Finding 112) | 13.3" 1920 × 1080 |
|---|---|---|
| Home | 1.21 % | **8.97 %** (max 42.24 %) |
| Settings | 0.00 % | 3.17 % |
| Queue | 0.96 % | 3.51 % |
| Artist page | 1.90 % | 4.38 % |
| Playlists | 1.00 % | 3.01 % |
| Radio | 3.90 % | 5.10 % |
| Albums | 2.96 % | 3.08 % |
| Artist grid | 1.98 % | 2.52 % |

Median dropped frames; full output in `data/113/guestpi-13.3in.txt`. Four
scenes were marked *disturbed* once each (something else drew during the
run); medians over 12 runs absorb one.

## What it means

A larger screen costs the panel's opening transitions, in proportion to what
they draw: Home - a row of cards and a strip of covers sliding in - most.
Where the time goes on this screen has not been traced; Finding 112's trace
was taken on `gexis`. Whether Home's 9 % is visible to a person was not
asked.

## Not taken further

George, on the device: *"record the learnings about the 13.3 inch screen but
do not investigate further. On device it feels fine."* The numbers stand as a
measurement; nothing is changed for them, and no trace was taken.

## The tool, corrected

The first two runs on this screen failed after their first scenes: the
virtual touch screen had a fixed 1280 × 800 range, which the compositor
stretches over the whole display, so on a 1280 × 720 page every tap landed
about 11 % too high. The range is now the page's own size, read at start;
on `gexis` that is 1280 × 800, as before.
