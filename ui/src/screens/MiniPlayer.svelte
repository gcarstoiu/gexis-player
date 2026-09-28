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

  let open = $state(false);
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
  .mini__note {
    font-size: var(--t-meta);
    color: var(--accent-warn);
  }
</style>
