<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The bar's pull-down tray (ADR-0109, Bar family): what the panel spreads
  over Now Playing's bottom row and its volume drawer, in one 136px band
  from the top edge. From `design/source/13b/Bar Frame.dc.html` (strip,
  sr main, pull down, tray) and `Bar States.dc.html` (tray-*), round 2:
  Home 64 (Settings with LMS off), the visualiser 60 (gone with no meters),
  a divider, then mute 60, the slider (knob 44, touches across the tray's
  height) and the value - or, in fixed output, the panel's padlock row.

  It stands where VolumeDrawer stands on a Standard screen and takes the
  same props from App.svelte, so it opens by itself on a volume change from
  elsewhere - over any screen, the library included - and closes after
  `drawer_autohide`, held open only while a finger is on it.

  **The slider fill stays LMS teal for every source** (George, 2026-10-01,
  review decision 7: keep the panel's), not the source accent round 2 drew.
-->
<script>
  import { fixedOutput, meters } from '../../lib/state.js';
  import { VolumeControl } from '../../lib/volumeControl.svelte.js';
  import { pressing } from '../../lib/press.svelte.js';
  import LockIcon from '../../lib/LockIcon.svelte';
  import VolumeIcon from '../../lib/VolumeIcon.svelte';
  import { pull, bandDrag, TRAY_H } from './tray.svelte.js';

  let { open, volume, active, onclose, onexternal, onactivity, onsettled, onhome, onvisualisation, rootless = false } = $props();

  const press = pressing();

  // ---- the level: one copy, shared with the panel's drawer -----------------
  //: lib/volumeControl.svelte.js. The level is measured against the rail,
  //: not the touch area, which is taller and wider.
  const vol = new VolumeControl({
    volume: () => volume,
    active: () => active,
    onexternal: () => onexternal,
    onsettled: () => onsettled,
  });
  const muted = $derived(vol.muted);
  const shown = $derived(vol.shown);
  const pct = $derived(vol.pct);
  const toast = $derived(vol.toast);
  let rail = $state(null);
  const down = (event) => vol.down(event, rail);
  const move = (event) => vol.move(event, rail);
  const up = () => vol.up();
  const toggleMute = () => vol.toggleMute();

  // ---- open, closed and in between -------------------------------------------
  //: How far the tray is from closed, 0 to TRAY_H: the strip's band while it
  //: pulls the tray down, this tray's own band while it pushes it back up.
  let closing = $state(null);
  const shownH = $derived(
    pull.offset !== null ? pull.offset : closing !== null ? TRAY_H - closing : open ? TRAY_H : 0,
  );
  const following = $derived(pull.offset !== null || closing !== null);

  //: **The control under the finger wins** (as on the strip's band). The
  //: close band is the tray's bottom 44px, but the slider takes touches
  //: across the tray's whole height and sits above it, and so do the
  //: buttons - so the band only takes what lands outside them: either side
  //: of the slider's column. A tap on the dimmed strip below closes it as
  //: well, and so does `drawer_autohide`.
  const band = bandDrag(-1, {
    onmove: (travel) => (closing = travel),
    onend: ({ tap, travel, cancelled }) => {
      closing = null;
      if (cancelled) return;
      if (tap || travel > TRAY_H * 0.35) onclose?.();
    },
  });

  function goHome() {
    press.act(() => {
      onclose?.();
      onhome?.();
    });
  }
  function goVisualiser() {
    press.act(() => {
      onclose?.();
      onvisualisation?.();
    });
  }
</script>

<div class="scrim" class:is-shown={open || following} style:opacity={shownH / TRAY_H}
  role="presentation" onclick={onclose}></div>

<div
  class="tray"
  class:is-shown={open || following}
  class:is-following={following}
  style:transform={`translateY(${shownH - TRAY_H - (shownH ? 0 : 60)}px)`}
  inert={!open}
  role="presentation"
  onpointerdown={onactivity}
  onpointerup={onsettled}
  onpointercancel={onsettled}
>
  <div class="closeband" role="button" tabindex="-1" aria-label="Close controls"
    onpointerdown={band.down} onpointermove={band.move} onpointerup={band.up} onpointercancel={band.cancel}></div>
  <div class="handle"></div>

  <button class="btn btn--home" class:is-pressed={press.is('home')} type="button" aria-label={rootless ? 'Settings' : 'Home'}
    onpointerdown={() => press.down('home')} onpointerup={press.up} onpointercancel={press.up} onclick={goHome}>
    {#if rootless}
      <span class="i-sliders"><i></i><b></b><i></i><b></b></span>
    {:else}
      <span class="i-tiles"><i></i><i></i><i></i><i></i></span>
    {/if}
  </button>
  {#if $meters}
    <button class="btn" class:is-pressed={press.is('viz')} type="button" aria-label="Visualization"
      onpointerdown={() => press.down('viz')} onpointerup={press.up} onpointercancel={press.up} onclick={goVisualiser}>
      <span class="i-meter"><i style="height:12px"></i><i style="height:22px"></i><i style="height:16px"></i><i style="height:8px"></i></span>
    </button>
  {/if}
  <span class="divider"></span>

  {#if $fixedOutput}
    <!-- ADR-0046: the sentence where the question is asked, not a disabled
         slider. -->
    <div class="fixed">
      <span class="fixed__lock"><LockIcon size={34} /></span>
      <span class="fixed__text">
        <span class="fixed__title">Fixed output</span>
        <span class="fixed__sub">Level is set downstream. Set it on your amplifier.</span>
      </span>
      <span class="fixed__level">100%</span>
    </div>
  {:else if volume}
    <button class="btn mute" class:is-muted={muted} type="button" aria-label={muted ? 'Unmute' : 'Mute'} onclick={toggleMute}>
      {#if muted}
        <!-- Round 2's muted glyph: the cone dimmed, crossed in amber. -->
        <span class="i-muted"><span class="i-muted__cone"></span><i></i><i></i></span>
      {:else}
        <VolumeIcon percent={pct} muted={false} />
      {/if}
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
      <div class="rail" bind:this={rail}>
        <div class="fill" class:is-muted={muted} style:width={`${pct}%`}></div>
        <div class="knob" class:is-muted={muted} style:left={`${pct}%`}></div>
      </div>
    </div>
    <span class="readout" class:is-muted={muted}>{muted ? 'Mute' : shown}</span>
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
    background: rgba(8, 12, 16, 0.55);
    pointer-events: none;
    visibility: hidden;
    transition: opacity 220ms ease, visibility 0s linear 220ms;
  }
  .scrim.is-shown {
    pointer-events: auto;
    visibility: visible;
    transition: opacity 220ms ease;
  }

  .tray {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    height: 136px;
    z-index: 13;
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 0 40px 14px;
    background: var(--bg-panel);
    border-radius: 0 0 24px 24px;
    border-bottom: 1px solid rgba(233, 238, 242, 0.12);
    box-shadow: 0 18px 44px rgba(0, 0, 0, 0.5);
    visibility: hidden;
    transition:
      transform 240ms cubic-bezier(0.2, 0.8, 0.2, 1),
      visibility 0s linear 240ms;
  }
  .tray.is-shown {
    visibility: visible;
    transition: transform 240ms cubic-bezier(0.2, 0.8, 0.2, 1);
  }
  /* Under a finger it is wherever the finger is. */
  .tray.is-following { transition: none; }

  .closeband {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 44px;
    z-index: 0;
    touch-action: none;
  }
  .handle {
    position: absolute;
    left: 50%;
    bottom: 10px;
    width: 88px;
    height: 6px;
    margin-left: -44px;
    border-radius: 3px;
    background: rgba(233, 238, 242, 0.42);
    pointer-events: none;
    z-index: 2;
  }

  .btn {
    position: relative;
    z-index: 1;
    width: var(--ctl);
    height: var(--ctl);
    border: 0;
    padding: 0;
    border-radius: var(--r-circle);
    background: var(--ink-fill);
    color: var(--ink);
    display: grid;
    place-items: center;
    flex-shrink: 0;
  }
  .btn:active,
  .btn.is-pressed { transform: scale(0.95); }
  .btn--home {
    width: 64px;
    height: 64px;
  }
  .i-tiles {
    width: 24px;
    height: 24px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 4px;
  }
  .i-tiles i { border-radius: 3px; background: rgba(233, 238, 242, 0.85); }
  .i-sliders {
    position: relative;
    width: 22px;
    height: 16px;
    display: block;
  }
  .i-sliders i,
  .i-sliders b {
    position: absolute;
    display: block;
    background: var(--ink-strong);
  }
  .i-sliders i {
    left: 0;
    width: 22px;
    height: 2px;
    border-radius: 1px;
    opacity: 0.6;
  }
  .i-sliders i:first-child { top: 3px; }
  .i-sliders i:nth-child(3) { top: 11px; }
  .i-sliders b { width: 6px; height: 6px; border-radius: 50%; }
  .i-sliders b:nth-child(2) { top: 1px; left: 5px; }
  .i-sliders b:nth-child(4) { top: 9px; left: 13px; }
  .i-meter { display: flex; align-items: flex-end; gap: 4px; height: 22px; }
  .i-meter i { width: 4px; border-radius: 2px; background: var(--ink-body); }

  .divider {
    width: 1px;
    height: 44px;
    background: rgba(233, 238, 242, 0.14);
    flex-shrink: 0;
  }

  .mute {
    border: 1px solid rgba(233, 238, 242, 0.12);
  }
  .mute.is-muted {
    background: rgba(224, 167, 88, 0.14);
    border-color: rgba(224, 167, 88, 0.45);
  }
  .i-muted {
    position: relative;
    width: 30px;
    height: 30px;
    display: block;
  }
  .i-muted__cone {
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 15px;
    height: 26px;
    background: rgba(233, 238, 242, 0.45);
    clip-path: polygon(0 27%, 42% 27%, 100% 0, 100% 100%, 42% 73%, 0 73%);
    display: block;
  }
  .i-muted i {
    position: absolute;
    left: 19px;
    top: 50%;
    width: 12px;
    height: 2.5px;
    margin-top: -1px;
    border-radius: 2px;
    background: var(--accent-warn);
    transform: rotate(45deg);
    display: block;
  }
  .i-muted i:last-child { transform: rotate(-45deg); }

  /* Touches across the tray's height: the area runs from the tray's top to
     its bottom edge (through the padding), above the close band. */
  .track {
    position: relative;
    z-index: 1;
    flex: 1;
    align-self: stretch;
    margin-bottom: -14px;
    display: flex;
    align-items: center;
    padding-bottom: 14px;
    min-width: 0;
    touch-action: none;
  }
  .rail {
    width: 100%;
    height: 10px;
    border-radius: var(--r-pill);
    background: rgba(233, 238, 242, 0.15);
    position: relative;
  }
  .fill {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    border-radius: var(--r-pill);
    background: var(--accent-lms);
    transition: background 160ms ease;
  }
  .fill.is-muted { background: rgba(224, 167, 88, 0.5); }
  .knob {
    position: absolute;
    top: 50%;
    width: 44px;
    height: 44px;
    border-radius: 50%;
    transform: translate(-50%, -50%);
    background: var(--ink);
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.45);
  }
  .knob.is-muted { background: rgba(233, 238, 242, 0.55); }
  .readout {
    font-family: var(--font-mono);
    font-size: 26px;
    font-weight: 700;
    width: 72px;
    text-align: right;
    flex-shrink: 0;
    color: var(--ink);
  }
  .readout.is-muted { color: var(--accent-warn); }

  .fixed {
    position: relative;
    z-index: 1;
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 20px;
    min-height: 78px;
    padding: 0 24px;
    border-radius: 18px;
    background: rgba(233, 238, 242, 0.05);
    border: 1px solid rgba(233, 238, 242, 0.12);
  }
  .fixed__lock {
    display: flex;
    flex-shrink: 0;
    color: rgba(233, 238, 242, 0.7);
  }
  .fixed__text {
    flex: 1;
    min-width: 0;
  }
  .fixed__title {
    display: block;
    font-size: 20px;
    font-weight: 600;
  }
  .fixed__sub {
    display: block;
    margin-top: 4px;
    font-size: 16px;
    line-height: 1.35;
    color: var(--ink-quiet);
  }
  .fixed__level {
    font-family: var(--font-mono);
    font-size: 15px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: rgba(233, 238, 242, 0.55);
    flex-shrink: 0;
  }

  .toast {
    position: absolute;
    z-index: 36;
    left: 50%;
    bottom: 40px;
    transform: translateX(-50%) translateY(12px);
    background: rgba(22, 35, 44, 0.97);
    border: 1px solid rgba(126, 214, 188, 0.3);
    border-radius: 14px;
    padding: 16px 26px;
    box-shadow: 0 18px 50px rgba(0, 0, 0, 0.5);
    transition: opacity 220ms ease, transform 220ms ease;
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
