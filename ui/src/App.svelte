<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script>
  import { onMount } from 'svelte';
  import { connect, active, metadata, volume } from './lib/state.js';
  import NowPlaying from './screens/NowPlaying.svelte';

  onMount(connect);
</script>

{#if $active}
  <NowPlaying active={$active} metadata={$metadata} volume={$volume} />
{:else}
  <!-- Home (ADR-0033) is the no-renderer screen; its content is Phase 7. -->
  <div class="placeholder" data-unwired="home">Nothing playing</div>
{/if}

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
