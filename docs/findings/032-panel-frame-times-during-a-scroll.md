# Finding 032 — Frame times on the panel during a scroll: what the instruments answered, and why the cause is still unattributed

**Date:** 2026-09-17
**Question:** George, after Phase 7 step 4c: the New Music strip was *"95%
there"* — could frame times be measured to find the rest?
**System:** `gexis` on the Phase 6 image with Phase 7 hand-installed, panel
Chromium 152 under labwc/Wayland with `--enable-gpu-rasterization
--use-angle=gles`, CPU governor `ondemand` (ADR-0039 was reverted before
this). Driven over the DevTools protocol, with a debugging port added to
`/usr/local/bin/gexis-kiosk-start` **temporarily** and the file restored
afterwards (verified byte-identical to `stage-gexis/04-ui/files/`).

**Scope:** synthetic drags only — no finger ever touched the glass during
these numbers. Two runs per variant, which is the finding's main limitation.
One strip of ten 176 px cards; nothing here covers the long lists of steps 6
and 7.

## Result

**5–9 % of scrolling frames are dropped**, and **which part of the screen
causes them is not established.**

### Two instruments answered a different question first

1. **`requestAnimationFrame` deltas: a flat 16.8 ms, every variant, no
   frame over 20 ms.** The strip scrolls off the main thread, so the main
   thread's own cadence stays perfect while frames are being dropped
   elsewhere. It measured that the page was idle, not that the screen was
   smooth.
2. **Chromium's frame trace with `benchmark,viz,input,latency` and the
   timeline frame category: zero frame events**, which reads exactly like
   "nothing was dropped". `PipelineReporter` lives in
   `cc,benchmark,disabled-by-default-devtools.timeline.frame`; without `cc`
   the trace contains no frames at all. The fate of each frame is in
   `args.frame_reporter.state`, not `args.state`.

Both produced a clean, plausible-looking result while answering nothing —
the shape `docs/LESSONS.md` exists for.

### What the working measurement shows

Per variant, scrolling frames and the share dropped:

| variant | 2 runs combined | per run |
|---|---|---|
| baseline | 6.9 % | 8 drops, then 1 |
| backdrop hidden | 5.5 % | 2, then 5 |
| artwork bleed blurred 24 px instead of 72 px | 7.1 % | 4, then 5 |
| backdrop promoted + 24 px blur | 6.2 % | 5, then 3 |
| mask removed (both `mask-image` and `-webkit-mask-image`) | — | see below |

**The run-to-run spread is larger than the differences between variants.**
An earlier single run per variant had made the shared backdrop look
decisive (9.5 % against 1.6 %); a second run of the same two configurations
did not reproduce it. Findings 003/004 produced exactly this once before,
which is why tier 3 requires 20 runs and a distribution: **the single-run
comparison here was worth nothing, and is recorded so the next person does
not repeat it.**

### Two things that are worth keeping

- **`will-change: transform` on the mask wrapper earns its place.** With it
  removed, one run measured 31.9 % dropped against 9.5 % — a threefold
  difference, far outside the spread the other variants showed. One run
  each, so it is a strong hint rather than a measurement.
- **A mask must be cleared in both properties to be tested.** The first
  "no mask" variant only set `mask-image: none`, leaving the element's
  `-webkit-mask-image` in force, so it measured the masked case twice.

### The caveat over all of it

**Every frame is reported `SCROLL_MAIN_THREAD`,** in every variant. Touch
events synthesised through the protocol are delivered to the renderer
rather than through the browser's gesture pipeline, so this harness may be
producing the stutter it measures. `Input.synthesizeScrollGesture`, which
does use that pipeline, scrolled nothing in this layout and produced no
scrolling frames at all.

**So these numbers do not establish what a finger sees.**

## What was done about it

Nothing further. The changes already in (artwork at the size drawn, no
per-frame layout reads, the mask off the scrolling element, containment,
one shared backdrop) took the strip to George's *"95% there"*. Attributing
the rest needs either an instrument that drives real input or a 20-run
distribution; guessing from single runs is what this finding exists to
prevent.

**Revisit at steps 6 and 7**, where the artist grid (917 rows) and Browse's
album lists make any real cost larger than the noise floor measured here.
