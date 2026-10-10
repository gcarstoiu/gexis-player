<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0101: the phone's mini player, pinned to the bottom of Settings. What
  is playing and from where, the volume, and two toggles that act on the
  panel - its visualiser and its idle screen - and say what it shows.

  George, 2026-09-28: "Option C - mini player. Only for phone." The volume
  is the panel's own slider (POST /volume), which is what Plexamp needs now
  that its app keeps a volume of its own.
-->
<script>
  import { active, metadata, volume, fixedOutput, meters, panel, setVolume, showPeppy, hidePeppy, requestIdle, goTo } from '../lib/state.js';
  import { fixedPending } from '../lib/settings.js';
  import SourceMark from '../lib/SourceMark.svelte';
  import { settingValues } from '../lib/settings.js';
  import { openTouchpad } from '../lib/touchpad.js';

  let open = $state(false);

  // ── ADR-0121: the touchpad and keyboard for the panel ────────────────
  //: Relative, as a laptop's touchpad: moves are sent as distances, and the
  //: panel scales them by Pointer speed. Open only while the sheet is.
  const TAP_MS = 300;
  const TAP_MOVE = 10;
  const touchpad = $derived(open && $settingValues.phone_touchpad !== false);
  let pad = null;
  let overField = $state(false);
  let typing = $state(false);
  let typeEl = $state(null);
  let typed = '';
  let touchStart = null;
  let last = null;
  let travelled = 0;
  let pending = { dx: 0, dy: 0 };
  let frame = 0;

  $effect(() => {
    if (!touchpad) return;
    pad = openTouchpad((message) => {
      if (message.t === 'over') overField = !!message.field;
      if (message.t === 'focus' && !message.field) stopTyping();
    });
    return () => {
      pad?.close();
      pad = null;
      overField = false;
      stopTyping();
    };
  });

  function stopTyping() {
    typing = false;
    typed = '';
    if (typeEl) {
      typeEl.value = '';
      typeEl.blur();
    }
  }

  /** Whole pixels go; **the fraction stays for the next frame**. A finger
   *  starts slowly - under a pixel a frame - and rounding each frame's share
   *  away held the pointer still and then let it jump (George, 2026-10-05:
   *  "choppy at the beginning"). The same for a two-finger scroll. */
  function flush() {
    frame = 0;
    const dx = Math.trunc(pending.dx);
    const dy = Math.trunc(pending.dy);
    if (dx || dy) pad?.send({ t: 'move', dx, dy });
    pending = { dx: pending.dx - dx, dy: pending.dy - dy };
    const sx = Math.trunc(scrolled.dx);
    const sy = Math.trunc(scrolled.dy);
    if (sx || sy) pad?.send({ t: 'scroll', dx: sx, dy: sy });
    scrolled = { dx: scrolled.dx - sx, dy: scrolled.dy - sy };
    if (Math.abs(zoomed - 1) > 0.002) {
      pad?.send({ t: 'zoom', by: Math.round(zoomed * 1000) / 1000 });
      zoomed = 1;
    }
  }

  function soon() {
    if (!frame) frame = requestAnimationFrame(flush);
  }

  // ── Two fingers (ADR-0121 §2, amended 2026-10-05) ─────────────────────
  //: How far two fingers go together, or apart, before the gesture is
  //: decided - a scroll or a zoom, which it then stays until they lift.
  const DECIDE = 12;
  //: How far in from the right and bottom edges a finger scrolls.
  const EDGE = 40;
  let edge = null;
  const fingers = new Map();
  //: 'one' (moving and tapping), 'two' (undecided), 'scroll', 'zoom', or
  //: 'done' - after two fingers, nothing until every finger has lifted.
  let gesture = null;
  let middle = null;
  let spread = 0;
  let firstMiddle = null;
  let firstSpread = 0;
  let scrolled = { dx: 0, dy: 0 };
  let sideways = false;
  let zoomed = 1;

  function midpoint() {
    const [a, b] = [...fingers.values()];
    return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  }
  function apart() {
    const [a, b] = [...fingers.values()];
    return Math.hypot(a.x - b.x, a.y - b.y);
  }

  function padDown(event) {
    event.currentTarget.setPointerCapture(event.pointerId);
    fingers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (fingers.size === 1 && gesture === null) {
      gesture = 'one';
      touchStart = { at: performance.now() };
      last = { x: event.clientX, y: event.clientY };
      travelled = 0;
      // **The scroll lines** (George, 2026-10-05): one finger along the
      // right edge scrolls up and down, along the bottom sideways - the
      // content following the finger, as two fingers do.
      const r = event.currentTarget.getBoundingClientRect();
      edge = event.clientX > r.right - EDGE ? 'y' : event.clientY > r.bottom - EDGE ? 'x' : null;
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
      if (edge === 'y') scrolled = { dx: 0, dy: scrolled.dy + dy };
      else if (edge === 'x') scrolled = { dx: scrolled.dx + dx, dy: 0 };
      else pending = { dx: pending.dx + dx, dy: pending.dy + dy };
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
        // One direction per scroll: a list goes up and down, a row sideways,
        // and a scroll a little off straight must not move both.
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
    if (was !== 'one' || !touchStart) return;
    const quick = performance.now() - touchStart.at < TAP_MS && travelled < TAP_MOVE;
    touchStart = null;
    if (!quick) return;
    // **The keyboard opens inside this same touch** (ADR-0121 §4): the panel
    // said in advance that the pointer is over a text field. The touch's own
    // mousedown, a moment later, would take the focus back to the page (seen
    // end to end, 2026-10-05) - the pad refuses it, below.
    if (overField && typeEl) {
      typeEl.value = '';
      typed = '';
      typeEl.focus();
      typing = true;
    }
    pad?.send({ t: 'tap' });
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

  /** What changed in the hidden field, sent as text and backspaces - so a
   *  keyboard's suggestions and corrections arrive as the panel needs them. */
  function typedInput() {
    const now = typeEl.value;
    let same = 0;
    while (same < typed.length && same < now.length && typed[same] === now[same]) same += 1;
    for (let i = same; i < typed.length; i += 1) pad?.send({ t: 'key', key: 'Backspace' });
    if (now.length > same) pad?.send({ t: 'text', text: now.slice(same) });
    typed = now;
  }

  function typedKey(event) {
    if (event.key === 'Enter') {
      event.preventDefault();
      pad?.send({ t: 'key', key: 'Enter' });
    }
  }
  let dragging = $state(false);
  let settling = $state(false);
  let local = $state(0);
  let note = $state(null);
  let noteTimer;

  const shown = $derived(dragging || settling ? local : ($volume?.percent ?? 0));
  const pct = $derived($volume?.muted ? 0 : shown);
  const title = $derived($metadata?.title ?? null);
  const artist = $derived($metadata?.artist ?? null);

  function say(text) {
    note = text;
    clearTimeout(noteTimer);
    noteTimer = setTimeout(() => (note = null), 2500);
  }

  // One request at a time; while one is in flight only the latest value
  // waits - the volume drawer's rule, for the same reason.
  let inFlight = false;
  let queued = null;
  async function send(percent) {
    if (inFlight) {
      queued = percent;
      return;
    }
    inFlight = true;
    try {
      await setVolume(percent);
    } catch (err) {
      say(`Volume not changed: ${err.message}`);
    } finally {
      inFlight = false;
    }
    if (queued !== null) {
      const next = queued;
      queued = null;
      await send(next);
    } else if (!dragging) {
      settling = false;
    }
  }

  function fromPointer(event) {
    const r = event.currentTarget.getBoundingClientRect();
    local = Math.round(Math.min(1, Math.max(0, (event.clientX - r.left) / r.width)) * 100);
    send(local);
  }
  function down(event) {
    dragging = true;
    settling = true;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    fromPointer(event);
  }
  function move(event) {
    if (dragging) fromPointer(event);
  }
  function up() {
    dragging = false;
    if (!inFlight && queued === null) settling = false;
  }
  function key(event) {
    const step = { ArrowRight: 2, ArrowUp: 2, ArrowLeft: -2, ArrowDown: -2 }[event.key];
    if (step === undefined) return;
    event.preventDefault();
    local = Math.min(100, Math.max(0, shown + step));
    settling = true;
    send(local);
  }

  async function toggleVisualiser() {
    try {
      await ($panel.visualiser ? hidePeppy() : showPeppy());
    } catch (err) {
      say(`Visualiser: ${err.message}`);
    }
  }
  //: ADR-0101 as amended 2026-10-05: where the panel goes. Now playing and
  //: Lyrics need something playing (N2); Home is always there.
  async function go(to, what) {
    try {
      await goTo(to);
    } catch (err) {
      say(`${what}: ${err.message}`);
    }
  }

  async function toggleIdle() {
    try {
      await requestIdle(!$panel.idle);
    } catch (err) {
      say(`Idle screen: ${err.message}`);
    }
  }

  //: **The page keeps clear of the closed sheet** (George, 2026-10-06: the
  //: last setting must be fully visible above it). Its height, measured
  //: while closed, is what Settings leaves free at its foot - App.svelte's
  //: `.remote--mini` - rather than a number that went stale when the sheet
  //: gained its row of icons.
  function closedHeight(node, isOpen) {
    let open = isOpen;
    const put = () => {
      if (!open) document.documentElement.style.setProperty('--mini-closed-h', `${node.offsetHeight}px`);
    };
    const watch = new ResizeObserver(put);
    watch.observe(node);
    put();
    return {
      update(next) {
        open = next;
        put();
      },
      destroy() {
        watch.disconnect();
        document.documentElement.style.removeProperty('--mini-closed-h');
      },
    };
  }
</script>

{#if open}
  <!-- Open, the sheet is the phone's whole attention: a touch outside it
       closes it and reaches nothing under it (George, 2026-10-05: no
       setting changed by a thumb that missed the touchpad). -->
  <div class="mini__scrim" role="presentation" onclick={() => (open = false)}></div>
{/if}

<div
  class="mini"
  use:closedHeight={open}
  class:mini--open={open}
  style:--src-accent={`var(--accent-${$active}, var(--accent-lms))`}
>
  <button class="mini__now" type="button" aria-expanded={open} onclick={() => (open = !open)}>
    {#if $active}
      <SourceMark source={$active} size={open ? 22 : 16} color="var(--src-accent)" />
    {/if}
    <span class="mini__text">
      <span class="mini__title">{title ?? ($active ? 'Playing' : 'Nothing playing')}</span>
      {#if open && artist}<span class="mini__artist">{artist}</span>{/if}
    </span>
    <span class="mini__chev" class:is-open={open}></span>
  </button>

  {#if touchpad}
    <!-- ADR-0121: a touchpad for the panel, above the slider. -->
    <div
      class="mini__pad"
      role="application"
      aria-label="Touchpad for the player's screen"
      onpointerdown={padDown}
      onpointermove={padMove}
      onpointerup={padUp}
      onpointercancel={padCancel}
      onmousedown={(event) => event.preventDefault()}
    >
      <span class="mini__pad-line mini__pad-line--y" aria-hidden="true"></span>
      <span class="mini__pad-line mini__pad-line--x" aria-hidden="true"></span>
      <span class="mini__pad-hint">{typing ? 'Typing on the player' : overField ? 'Tap to type' : 'Touchpad'}</span>
    </div>
    <input
      class="mini__type"
      bind:this={typeEl}
      type="text"
      autocomplete="off"
      autocorrect="off"
      spellcheck="false"
      aria-label="Text for the player's screen"
      oninput={typedInput}
      onkeydown={typedKey}
      onblur={() => (typing = false)}
    />
  {/if}

  <!-- ADR-0101 as amended 2026-10-06 (George): **every toggle in one row,
       icons only, open or not** - opening the sheet adds the touchpad and
       nothing else. The row stands between the touchpad and the volume, so
       a sideways stroke that overshoots the pad lands on buttons that want
       a tap, not on the slider. Now playing is a toggle: up on the panel it
       minimises to the strip (ADR-0122); down, it brings it up. -->
  <div class="mini__icons">
    <button class="mini__icon" type="button" aria-label="Home on the panel" onclick={() => go('home', 'Home')}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 11.5 12 5l8 6.5M6.5 10v9h11v-9" /></svg>
    </button>
    <button
      class="mini__icon"
      class:is-on={!!$active && $panel.now}
      type="button"
      disabled={!$active}
      aria-pressed={!!$active && !!$panel.now}
      aria-label={$panel.now ? 'Minimise Now Playing' : 'Now Playing on the panel'}
      onclick={() => go($panel.now ? 'minimise' : 'now', 'Now playing')}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8" /><path d="M10.5 9v6l4.5-3z" /></svg>
    </button>
    <button
      class="mini__icon"
      class:is-on={!!$active && $panel.lyrics}
      type="button"
      disabled={!$active}
      aria-pressed={!!$active && !!$panel.lyrics}
      aria-label="Lyrics on the panel"
      onclick={() => go($panel.lyrics ? 'track' : 'lyrics', 'Lyrics')}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 7h14M5 12h9M5 17h11" /></svg>
    </button>
    {#if $meters}
      <button
        class="mini__icon"
        class:is-on={$panel.visualiser}
        type="button"
        aria-pressed={$panel.visualiser}
        aria-label="Visualiser on the panel"
        onclick={toggleVisualiser}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 19V11M10 19V5M15 19V9M20 19V13" /></svg>
      </button>
    {/if}
    <button
      class="mini__icon"
      class:is-on={$panel.idle}
      type="button"
      aria-pressed={$panel.idle}
      aria-label="Idle screen on the panel"
      onclick={toggleIdle}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 14.5A7.5 7.5 0 0 1 9.5 5 7.5 7.5 0 1 0 19 14.5Z" /></svg>
    </button>
  </div>

  <!-- ADR-0046 as amended: a Volume change waiting for a pause says so. -->
  {#if $fixedPending}
    <div class="mini__pending">{$fixedPending === 'on' ? "Fixed output starts at the next pause or stop" : "Fixed output ends at the next pause or stop"}.</div>
  {/if}
  <div class="mini__row">
    {#if $fixedOutput}
      <span class="mini__fixed">Fixed output · the amplifier sets the level</span>
    {:else}
      <div
        class="mini__slider"
        role="slider"
        tabindex="0"
        aria-label="Volume"
        aria-valuemin="0"
        aria-valuemax="100"
        aria-valuenow={pct}
        onpointerdown={down}
        onpointermove={move}
        onpointerup={up}
        onpointercancel={up}
        onkeydown={key}
      >
        <span class="mini__track"><span class="mini__fill" style:width={`${pct}%`}></span></span>
        <span class="mini__knob" style:left={`${pct}%`}></span>
      </div>
      <span class="mini__pct">{$volume?.muted ? 'Muted' : `${shown}%`}</span>
    {/if}
  </div>

  {#if note}<div class="mini__note" role="status">{note}</div>{/if}
</div>

<style>
  .mini__pending {
    font-size: 14px;
    line-height: 1.35;
    color: var(--accent-warn);
    padding: 0 2px 6px;
  }
  .mini {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 20;
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 16px 16px calc(12px + env(safe-area-inset-bottom, 0px));
    background: var(--bg-panel);
    /* **A sheet over Settings, not the end of it** (George, 2026-10-06:
       "more shadow or some sort of separation between the closed sheet and
       the settings"): rounded at the top, a lit edge, a deeper shadow, and a
       handle. */
    border-top: 1px solid rgba(233, 238, 242, 0.16);
    border-radius: 20px 20px 0 0;
    box-shadow: 0 -10px 32px rgba(0, 0, 0, 0.6), 0 -1px 0 rgba(0, 0, 0, 0.4);
    font-family: var(--font-ui);
    color: var(--ink);
  }
  .mini::before {
    content: '';
    position: absolute;
    top: 6px;
    left: 50%;
    width: 36px;
    height: 4px;
    margin-left: -18px;
    border-radius: 2px;
    background: rgba(233, 238, 242, 0.24);
  }
  .mini__now {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
    padding: 0;
    background: none;
    border: 0;
    color: inherit;
    font: inherit;
    text-align: left;
    cursor: pointer;
  }
  .mini__text {
    display: flex;
    flex-direction: column;
    min-width: 0;
    flex: 1;
  }
  .mini__title {
    font-size: var(--t-body-sm);
    font-weight: 700;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .mini__artist {
    font-size: var(--t-meta);
    color: var(--ink-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .mini__chev {
    width: 10px;
    height: 10px;
    border-left: 2px solid var(--ink-quiet);
    border-top: 2px solid var(--ink-quiet);
    transform: rotate(45deg) translate(2px, 2px);
    flex: none;
  }
  .mini__chev.is-open {
    transform: rotate(225deg) translate(2px, 2px);
  }
  .mini__row {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .mini__slider {
    position: relative;
    flex: 1;
    height: 32px;
    display: flex;
    align-items: center;
    touch-action: none;
    cursor: pointer;
  }
  .mini__track {
    width: 100%;
    height: 6px;
    border-radius: 3px;
    background: var(--ink-fill-press);
    overflow: hidden;
  }
  .mini__fill {
    display: block;
    height: 100%;
    background: var(--src-accent);
  }
  .mini__knob {
    position: absolute;
    top: 50%;
    width: 20px;
    height: 20px;
    margin: -10px 0 0 -10px;
    border-radius: 50%;
    background: var(--ink);
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);
  }
  .mini__pct {
    width: 52px;
    font-family: var(--font-mono);
    font-size: var(--t-label);
    color: var(--ink-muted);
    text-align: right;
    flex: none;
  }
  .mini__fixed {
    flex: 1;
    font-size: var(--t-meta);
    color: var(--ink-quiet);
  }
  /* One row of equal icon buttons, the width of the sheet. */
  .mini__icons {
    display: flex;
    gap: 8px;
  }
  .mini__icon {
    flex: 1;
    height: 44px;
    border-radius: 12px;
    border: 1px solid var(--ink-line);
    background: var(--ink-fill);
    color: var(--ink-quiet);
    display: grid;
    place-items: center;
    padding: 0;
    cursor: pointer;
  }
  .mini__icon:disabled {
    opacity: 0.38;
    cursor: default;
  }
  .mini__icon.is-on {
    background: var(--src-accent);
    border-color: transparent;
    color: var(--ink-on-accent);
  }
  .mini__icon svg {
    width: 22px;
    height: 22px;
    fill: none;
    stroke: currentColor;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .mini__icons + .mini__row {
    margin-top: 4px;
  }
  .mini__scrim {
    position: fixed;
    inset: 0;
    z-index: 19;
    background: rgba(0, 0, 0, 0.45);
    touch-action: none;
  }
  /* Half the phone's height and reaching up from the slider, so a thumb
     moving up has room before the edge (George, 2026-10-05: 180 px was
     not enough). */
  .mini__pad {
    height: clamp(220px, 50dvh, 520px);
    border-radius: 16px;
    border: 1px solid rgba(233, 238, 242, 0.14);
    background: rgba(233, 238, 242, 0.05);
    display: flex;
    align-items: flex-end;
    justify-content: center;
    padding-bottom: 32px;
    box-sizing: border-box;
    touch-action: none;
    user-select: none;
    -webkit-user-select: none;
  }
  .mini__pad {
    position: relative;
  }
  /* The scroll lines: drawn thin, answering a finger anywhere within 40 px
     of the edge. */
  .mini__pad-line {
    position: absolute;
    border-radius: 2px;
    background: rgba(233, 238, 242, 0.22);
    pointer-events: none;
  }
  .mini__pad-line--y {
    right: 18px;
    top: 18px;
    bottom: 40px;
    width: 3px;
  }
  .mini__pad-line--x {
    left: 18px;
    right: 40px;
    bottom: 18px;
    height: 3px;
  }
  .mini__pad-hint {
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--ink-muted);
  }
  /* Focusable, so the phone's keyboard opens for it, and out of sight. */
  .mini__type {
    position: absolute;
    left: 0;
    bottom: 0;
    width: 1px;
    height: 1px;
    opacity: 0;
    border: 0;
    padding: 0;
    font-size: 16px;
  }
  .mini__note {
    font-size: var(--t-meta);
    color: var(--accent-warn);
  }
</style>
