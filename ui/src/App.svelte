<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script>
  import { onMount, untrack } from 'svelte';
  import { connect, active, metadata, volume, handoff, handoffExemptPairs } from './lib/state.js';
  import NowPlaying from './screens/NowPlaying.svelte';
  import IdleScreen from './screens/IdleScreen.svelte';
  import VolumeDrawer from './screens/VolumeDrawer.svelte';
  import HandoffScreen from './screens/HandoffScreen.svelte';
  import Settings from './screens/Settings.svelte';
  import { loadSettings, settingValues } from './lib/settings.js';

  // ADR-0033: idle is "not playing and not touched", one timeout everywhere.
  // From settings (idle_timeout, minutes); `?idle_seconds=` overrides it for testing.
  const IDLE_OVERRIDE_S = Number(new URLSearchParams(location.search).get('idle_seconds')) || null;
  const IDLE_MS = $derived((IDLE_OVERRIDE_S ?? ($settingValues.idle_timeout ?? 5) * 60) * 1000);

  let idle = $state(false);
  let volumeOpen = $state(false);

  // Criterion 4: shown for the takeover itself unless the pair is measured
  // fast enough to be exempt, and held long enough not to flash.
  const HANDOFF_MIN_MS = 1400;
  let shownHandoff = $state.raw(null);
  let handoffShownAt = 0;
  let handoffTimer;
  $effect(() => {
    const h = $handoff;
    const exempt = h && $handoffExemptPairs.some(([a, b]) => a === h.from && b === h.to);
    untrack(() => {
      clearTimeout(handoffTimer);
      if (h && !exempt) {
        if (!shownHandoff) handoffShownAt = performance.now();
        shownHandoff = h;
      } else if (shownHandoff) {
        const remaining = HANDOFF_MIN_MS - (performance.now() - handoffShownAt);
        handoffTimer = setTimeout(() => (shownHandoff = null), Math.max(0, remaining));
      }
    });
  });

  // Opened by a change from elsewhere, the drawer closes itself once volume
  // activity stops; opened by the panel's own button, it stays until closed.
  const AUTO_HIDE_MS = $derived(($settingValues.drawer_autohide ?? 3) * 1000);
  let autoHide = null;
  function openFromExternal() {
    if ($settingValues.drawer_on_external === false) return;
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

  // ADR-0032: the panel renders everything; a remote browser only settings.
  let surface = $state(null);
  onMount(() => {
    connect();
    loadSettings();
    fetch('/surface')
      .then((r) => r.json())
      .then((body) => (surface = body.surface))
      .catch(() => (surface = 'panel'));
  });
</script>

<svelte:window onpointerdowncapture={() => touches++} />

{#if surface === 'remote'}
  <div class="remote"><Settings /></div>
{:else if surface === 'panel'}

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

  {#if shownHandoff}
    <HandoffScreen from={shownHandoff.from} to={shownHandoff.to} />
  {/if}
</div>
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

  :global(html),
  :global(body),
  :global(#app) {
    height: 100%;
  }

  .remote {
    height: 100%;
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
