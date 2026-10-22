# Finding 136 — A black box after a skin change: the spectrum kept the first skin's box

**Date:** 2026-10-22. **For:** George (*"Fix also the last two so I check
everything"*), on the black box over Marschal S+M seen in Findings 133-134.

## Scope

- **Device:** ShelvesPi (1480 × 320), gexis-player `1.3.1+git48`, music
  through Lyrion at volume 5; the visualiser's settings, Lyrion's queue and
  volume restored after each run.
- **Measured:** the share of pure-black pixels in the box 240-393 × 65-160
  (6 % is the skin's own shadow), from screenshots 1-75 s after the skin
  was shown; the fix tried on a patched copy of the installed driver, the
  packaged one put back after (`dpkg --verify` clean).
- **Not tested:** the other sizes; every pair of skins - the pair here is the
  rotation's default start and a skin whose spectrum sits elsewhere.

## Results

1. **The box is the first spectrum skin's.** In both screenshots that had it
   the extra black was one rectangle, 240-1183 × 65-213, with the meter face
   and the new spectrum painted over parts of it: MarschalSpectrum's
   spectrum box (240,65, 1149 × 148), the album art covering the rest.
   Pure black (0,0,0) - not that skin's picture, which is dark brown there.
2. **It needs the visualiser to have started on a skin with its spectrum
   elsewhere.** Started on Marschal S+M: no box in 16 screenshots over
   several sequences. Restarted on MarschalSpectrum (the default) and changed
   to Marschal S+M: 61 % black at 1 s, 35 % at 75 s as the needles repaint
   their boxes.
3. **Cause:** PeppySpectrum takes `util.screen_rect` once, when it is made,
   as its container's own box and content; our `SpectrumState.follow` moves
   `util.screen_rect`, the backdrop and the bars to each skin's section but
   left the container's box at the first skin's. That box is painted black
   over a later skin, and a backdrop of a colour or a gradient is sized to it.
4. **With the container's box and content following each skin**, the same
   sequence gave 6 % at every moment from 1 s to 75 s.

## What changed

`SpectrumState.follow` sets the engine's `bounding_box` and `content` to the
skin's spectrum box before rebuilding its images. A test drives it through
two skins with different boxes.
