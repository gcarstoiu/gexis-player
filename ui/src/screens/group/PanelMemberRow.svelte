<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  A member's own level in the panel's group volume (ADR-0166 D6;
  design/source/22, Multiroom Panel, `gvRows`): its name and tag, then its
  mute and slider - a Fixed member's locked row, an unreachable one's dashed
  *Not reachable* - and Remove where it can be taken out.
-->
<script>
  import VolumeIcon from '../../lib/VolumeIcon.svelte';
  import { track } from './panelSlider.js';

  //: `level`: what the slider shows (the finger's, while it moves).
  //: `armsAt`: the drawer's (VolumeDrawer); no touch before it.
  let { m, level, armsAt = 0, canremove = false, onlevel, ondone, onmute, onremove } = $props();
  const armed = () => performance.now() >= armsAt;

  const tag = $derived(!m.reachable ? 'Off' : m.leads ? 'Leads' : m.me ? 'This one' : m.fixed ? 'Fixed' : '');
  const drag = track((percent) => onlevel?.(percent), () => ondone?.());
  //: Left and Right on the slider (ADR-0161), as the drawer's own steps.
  const DPAD_STEP = 2;
</script>

<div class="member">
  <span class="who">
    <span class="name">{m.name}</span>
    <span class="tag" class:is-lead={m.leads && m.reachable}>{tag}</span>
  </span>
  {#if !m.reachable}
    <span class="off">Not reachable</span>
  {:else if m.fixed}
    {#if m.fixed_mute !== null}
      <button class="mute" type="button" aria-label={m.muted ? `Unmute ${m.name}` : `Mute ${m.name}`} onclick={() => armed() && onmute?.()}>
        <span class="small"><VolumeIcon percent={100} muted={m.muted} /></span>
      </button>
    {:else}
      <span class="gap"></span>
    {/if}
    <div class="locked">
      <span class="padlock"><i></i><b></b></span>
      <span class="locked__text">Fixed output · the amplifier sets the level</span>
      <span class="locked__tag">{m.muted ? 'Off' : '100%'}</span>
    </div>
  {:else}
    <button class="mute" type="button" aria-label={m.muted ? `Unmute ${m.name}` : `Mute ${m.name}`} onclick={() => armed() && onmute?.()}>
      <span class="small"><VolumeIcon percent={level} muted={m.muted} /></span>
    </button>
    <div class="track" role="slider" tabindex="-1" aria-label={`${m.name} volume`}
         aria-valuemin="0" aria-valuemax="100" aria-valuenow={level ?? 0} data-step={DPAD_STEP}
         ondpadstep={(event) => { onlevel?.(Math.max(0, Math.min(100, (level ?? 0) + event.detail.step * DPAD_STEP))); ondone?.(); }}
         onpointerdown={(event) => armed() && drag.down(event)} onpointermove={drag.move} onpointerup={drag.up} onpointercancel={drag.up}>
      <div class="rail">
        <div class="fill" class:is-muted={m.muted} style:width={`${level ?? 0}%`}></div>
        <div class="knob" style:left={`${level ?? 0}%`} data-dpad-knob></div>
      </div>
    </div>
    <span class="value">{m.muted ? 'Off' : (level ?? '—')}</span>
  {/if}
  {#if canremove}
    <button class="remove" type="button" aria-label={`Remove ${m.name}`} onclick={() => armed() && onremove?.()}>
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" style="stroke: var(--ink-body)"
           stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
    </button>
  {:else}
    <span class="gap"></span>
  {/if}
</div>

<style>
  .member {
    display: flex;
    align-items: center;
    gap: 16px;
    min-height: 64px;
    flex-shrink: 0;
  }
  .who {
    width: 200px;
    flex-shrink: 0;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .name {
    font-size: 17px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    padding-right: 3px;
  }
  .tag {
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: var(--group-leads-tracking);
    text-transform: uppercase;
    white-space: nowrap;
    color: var(--ink-quiet);
  }
  .tag:empty { display: none; }
  .tag.is-lead { color: var(--group-ink); }

  .mute {
    position: relative;
    width: 48px;
    height: 48px;
    border-radius: var(--r-13);
    flex-shrink: 0;
    display: grid;
    place-items: center;
    padding: 0;
    border: 0;
    background: transparent;
    color: inherit;
  }
  .mute:active { transform: scale(0.95); }
  .small { transform: scale(0.8); display: block; }

  .track {
    flex: 1;
    min-width: 0;
    height: 52px;
    display: flex;
    align-items: center;
    touch-action: none;
  }
  .rail {
    width: 100%;
    height: 10px;
    border-radius: var(--r-pill);
    background: var(--mark-line);
    position: relative;
  }
  .fill {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    border-radius: var(--r-pill);
    background: var(--group-ink);
  }
  .fill.is-muted { background: var(--c-lms-35); }
  .knob {
    position: absolute;
    top: 50%;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    transform: translate(-50%, -50%);
    box-shadow: 0 3px 10px var(--c-black-45);
    background: var(--ink);
  }
  .value {
    font-family: var(--font-mono);
    font-size: 20px;
    font-weight: 600;
    width: 64px;
    text-align: right;
    flex-shrink: 0;
  }

  .locked {
    flex: 1;
    min-width: 0;
    height: 52px;
    border-radius: var(--r-14);
    background: var(--c-ink-05);
    border: 1px solid var(--c-ink-12);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 0 18px;
  }
  /* The design's padlock, drawn as it draws it. */
  .padlock { position: relative; width: 22px; height: 26px; flex-shrink: 0; display: block; }
  .padlock i {
    position: absolute; left: 4px; top: 0; width: 14px; height: 12px;
    border: 2.5px solid var(--c-ink-70); border-bottom: none;
    border-radius: var(--r-7) var(--r-7) 0 0; box-sizing: border-box; display: block;
  }
  .padlock b {
    position: absolute; left: 0; bottom: 0; width: 22px; height: 15px;
    border-radius: var(--r-4); background: var(--c-ink-70); display: block;
  }
  .locked__text {
    flex: 1;
    min-width: 0;
    font-size: 16px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .locked__tag {
    font-family: var(--font-mono);
    font-size: 14px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--ink-quiet);
    flex-shrink: 0;
  }

  .off {
    flex: 1;
    min-width: 0;
    height: 52px;
    border-radius: var(--r-14);
    border: 1px dashed var(--ink-fill-press);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    padding: 0 18px;
    font-size: 16px;
    color: var(--ink-quiet);
  }

  .remove {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    flex-shrink: 0;
    display: grid;
    place-items: center;
    padding: 0;
    background: var(--ink-fill);
    border: 1px solid var(--c-ink-12);
    box-sizing: border-box;
  }
  .remove:active { transform: scale(0.95); }
  .gap { width: 48px; flex-shrink: 0; display: block; }
</style>
