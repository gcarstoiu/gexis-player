// SPDX-License-Identifier: GPL-3.0-or-later
// **The D-pad on the panel** (ADR-0161). A press arrives as a keyboard's -
// an arrow, Enter or Escape - from the core's virtual keyboard (Home
// Assistant's remote), a USB keyboard or, later, a TV remote; one handler
// answers them all.
//
// - The focus moves by position (D3): the nearest control in the pressed
//   direction, measured on the screen, within the topmost layer - a sheet,
//   drawer, tray or dialog over the screen - scrolled into view. Left and
//   Right go first to a control level with the focused one.
// - A control taller than the list it scrolls in (an opened biography):
//   Up and Down scroll through it before they leave it, and the ring goes
//   round the part in view.
// - It is hidden until the first press, which only shows it (D4): on the
//   control focused last in that layer, or on its main one. A touch hides it,
//   and so do the phone's touchpad and a screen over everything (the idle
//   screen).
// - Its look is the design's (`design/source/19/Focus Ring.dc.html`, George's
//   teal ring, Jump): one element over the control's box, in no layout.
//
// Components take part through attributes and two events, so a new screen
// needs nothing here:
// - `data-dpad-layer` on an overlay that is not a `role="dialog"`;
// - `data-dpad-main` on a screen's main control, `data-dpad-start` on the
//   list or grid whose first item a screen starts on;
// - `data-dpad-back` on the control Back presses (a screen's Back,
//   Minimise, a sheet's Cancel), or a `dpadback` listener on the layer that
//   calls `preventDefault()` once it has closed itself;
// - a `dpadstep` listener (`detail.step` +1 or -1) on a custom slider
//   (Left and Right; Up and Down on one with `aria-orientation="vertical"`;
//   a scroll along it sends the same, one per `data-step`, scrollSlide.js),
//   and `data-dpad-box` inside a control on the parts the ring goes round;
// - `data-dpad-knob` on a slider's knob that runs past its ends: the ring
//   takes in the knob's whole travel, the same at every value;
// - `data-dpad-off` on the screens the D-pad leaves to the phone (D8);
// - `data-dpad-cover` on a screen over everything that a press only takes
//   down (the idle screen, a takeover's).
//
// **The phone's remote drives it too** (ADR-0164): its D-pad arrives as
// these keys, and `dpadring` says whether OK would land in a text field, so
// the phone can bring up its keyboard in the same touch.

import { stepSlider } from './scrollSlide.js';

const KEYS = { ArrowUp: 'up', ArrowDown: 'down', ArrowLeft: 'left', ArrowRight: 'right', Enter: 'ok', Escape: 'back' };

const FOCUSABLE = [
  'button', 'a[href]', 'input:not([type="hidden"])', 'select', 'textarea',
  '[role="button"]', '[role="tab"]', '[role="slider"]', '[role="switch"]', '[role="option"]',
  '[role="menuitem"]', '[role="link"]', '[tabindex]:not([tabindex="-1"])',
].join(',');
const LAYERS = '[data-dpad-layer], [role="dialog"], [role="alertdialog"]';
const COVERS = '[data-dpad-cover]';
const TEXT = /^(text|search|email|url|tel|password|number)$/;

// The design's ring (design/tokens.css, *Phase 19: the D-pad's focus*).
const GAP = 4;
const BAND = 6;
const OUT = GAP + BAND;
const INSET = 2;
const NEIGHBOUR = 12;
// Kept clear of a scrolled list's edge, so the ring outside it shows.
const SCROLL_MARGIN = 24;

function visible(el) {
  if (!el.isConnected || el.closest('[inert], [aria-hidden="true"], .is-kept')) return false;
  if (el.checkVisibility && !el.checkVisibility({ opacityProperty: true, visibilityProperty: true })) return false;
  const r = el.getBoundingClientRect();
  // A control kept for a keyboard but drawn as nothing (the queue row's
  // Remove, 1 x 1) is not one the ring can show.
  return r.width > 1 && r.height > 1;
}

function layerShown(el) {
  if (!visible(el)) return false;
  const style = getComputedStyle(el);
  if (style.pointerEvents === 'none') return false;
  const r = el.getBoundingClientRect();
  return r.right > 0 && r.bottom > 0 && r.left < innerWidth && r.top < innerHeight;
}

function scrollers(el, stop) {
  const out = [];
  for (let p = el.parentElement; p && p !== stop?.parentElement; p = p.parentElement) {
    const s = getComputedStyle(p);
    const y = /(auto|scroll)/.test(s.overflowY) && p.scrollHeight > p.clientHeight + 1;
    const x = /(auto|scroll)/.test(s.overflowX) && p.scrollWidth > p.clientWidth + 1;
    if (x || y) out.push({ el: p, x, y });
  }
  return out;
}

function isSlider(el) {
  return el.matches('[role="slider"], input[type="range"], [data-dpad-slider]');
}

//: An upright slider (the equaliser's bands, ADR-0162) steps on Up and Down,
//: and Left and Right move to its neighbours.
function isVertical(el) {
  return el.getAttribute('aria-orientation') === 'vertical';
}

function isText(el) {
  return el.matches('textarea') || (el.matches('input') && TEXT.test(el.type || 'text'));
}

function radius(el, r) {
  const s = getComputedStyle(el).borderTopLeftRadius;
  if (s.endsWith('%')) return (parseFloat(s) / 100) * Math.min(r.width, r.height);
  return parseFloat(s) || 0;
}

function union(rects) {
  const left = Math.min(...rects.map((r) => r.left)), top = Math.min(...rects.map((r) => r.top));
  const right = Math.max(...rects.map((r) => r.right)), bottom = Math.max(...rects.map((r) => r.bottom));
  return { left, top, right, bottom, width: right - left, height: bottom - top };
}

// The gap between two intervals; 0 when they overlap.
const gap = (a1, a2, b1, b2) => Math.max(0, Math.max(a1, b1) - Math.min(a2, b2));

// The part of `r` its scroll areas show, along the way each one scrolls.
function inView(el, r) {
  let { left, top, right, bottom } = r;
  for (const { el: box, x, y } of scrollers(el)) {
    const b = box.getBoundingClientRect();
    if (y) {
      top = Math.max(top, b.top);
      bottom = Math.min(bottom, b.bottom);
    }
    if (x) {
      left = Math.max(left, b.left);
      right = Math.min(right, b.right);
    }
  }
  return { left, top, right, bottom, width: Math.max(0, right - left), height: Math.max(0, bottom - top) };
}

// The list a control is taller than, which it cannot be scrolled into
// whole; null for any other.
function taller(el) {
  const s = scrollers(el).find((one) => one.y);
  if (!s) return null;
  const b = s.el.getBoundingClientRect();
  return el.getBoundingClientRect().height > b.height - 2 * SCROLL_MARGIN ? s : null;
}

// How far Up or Down scrolls such a control's list before the press leaves
// the control; null when it shows the control's end that way.
function through(el, dir) {
  const s = taller(el);
  if (!s) return null;
  const r = el.getBoundingClientRect();
  const b = s.el.getBoundingClientRect();
  const rest = dir === 'down'
    ? Math.min(r.bottom - (b.bottom - SCROLL_MARGIN), s.el.scrollHeight - s.el.clientHeight - s.el.scrollTop)
    : Math.min(b.top + SCROLL_MARGIN - r.top, s.el.scrollTop);
  if (rest <= 1) return null;
  return { box: s.el, by: Math.min(rest, b.height * 0.75) * (dir === 'down' ? 1 : -1) };
}

function score(c, r, dir) {
  const cx = c.left + c.width / 2, cy = c.top + c.height / 2;
  const rx = r.left + r.width / 2, ry = r.top + r.height / 2;
  let primary, ortho, off;
  if (dir === 'down') {
    if (ry <= cy + 1 || r.top < c.top + 1) return Infinity;
    primary = Math.max(0, r.top - c.bottom); ortho = gap(c.left, c.right, r.left, r.right); off = Math.abs(rx - cx);
  } else if (dir === 'up') {
    if (ry >= cy - 1 || r.bottom > c.bottom - 1) return Infinity;
    primary = Math.max(0, c.top - r.bottom); ortho = gap(c.left, c.right, r.left, r.right); off = Math.abs(rx - cx);
  } else if (dir === 'right') {
    if (rx <= cx + 1 || r.left < c.left + 1) return Infinity;
    primary = Math.max(0, r.left - c.right); ortho = gap(c.top, c.bottom, r.top, r.bottom); off = Math.abs(ry - cy);
  } else {
    if (rx >= cx - 1 || r.right > c.right - 1) return Infinity;
    primary = Math.max(0, c.left - r.right); ortho = gap(c.top, c.bottom, r.top, r.bottom); off = Math.abs(ry - cy);
  }
  return primary + ortho * 3 + off * 0.05;
}

function readingOrder(a, b) {
  const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
  return Math.abs(ra.top - rb.top) > 8 ? ra.top - rb.top : ra.left - rb.left;
}

// What the ring goes round: the control, or its `data-dpad-box` parts; a
// slider's widened by half its knob each way, so the knob stays inside at
// either end.
function ringBox(el, boxes, slider) {
  const r = boxes.length > 1 ? union(boxes.map((b) => b.getBoundingClientRect()))
    : (boxes[0] ?? el).getBoundingClientRect();
  const knob = slider ? el.querySelector('[data-dpad-knob]') : null;
  if (!knob) return r;
  const k = knob.getBoundingClientRect();
  return union([
    { left: r.left - k.width / 2, top: r.top, right: r.right + k.width / 2, bottom: r.bottom },
    { left: r.left, top: k.top, right: r.right, bottom: k.bottom },
  ]);
}

function makeRing() {
  const ring = document.createElement('div');
  ring.className = 'dpad-ring';
  ring.dataset.focusRing = 'ring';
  ring.hidden = true;
  const arrow = (side, d) => {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 20 28');
    svg.setAttribute('class', `dpad-ring__arrow dpad-ring__arrow--${side}`);
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', d);
    svg.append(path);
    return svg;
  };
  ring.append(arrow('left', 'M17 3 L4 14 L17 25 Z'), arrow('right', 'M3 3 L16 14 L3 25 Z'));
  document.body.append(ring);
  return ring;
}

/**
 * Starts the D-pad on the panel; returns the function that stops it.
 * - `root()`: the panel's element.
 * - `onkey()`: each press, as attention - what a touch counts as.
 * - `wake()`: true when the press only woke the panel (the idle screen), as
 *   a first touch does (D4).
 * - `trayUp()`: on a bar, Up from the top row opens the tray (D3); true when
 *   it did.
 */
export function startDpad({ root, onkey = () => {}, wake = () => false, trayUp = () => false }) {
  const ring = makeRing();
  const last = new WeakMap();
  let current = null;
  // Inside the control or outside it, decided when the focus lands.
  let insetForm = false;
  let shown = false;
  // Shown, but what it was on has gone (a drawer closing): hidden until it
  // lands again, so it never outlives the drawer's fade.
  let lost = false;
  let follow = 0;
  let nudge = null;
  let nudgeTimer;
  let lostTimer;
  // What OK pressed, newest last: Back brings the ring back to the control
  // that opened the screen it leaves, found by its name (screens are drawn
  // anew, so the element itself is gone).
  const openers = [];
  let returnTo = null;
  // The control OK pressed, until the screen changes under it (then it was
  // an opener) or a moment passes (a toggle, Play).
  let pressed = null;
  let pressedAt = 0;

  function layers() {
    const panel = root();
    if (!panel) return [];
    return [...panel.querySelectorAll(LAYERS)].filter(layerShown);
  }

  function topLayer() {
    const shownLayers = layers();
    return shownLayers.length ? shownLayers[shownLayers.length - 1] : root();
  }

  function off() {
    return !root() || [...document.querySelectorAll('[data-dpad-off]')].some(layerShown);
  }

  // Svelte makes a screen inert while it fades out.
  function covered() {
    return [...document.querySelectorAll(COVERS)].some((el) => el.isConnected && !el.closest('[inert]'));
  }

  // In a layer that is closing (still fading out) or closed, or nested in
  // one: not reachable from `layer`.
  function shut(el, layer) {
    const own = el.closest(LAYERS);
    return !!own && own !== layer && layer.contains(own);
  }

  function candidates(layer) {
    return [...layer.querySelectorAll(FOCUSABLE)].filter((el) => {
      if (el.disabled || el.closest('[data-dpad-skip]')) return false;
      if (shut(el, layer)) return false;
      if (!visible(el)) return false;
      const r = el.getBoundingClientRect();
      const onScreen = r.right > 0 && r.bottom > 0 && r.left < innerWidth && r.top < innerHeight;
      return onScreen || scrollers(el, layer).length > 0;
    });
  }

  const named = (el) => `${el.getAttribute('aria-label') ?? ''}|${el.textContent.trim().replace(/\s+/g, ' ')}`;

  function start(layer, list) {
    if (returnTo) {
      const name = returnTo;
      returnTo = null;
      const again = list.find((el) => named(el) === name);
      if (again) return again;
    }
    const kept = last.get(layer);
    if (kept && list.includes(kept)) return kept;
    const main = list.find((el) => el.matches('[data-dpad-main]'));
    if (main) return main;
    for (const box of layer.querySelectorAll('[data-dpad-start]')) {
      const inside = list.filter((el) => box.contains(el)).sort(readingOrder);
      if (inside.length) return inside[0];
    }
    return [...list].sort(readingOrder)[0] ?? null;
  }

  function reveal(el, layer) {
    for (const { el: box, x, y } of scrollers(el, layer)) {
      const r = el.getBoundingClientRect();
      const b = box.getBoundingClientRect();
      if (y) {
        if (r.top < b.top + SCROLL_MARGIN) box.scrollTop -= b.top + SCROLL_MARGIN - r.top;
        else if (r.bottom > b.bottom - SCROLL_MARGIN) box.scrollTop += r.bottom - (b.bottom - SCROLL_MARGIN);
      }
      if (x) {
        if (r.left < b.left + SCROLL_MARGIN) box.scrollLeft -= b.left + SCROLL_MARGIN - r.left;
        else if (r.right > b.right - SCROLL_MARGIN) box.scrollLeft += r.right - (b.right - SCROLL_MARGIN);
      }
    }
  }

  function inset(el, r, list) {
    if (el.matches('[data-dpad-ring="inset"]')) return true;
    if (el.matches('[data-dpad-ring="outside"]')) return false;
    if (r.left - OUT < 0 || r.top - OUT < 0 || r.right + OUT > innerWidth || r.bottom + OUT > innerHeight) return true;
    for (const other of list) {
      if (other === el || other.contains(el) || el.contains(other)) continue;
      const o = other.getBoundingClientRect();
      const dx = gap(r.left, r.right, o.left, o.right);
      const dy = gap(r.top, r.bottom, o.top, o.bottom);
      if ((dx === 0 && dy < NEIGHBOUR) || (dy === 0 && dx < NEIGHBOUR)) return true;
    }
    return false;
  }

  let ringField = false;
  function tell() {
    // A field, or a control that opens one focused (`data-text-entry`).
    const now = shown && !lost && !!current && (isText(current) || !!current.closest('[data-text-entry]'));
    if (now === ringField) return;
    ringField = now;
    dispatchEvent(new CustomEvent('dpadring', { detail: { field: now } }));
  }

  let placed = '';
  function draw() {
    tell();
    if (!shown || lost || !current || !visible(current)) {
      if (!ring.hidden) ring.hidden = true;
      placed = '';
      return;
    }
    // A control whose touch area is larger than what it draws (the bar
    // tray's slider) names the part the ring goes round: `data-dpad-box`.
    const boxes = [...current.querySelectorAll('[data-dpad-box]')];
    const box = boxes[0] ?? current;
    const slider = isSlider(current) && !isVertical(current);
    const r = inView(current, ringBox(current, boxes, slider));
    const rad = radius(box, r);
    let x, y, w, h, rr;
    if (!slider && insetForm) {
      x = r.left + INSET; y = r.top + INSET; w = Math.max(0, r.width - 2 * INSET); h = Math.max(0, r.height - 2 * INSET);
      rr = Math.max(4, rad - INSET);
    } else {
      const round = rad >= Math.min(r.width, r.height) / 2 - 0.5;
      x = r.left - OUT; y = r.top - OUT; w = r.width + 2 * OUT; h = r.height + 2 * OUT;
      rr = round ? 9999 : rad + OUT;
    }
    const key = `${x}|${y}|${w}|${h}|${rr}|${slider}|${nudge}`;
    if (key === placed) return;
    placed = key;
    ring.hidden = false;
    ring.style.transform = `translate(${x}px, ${y}px)`;
    ring.style.width = `${w}px`;
    ring.style.height = `${h}px`;
    ring.style.borderRadius = `${rr}px`;
    ring.classList.toggle('dpad-ring--slider', slider);
    ring.classList.toggle('dpad-ring--left', slider && nudge === -1);
    ring.classList.toggle('dpad-ring--right', slider && nudge === 1);
  }

  // Follows the control for a moment after it moved (a list scrolling, a
  // sheet opening), then at a slower beat while shown.
  function track(frames = 40) {
    follow = Math.max(follow, frames);
    const tick = () => {
      if (follow-- <= 0) return;
      draw();
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  function focus(el, layer, list) {
    current = el;
    shown = !!el;
    lost = false;
    if (el) {
      last.set(layer, el);
      reveal(el, layer);
      insetForm = inset(el, inView(el, el.getBoundingClientRect()), list ?? candidates(layer));
    }
    draw();
    track();
  }

  function step(el, dir) {
    stepSlider(el, dir);
    nudge = dir;
    clearTimeout(nudgeTimer);
    nudgeTimer = setTimeout(() => { nudge = null; draw(); }, 300);
    draw();
  }

  function back(layer) {
    const asked = new CustomEvent('dpadback', { cancelable: true });
    if (!layer.dispatchEvent(asked)) return true;
    const own = [...layer.querySelectorAll('[data-dpad-back]')].filter(visible);
    const inner = [...layer.querySelectorAll(LAYERS)].filter((l) => l !== layer);
    // The last one shown: an overlay's own head comes after the screen's.
    const target = own.filter((el) => !inner.some((l) => l.contains(el))).pop();
    if (target) {
      target.click();
      return true;
    }
    return false;
  }

  function onKey(event) {
    const key = KEYS[event.key];
    if (!key || !event.isTrusted || event.altKey || event.ctrlKey || event.metaKey) return;
    if (off()) {
      shown = false;
      draw();
      return;
    }
    const typing = document.activeElement && isText(document.activeElement);
    if (typing && (key === 'left' || key === 'right' || key === 'ok')) return;
    event.preventDefault();
    event.stopPropagation();
    onkey();
    if (wake() || covered()) {
      hide();
      return;
    }
    if (typing) document.activeElement.blur();
    const layer = topLayer();
    if (key === 'back') {
      returnTo = back(layer) ? (openers.pop() ?? null) : null;
      return;
    }
    returnTo = null;
    // **A page from another site** (the Home Assistant dashboard, D1): the
    // keys go to it, so the frame takes the keyboard and draws its own focus.
    const frame = layer.matches('[data-dpad-frame]') ? layer.querySelector('iframe') : null;
    if (frame) {
      shown = false;
      draw();
      frame.focus();
      return;
    }
    const list = candidates(layer);
    if (!shown || !current || !list.includes(current)) {
      // The first press shows where the focus is; it does not move it (D4).
      focus(start(layer, list), layer, list);
      return;
    }
    if (key === 'ok') {
      pressed = named(current);
      pressedAt = performance.now();
      if (isText(current)) current.focus();
      else current.click();
      track();
      return;
    }
    if (isSlider(current) && !isVertical(current) && (key === 'left' || key === 'right')) {
      step(current, key === 'right' ? 1 : -1);
      return;
    }
    if (isSlider(current) && isVertical(current) && (key === 'up' || key === 'down')) {
      step(current, key === 'up' ? 1 : -1);
      return;
    }
    const scroll = (key === 'up' || key === 'down') && through(current, key);
    if (scroll) {
      scroll.box.scrollTop += scroll.by;
      track();
      return;
    }
    const from = taller(current) ? inView(current, current.getBoundingClientRect()) : current.getBoundingClientRect();
    const sideways = key === 'left' || key === 'right';
    let best = null;
    let bestScore = Infinity;
    let bestLevel = false;
    for (const el of list) {
      if (el === current) continue;
      const r = el.getBoundingClientRect();
      const s = score(from, r, key);
      if (s === Infinity) continue;
      // Level with the focused control: across it by half the smaller of
      // the two, and no more than three times its height (the equaliser's
      // switch beside Back, over the bands below; not the bar's rail, which
      // is level with everything).
      const across = Math.min(from.bottom, r.bottom) - Math.max(from.top, r.top);
      const level = sideways && across >= Math.min(r.height, from.height) / 2 && r.height <= 3 * from.height;
      if (level > bestLevel || (level === bestLevel && s < bestScore)) {
        bestScore = s;
        bestLevel = level;
        best = el;
      }
    }
    if (best) focus(best, layer, list);
    else if (key === 'up' && trayUp()) track();
  }

  function hide() {
    shown = false;
    draw();
  }

  function onPointer(event) {
    if (event.isTrusted) hide();
  }

  // A control that went away (a screen changed under it): the ring comes
  // back on the new screen's start, as if the press had been the first.
  // So is one now under a sheet or drawer that opened over it, and the
  // control a closed one was opened from gets it back (`last`).
  const here = () => {
    const layer = topLayer();
    return !!current && visible(current) && layer.contains(current) && !shut(current, layer);
  };
  function check() {
    if (!shown) return;
    if (covered()) {
      hide();
      return;
    }
    if (here()) {
      if (lost) {
        lost = false;
        track();
      }
      draw();
      return;
    }
    if (lost) return;
    lost = true;
    draw();
    if (pressed && performance.now() - pressedAt < 1500) {
      openers.push(pressed);
      if (openers.length > 20) openers.shift();
    }
    pressed = null;
    clearTimeout(lostTimer);
    lostTimer = setTimeout(() => {
      if (!shown || off()) return;
      if (here()) {
        lost = false;
        draw();
        return;
      }
      const layer = topLayer();
      // Over a page from another site the ring stays away, as a press there
      // leaves it (D1).
      if (layer.matches('[data-dpad-frame]')) hide();
      else focus(start(layer, candidates(layer)), layer);
    }, 150);
  }
  const watch = setInterval(check, 250);
  // As the page changes, not only at the watch's beat: a drawer that closes
  // takes the ring with it.
  let checking = 0;
  const observer = new MutationObserver((records) => {
    if (!shown || checking || records.every((r) => ring.contains(r.target))) return;
    checking = requestAnimationFrame(() => {
      checking = 0;
      check();
    });
  });
  observer.observe(document.body, {
    subtree: true, childList: true, attributes: true,
    attributeFilter: ['class', 'hidden', 'inert', 'aria-hidden', 'open'],
  });
  const onScroll = () => shown && draw();

  addEventListener('keydown', onKey, true);
  addEventListener('pointerdown', onPointer, true);
  // The phone's touchpad: its pointer moves and taps are made up in the page.
  addEventListener('panelpointer', hide);
  addEventListener('scroll', onScroll, true);
  addEventListener('resize', onScroll);
  return () => {
    removeEventListener('keydown', onKey, true);
    removeEventListener('pointerdown', onPointer, true);
    removeEventListener('panelpointer', hide);
    removeEventListener('scroll', onScroll, true);
    removeEventListener('resize', onScroll);
    clearInterval(watch);
    observer.disconnect();
    cancelAnimationFrame(checking);
    clearTimeout(nudgeTimer);
    clearTimeout(lostTimer);
    ring.remove();
  };
}
