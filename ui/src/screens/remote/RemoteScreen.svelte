<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0164 D2: the Remote page of a player with a screen (design/source/21,
  *Remote page: a player with a screen*). Top to bottom: now playing - the
  cover, the track, a progress bar to read and the transport - the touch
  area, which takes the height that is left, the quick actions and the
  volume row.
-->
<script>
  import { active, metadata } from '../../lib/state.js';
  import { playhead, mmss } from '../../lib/playhead.svelte.js';
  import RemoteTransport from './RemoteTransport.svelte';
  import TouchArea from './TouchArea.svelte';
  import QuickActions from './QuickActions.svelte';
  import VolumeRow from './VolumeRow.svelte';
  import { FILLED } from './icons.js';

  let { pad, onpad, padSwitch, socket, onok, ontouch, onsay, oneq } = $props();

  const hasTrack = $derived(!!$active);
  let failed = $state(null);
  const artwork = $derived($metadata?.artwork && $metadata.artwork !== failed ? $metadata.artwork : null);
  const head = playhead(() => $metadata);
</script>

<div class="page">
  <div class="now">
    <div class="track">
      <div class="cover">
        {#if hasTrack && artwork}
          <img src={artwork} alt="" onerror={() => (failed = artwork)} />
        {:else}
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.note} /></svg>
        {/if}
      </div>
      <div class="text">
        <span class="title" class:is-none={!hasTrack}>{hasTrack ? ($metadata?.title ?? 'Playing') : 'Nothing playing'}</span>
        {#if hasTrack}
          {#if $metadata?.artist}<span class="artist">{$metadata.artist}</span>{/if}
          {#if $metadata?.album}<span class="album">{$metadata.album}</span>{/if}
        {/if}
      </div>
    </div>
    {#if hasTrack}
      <div class="progress">
        <div class="bar" class:is-live={!head.hasPosition}>
          {#if head.hasPosition}<div class="bar__fill" style:width={`${head.percent}%`}></div>{/if}
        </div>
        <div class="times">
          <span>{head.hasPosition ? mmss(head.elapsed) : mmss($metadata?.position ?? 0)}</span>
          <span>{head.hasPosition ? mmss(head.duration) : 'live'}</span>
        </div>
      </div>
    {/if}
    <RemoteTransport />
  </div>

  <TouchArea {pad} {onpad} {padSwitch} {socket} {onok} {ontouch} {onsay} />
  <QuickActions {onsay} {ontouch} />
  <div class="volume"><VolumeRow {oneq} {onsay} /></div>
</div>

<style>
  .page {
    height: 100%;
    box-sizing: border-box;
    padding: 0 16px 16px;
    display: flex;
    flex-direction: column;
  }
  .now {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .track {
    display: flex;
    gap: 16px;
    align-items: stretch;
  }
  .cover {
    position: relative;
    width: 168px;
    height: 168px;
    border-radius: 20px;
    overflow: hidden;
    background: rgba(233, 238, 242, 0.07);
    display: grid;
    place-items: center;
    flex-shrink: 0;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
    color: rgba(233, 238, 242, 0.5);
  }
  .cover img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
  .cover svg {
    width: 48px;
    height: 48px;
    fill: currentColor;
  }
  .text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    gap: 4px;
    padding-bottom: 4px;
  }
  .title {
    font-size: 22px;
    font-weight: 700;
    line-height: 1.2;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    overflow-wrap: anywhere;
  }
  .title.is-none {
    color: rgba(233, 238, 242, 0.6);
  }
  .artist,
  .album {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    overflow-wrap: anywhere;
  }
  .artist {
    font-size: 16px;
    color: rgba(233, 238, 242, 0.72);
  }
  .album {
    font-size: 14px;
    color: rgba(233, 238, 242, 0.6);
  }
  .progress {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .bar {
    position: relative;
    height: 4px;
    border-radius: 2px;
    overflow: hidden;
    background: rgba(233, 238, 242, 0.14);
  }
  /* No duration (Bluetooth, a live stream): the design's inert rule. */
  .bar.is-live {
    background: linear-gradient(90deg, rgba(233, 238, 242, 0), rgba(233, 238, 242, 0.15) 16%, rgba(233, 238, 242, 0.15) 84%, rgba(233, 238, 242, 0));
  }
  .bar__fill {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    background: #7ed6bc;
  }
  .times {
    display: flex;
    justify-content: space-between;
    font-family: var(--font-mono);
    font-size: 12px;
    color: rgba(233, 238, 242, 0.6);
  }
  .volume {
    margin-top: 12px;
    flex-shrink: 0;
  }
</style>
