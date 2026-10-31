<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Volume drawer, Phase 4 step 4e (criterion 8, ADR-0034). Ported from the
  "Controls" drawer in design/source/Now Playing.dc.html. The number is the
  slider position; mute restores the level from before it.
-->
<script>
  import { fixedMute, fixedOutput } from '../lib/state.js';
  import { VolumeControl } from '../lib/volumeControl.svelte.js';
  import LockIcon from '../lib/LockIcon.svelte';
  import VolumeIcon from '../lib/VolumeIcon.svelte';
  import EqQuick from './eq/EqQuick.svelte';
  import GroupGlyph from '../lib/GroupGlyph.svelte';
  import { group } from '../lib/group.svelte.js';
  import PanelGroupVolume from './group/PanelGroupVolume.svelte';
  import PanelAddPlayers from './group/PanelAddPlayers.svelte';
  import PanelUndoConfirm from './group/PanelUndoConfirm.svelte';

  //: `armsAt`: before this (performance.now()), a drawer that opened by
  //: itself takes no touch on its level or mute (App.svelte, VOLUME_ARM_MS).
  let { open, armsAt = 0, volume, active, onclose, onexternal, onactivity, onsettled, onequaliser = null } = $props();

  //: The level, dragging, mute and the changes from elsewhere: one copy,
  //: shared with the bar's tray (lib/volumeControl.svelte.js).
  const vol = new VolumeControl({
    volume: () => volume,
    active: () => active,
    onexternal: () => onexternal,
    onsettled: () => onsettled,
    fixedMute: () => $fixedMute,
  });
  const muted = $derived(vol.muted);
  const shown = $derived(vol.shown);
  const pct = $derived(vol.pct);
  const toast = $derived(vol.toast);
  const armed = () => performance.now() >= armsAt;
  const down = (event) => armed() && vol.down(event, event.currentTarget);
  const move = (event) => vol.move(event, event.currentTarget);
  const up = () => vol.up();
  const toggleMute = () => armed() && vol.toggleMute();
  //: Left and Right on the slider (ADR-0161), as the phone's touchpad steps.
  const DPAD_STEP = 2;

  // -- ADR-0166, design/source/22 (2a): the group, in the drawer ----------------
  //: The other players on the network, asked each time the drawer opens
  //: (`/players`, kept warm by the core): the *Other players* row is offered
  //: only where there is one.
  let others = $state([]);
  let selfName = $state('');
  let selfId = $state(null);
  async function loadPlayers() {
    try {
      const response = await fetch('/players');
      if (!response.ok) return;
      const body = await response.json();
      others = Array.isArray(body.others) ? body.others : [];
      selfName = body.self?.name ?? '';
      selfId = body.self?.id ?? null;
    } catch {
      // No network answer: the row waits for the next opening.
    }
  }
  //: `add`: the card turned to *Add players*; `confirming`: *Undo the group?*.
  let page = $state('main');
  let confirming = $state(false);
  $effect(() => {
    if (open) {
      loadPlayers();
    } else {
      page = 'main';
      confirming = false;
    }
  });
  const g = $derived($group);
  //: Whose music a player that joins will play: the leader's, or this one's.
  const leaderName = $derived(g?.members.find((m) => m.leads)?.name ?? selfName ?? 'this player');
  const flash = (text) => vol.flash(text);
</script>

<div class="scrim" class:is-open={open} role="presentation" onclick={onclose}></div>

<div class="drawer" class:is-open={open && page === 'main'} class:is-grouped={!!g} role="presentation" data-dpad-layer
     ondpadback={(event) => { event.preventDefault(); onclose?.(); }}
     onpointerdown={onactivity} onpointerup={onsettled}
     onpointercancel={onsettled} onpointerleave={onsettled}
     onpointerenter={(event) => event.pointerType === 'mouse' && onactivity?.(event)}>
  <div class="drawer__title">Controls</div>
  {#if g}
    <!-- ADR-0166 D6: grouped, the volume is the group's. -->
    <PanelGroupVolume {g} onadd={() => (page = 'add')} onundo={() => (confirming = true)} onflash={flash} />
  {:else if $fixedOutput}
    <!--
      ADR-0046: the drawer still opens, so the answer is where the question
      is asked. Not a disabled slider - the design ruled that out by name.
    -->
    <div class="fixed">
      <!-- ADR-0165: mute stays where the output has a control to silence. -->
      {#if $fixedMute !== null}
        <button class="mute" class:is-muted={muted} type="button" aria-label={muted ? 'Unmute' : 'Mute'} onclick={toggleMute}>
          <VolumeIcon percent={100} {muted} />
        </button>
      {/if}
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
      data-dpad-main
      data-step={DPAD_STEP}
      ondpadstep={(event) => vol.step(event.detail.step * DPAD_STEP)}
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
  {#if !g && others.length}
    <!-- ADR-0166 (2a-1): other players to join to this one. -->
    <div class="rule"></div>
    <div class="players">
      <GroupGlyph size={26} ink="rgba(233,238,242,0.82)" />
      <div class="players__text">
        <div class="players__title">Other players</div>
        <div class="players__sub">Join players to this one to play the same music in sync.</div>
      </div>
      <button class="add" type="button" onclick={() => (page = 'add')}><span class="add__plus">+</span>Add players</button>
    </div>
  {/if}
  <!-- ADR-0162 (design/source/20, Q01-Q05): the equaliser's quick change. -->
  <div class="eq">
    <EqQuick host="drawer" onedit={() => { onclose?.(); onequaliser?.(); }} />
  </div>
</div>

<PanelAddPlayers open={open && page === 'add'} {g} {others} {selfId} leader={leaderName}
                 onback={() => (page = 'main')} onflash={flash} onjoined={loadPlayers} />
<PanelUndoConfirm open={open && confirming && !!g} {g} oncancel={() => (confirming = false)}
                  ondone={() => (confirming = false)} onflash={flash} />

<div class="toast" class:is-shown={toast}>
  <span>{toast ?? ''}</span>
</div>

<style>
  .pending {
    margin: -4px 0 12px;
    font-size: 15px;
    line-height: 1.35;
    color: var(--accent-warn);
  }
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
  /* ADR-0166: grouped, the drawer holds the group's rows and still fits the
     shortest panel: where it does not, the card itself scrolls (its radius
     kept), the equaliser below the fold. Nothing in it gives way. */
  .drawer.is-grouped {
    display: flex;
    flex-direction: column;
    max-height: calc(100% - 24px);
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-width: none;
  }
  .drawer.is-grouped::-webkit-scrollbar { display: none; }
  .drawer.is-grouped > .drawer__title,
  .drawer.is-grouped > .eq {
    flex-shrink: 0;
  }

  .rule {
    height: 1px;
    background: rgba(233, 238, 242, 0.1);
    margin: 22px 0 20px;
  }
  .players {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .players__text { flex: 1; min-width: 0; }
  .players__title { font-size: 19px; font-weight: 600; }
  .players__sub { font-size: 15px; margin-top: 4px; color: rgba(233, 238, 242, 0.6); }
  .add {
    font: inherit;
    height: 58px;
    padding: 0 22px;
    border-radius: 15px;
    box-sizing: border-box;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.14);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    font-size: 17px;
    font-weight: 600;
    white-space: nowrap;
    flex-shrink: 0;
    color: var(--ink);
  }
  .add:active { transform: scale(0.95); }
  .add__plus { font-size: 24px; font-weight: 400; line-height: 1; margin-top: -2px; }

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
