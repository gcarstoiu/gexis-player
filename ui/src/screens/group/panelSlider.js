// SPDX-License-Identifier: GPL-3.0-or-later
// The group's sliders on the panel and the bar (design/source/22): a tap on
// the track sets the level where it lands, and a drag along it follows it.

/** 0-100 for where the pointer is along `el`. */
export function ratio(event, el) {
  const r = el.getBoundingClientRect();
  return Math.round(Math.max(0, Math.min(1, (event.clientX - r.left) / r.width)) * 100);
}

//: **The move decides first, as the bar's tray does** (the review of
//: 1.16.1): the sliders sit in lists that scroll up and down, and a swipe
//: that began on one set a member's level where the finger landed instead.
//: 8 px mostly sideways is the slider, from where the finger landed; mostly
//: up or down is not, and the browser scrolls (`touch-action: pan-y` on the
//: panel's tracks); a tap sets the level as it lifts.
const DECIDE = 8;

/** Pointer handlers for a track: `onlevel(percent, first)` once the
 *  gesture is the slider's, and on each move after; `ondone()` when the
 *  finger lifts. */
export function track(onlevel, ondone = () => {}) {
  let pending = null;
  const landed = () => ratio({ clientX: pending.x }, pending.el);
  return {
    down(event) {
      pending = { x: event.clientX, y: event.clientY, el: event.currentTarget, id: event.pointerId, way: null };
    },
    move(event) {
      if (!pending || event.pointerId !== pending.id) return;
      if (pending.way === null) {
        const dx = event.clientX - pending.x;
        const dy = event.clientY - pending.y;
        if (Math.max(Math.abs(dx), Math.abs(dy)) < DECIDE) return;
        pending.way = Math.abs(dx) >= Math.abs(dy) ? 'slide' : 'scroll';
        if (pending.way === 'scroll') return;
        try { pending.el.setPointerCapture(pending.id); } catch { /* a synthetic event */ }
        onlevel(landed(), true);
      }
      if (pending.way === 'slide') onlevel(ratio(event, pending.el), false);
    },
    //: Also `pointercancel`: the browser took the touch to scroll.
    up(event) {
      if (!pending) return;
      if (pending.way === null && event?.type === 'pointerup') {
        onlevel(landed(), true);
        ondone();
      } else if (pending.way === 'slide') {
        ondone();
      }
      pending = null;
    },
  };
}
