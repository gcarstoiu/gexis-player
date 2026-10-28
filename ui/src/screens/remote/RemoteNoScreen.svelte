<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0164 D5: the Remote page of a player without a screen
  (design/source/21, *Remote page: a player without a screen*): a large
  cover in the space above the title, the title and artist · album, a seek
  bar, larger transport and the volume row. The bar seeks where the renderer
  can (C2); otherwise it is the design's inert rule, with no knob. Nothing
  playing: the bar, the times and the transport at 0.38, inert. Shorter than
  the drawing, the cover gives way to its floor (C10) before the page
  scrolls.
-->
<script>
  import { active, available, metadata } from '../../lib/state.js';
  import { playhead, mmss } from '../../lib/playhead.svelte.js';
  import RemoteCover from './RemoteCover.svelte';
  import RemoteTransport from './RemoteTransport.svelte';
  import VolumeRow from './VolumeRow.svelte';
  import GroupMark from './GroupMark.svelte';
  import { seek } from './commands.js';

  let { artwork = null, onartfailed, onsay, oneq, ongroup, onmark } = $props();

  const hasTrack = $derived(!!$active);
  const head = playhead(() => $metadata);
  const canSeek = $derived(hasTrack && head.hasPosition && $available.includes('seek'));
  const byline = $derived([$metadata?.artist, $metadata?.album].filter(Boolean).join(' · '));

  //: While a finger is on the bar it shows where the finger is, and for a
  //: moment after, until the player reports the new position.
  let held = $state(null);
  let heldTimer;
  const fraction = $derived(held ?? (head.hasPosition ? head.percent / 100 : 0));
  function ratio(event, el) {
    const r = el.getBoundingClientRect();
    return Math.max(0, Math.min(1, (event.clientX - r.left) / r.width));
  }
  let seeking = null;
  function down(event) {
    if (!canSeek) return;
    const el = event.currentTarget;
    el.setPointerCapture?.(event.pointerId);
    seeking = el;
    clearTimeout(heldTimer);
    held = ratio(event, el);
  }
  function move(event) {
    if (seeking) held = ratio(event, seeking);
  }
  function up() {
    if (!seeking) return;
    seeking = null;
    const at = held * (head.duration ?? 0);
    seek(at);
    heldTimer = setTimeout(() => (held = null), 1500);
  }
  $effect(() => {
    void $metadata?.position;
    if (!seeking && held !== null) {
      clearTimeout(heldTimer);
      heldTimer = setTimeout(() => (held = null), 200);
    }
  });
</script>

<div class="page">
  <div class="art">
    <div class="cover"><RemoteCover {artwork} {hasTrack} big onfailed={onartfailed} /></div>
  </div>
  <div class="text">
    <span class="title" class:is-none={!hasTrack}>{hasTrack ? ($metadata?.title ?? 'Playing') : 'Nothing playing'}</span>
    {#if hasTrack && byline}<span class="by">{byline}</span>{/if}
  </div>
  <div class="played" class:is-idle={!hasTrack} inert={!hasTrack}>
    <div class="seek" class:can-seek={canSeek} role="slider" tabindex="-1" aria-label="Position"
         aria-valuemin="0" aria-valuemax={Math.round(head.duration ?? 0)} aria-valuenow={Math.round(fraction * (head.duration ?? 0))}
         onpointerdown={down} onpointermove={move} onpointerup={up} onpointercancel={up}>
      <span class="seek__track" class:is-live={hasTrack && !head.hasPosition}>
        {#if hasTrack && head.hasPosition}<span class="seek__fill" style:width={`${fraction * 100}%`}></span>{/if}
      </span>
      {#if canSeek}<span class="seek__knob" style:left={`${fraction * 100}%`}></span>{/if}
    </div>
    <div class="times">
      <span>{!hasTrack ? '0:00' : head.hasPosition ? mmss(held !== null ? held * head.duration : head.elapsed) : mmss($metadata?.position ?? 0)}</span>
      <span>{!hasTrack ? '0:00' : head.hasPosition ? mmss(head.duration) : 'live'}</span>
    </div>
  </div>
  <!-- ADR-0166 (3a): the grouped mark, under the times, above the transport. -->
  <GroupMark onopen={onmark} gap={8} height={20} />
  <div class="transport"><RemoteTransport big /></div>
  <div class="volume"><VolumeRow {oneq} {ongroup} {onsay} /></div>
</div>

<style>
  .page {
    min-height: 100%;
    box-sizing: border-box;
    padding: 0 16px 16px;
    display: flex;
    flex-direction: column;
  }
  .art {
    position: relative;
    flex: 1 1 0;
    min-height: 140px;
    margin: 6px 0 18px;
    container-type: size;
  }
  /* Square, the space's height up to 380 and never wider than the column
     (the design's); sized from both, so a narrow phone keeps it square. */
  .cover {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: min(100cqw, 100cqh, 380px);
    aspect-ratio: 1 / 1;
  }
  .text {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    text-align: center;
    min-width: 0;
  }
  .title {
    max-width: 100%;
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.01em;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    overflow-wrap: anywhere;
  }
  .title.is-none {
    color: rgba(233, 238, 242, 0.6);
  }
  .by {
    max-width: 100%;
    font-size: 17px;
    color: rgba(233, 238, 242, 0.72);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .played {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
  }
  .played.is-idle {
    opacity: 0.38;
  }
  .seek {
    position: relative;
    flex-shrink: 0;
    height: 28px;
    margin-top: 14px;
    display: flex;
    align-items: center;
    touch-action: none;
    cursor: default;
  }
  .seek.can-seek {
    cursor: pointer;
  }
  .seek__track {
    position: relative;
    width: 100%;
    height: 6px;
    border-radius: 3px;
    overflow: hidden;
    display: block;
    background: rgba(233, 238, 242, 0.14);
  }
  .seek__track.is-live {
    background: linear-gradient(90deg, rgba(233, 238, 242, 0), rgba(233, 238, 242, 0.15) 16%, rgba(233, 238, 242, 0.15) 84%, rgba(233, 238, 242, 0));
  }
  .seek__fill {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    background: #7ed6bc;
    display: block;
  }
  .seek__knob {
    position: absolute;
    top: 50%;
    width: 18px;
    height: 18px;
    margin: -9px 0 0 -9px;
    border-radius: 50%;
    background: #e9eef2;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);
    display: block;
    pointer-events: none;
  }
  .times {
    flex-shrink: 0;
    display: flex;
    justify-content: space-between;
    font-family: var(--font-mono);
    font-size: 12px;
    line-height: 16px;
    color: rgba(233, 238, 242, 0.6);
  }
  .transport {
    flex-shrink: 0;
    margin-top: 10px;
  }
  .volume {
    flex-shrink: 0;
    margin-top: 16px;
  }
</style>
