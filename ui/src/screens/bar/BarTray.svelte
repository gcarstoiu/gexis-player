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

  **ADR-0166 (design/source/22, 2a): the group.** A *Group* pill beside the
  equaliser's opens a second band as the equaliser's does: the members'
  cards, + Add players, Leave and Undo group - or, not grouped, Add players.
  Grouped, the pill names how many play together and the slider is the
  *All* slider, its mute the group's.
-->
<script>
  import { onMount } from 'svelte';
  import { fixedMute, fixedOutput, meters } from '../../lib/state.js';
  import { VolumeControl } from '../../lib/volumeControl.svelte.js';
  import { pressing } from '../../lib/press.svelte.js';
  import LockIcon from '../../lib/LockIcon.svelte';
  import VolumeIcon from '../../lib/VolumeIcon.svelte';
  import { pull, bandDrag, TRAY_H, trayAsk } from './tray.svelte.js';
  import { equaliser } from '../../lib/equaliser.svelte.js';
  import EqQuick from '../eq/EqQuick.svelte';
  import GroupGlyph from '../../lib/GroupGlyph.svelte';
  import { dragStart, group, groupLevel, LevelSender, setGroupMute } from '../../lib/group.svelte.js';
  import BarAddBand from '../group/BarAddBand.svelte';
  import BarGroupBand from '../group/BarGroupBand.svelte';
  import BarUndoConfirm from '../group/BarUndoConfirm.svelte';

  //: `armsAt`: before this (performance.now()), a tray that came down by
  //: itself takes no touch on its level or mute (App.svelte, VOLUME_ARM_MS).
  let { open, armsAt = 0, volume, active, onclose, onexternal, onactivity, onsettled, onhome, onvisualisation, ondashboard = null, onequaliser = null, rootless = false } = $props();

  //: ADR-0162 (design/source/20, Q06-Q09): the EQ button opens a second band
  //: under the first - the switch, the settings, the note and Edit. ADR-0166
  //: (design/source/22, 2a): the Group pill opens its own there, 150 tall -
  //: the members (`group`) or Add players (`add`).
  const EQ_H = 254;
  const GROUP_H = 290;
  let second = $state(null);
  let confirming = $state(false);
  $effect(() => {
    if (!open) {
      second = null;
      confirming = false;
    }
  });
  //: The grouped mark on Now Playing asked for the group's band.
  $effect(() => {
    if (open && trayAsk.band) {
      second = trayAsk.band === 'group' && !$group ? 'add' : trayAsk.band;
      trayAsk.band = null;
    }
  });
  //: A group undone or left while its band shows: the band goes with it.
  $effect(() => {
    if (second === 'group' && !$group) second = null;
  });
  const eqBand = $derived(second === 'eq');
  const groupBand = $derived(second === 'group' || second === 'add');
  const trayH = $derived(eqBand ? EQ_H : groupBand ? GROUP_H : TRAY_H);
  const eqLit = $derived(!!$equaliser?.on && !$equaliser?.dsd);
  const eqName = $derived(!$equaliser ? '' : !$equaliser.on ? 'EQ off' : $equaliser.dsd ? 'DSD'
    : $equaliser.sel === 'custom' ? 'Custom' : ($equaliser.name ?? 'Flat'));
  function goEqualiser() {
    onclose?.();
    onequaliser?.();
  }

  const press = pressing();

  // ---- the group (ADR-0166) ----------------------------------------------------
  //: The other players, for the pill and Add players: asked each time the
  //: tray opens, as the phone's list is.
  let players = $state([]);
  let here = $state(null);
  async function loadPlayers() {
    try {
      const response = await fetch('/players');
      if (!response.ok) return;
      const body = await response.json();
      here = body.self ?? null;
      players = body.others ?? [];
    } catch {
      // Kept as it was: the pill stays as it is until the next answer.
    }
  }
  $effect(() => {
    if (open) loadPlayers();
  });
  // Asked once at the start too, so the pill is there the first time.
  onMount(loadPlayers);
  const grouped = $derived(!!$group);
  //: Only where there is somebody to group with, or a group already.
  const groupOffered = $derived(grouped || players.length > 0);
  function toggleGroup() {
    if (groupBand) {
      second = null;
      return;
    }
    second = grouped ? 'group' : 'add';
    if (!grouped) loadPlayers();
  }
  function openAdd() {
    second = 'add';
    loadPlayers();
  }

  // ---- the level: one copy, shared with the panel's drawer -----------------
  //: lib/volumeControl.svelte.js. The level is measured against the rail,
  //: not the touch area, which is taller and wider.
  const vol = new VolumeControl({
    volume: () => volume,
    active: () => active,
    onexternal: () => onexternal,
    onsettled: () => onsettled,
    fixedMute: () => $fixedMute,
  });
  const toast = $derived(vol.toast);
  let rail = $state(null);

  //: **Grouped, the slider is the *All* slider** (D6, the design's
  //: `dragGroup`): every Variable member the same share of its own way from
  //: where they were when the finger landed, drawn before the core's answer.
  const gsend = new LevelSender((percent, from) => groupLevel(percent, from),
    (error) => vol.flash(`Volume not changed: ${error.message}`));
  let gLocal = $state(null);
  let gFrom = null;
  const gVariable = $derived(($group?.members ?? []).some((m) => m.reachable && !m.fixed && m.volume != null));
  function gSet(x) {
    const r = rail.getBoundingClientRect();
    gLocal = Math.round(Math.max(0, Math.min(1, (x - r.left) / r.width)) * 100);
    gsend.send(gLocal, gFrom);
  }
  let gTimer;
  function gUp() {
    gFrom = null;
    // The members' own reports take over once they arrive.
    clearTimeout(gTimer);
    gTimer = setTimeout(() => { if (gFrom === null) gLocal = null; }, 1200);
  }
  const slide = {
    down(x, target, pointerId) {
      if (!grouped) return vol.down({ clientX: x, currentTarget: target, pointerId }, rail);
      if (!gVariable) return;
      gFrom = dragStart($group);
      gSet(x);
    },
    move(event) {
      if (!grouped) return vol.move(event, rail);
      if (gFrom) gSet(event.clientX);
    },
    up() {
      if (!grouped) return vol.up();
      gUp();
    },
    step(delta) {
      if (!grouped) return vol.step(delta);
      if (!gVariable) return;
      gFrom = dragStart($group);
      // From the level shown: a scroll sends several steps before the
      // members' answer arrives.
      gLocal = Math.max(0, Math.min(100, (gLocal ?? $group?.level ?? 0) + delta));
      gsend.send(gLocal, gFrom);
      gUp();
    },
  };
  const muted = $derived(grouped ? !!$group?.muted : vol.muted);
  const pct = $derived(grouped ? (gLocal ?? $group?.level ?? 0) : vol.pct);
  const shown = $derived(grouped ? (gVariable ? pct : '—') : vol.shown);
  //: **The slider waits to see which way the finger goes** (George,
  //: 2026-10-04: the swipe up "still doesn't work"). The slider is most of
  //: the tray, and it took every touch at once - setting the level under the
  //: finger - so a swipe up that began on it never reached the tray. Now a
  //: move of 8 px decides: mostly upward closes the tray, anything else is
  //: the slider, from where the finger first landed. A tap sets the level,
  //: on lift.
  const DECIDE = 8;
  let pending = null;
  function down(event) {
    if (performance.now() < armsAt) return;
    pending = { x: event.clientX, y: event.clientY, id: event.pointerId, way: null };
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }
  function move(event) {
    if (!pending) return;
    if (pending.way === null) {
      const dx = event.clientX - pending.x;
      const dy = event.clientY - pending.y;
      if (Math.max(Math.abs(dx), Math.abs(dy)) < DECIDE) return;
      pending.way = -dy > Math.abs(dx) ? 'close' : 'slide';
      if (pending.way === 'close') band.down({ clientY: pending.y, pointerId: pending.id });
      else slide.down(pending.x, event.currentTarget, pending.id);
    }
    if (pending.way === 'close') band.move(event);
    else slide.move(event);
  }
  function up(event) {
    if (!pending) return;
    const way = pending.way;
    if (way === null) {
      // A tap: the level where it landed.
      slide.down(pending.x, event.currentTarget, pending.id);
      slide.up();
    } else if (way === 'close') {
      band.up();
      slide.up();
    } else {
      slide.up();
    }
    pending = null;
  }
  function cancel() {
    if (pending?.way === 'close') band.cancel();
    if (pending?.way === 'slide') slide.up();
    pending = null;
  }
  async function toggleMute() {
    if (performance.now() < armsAt) return;
    if (!grouped) return vol.toggleMute();
    try {
      await setGroupMute(!$group.muted);
    } catch (error) {
      vol.flash(`Mute not changed: ${error.message}`);
    }
  }

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

  //: **A swipe up anywhere closes it** (George, 2026-10-04: "Dismissing it
  //: should work as well with a swipe up") - not only on the close band.
  //: Still the control under the finger first: a touch that lands on a
  //: button or the slider is theirs.
  //: The group's cards scroll sideways under a finger (ADR-0166).
  const OWN = 'button, input, .slider, [role="slider"], .closeband, [data-pan-x]';
  const bodySwipe = {
    down(event) { if (!event.target.closest(OWN)) band.down(event); },
    move: band.move,
    up: band.up,
    cancel: band.cancel,
  };

  //: Each acts when the finger lifts on it (`press.lift`, which says why);
  //: `press.click` takes a mouse's click.
  function goHome() {
    onclose?.();
    onhome?.();
  }
  //: ADR-0156: the Home Assistant dashboard, when an address is set.
  function goDashboard() {
    onclose?.();
    ondashboard?.();
  }
  function goVisualiser() {
    onclose?.();
    onvisualisation?.();
  }
</script>

<!-- **The rest of the screen takes the swipe too** (George, 2026-10-04: "a
     swipe up from the bottom of the display should work"): a swipe up that
     starts below the tray closes it, and a tap still does. -->
<div class="scrim" class:is-shown={open || following} style:opacity={shownH / TRAY_H}
  role="presentation"
  onpointerdown={band.down} onpointermove={band.move} onpointerup={band.up} onpointercancel={band.cancel}></div>

<div
  class="tray"
  class:is-shown={open || following}
  class:is-following={following}
  style:height={`${trayH}px`}
  style:transform={`translateY(${shownH - TRAY_H - (shownH ? 0 : 60 + trayH - TRAY_H)}px)`}
  inert={!open}
  role="presentation"
  data-dpad-layer
  ondpadback={(event) => { event.preventDefault(); onclose?.(); }}
  onpointerdown={(event) => { onactivity?.(event); bodySwipe.down(event); }}
  onpointermove={bodySwipe.move}
  onpointerup={(event) => { onsettled?.(event); bodySwipe.up(event); }}
  onpointercancel={(event) => { onsettled?.(event); bodySwipe.cancel(event); }}
  onpointerenter={(event) => event.pointerType === 'mouse' && onactivity?.(event)}
  onpointerleave={(event) => event.pointerType === 'mouse' && onsettled?.(event)}
>
  <div class="closeband" role="button" tabindex="-1" aria-label="Close controls" data-dpad-skip
    onpointerdown={band.down} onpointermove={band.move} onpointerup={band.up} onpointercancel={band.cancel}></div>
  <div class="handle"></div>

  <div class="row">
  <button class="btn btn--home" class:is-pressed={press.is('home')} type="button" data-dpad-main aria-label={rootless ? 'Settings' : 'Home'}
    onpointerdown={() => press.down('home')} onpointerup={(event) => press.lift(event, goHome)} onpointercancel={press.up} onclick={() => press.click(goHome)}>
    {#if rootless}
      <span class="i-sliders"><i></i><b></b><i></i><b></b></span>
    {:else}
      <span class="i-tiles"><i></i><i></i><i></i><i></i></span>
    {/if}
  </button>
  {#if $meters}
    <button class="btn" class:is-pressed={press.is('viz')} type="button" aria-label="Visualization"
      onpointerdown={() => press.down('viz')} onpointerup={(event) => press.lift(event, goVisualiser)} onpointercancel={press.up} onclick={() => press.click(goVisualiser)}>
      <span class="i-meter"><i style="height:12px"></i><i style="height:22px"></i><i style="height:16px"></i><i style="height:8px"></i></span>
    </button>
  {/if}
  {#if ondashboard}
    <button class="btn" class:is-pressed={press.is('dash')} type="button" aria-label="Home Assistant dashboard"
      onpointerdown={() => press.down('dash')} onpointerup={(event) => press.lift(event, goDashboard)} onpointercancel={press.up} onclick={() => press.click(goDashboard)}>
      <svg class="i-dash" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 11 12 4.5 20 11v8.5H14.5V14h-5v5.5H4Z" /></svg>
    </button>
  {/if}
  {#if $equaliser}
    <button class="eqbtn" class:is-lit={eqLit} type="button" aria-label="Equaliser" aria-expanded={eqBand}
      onpointerup={(event) => press.lift(event, () => (second = eqBand ? null : 'eq'))} onclick={() => press.click(() => (second = eqBand ? null : 'eq'))}>
      <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <path d="M6 4v16M12 4v16M18 4v16" />
        <circle cx="6" cy="14" r="2.6" fill="#16232c" /><circle cx="12" cy="8" r="2.6" fill="#16232c" /><circle cx="18" cy="15" r="2.6" fill="#16232c" />
      </svg>
      <span class="eqbtn__name">{eqName}</span>
      <span class="eqbtn__chev" class:is-open={eqBand}></span>
    </button>
  {/if}
  {#if groupOffered}
    <!-- ADR-0166: beside the equaliser's, built as it is. -->
    <button class="eqbtn" class:is-lit={grouped || groupBand} type="button" aria-label="Group" aria-expanded={groupBand}
      onpointerup={(event) => press.lift(event, toggleGroup)} onclick={() => press.click(toggleGroup)}>
      <GroupGlyph size={24} />
      <span class="eqbtn__name">{grouped ? `${$group.members.length} players` : 'Group'}</span>
      <span class="eqbtn__chev" class:is-open={groupBand}></span>
    </button>
  {/if}
  <span class="divider"></span>

  {#if $fixedOutput && !grouped}
    <!-- ADR-0046: the sentence where the question is asked, not a disabled
         slider. ADR-0165: mute before it, where the output can be silenced. -->
    {#if $fixedMute !== null}
      <button class="btn mute" class:is-muted={muted} type="button" aria-label={muted ? 'Unmute' : 'Mute'}
        onpointerup={(event) => press.lift(event, toggleMute)} onclick={() => press.click(toggleMute)}>
        {#if muted}
          <span class="i-muted"><span class="i-muted__cone"></span><i></i><i></i></span>
        {:else}
          <VolumeIcon percent={100} muted={false} />
        {/if}
      </button>
    {/if}
    <div class="fixed">
      <span class="fixed__lock"><LockIcon size={34} /></span>
      <span class="fixed__text">
        <span class="fixed__title">Fixed output</span>
        <span class="fixed__sub">Level is set downstream. Set it on your amplifier.</span>
      </span>
      <span class="fixed__level" class:is-muted={muted}>{muted ? 'Mute' : '100%'}</span>
    </div>
  {:else if volume || grouped}
    {#if grouped}<span class="all">All</span>{/if}
    <button class="btn mute" class:is-muted={muted} type="button" aria-label={muted ? 'Unmute' : 'Mute'}
      onpointerup={(event) => press.lift(event, toggleMute)} onclick={() => press.click(toggleMute)}>
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
      aria-label={grouped ? 'All players volume' : 'Volume'}
      aria-valuemin="0"
      aria-valuemax="100"
      aria-valuenow={pct}
      data-step="2"
      ondpadstep={(event) => slide.step(event.detail.step * 2)}
      onpointerdown={down}
      onpointermove={move}
      onpointerup={up}
      onpointercancel={cancel}
    >
      <div class="rail" bind:this={rail} data-dpad-box>
        <div class="fill" class:is-muted={muted} style:width={`${pct}%`}></div>
        <div class="knob" class:is-muted={muted} style:left={`${pct}%`} data-dpad-knob></div>
      </div>
    </div>
    <span class="readout" class:is-muted={muted}>{muted ? 'Mute' : shown}</span>
  {/if}
  </div>
  {#if eqBand}
    <div class="eqband">
      <EqQuick host="bartray" onedit={goEqualiser} />
    </div>
  {:else if second === 'group' && $group}
    <BarGroupBand g={$group} onadd={openAdd} onundo={() => (confirming = true)} onerror={(text) => vol.flash(text)} />
  {:else if second === 'add'}
    <BarAddBand g={$group} {players} {here} ondone={() => (second = grouped ? 'group' : null)}
      onerror={(text) => vol.flash(text)} />
  {/if}
</div>

<BarUndoConfirm open={confirming} g={$group} onclose={() => (confirming = false)} onerror={(text) => vol.flash(text)} />

<div class="toast" class:is-shown={toast}>
  <span>{toast ?? ''}</span>
</div>

<style>
  .pending {
    flex-shrink: 0;
    font-size: 15px;
    color: var(--accent-warn);
    white-space: nowrap;
  }
  .scrim {
    position: absolute;
    inset: 0;
    z-index: 12;
    touch-action: none;
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
    /* **The page's, not the browser's** - without it a finger's drag on the
       tray became a browser pan, which cancels the swipe up, and the tray
       closed only when its 3 s timer ran out (George, 2026-10-04: "I do it
       and then 2 or 3 seconds later it actually does it"). The slider sets
       its own. */
    touch-action: none;
    z-index: 13;
    display: flex;
    flex-direction: column;
    padding: 0 0 14px;
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
  .row {
    height: 122px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 0 40px;
  }
  /* ADR-0162: the equaliser's band, under the first (design/source/20, Q07). */
  .eqband {
    position: relative;
    z-index: 1;
    height: 120px;
    flex-shrink: 0;
    padding: 0 40px;
    border-top: 1px solid rgba(233, 238, 242, 0.08);
  }
  .eqbtn {
    position: relative;
    z-index: 1;
    height: 60px;
    padding: 0 20px 0 18px;
    border-radius: 30px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.14);
    color: rgba(233, 238, 242, 0.82);
    font: inherit;
  }
  .eqbtn.is-lit {
    background: rgba(126, 214, 188, 0.12);
    border-color: rgba(126, 214, 188, 0.45);
    color: #7ed6bc;
  }
  .eqbtn:active {
    transform: scale(0.95);
  }
  .eqbtn__name {
    font-size: 19px;
    font-weight: 700;
    white-space: nowrap;
  }
  .eqbtn__chev {
    width: 9px;
    height: 9px;
    border-right: 2.5px solid rgba(233, 238, 242, 0.6);
    border-bottom: 2.5px solid rgba(233, 238, 242, 0.6);
    transform: rotate(45deg) translate(-2px, -2px);
    transition: transform 160ms ease;
  }
  .eqbtn__chev.is-open {
    transform: rotate(-135deg) translate(-2px, -2px);
  }

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
  .i-dash { width: 26px; height: 26px; fill: none; stroke: rgba(233, 238, 242, 0.85); stroke-width: 2; stroke-linejoin: round; }
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

  /* ADR-0166: the group's level, the design's label before its mute. */
  .all {
    font-family: var(--font-mono);
    font-size: 14px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--group-ink);
    flex-shrink: 0;
  }

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
  .fixed__level.is-muted {
    color: var(--accent-warn);
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
