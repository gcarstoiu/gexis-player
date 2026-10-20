# Finding 131 — The visualiser shown without its picture: only what the needles repaint comes back

**Date:** 2026-10-20. **For:** George's two photos of sofapi's visualiser
(*"Also again issues with the visualiser ... make it more robust. Add also a
better coverage set of tests"*).

## Scope

- **Device:** sofapi (Pi 4, Waveshare 10.1" at 1280 × 800 on HDMI-A-1, a TV
  on HDMI-A-2 at 640 × 480 beside it), gexis-ui/-player `1.2.0+git23`,
  `gexis-skins-1280x800 0.6.0+git11`, labwc 0.20.2, SDL 2.32.4, pygame
  2.6.1. On the device **only read**: logs, config, packages, outputs, a
  screenshot of the panel (the idle screen was up, the visualiser hidden). The
  visualiser was **not** raised or restarted for this, so what happened at
  the moment of the photos is inferred from them and from the engine, not
  watched.
- **Off the device:** the shipped driver and the engine copied from sofapi,
  every skin of the five packs in the build cache, rendered headless (SDL's
  dummy driver) on Python 3.13 with pygame 2.6.1 in Docker
  (`packaging/skin-packs/frames.py`).
- **Not measured:** which compositor event replaces the window's buffer
  (labwc re-maximising a minimised window on `wlrctl focus` is the likely
  one); the spectrum engine's region under the same loss; the bars and the
  other sizes on their own hardware.

## Results

1. **The two skins.** Photo 1 is `104G5_Lyngdorf S+M`, photo 2
   `101G5_Free S+M` (gelo5-420; identified by layout - art at 24,400, 296 px
   wide; time at 366,591 - and by the journal, which logged both this
   morning). Both have a full, opaque 1280 × 800 `screen.bgr`.
2. **Photo 2 is a frame whose full picture is gone.** Its brass frames,
   rivets and panels - `Free.jpg` - are absent; what shows is the meter faces
   with stepped tops and the brass rail under them, the art, and the text over
   beige boxes, on white. That is exactly what PeppyMeter repaints after it
   starts: it draws `screen.bgr` and the meter's pictures **once, in
   `Meter.start()`**, and from then on only the box around each needle
   (`CircularAnimator`), while our layer redraws its text over its own crops
   of the background. The stepped tops are the edges of the needles' boxes.
   The white is the page behind the window - the player's own transport row
   shows through at the bottom of both photos.
3. **Measured headless, every skin:** after a lost frame, two seconds of
   needle frames bring back **0-31 % of the 1280 × 800 frame (median 4 %)**;
   10.7 % for Free S+M, 1.6 % for Lyngdorf. The other packs: 800 × 480
   0-46 % (median 5 %), 1280 × 400 0-51 % (9 %), 1480 × 320 0-40 % (11 %),
   1920 × 1080 0-31 % (3 %). The frame rendered this way for Free S+M has
   photo 2's pattern.
4. **Nothing painted it again.** Skins change at track changes, while the
   window is minimised; the driver draws nothing of its own while hidden
   (ADR-0019 as amended), and the next full frame was the next skin change.
5. **Also found by the same check:**
   - five skins of the 1280 × 800 pack leave part of the frame unpainted when
     they start (`vertical-turntable-blue` 4 %): on a player, the skin before
     showed there;
   - `134G5_Bose S+M` (1480 × 320 pack) has a 1480 × **310** picture, and
     `04G5_McIntosh Tube` (1920 × 1080) a 1920 × **1115** one: the engine
     draws them from the corner, while the text layer scaled them to the
     screen - so it erased titles back to a picture that was not there.
6. **Photo 1** (Lyngdorf's rack visible but washed light, its black areas
   showing the page) is not explained in full by the loss alone; its black
   areas are the regions the spectrum and the text layer repaint. Not
   reproduced here.

## What was changed (branch `viz-robust`)

- **`Rotation.refresh()`**: the whole frame of the skin on screen painted
  again from black - the meter restarted, the spectrum, text, motion and
  fanart layers set afresh, the whole window presented. Asked for by any
  window event pygame reports (logged `peppy: window ...`, so the next time
  the device says which events it sends) and 0.6 s and 2 s after the shown
  flag goes up (the core raises 0.25 s after it).
- **Every skin change starts from black.**
- **The text layer places a picture of another size as the engine does**
  (from the corner, on black), not scaled.
- **Tests:** six in `test_peppy_driver.py` and one in `test_peppy_render.py`,
  each failing without its change.
- **`make check-skins`** (part of `make image`): every skin of every pack,
  through the shipped driver and the engine - starts, paints every pixel,
  comes back from a lost frame pixel-exact. 978 skins in five packs, about a
  minute. With the driver on `next` before this branch, **all 286 skins** of
  the 1280 × 800 pack failed it.
