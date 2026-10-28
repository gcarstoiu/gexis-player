// SPDX-License-Identifier: GPL-3.0-or-later
// **A scroll along a slider moves it** (George, 2026-10-28; ADR-0121
// amended): a sideways scroll over a sideways slider, an up-and-down one over
// an upright band, the knob following the fingers as content does - from a
// computer's touchpad (a wheel event) and from the phone's touchpad
// (PanelPointer). Any other scroll scrolls what it did before.
//
// A slider moves in its own steps, the D-pad's (`stepSlider`): one for each
// step's length along it, so the knob keeps up with the fingers. A custom
// slider names its step in its own units (`aria-valuemin` to
// `aria-valuemax`) with `data-step`; a range input has its own.

const SLIDER = '[role="slider"], input[type="range"]';
//: A pause this long starts a new scroll: what was owed is dropped.
const IDLE_MS = 300;
//: At most this many steps for one event, so a flung wheel cannot jump.
const MOST = 20;
//: A wheel that counts in lines (Firefox's mouse) or pages.
const LINE_PX = 16;

const changeTimers = new WeakMap();

/** One step of `el` up (`dir` 1) or down (-1), as a D-pad press makes it. */
export function stepSlider(el, dir) {
  if (el.matches('input[type="range"]')) {
    if (dir > 0) el.stepUp(); else el.stepDown();
    el.dispatchEvent(new Event('input', { bubbles: true }));
    // Saved once the steps stop, not at each one.
    clearTimeout(changeTimers.get(el));
    changeTimers.set(el, setTimeout(() => el.dispatchEvent(new Event('change', { bubbles: true })), 400));
  } else {
    el.dispatchEvent(new CustomEvent('dpadstep', { detail: { step: dir }, bubbles: true }));
  }
}

const owed = new WeakMap();

/** A scroll of `dx`, `dy` px the fingers' way (right and down positive) over
 *  `target`: true when a slider there took it. */
export function scrollSlider(target, dx, dy) {
  const el = target?.closest?.(SLIDER);
  if (!el || el.disabled || el.getAttribute('aria-disabled') === 'true') return false;
  const upright = el.getAttribute('aria-orientation') === 'vertical';
  if (upright ? Math.abs(dy) <= Math.abs(dx) : Math.abs(dx) <= Math.abs(dy)) return false;
  const along = upright ? -dy : dx;
  const range = el instanceof HTMLInputElement
    ? Number(el.max || 100) - Number(el.min || 0)
    : Number(el.getAttribute('aria-valuemax')) - Number(el.getAttribute('aria-valuemin'));
  const step = Number(el.dataset.step || (el instanceof HTMLInputElement ? el.step : 0)) || range / 50;
  const r = el.getBoundingClientRect();
  const length = upright ? r.height : r.width;
  const per = range > 0 && step > 0 ? (length * step) / range : length / 50;
  if (!(per > 0)) return true;
  const now = performance.now();
  const was = owed.get(el);
  let px = was && now - was.at < IDLE_MS && Math.sign(was.px) === Math.sign(along) ? was.px + along : along;
  const whole = Math.trunc(px / per);
  const n = Math.max(-MOST, Math.min(MOST, whole));
  px = n === whole ? px - n * per : 0;
  owed.set(el, { px, at: now });
  for (let i = 0; i < Math.abs(n); i += 1) stepSlider(el, Math.sign(n));
  return true;
}

/** A computer's touchpad or wheel over a slider. Its deltas are the
 *  content's; with natural scrolling, a touchpad's usual, the content follows
 *  the fingers, so the fingers' way is the other. Pinching (Ctrl) is left to
 *  the browser. */
export function startWheelSlides() {
  function onWheel(event) {
    if (event.ctrlKey) return;
    const k = event.deltaMode === 1 ? LINE_PX : event.deltaMode === 2 ? window.innerHeight : 1;
    if (scrollSlider(event.target, -event.deltaX * k, -event.deltaY * k)) event.preventDefault();
  }
  window.addEventListener('wheel', onWheel, { passive: false });
  return () => window.removeEventListener('wheel', onWheel);
}
