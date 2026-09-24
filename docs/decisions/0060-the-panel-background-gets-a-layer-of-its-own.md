# ADR-0060 — The panel's background gets a compositor layer of its own

**Status:** **Accepted**, 2026-09-24. George: *"Go for a"*, having seen the
before/after and the pixel difference.
**Date:** 2026-09-24
**Relates to:** [ADR-0041](0041-no-live-blur-behind-a-sheet.md) (no live
blur behind a sheet — the same cost, found in a different place),
[Finding 059](../findings/059-what-the-panel-pays-for-its-blur.md) (the
blurs are what every scroll pays for),
[Finding 061](../findings/061-the-background-wants-a-layer-of-its-own.md)
(this measurement, and the correction that produced it),
[Finding 060](../findings/060-the-queue-rails-own-cost.md) (the rail's own
cost, which this does not touch)

## Context

`PanelBackground` draws two blurred layers behind every screen: a
`blur(70px)` weave and a `blur(72px) saturate(1.7)` bleed of the artwork.
They are drawn once, they do not animate, and they cost nothing while the
panel is still.

They cost during a scroll. A blur is re-evaluated over the region a frame
damages, and a scroll damages the whole scroller — so the cost is the
scroller's *area*, which is why Finding 058 eliminated eight candidates
inside the artist grid without moving the number: emptying the tiles,
cutting the list from 39,751 px to 6,013, stopping the photo fetches and
removing all 917 `IntersectionObserver`s change no area.

The queue rail is the control. It sits on `--bg-panel: #16232c`, fully
opaque, which occludes the blur beneath it — and it is indifferent to all of
this.

## Decision

**One declaration on the background's own element.**

```css
.bg {
  will-change: transform;
}
```

The blur is then rastered once into a compositor layer of its own and
reused, instead of being redrawn inside whatever a scroll damages.

| artist grid | dropped | fps | frames drawn/s |
| --- | --- | --- | --- |
| as it ships | 29.32% | 27.8 | 27.8 |
| **with this** | **4.06%** | **52.9** | 52.8 |
| both blurs deleted (the ceiling) | 2.44% | 51.6 | 52.8 |

**As good as deleting the background, and it changes nothing on the glass.**
Photographed with playback paused, so the artwork could not change between
captures: **the maximum difference is 2 of 255, and 0.00 % of pixels differ
by more than 4.** Deleting the blurs changes 73 % of them.

## Alternatives, all measured

- **`transform: translateZ(0)`** — 49.1 fps. The same idea, the older
  spelling, and slightly worse here. `will-change` says what is wanted
  rather than implying it through a no-op transform.
- **`contain: paint`** — 26.6 fps, no help. It clips; it does not promote.
- **Serve a photograph of the background, recaptured on track change**
  (George's proposal) — 50.7 fps, and pixel-exact by construction. It works
  and it is kept in reserve, because it needs a capture, a cache and an
  invalidation, where this needs a line. **It is the fallback if the layer's
  memory ever matters.**
- **A smaller blur radius** — 9 px costs nearly what 70 px costs. It is the
  filter's existence, not its radius.
- **Deleting the blurs** — the ceiling, and a different-looking panel.
- **An opaque background on each scroller** — 0.00 % dropped at 13.9 fps.
  It improves the metric by halving the frame rate.

## Consequences

- **A full-panel compositor layer is roughly 4 MB and has not been
  measured.** If it ever matters, George's photograph is the way out and
  costs nothing on the glass either.
- **This does not help the queue rail**, which never saw the blur. The
  rail's own 17.9 % is [Finding 060](../findings/060-the-queue-rails-own-cost.md)
  and is a separate decision.
- **It may stop mattering entirely.** If `--disable-lcd-text` is taken
  (tested next, at George's direction), every scroll runs on the compositor
  and no blur is re-rastered during one. This is still worth having: it is
  one line, it is free, and it does not depend on a browser flag.
