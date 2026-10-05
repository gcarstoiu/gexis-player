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
-->
<script>
  import { onDestroy } from 'svelte';
  import { settingValues } from './settings.js';
  import { openTouchpad, takesText } from './touchpad.js';

  const HIDE_MS = 5000;
  //: Pinch: from the panel as it is to three times as large (ADR-0121 §2).
  const ZOOM_MAX = 3;

  let x = $state(window.innerWidth / 2);
  let y = $state(window.innerHeight / 2);
  let shown = $state(false);
  let hideTimer;
  let pad = null;
  let over = false;

  const on = $derived($settingValues.phone_touchpad !== false);
  const speed = $derived(Math.max(0.25, Number($settingValues.pointer_speed ?? 150) / 100));

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
      shown = false;
      unzoom();
    };
  });

  onDestroy(() => clearTimeout(hideTimer));

  function wake() {
    shown = true;
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => (shown = false), HIDE_MS);
  }

  /** What lies under the pointer; the pointer itself takes no events. */
  function under() {
    return document.elementFromPoint(Math.round(x), Math.round(y));
  }

  function receive(message) {
    switch (message.t) {
      case 'move': {
        x = edge(x + Number(message.dx || 0) * speed, window.innerWidth, 'x');
        y = edge(y + Number(message.dy || 0) * speed, window.innerHeight, 'y');
        wake();
        const field = takesText(under());
        if (field !== over) {
          over = field;
          pad?.send({ t: 'over', field });
        }
        break;
      }
      case 'tap':
        wake();
        tap();
        break;
      case 'text':
        insert(String(message.text ?? ''));
        break;
      case 'key':
        key(String(message.key ?? ''));
        break;
      case 'scroll':
        wake();
        scroll(Number(message.dx || 0), Number(message.dy || 0));
        break;
      case 'zoom':
        wake();
        zoomBy(Number(message.by) || 1);
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
    if (takesText(target)) target.focus();
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

{#if on && shown}
  <div class="pointer" use:outside style:transform={`translate(${x}px, ${y}px)`} aria-hidden="true">
    <svg viewBox="0 0 24 24" width="30" height="30">
      <path d="M3 2 L3 19 L8 14.5 L11.5 22 L14.5 20.6 L11 13.3 L17.5 13.3 Z" />
    </svg>
  </div>
{/if}

<style>
  :global(html.panel-zoomed),
  :global(html.panel-zoomed body) {
    overflow: hidden;
  }
  .pointer {
    position: fixed;
    left: 0;
    top: 0;
    z-index: 1000;
    pointer-events: none;
    will-change: transform;
  }
  .pointer svg {
    display: block;
    fill: #f4f7f9;
    stroke: #0b1218;
    stroke-width: 1.4;
    stroke-linejoin: round;
    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.5));
  }
</style>
