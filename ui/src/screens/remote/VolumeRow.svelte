<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0164: the remote's volume row (design/source/21, *Volume*): a bar that
  a tap or a drag anywhere sets, mute inside it at the left, the level at the
  right, the equaliser's setting named in the middle - a second copy, clipped
  to the fill, reads dark over it - then the EQ button, which opens the EQ
  sheet. Its touch sizes are the design's (ADR-0164 D6). With Fixed volume
  the bar's place says so (C3) and the EQ button stays.
-->
<script>
  import { fixedOutput, setMute, setVolume, volume } from '../../lib/state.js';
  import { equaliser } from '../../lib/equaliser.svelte.js';
  import LockIcon from '../../lib/LockIcon.svelte';
  import { FILLED } from './icons.js';

  let { oneq = () => {}, onsay = () => {} } = $props();

  let dragging = $state(false);
  let settling = $state(false);
  let local = $state(0);
  const shown = $derived(dragging || settling ? local : Math.round($volume?.percent ?? 0));
  const muted = $derived(!!$volume?.muted);

  const eq = $derived($equaliser);
  const eqOn = $derived(!!eq?.on);
  const eqLit = $derived(eqOn && !eq?.dsd);
  const eqName = $derived(!eq ? '' : !eq.on ? 'Off' : eq.dsd ? 'DSD' : eq.sel === 'custom' ? 'Custom' : (eq.name ?? 'Flat'));

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
      onsay(`Volume not changed: ${err.message}`);
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

  function at(target, x) {
    const r = target.getBoundingClientRect();
    local = Math.round(Math.min(1, Math.max(0, (x - r.left) / r.width)) * 100);
    send(local);
  }

  //: The design's: a tap or a drag anywhere sets the level from where the
  //: finger is, and unmutes.
  function down(event) {
    event.currentTarget.setPointerCapture?.(event.pointerId);
    dragging = true;
    settling = true;
    if (muted) setMute(false).catch(() => {});
    at(event.currentTarget, event.clientX);
  }
  function move(event) {
    if (dragging) at(event.currentTarget, event.clientX);
  }
  function up() {
    dragging = false;
    if (!inFlight && queued === null) settling = false;
  }
  function keyed(event) {
    const step = { ArrowRight: 2, ArrowUp: 2, ArrowLeft: -2, ArrowDown: -2 }[event.key];
    if (step === undefined) return;
    event.preventDefault();
    local = Math.min(100, Math.max(0, shown + step));
    settling = true;
    send(local);
  }
  function toggleMute(event) {
    event.stopPropagation();
    setMute(!muted).catch((err) => onsay(`Mute: ${err.message}`));
  }
</script>

<div class="row">
  {#if $fixedOutput}
    <div class="fixed" role="status">
      <LockIcon size={20} />
      <span>Fixed output · the amplifier sets the level</span>
    </div>
  {:else}
    <div
      class="bar"
      role="slider"
      tabindex="0"
      aria-label="Volume"
      aria-valuemin="0"
      aria-valuemax="100"
      aria-valuenow={muted ? 0 : shown}
      onpointerdown={down}
      onpointermove={move}
      onpointerup={up}
      onpointercancel={up}
      onkeydown={keyed}
    >
      <span class="fill" class:is-muted={muted} style:width={`${shown}%`}></span>
      {#if eq}
        <span class="eq" class:is-lit={eqLit}><span class="eq__word">EQ</span><span class="eq__name">{eqName}</span></span>
        {#if !muted}
          <span class="eq eq--dark" style:clip-path={`inset(0 ${100 - shown}% 0 0)`} aria-hidden="true">
            <span class="eq__word">EQ</span><span class="eq__name">{eqName}</span>
          </span>
        {/if}
      {/if}
      <button class="mute" class:is-dark={!muted && shown > 14} type="button" aria-label={muted ? 'Unmute' : 'Mute'}
              aria-pressed={muted} onpointerdown={(e) => e.stopPropagation()} onclick={toggleMute}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d={muted ? FILLED.muted : FILLED.speaker} /></svg>
      </button>
      <span class="level" class:is-dark={!muted && shown > 86}>{muted ? 'Off' : shown}</span>
    </div>
  {/if}
  {#if eq}
    <button class="eqbtn" class:is-on={eqOn} type="button" aria-label="Equaliser" onclick={oneq}>
      <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <path d="M6 4v16M12 4v16M18 4v16" />
        <circle cx="6" cy="14" r="2.6" fill="#16232c" /><circle cx="12" cy="8" r="2.6" fill="#16232c" /><circle cx="18" cy="12" r="2.6" fill="#16232c" />
      </svg>
    </button>
  {/if}
</div>

<style>
  .row {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .bar {
    position: relative;
    flex: 1;
    min-width: 0;
    height: var(--remote-vol-height);
    border-radius: var(--remote-vol-radius);
    background: var(--remote-vol-ground);
    overflow: hidden;
    cursor: pointer;
    touch-action: none;
    outline: none;
  }
  .fill {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    background: #7ed6bc;
  }
  .fill.is-muted {
    opacity: 0.35;
  }
  .eq {
    position: absolute;
    inset: 0;
    padding: 0 52px 0 44px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    white-space: nowrap;
    overflow: hidden;
    pointer-events: none;
    color: rgba(233, 238, 242, 0.72);
  }
  .eq.is-lit {
    color: #7ed6bc;
  }
  .eq--dark {
    color: var(--remote-vol-ink-on-fill);
  }
  .eq__word {
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.14em;
    flex-shrink: 0;
  }
  .eq__name {
    min-width: 0;
    font-size: 13px;
    font-weight: 700;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .mute {
    position: absolute;
    left: 4px;
    top: 2px;
    width: 32px;
    height: 32px;
    border-radius: 10px;
    border: 0;
    padding: 0;
    background: none;
    display: grid;
    place-items: center;
    cursor: pointer;
    color: #e9eef2;
  }
  .mute.is-dark {
    color: var(--remote-vol-ink-on-fill);
  }
  .mute svg {
    width: 24px;
    height: 24px;
    fill: currentColor;
  }
  .level {
    position: absolute;
    right: 16px;
    top: 0;
    bottom: 0;
    display: flex;
    align-items: center;
    font-family: var(--font-mono);
    font-size: 16px;
    font-weight: 600;
    pointer-events: none;
    color: #e9eef2;
  }
  .level.is-dark {
    color: var(--remote-vol-ink-on-fill);
  }
  .fixed {
    flex: 1;
    min-width: 0;
    height: var(--remote-vol-height);
    border-radius: var(--remote-vol-radius);
    background: var(--remote-vol-ground);
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 12px;
    box-sizing: border-box;
    font-size: 13px;
    color: rgba(233, 238, 242, 0.72);
    white-space: nowrap;
    overflow: hidden;
  }
  .fixed span {
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .eqbtn {
    width: var(--remote-button);
    height: var(--remote-button);
    border-radius: var(--remote-button-radius);
    display: grid;
    place-items: center;
    box-sizing: border-box;
    flex-shrink: 0;
    cursor: pointer;
    padding: 0;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.14);
    color: rgba(233, 238, 242, 0.82);
  }
  .eqbtn.is-on {
    background: rgba(126, 214, 188, 0.12);
    border-color: rgba(126, 214, 188, 0.45);
    color: #7ed6bc;
  }
  .eqbtn svg {
    width: 22px;
    height: 22px;
  }
</style>
