# Finding 026 — The static skins are the spectrum-only ones; PeppySpectrum is not running

**Date:** 2026-09-16
**Raised by:** George, watching the panel: "not all skins have the animations
working... one with a vinyl disc in the background that is completely static."
**System:** `gexis`, stock PeppyMeter alone from `/tmp/spike`, fed by our
visualisation service's passthrough pipe, music playing.

## Measured

Two frames three seconds apart, same skin, compared byte for byte:

| skin | `meter.visible` | result |
|---|---|---|
| `galaxy-spectrum` | `False` | **identical — static** |
| `gold` | (absent, so visible) | **differ — animating** |

**Cause: `meter.visible = False` skins draw no meter by design.** Their motion
is the spectrum, and PeppySpectrum is not running — only PeppyMeter is. Six of
the wrapper's fifteen 1280x800 skins are spectrum-only, which matches "not
all skins" rather than "some skins are broken".

Nothing is wrong with those skins, the levels, or the passthrough pipe: the
spectrum half of the screen has no renderer yet.

## Consequence for Phase 5

The two engines must run **in one process**, which is what foonerd's Volumio
wrapper does and what ADR-0026's amendment already puts on us: our own driver
imports both. Until it exists, every spectrum-only skin is a still image.

Gelo5's corpus has the same shape — 3 of its 84 sections are spectrum-only,
and 13 carry a `spectrum.name` link — so this is not specific to the stock
skins.

## Not established

- Whether PeppySpectrum renders correctly on this hardware at all: it has
  never been started here.
- Whether the two together stay inside the Pi 4's headroom. PeppyMeter alone
  measured 12-29 % of one core (Findings 023, 025).
