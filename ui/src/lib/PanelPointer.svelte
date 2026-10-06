<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0121: the pointer a phone moves on the panel. Relative, as a laptop's
  touchpad: each move shifts it from where it is, scaled by Pointer speed,
  so a bar and a 16:9 panel take the same touchpad. Shown only while a phone
  is controlling - it hides after 5 seconds with no move and no tap
  (George, 2026-10-05). A tap lands on what lies under it; typing goes into
  the field that has focus, inserted as text so any character works.

  The panel tells the phones, in advance, whether the pointer is over a text
  field - so the phone's tap there can open its keyboard within that same
  touch, the one moment a browser allows it (ADR-0121 §4).

  Two styles, from Claude Design's *Cursors* handoff (ADR-0121 §3), chosen
  by Pointer style: **Dot** - a dot, a ring around a small round control, a
  pill over a slider or while two fingers scroll - and **Arrow**, with a
  ring at its tip over what can be pressed and a double arrow over a
  slider. The shapes are drawn where the control is; **the pointer itself
  never moves to it**, so it stays where the finger left it.
-->
<script>
  import { onDestroy } from 'svelte';
  import { settingValues } from './settings.js';
  import { openTouchpad, takesText, fieldOf } from './touchpad.js';

  const HIDE_MS = 5000;
  //: Pinch: from the panel as it is to three times as large (ADR-0121 §2).
  const ZOOM_MAX = 3;

  let x = $state(window.innerWidth / 2);
  let y = $state(window.innerHeight / 2);
  let shown = $state(false);
  //: What the pointer is over, for its shape: 'plain', 'press', 'slide',
  //: or 'scroll' / 'scrollx' while two fingers scroll down or across.
  let kind = $state('plain');
  //: The ring around a small round control: its centre and size, or null.
  let ring = $state(null);
  let scrolledAt = 0;
  //: Which way two fingers last scrolled, for the shape: up-down or across.
  let scrolledX = false;
  //: After a tap, no ring until the pointer moves: what was pressed has
  //: done its work, and a ring left on whatever stands in its place reads as
  //: the press still held (George, 2026-10-06: "stays in place for a few
  //: seconds until it's hidden").
  let tapped = false;
  let hideTimer;
  let pad = null;
  let over = false;

  const on = $derived($settingValues.phone_touchpad !== false);
  const speed = $derived(Math.max(0.25, Number($settingValues.pointer_speed ?? 150) / 100));
  const arrow = $derived($settingValues.pointer_style === 'Arrow');

  //: Pressable things and sliders, as the panel marks them.
  const PRESSABLE = 'button, a[href], input, select, textarea, label, summary, [role=button], [role=tab], [role=switch], [role=checkbox], [role=option], [role=menuitem], [role=link]';
  const SLIDER = '[role=slider], input[type=range], .slider';
  //: The design's round control: width and height within 1.6 of each other.
  //: And small - the design drew rings round buttons; a home screen card is
  //: as square, and a ring round it would cover the screen.
  const ROUND = 1.6;
  const RING_MAX = 96;

  /** The pointer's shape for what lies under it, what it is over, and
   *  whether that takes text - asked on every move and four times a second
   *  while shown, since a tap or the player can change the screen under a
   *  pointer that has not moved (2026-10-05: a ring left round a button that
   *  had gone, and a field that opened under the pointer not offered to the
   *  phone's keyboard). */
  function look() {
    const target = under();
    hover(target);
    const field = !!fieldOf(target);
    if (field !== over) {
      over = field;
      pad?.send({ t: 'over', field });
    }
    const slider = target?.closest(SLIDER);
    const pressable = !slider && target?.closest(PRESSABLE);
    kind = performance.now() - scrolledAt < 400 ? (scrolledX ? 'scrollx' : 'scroll') : slider ? 'slide' : pressable ? 'press' : 'plain';
    ring = null;
    if (tapped) return;
    // A ring for a button that is only an icon: a tab or a row with words in
    // it is not the design's round control, however square (George,
    // 2026-10-05: "the track entry in now playing shouldn't get the
    // highlight").
    if (kind === 'press' && !arrow && !words(pressable)) {
      const r = pressable.getBoundingClientRect();
      const long = Math.max(r.width, r.height);
      if (long / Math.max(1, Math.min(r.width, r.height)) < ROUND && long <= RING_MAX) {
        ring = { cx: r.left + r.width / 2, cy: r.top + r.height / 2, size: long + 16 };
      }
    }
  }

  /** A button's own words - a count on a badge is not one (the queue
   *  button's "up next", George 2026-10-06). */
  function words(el) {
    let text = '';
    const walk = (node) => {
      for (const child of node.childNodes) {
        if (child.nodeType === Node.TEXT_NODE) text += child.textContent;
        else if (child.nodeType === Node.ELEMENT_NODE && !child.hasAttribute('data-badge')) walk(child);
      }
    };
    walk(el);
    return text.trim();
  }

  $effect(() => {
    if (!on) return;
    pad = openTouchpad(receive);
    const focusChanged = () => pad?.send({ t: 'focus', field: takesText(document.activeElement) });
    // After a focus-out the new focus is not yet set; read it a moment later.
    const focusLeft = () => setTimeout(focusChanged, 0);
    document.addEventListener('focusin', focusChanged);
    document.addEventListener('focusout', focusLeft);
    return () => {
      document.removeEventListener('focusin', focusChanged);
      document.removeEventListener('focusout', focusLeft);
      pad?.close();
      pad = null;
      rest();
      unzoom();
    };
  });

  onDestroy(() => {
    cancelAnimationFrame(moveFrame);
    clearTimeout(hideTimer);
    clearInterval(lookTimer);
  });

  let lookTimer;

  function wake() {
    shown = true;
    clearTimeout(hideTimer);
    hideTimer = setTimeout(rest, HIDE_MS);
    if (!lookTimer) lookTimer = setInterval(look, 250);
  }

  /** Hidden: the pointer has left whatever it was over. */
  function rest() {
    shown = false;
    clearInterval(lookTimer);
    lookTimer = undefined;
    hover(null);
    ring = null;
  }

  // ── Hover, as a mouse gives it ─────────────────────────────────────────
  //: What the pointer is over, outermost first. Entering and leaving are
  //: told as a mouse's are - so the volume drawer holds open while the
  //: pointer rests on it (George, 2026-10-05) - and never otherwise acted on.
  let hovered = [];

  function hover(target) {
    const chain = [];
    for (let el = target; el; el = el.parentElement) chain.unshift(el);
    let same = 0;
    while (same < chain.length && same < hovered.length && chain[same] === hovered[same]) same += 1;
    const at = { clientX: x, clientY: y, pointerId: 1, pointerType: 'mouse', isPrimary: true, view: window };
    const left = hovered.slice(same).reverse();
    if (left.length) left[0].dispatchEvent(new PointerEvent('pointerout', { ...at, bubbles: true, composed: true }));
    for (const el of left) el.dispatchEvent(new PointerEvent('pointerleave', at));
    const entered = chain.slice(same);
    if (entered.length) entered[entered.length - 1].dispatchEvent(new PointerEvent('pointerover', { ...at, bubbles: true, composed: true }));
    for (const el of entered) el.dispatchEvent(new PointerEvent('pointerenter', at));
    hovered = chain;
  }

  /** What lies under the pointer; the pointer itself takes no events. */
  function under() {
    return document.elementFromPoint(Math.round(x), Math.round(y));
  }

  //: **Moves land once a frame** (George, 2026-10-06: "sometimes the cursor
  //: movement is choppy still"). Wi-Fi delivers the phone's moves in bunches,
  //: and each one asked what lies under the pointer - a layout on a busy
  //: page; now the frame's moves are added up and asked about once.
  let moved = { dx: 0, dy: 0 };
  let moveFrame = 0;
  function applyMove() {
    moveFrame = 0;
    x = edge(x + moved.dx * speed, window.innerWidth, 'x');
    y = edge(y + moved.dy * speed, window.innerHeight, 'y');
    moved = { dx: 0, dy: 0 };
    wake();
    look();
  }

  function receive(message) {
    switch (message.t) {
      case 'move': {
        tapped = false;
        moved.dx += Number(message.dx || 0);
        moved.dy += Number(message.dy || 0);
        if (!moveFrame) moveFrame = requestAnimationFrame(applyMove);
        break;
      }
      case 'tap':
        wake();
        tapped = true;
        tap();
        // What the tap opened is now under the pointer.
        requestAnimationFrame(look);
        break;
      case 'text':
        insert(String(message.text ?? ''));
        break;
      case 'key':
        key(String(message.key ?? ''));
        break;
      case 'scroll':
        wake();
        scrolledAt = performance.now();
        scrolledX = Math.abs(Number(message.dx || 0)) > Math.abs(Number(message.dy || 0));
        scroll(Number(message.dx || 0), Number(message.dy || 0));
        look();
        break;
      case 'zoom':
        wake();
        zoomBy(Number(message.by) || 1);
        look();
        break;
      case 'gone':
        // A phone's sheet closed, or the phone went: never leave the panel
        // zoomed for whoever looks at it next.
        unzoom();
        break;
    }
  }

  // ── Two fingers (ADR-0121 §2, amended 2026-10-05) ─────────────────────

  /** **The content follows the fingers**, as on the phone's own screen:
   *  fingers up move the list up. What scrolls is the nearest thing under
   *  the pointer that scrolls that way; the page otherwise. */
  function scroll(dx, dy) {
    if (dy) scroller(under(), 'y')?.scrollBy({ top: -dy * speed, behavior: 'instant' });
    if (dx) scroller(under(), 'x')?.scrollBy({ left: -dx * speed, behavior: 'instant' });
  }

  function scroller(element, axis) {
    for (let el = element; el && el !== document.documentElement; el = el.parentElement) {
      const style = getComputedStyle(el);
      const overflow = axis === 'y' ? style.overflowY : style.overflowX;
      const room = axis === 'y' ? el.scrollHeight > el.clientHeight : el.scrollWidth > el.clientWidth;
      if (room && /(auto|scroll)/.test(overflow)) return el;
    }
    return document.scrollingElement;
  }

  //: The panel's magnification and where its corner sits on the screen.
  let zoom = 1;
  let tx = 0;
  let ty = 0;

  /** Larger or smaller around the pointer: what is under it stays under it. */
  function zoomBy(by) {
    const next = Math.max(1, Math.min(ZOOM_MAX, zoom * by));
    if (next === zoom) return;
    tx = x - ((x - tx) / zoom) * next;
    ty = y - ((y - ty) / zoom) * next;
    zoom = next;
    paint();
  }

  function unzoom() {
    zoom = 1;
    tx = 0;
    ty = 0;
    paint();
  }

  /** Zoomed, the pointer pushing past an edge moves the view instead. */
  function edge(to, size, axis) {
    const inside = Math.max(0, Math.min(size - 1, to));
    if (zoom > 1 && inside !== to) {
      if (axis === 'x') tx -= to - inside;
      else ty -= to - inside;
      paint();
    }
    return inside;
  }

  /** The whole page drawn at `zoom`, kept covering the screen. */
  function paint() {
    const app = document.getElementById('app');
    if (!app) return;
    tx = Math.min(0, Math.max(window.innerWidth * (1 - zoom), tx));
    ty = Math.min(0, Math.max(window.innerHeight * (1 - zoom), ty));
    if (zoom === 1) {
      app.style.transform = '';
      app.style.transformOrigin = '';
      document.documentElement.classList.remove('panel-zoomed');
      return;
    }
    app.style.transformOrigin = '0 0';
    app.style.transform = `translate(${tx}px, ${ty}px) scale(${zoom})`;
    document.documentElement.classList.add('panel-zoomed');
  }

  /** The pointer lives outside the page it points at: a zoom drawn on the
   *  page must not carry the pointer with it. */
  function outside(node) {
    document.body.appendChild(node);
    return { destroy: () => node.remove() };
  }

  /** A tap where the pointer is: the events a finger's tap would make.
   *  As the mouse's (pointer 1): a control that captures the pointer can
   *  only capture one that exists, and any other id throws, which left the
   *  volume slider held (measured on gexis, 2026-10-05). */
  function tap() {
    const target = under();
    if (!target) return;
    const at = { bubbles: true, cancelable: true, composed: true, clientX: x, clientY: y, view: window };
    const pointer = { ...at, pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0, buttons: 1 };
    target.dispatchEvent(new PointerEvent('pointerdown', pointer));
    target.dispatchEvent(new MouseEvent('mousedown', { ...at, button: 0, buttons: 1 }));
    fieldOf(target)?.focus();
    target.dispatchEvent(new PointerEvent('pointerup', { ...pointer, buttons: 0 }));
    target.dispatchEvent(new MouseEvent('mouseup', { ...at, button: 0 }));
    target.dispatchEvent(new MouseEvent('click', { ...at, button: 0 }));
    if (target instanceof HTMLInputElement && target.type === 'range') slide(target);
  }

  /** A browser's own slider ignores made-up events: set it to where the tap
   *  landed, as a finger's tap on its track would, and say so. */
  function slide(range) {
    const r = range.getBoundingClientRect();
    const min = Number(range.min || 0);
    const max = Number(range.max || 100);
    range.value = String(min + Math.min(1, Math.max(0, (x - r.left) / r.width)) * (max - min));
    range.dispatchEvent(new Event('input', { bubbles: true }));
    range.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function insert(text) {
    const field = document.activeElement;
    if (!text || !takesText(field)) return;
    if (field.isContentEditable) {
      document.execCommand('insertText', false, text);
      return;
    }
    const start = field.selectionStart ?? field.value.length;
    const end = field.selectionEnd ?? start;
    field.setRangeText(text, start, end, 'end');
    field.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: text }));
  }

  function key(name) {
    const field = document.activeElement;
    if (!takesText(field)) return;
    if (name === 'Backspace') {
      if (field.isContentEditable) {
        document.execCommand('delete');
        return;
      }
      const start = field.selectionStart ?? field.value.length;
      const end = field.selectionEnd ?? start;
      if (start === end && start === 0) return;
      field.setRangeText('', start === end ? start - 1 : start, end, 'end');
      field.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'deleteContentBackward' }));
      return;
    }
    if (name === 'Enter') {
      const at = { bubbles: true, cancelable: true, key: 'Enter', code: 'Enter' };
      const unhandled = field.dispatchEvent(new KeyboardEvent('keydown', at));
      field.dispatchEvent(new KeyboardEvent('keyup', at));
      if (unhandled) field.form?.requestSubmit();
    }
  }
</script>

{#if on}
  {#if ring}
    <div
      class="ring"
      class:shown
      use:outside
      style:transform={`translate(${ring.cx}px, ${ring.cy}px)`}
      style:--size={`${ring.size}px`}
      aria-hidden="true"
    ></div>
  {/if}
  <div class="pointer" class:shown use:outside style:transform={`translate(${x}px, ${y}px)`} aria-hidden="true">
    {#if arrow}
      <!-- The Arrow set: 32 px, its point (6, 4) on the pointer. -->
      {#if kind === 'slide'}
        <svg class="arrow arrow--drag" viewBox="0 0 32 32" width="32" height="32">
          <path d="M3 16l6.5-6.5v4.3h13v-4.3L29 16l-6.5 6.5v-4.3h-13v4.3z" />
        </svg>
      {:else}
        <svg class="arrow" viewBox="0 0 32 32" width="32" height="32">
          {#if kind === 'press'}<circle class="arrow__press" cx="6" cy="4" r="4.6" />{/if}
          <path d="M6 4l20 10.5-9.6 2.6L12.6 27z" />
        </svg>
      {/if}
    {:else}
      <!-- The Dot set: a 28 px dot that becomes a pill over a slider (48 x 22)
           or while two fingers scroll (22 x 48), and a small dot inside a
           ring round a small round control. -->
      <span class="dot dot--{ring ? 'ringed' : kind}">
        <svg class="dot__marks" class:on={kind === 'slide' || kind === 'scroll' || kind === 'scrollx'} viewBox="0 0 64 64" aria-hidden="true">
          {#if kind === 'scroll'}
            <path d="M26 22l6-6 6 6M26 42l6 6 6-6" />
          {:else}
            <path d="M22 26l-6 6 6 6M42 26l6 6-6 6" />
          {/if}
        </svg>
      </span>
    {/if}
  </div>
{/if}

<style>
  :global(html.panel-zoomed),
  :global(html.panel-zoomed body) {
    overflow: hidden;
  }
  .pointer,
  .ring {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 1000;
    pointer-events: none;
    will-change: transform;
    opacity: 0;
    transition: opacity 300ms ease-out;
  }
  .pointer.shown,
  .ring.shown {
    opacity: 1;
    transition-duration: 0ms;
  }

  /* The Arrow set (Claude Design, Cursors, mouse 2c). */
  .arrow {
    position: absolute;
    left: -6px;
    top: -4px;
    display: block;
    fill: #7ed6bc;
    stroke: #0c1014;
    stroke-width: 1.6;
    stroke-linejoin: round;
  }
  .arrow--drag {
    left: -16px;
    top: -16px;
  }
  .arrow__press {
    fill: rgba(233, 238, 242, 0.2);
    stroke: #e9eef2;
    stroke-width: 1.8;
  }

  /* The Dot set (Claude Design, Cursors, remote 2g). Shape changes take
     140 ms; the position follows at once - a glide would add to the
     touchpad's round trip (ADR-0121 §3). */
  .dot {
    position: absolute;
    left: 0;
    top: 0;
    width: 28px;
    height: 28px;
    transform: translate(-50%, -50%);
    border-radius: 999px;
    background: #7ed6bc;
    border: 2.4px solid #0c1014;
    box-sizing: border-box;
    transition:
      width 140ms ease-out,
      height 140ms ease-out,
      border-width 140ms ease-out;
  }
  .dot--slide {
    width: 48px;
    height: 22px;
  }
  .dot--scroll {
    width: 22px;
    height: 48px;
  }
  /* Across: the slider's pill and its left-right marks. */
  .dot--scrollx {
    width: 48px;
    height: 22px;
  }
  .dot--ringed {
    width: 9px;
    height: 9px;
    border-width: 0;
  }
  .dot__marks {
    position: absolute;
    left: 50%;
    top: 50%;
    width: 64px;
    height: 64px;
    transform: translate(-50%, -50%);
    fill: none;
    stroke: #0c1014;
    stroke-width: 3;
    stroke-linecap: round;
    stroke-linejoin: round;
    opacity: 0;
    transition: opacity 140ms ease-out;
  }
  .dot__marks.on {
    opacity: 1;
  }
  .ring {
    width: var(--size);
    height: var(--size);
    margin: calc(var(--size) / -2) 0 0 calc(var(--size) / -2);
    border-radius: 999px;
    border: 4px solid #7ed6bc;
    background: rgba(233, 238, 242, 0.14);
    box-sizing: border-box;
  }
</style>
