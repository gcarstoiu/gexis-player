<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0164 D3: the touch area of a player with a screen (design/source/21,
  *Touch area*). Corner buttons for Home, Lyrics, Back and Meters; a switch
  between the two pads:

  - **Trackpad**: the panel's pointer, relative, as a laptop's touchpad, with
    ADR-0121's gestures - one finger moves and taps, two scroll or pinch.
    Nothing is drawn on the phone: the pointer on the screen is the feedback.
    The strips along the right and bottom edges, drawn still, scroll what is
    under the pointer by 24 px for each 24 px of drag, the content following
    the finger (C11).
  - **D-pad**: the arrows and OK as buttons, driving the panel's ring
    (ADR-0161).

  A tap calls `ontap`, and OK `onok`, first, inside the touch, so the phone's
  keyboard can open for the text field the pointer or the ring is on (C5).
-->
<script>
  import { active, meters, panel } from '../../lib/state.js';
  import { key, showing, view } from './commands.js';
  import { FILLED, STROKED } from './icons.js';

  let {
    pad = 'touch',
    onpad = () => {},
    padSwitch = true,
    socket = null,
    onok = () => {},
    ontap = () => {},
    onsay = () => {},
  } = $props();

  const off = $derived(!!$panel.standby);
  const lit = (which) => !off && $showing === which;

  function press(name) {
    if (name === 'ok') onok();
    key(name);
  }

  // ── The trackpad (ADR-0121) ─────────────────────────────────────────────
  //: A tap: quick, and hardly moved.
  const TAP_MS = 300;
  const TAP_MOVE = 10;
  //: How far two fingers go together, or apart, before the gesture is
  //: decided - a scroll or a zoom, which it then stays until they lift.
  const DECIDE = 12;

  const fingers = new Map();
  //: 'one' (moving and tapping), 'two' (undecided), 'scroll', 'zoom', or
  //: 'done' - after two fingers, nothing until every finger has lifted.
  let gesture = null;
  let touchStart = null;
  let last = null;
  let travelled = 0;
  let middle = null;
  let spread = 0;
  let firstMiddle = null;
  let firstSpread = 0;
  let sideways = false;
  let pending = { dx: 0, dy: 0 };
  let scrolled = { dx: 0, dy: 0 };
  let zoomed = 1;
  let frame = 0;

  /** Whole pixels go; **the fraction stays for the next frame**, so a
   *  finger starting slowly is not held still and then let jump (George,
   *  2026-10-05: "choppy at the beginning"). The same for two fingers. */
  function flush() {
    frame = 0;
    const dx = Math.trunc(pending.dx);
    const dy = Math.trunc(pending.dy);
    if (dx || dy) socket?.send({ t: 'move', dx, dy });
    pending = { dx: pending.dx - dx, dy: pending.dy - dy };
    const sx = Math.trunc(scrolled.dx);
    const sy = Math.trunc(scrolled.dy);
    if (sx || sy) socket?.send({ t: 'scroll', dx: sx, dy: sy });
    scrolled = { dx: scrolled.dx - sx, dy: scrolled.dy - sy };
    if (Math.abs(zoomed - 1) > 0.002) {
      socket?.send({ t: 'zoom', by: Math.round(zoomed * 1000) / 1000 });
      zoomed = 1;
    }
  }
  function soon() {
    if (!frame) frame = requestAnimationFrame(flush);
  }
  function midpoint() {
    const [a, b] = [...fingers.values()];
    return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  }
  function apart() {
    const [a, b] = [...fingers.values()];
    return Math.hypot(a.x - b.x, a.y - b.y);
  }

  function padDown(event) {
    // A finger after a quiet spell: is the socket still there?
    socket?.probe?.();
    event.currentTarget.setPointerCapture?.(event.pointerId);
    fingers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (fingers.size === 1 && gesture === null) {
      gesture = 'one';
      touchStart = performance.now();
      last = { x: event.clientX, y: event.clientY };
      travelled = 0;
    } else if (fingers.size === 2 && gesture === 'one') {
      // The second finger: no tap, no pointer movement, until decided.
      gesture = 'two';
      touchStart = null;
      middle = firstMiddle = midpoint();
      spread = firstSpread = apart();
    } else {
      gesture = 'done';
    }
  }

  function padMove(event) {
    if (!fingers.has(event.pointerId)) return;
    fingers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (gesture === 'one') {
      const dx = event.clientX - last.x;
      const dy = event.clientY - last.y;
      last = { x: event.clientX, y: event.clientY };
      travelled += Math.abs(dx) + Math.abs(dy);
      pending = { dx: pending.dx + dx, dy: pending.dy + dy };
      soon();
      return;
    }
    if (fingers.size !== 2) return;
    const m = midpoint();
    const d = apart();
    if (gesture === 'two') {
      if (Math.abs(d - firstSpread) > DECIDE * 1.5) gesture = 'zoom';
      else if (Math.hypot(m.x - firstMiddle.x, m.y - firstMiddle.y) > DECIDE) {
        gesture = 'scroll';
        // One direction per scroll: a list goes up and down, a row sideways.
        sideways = Math.abs(m.x - firstMiddle.x) > Math.abs(m.y - firstMiddle.y);
      } else return;
      // Counted from here, so the deciding distance is not a jump.
      middle = m;
      spread = d;
      return;
    }
    if (gesture === 'scroll') {
      scrolled = sideways
        ? { dx: scrolled.dx + m.x - middle.x, dy: 0 }
        : { dx: 0, dy: scrolled.dy + m.y - middle.y };
      middle = m;
      soon();
    } else if (gesture === 'zoom' && spread > 0) {
      zoomed *= d / spread;
      spread = d;
      soon();
    }
  }

  function padUp(event) {
    fingers.delete(event.pointerId);
    const was = gesture;
    if (fingers.size > 0) {
      if (gesture !== 'one') gesture = 'done';
      return;
    }
    gesture = null;
    last = null;
    if (was !== 'one' || touchStart === null) return;
    const quick = performance.now() - touchStart < TAP_MS && travelled < TAP_MOVE;
    touchStart = null;
    if (!quick) return;
    // **The keyboard opens inside this same touch** (ADR-0121 §4): the
    // panel has said in advance that the pointer is over a text field.
    ontap();
    socket?.send({ t: 'tap' });
  }

  function padCancel(event) {
    fingers.delete(event.pointerId);
    touchStart = null;
    if (fingers.size === 0) {
      gesture = null;
      last = null;
    } else {
      gesture = 'done';
    }
  }

  // ── The scroll strips (C11) ─────────────────────────────────────────────
  const SCROLL_STEP = 24;
  let strip = null;
  function stripDown(event, axis) {
    socket?.probe?.();
    event.currentTarget.setPointerCapture?.(event.pointerId);
    strip = { id: event.pointerId, axis, at: axis === 'y' ? event.clientY : event.clientX };
  }
  function stripMove(event) {
    if (!strip || event.pointerId !== strip.id) return;
    const now = strip.axis === 'y' ? event.clientY : event.clientX;
    const d = now - strip.at;
    if (Math.abs(d) < SCROLL_STEP) return;
    // The content follows the finger, as two fingers' scroll does.
    const by = Math.sign(d) * SCROLL_STEP;
    socket?.send(strip.axis === 'y' ? { t: 'scroll', dx: 0, dy: by } : { t: 'scroll', dx: by, dy: 0 });
    strip.at += by;
  }
  function stripUp() {
    strip = null;
  }

  function corner(which) {
    view(which, onsay);
  }
</script>

<div class="area">
  <div class="pad">
    {#if pad === 'touch'}
      <!-- A touch's own mousedown, after the tap, would take the focus from
           the phone's keyboard field (ADR-0121 §4): refused. -->
      <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
      <div class="touch" role="application" aria-label="Trackpad"
           onpointerdown={padDown} onpointermove={padMove} onpointerup={padUp} onpointercancel={padCancel}
           onmousedown={(e) => e.preventDefault()}></div>
    {:else}
      <div class="dpad-wrap">
        <div class="dpad">
          <button class="arrow arrow--up" type="button" aria-label="Up" onclick={() => press('up')}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.up} /></svg>
          </button>
          <button class="arrow arrow--down" type="button" aria-label="Down" onclick={() => press('down')}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.down} /></svg>
          </button>
          <button class="arrow arrow--left" type="button" aria-label="Left" onclick={() => press('left')}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.left} /></svg>
          </button>
          <button class="arrow arrow--right" type="button" aria-label="Right" onclick={() => press('right')}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.right} /></svg>
          </button>
          <button class="ok" type="button" aria-label="OK" onclick={() => press('ok')}>OK</button>
        </div>
      </div>
    {/if}

    {#if pad === 'touch' && socket}
      <div class="strip strip--v" role="application" aria-label="Scroll up and down"
           onpointerdown={(e) => stripDown(e, 'y')} onpointermove={stripMove} onpointerup={stripUp} onpointercancel={stripUp}>
        <span class="strip__line"></span>
        <span class="strip__mark"></span>
      </div>
      <div class="strip strip--h" role="application" aria-label="Scroll left and right"
           onpointerdown={(e) => stripDown(e, 'x')} onpointermove={stripMove} onpointerup={stripUp} onpointercancel={stripUp}>
        <span class="strip__line"></span>
        <span class="strip__mark"></span>
      </div>
    {/if}

    <button class="corner corner--tl" class:is-on={lit('home')} type="button" aria-label="Home" onclick={() => corner('home')}>
      <svg class="stroke" viewBox="0 0 24 24" aria-hidden="true"><path d={STROKED.home} /></svg>
    </button>
    <button class="corner corner--tr" class:is-on={lit('lyrics')} type="button" aria-label="Lyrics"
            disabled={!$active} onclick={() => corner('lyrics')}>
      <svg class="stroke" viewBox="0 0 24 24" aria-hidden="true"><path d={STROKED.lyrics} /></svg>
    </button>
    <button class="corner corner--bl" type="button" aria-label="Back" onclick={() => press('back')}>
      <svg class="fill" viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.back} /></svg>
    </button>
    {#if $meters}
      <button class="corner corner--br" class:is-on={lit('meters')} type="button" aria-label="Meters" onclick={() => corner('meters')}>
        <svg class="stroke" viewBox="0 0 24 24" aria-hidden="true"><path d={STROKED.meters} /></svg>
      </button>
    {/if}

    {#if padSwitch}
      <div class="switch">
        <span class="switch__ind" style:transform={pad === 'dpad' ? 'translateX(44px)' : 'none'}></span>
        <button class="seg" class:is-on={pad === 'touch'} type="button" aria-label="Trackpad" aria-pressed={pad === 'touch'}
                onclick={() => onpad('touch')}>
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="4.5" y="3" width="15" height="18" rx="3" /><circle cx="12" cy="11" r="2.4" />
          </svg>
        </button>
        <button class="seg" class:is-on={pad === 'dpad'} type="button" aria-label="D-pad" aria-pressed={pad === 'dpad'}
                onclick={() => onpad('dpad')}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.dpad} fill="currentColor" /></svg>
        </button>
      </div>
    {/if}
  </div>
</div>

<style>
  /* C10: the drawing's height and more; shorter, down to where the D-pad
     still clears the pad switch, before the page scrolls. */
  .area {
    flex: 1 1 0;
    min-height: 312px;
    margin-top: 12px;
    display: flex;
  }
  .pad {
    position: relative;
    flex: 1;
    min-width: 0;
    border-radius: var(--remote-touch-radius);
    background: var(--remote-touch-ground);
    border: 1px solid var(--remote-touch-line);
    overflow: hidden;
  }
  .touch {
    position: absolute;
    inset: 0;
    touch-action: none;
    cursor: default;
  }
  .dpad-wrap {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding-top: 20px;
    box-sizing: border-box;
  }
  .dpad {
    position: relative;
    width: 216px;
    height: 216px;
    border-radius: 50%;
    background: rgba(233, 238, 242, 0.06);
    border: 1px solid rgba(233, 238, 242, 0.12);
    box-sizing: border-box;
    flex-shrink: 0;
  }
  .arrow {
    position: absolute;
    border: 0;
    padding: 0;
    background: none;
    border-radius: 14px;
    display: grid;
    place-items: center;
    cursor: pointer;
    color: #e9eef2;
  }
  .arrow:active {
    background: rgba(126, 214, 188, 0.18);
  }
  .arrow svg {
    width: 32px;
    height: 32px;
    fill: currentColor;
  }
  .arrow--up { left: 32%; top: 3%; width: 36%; height: 28%; }
  .arrow--down { left: 32%; bottom: 3%; width: 36%; height: 28%; }
  .arrow--left { top: 32%; left: 3%; width: 28%; height: 36%; }
  .arrow--right { top: 32%; right: 3%; width: 28%; height: 36%; }
  .ok {
    position: absolute;
    left: 32%;
    top: 32%;
    width: 36%;
    height: 36%;
    border-radius: 50%;
    background: var(--remote-button-ground);
    border: 1px solid var(--remote-button-line);
    box-sizing: border-box;
    display: grid;
    place-items: center;
    cursor: pointer;
    color: #e9eef2;
    font: inherit;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.04em;
    padding: 0;
  }
  .ok:active {
    transform: scale(0.95);
  }
  /* OK, the corners and the switch look as the quick actions do, not the
     drawing's dark ground (George, 2026-10-27). */
  .corner {
    position: absolute;
    width: var(--remote-corner);
    height: var(--remote-corner);
    border-radius: 50%;
    background: var(--remote-button-ground);
    border: 1px solid var(--remote-button-line);
    box-sizing: border-box;
    display: grid;
    place-items: center;
    cursor: pointer;
    padding: 0;
    color: #e9eef2;
  }
  .corner:active {
    transform: scale(0.94);
  }
  .corner.is-on {
    color: #7ed6bc;
  }
  .corner:disabled {
    opacity: 0.38;
    cursor: default;
  }
  .corner--tl { left: 10px; top: 10px; }
  .corner--tr { right: 10px; top: 10px; }
  .corner--bl { left: 10px; bottom: 10px; }
  .corner--br { right: 10px; bottom: 10px; }
  .corner svg {
    width: 22px;
    height: 22px;
  }
  .corner .fill {
    fill: currentColor;
  }
  .corner .stroke {
    fill: none;
    stroke: currentColor;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .strip {
    position: absolute;
    touch-action: none;
  }
  .strip--v {
    right: 20px;
    top: 28%;
    bottom: 28%;
    width: 28px;
    cursor: ns-resize;
  }
  .strip--h {
    left: 28%;
    right: 28%;
    bottom: 20px;
    height: 28px;
    cursor: ew-resize;
  }
  .strip__line,
  .strip__mark {
    position: absolute;
    display: block;
    pointer-events: none;
  }
  .strip__line {
    background: var(--remote-scroll-line);
  }
  .strip--v .strip__line { left: 50%; top: 0; bottom: 0; width: 1px; margin-left: -0.5px; }
  .strip--h .strip__line { top: 50%; left: 0; right: 0; height: 1px; margin-top: -0.5px; }
  /* Still: nothing moves or changes colour while dragging (the design). */
  .strip__mark {
    border-radius: 2px;
    background: var(--remote-scroll-thumb);
  }
  .strip--v .strip__mark { left: 50%; top: 50%; width: 3px; height: 24px; margin: -12px 0 0 -1.5px; }
  .strip--h .strip__mark { top: 50%; left: 50%; height: 3px; width: 24px; margin: -1.5px 0 0 -12px; }
  .switch {
    position: absolute;
    left: 50%;
    top: 12px;
    transform: translateX(-50%);
    display: flex;
    padding: 3px;
    border-radius: 14px;
    background: var(--remote-button-ground);
    border: 1px solid var(--remote-button-line);
  }
  .switch__ind {
    position: absolute;
    left: 3px;
    top: 3px;
    width: 44px;
    height: 36px;
    border-radius: 11px;
    background: var(--remote-select);
    transition: transform var(--remote-slide);
    pointer-events: none;
  }
  .seg {
    position: relative;
    width: 44px;
    height: 36px;
    border-radius: 11px;
    border: 0;
    padding: 0;
    background: none;
    display: grid;
    place-items: center;
    cursor: pointer;
    color: rgba(233, 238, 242, 0.72);
    transition: color 200ms ease;
  }
  .seg.is-on {
    color: #7ed6bc;
  }
  .seg svg {
    width: 19px;
    height: 19px;
  }
</style>
