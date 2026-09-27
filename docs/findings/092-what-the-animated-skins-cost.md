# Finding 092 — What the turntable and cassette skins cost on the device, and what they drew wrong

**Date:** 2026-09-27
**Question:** ADR-0096 decision 4: measure the animated skins on `gexis` before
they reach an image. George, midway through: *"some of the measurements you are
making now are on skins that have some broken layouts. For some the title is
flashing, for other the album art is flashing or not fully painted, sometimes
the text is out of bounds, sometimes it looks as though the tonearm has a mask
that is hiding some elements."*

**Scope:** `gexis` (Pi 4, 3.8 GB), panel 1280x800 under Wayland, the Peppy
driver hand-deployed from branch `peppy-animated-skins`. LMS was playing
throughout (one album, 16 tracks) through squeezelite. Each CPU figure is
**one 20 s window after an 8 s settle**, on 12 of the 90 animated skins plus
George's own static skin (101G5_Free S+M, a meter and a spectrum) at the
start and the end. The memory sweeps loaded all 90 once in turn, 4 s each. The
drawing check was all 90 skins, three screenshots 0.4 s apart, one pass. **Not
measured:** smooth rotation against the stepped rotation built here (only
stepped exists: 6° frames, 8 redraws a second), a skin left running for hours,
Bluetooth or AirPlay as the source, the panel's responsiveness (ADR-0065) while
a skin turns, and panel temperature over a long run.

## Cost

Peppy's CPU is its process's user and system time over the window, as a share
of one core. Measured again after the drawing was fixed (below): the first
measurement drew less than it should have, as George said.

| Skin | Peppy, % of one core | Whole machine busy | squeezelite |
|---|---|---|---|
| 101G5_Free S+M (static, George's) | 34.9 / 34.8 | 12.8% / 12.3% | 2.6% |
| 141G5_01_Vertere Turn (vinyl, art on it, arm) | 32.0 | 10.8% | 2.4% |
| 141G5_02_Vertere Turn | 32.9 | 11.1% | 2.4% |
| 141G5_03_Vertere Turn (still art) | 18.3 | 7.1% | 2.1% |
| 196G5_01_SME60 | 38.2 | 12.4% | 2.5% |
| 145G5_01_McIntosh MTI100 | 29.5 | 10.3% | 2.3% |
| 153G5_Studer A810 (reels) | 21.8 | 7.8% | 1.9% |
| 157G5_Revox B77 | 28.9 | 10.2% | 2.3% |
| 161G5_Pioneer Cassette | 22.2 | 9.0% | 2.8% |
| 244G5_Pioneer CT_F1250 | 14.3 | 7.4% | 2.8% |
| t1800_Fisher | 12.0 | 6.3% | 2.5% |
| t1800_ReelTape | 22.2 | 8.2% | 2.1% |

**An animated skin costs what the static skin George uses costs** - 12 to 38%
of one core against 35% - because that one draws a spectrum. Upstream's 85-95%
of a Pi 4 does not happen here. `vcgencmd get_throttled` read `0x0` after every
window; the SoC sat at 66-70 °C.

## Memory

**PeppyMeter's needle cache held every circular skin's pre-rotated needles, up
to `cache.size = 20` skins, and let none go.** One pass over the 90 animated
skins grew the driver from 635 MB to 1.4 GB. The setting was upstream's default,
carried over in Phase 5. Rotation per track reaches that ceiling on any device,
animated skins or not. With `use.cache = False`:

- a first pass over the 90 went from 277 MB to 860 MB;
- **a second pass, without restarting, stayed between 860 and 976 MB and
  settled back at 861** - the allocator's high-water mark, not a leak;
- three skins cycled five times read the same RSS on every cycle.

The re-measurement above, after a restart: 349 to 489 MB.

## What was drawn wrong

The motion layer painted the background over **one rectangle round every moving
part** and drew back only what moved. Everything else inside - a title, still
artwork, a needle not moving, the badge - was gone until it next changed. That
is each of George's symptoms:

- the title flashed: the text layer redraws once a second for the clock, the
  spin wiped it eight times a second;
- the art was half painted where the record's or the arm's rectangle crossed it;
- the "mask" on the tonearm was the rectangle round the arm, repainted with the
  bare background;
- on a cassette the rectangle ran from one reel to the other, straight through
  the title between them.

Fixed by composing each region on its own, in upstream's z-order (background,
what turns, artwork, needles, title fields, tonearm, time and badge,
foreground), with the text layer's own changes going through the same compose.
After the fix, **no text, artwork or badge differed between the three frames on
any of the 90 skins**; the differences were the record, the reels, the arm, the
needles and the clock.

**Out of bounds:** 66 of the 90 give the clock its own size
(`time.remaining.fontsize`), which the renderer ignored for the digi face's
(45 px on the Vertere against the skin's 37). The Sansui cassette's digits ran
into its meter. Now honoured; none of the 99 other skins sets the key.

## Still open

- **27 of the 90 show no title at all.** Their only title field is the scrolling
  ticker (`playinfo.ticker.*`), which ADR-0096's first cut deferred. A decision
  for George.
- The clock's own face (`time.remaining.font`, e.g. `fonts/MyDigi.ttf`) is not
  used; it is drawn in ours. Not seen to clip after the size fix.
