<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script>
  import { onMount, untrack } from 'svelte';
  import { connect, active, metadata, volume, handoff, handoffExemptPairs, capabilities, available, availability, shuffle, repeat, queue, pairing, fixedOutput } from './lib/state.js';
  import NowPlaying from './screens/NowPlaying.svelte';
  import Library from './screens/Library.svelte';
  import WaitingHome from './screens/WaitingHome.svelte';
  import PanelBackground from './screens/PanelBackground.svelte';
  import IdleScreen from './screens/IdleScreen.svelte';
  import VolumeDrawer from './screens/VolumeDrawer.svelte';
  import HandoffScreen from './screens/HandoffScreen.svelte';
  import PairingFrame from './screens/PairingFrame.svelte';
  import Settings from './screens/Settings.svelte';
  import { loadSettings, settingValues } from './lib/settings.js';
  import { loadLibraryRoot } from './lib/library.js';
  import { reportTouch, showPeppy, reportPainted } from './lib/state.js';

  // ADR-0033: idle is "not playing and not touched", one timeout everywhere.
  // From settings (idle_timeout, minutes); `?idle_seconds=` overrides it for testing.
  const IDLE_OVERRIDE_S = Number(new URLSearchParams(location.search).get('idle_seconds')) || null;
  const IDLE_MS = $derived((IDLE_OVERRIDE_S ?? ($settingValues.idle_timeout ?? 5) * 60) * 1000);

  let idle = $state(false);

  // Reported to the daemon at most once a second: it only needs to know the
  // panel was touched, not how often (ADR-0036).
  //
  // **Only from the panel.** A touch is what ADR-0036 counts as attention,
  // and attention takes the visualiser down - so a tap on a phone's settings
  // screen was ending the visualisation on a device in another room, which
  // is exactly the case the phone exists for (George, 2026-09-22: changing
  // the skin *"stops showing the visualisation. It should stay on"*). The
  // daemon cannot see the glass, which is why the panel reports at all; a
  // remote browser is not the glass.
  let lastReported = 0;
  function onPointerDown() {
    touches++;
    if (surface !== 'panel') return;
    const now = Date.now();
    if (now - lastReported > 1000) {
      lastReported = now;
      reportTouch();
    }
  }
  //: Set when now playing's artist line is tapped: the library opens
  //: on that artist rather than at its root.
  let libraryArtist = $state(null);

  let volumeOpen = $state(false);

  // Criterion 4: shown for the takeover itself unless the pair is measured
  // fast enough to be exempt, and held long enough not to flash.
  //
  // **Both are settings now** (ADR-0022's `show_transition` and
  // `handoff_duration`, wired 2026-09-25). The fallback is the 1.4s this
  // shipped with, so wiring the row changed nothing until somebody moves
  // it - the registry's own default was raised to match rather than the
  // screen being quietly lengthened.
  const HANDOFF_MIN_MS = $derived(($settingValues.handoff_duration ?? 1.4) * 1000);
  // **ADR-0078: the threshold is how long a takeover has to be in flight
  // before the panel explains it.** ADR-0010 set 1s and nothing ever read it -
  // the exempt list was compared against it once, by hand. A takeover that
  // finishes inside the wait is never announced, which is what stops the
  // screen being "a flicker - noise, not information". 0 announces every one
  // immediately, exactly as this behaved before.
  const HANDOFF_WAIT_MS = $derived(($settingValues.handoff_threshold ?? 1) * 1000);
  let shownHandoff = $state.raw(null);
  let handoffShownAt = 0;
  // Two timers, not one: the wait before the screen appears and the hold that
  // stops it flashing are both in flight at different moments, and a single
  // handle let the hold cancel a wait that had not fired yet.
  let handoffWait;
  let handoffTimer;
  $effect(() => {
    const h = $handoff;
    const exempt = h && $handoffExemptPairs.some(([a, b]) => a === h.from && b === h.to);
    untrack(() => {
      clearTimeout(handoffTimer);
      if ($settingValues.show_transition === false) {
        clearTimeout(handoffWait);
        shownHandoff = null;
        return;
      }
      if (h && !exempt) {
        if (shownHandoff) {
          // Already up: a second takeover replaces what it says rather than
          // restarting the wait.
          shownHandoff = h;
          return;
        }
        clearTimeout(handoffWait);
        const show = () => {
          handoffShownAt = performance.now();
          shownHandoff = h;
        };
        if (HANDOFF_WAIT_MS <= 0) show();
        else handoffWait = setTimeout(show, HANDOFF_WAIT_MS);
      } else {
        // The takeover is over. Anything still waiting is cancelled - it
        // finished inside the threshold and is not announced at all.
        clearTimeout(handoffWait);
        if (shownHandoff) {
          const remaining = HANDOFF_MIN_MS - (performance.now() - handoffShownAt);
          handoffTimer = setTimeout(() => (shownHandoff = null), Math.max(0, remaining));
        }
      }
    });
  });

  // **The drawer closes itself 3 s after volume activity stops, however it
  // was opened** (ADR-0022's row, as George found it should behave on
  // 2026-09-23). It is pinned only while a finger is actually on it.
  const AUTO_HIDE_MS = $derived(($settingValues.drawer_autohide ?? 3) * 1000);
  let autoHide = null;
  function openFromExternal() {
    if ($settingValues.drawer_on_external === false) return;
    volumeOpen = true;
    armAutoHide();
  }
  // Held open only while a finger is on it. It used to be held open by the
  // *first* touch and never released, so a drag on the panel's own slider
  // left the drawer up indefinitely and no later change from elsewhere
  // could arm the timer either - `openFromExternal` returned early for a
  // drawer in that state (George, 2026-09-23).
  function keepVolumeOpen() {
    clearTimeout(autoHide);
    autoHide = null;
  }
  function armAutoHide() {
    clearTimeout(autoHide);
    autoHide = setTimeout(closeVolume, AUTO_HIDE_MS);
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

  //: **A takeover wakes the panel** (George, 2026-09-26, reproduced: *"when
  //: plexamp takes over, idle screen doesn't go away"*, and then *"the idle
  //: screen was shown then the transition screen and then the idle I think and
  //: then now playing"*).
  //:
  //: Until this, `idle` was cleared by exactly one thing - a renderer reporting
  //: `playing` - and a takeover can be a long way from that. Measured on the
  //: panel: starting Plexamp from idle left the idle screen up for **2.1 s**,
  //: and activating LMS while Plexamp held the device left it up for the whole
  //: **30 s** the probe watched, because the incoming renderer was paused and
  //: never said `playing` at all. The handoff screen draws *over* the idle one,
  //: which is the flicker George described: idle, transition, idle again.
  //:
  //: **A renderer taking the device is attention** - ADR-0027 makes every
  //: acquisition a deliberate act, so somebody just did something. Counted as a
  //: touch as well as cleared, exactly as the pairing frame below is, so the
  //: panel does not drop back to idle the moment the takeover finishes.
  //:
  //: `untrack` for the same reason it is used below: `touches += 1` reads
  //: `touches`, and without it the effect depends on what it writes.
  $effect(() => {
    const who = $active;
    const takeover = $handoff;
    if (who === null && !takeover) return;
    untrack(() => {
      idle = false;
      touches += 1;
    });
  });

  //: **A pairing request wakes the panel.** It lapses in thirty seconds and
  //: a question nobody can see cannot be answered - and the frame is only
  //: 95% opaque, so over the idle screen the clock reads through it
  //: (George, on the panel, 2026-09-21). Counted as attention as well as
  //: dismissed, so the panel does not drop straight back to idle the moment
  //: the frame closes: after pairing, the thing you just connected is the
  //: thing you want to look at.
  //:
  //: **`untrack` is load-bearing.** `touches += 1` *reads* `touches` to
  //: increment it, so without this the effect depends on what it writes and
  //: re-triggers itself - Svelte raises `effect_update_depth_exceeded` and
  //: the whole tree stops updating. It only fires when a request arrives,
  //: so it survived every other deploy and showed up as a pairing frame
  //: with a frozen countdown whose buttons appeared dead (George, on the
  //: panel, 2026-09-21). The answers were landing; nothing was re-rendering.
  $effect(() => {
    if (!$pairing) return;
    untrack(() => {
      idle = false;
      touches += 1;
    });
  });

  // The library is a layer over now playing (source/Now Playing.dc.html). It
  // is Home, the no-renderer screen (ADR-0033), so it is always open while
  // nothing is connected; otherwise now playing's Home button opens it and
  // the mini strip closes it.
  let libraryRequested = $state(false);
  // **ADR-0079: with LMS off there is no library, so the panel is two
  // screens.** Nothing playing is the waiting marks; something playing is now
  // playing, as the root.
  //
  // **The row decides it, not `availability.lms`.** Availability is also false
  // when the server is merely unreachable, and a library that vanished on a
  // Wi-Fi blip and grew back a few seconds later would be two different
  // products in one minute. A row somebody set is a stable fact.
  const lmsOff = $derived($settingValues.lms_enabled === false);
  const libraryOpen = $derived(!lmsOff && (!$active || libraryRequested));
  const waitingOpen = $derived(lmsOff && !$active);
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
  // A reopen refreshes quietly: what is on screen stays until the new
  // read, with its covers, is ready to replace it.
  $effect(() => {
    if (libraryOpen) untrack(() => loadLibraryRoot());
  });

  function openSettings() {
    closeVolume();
    settingsOpen = true;
  }

  const openVolume = () => {
    armAutoHide();
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
    // Ahead of the first time Home opens (see lib/library.js). Not with LMS
    // off: there is no home to be ahead of, and the read would be three
    // requests to a server this device is not using (ADR-0079).
    if ($settingValues.lms_enabled !== false) loadLibraryRoot();
    fetch('/surface')
      .then((r) => r.json())
      .then((body) => (surface = body.surface))
      .catch(() => (surface = 'panel'));

    // ADR-0043: end the boot animation only once something is actually on
    // the glass. onMount runs before the browser has painted, so this waits
    // for the frame after the one being composed now - two rAFs, which is
    // the earliest point at which a pixel of this app has been presented.
    requestAnimationFrame(() => requestAnimationFrame(reportPainted));
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
  {:else if waitingOpen}
    <div class="screen-layer">
      <WaitingHome availability={$availability} onsettings={openSettings} />
    </div>
  {:else if libraryOpen}
    <div class="screen-layer">
      <Library
        active={$active}
        metadata={$metadata}
        volume={$volume}
        controls={$active ? ($capabilities[$active]?.controls ?? []) : []}
        availability={$availability}
        openArtistNamed={libraryArtist}
        onclose={() => { libraryRequested = false; libraryArtist = null; }}
        onsettings={openSettings}
        onvolume={openVolume}
      />
    </div>
  {:else if $active}
    <div class="screen-layer">
      <!-- ADR-0079: with LMS off the Home button is a Settings button and
           `onartist` is not passed at all, so the artist line is a name rather
           than a link that leads nowhere. -->
      <NowPlaying active={$active} metadata={$metadata} volume={$volume} controls={$capabilities[$active]?.controls ?? []} available={$available} shuffle={$shuffle} repeat={$repeat} queue={$queue} onvolume={openVolume} onvisualisation={showVisualisation}
        rootless={lmsOff}
        onhome={lmsOff ? openSettings : () => (libraryRequested = true)}
        onartist={lmsOff ? undefined : (name) => { libraryArtist = name; libraryRequested = true; }} />
    </div>
  {/if}

  <!-- ADR-0046: **mounted in fixed output too, with no level to show.**
       The drawer is where the sentence lives - "the answer is where the
       question is asked" - and `{#if $volume}` alone left the padlock
       opening nothing at all. -->
  {#if $volume || $fixedOutput}
    <VolumeDrawer
      open={volumeOpen}
      volume={$volume}
      active={$active}
      onclose={closeVolume}
      onexternal={openFromExternal}
      onactivity={keepVolumeOpen}
      onsettled={armAutoHide}
    />
  {/if}

  {#if idle}
    <!-- ADR-0047: the screen reads eight rows, so it takes the values
         rather than fetching /settings for itself - one loader, one place
         a revision bump lands. -->
    <IdleScreen ondismiss={() => (idle = false)} settings={$settingValues} />
  {/if}

  {#if shownHandoff}
    <HandoffScreen from={shownHandoff.from} to={shownHandoff.to} />
  {/if}

  <!-- Last, and above everything (ADR-0045). A request that cannot be seen
       cannot be answered, and it lapses in thirty seconds either way - so it
       takes the screen from the visualiser or the idle screen rather than
       waiting politely behind them. It is also the only layer here with no
       dismiss of its own: the agent takes it away. -->
  {#if $pairing}
    <PairingFrame request={$pairing} />
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
