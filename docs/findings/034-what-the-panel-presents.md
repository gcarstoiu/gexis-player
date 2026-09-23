# Finding 034 — What the panel presents, measured through the kernel: a baseline, and the four ways the instrument lied first

**Date:** 2026-09-18
**Question:** Phase 7a criteria 2 and 3. George, after the queue rail landed:
*"Everything quite slow though."*
[Finding 032](032-panel-frame-times-during-a-scroll.md) had tried to
attribute this and could not — its own harness may have caused the stutter
it measured. So: an instrument that survives its own scrutiny, and a
baseline to hold Phase 9's work to.
**System:** `gexis` on the Phase 6 image with Phase 7a step 1 hand-installed
(artwork at the size drawn), panel Chromium 152 under labwc/Wayland, CPU
governor `ondemand`, LMS playing throughout unless stated.
**Tools:** `tools/panel-touch.py`, `tools/panel-frames.py`, both in this
repository.

**Amended 2026-09-18 — there was a fifth fault, and it is the one that
mattered most.** The idle control below was measuring **a queue rail left
open by the run before it**, whose blurred scrim costs 71 % of the frames on
its own. The "why is a playing panel never idle?" question this finding
handed to Phase 9 had a false premise: **an idle panel is idle.** See the
amendment at the end, and
[ADR-0041](../decisions/0041-scrims-dim-but-do-not-blur.md), which the chase
produced.

**Scope:** one device, one session, one bundle. The numbers below are for
**this** build; they are a baseline to compare against, not a claim about
Chromium, Wayland or the Pi 4 in general. Nothing here attributes a cause —
that is Phase 9's work, and this finding exists so that work can be judged.

## The instrument

**Input goes through the kernel.** `panel-touch.py` creates a multitouch
device on `/dev/uinput` shaped like the panel's own WaveShare (type B, slots
and tracking ids, `INPUT_PROP_DIRECT`), so events travel kernel → libinput →
labwc → Chromium. Finding 032's touches were synthesised over the DevTools
protocol, which delivers them straight to the renderer: every frame there
came back `SCROLL_MAIN_THREAD`, and that caveat could not be resolved.
**Confirmed reaching Chromium** by the panel's own report: a tap produces
`POST /touch` with the panel's user-agent (ADR-0036).

**Frames come from the compositor.** `PipelineReporter` events, with the
`cc` category, read from `args.frame_reporter.state` — the three corrections
Finding 032 recorded.

**The kiosk exposes the protocol through a switch, not a hand edit.**
`GEXIS_KIOSK_DEBUG_PORT` in `/etc/gexis/kiosk.env`, empty by default.
Finding 032 had to edit `/usr/local/bin/gexis-kiosk-start` and remember to
put it back.

## The four faults, before any number was worth anything

Each was found by checking the instrument, not by a result looking wrong.
All four produced confident, plausible numbers.

1. **Partial frames counted as dropped.** `STATE_PRESENTED_PARTIAL` reached
   the screen — part of the update (typically the main thread's) was not in
   it. Counting it as a drop reported **17.9 % dropped on a panel nobody was
   touching**.
2. **Fixed coordinates.** The first version swiped where the New Music strip
   sits *on Home* while the panel was showing now playing, and reported
   **25–31 % dropped for a gesture that scrolled nothing**. Gestures are now
   aimed at an element's own rectangle, and every step asserts which screen
   it is on before it measures.
3. **Playback uncontrolled.** A 20-run pass reported **57.7 % dropped for
   the idle control that had measured 0.00 % an hour earlier** — music had
   started in between. With LMS playing, Chromium sits at ~30 % CPU and the
   **minimised** PeppyMeter at ~13 %. Every run now holds the transport in a
   stated state, records it, and flags any run whose gesture changed the
   track.
4. **Every frame counted twice.** `PipelineReporter` is an async pair,
   `ph: "b"` and `ph: "e"`. Counting events rather than frames is how a
   60 Hz panel appeared to present **102 fps**. Frames are identified by
   `frame_source` + `frame_sequence`.

**A percentage alone is not a target,** which is why George declined the
single number he had first set. Its denominator is the frames the compositor
*wanted*, and that moves with whatever else is animating — now playing's
progress bar changes it — so the same panel scores differently depending on
the screen it is on. Frames presented per second *of the gesture* is the
number that means what it says, with 60 the ceiling. Runs with fewer than 25
frames carry no percentage at all and are reported as thin, never averaged.

## The baseline

**20 runs per interaction, LMS playing** - the state George uses the panel
in. `fps` is frames put on the screen per second *of the gesture*, ceiling
60. `dropped` is of the frames the compositor wanted.

| interaction | fps (median) | dropped (median, min-max) | frames/run |
|---|---|---|---|
| idle control (no input) — **void, see the amendment** | — | ~~71.25 %~~ (69.88-73.49) | 84 |
| home-open | 45.1 | 5.67 % (4.23-52.17) | 71 |
| new-music-scroll | 47.1 | 2.51 % (0.00-9.88) | 78 |
| artist-grid-open | 19.0 | 11.94 % (3.08-22.22) | 34 |
| artist-grid-scroll | 23.1 | 50.71 % (44.62-54.29) | 69 |
| queue-rail-open | 15.1 | 73.05 % (52.86-75.34) | 70 |
| queue-rail-scroll | 13.9 | 75.18 % (69.23-77.46) | 69 |

The rail rows were re-measured after the queue was moved to its first track:
the 20-run pass had the current track at position 99 of 100, so the rail was
showing **one row below it and there was nothing to scroll**. The line above
is the 8-run re-measurement with a full rail; the rest of the table is the
20-run pass.

**The ranking is George's own.** He called the New Music strip *"95 % there"*,
the artist grid slow, and the rail *"still choppy"*. The instrument, which
knows none of that, puts them at 47, 23 and 14 fps. That agreement is the
strongest evidence here that it measures what a person feels.

**Against the target** (Phase 7a criterion 4: under 2 % dropped, no
interaction below 55 fps, and George's go-ahead): everything fails. Nothing
reaches 55 fps; only the New Music strip is near 2 %.

### The result that was not expected: the panel is not idle when it is idle

**With LMS playing and nobody touching the panel, 71 % of the frames the
compositor wants are dropped**, and about 17 are presented per second. With
the player paused, the same control produces **fewer than 25 frames in the
whole window** - the compositor is barely asked for anything, which is what
an idle panel should look like. Measured both ways, 8-20 runs each.

So the panel is doing continuous work while music plays, before any
interaction, and every interaction is measured on top of that.

**PeppyMeter is not the cause.** It renders while minimised and costs about
13 % CPU with music playing (Chromium sits at ~30 %), which made it the
obvious suspect. Stopping `gexis-peppy` outright and repeating the idle
control: **68.45 %** dropped against 71.25 % with it running, and the rail
scroll 70.70 % against 75.18 %. Both differences are inside the spread of
the runs themselves. The service was restarted afterwards.

No other candidate was tested. That is Phase 9's work.

## What it does not say

- **No cause is attributed.** Not the list lengths, not the card weight, not
  the backdrop, not the meter's 13 %. Candidates belong to Phase 9, and this
  baseline is how they will be judged.
- **One device, one bundle, one session.** Nothing here has been repeated on
  another day, which Findings 003/004 and 032 both show is where
  measurements of this kind go wrong.
- **The idle control is not a smoothness measure.** With no gesture there is
  no rate worth reporting. It was included to show the harness was not the
  cause of what it measured - and with the player paused it does exactly
  that, producing almost no frames at all. With music playing it turned into
  the most interesting result in this finding instead.

## Amendment, 2026-09-18 — the fifth fault: the idle control was not idle

Phase 9's first step was the question this finding raised — *why is a playing
panel never idle?* — and the answer is that it was not idle.

**The control ran with a queue rail still open**, left there by the run
before it, and the rail draws a full-screen `backdrop-filter` scrim. That
scrim alone accounts for the 71 %. With nothing on screen but the screen, an
idle panel drops almost nothing.

**So every number in the table above stands, and the control does not.** The
interaction rows were each measured on their own screen and are unaffected;
what is void is the claim that they sit on top of a continuous 71 % floor.
They do not. There is no floor.

**Why it got past four rounds of instrument scrutiny:** the control was the
one measurement with no gesture, so the harness had nothing to assert about
which screen it was on — fault 2 above fixed exactly this for gestures and
left the control uncovered, because a control appears to need no screen. It
needs one more than anything else does.

**What the chase produced:**
[ADR-0041](../decisions/0041-scrims-dim-but-do-not-blur.md) and
[Finding 037](037-why-a-blurred-scrim-costs-the-panel.md) —
`backdrop-filter` costs 24.5 ms a frame in draw-and-submit against a 16.7 ms
budget, with the CPU idle, because the compositor draws the backdrop into
its own texture and reads it back every frame. Removing it takes the rail
from ~15 fps to ~36 against a 55 fps floor; the rest is the list work.

**This baseline is now stale for a second reason**, unrelated to the fault:
Phase 9's design sweep rebuilt most of the screens it measures. **It has to
be retaken before Phase 9 criterion 0 can be judged**, not merely corrected.
