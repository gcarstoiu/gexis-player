// SPDX-License-Identifier: GPL-3.0-or-later
//
// The bar's sideways lists (ADR-0109, Bar family): New Music, Artists, the
// playlists, a playlist's tracks, an artist's albums and the radio grid all
// run across the screen rather than down it, because a 400 px screen has
// room for one row of anything worth touching.
//
// **A finger scrolls them natively.** Each scroller is `overflow-x: auto`
// with `touch-action: pan-x`, as the panel's New Music strip is, so a swipe
// is the compositor's and never this file's (ADR-0061). The pull-down band
// that brings the tray belongs to the Now Playing strip alone
// (tray.svelte.js); nothing on a library screen claims a vertical drag, so
// the two gestures never meet.
//
// **A mouse drags them here.** A mouse has no sideways wheel on most desks
// and the panel's kiosk is driven by one during setup and testing; a pressed
// drag moves the list, and the click that ends a drag is swallowed so the
// tile under the pointer does not open.

/** Below this a pointer has not moved; a release is a click. */
const CLICK = 6;

/** Svelte action: a mouse drag scrolls the node sideways. */
export function dragScroll(node) {
  let start = null;
  let from = 0;
  let dragged = false;

  function down(event) {
    if (event.pointerType !== 'mouse' || event.button !== 0) return;
    start = event.clientX;
    from = node.scrollLeft;
    dragged = false;
  }
  function move(event) {
    if (start === null) return;
    const dx = event.clientX - start;
    if (!dragged && Math.abs(dx) > CLICK) {
      dragged = true;
      node.setPointerCapture?.(event.pointerId);
    }
    if (dragged) node.scrollLeft = from - dx;
  }
  function up() {
    start = null;
  }
  // Capture phase: the tile's own click handler must not see a drag's end.
  function click(event) {
    if (!dragged) return;
    dragged = false;
    event.stopPropagation();
    event.preventDefault();
  }

  node.addEventListener('pointerdown', down);
  node.addEventListener('pointermove', move);
  node.addEventListener('pointerup', up);
  node.addEventListener('pointercancel', up);
  node.addEventListener('click', click, true);
  return {
    destroy() {
      node.removeEventListener('pointerdown', down);
      node.removeEventListener('pointermove', move);
      node.removeEventListener('pointerup', up);
      node.removeEventListener('pointercancel', up);
      node.removeEventListener('click', click, true);
    },
  };
}

/**
 * A sideways scroller's offset and width, as state - `watchScroller`
 * (lib/window.svelte.js) turned on its side. Read once per frame, passively,
 * so it never holds a scroll back.
 */
export function watchSideways() {
  let left = $state(0);
  let view = $state(0);
  let width = $state(0);
  let frame = null;

  function attach(node) {
    const read = () => {
      left = node.scrollLeft;
      view = node.clientWidth;
      width = node.scrollWidth;
    };
    read();
    // Per scroll frame only the offset: the widths cannot change by
    // scrolling, and are re-read when something can change them.
    const onScroll = () => {
      if (frame === null) {
        frame = requestAnimationFrame(() => {
          frame = null;
          left = node.scrollLeft;
        });
      }
    };
    node.addEventListener('scroll', onScroll, { passive: true });
    const resized = new ResizeObserver(read);
    resized.observe(node);
    // The content arriving changes the width without a scroll or a resize
    // of the scroller itself.
    const grown = new MutationObserver(() => requestAnimationFrame(read));
    grown.observe(node, { childList: true });
    return {
      destroy() {
        node.removeEventListener('scroll', onScroll);
        resized.disconnect();
        grown.disconnect();
        if (frame !== null) cancelAnimationFrame(frame);
      },
    };
  }

  return {
    attach,
    get left() {
      return left;
    },
    get view() {
      return view;
    },
    /** Whether there is more to the left / right of what is shown. */
    get moreBefore() {
      return left > 2;
    },
    get moreAfter() {
      return width - view - left > 2;
    },
  };
}

/** The panel's edge fade (Library.svelte's New Music strip): 88 px wide,
 *  drawn only on an edge that has more beyond it. */
export function edgeMask(before, after) {
  return (
    'linear-gradient(90deg,' +
    (before ? 'transparent 0,rgba(0,0,0,0.35) 22px,#000 88px,' : '#000 0,') +
    (after ? '#000 calc(100% - 88px),rgba(0,0,0,0.35) calc(100% - 22px),transparent 100%)' : '#000 100%)')
  );
}
