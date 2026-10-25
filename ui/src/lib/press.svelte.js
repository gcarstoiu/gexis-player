// SPDX-License-Identifier: GPL-3.0-or-later
/**
 * A control that says it was pressed (ADR-0066, extended 2026-09-25).
 *
 * The panel holds its last frame until the next one is painted, so a
 * control whose work takes a moment looks ignored: George reported exactly
 * that for the home cards, and the same is true of Back, Home, the
 * visualisation button and anything else that changes a screen.
 *
 * `:active` alone is not enough - a quick tap can begin and end inside one
 * frame, and the frame that would have carried it is the one spent doing
 * the work. So the press is held long enough to be painted, and the work
 * runs a painted frame later.
 */
import { afterPaint } from './chunks.svelte.js';

//: Long enough past the lift for the pressed frame to have gone out.
const HOLD_MS = 130;
//: How far outside the control a lifting finger still counts as on it.
const LIFT_SLOP = 10;
//: A click this soon after a lift that acted is the same tap.
const CLICK_AFTER_LIFT_MS = 600;

export function pressing() {
  let held = $state(null);
  let lifting = null;
  let liftedAt = -Infinity;

  const up = () => {
    clearTimeout(lifting);
    lifting = setTimeout(() => (held = null), HOLD_MS);
  };

  return {
    /** Whether `what` is the control being pressed. */
    is(what) {
      return held === what;
    },
    down(what) {
      clearTimeout(lifting);
      held = what;
    },
    up,
    /** Runs `go` once the pressed frame is on the screen. */
    act(go) {
      afterPaint(go);
    },
    /**
     * **A finger acts when it lifts on the control**, not on the click that
     * should follow it. A tap within about a second of pulling the bar's
     * tray down gets no click from Chromium - its pointerdown and pointerup
     * land on the button and nothing more (recorded on the bar, 2026-10-24:
     * 9 taps of 9, from 0.52 to 0.97 s after the pull). `click` then skips
     * the click that does come; a mouse acts on its click alone.
     */
    lift(event, go) {
      up();
      if (event.pointerType === 'mouse') return;
      const r = event.currentTarget.getBoundingClientRect();
      const { clientX: x, clientY: y } = event;
      if (x < r.left - LIFT_SLOP || x > r.right + LIFT_SLOP || y < r.top - LIFT_SLOP || y > r.bottom + LIFT_SLOP) return;
      liftedAt = performance.now();
      afterPaint(go);
    },
    click(go) {
      if (performance.now() - liftedAt < CLICK_AFTER_LIFT_MS) return;
      afterPaint(go);
    },
    stop() {
      clearTimeout(lifting);
    },
  };
}
