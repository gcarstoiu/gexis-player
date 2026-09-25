# Finding 067 — What the panel presents at the end of criterion 0

**Date:** 2026-09-25
**Question:** Does the panel meet Phase 7a's target — *under 2 % of frames
dropped on every interaction, and no interaction below 55 fps*?
**Scope:** `gexis`, 2026-09-25, the whole interaction set, 12 runs each,
music playing, ADRs 0060–0075 live and `--disable-lcd-text` in the kiosk.
Frames counted as `drawn/s` (`DrawToScheduleOverlay`), which is the honest
one — `PipelineReporter`'s `fps` under-counts a scroll the compositor drives
([Finding 061](061-the-background-wants-a-layer-of-its-own.md)).

## The scrolls meet it

| | drawn/s | dropped |
| --- | --- | --- |
| queue rail | **59.5** | 0.00 % |
| new music | 59.2 | 0.00 % |
| artist grid | 58.2 | 0.00 % |
| browse pane | 58.2 | 0.00 % |
| artist page | 56.9 | 0.00 % |
| settings | composited, nothing repainted | |

Every list is at the panel's 60 Hz ceiling and drops nothing. **Against the
baseline this began from**: the artist grid scrolled at 25.5 and dropped
32 %.

## The opens do not

| | drawn/s | dropped |
| --- | --- | --- |
| queue rail open | 52.7 | 3.18 % |
| artist grid open | 41.8 | 4.92 % |
| artist page open | 41.6 | 5.63 % |
| albums open | 41.7 | 5.26 % |
| radio open | 41.3 | 4.27 % |
| home open | 37.5 | 2.50 % |
| playlists open | 37.5 | 5.31 % |
| settings open | 30.2 | 4.00 % |

**Every screen change is 30–53 frames a second and drops 2.5–5.6 %**, where
the target is 55 and 2 %. In use each is one transition of 200–400 ms, so
5 % is a frame or two — the opens read as *fast* (150–250 ms to first paint)
rather than *smooth*.

**Two caveats on those numbers.** `settings-open` produced 7 usable runs of
12 — its trace is thin, so 30.2 is soft. `home-open` at 2.50 % is within a
whisker of the line.

**The still screens sit at 49.9 drawn/s and 0.00 %**, which is not a
shortfall: nothing is asking for more than the progress bar.

## What the remaining gap is made of

Measured while answering George's question about keeping a screen warm: the
transition cost is dominated by **leaving the home screen**. Hiding its
parts one at a time, with the same destination each time:

| leaving home → radio | busy in the 450 ms after the tap |
| --- | --- |
| home as it is | 280 ms |
| without the New Music strip | 190 ms |
| without the cards | 93 ms |
| without either | 94 ms |

So roughly **190 ms of a ~280 ms transition is home's own five cards and
twelve album covers being torn down**, against a ~93 ms floor for changing
screen at all. The destination barely matters — radio, which is nearly
empty, costs the same as the artist grid.

**The lever nobody has pulled** is keeping the home screen mounted rather
than destroying and rebuilding it — `content-visibility: hidden` is the
mechanism. It is untested here and it carries a real risk: a permanently
mounted screen can slow every other layout.

## What this does not settle

- **Whether the opens matter in use.** George, 2026-09-25: *"The panel feels
  fast based on current interaction."* That is one person on one evening.
- **A phone.** Everything here is the 1280×800 panel at a device pixel ratio
  of 1.
- **Whether keeping home mounted would work**, or what it would cost the
  screens that are on show.
