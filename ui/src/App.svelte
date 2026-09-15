<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script>
  import { onMount } from 'svelte';
  import { connect, active, metadata, volume } from './lib/state.js';
  import NowPlaying from './screens/NowPlaying.svelte';
  import IdleScreen from './screens/IdleScreen.svelte';
  import VolumeDrawer from './screens/VolumeDrawer.svelte';

  // ADR-0033: idle is "not playing and not touched", one timeout everywhere.
  // Hardcoded until settings exist; `?idle_seconds=` shortens it for testing.
  const IDLE_MS = (Number(new URLSearchParams(location.search).get('idle_seconds')) || 300) * 1000;

  let idle = $state(false);
  let volumeOpen = $state(false);

  // Opened by a change from elsewhere, the drawer closes itself once volume
  // activity stops; opened by the panel's own button, it stays until closed.
  const AUTO_HIDE_MS = 3000;
  let autoHide = null;
  function openFromExternal() {
    if (volumeOpen && autoHide === null) return;
    volumeOpen = true;
    clearTimeout(autoHide);
    autoHide = setTimeout(closeVolume, AUTO_HIDE_MS);
  }
  function keepVolumeOpen() {
    clearTimeout(autoHide);
    autoHide = null;
  }
  function closeVolume() {
    keepVolumeOpen();
    volumeOpen = false;
  }
  let touches = $state(0);
  const playing = $derived($active !== null && $metadata?.transport === 'playing');

  $effect(() => {
    touches;
    if (playing) {
      idle = false;
      return;
    }
    const id = setTimeout(() => (idle = true), IDLE_MS);
    return () => clearTimeout(id);
  });

  onMount(connect);
</script>

<svelte:window onpointerdowncapture={() => touches++} />

<div class="panel">
  {#if $active}
    <NowPlaying active={$active} metadata={$metadata} volume={$volume} onvolume={() => { keepVolumeOpen(); volumeOpen = true; }} />
  {:else}
    <!-- Home (ADR-0033) is the no-renderer screen; its content is Phase 7. -->
    <div class="placeholder" data-unwired="home">Nothing playing</div>
  {/if}

  {#if $volume}
    <VolumeDrawer
      open={volumeOpen}
      volume={$volume}
      active={$active}
      onclose={closeVolume}
      onexternal={openFromExternal}
      onactivity={keepVolumeOpen}
    />
  {/if}

  {#if idle}
    <IdleScreen ondismiss={() => (idle = false)} />
  {/if}
</div>

<style>
  :global(*, *::before, *::after) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    background: var(--bg-base);
    font-family: var(--font-ui);
    color: var(--ink);
    -webkit-tap-highlight-color: transparent;
  }

  .panel {
    position: relative;
    width: 1280px;
    height: 800px;
    overflow: hidden;
  }

  .placeholder {
    width: 1280px;
    height: 800px;
    display: grid;
    place-items: center;
    font-family: var(--font-mono);
    font-size: var(--t-label);
    letter-spacing: var(--track-label);
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
</style>
