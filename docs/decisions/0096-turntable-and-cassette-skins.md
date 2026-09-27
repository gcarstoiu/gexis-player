# ADR-0096 — Turntable and cassette skins move

**Status:** **Accepted** — George, 2026-09-27: *"I want the other skins too. Go
ahead!"*, then, given six decisions, *"All recommended"*. **Amends
[ADR-0026](0026-peppymeter-native-process-integration.md)'s Scope**, which left the
turntable and cassette handlers out because George had not ruled on them.
**Building; not measured, not shipped.**
**Date:** 2026-09-27
**Raised by:** George asking whether any skin animates a platter or a deck.
None of the 99 in the corpus does - no `vinyl.`, `tonearm.` or `reel.` key, no
`albumart.rotation = True` - and the handlers that would draw them were never
vendored.

## What exists

Researched 2026-09-27; the scan and its sources are summarised here because the
research itself lived in a session scratchpad.

- **One source.** `github.com/foonerd/peppy_templates`, where the Volumio forum's
  template threads moved on 2026-01-02. Gelo5, whose pack is the current corpus
  (ADR-0051), commits there himself.
- **Nothing native to this panel turns a platter.** At 1280x800 there are four
  reel-to-reel skins (`1280x800_t1800_pack7`, by Pakit S). The Gelo5 sets are
  **1280x720**: 48 turntables (`g5_710_Turntables`: spinning vinyl, the album art
  on it, a tonearm tracking progress), 15 cassette decks (`g5_712_Cassette`) and
  20 reel-to-reel recorders (`g5_711_Tape_Recorder`).
- **The code is permissive.** `foonerd/peppy_screensaver` is MIT; its file headers
  carry 2aCD's (ISC) and foonerd's copyright. Both are GPL-compatible, and
  ADR-0025's combined work stays GPL-3.0. ADR-0026 called the handlers' licence
  surface GPL v3; the files themselves are MIT/ISC.

## Decision (George's six)

1. **The 1280x720 skins are shown letterboxed** - 40 px above and below. Asking
   Gelo5 for native 1280x800 versions, which he has offered to others, is
   George's to do or not.
2. **The same licence bar as the corpus already has.** The skins carry no terms
   of their own; the hosting repository's MIT is the grant, exactly as
   `PeppyMeter.doc`'s GPL is for the 99 shipped today (`skins/README.md`).
   **Fetched at build time, pinned by commit and sha256**, through the existing
   cache (ADR-0042) - never committed here.
3. **First cut: the motion, and what the renderer already draws** - title,
   artist, album, artwork, the source badge, time remaining. The skins leave
   room for more (a progress bar, elapsed and total time, volume, mute, shuffle,
   repeat, the next track); those are a follow-up, and until then the room is
   empty.
   **Amended 2026-09-27 (George, choice A of three):** 27 of the 90 place their
   title only as upstream's scrolling ticker, and showed none. Their ticker
   box now carries a still line - "Title • Artist • Album" in the ticker's own
   colour and separator, trimmed with "…" - drawn only where the skin has no
   title field of its own (nine have both). The scroll, and the next track it
   appends, stay deferred. Rejected: building the scroll now (a per-frame
   redraw, a new cost to measure), and leaving the 27 out of rotation.
4. **Measured on `gexis` before it reaches an image.** Upstream quotes 85-95% of
   a Pi 4 for a turntable skin at 1280x720 against 30-40% for a plain one; this
   device measured plain skins far below upstream (Finding 023, 12-17% of one
   core), so upstream's numbers predict nothing here. Memory is estimated at
   ~350 MB of precomputed rotation frames per turntable skin, against 3.8 GB
   installed and 2.7 GB available. Smooth against stepped rotation is measured,
   not assumed.
5. **Not Glass.** Upstream's replacement engine (`foonerd/glass`, Rust, MIT)
   claims half the CPU and a tenth of the memory, and was three days old when
   this was decided. Revisit when it has matured.
6. **Settings come after the measurement.** Rotation quality, speed, reel
   direction and adaptive spools are candidates for ADR-0022's inventory; which
   ones earn a row is decided on the numbers, and proposed to George before any
   is added.

## How (as built - filled in when it is)

The intent, from the research: keep our driver and `MetadataLayer` - the badge,
slot and font work is ours and stays - and add the three renderers that make
things move (upstream's vinyl, tonearm and reel classes, which depend only on
pygame), driven from `nowplaying.json`. Not the whole Volumio handler: it owns
the frame, runs the meter itself and brings its own text and badge path.

As built (2026-09-27): `gexis_peppy_motion.py` - a spinner for the vinyl (with
the art composited onto it) and for each reel, pre-rendered at 6° and redrawn 8
times a second; a tonearm rotated when it moves rather than pre-rendered. The
1280x720 packs are letterboxed at build time (`letterbox.py`). **Whatever moves
is repainted whole, in upstream's z-order** - background, what turns, artwork,
needles, title fields, tonearm, time and badge, foreground - and the text
layer's own changes go through the same compose; the first cut repainted only
the background and what moved, and George saw titles flash and art half drawn.
The clock takes the skin's `time.remaining.fontsize`. Measured in
[Finding 092](../findings/092-what-the-animated-skins-cost.md): 12-38% of one
core against 35% for George's static spectrum skin, and PeppyMeter's needle
cache turned off, which had grown the driver to 1.4 GB across the skins.

## Reversal conditions

If the measured cost does not fit beside the panel - ADR-0065's responsiveness
work is what it competes with - the motion is cut back (stepped rotation, a
smaller skin set) before it is dropped.
