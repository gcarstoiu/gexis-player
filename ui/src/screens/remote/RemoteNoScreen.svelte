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

  A station (ADR-0180, design/source/31 H20-H22): its quality on a line of
  its own, the heart at the transport's left, and while it reconnects or
  does not answer the line that says so, the cover at 0.45.
-->
<script>
  import { active, available, metadata } from '../../lib/state.js';
  import { playhead, mmss } from '../../lib/playhead.svelte.js';
  import RemoteCover from './RemoteCover.svelte';
  import RemoteTransport from './RemoteTransport.svelte';
  import VolumeRow from './VolumeRow.svelte';
  import GroupMark from './GroupMark.svelte';
  import { seek } from './commands.js';
  import { radio } from '../../lib/radio.js';
  import { quality } from './radio/words.js';
  import { RADIO } from './radio/glyphs.js';

  let { artwork = null, onartfailed, onsay, oneq, ongroup, onmark, onroom } = $props();

  const hasTrack = $derived(!!$active);
  const head = playhead(() => $metadata);
  const canSeek = $derived(hasTrack && head.hasPosition && $available.includes('seek'));
  //: A station that sends nothing has its name as the title and the album:
  //: once is enough.
  const byline = $derived([$metadata?.artist,
    $active === 'radio' && $metadata?.album === $metadata?.title ? null : $metadata?.album].filter(Boolean).join(' · '));

  const station = $derived($active === 'radio' ? ($radio?.station ?? null) : null);
  const status = $derived(station && ['reconnecting', 'not_answering'].includes($radio?.state) ? $radio.state : null);

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
  //: A scroll along the bar (lib/scrollSlide.js): 5 s a step, sought once
  //: the steps stop.
  const STEP_S = 5;
  let stepping = null;
  function seekStep(step) {
    const duration = head.duration ?? 0;
    if (!canSeek || seeking || !duration) return;
    clearTimeout(heldTimer);
    held = Math.max(0, Math.min(1, fraction + (step * STEP_S) / duration));
    clearTimeout(stepping);
    stepping = setTimeout(() => {
      stepping = null;
      seek(held * duration);
      heldTimer = setTimeout(() => (held = null), 1500);
    }, 400);
  }
  $effect(() => {
    void $metadata?.position;
    if (!seeking && !stepping && held !== null) {
      clearTimeout(heldTimer);
      heldTimer = setTimeout(() => (held = null), 200);
    }
  });
</script>

<div class="page">
  <div class="art">
    <div class="cover" class:is-dim={!!status}><RemoteCover {artwork} {hasTrack} big onfailed={onartfailed} /></div>
  </div>
  <div class="text">
    <span class="title" class:is-none={!hasTrack}>{hasTrack ? ($metadata?.title ?? 'Playing') : 'Nothing playing'}</span>
    {#if hasTrack && byline}<span class="by">{byline}</span>{/if}
    {#if station && quality(station)}<span class="quality">{quality(station)}</span>{/if}
  </div>
  {#if status}
    <div class="status" role="status">
      {#if status === 'reconnecting'}
        <svg class="status__turn" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d={RADIO.spinner} /></svg>
        Reconnecting <span class="status__try">try {$radio.attempt} of {$radio.tries}</span>
      {:else}
        <svg class="status__warn" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
          {#each RADIO.warn as d (d)}<path {d} />{/each}<circle cx="12" cy="16.9" r="0.6" />
        </svg>
        The station is not answering
      {/if}
    </div>
  {/if}
  <div class="played" class:is-idle={!hasTrack} inert={!hasTrack}>
    <div class="seek" class:can-seek={canSeek} role="slider" tabindex="-1" aria-label="Position"
         aria-valuemin="0" aria-valuemax={Math.round(head.duration ?? 0)} aria-valuenow={Math.round(fraction * (head.duration ?? 0))}
         aria-disabled={!canSeek} data-step={STEP_S} ondpadstep={(e) => seekStep(e.detail.step)}
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
  <div class="transport"><RemoteTransport big heart="start" {onsay} /></div>
  <div class="volume"><VolumeRow {oneq} {ongroup} {onsay} {onroom} /></div>
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
    color: var(--ink-quiet);
  }
  .cover.is-dim {
    opacity: 0.45;
  }
  .quality {
    max-width: 100%;
    margin-top: 2px;
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.04em;
    color: var(--ink-quiet);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .status {
    flex-shrink: 0;
    margin-top: 6px;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 700;
    color: var(--accent-warn);
  }
  .status svg {
    flex-shrink: 0;
    fill: none;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .status__turn {
    stroke-width: 3;
    animation: turn 1s linear infinite;
  }
  .status__warn {
    stroke-width: 2;
  }
  .status__warn circle {
    fill: currentColor;
  }
  .status__try {
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 400;
    color: var(--ink-muted);
  }
  @keyframes turn {
    to {
      transform: rotate(360deg);
    }
  }
  .by {
    max-width: 100%;
    font-size: 17px;
    color: var(--ink-muted);
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
    background: var(--c-ink-14);
  }
  .seek__track.is-live {
    background: linear-gradient(90deg, var(--c-ink-00), var(--c-ink-15) 16%, var(--c-ink-15) 84%, var(--c-ink-00));
  }
  .seek__fill {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    background: var(--accent-lms);
    display: block;
  }
  .seek__knob {
    position: absolute;
    top: 50%;
    width: 18px;
    height: 18px;
    margin: -9px 0 0 -9px;
    border-radius: 50%;
    background: var(--ink);
    box-shadow: 0 1px 4px var(--c-black-40);
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
    color: var(--ink-quiet);
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
