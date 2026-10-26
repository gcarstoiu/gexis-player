<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0164 D3: the touch area of a player with a screen (design/source/21,
  *Touch area*). Corner buttons for Home, Lyrics, Back and Meters; a switch
  between the two pads, both driving the panel's D-pad ring (ADR-0161):

  - **Touchpad**: every 52 px of travel on the main axis sends one step and
    starts counting again; a release that never stepped is OK if it moved
    under 12 px, else one step its way. What was sent is named for a second,
    counting repeats (*Up × 3*). The strips along the right and bottom edges
    scroll, a step each 24 px (C11).
  - **D-pad**: the arrows and OK as buttons, with no name shown.

  OK calls `onok` first, inside the touch, so the phone's keyboard can open
  for a text field the ring is on (C5).
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
    ontouch = () => {},
    onsay = () => {},
  } = $props();

  const STEP = 52;
  const TAP = 12;
  const SCROLL_STEP = 24;
  const NAMES = { up: 'Up', down: 'Down', left: 'Left', right: 'Right', ok: 'OK', back: 'Back' };

  const off = $derived(!!$panel.standby);
  const lit = (which) => !off && $showing === which;

  // ── What was sent, named ────────────────────────────────────────────────
  let sent = $state(null);
  let count = $state(0);
  let sentOn = $state(false);
  let sentTimer;
  let goneTimer;
  function press(name, quiet = false) {
    ontouch();
    if (name === 'ok') onok();
    key(name);
    if (quiet) return;
    clearTimeout(sentTimer);
    clearTimeout(goneTimer);
    count = sent === name ? count + 1 : 1;
    sent = name;
    sentOn = true;
    sentTimer = setTimeout(() => {
      sentOn = false;
      goneTimer = setTimeout(() => (sent = null), 240);
    }, 1000);
  }
  const sentText = $derived(sent ? NAMES[sent] + (count > 1 ? ` × ${count}` : '') : '');

  const dir = (dx, dy) => (Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : dy > 0 ? 'down' : 'up');

  // ── The touchpad ────────────────────────────────────────────────────────
  let finger = null;
  let dot = $state(null);
  let lastDot = { x: -100, y: -100 };
  function point(event, el) {
    const r = el.getBoundingClientRect();
    return { x: event.clientX - r.left, y: event.clientY - r.top };
  }
  function padDown(event) {
    if (finger) return;
    const el = event.currentTarget;
    el.setPointerCapture?.(event.pointerId);
    const a = point(event, el);
    finger = { id: event.pointerId, sx: a.x, sy: a.y, ax: a.x, ay: a.y, stepped: false };
    dot = a;
    socket?.probe?.();
  }
  function padMove(event) {
    if (!finger || event.pointerId !== finger.id) return;
    const a = point(event, event.currentTarget);
    const dx = a.x - finger.ax;
    const dy = a.y - finger.ay;
    if (Math.max(Math.abs(dx), Math.abs(dy)) >= STEP) {
      press(dir(dx, dy));
      finger.ax = a.x;
      finger.ay = a.y;
      finger.stepped = true;
    }
    dot = a;
  }
  function padUp(event) {
    if (!finger || event.pointerId !== finger.id) return;
    const f = finger;
    finger = null;
    if (!f.stepped) {
      const a = point(event, event.currentTarget);
      const dx = a.x - f.sx;
      const dy = a.y - f.sy;
      press(Math.hypot(dx, dy) < TAP ? 'ok' : dir(dx, dy));
    }
    dot = null;
  }
  function padCancel() {
    finger = null;
    dot = null;
  }
  const shownDot = $derived.by(() => {
    if (dot) lastDot = dot;
    return dot ?? lastDot;
  });

  // ── The scroll strips ───────────────────────────────────────────────────
  let strip = null;
  let thumb = $state(null);
  function fraction(event, el, axis) {
    const r = el.getBoundingClientRect();
    const f = axis === 'y' ? (event.clientY - r.top) / r.height : (event.clientX - r.left) / r.width;
    return Math.max(0.12, Math.min(0.88, f));
  }
  function stripDown(event, axis) {
    const el = event.currentTarget;
    el.setPointerCapture?.(event.pointerId);
    strip = { id: event.pointerId, axis, at: axis === 'y' ? event.clientY : event.clientX };
    thumb = { axis, f: fraction(event, el, axis) };
    ontouch();
  }
  function stripMove(event) {
    if (!strip || event.pointerId !== strip.id) return;
    const now = strip.axis === 'y' ? event.clientY : event.clientX;
    const d = now - strip.at;
    if (Math.abs(d) >= SCROLL_STEP) {
      socket?.send({ t: 'scroll', step: strip.axis, by: Math.sign(d) });
      strip.at = now;
    }
    thumb = { axis: strip.axis, f: fraction(event, event.currentTarget, strip.axis) };
  }
  function stripUp() {
    strip = null;
    thumb = null;
  }

  function corner(which) {
    ontouch();
    view(which, onsay);
  }
</script>

<div class="area">
  <div class="pad">
    {#if pad === 'touch'}
      <!-- A touch's own mousedown, after the tap, would take the focus from
           the phone's keyboard field (ADR-0121 §4): refused. -->
      <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
      <div class="touch" role="application" aria-label="Touchpad"
           onpointerdown={padDown} onpointermove={padMove} onpointerup={padUp} onpointercancel={padCancel}
           onmousedown={(e) => e.preventDefault()}>
        <div class="hint" style:opacity={dot || sentOn ? 0 : 1}>
          <span>Swipe to move</span>
          <span>Tap to choose</span>
        </div>
        <span class="dot" style:left={`${shownDot.x}px`} style:top={`${shownDot.y}px`} style:opacity={dot ? 1 : 0}></span>
      </div>
    {:else}
      <div class="dpad-wrap">
        <div class="dpad">
          <button class="arrow arrow--up" type="button" aria-label="Up" onclick={() => press('up', true)}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.up} /></svg>
          </button>
          <button class="arrow arrow--down" type="button" aria-label="Down" onclick={() => press('down', true)}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.down} /></svg>
          </button>
          <button class="arrow arrow--left" type="button" aria-label="Left" onclick={() => press('left', true)}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.left} /></svg>
          </button>
          <button class="arrow arrow--right" type="button" aria-label="Right" onclick={() => press('right', true)}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.right} /></svg>
          </button>
          <button class="ok" type="button" aria-label="OK" onclick={() => press('ok', true)}>OK</button>
        </div>
      </div>
    {/if}

    <button class="corner corner--bl" type="button" aria-label="Back" onclick={() => press('back')}>
      <svg class="fill" viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.back} /></svg>
    </button>
    <button class="corner corner--tl" class:is-on={lit('home')} type="button" aria-label="Home" onclick={() => corner('home')}>
      <svg class="stroke" viewBox="0 0 24 24" aria-hidden="true"><path d={STROKED.home} /></svg>
    </button>
    <button class="corner corner--tr" class:is-on={lit('lyrics')} type="button" aria-label="Lyrics"
            disabled={!$active} onclick={() => corner('lyrics')}>
      <svg class="stroke" viewBox="0 0 24 24" aria-hidden="true"><path d={STROKED.lyrics} /></svg>
    </button>
    {#if $meters}
      <button class="corner corner--br" class:is-on={lit('meters')} type="button" aria-label="Meters" onclick={() => corner('meters')}>
        <svg class="stroke" viewBox="0 0 24 24" aria-hidden="true"><path d={STROKED.meters} /></svg>
      </button>
    {/if}

    {#if pad === 'touch' && socket}
      <div class="strip strip--v" role="application" aria-label="Scroll up and down"
           onpointerdown={(e) => stripDown(e, 'y')} onpointermove={stripMove} onpointerup={stripUp} onpointercancel={stripUp}>
        <span class="strip__line"></span>
        <span class="strip__thumb" class:is-on={thumb?.axis === 'y'} style:top={`${thumb?.axis === 'y' ? thumb.f * 100 : 50}%`}></span>
      </div>
      <div class="strip strip--h" role="application" aria-label="Scroll left and right"
           onpointerdown={(e) => stripDown(e, 'x')} onpointermove={stripMove} onpointerup={stripUp} onpointercancel={stripUp}>
        <span class="strip__line"></span>
        <span class="strip__thumb" class:is-on={thumb?.axis === 'x'} style:left={`${thumb?.axis === 'x' ? thumb.f * 100 : 50}%`}></span>
      </div>
    {/if}

    <span class="sent" style:opacity={sentOn ? 1 : 0}>{sentText}</span>

    {#if padSwitch}
      <div class="switch">
        <span class="switch__ind" style:transform={pad === 'dpad' ? 'translateX(44px)' : 'none'}></span>
        <button class="seg" class:is-on={pad === 'touch'} type="button" aria-label="Touchpad" aria-pressed={pad === 'touch'}
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
  .area {
    flex: 1;
    min-height: 0;
    margin-top: 14px;
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
    cursor: pointer;
  }
  .hint {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    pointer-events: none;
    color: rgba(233, 238, 242, 0.6);
    font-size: 15px;
    white-space: nowrap;
    transition: opacity 200ms ease;
  }
  .dot {
    position: absolute;
    width: 68px;
    height: 68px;
    margin: -34px 0 0 -34px;
    border-radius: 50%;
    box-sizing: border-box;
    background: rgba(126, 214, 188, 0.16);
    border: 1.5px solid rgba(126, 214, 188, 0.6);
    pointer-events: none;
    transition: opacity 160ms ease;
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
    background: #16232c;
    border: 1px solid rgba(233, 238, 242, 0.16);
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
  .corner {
    position: absolute;
    width: var(--remote-corner);
    height: var(--remote-corner);
    border-radius: 50%;
    background: var(--remote-control-ground);
    border: 1px solid rgba(233, 238, 242, 0.14);
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
  .strip__line {
    position: absolute;
    display: block;
    pointer-events: none;
    background: var(--remote-scroll-line);
  }
  .strip--v .strip__line { left: 50%; top: 0; bottom: 0; width: 1px; margin-left: -0.5px; }
  .strip--h .strip__line { top: 50%; left: 0; right: 0; height: 1px; margin-top: -0.5px; }
  .strip__thumb {
    position: absolute;
    display: block;
    border-radius: 2px;
    pointer-events: none;
    background: var(--remote-scroll-thumb);
    transition: background 120ms ease;
  }
  .strip__thumb.is-on {
    background: #7ed6bc;
  }
  .strip--v .strip__thumb { left: 50%; width: 3px; height: 24px; margin: -12px 0 0 -1.5px; }
  .strip--h .strip__thumb { top: 50%; height: 3px; width: 24px; margin: -1.5px 0 0 -12px; }
  .sent {
    position: absolute;
    left: 64px;
    right: 64px;
    bottom: 46px;
    text-align: center;
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #7ed6bc;
    pointer-events: none;
    transition: opacity 220ms ease;
  }
  .switch {
    position: absolute;
    left: 50%;
    top: 12px;
    transform: translateX(-50%);
    display: flex;
    padding: 3px;
    border-radius: 14px;
    background: var(--remote-control-ground);
    border: 1px solid var(--remote-control-line);
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
