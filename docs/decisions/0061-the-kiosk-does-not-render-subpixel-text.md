# ADR-0061 — The kiosk does not render subpixel text

**Status:** **Accepted**, 2026-09-24. George, having run the panel with it:
*"C works. I am but seeing any odd things with the fonts."*
**Date:** 2026-09-24
**Relates to:** [ADR-0060](0060-the-panel-background-gets-a-layer-of-its-own.md)
(the background's layer, which this makes redundant but does not replace),
[Finding 061](../findings/061-the-background-wants-a-layer-of-its-own.md)
(the flag identified and first mis-read),
[Finding 062](../findings/062-the-two-changes-together.md) (both together),
[Finding 060](../findings/060-the-queue-rails-own-cost.md) (the rail's own
cost, which this subsumes)

## Context

Every list on the panel scrolled on the main thread — the artist grid, the
artist page, the browse panes, the queue rail. Finding 032 saw this in 2026
and blamed its own synthesised touches; with real touches through
`/dev/uinput` it was still true, so that caveat was resolved in the other
direction.

The reason is Chromium's `kNotOpaqueForTextAndLCDText`. A scroller whose
contents are not opaque cannot keep subpixel text antialiasing if the
compositor scrolls it, so Chromium keeps the scroll on the main thread
instead. **Every screen on this panel draws over a translucent veil**, so
every one of them pays.

And a main-thread scroll re-rasters whatever it damages every frame, which
is what made the background's blurs (Finding 059) and the queue rail's
shadow and remove button (Finding 060) cost what they cost.

## Decision

**`--disable-lcd-text` in `gexis-kiosk-start`.**

| scroll | shipped | ADR-0060 | **with this** |
| --- | --- | --- | --- |
| artist grid | 25.5 drawn/s | 50.0 | **57.0** |
| queue rail | 39.1 | 34.5 | **58.9** |
| browse artists | 44.2 | 57.5 | **58.0** |
| artist page | ~30 | 54.7 | **56.8** |

**Every scroll at the 60 Hz ceiling and 0.00 % dropped**, including the
queue rail, which ADR-0060 could not help because it never saw the blur.

## Why this is not a loss

**It is not clear the panel was rendering subpixel text at all.** The
shipped now-playing title, over a near-neutral backdrop, measures a maximum
edge chroma of 18 of 255 — greyscale antialiasing. Captures with and without
the flag are byte-identical, **which proves nothing**, because
`Page.captureScreenshot` may composite into a surface that never applies
subpixel antialiasing either.

**So the decision rests on George looking at the panel**, which is the only
instrument that could answer it, and did.

## Consequences

- **[Finding 060](../findings/060-the-queue-rails-own-cost.md) is subsumed.**
  The rail's `box-shadow` and its per-row remove button cost about eight
  frames each on a main-thread scroll and nothing on a composited one.
  Neither is worth changing for performance now. *(The remove button is
  being replaced anyway, for reasons that are not performance —
  [ADR-0062](0062-the-queue-removes-by-swipe.md).)*
- **ADR-0060 stays.** Under this flag it changes no number, but it is one
  CSS line, it costs nothing, and it does not depend on a browser flag
  surviving a Chromium upgrade.
- **It is a global flag.** It applies to every pixel of text the kiosk
  draws, not only to lists. This is why the whole 17-scene pass is run
  under it rather than the four scrolls that motivated it.
- **The remote settings surface is unaffected** — it runs in someone else's
  browser (ADR-0032).
