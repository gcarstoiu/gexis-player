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

//: **Just past one screen.** The artist grid draws 7 cards a row in a 600px
//: window - 28 of them visible, so this is two screenfuls. 140 was the
//: first try and it cost 584ms to the first painted frame, which is long
//: enough to look like the tap did nothing: the home screen leaves the DOM
//: at 155ms and the panel shows its last frame until the new one is ready
//: (George, 2026-09-24: *"the animation ... is gone except for Radio"* -
//: Radio's skeleton is a handful of nodes and paints at once).
const FIRST = 56;

//: How many more per frame, once something is on screen. Larger than the
//: first pass on purpose: by then the panel has answered.
const CHUNK = 180;

/**
 * A count that starts at a screenful and grows to `total()`.
 *
 * **It reads the total and nothing else.** An effect that also read its own
 * count would wake itself, which is how the panel once stopped answering
 * (LESSONS 31) - so the growing count is mirrored in a plain variable and
 * the state is only ever written.
 */
//: **After the frame is on the screen, not before it.** A
//: `requestAnimationFrame` callback runs *before* the paint it belongs to,
//: so scheduling the next chunk there puts it in the same frame: the panel
//: kept building and the first screenful was not painted for 584ms, whether
//: that screenful was 140 rows or 56. The timeout runs once the frame has
//: gone out.
function afterPaint(run) {
  let timer = null;
  const frame = requestAnimationFrame(() => {
    timer = setTimeout(run, 0);
  });
  return () => {
    cancelAnimationFrame(frame);
    if (timer) clearTimeout(timer);
  };
}

export function revealing(total) {
  let shown = $state(FIRST);
  let cancel = null;

  $effect(() => {
    const want = total();
    if (cancel) cancel();
    let at = Math.min(FIRST, want);
    shown = at;
    const step = () => {
      at = Math.min(want, at + CHUNK);
      shown = at;
      cancel = at < want ? afterPaint(step) : null;
    };
    cancel = at < want ? afterPaint(step) : null;
    return () => {
      if (cancel) cancel();
      cancel = null;
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
      if (cancel) cancel();
      cancel = null;
      shown = Number.MAX_SAFE_INTEGER;
    },
  };
}
