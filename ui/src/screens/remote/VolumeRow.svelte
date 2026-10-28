<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0164: the remote's volume row (design/source/21, *Volume*): a bar that
  a tap or a drag anywhere sets, mute inside it at the left, the level at the
  right, the equaliser's setting named in the middle - a second copy, clipped
  to the fill, reads dark over it - then the EQ button, which opens the EQ
  sheet. Its touch sizes are the design's (ADR-0164 D6). With Fixed volume
  the bar becomes the panel's locked row - mute, where the output has a
  control to silence (ADR-0165, C3), the padlock, *Fixed output* and the EQ
  name - and the EQ button stays.

  ADR-0166, design/source/22 (*Phone: group volume*): grouped, the bar is the
  group's *All* slider - *GROUP* and the count in its middle, its mute the
  group's - and the group button left of EQ opens the group volume sheet.
-->
<script>
  import { onDestroy } from 'svelte';
  import { fixedMute, fixedOutput, setMute, setVolume, volume } from '../../lib/state.js';
  import { equaliser } from '../../lib/equaliser.svelte.js';
  import { FILLED } from './icons.js';
  import GroupGlyph from '../../lib/GroupGlyph.svelte';
  import { LevelSender, dragStart, group, groupLevel, setGroupMute } from '../../lib/group.svelte.js';

  let { oneq = () => {}, ongroup = () => {}, onsay = () => {} } = $props();

  const g = $derived($group);
  const groupFixed = $derived(!!g && !g.members.some((m) => m.reachable && !m.fixed && m.volume != null));
  const groupSender = new LevelSender(groupLevel, (err) => onsay(`Volume not changed: ${err.message}`));
  let groupFrom = null;

  let dragging = $state(false);
  let settling = $state(false);
  let local = $state(0);
  const shown = $derived(dragging || settling ? local
    : g ? (groupFixed ? 0 : (g.level ?? 0)) : Math.round($volume?.percent ?? 0));
  const muted = $derived(g ? !!g.muted && !dragging : $fixedOutput ? $fixedMute === true : !!$volume?.muted);

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
    } else if (!dragging && !stepHeld) {
      settling = false;
    }
  }

  function at(target, x) {
    const r = target.getBoundingClientRect();
    local = Math.round(Math.min(1, Math.max(0, (x - r.left) / r.width)) * 100);
    if (g) groupSender.send(local, groupFrom);
    else send(local);
  }

  //: The design's: a tap or a drag anywhere sets the level from where the
  //: finger is, and unmutes.
  function down(event) {
    if (g && groupFixed) return;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    dragging = true;
    settling = true;
    // Grouped, the members' levels as the drag begins, so it keeps their
    // balance; the core unmutes them as it moves them.
    if (g) groupFrom = dragStart(g);
    else if (muted) setMute(false).catch(() => {});
    at(event.currentTarget, event.clientX);
  }
  function move(event) {
    if (dragging) at(event.currentTarget, event.clientX);
  }
  //: Grouped, the core's answer arrives through every member's /state: the
  //: bar keeps the finger's level for SETTLE_MS, as the panel's does, or it
  //: jumps back to the old mean first.
  const SETTLE_MS = 1500;
  let settle = null;
  //: Alone too, after a step (a key, a scroll), which starts from the level
  //: shown: a scroll sends steps faster than the player answers.
  let stepHeld = false;
  function settleLater() {
    clearTimeout(settle);
    settle = setTimeout(() => {
      stepHeld = false;
      if (!dragging && !inFlight && queued === null) settling = false;
    }, SETTLE_MS);
  }
  onDestroy(() => clearTimeout(settle));
  function up() {
    dragging = false;
    if (g) {
      groupFrom = null;
      settleLater();
      return;
    }
    if (!inFlight && queued === null) settling = false;
  }
  function keyed(event) {
    const step = { ArrowRight: 2, ArrowUp: 2, ArrowLeft: -2, ArrowDown: -2 }[event.key];
    if (step === undefined) return;
    event.preventDefault();
    stepBy(step);
  }
  //: A key, or a scroll along the bar (lib/scrollSlide.js): `delta` per cent
  //: from the level shown.
  function stepBy(delta) {
    if (g && groupFixed) return;
    local = Math.min(100, Math.max(0, shown + delta));
    if (g) {
      groupSender.send(local, dragStart(g));
      settling = true;
      settleLater();
      return;
    }
    settling = true;
    stepHeld = true;
    settleLater();
    send(local);
  }
  function toggleMute(event) {
    event.stopPropagation();
    (g ? setGroupMute(!g.muted) : setMute(!muted)).catch((err) => onsay(`Mute: ${err.message}`));
  }
</script>

{#snippet caption(dark)}
  {#if g}
    <span class="eq" class:eq--dark={dark} class:is-group={!dark} aria-hidden={dark}>
      <span class="eq__word">GROUP</span><span class="eq__name">{g.members.length}</span>
    </span>
  {:else if eq}
    <span class="eq" class:eq--dark={dark} class:is-lit={!dark && eqLit} aria-hidden={dark}>
      <span class="eq__word">EQ</span><span class="eq__name">{eqName}</span>
    </span>
  {/if}
{/snippet}

<div class="row">
  {#if $fixedOutput && !g}
    <div class="fixed" class:has-mute={$fixedMute !== null} role="group" aria-label="Fixed output">
      {#if $fixedMute !== null}
        <button class="mute mute--fixed" type="button" aria-label={muted ? 'Unmute' : 'Mute'} aria-pressed={muted} onclick={toggleMute}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d={muted ? FILLED.muted : FILLED.speaker} /></svg>
        </button>
      {/if}
      <span class="lock" aria-hidden="true"><span class="lock__shackle"></span><span class="lock__body"></span></span>
      <span class="fixed__text">Fixed output</span>
      {#if eq}
        <span class="eq-fixed" class:is-lit={eqLit}><span class="eq__word">EQ</span><span class="eq-fixed__name">{eqName}</span></span>
      {/if}
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
      data-step="2"
      ondpadstep={(event) => stepBy(event.detail.step * 2)}
      onpointerdown={down}
      onpointermove={move}
      onpointerup={up}
      onpointercancel={up}
      onkeydown={keyed}
    >
      <span class="fill" class:is-muted={muted} style:width={`${shown}%`}></span>
      {@render caption(false)}
      {#if !muted && (g || eq)}
        <span class="clip" style:clip-path={`inset(0 ${100 - shown}% 0 0)`}>{@render caption(true)}</span>
      {/if}
      <button class="mute" class:is-dark={!muted && shown > 14} type="button" aria-label={muted ? 'Unmute' : 'Mute'}
              aria-pressed={muted} onpointerdown={(e) => e.stopPropagation()} onclick={toggleMute}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d={muted ? FILLED.muted : FILLED.speaker} /></svg>
      </button>
      <span class="level" class:is-dark={!muted && shown > 86}>{g && groupFixed ? 'Fixed' : muted ? 'Off' : shown}</span>
    </div>
  {/if}
  {#if g}
    <button class="groupbtn" type="button" aria-label="Group volume" onclick={ongroup}>
      <GroupGlyph size={22} />
    </button>
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
  .eq.is-group {
    color: #e9eef2;
  }
  .clip {
    position: absolute;
    inset: 0;
    pointer-events: none;
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
  /* The panel's locked row (design, *Fixed volume*). */
  .fixed {
    position: relative;
    flex: 1;
    min-width: 0;
    height: var(--remote-vol-height);
    border-radius: var(--remote-vol-radius);
    background: var(--remote-fixed-ground);
    border: 1px solid var(--remote-fixed-line);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 0 15px;
  }
  .fixed.has-mute {
    padding-left: 44px;
  }
  .mute--fixed {
    left: 3px;
    top: 1px;
  }
  .lock {
    position: relative;
    width: 14px;
    height: 16px;
    flex-shrink: 0;
    display: block;
  }
  .lock__shackle {
    position: absolute;
    left: 2px;
    top: 0;
    width: 10px;
    height: 8px;
    border: 2px solid rgba(233, 238, 242, 0.7);
    border-bottom: none;
    border-radius: 5px 5px 0 0;
    box-sizing: border-box;
    display: block;
  }
  .lock__body {
    position: absolute;
    left: 0;
    bottom: 0;
    width: 14px;
    height: 9px;
    border-radius: 2.5px;
    background: rgba(233, 238, 242, 0.7);
    display: block;
  }
  .fixed__text {
    flex: 1;
    min-width: 0;
    font-size: 14px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .eq-fixed {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
    white-space: nowrap;
    color: rgba(233, 238, 242, 0.72);
  }
  .eq-fixed.is-lit {
    color: #7ed6bc;
  }
  .eq-fixed__name {
    font-size: 13px;
    font-weight: 700;
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
  .groupbtn {
    width: var(--remote-button);
    height: var(--remote-button);
    border-radius: var(--remote-button-radius);
    display: grid;
    place-items: center;
    box-sizing: border-box;
    flex-shrink: 0;
    cursor: pointer;
    padding: 0;
    background: var(--group-on-ground);
    border: 1px solid var(--group-on-line);
    color: var(--group-ink);
  }
  .groupbtn:active {
    transform: scale(0.97);
  }
</style>
