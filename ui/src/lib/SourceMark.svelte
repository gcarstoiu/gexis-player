<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  A renderer's mark at a given size: the design's sourceIcon(). Lyrion below
  40px is its four-bar reduction, because the ten-bar SVG antialiases to a
  smear there; Spotify and Bluetooth are their image marks, Bluetooth drawn
  12% taller as the design does.
-->
<script>
  import spotifyMark from '../assets/icon-spotify.png';
  import bluetoothMark from '../assets/icon-bluetooth.png';

  let { source, size = 18, color = 'currentColor', opacity = 1 } = $props();

  const bar = $derived(Math.max(3, Math.round(size * 0.15)));
  const gap = $derived(Math.max(2, Math.round(size * 0.11)));
</script>

{#if source === 'lms'}
  <span class="bars" style:height={`${size}px`} style:gap={`${gap}px`} style:opacity>
    {#each [0.5, 1, 0.72, 0.88] as h}
      <i style:width={`${bar}px`} style:height={`${Math.round(size * h)}px`} style:background={color}></i>
    {/each}
  </span>
{:else if source === 'spotify' || source === 'bluetooth'}
  <img
    class="mark"
    src={source === 'bluetooth' ? bluetoothMark : spotifyMark}
    alt=""
    style:height={`${source === 'bluetooth' ? size * 1.12 : size}px`}
    style:opacity
  />
{/if}

<style>
  .bars {
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }
  .bars i {
    border-radius: 2px;
    flex-shrink: 0;
  }
  .mark {
    width: auto;
    flex-shrink: 0;
    display: block;
  }
</style>
