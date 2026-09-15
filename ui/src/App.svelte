<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Phase 4b skeleton, deliberately plain.

  This is NOT the now-playing screen. Its whole job is to prove the path
  works end to end - static files served by gexis-core, Svelte's compiled
  output loading under the panel's Chromium (ADR-0023's own open question),
  the store fed by the WebSocket, and reconnection surviving a daemon
  restart. It gets replaced wholesale in 4c when the designs arrive.

  It shows the raw payload on purpose: at this stage the useful thing on
  screen is what the daemon actually publishes, not a prettier version of
  it.
-->
<script>
  import { onMount } from 'svelte';
  import { connect, playback, connection } from './lib/state.js';

  onMount(connect);
</script>

<main>
  <header>
    <h1>gexis</h1>
    <span class="status" data-connection={$connection}>{$connection}</span>
  </header>

  {#if $playback}
    <dl>
      <dt>active</dt>
      <dd>{$playback.active ?? 'nobody'}</dd>
      <dt>transport</dt>
      <dd>{$playback.metadata?.transport ?? '—'}</dd>
      <dt>volume</dt>
      <dd>{$playback.volume ? `${$playback.volume.percent}% (${$playback.volume.db} dB)` : '—'}</dd>
      <dt>handoff</dt>
      <dd>{$playback.handoff ? `${$playback.handoff.from} → ${$playback.handoff.to}` : '—'}</dd>
    </dl>

    <pre>{JSON.stringify($playback, null, 2)}</pre>
  {:else}
    <p class="waiting">waiting for the first frame…</p>
  {/if}
</main>

<style>
  :global(body) {
    margin: 0;
    background: #121214;
    color: #e8e8ea;
    font: 16px/1.5 system-ui, sans-serif;
  }

  main {
    padding: 24px 32px;
  }

  header {
    display: flex;
    align-items: baseline;
    gap: 16px;
  }

  h1 {
    margin: 0;
    font-size: 28px;
    font-weight: 600;
    letter-spacing: 0.02em;
  }

  .status {
    font-size: 13px;
    padding: 2px 10px;
    border-radius: 999px;
    background: #2a2a30;
  }

  .status[data-connection='open'] {
    background: #1d3a24;
    color: #8fe0a2;
  }

  .status[data-connection='reconnecting'] {
    background: #3a2a1d;
    color: #e0b88f;
  }

  dl {
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 4px 20px;
    margin: 24px 0;
  }

  dt {
    color: #8b8b93;
  }

  pre {
    background: #1a1a1e;
    padding: 16px;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 13px;
  }

  .waiting {
    color: #8b8b93;
  }
</style>
