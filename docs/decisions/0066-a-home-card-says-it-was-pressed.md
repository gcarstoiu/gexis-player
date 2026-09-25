# ADR-0066 — A home card says it was pressed

**Status:** **Accepted and built**, 2026-09-24. George: *"I am still not
seeing the animation on the tap. Radio has a tapping animation. The rest do
not - settings, artists, browse or playlists."*
**Date:** 2026-09-24
**Relates to:** [ADR-0065](0065-long-lists-are-built-a-screenful-at-a-time.md)
(why the screens had nothing to show), and the 2026-09-21 decision to take
press feedback *off* list rows, which this does not contradict

## Context

Radio appeared to have a tap animation and the other four cards did not.
Neither had one. What differed was what happened next: **the panel holds its
last frame until the next screen is painted**, and Radio's is a six-row
skeleton that paints at once where the artist grid took 600 ms. So Radio
looked alive and the rest looked ignored.

ADR-0065 has since brought the artist grid to 271–318 ms, which helps and is
not the same as answering the finger.

**`:active` alone does not answer it.** A quick tap can begin and end inside
one frame, and the frame that would have carried it is the one spent opening
the next screen.

## Decision

**The press is held long enough to be painted, and the screen opens a
painted frame later.**

- `is-pressed` on `pointerdown`, cleared 130 ms after the finger lifts.
- The card dims to its own tint, brightens its border and takes
  `scale(0.975)`, over 110 ms.
- **The navigation runs in `afterPaint`** — `requestAnimationFrame` then
  `setTimeout(…, 0)` — so the feedback frame goes out before the work that
  would have blocked it.

Measured: every card is pressed within 8–14 ms of the touch and **a frame
carrying it is painted at 25–37 ms**, Settings and Radio included.

## Why this is not the row decision reversed

On 2026-09-21 press feedback came off browse rows, playlist and radio rows,
album tracks and radio cards, for two reasons: the design gives a row none,
and *the list is replaced under the finger* — the browser keeps `:active` on
whatever element takes the tapped one's place, so the wrong row lit up.

**A home card is not replaced under the finger.** The whole screen goes, the
card with it, and there is no successor to inherit the state. The hazard
that removed it from rows does not exist here.

## Extended beyond the home cards, 2026-09-25

George: *"Add the same feedback response on tapping as the Homescreen tiles
to back, home screen, visualisation buttons."*

The reasoning is the same wherever a tap changes the screen, so the pattern
is now a helper — `lib/press.svelte.js` — rather than three copies of it.
Applied to now playing's **Home** and **Visualization**, the library
header's **Home** and **Back**, and Settings' **Back**.

Measured, from the touch to a frame carrying the pressed state:

| | pressed at | painted while pressed |
| --- | --- | --- |
| now playing: Home | 14 ms | 29 ms |
| now playing: Visualization | 11 ms | 19 ms |
| library: Back | 8 ms | 14 ms |
| library: Home | 8 ms | 17 ms |
| settings: Back | 16 ms | 24 ms |

## Consequences

- **Every navigation off the home screen is one painted frame slower** —
  about 16 ms. That is the cost of the panel answering first.
- **The five cards are the only place this is applied.** Lists keep the
  2026-09-21 decision.
