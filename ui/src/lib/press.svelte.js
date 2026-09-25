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

export function pressing() {
  let held = $state(null);
  let lifting = null;

  return {
    /** Whether `what` is the control being pressed. */
    is(what) {
      return held === what;
    },
    down(what) {
      clearTimeout(lifting);
      held = what;
    },
    up() {
      clearTimeout(lifting);
      lifting = setTimeout(() => (held = null), HOLD_MS);
    },
    /** Runs `go` once the pressed frame is on the screen. */
    act(go) {
      afterPaint(go);
    },
    stop() {
      clearTimeout(lifting);
    },
  };
}
