<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0164 D2: the Remote page of a player with a screen (design/source/21,
  *Remote page: a player with a screen*). Top to bottom: now playing - the
  cover, and beside it the title, the artist and the transport - the
  progress to read, the touch area, which takes the height that is left,
  the quick actions and the volume row. Shorter than the drawing, the touch
  area gives way to its floor (C10) before the page scrolls.
-->
<script>
  import { active, metadata } from '../../lib/state.js';
  import { playhead, mmss } from '../../lib/playhead.svelte.js';
  import RemoteCover from './RemoteCover.svelte';
  import RemoteTransport from './RemoteTransport.svelte';
  import TouchArea from './TouchArea.svelte';
  import QuickActions from './QuickActions.svelte';
  import VolumeRow from './VolumeRow.svelte';
  import GroupMark from './GroupMark.svelte';

  let { artwork = null, onartfailed, pad, onpad, padSwitch, socket, onok, ontap, onsay, oneq, ongroup, onmark } = $props();

  const hasTrack = $derived(!!$active);
  const head = playhead(() => $metadata);
</script>

<div class="page">
  <div class="now">
    <div class="cover"><RemoteCover {artwork} {hasTrack} onfailed={onartfailed} /></div>
    <div class="side">
      <div class="text">
        <span class="title" class:is-none={!hasTrack}>{hasTrack ? ($metadata?.title ?? 'Playing') : 'Nothing playing'}</span>
        {#if hasTrack && $metadata?.artist}<span class="artist">{$metadata.artist}</span>{/if}
      </div>
      <RemoteTransport />
    </div>
  </div>

  <!-- ADR-0166 (3a): the grouped mark, under the transport row, above the
       progress bar. -->
  <GroupMark onopen={onmark} gap={12} after={-2} height={18} />
  <div class="progress" class:is-idle={!hasTrack}>
    <div class="bar" class:is-live={hasTrack && !head.hasPosition}>
      {#if hasTrack && head.hasPosition}<div class="bar__fill" style:width={`${head.percent}%`}></div>{/if}
    </div>
    <div class="times">
      <span>{!hasTrack ? '0:00' : head.hasPosition ? mmss(head.elapsed) : mmss($metadata?.position ?? 0)}</span>
      <span>{!hasTrack ? '0:00' : head.hasPosition ? mmss(head.duration) : 'live'}</span>
    </div>
  </div>

  <TouchArea {pad} {onpad} {padSwitch} {socket} {onok} {ontap} {onsay} />
  <QuickActions {onsay} />
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
  .now {
    flex-shrink: 0;
    display: flex;
    gap: 16px;
  }
  /* The cover gives way first on a narrow phone, to 96 (the design's). */
  .cover {
    width: var(--remote-cover);
    min-width: 96px;
    aspect-ratio: 1 / 1;
    align-self: flex-start;
    flex-shrink: 1;
  }
  .side {
    flex: 1 0 168px;
    min-width: 168px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 10px;
    padding: 2px 0;
  }
  .text {
    display: flex;
    flex-direction: column;
    gap: 3px;
    min-width: 0;
  }
  .title {
    font-size: 20px;
    font-weight: 700;
    line-height: 1.2;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    overflow-wrap: anywhere;
  }
  .title.is-none {
    color: rgba(233, 238, 242, 0.6);
  }
  .artist {
    font-size: 15px;
    color: rgba(233, 238, 242, 0.72);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .progress {
    flex-shrink: 0;
    margin-top: 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .progress.is-idle {
    opacity: 0.38;
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
    line-height: 16px;
    color: rgba(233, 238, 242, 0.6);
  }
  .volume {
    margin-top: 12px;
    flex-shrink: 0;
  }
</style>
