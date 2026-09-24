<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Volume drawer, Phase 4 step 4e (criterion 8, ADR-0034). Ported from the
  "Controls" drawer in design/source/Now Playing.dc.html. The number is the
  slider position; mute restores the level from before it.
-->
<script>
  import { setVolume, setMute, fixedOutput } from '../lib/state.js';
  import LockIcon from '../lib/LockIcon.svelte';
  import VolumeIcon from '../lib/VolumeIcon.svelte';

  let { open, volume, active, onclose, onexternal, onactivity, onsettled } = $props();

  let dragging = $state(false);
  let settling = $state(false);
  let local = $state(0);
  let toast = $state(null);
  let toastTimer;

  const muted = $derived(!!volume?.muted);
  const shown = $derived(dragging || settling ? local : (volume?.percent ?? 0));
  const pct = $derived(muted ? 0 : shown);

  // A level change the panel did not cause - a phone, most often - opens the
  // drawer. Ours are recognised by a short window after each command; a
  // takeover restoring a renderer's remembered level is not a user action.
  const OWN_WINDOW_MS = 1500;
  let ownUntil = 0;
  let activeChangedAt = 0;
  let last = null;
  let lastActive;
  $effect(() => {
    if (active !== lastActive) {
      if (lastActive !== undefined) activeChangedAt = performance.now();
      lastActive = active;
    }
  });
  $effect(() => {
    const current = volume ? `${volume.percent}/${volume.muted}` : null;
    const previous = last;
    last = current;
    if (previous === null || current === previous) return;
    const now = performance.now();
    if (now < ownUntil || dragging || now - activeChangedAt < 3000) return;
    onexternal?.();
  });
  const markOwn = () => (ownUntil = performance.now() + OWN_WINDOW_MS);

  function flash(text) {
    toast = text;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toast = null), 2200);
  }

  // One request at a time; while one is in flight only the latest value waits.
  let inFlight = false;
  let queued = null;
  async function send(percent) {
    if (inFlight) {
      queued = percent;
      return;
    }
    inFlight = true;
    markOwn();
    try {
      await setVolume(percent);
      markOwn();
    } catch (err) {
      flash(`Volume not changed: ${err.message}`);
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
    // **The drawer stops being held open when the finger leaves it**
    // (George, 2026-09-23: "the volume modal is not going away after the
    // 3s"). `onactivity` pins it on pointerdown so a drag is never cut off
    // mid-gesture; without a matching release the pin was permanent, so a
    // drag on the panel's own slider left the drawer up until somebody
    // tapped it away.
    onsettled?.();
  }

  async function toggleMute() {
    const next = !muted;
    markOwn();
    try {
      await setMute(next);
      markOwn();
      flash(next ? 'Muted' : 'Unmuted');
    } catch (err) {
      flash(`Mute not changed: ${err.message}`);
    }
  }
</script>

<div class="scrim" class:is-open={open} role="presentation" onclick={onclose}></div>

<div class="drawer" class:is-open={open} role="presentation"
     onpointerdown={onactivity} onpointerup={onsettled}
     onpointercancel={onsettled} onpointerleave={onsettled}>
  <div class="drawer__title">Controls</div>
  {#if $fixedOutput}
    <!--
      ADR-0046: the drawer still opens, so the answer is where the question
      is asked. Not a disabled slider - the design ruled that out by name.
    -->
    <div class="fixed">
      <LockIcon size={26} />
      <span>Fixed output — level is set downstream. Set it on your amplifier.</span>
    </div>
  {:else}
  <div class="row">
    <button class="mute" class:is-muted={muted} type="button" aria-label={muted ? 'Unmute' : 'Mute'} onclick={toggleMute}>
      <VolumeIcon percent={pct} {muted} />
    </button>

    <div
      class="track"
      role="slider"
      tabindex="-1"
      aria-label="Volume"
      aria-valuemin="0"
      aria-valuemax="100"
      aria-valuenow={pct}
      onpointerdown={down}
      onpointermove={move}
      onpointerup={up}
      onpointercancel={up}
    >
      <div class="rail">
        <div class="fill" class:is-muted={muted} style:width={`${pct}%`}></div>
        <div class="knob" class:is-muted={muted} style:left={`${pct}%`}></div>
      </div>
    </div>

    <span class="readout" class:is-muted={muted}>{muted ? 'Mute' : shown}</span>
  </div>
  {/if}
</div>

<div class="toast" class:is-shown={toast}>
  <span>{toast ?? ''}</span>
</div>

<style>
  .scrim {
    position: absolute;
    inset: 0;
    z-index: 12;
    background: rgba(8, 12, 16, 0.6);
    /* No `backdrop-filter`: with it, this drawer drops 71 % of the
       panel's frames while nothing is even happening, against 9 % without
       (Finding 037). It is also the sheet this device opens most - every
       volume change from a phone raises it, over whatever is on screen. */
    transition: opacity 220ms ease;
    opacity: 0;
    pointer-events: none;
  }
  .scrim.is-open {
    opacity: 1;
    pointer-events: auto;
  }

  .drawer {
    position: absolute;
    left: 50%;
    top: 50%;
    z-index: 13;
    width: 820px;
    background: var(--bg-panel);
    border: 1px solid rgba(126, 214, 188, 0.22);
    border-radius: 28px;
    padding: 34px 40px 36px;
    box-shadow: 0 34px 90px rgba(0, 0, 0, 0.6);
    transition:
      transform 240ms cubic-bezier(0.2, 0.8, 0.2, 1),
      opacity 200ms ease;
    transform: translate(-50%, -50%) scale(0.94);
    opacity: 0;
    pointer-events: none;
  }
  .drawer.is-open {
    transform: translate(-50%, -50%) scale(1);
    opacity: 1;
    pointer-events: auto;
  }
  .drawer__title {
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: rgba(233, 238, 242, 0.6);
    margin-bottom: 22px;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 22px;
  }

  .mute {
    width: 58px;
    height: 58px;
    border-radius: 15px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    background: transparent;
    border: 1px solid transparent;
    color: inherit;
  }
  .mute:active {
    background: rgba(233, 238, 242, 0.2);
  }
  .mute.is-muted {
    background: rgba(224, 167, 88, 0.16);
    border-color: rgba(224, 167, 88, 0.42);
  }

  .track {
    flex: 1;
    height: 64px;
    display: flex;
    align-items: center;
    min-width: 0;
    touch-action: none;
  }
  .rail {
    width: 100%;
    height: 14px;
    border-radius: var(--r-pill);
    background: rgba(233, 238, 242, 0.14);
    position: relative;
  }
  .fill {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    border-radius: var(--r-pill);
    transition: background 160ms ease;
    background: var(--accent-lms);
  }
  .fill.is-muted {
    background: rgba(224, 167, 88, 0.5);
  }
  .knob {
    position: absolute;
    top: 50%;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    transform: translate(-50%, -50%);
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.45);
    background: var(--ink);
  }
  .knob.is-muted {
    background: rgba(233, 238, 242, 0.55);
  }

  .readout {
    font-family: var(--font-mono);
    font-size: 26px;
    font-weight: 600;
    width: 76px;
    text-align: right;
    flex-shrink: 0;
    color: var(--ink);
  }
  .readout.is-muted {
    color: var(--accent-warn);
  }

  .fixed {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 4px 6px 2px;
    color: var(--ink-dim, #9fb0bd);
    font-size: 19px;
    line-height: 1.35;
  }

  .toast {
    position: absolute;
    z-index: 36;
    left: 50%;
    bottom: 132px;
    transform: translateX(-50%) translateY(12px);
    background: rgba(22, 35, 44, 0.97);
    border: 1px solid rgba(126, 214, 188, 0.3);
    border-radius: 14px;
    padding: 16px 26px;
    box-shadow: 0 18px 50px rgba(0, 0, 0, 0.5);
    transition:
      opacity 220ms ease,
      transform 220ms ease;
    opacity: 0;
    pointer-events: none;
    white-space: nowrap;
  }
  .toast.is-shown {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
  .toast span {
    font-size: 18px;
    font-weight: 600;
    color: var(--ink);
  }
</style>
