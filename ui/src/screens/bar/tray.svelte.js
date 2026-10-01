// SPDX-License-Identifier: GPL-3.0-or-later
//
// The bar's pull-down tray, shared between the strip that pulls it and the
// tray itself (ADR-0109, Bar family). The tray is mounted by App.svelte over
// every screen, because a volume change from elsewhere brings it down over
// any of them (design round 2, *Tray*); the band that pulls it belongs to the
// Now Playing strip alone. While a finger drags that band, `offset` is how
// far down the tray has come, and the tray follows it; otherwise null.

/** The tray's height, from the design: 136 from the top edge. */
export const TRAY_H = 136;

export const pull = $state({ offset: null });

/**
 * A vertical drag on a band: follows the finger, and on release says whether
 * the gesture was a tap or how far it went. `sign` is +1 for a band dragged
 * down (opening) and -1 for one dragged up (closing).
 */
export function bandDrag(sign, { onmove, onend }) {
  //: Below this a finger has not moved; a release is a tap.
  const TAP = 8;
  let start = null;
  let moved = false;
  let dy = 0;
  return {
    down(event) {
      start = event.clientY;
      moved = false;
      dy = 0;
      event.currentTarget.setPointerCapture?.(event.pointerId);
      onmove(0);
    },
    move(event) {
      if (start === null) return;
      dy = event.clientY - start;
      if (Math.abs(dy) > TAP) moved = true;
      onmove(Math.max(0, Math.min(TRAY_H, dy * sign)));
    },
    up() {
      if (start === null) return;
      start = null;
      onend({ tap: !moved, travel: Math.max(0, dy * sign) });
    },
    cancel() {
      start = null;
      onend({ tap: false, travel: 0, cancelled: true });
    },
  };
}
