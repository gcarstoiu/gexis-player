# Finding 037 — Why a blurred scrim costs this panel two thirds of its frames

**Date:** 2026-09-18
**Question:** George, on being offered the removal of `backdrop-filter`:
*"Why? Why is it costing so much on a device that should be able to render 2
4k screens. Before removing things let's answer that."*
**System:** `gexis`, panel Chromium 152 under labwc/Wayland,
ANGLE (Broadcom **V3D 4.2.14.0**, OpenGL ES 3.1, Mesa 26.2.2), LMS playing
a local track. Measured with `tools/panel-frames.py` and Chromium's own
trace.

**The rule this gives the design**, and the reason to record it rather than
fix each screen as it is found: **a live backdrop blur over a large area is
unaffordable on this panel**, whatever its radius, and Vulkan makes it
worse. A **static** blurred image costs almost nothing - the artwork bleed
behind every screen is one, and hiding it changes no number here. A solid or
gradient scrim costs nothing at all. Depth is affordable; live readback is
not.

**Scope:** one device, one GPU, one afternoon. Two sheets were measured -
the queue rail and the volume drawer - and both have full-screen scrims.
Nothing here is a claim about Chromium or the Pi 4 in general.

## Result

**It is not compute. It is a render-target round trip, every frame, on a GPU
built to avoid exactly that.**

### What it costs

**Interleaved, six rounds each**, playback held playing, every run asserting
the rail was open, the list longer than the gesture, and the scroll actually
moved. Sequential runs contradicted each other three times first; see "How
this was got wrong" below.

| queue rail, scrolling | fps | dropped |
|---|---|---|
| `backdrop-filter: blur(3px)` (as drawn) | **14.8-16.1** | 75-76 % |
| the same, on the Vulkan backend | **6.9** | 86 % |
| the static backdrop image blurred harder instead | **32.2** | 29 % |
| blur removed, scrim kept | **36.3** | 24 % |
| the scrim element removed entirely | **35.1** | 25 % |

| volume drawer, panel **still** | dropped |
|---|---|
| blur on (as drawn) | **71.2 %** |
| blur off | **9.3 %** |

Three things fall out of that:

- **The radius does not matter** - measured separately, 1 px costs as much
  as 8 px. The cost is the readback, not the filtering.
- **The dark scrim is free.** Removing the blur is worth 21 fps; removing
  the element as well is worth nothing (36.3 against 35.1, inside the
  spread). A sheet can still read as a sheet.
- **Area does not matter either.** The volume drawer's panel is a fraction
  of the rail's and its full-screen scrim costs the same - and it is the
  sheet this device opens most, on every volume change from a phone, over
  whatever screen is up.

**Removing the blur does not reach Phase 7a's target on its own.** 36 fps
against a 55 fps floor: the blur is about half the rail's cost and its own
list is the rest.

### Where the time goes

Chromium's frame pipeline, median per stage during the same scroll:

| stage | blur on | blur off |
|---|---|---|
| **EndActivateToSubmitCompositorFrame** | **24.51 ms** | **1.80 ms** |
| SendBeginMainFrameToCommit | 2.58 ms | 2.69 ms |
| Commit | 0.55 ms | 0.54 ms |
| RendererMainProcessing | 1.13 ms | 1.22 ms |

The frame is late in **draw-and-submit** and nowhere else. Input, main-thread
work and commit are unchanged. 24.5 ms against a 16.7 ms budget is about two
frames' worth of GPU time per frame, which is the ~73 % drop rate.

### And no processor is busy

Per-process CPU over 8-second windows, from `/proc`:

| | chromium (all processes) |
|---|---|
| rail open, blur on | **< 1 %** |
| rail open, blur off | **< 1 %** |
| rail closed | < 1 % |

The panel is not computing. It is **waiting on the GPU**.

## Why this GPU in particular

`backdrop-filter` cannot be drawn in one pass. The compositor must render
everything behind the scrim into a **separate render-pass texture**, then
sample that texture back to blur it, then composite the result - once per
frame, whether or not anything moved.

The Pi 4's V3D is a **tile-based deferred renderer**. It works by keeping a
small on-chip tile and writing each finished tile out to memory once. A
render-pass round trip breaks that: the tiles must be flushed to memory and
read back as a texture. Tilers exist precisely to avoid that traffic, and it
is their worst case - on shared LPDDR4, with the display scanout using the
same bus.

**On "it can drive two 4K screens":** that is *scanout* - a linear DMA read
of a finished framebuffer out to HDMI, the most optimised path in the
machine. It says nothing about the GPU's ability to do a full-screen
render-target round trip sixty times a second. Different engine, different
bandwidth, different question.

## What this rules out

- **Not a software fallback.** `SystemInfo.getInfo` reports
  `gpu_compositing: enabled`, `rasterization: enabled_force`,
  `opengl: enabled_on`.
- **Not the blur radius**, per the table above.
- **Not "only while scrolling".** An idle panel with the rail open drops
  73 % of its frames. There is no "blur while still, drop it while moving"
  mitigation, because a static blurred scrim costs the same.
- **Not the artwork backdrop.** `PanelBackground`'s blurred bleed is a
  *filter on an image*, rasterised once. Hiding it changed nothing (0.00 %
  either way).

## How this was got wrong

Three sequential runs of this experiment contradicted each other, and each
disagreement had a cause found only by asserting more state. They are
recorded because the instrument was honest every time and the experiment was
not.

1. **A list at its end.** Five scrolls per variant with no reset: after the
   first, the rail was already at the bottom and the gesture moved nothing.
2. **A rail with 18 rows.** The queue had been replaced by a short album, so
   the list ran out before the gesture did.
3. **Playback stopped.** The important one. A panel with nothing playing
   asks for almost no frames, so a *per-frame* cost has nothing to bite on:
   blur and no-blur measured identically at ~25 fps and the effect appeared
   to vanish. **These numbers mean something only while music is playing**,
   which is the only state in which anyone looks at the panel anyway.

A fourth failure was the harness refusing to measure at all, which is the
part that worked: a volume drawer left open swallowed the tap meant for the
queue button, and `must_be` stopped rather than measuring the wrong screen.

## What it does not say

- **Whether a *smaller scrim* would be affordable.** Both sheets measured
  have full-screen scrims. The volume drawer shows a small *panel* does not
  help, but a scrim covering a third of the screen was never measured
  cleanly - the run that tried it was one of the invalid ones above.
- **Whether a newer Mesa helps.** Vulkan *was* tested, by starting the
  kiosk with `--enable-features=Vulkan --use-vulkan=native` until
  `SystemInfo` reported `vulkan: enabled_on`, and it is **worse**: 6.9 fps
  against 15.0 for the same blurred rail. Without the blur it is slightly
  better (38.7 against 35.1), which is not worth changing a graphics
  backend for. The launcher was restored and verified by md5.
- **Anything about Settings' scrim or the rail's source sheet.** Both carry
  the same property and neither was measured; they are rare enough that
  nobody has complained about them.

## Correction to [Finding 034](034-what-the-panel-presents.md)

**That finding's idle control is wrong, and this is why.** It reported
71.25 % of frames dropped on an untouched panel with music playing, which
became Phase 9's opening question: *why is a playing panel never idle?*

It is. The 20-run pass was preceded by a validation run that ended on
`queue-rail-scroll`, and **nothing closed the rail** - so the idle control
measured a panel with the rail's blurred scrim over it. Today's
`queue-rail-open` measures **71.24 %**; the idle control, with the rail shut,
is asked for fewer than 25 frames in a whole window, which is what an idle
panel should look like.

**Everything else in Finding 034 reproduced** on 2026-09-18 with the same
instrument: New Music 46.0 fps / 2.6 % against 47.1 / 2.5, artist grid 24.0 /
49.0 against 23.1 / 50.7, queue rail 16.0 / 73.3 against 13.9 / 75.2. The
baseline stands; one control in it does not.

**The instrument has been changed** so this cannot recur: `Screen` closes the
rail after a rail interaction, and the idle control asserts that no scrim is
on screen before it measures.
