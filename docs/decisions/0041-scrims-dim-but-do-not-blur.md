# ADR-0041 — Scrims dim but do not blur

**Status:** Accepted — George checked the panel and kept it, 2026-09-18
**Date:** 2026-09-18
**Raised by:** Phase 9 step 1, chasing why a panel drops frames
**Evidence:**
[Finding 037](../findings/037-why-a-blurred-scrim-costs-the-panel.md)
**Amends:** the designs in `design/source/`, which draw every sheet over a
blurred backdrop

## Context

The designs put `backdrop-filter: blur()` behind four sheets: the queue
rail, its source sheet, Settings and the volume drawer. It is a live blur -
it blurs whatever is behind the element, which is the screen, which changes.

On this panel that costs two thirds of the frames. Finding 037 has the
mechanism and the numbers; the short of it is that `backdrop-filter` makes
the compositor draw the backdrop into its own texture and read it back
**every frame**, and the Pi's V3D is a tile-based renderer, for which that
round trip is the worst case. Chromium's own accounting puts the whole cost
in draw-and-submit: **24.5 ms against 1.8 ms**, on a 16.7 ms budget, with
the CPU under 1 % either way. The panel is not computing; it is waiting.

## Decision

**A scrim dims. It does not blur.**

- **No `backdrop-filter` anywhere in the panel.** Not at a smaller radius
  (1 px costs what 8 px costs), not over a smaller panel (the volume
  drawer's scrim costs the same as the rail's), and not on a different
  graphics backend (Vulkan is worse: 6.9 fps against 15.0).
- **A static blurred image is fine and stays.** `PanelBackground`'s artwork
  bleed is a `filter` on an image: blurred once when it is rasterised, then
  composited like any other texture. Hiding it changes no measurement.
  Blurring *that* harder when a sheet opens is available if a screen ever
  wants the impression of depth back - measured at 32 fps against 35 with no
  blur at all.
- **The dimming itself is free.** Removing the scrim element on top of
  removing its blur bought nothing (36.3 fps against 35.1, inside the
  spread), so sheets keep their dark layer and still read as sheets.

**Done 2026-09-18 for the queue rail and the volume drawer**, which is what
George checked and kept. Settings and the rail's source sheet still carry
the property and are left for the Phase 9 sweep; they are opened rarely and
never while something is scrolling underneath.

## Consequences

- **The design has a hardware constraint it did not have before**, and it is
  worth stating positively rather than as a veto: *depth is affordable, live
  readback is not*. A design asking for the look of blurred glass behind a
  sheet can have it from a pre-blurred image; it cannot have it from the
  live screen.
- **This does not meet Phase 7a's target on its own.** The queue rail goes
  from ~15 fps to ~36 against a 55 fps floor. The blur was about half of
  that screen's cost; its own list is the rest, and that is the same work
  the artist grid needs.
- **The volume drawer is the one that mattered most.** It opens on every
  volume change from a phone, over whatever is on screen, and it was
  dropping 71 % of frames while nothing was happening at all.

## Alternatives considered

- **A smaller blur radius** - measured, no help: the cost is the readback.
- **A smaller blurred area** - the volume drawer disproves the panel size
  mattering; a scrim covering a third of the screen was never measured
  cleanly and remains the one untested variant.
- **The Vulkan backend** - measured, worse for the blurred case and only
  ~10 % better without it, which does not justify changing how every pixel
  on the device is drawn.
- **Keeping the design as drawn** - the rail would stay at ~15 fps and could
  never meet the floor, and the volume drawer would keep costing 71 % of the
  frames every time a phone changes the volume.
