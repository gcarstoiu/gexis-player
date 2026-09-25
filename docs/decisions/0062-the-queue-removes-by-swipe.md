# ADR-0062 — A queue row is removed by swiping it

**Status:** **Accepted**, 2026-09-24. George: *"With regards to the queue I
like the idea to remove the X and do a swipe to remove."*
**Date:** 2026-09-24
**Relates to:** [ADR-0038](0038-library-and-radio-on-the-panel.md) §1 (the
rail), [Finding 060](../findings/060-the-queue-rails-own-cost.md) (where the
button's cost was measured),
[ADR-0061](0061-the-kiosk-does-not-render-subpixel-text.md) (which removes
the performance reason for doing this)

## Context

Every queue row carried a 44 × 44 remove button: a 12 px radius, a 1 px
border and two 15 × 2.5 px bars at ±45°, on all of them. Finding 060
measured it at about eight frames a second on a main-thread scroll — the
largest single item on the rail, ahead of its artwork.

**That reason is gone.** ADR-0061 moves the rail's scroll to the compositor,
where the button costs nothing. This is being done anyway, because George
asked for it on its merits and because the button takes room the titles
want: without it *"It Was A Very Good Year"* and *"Who Designed The
Snowflake"* stop being truncated, which is 50 px back on a 417 px rail.

## Decision

**Swipe a row to the left to remove it.** No button.

- **The gesture decides itself at 12 px**, on whichever axis is larger. The
  list keeps a vertical gesture and the row keeps a horizontal one, and a
  pointer is captured only once the row has won — so an ambiguous drag
  still scrolls.
- **96 px removes it**, about a quarter of the rail's width. Short of that
  the row springs back.
- **`touch-action: pan-y` on the row**, so the browser handles the scroll
  natively and only the horizontal gesture reaches this component.
- **The row's own surface is opaque** (`--bg-panel`), because it now slides
  over something: *Remove* sits behind it, uncovered rather than faded in.
- **A tap still plays.** The click that ends a swipe is ignored for 320 ms
  after it.

## The spacing belongs to the row, 2026-09-25

George: *"it has a few pixels settle after the removal itself, when all
tracks under the removed one just push up by a few pixels."*

**Three pixels, and the list's `gap` was three pixels.** A collapsing row
animates its own height to nothing, but a `gap` belongs to the *list*, so
the space the row was holding stays open until the node is destroyed — which
is when the new queue arrives, about a second after the animation ended.
Watched on the row below: 493 → 433 over 600 ms, then **433 → 430 at
951 ms**.

The spacing is now `margin-bottom` on the row and collapses with it. The
same row now travels 490 → 427 in one movement ending at 610 ms, and stays
there.

**It also made the windowing exact.** A spacer standing in for *n* rows is
*n* pitches tall, but the flex `gap` added one more gap either side of it,
so the rail measured three pixels taller than the arithmetic. 455 rows now
give 28,665 px, which is 455 × 63 exactly.

## The affordance, which is the cost

**A swipe cannot be seen.** The X said what it did and where; this says
nothing until it is tried, and on an appliance in a living room the person
using it is not always the person who set it up.

- **It is recoverable.** Removing from a queue is not destructive: the track
  is still in the library and the row can be put back from it.
- **It keeps an accessible control.** The button is off screen, not deleted
  — `aria-label="Remove <title> from the queue"`, and it returns to view on
  keyboard focus. A swipe has no accessible name and nothing to focus, and
  an appliance is not exempt from that.
- **Not yet decided: whether it needs a hint.** A first-run nudge, or the
  first row resting a few pixels open, are both cheap. Neither is built.
  **This is George's to call** once he has lived with it.

## Alternatives

- **Reveal on tap, as the library rows do** — the pattern already exists
  and is discoverable. Rejected by George. It costs a tap on every jump, and
  the rail's tap *is* the action: tapping a row plays it.
- **Long press** — invisible in the same way as a swipe, and slower.
- **Keep the X and make it cheaper** — never measured. The whole button was
  suppressed, so which part of it cost the eight frames is unknown. Moot
  under ADR-0061.
