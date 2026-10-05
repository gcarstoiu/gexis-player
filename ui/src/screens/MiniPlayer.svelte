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
  import { active, metadata, volume, fixedOutput, meters, panel, setVolume, showPeppy, hidePeppy, requestIdle } from '../lib/state.js';
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

  function flush() {
    frame = 0;
    if (pending.dx || pending.dy) pad?.send({ t: 'move', dx: Math.round(pending.dx), dy: Math.round(pending.dy) });
    pending = { dx: 0, dy: 0 };
  }

  function padDown(event) {
    event.currentTarget.setPointerCapture(event.pointerId);
    touchStart = { at: performance.now() };
    last = { x: event.clientX, y: event.clientY };
    travelled = 0;
  }

  function padMove(event) {
    if (!last) return;
    const dx = event.clientX - last.x;
    const dy = event.clientY - last.y;
    last = { x: event.clientX, y: event.clientY };
    travelled += Math.abs(dx) + Math.abs(dy);
    pending = { dx: pending.dx + dx, dy: pending.dy + dy };
    if (!frame) frame = requestAnimationFrame(flush);
  }

  function padUp() {
    if (!touchStart) return;
    const quick = performance.now() - touchStart.at < TAP_MS && travelled < TAP_MOVE;
    touchStart = null;
    last = null;
    if (!quick) return;
    // **The keyboard opens inside this same touch** (ADR-0121 §4): the panel
    // said in advance that the pointer is over a text field.
    if (overField && typeEl) {
      typeEl.value = '';
      typed = '';
      typeEl.focus();
      typing = true;
    }
    pad?.send({ t: 'tap' });
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
  async function toggleIdle() {
    try {
      await requestIdle(!$panel.idle);
    } catch (err) {
      say(`Idle screen: ${err.message}`);
    }
  }
</script>

<div
  class="mini"
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
      onpointercancel={() => { touchStart = null; last = null; }}
    >
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

    {#if $meters}
      <button
        class="mini__toggle"
        class:is-on={$panel.visualiser}
        type="button"
        aria-pressed={$panel.visualiser}
        aria-label="Visualiser on the panel"
        onclick={toggleVisualiser}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 19V11M10 19V5M15 19V9M20 19V13" /></svg>
        {#if open}<span>Visualiser</span>{/if}
      </button>
    {/if}
    <button
      class="mini__toggle"
      class:is-on={$panel.idle}
      type="button"
      aria-pressed={$panel.idle}
      aria-label="Idle screen on the panel"
      onclick={toggleIdle}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 14.5A7.5 7.5 0 0 1 9.5 5 7.5 7.5 0 1 0 19 14.5Z" /></svg>
      {#if open}<span>Idle screen</span>{/if}
    </button>
  </div>

  {#if note}<div class="mini__note" role="status">{note}</div>{/if}
</div>

<style>
  .mini {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 20;
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px 16px calc(12px + env(safe-area-inset-bottom, 0px));
    background: var(--bg-panel);
    border-top: 1px solid var(--ink-line);
    box-shadow: 0 -8px 24px rgba(0, 0, 0, 0.35);
    font-family: var(--font-ui);
    color: var(--ink);
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
  .mini--open .mini__track {
    height: 10px;
    border-radius: 5px;
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
  .mini__toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    height: 40px;
    min-width: 40px;
    padding: 0 9px;
    border-radius: 12px;
    border: 1px solid var(--ink-line);
    background: var(--ink-fill);
    color: var(--ink-quiet);
    font: inherit;
    font-size: var(--t-meta);
    cursor: pointer;
    flex: none;
  }
  .mini__toggle.is-on {
    background: var(--src-accent);
    border-color: transparent;
    color: var(--ink-on-accent);
  }
  .mini__toggle svg {
    width: 20px;
    height: 20px;
    fill: none;
    stroke: currentColor;
    stroke-width: 2.2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .mini--open .mini__row {
    flex-wrap: wrap;
  }
  .mini--open .mini__slider {
    flex-basis: calc(100% - 64px);
  }
  .mini__pad {
    height: 180px;
    border-radius: 16px;
    border: 1px solid rgba(233, 238, 242, 0.14);
    background: rgba(233, 238, 242, 0.05);
    display: flex;
    align-items: flex-end;
    justify-content: center;
    padding-bottom: 10px;
    box-sizing: border-box;
    touch-action: none;
    user-select: none;
    -webkit-user-select: none;
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
