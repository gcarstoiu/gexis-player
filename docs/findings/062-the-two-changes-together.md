# Finding 062 — ADR-0060 built, and both changes together

**Date:** 2026-09-24
**Question:** George: *"Go for a and then we test with c together."*
**Scope:** `gexis`, 2026-09-24, the UI built from this branch and deployed,
music playing, the same 170 px gesture, medians of 10 runs. **Four scrolls,
not the whole panel.** The flag was applied, measured and reverted; the
device is back as it was.

## ADR-0060, built and measured

`will-change: transform` on `.bg`, shipped in the UI rather than injected:

| scroll | before | with ADR-0060 |
| --- | --- | --- |
| artist grid | 25.5 drawn/s, 32.26% | **50.0 drawn/s, 5.57%** |
| artist page | ~30, 28.36% | **54.7, 3.28%** |
| browse artists | 44.2, 10.00% | **57.5, 0.00%** |
| queue rail | 39.1, 17.91% | 34.5, 18.77% |

**The rail is unchanged, exactly as predicted** — it sits on an opaque plate
and never saw the blur ([Finding 059](059-what-the-panel-pays-for-its-blur.md)).

## Both together

Adding `--disable-lcd-text`:

| scroll | shipped | ADR-0060 | **both** | where |
| --- | --- | --- | --- | --- |
| artist grid | 25.5 | 50.0 | **57.0** | compositor |
| queue rail | 39.1 | 34.5 | **58.9** | compositor |
| browse artists | 44.2 | 57.5 | **58.0** | main thread |
| artist page | ~30 | 54.7 | **56.8** | main thread |

**Every scroll at the 60 Hz ceiling, 0.00 % dropped, including the rail that
ADR-0060 could not help.** Two of the four still report a main-thread
scroll and reach the ceiling anyway, because with the background promoted
there is nothing expensive left to raster there.

**So the flag subsumes [Finding 060](060-the-queue-rails-own-cost.md).** The
rail's `box-shadow` and its per-row remove button cost about eight frames
each on a main-thread scroll and cost nothing on a composited one. If the
flag is taken, neither is worth changing for performance.

**`fps` reads 12–16 in this configuration and is wrong** — `PipelineReporter`
under-counts a scroll the compositor drives
([Finding 061](061-the-background-wants-a-layer-of-its-own.md)). The numbers
above are `drawn/s`, from `DrawToScheduleOverlay`.

## What the flag costs on the glass: not established

Now playing was photographed paused — so the track could not change — with
the flag and without it. **The two captures are identical: maximum
difference 0 across the whole frame.** The queue rail differs in 0.02 % of
pixels, consistent with the list resting a pixel differently between runs.

**This does not prove the flag is invisible.** `Page.captureScreenshot` may
composite into a surface that never applies subpixel antialiasing, in which
case two captures would be identical whatever the flag does. The shipped
capture's title edges measure a maximum chroma of 18 of 255 — already
greyscale — which fits *both* "this panel never renders subpixel text" and
"a screenshot cannot show it". **Nothing here separates them.**

**Only the panel itself can answer this**, with George looking at it. The
measurement is cheap to arrange and the answer is one he has to give.

## What this does not settle

- **The rest of the panel under the flag.** Four scrolls were measured. The
  still screens, every open/close animation and the idle screen were not.
- **Text everywhere else.** Two screens were photographed.
- **Whether ADR-0060 is still needed if the flag is taken.** It costs
  nothing, it is already built, and it does not depend on a browser flag —
  but under the flag it changes no number in this table.
