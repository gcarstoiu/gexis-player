<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script>
  import { onMount, untrack } from 'svelte';
  import { connect, active, metadata, volume, handoff, handoffExemptPairs, capabilities, available, availability, shuffle, repeat } from './lib/state.js';
  import NowPlaying from './screens/NowPlaying.svelte';
  import Library from './screens/Library.svelte';
  import PanelBackground from './screens/PanelBackground.svelte';
  import IdleScreen from './screens/IdleScreen.svelte';
  import VolumeDrawer from './screens/VolumeDrawer.svelte';
  import HandoffScreen from './screens/HandoffScreen.svelte';
  import Settings from './screens/Settings.svelte';
  import { loadSettings, settingValues } from './lib/settings.js';
  import { reportTouch, showPeppy } from './lib/state.js';

  // ADR-0033: idle is "not playing and not touched", one timeout everywhere.
  // From settings (idle_timeout, minutes); `?idle_seconds=` overrides it for testing.
  const IDLE_OVERRIDE_S = Number(new URLSearchParams(location.search).get('idle_seconds')) || null;
  const IDLE_MS = $derived((IDLE_OVERRIDE_S ?? ($settingValues.idle_timeout ?? 5) * 60) * 1000);

  let idle = $state(false);

  // Reported to the daemon at most once a second: it only needs to know the
  // panel was touched, not how often (ADR-0036).
  let lastReported = 0;
  function onPointerDown() {
    touches++;
    const now = Date.now();
    if (now - lastReported > 1000) {
      lastReported = now;
      reportTouch();
    }
  }
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

  // The library is a layer over now playing (source/Now Playing.dc.html). It
  // is Home, the no-renderer screen (ADR-0033), so it is always open while
  // nothing is connected; otherwise now playing's Home button opens it and
  // the mini strip closes it.
  let libraryRequested = $state(false);
  const libraryOpen = $derived(!$active || libraryRequested);
  let previousActive = null;
  $effect(() => {
    const now = $active;
    // A renderer arriving shows now playing (ADR-0033's assumption).
    if (previousActive === null && now !== null) untrack(() => (libraryRequested = false));
    previousActive = now;
  });

  // Settings is reached from the library root's card and nowhere else on the
  // panel (design/screens.md, Navigation); its Back closes it.
  let settingsOpen = $state(false);
  function openSettings() {
    closeVolume();
    settingsOpen = true;
  }

  const openVolume = () => {
    keepVolumeOpen();
    volumeOpen = true;
  };

  // ADR-0032: the panel renders everything; a remote browser only settings.
  let surface = $state(null);
  async function showVisualisation() {
    try {
      await showPeppy();
    } catch (err) {
      // 409 means the meter process is not running; the panel simply stays.
      console.info('visualisation unavailable:', err.message);
    }
  }

  onMount(() => {
    connect();
    loadSettings();
    fetch('/surface')
      .then((r) => r.json())
      .then((body) => (surface = body.surface))
      .catch(() => (surface = 'panel'));
  });
</script>

<svelte:window onpointerdowncapture={onPointerDown} />

{#if surface === 'remote'}
  <div class="remote"><Settings /></div>
{:else if surface === 'panel'}

<div class="panel">
  <!-- One backdrop for the whole panel, so a screen change does not build
       two large blurred layers again (George, 2026-09-17). Exactly one
       screen is mounted over it at a time: the screens are transparent now,
       so overlapping them would show both at once. -->
  <PanelBackground artwork={$metadata?.artwork ?? null} />

  <!-- No animation on a screen change at all (George, 2026-09-17). Over a
       shared backdrop the screens are transparent, so anything that fades
       one in or out shows the bare backdrop between them - which read as a
       blink on the panel, in both the two-way and the fade-in-only form.
       The backdrop does not move across a change, so the swap is the whole
       effect. The drawer, idle screen and handoff keep their own. -->
  {#if settingsOpen}
    <div class="screen-layer">
      <Settings onback={() => (settingsOpen = false)} embedded />
    </div>
  {:else if libraryOpen}
    <div class="screen-layer">
      <Library
        active={$active}
        metadata={$metadata}
        volume={$volume}
        controls={$active ? ($capabilities[$active]?.controls ?? []) : []}
        availability={$availability}
        onclose={() => (libraryRequested = false)}
        onsettings={openSettings}
        onvolume={openVolume}
      />
    </div>
  {:else if $active}
    <div class="screen-layer">
      <NowPlaying active={$active} metadata={$metadata} volume={$volume} controls={$capabilities[$active]?.controls ?? []} available={$available} shuffle={$shuffle} repeat={$repeat} onvolume={openVolume} onvisualisation={showVisualisation} onhome={() => (libraryRequested = true)} />
    </div>
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

  /* Above the panel's backdrop, below the volume drawer (12-13), the idle
     screen (20) and the handoff (30). The design puts settings at 42, which
     would cover the idle screen ADR-0033 puts over every screen. */
  .screen-layer {
    position: absolute;
    inset: 0;
    z-index: 5;
    overflow: hidden;
  }
</style>
