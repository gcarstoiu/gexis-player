// SPDX-License-Identifier: GPL-3.0-or-later
/**
 * Building a long list a screenful at a time (ADR-0065).
 *
 * The panel used to build every row of a list before drawing any of them,
 * at two to three milliseconds a row: 1.9 seconds of nothing for the artist
 * grid's 917 cards, 1.4 for a 467-track playlist
 * (`docs/findings/063-the-panel-builds-every-row-before-it-draws-one.md`).
 * The rows are cheap to *have* - since ADR-0061 the grid scrolls all 917 at
 * sixty frames a second - so what changes here is when they are made.
 */

//: Enough to fill the panel and a little past it: the grid draws 7 cards a
//: row in a 600px window, a playlist's rows are 56px in 700px. Bigger
//: delays the first paint for rows nobody has reached; smaller leaves the
//: scroller too short to drag.
const FIRST = 140;

//: How many more per frame. At 2-3ms a row this is a few frames' work per
//: pass, spread across frames rather than spent before the first one.
const CHUNK = 160;

/**
 * A count that starts at a screenful and grows to `total()`.
 *
 * **It reads the total and nothing else.** An effect that also read its own
 * count would wake itself, which is how the panel once stopped answering
 * (LESSONS 31) - so the growing count is mirrored in a plain variable and
 * the state is only ever written.
 */
export function revealing(total) {
  let shown = $state(FIRST);
  let frame = null;

  $effect(() => {
    const want = total();
    if (frame) cancelAnimationFrame(frame);
    let at = Math.min(FIRST, want);
    shown = at;
    const step = () => {
      at = Math.min(want, at + CHUNK);
      shown = at;
      frame = at < want ? requestAnimationFrame(step) : null;
    };
    frame = at < want ? requestAnimationFrame(step) : null;
    return () => {
      if (frame) cancelAnimationFrame(frame);
      frame = null;
    };
  });

  return {
    get shown() {
      return shown;
    },
    /** Everything, now. For anything that reads the DOM it is about to act
     *  on - the A-Z rail jumps to a group, and cannot jump to one that has
     *  not been built yet. */
    all() {
      if (frame) cancelAnimationFrame(frame);
      frame = null;
      shown = Number.MAX_SAFE_INTEGER;
    },
  };
}
