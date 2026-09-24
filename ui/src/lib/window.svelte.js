// SPDX-License-Identifier: GPL-3.0-or-later
/**
 * Watching a scroller, so a list can build only what is inside it
 * (ADR-0067).
 *
 * The artist grid's 917 cards cost about 1.3ms each to create and lay out,
 * and nothing in a card accounts for it - a card with no photo, no tint and
 * nothing observing it costs the same
 * (`docs/findings/064-the-count-is-the-cost.md`). So the only answer is
 * fewer of them.
 */

/**
 * A scroller's offset and height, as state.
 *
 * **Reads two numbers, once per frame, passively.** The panel's scrolls are
 * composited (ADR-0061) and this must not take that back: the listener
 * cannot block the scroll, and a burst of scroll events collapses into one
 * read.
 */
export function watchScroller() {
  let top = $state(0);
  let view = $state(0);
  let frame = null;

  function attach(node) {
    const read = () => {
      frame = null;
      top = node.scrollTop;
      view = node.clientHeight;
    };
    read();
    const onScroll = () => {
      if (frame === null) frame = requestAnimationFrame(read);
    };
    node.addEventListener('scroll', onScroll, { passive: true });
    // A card's height depends on the panel's width, so a resize is a
    // relayout and the heights have to be read again.
    const resized = new ResizeObserver(read);
    resized.observe(node);
    return {
      destroy() {
        node.removeEventListener('scroll', onScroll);
        resized.disconnect();
        if (frame !== null) cancelAnimationFrame(frame);
      },
    };
  }

  return {
    attach,
    get top() {
      return top;
    },
    get view() {
      return view;
    },
  };
}

/**
 * Which of `blocks` are inside the window, given their heights.
 *
 * `blocks` is `[{ top, height }, …]` in order. Returns the first and last
 * index to build, and the space to leave above and below them, so the
 * scroller keeps its full height while holding a fraction of its contents.
 */
export function inView(blocks, top, view, over) {
  if (!blocks.length) return { from: 0, to: 0, above: 0, below: 0 };
  const lo = top - over;
  const hi = top + view + over;
  let from = 0;
  while (from < blocks.length - 1 && blocks[from].top + blocks[from].height <= lo) from++;
  let to = from;
  while (to < blocks.length - 1 && blocks[to + 1].top < hi) to++;
  const last = blocks[blocks.length - 1];
  return {
    from,
    to,
    above: blocks[from].top,
    below: last.top + last.height - (blocks[to].top + blocks[to].height),
  };
}
