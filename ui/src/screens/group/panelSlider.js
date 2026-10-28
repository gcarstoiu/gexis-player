// SPDX-License-Identifier: GPL-3.0-or-later
// The group's sliders on the panel and the bar (design/source/22): a finger
// down on the track sets the level where it lands, and a drag follows it.

/** 0-100 for where the pointer is along `el`. */
export function ratio(event, el) {
  const r = el.getBoundingClientRect();
  return Math.round(Math.max(0, Math.min(1, (event.clientX - r.left) / r.width)) * 100);
}

/** Pointer handlers for a track: `onlevel(percent)` on down and move, and
 *  `ondone()` when the finger lifts. */
export function track(onlevel, ondone = () => {}) {
  let el = null;
  return {
    down(event) {
      el = event.currentTarget;
      try { el.setPointerCapture(event.pointerId); } catch { /* a synthetic event */ }
      onlevel(ratio(event, el), true);
    },
    move(event) {
      if (el) onlevel(ratio(event, el), false);
    },
    up() {
      if (el) ondone();
      el = null;
    },
  };
}
