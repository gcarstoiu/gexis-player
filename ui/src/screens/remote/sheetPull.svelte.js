// SPDX-License-Identifier: GPL-3.0-or-later
//
// **A sheet pulled down to close** (George, 2026-10-27, for the EQ sheet):
// the gesture decides its direction past 12 px - sideways is a slider's or
// the chips', down is the sheet's - and closes past 80 px or on a flick.
// The same rule as EqSheet's, for the group volume sheet (ADR-0166).
const DECIDE_AT = 12;
const CLOSE_AT = 80;
const FLICK = 0.5; // px/ms, downwards

export class SheetPull {
  /** How far the finger has pulled the sheet down, while it does. */
  pull = $state(null);
  #gesture = null;
  #pulled = 0;
  #onclose;

  constructor(onclose) {
    this.#onclose = onclose;
  }

  grab = (event) => {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    this.#gesture = { id: event.pointerId, x: event.clientX, y: event.clientY, trail: [], decided: false };
  };

  drag = (event) => {
    const g = this.#gesture;
    if (!g || event.pointerId !== g.id) return;
    const dx = event.clientX - g.x;
    const dy = event.clientY - g.y;
    if (!g.decided) {
      if (Math.max(Math.abs(dx), Math.abs(dy)) <= DECIDE_AT) return;
      if (dy <= 0 || Math.abs(dx) > dy) {
        this.#gesture = null;
        return;
      }
      g.decided = true;
      event.currentTarget.setPointerCapture?.(event.pointerId);
    }
    this.pull = Math.max(0, dy);
    g.trail.push([event.timeStamp, this.pull]);
    while (g.trail.length > 2 && event.timeStamp - g.trail[0][0] > 100) g.trail.shift();
  };

  release = (event, cancelled = false) => {
    const g = this.#gesture;
    if (!g || event.pointerId !== g.id) return;
    this.#gesture = null;
    const [t0, y0] = g.trail[0] ?? [0, 0];
    const [t1, y1] = g.trail.at(-1) ?? [0, 0];
    const v = event.timeStamp - t1 > 100 || t1 <= t0 ? 0 : (y1 - y0) / (t1 - t0);
    if (!g.decided) return;
    this.#pulled = Date.now();
    if (!cancelled && (this.pull > CLOSE_AT || v > FLICK)) this.#onclose();
    this.pull = null;
  };

  /** The click that ends a pull is not a tap. */
  notTapped = (event) => {
    if (Date.now() - this.#pulled > 320) return;
    event.stopPropagation();
    event.preventDefault();
  };
}
