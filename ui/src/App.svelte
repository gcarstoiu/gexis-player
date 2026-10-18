<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script>
  import { onMount, untrack } from 'svelte';
  import { connect, active, metadata, volume, handoff, capabilities, available, availability, shuffle, repeat, queue, pairing, fixedOutput, panel, setup, personalise, personaliseLater } from './lib/state.js';
  import NowPlaying from './screens/NowPlaying.svelte';
  import BarNowPlaying from './screens/bar/BarNowPlaying.svelte';
  import BarTray from './screens/bar/BarTray.svelte';
  import Library from './screens/Library.svelte';
  import BarLibrary from './screens/bar/BarLibrary.svelte';
  import WaitingHome from './screens/WaitingHome.svelte';
  import PanelBackground from './screens/PanelBackground.svelte';
  import IdleScreen from './screens/IdleScreen.svelte';
  import VolumeDrawer from './screens/VolumeDrawer.svelte';
  import HandoffScreen from './screens/HandoffScreen.svelte';
  import PairingFrame from './screens/PairingFrame.svelte';
  import Settings from './screens/Settings.svelte';
  import MiniPlayer from './screens/MiniPlayer.svelte';
  import SetupScreen from './screens/SetupScreen.svelte';
  import FirstUsePage from './screens/FirstUsePage.svelte';
  import { screen } from './lib/family.svelte.js';
  import UpdateScreen from './screens/UpdateScreen.svelte';
  import PanelPointer from './lib/PanelPointer.svelte';
  import { update, updateAsked, connection, hidePeppy, screenConfirm, answerScreen, screenNew, answerNewScreen, screenCheck, sendScreenCheck } from './lib/state.js';
  import TestPattern from './screens/TestPattern.svelte';
  import SettlingScreen from './screens/SettlingScreen.svelte';
  import ResetScreen from './screens/ResetScreen.svelte';
  import CableKeep from './screens/CableKeep.svelte';
  import { settling, settlingDone, settlingHide, resetting } from './lib/state.js';
  import KeepScreen from './screens/KeepScreen.svelte';
  import PhoneKeepScreen from './screens/PhoneKeepScreen.svelte';
  import NewScreen from './screens/NewScreen.svelte';
  import { loadSettings, settingValues, settingsDevice } from './lib/settings.js';
  import { loadLibraryRoot } from './lib/library.js';
  import { reportTouch, showPeppy, reportPainted, reportShown } from './lib/state.js';
  import { lyricsAsk, lyricsShown } from './lib/panelView.js';

  //: The browser tab says which player it is (George, 2026-10-10: with
  //: several players open in tabs "it is hard to distinguish between the
  //: tabs"). Its name as Settings shows it; "gexis" until it is known.
  $effect(() => {
    document.title = $settingsDevice.name || 'gexis';
  });

  // ADR-0033: idle is "not playing and not touched", one timeout everywhere.
  // From settings (idle_timeout, minutes); `?idle_seconds=` overrides it for testing.
  const IDLE_OVERRIDE_S = Number(new URLSearchParams(location.search).get('idle_seconds')) || null;
  const idleOn = $derived($settingValues.idle_enabled === true);
  const IDLE_MS = $derived((IDLE_OVERRIDE_S ?? ($settingValues.idle_timeout ?? 5) * 60) * 1000);

  let idle = $state(false);
  //: **ADR-0101: asked for from a phone.** An idle screen somebody asked for
  //: stays up while music plays, until it is turned off or the panel is
  //: touched - the ask is explicit, which is why it beats ADR-0033's "not
  //: playing".
  let askedIdle = $state(false);

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

  // **Every takeover is shown, however quick, for the length the user set**
  // (ADR-0094, George 2026-09-26: *"handoff visualisation is to be shown at
  // all times even when the takeover is nearly instantaneous. The length of
  // the visualisation is to be dictated by the Transition screen length
  // setting"*). This replaced ADR-0078's threshold - a takeover that finished
  // inside it was never announced - and ADR-0010's list of pairs exempt for
  // being fast. A takeover still in flight when the length runs out keeps the
  // screen up until it finishes. Nothing here touches the takeover itself.
  const HANDOFF_MIN_MS = $derived(($settingValues.handoff_duration ?? 1.5) * 1000);
  let shownHandoff = $state.raw(null);
  let handoffShownAt = 0;
  let handoffTimer;
  $effect(() => {
    const h = $handoff;
    untrack(() => {
      clearTimeout(handoffTimer);
      if ($settingValues.show_transition === false) {
        shownHandoff = null;
        return;
      }
      if (h) {
        // A second takeover while the screen is up replaces what it says
        // without restarting the clock.
        if (!shownHandoff) handoffShownAt = performance.now();
        shownHandoff = h;
      } else if (shownHandoff) {
        const remaining = HANDOFF_MIN_MS - (performance.now() - handoffShownAt);
        handoffTimer = setTimeout(() => (shownHandoff = null), Math.max(0, remaining));
      }
    });
  });

  // **The drawer closes itself 3 s after volume activity stops, however it
  // was opened** (ADR-0022's row, as George found it should behave on
  // 2026-09-23). It is pinned only while a finger is actually on it.
  const AUTO_HIDE_MS = $derived(($settingValues.drawer_autohide ?? 3) * 1000);
  let autoHide = null;
  //: **A drawer that opened by itself takes no touch at first** (code
  //: review, 2026-10-12). A change from a phone opens it over whatever is on
  //: the panel, taking touches while it is still fading in: a tap meant for
  //: an album card under the slider set the level at that point, near 100%
  //: from the right of the card. Until this long after such an opening the
  //: level and mute take nothing; someone who meant the slider has not yet
  //: seen it.
  const VOLUME_ARM_MS = 400;
  let volumeArmsAt = $state(0);
  function openFromExternal() {
    if ($settingValues.drawer_on_external === false) return;
    if (!volumeOpen) volumeArmsAt = performance.now() + VOLUME_ARM_MS;
    volumeOpen = true;
    armAutoHide();
  }
  // Held open only while a finger is on it. It used to be held open by the
  // *first* touch and never released, so a drag on the panel's own slider
  // left the drawer up indefinitely and no later change from elsewhere
  // could arm the timer either - `openFromExternal` returned early for a
  // drawer in that state (George, 2026-09-23).
  //
  // **And while the phone's pointer rests on it** (ADR-0121; George,
  // 2026-10-05: "while the cursor is above the modal, it should not be
  // dismissed"): the pointer entering holds it, leaving lets the timer run.
  // A tap made there lifts like a finger, which alone would arm the timer.
  let pointerOver = false;
  function keepVolumeOpen(event) {
    if (event?.type === 'pointerenter' && event.pointerType === 'mouse') pointerOver = true;
    clearTimeout(autoHide);
    autoHide = null;
  }
  function armAutoHide(event) {
    if (event?.type === 'pointerleave' && event.pointerType === 'mouse') pointerOver = false;
    if (pointerOver) return;
    clearTimeout(autoHide);
    autoHide = setTimeout(closeVolume, AUTO_HIDE_MS);
  }
  function closeVolume() {
    pointerOver = false;
    keepVolumeOpen();
    volumeOpen = false;
  }
  let touches = $state(0);
  const playing = $derived($active !== null && $metadata?.transport === 'playing');

  $effect(() => {
    touches;
    // **No idle screen while setup is showing** (George, 2026-09-28: the
    // clock appeared at the end of setup, "completely out of place"). The
    // timer ran under the setup screen, and whoever finished setup on the
    // phone had not touched the panel for minutes.
    if (setupShown) {
      untrack(() => { idle = false; askedIdle = false; });
      return;
    }
    // **The idle screen can be off** (ADR-0133 amended 2026-10-11, second;
    // off on a new player): the panel then stays on what it shows.
    if (!idleOn) {
      untrack(() => { idle = false; askedIdle = false; });
      return;
    }
    if (playing) {
      if (!untrack(() => askedIdle)) idle = false;
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
      askedIdle = false;
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
      askedIdle = false;
      touches += 1;
    });
  });

  //: **ADR-0101: the phone's idle toggle.** Each ask is numbered and applied
  //: once; one older than a minute is history, not an ask (a panel that
  //: reloads must not replay it). Hiding it is attention like a touch, so
  //: the countdown restarts from that moment (George: "Timers would restart
  //: from that point").
  let appliedIdleAsk = null;
  $effect(() => {
    const ask = $panel.idle_request;
    if (surface !== 'panel' || !ask || ask.seq === appliedIdleAsk) return;
    appliedIdleAsk = ask.seq;
    if (ask.at && Date.now() / 1000 - ask.at > 60) return;
    untrack(() => {
      idle = ask.show && idleOn;
      askedIdle = ask.show && idleOn;
      if (!ask.show) touches += 1;
    });
  });

  //: The panel has one screen: the visualiser coming up takes the idle
  //: screen down, whoever asked for it.
  $effect(() => {
    if (!$panel.visualiser) return;
    untrack(() => {
      idle = false;
      askedIdle = false;
    });
  });

  //: ...and says whether its idle screen is up, so the phone's toggle shows
  //: what is on the glass, whatever changed it.
  $effect(() => {
    const shown = idle;
    if (surface !== 'panel') return;
    reportShown({ idle: shown }).catch(() => {});
  });

  //: **ADR-0101 as amended 2026-10-05: Home, Now playing and Lyrics from the
  //: phone.** Applied once per ask, as the idle ask is, and attention like a
  //: touch. Home is the library's root (a fresh one - wherever the library
  //: had got to), or the root screen with LMS off; the others close what
  //: covers Now Playing, and Lyrics and Track set its tab.
  let appliedViewAsk = null;
  let libraryHome = $state(0);
  $effect(() => {
    const ask = $panel.view_request;
    if (surface !== 'panel' || !ask || ask.seq === appliedViewAsk) return;
    appliedViewAsk = ask.seq;
    if (ask.at && Date.now() / 1000 - ask.at > 60) return;
    untrack(() => {
      idle = false;
      askedIdle = false;
      touches += 1;
      settingsOpen = false;
      closeVolume();
      // An artist or album asked for earlier is not asked for again: the
      // library remounts on `libraryHome` with these as its props, and an
      // album left here reopened at every phone Home (Finding 125 #13,
      // 2026-10-14).
      libraryArtist = null;
      libraryAlbum = null;
      if (ask.to === 'home') {
        libraryRequested = !lmsOff;
        libraryHome += 1;
        return;
      }
      if (!$active) return;
      // ADR-0122 from the phone: down to the strip, the library as left.
      if (ask.to === 'minimise') {
        libraryRequested = !lmsOff;
        return;
      }
      libraryRequested = false;
      if (ask.to === 'lyrics' || ask.to === 'track') lyricsAsk.set({ on: ask.to === 'lyrics' });
    });
  });

  //: ...and whether Now Playing is what the glass shows, so the phone's Now
  //: playing is a toggle: up, it minimises; down, it brings it up (George,
  //: 2026-10-06).
  let reportedNow = null;
  $effect(() => {
    const showing = !!$active && !libraryOpen && !settingsOpen && !waitingOpen && !idle;
    if (surface !== 'panel' || showing === reportedNow) return;
    reportedNow = showing;
    reportShown({ now: showing }).catch(() => (reportedNow = null));
  });

  let reportedLyrics = null;
  //: ...and whether the lyrics are what the glass shows: Now Playing up,
  //: nothing over it, its lyrics on.
  $effect(() => {
    const showing =
      $lyricsShown && !!$active && !libraryOpen && !settingsOpen && !idle && !$panel.visualiser;
    // The state this reads arrives every second; the core hears a change.
    if (surface !== 'panel' || showing === reportedLyrics) return;
    reportedLyrics = showing;
    reportShown({ lyrics: showing }).catch(() => (reportedLyrics = null));
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
  //: **ADR-0149: Library on the screen off** (Phase 14; George, 2026-10-15:
  //: "the lyrion client is up and running but there is no library
  //: navigation on the screen"): the panel is the same two screens as with
  //: the client off - the waiting home and Now Playing - while Lyrion's apps
  //: and controllers still play to it. `lmsOff` stays the client itself.
  const lmsOff = $derived($settingValues.lms_enabled === false || $settingValues.lms_library === false);
  const libraryOpen = $derived(!lmsOff && (!$active || libraryRequested));
  const waitingOpen = $derived(lmsOff && !$active);
  //: **ADR-0122: the library is kept while Now Playing is up**, mounted and
  //: hidden, so Minimise shows it as it was left - path, levels, scroll.
  //: Home remounts it at its root (`libraryHome`), as the phone's Home does.
  let libraryKept = $state(false);
  $effect(() => {
    if (libraryOpen) libraryKept = true;
    if (lmsOff) {
      libraryKept = false;
      // The library is dropped, and mounts afresh when LMS comes back - with
      // these as its props, so an artist or album opened from Now Playing
      // before LMS was turned off reopened then, not the root (Finding 125
      // #13, 2026-10-14).
      libraryArtist = null;
      libraryAlbum = null;
    }
  });
  const libraryShown = $derived(libraryOpen && !settingsOpen && !waitingOpen);
  function openLibraryHome() {
    libraryArtist = null;
    libraryAlbum = null;
    libraryHome += 1;
    libraryRequested = true;
  }
  function openLibraryArtist(name) {
    libraryArtist = name;
    libraryAlbum = null;
    libraryHome += 1;
    libraryRequested = true;
  }
  //: George, 2026-10-14: the release title in Now Playing opens its album.
  let libraryAlbum = $state(null);
  function openLibraryAlbum(title, artist) {
    libraryArtist = null;
    libraryAlbum = { title, artist, n: (libraryAlbum?.n ?? 0) + 1 };
    libraryHome += 1;
    libraryRequested = true;
  }
  const minimise = () => (libraryRequested = true);
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

  //: ADR-0109, amended 2026-10-03: the answer to "a different screen is
  //: attached". Choose opens Settings on the Attached screen row.
  let openRow = $state(null);
  async function answerNew(answer) {
    try {
      await answerNewScreen(answer);
    } catch {
      return;
    }
    if (answer === 'choose') {
      openRow = 'screen';
      if (surface === 'panel') openSettings();
    }
  }

  const openVolume = () => {
    armAutoHide();
    volumeArmsAt = 0;
    volumeOpen = true;
  };

  //: **ADR-0104 §5: the panel during setup.** While the setup network is up,
  //: or a new device waits to be set up, the glass shows the way in and
  //: nothing else. A configured device waiting its 90 s at boot shows its
  //: ordinary screens: most boots end with the Wi-Fi back, and a setup
  //: screen flashing on every one would be a fault in itself.
  const setupShown = $derived(
    !!$setup &&
      (['open', 'failed', 'joining', 'done'].includes($setup.network) ||
        ($setup.needed && ['waiting', 'online'].includes($setup.network)))
  );

  //: **...and on a phone, the setup page** in place of Settings while setup
  //: is on (ADR-0104). Held once shown: finishing takes the network down
  //: under the page, and it must keep its last screen - where to go next -
  //: rather than swap to Settings as the state changes behind it.
  //:
  //: **"joining" keeps it but never opens it** (2026-10-11, the outage test on
  //: sofapi): a page that reconnected the moment the player was rejoining its
  //: own Wi-Fi - after the setup network of ADR-0134 - switched to setup and
  //: held it, on a player with no setup running. A phone doing setup always
  //: saw "open" first.
  let setupPageHeld = $state(false);
  const setupPage = $derived(
    setupPageHeld ||
      (!!$setup && (['open', 'failed'].includes($setup.network) || $setup.needed))
  );
  $effect(() => {
    if (setupPage && surface === 'remote') untrack(() => (setupPageHeld = true));
  });

  //: **ADR-0149: first use's part 2 on the phone** while it is owed. Held
  //: once shown, as setup's page is: finishing ends it on the player, and
  //: the page has its own last screen (what is downloading) to show, until
  //: its Close.
  let personaliseHeld = $state(false);
  const personalisePage = $derived(!setupPage && (personaliseHeld || $personalise === 'pending'));
  $effect(() => {
    if (personalisePage && surface === 'remote') untrack(() => (personaliseHeld = true));
  });
  //: ...and on the panel, the way to it: a code to the player's own page.
  const personaliseAt = $derived(
    $settingsDevice.hostname ? `http://${$settingsDevice.hostname}.local:8090` : $settingsDevice.address ? `http://${$settingsDevice.address}:8090` : null
  );

  //: Setup ending is attention, like a touch: the panel comes back to its
  //: own screens and the idle timer starts from there.
  let setupWasShown = false;
  $effect(() => {
    const now = setupShown;
    if (setupWasShown && !now) untrack(() => (touches += 1));
    setupWasShown = now;
  });

  // ADR-0032: the panel renders everything; a remote browser only settings.
  let surface = $state(null);
  //: **No answer is asked again, not taken for the panel** (code review,
  //: 2026-10-12). A phone that loaded the page as the core restarted used to
  //: become a panel until reloaded: drawn at 1280 px, its taps ending the
  //: real panel's visualiser, its screens reported as the panel's. Nothing
  //: shows until the core says which this is - on the panel too, which only
  //: waits for the restart it was going to wait for anyway.
  const SURFACE_RETRY_MAX_MS = 5000;
  function askSurface(delay = 500) {
    fetch('/surface')
      .then((r) => r.json())
      .then((body) => {
        if (body?.surface !== 'panel' && body?.surface !== 'remote') throw new Error(`surface ${body?.surface}`);
        surface = body.surface;
      })
      .catch(() => setTimeout(() => askSurface(Math.min(delay * 2, SURFACE_RETRY_MAX_MS)), delay));
  }

  // **No system cursor on the panel** (George, 2026-10-05: "two cursors").
  // The compositor draws one where it starts and hides it only at the
  // first real touch; driven from a phone, the panel never gets that
  // touch. The phone's pointer is our own (lib/PanelPointer.svelte).
  $effect(() => {
    document.documentElement.classList.toggle('on-panel', surface === 'panel');
  });

  //: **Text size** (ADR-0148; George, 2026-10-14): every font size in
  //: pixels is multiplied by `--text-scale` (vite.config.js), on the
  //: player's own screen only - a phone keeps its own size.
  $effect(() => {
    const percent = Number($settingValues.text_size ?? 100);
    const scale = surface === 'panel' && percent >= 90 && percent <= 130 ? percent / 100 : 1;
    document.documentElement.style.setProperty('--text-scale', String(scale));
  });

  //: **ADR-0109 decision 5: Keep this screen?** The core asks while a newly
  //: chosen screen waits; its countdown runs from when the question is drawn
  //: (`deadline`, this device's clock). Only the panel answers (decision 2).
  let keepNow = $state(Date.now());
  $effect(() => {
    if (!$screenConfirm) return;
    const id = setInterval(() => (keepNow = Date.now()), 250);
    return () => clearInterval(id);
  });
  //: **...and starts when the question is on the glass** (George,
  //: 2026-10-14: "The countdown should start with the keep screen
  //: displayed"). Two frames after it is drawn, the panel says so; the core
  //: sets `deadline` from then. Said again until the deadline arrives, in
  //: case one report is lost; the core starts it once.
  $effect(() => {
    const question = $screenConfirm;
    if (surface !== 'panel' || !question || question.deadline || updateLock) return;
    let frame = requestAnimationFrame(() => {
      frame = requestAnimationFrame(() => answerScreen('shown').catch(() => {}));
    });
    const again = setInterval(() => answerScreen('shown').catch(() => {}), 3000);
    return () => {
      cancelAnimationFrame(frame);
      clearInterval(again);
    };
  });
  const keepLeft = $derived(
    $screenConfirm?.deadline ? ($screenConfirm.deadline * 1000 - keepNow) / 1000 : ($screenConfirm?.total ?? 30)
  );

  //: **ADR-0110 §6: the panel is locked while it updates.** Up from the
  //: moment an install runs; kept up while the core restarts and the socket
  //: reconnects (nothing else shows in between); then the outcome for a few
  //: seconds, and a reload when the release changed the page's own files.
  const OUTCOME_MS = 6000;
  //: **A finished update waits for Done** (ADR-0110, 2026-10-05: George,
  //: "keep the user in the installation screen which he would need to
  //: dismiss"). The limit is for a panel nobody watches.
  const DONE_MS = 10 * 60 * 1000;
  let outcomeTimer;
  function leaveUpdate(changed) {
    clearTimeout(outcomeTimer);
    if (changed) location.reload();
    else {
      updateLock = false;
      updateOutcome = null;
    }
  }
  //: **An update that ends without an outcome lets the panel go** (code
  //: review, 2026-10-12). An updater killed mid-way leaves its file on
  //: *installing*; an install whose own check finds nothing newer ends on
  //: *current*. Either way the unit stops and `active` drops with no *done*
  //: or *failed* to show, and the lock - which takes no input - stayed up
  //: until a power cycle, which it tells the user not to do. Not at once:
  //: between two steps the file can sit a moment on a state the core does
  //: not count as running.
  const STRANDED_MS = 30 * 1000;
  let strandedTimer;
  let updateLock = $state(false);
  let updateOutcome = $state(null);
  let updateChanged = false;
  let loadedRelease = null;
  $effect(() => {
    const u = $update;
    if (loadedRelease === null && u?.installed) loadedRelease = u.installed;
    if (u?.active) {
      if (!untrack(() => updateLock)) hidePeppy();
      updateLock = true;
      updateOutcome = null;
      clearTimeout(strandedTimer);
      strandedTimer = undefined;
      return;
    }
    if (!untrack(() => updateLock) || untrack(() => updateOutcome) || $connection !== 'open') {
      clearTimeout(strandedTimer);
      strandedTimer = undefined;
      return;
    }
    if (u && ['done', 'failed'].includes(u.state)) {
      clearTimeout(strandedTimer);
      strandedTimer = undefined;
      updateOutcome = u.state;
      const changed = u.state === 'done' && u.installed && u.installed !== loadedRelease;
      updateChanged = changed;
      outcomeTimer = setTimeout(() => leaveUpdate(changed), u.state === 'done' ? DONE_MS : OUTCOME_MS);
    } else if (strandedTimer === undefined) {
      strandedTimer = setTimeout(() => {
        strandedTimer = undefined;
        leaveUpdate(Boolean($update?.installed && $update.installed !== loadedRelease));
      }, STRANDED_MS);
    }
  });
  //: **Locked from the tap, not from the updater's first report** (George,
  //: 2026-10-15). On the panel only - a phone follows the install in the
  //: modal. An install that never starts lets go after STRANDED_MS, as one
  //: that ends without an outcome does.
  $effect(() => {
    if (!$updateAsked || surface !== 'panel' || untrack(() => updateLock)) return;
    hidePeppy();
    updateLock = true;
    updateOutcome = null;
    clearTimeout(strandedTimer);
    strandedTimer = setTimeout(() => {
      strandedTimer = undefined;
      if (!$update?.active) leaveUpdate(Boolean($update?.installed && $update.installed !== loadedRelease));
    }, STRANDED_MS);
  });
  //: **A new UI build reloads the panel too** (ADR-0110 as amended
  //: 2026-10-09). The reload above follows the release; a UI package
  //: installed under the same release - a preview over SSH, a package put on
  //: by hand - left guestpi's panel running 7 October's code for two days,
  //: and the test pattern a phone asked for never appeared. Once a minute the
  //: panel reads its own index.html and compares the build it names with the
  //: one it runs; it reloads when they differ and nothing that must not be cut
  //: short is up. Phones load the page afresh each time and are left alone.
  const BUILD_CHECK_MS = 60 * 1000;
  const BUILD = /\/assets\/index-[\w-]+\.js/;
  const runningBuild =
    document.querySelector('script[type="module"][src*="/assets/index-"]')?.getAttribute('src')?.match(BUILD)?.[0] ?? null;
  async function checkBuild() {
    if (!runningBuild || !document.documentElement.classList.contains('on-panel')) return;
    if (updateLock || setupShown || $screenConfirm || $screenCheck?.showing) return;
    try {
      const r = await fetch('/', { cache: 'no-store' });
      if (!r.ok) return;
      const now = (await r.text()).match(BUILD)?.[0];
      if (now && now !== runningBuild) {
        console.info(`panel: build ${runningBuild} replaced by ${now}; reloading`);
        location.reload();
      }
    } catch {
      /* the core is restarting: the next check sees the answer */
    }
  }
  $effect(() => {
    const id = setInterval(checkBuild, BUILD_CHECK_MS);
    return () => clearInterval(id);
  });

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
    askSurface();


    // ADR-0043: end the boot animation only once something is actually on
    // the glass. onMount runs before the browser has painted, so this waits
    // for the frame after the one being composed now - two rAFs, which is
    // the earliest point at which a pixel of this app has been presented.
    requestAnimationFrame(() => requestAnimationFrame(reportPainted));
  });
</script>

<svelte:window onpointerdowncapture={onPointerDown} />

{#if surface === 'remote' && setupPage}
  <FirstUsePage mode="p1" setup={$setup} />
{:else if surface === 'remote' && personalisePage}
  <FirstUsePage mode="p2" onclose={() => (personaliseHeld = false)} />
{:else if surface === 'remote'}
  <!-- ADR-0101: on a phone, Settings and the mini player under it. -->
  <div class="remote remote--mini"><Settings {openRow} onrowopened={() => (openRow = null)} /></div>
  <MiniPlayer />
  {#if $screenNew}
    <NewScreen question={$screenNew} onanswer={answerNew} />
  {/if}
  {#if $settling && !$settling.hidden}
    <SettlingScreen settling={$settling} ondone={() => settlingDone().catch(() => {})} onhide={() => settlingHide().catch(() => {})} />
  {/if}
  <!-- ADR-0123: a new cable address waiting to be kept, on every page. -->
  <CableKeep />
  <!-- ADR-0147 D3: a screen without touch - a TV - is kept from here; so is
       a listed panel whose touch the player does not recognise, which may
       need a driver it never installs (Finding 125, 2026-10-14). -->
  {#if $screenConfirm?.phone}
    <PhoneKeepScreen
      question={$screenConfirm}
      secondsLeft={keepLeft}
      onkeep={() => answerScreen('keep')}
      onrevert={() => answerScreen('revert')}
    />
  {/if}
{:else if surface === 'panel'}

<div class="panel" class:panel--bar={screen.family === 'bar'} data-family={screen.family}>
  <!-- One backdrop for the whole panel, so a screen change does not build
       two large blurred layers again (George, 2026-09-17). Exactly one
       screen is drawn over it at a time: the screens are transparent now,
       so overlapping them would show both at once. The library may stay
       mounted under another, kept and not drawn (ADR-0122). -->
  <PanelBackground artwork={$metadata?.artwork ?? null} />

  <!-- No animation on a screen change at all (George, 2026-09-17). Over a
       shared backdrop the screens are transparent, so anything that fades
       one in or out shows the bare backdrop between them - which read as a
       blink on the panel, in both the two-way and the fade-in-only form.
       The backdrop does not move across a change, so the swap is the whole
       effect. The drawer, idle screen and handoff keep their own. -->
  {#if settingsOpen}
    <div class="screen-layer">
      <Settings onback={() => (settingsOpen = false)} embedded {openRow} onrowopened={() => (openRow = null)} />
    </div>
  {:else if waitingOpen}
    <div class="screen-layer">
      <WaitingHome availability={$availability} onsettings={openSettings} settings={$settingValues} />
    </div>
  {:else if libraryOpen}
    <!-- The library's layer, below: kept mounted (ADR-0122). -->
  {:else if $active}
    <div class="screen-layer">
      <!-- ADR-0079: with LMS off the Home button is a Settings button and
           `onartist` is not passed at all, so the artist line is a name rather
           than a link that leads nowhere. -->
      {#if screen.family === 'bar'}
        <!-- ADR-0109, Bar family: the strip, with the same props. -->
        <BarNowPlaying active={$active} metadata={$metadata} volume={$volume} controls={$capabilities[$active]?.controls ?? []} available={$available} shuffle={$shuffle} repeat={$repeat} queue={$queue} onvolume={openVolume} onvisualisation={showVisualisation}
          rootless={lmsOff}
          onhome={lmsOff ? openSettings : openLibraryHome}
          onminimise={lmsOff ? null : minimise}
          onartist={lmsOff ? undefined : openLibraryArtist}
          onalbum={lmsOff ? undefined : openLibraryAlbum} />
      {:else}
      <NowPlaying active={$active} metadata={$metadata} volume={$volume} controls={$capabilities[$active]?.controls ?? []} available={$available} shuffle={$shuffle} repeat={$repeat} queue={$queue} onvolume={openVolume} onvisualisation={showVisualisation}
        rootless={lmsOff}
        onhome={lmsOff ? openSettings : openLibraryHome}
        onminimise={lmsOff ? null : minimise}
        onartist={lmsOff ? undefined : openLibraryArtist}
          onalbum={lmsOff ? undefined : openLibraryAlbum} />
      {/if}
    </div>
  {/if}

  {#if libraryKept || libraryOpen}
    <!-- ADR-0122: kept while hidden - drawn and touchable only while shown. -->
    <div class="screen-layer" class:is-kept={!libraryShown}>
      {#if screen.family === 'bar'}
      <!-- ADR-0109, Bar family: the library as strips and a rail, with
           Library's props. -->
      {#key libraryHome}
      <BarLibrary
        active={$active}
        metadata={$metadata}
        volume={$volume}
        controls={$active ? ($capabilities[$active]?.controls ?? []) : []}
        availability={$availability}
        openArtistNamed={libraryArtist}
        openAlbumNamed={libraryAlbum}
        onclose={() => { libraryRequested = false; libraryArtist = null; libraryAlbum = null; }}
        onsettings={openSettings}
        onvolume={openVolume}
      />
      {/key}
      {:else}
      {#key libraryHome}
      <Library
        active={$active}
        metadata={$metadata}
        volume={$volume}
        controls={$active ? ($capabilities[$active]?.controls ?? []) : []}
        availability={$availability}
        openArtistNamed={libraryArtist}
        openAlbumNamed={libraryAlbum}
        onclose={() => { libraryRequested = false; libraryArtist = null; libraryAlbum = null; }}
        onsettings={openSettings}
        onvolume={openVolume}
      />
      {/key}
      {/if}
    </div>
  {/if}

  <!-- ADR-0046: **mounted in fixed output too, with no level to show.**
       The drawer is where the sentence lives - "the answer is where the
       question is asked" - and `{#if $volume}` alone left the padlock
       opening nothing at all. -->
  {#if screen.family === 'bar'}
    <!-- ADR-0109, Bar family: the pull-down tray stands where the drawer
         stands, over every screen. Always mounted: it carries Home and the
         visualiser as well as the level, so it is needed with no level to
         show. -->
    <BarTray
      open={volumeOpen}
      armsAt={volumeArmsAt}
      volume={$volume}
      active={$active}
      onclose={closeVolume}
      onexternal={openFromExternal}
      onactivity={keepVolumeOpen}
      onsettled={armAutoHide}
      rootless={lmsOff}
      onhome={lmsOff ? openSettings : openLibraryHome}
      onvisualisation={showVisualisation}
    />
  {:else if $volume || $fixedOutput}
    <VolumeDrawer
      open={volumeOpen}
      armsAt={volumeArmsAt}
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
    <IdleScreen ondismiss={() => { idle = false; askedIdle = false; }} settings={$settingValues} />
  {/if}

  {#if shownHandoff}
    <HandoffScreen from={shownHandoff.from} to={shownHandoff.to} />
  {/if}

  <!-- Last, and above everything (ADR-0045). A request that cannot be seen
       cannot be answered, and it lapses in thirty seconds either way - so it
       takes the screen from the visualiser or the idle screen rather than
       waiting politely behind them. It is also the only layer here with no
       dismiss of its own: the agent takes it away. -->
  {#if setupShown}
    <SetupScreen setup={$setup} />
  {/if}

  {#if $pairing}
    <PairingFrame request={$pairing} />
  {/if}

  {#if $screenNew && !$screenConfirm && !setupShown && !updateLock}
    <NewScreen question={$screenNew} onanswer={answerNew} />
  {/if}

  <!-- ADR-0128: the first start after setup, until it has settled - over
       everything but Keep this screen and the update lock. -->
  {#if $settling && !$settling.hidden && !$screenConfirm && !updateLock && !setupShown}
    <SettlingScreen settling={$settling} ondone={() => settlingDone().catch(() => {})} onhide={() => settlingHide().catch(() => {})} />
  {:else if $personalise === 'pending' && $settingValues.headless !== true && !$screenConfirm && !updateLock && !setupShown}
    <!-- ADR-0149: part 2 is owed; the panel shows the way to it - **at
         once**, before the player's address has arrived (George, 2026-10-18:
         after setup's restart the player's own screens showed first). The
         code fills in when the address does. -->
    <SetupScreen setup={$setup} personalise={personaliseAt ?? true} onlater={() => personaliseLater().catch(() => {})} />
  {/if}
  {#if !setupShown}
    <CableKeep />
  {/if}

  <!-- ADR-0126: the hardware report's test pattern, over everything but
       Keep this screen and the update lock. -->
  {#if $screenCheck?.showing && !$screenConfirm && !updateLock}
    {#key $screenCheck.seq}
      <TestPattern check={$screenCheck} onresult={(r) => sendScreenCheck(r).catch(() => {})} />
    {/key}
  {/if}

  <!-- ADR-0109 decision 5: above everything but the update lock - the
       question is whether this screen works at all. -->
  {#if $screenConfirm && !updateLock}
    <KeepScreen
      model={$screenConfirm.model}
      previous={$screenConfirm.rotation_only ? $screenConfirm.previous_rotation : ($screenConfirm.previous ?? "the screen's own settings")}
      untested={$screenConfirm.untested}
      rotationOnly={$screenConfirm.rotation_only}
      phone={!!$screenConfirm.phone}
      buttons={$screenConfirm.panel_buttons ?? !$screenConfirm.phone}
      secondsLeft={keepLeft}
      total={$screenConfirm.total ?? 30}
      onkeep={() => answerScreen('keep')}
      onrevert={() => answerScreen('revert')}
    />
  {/if}

  <!-- ADR-0110 §6: above even setup and pairing - nothing on this panel is
       usable while its software is being replaced. -->
  {#if updateLock}
    <UpdateScreen update={$update} reconnecting={$connection !== 'open'} outcome={updateOutcome}
                  oncontinue={() => leaveUpdate(updateChanged)} />
  {/if}

  <!-- ADR-0121: a phone's pointer, over everything, while one controls. -->
  <PanelPointer />
</div>
{/if}

<!-- ADR-0135: the screen in standby. Its output is off; this black is for a
     screen whose output could not be switched, and it takes the tap that
     wakes it, so that tap presses nothing underneath. -->
{#if surface === 'panel' && $panel.standby}
  <div class="standby-cover" aria-hidden="true"></div>
{/if}

<!-- ADR-0132: a factory reset under way - over everything, on every surface. -->
{#if $resetting}
  <ResetScreen surface={surface === 'remote' ? 'remote' : 'panel'} />
{/if}

<style>
  .standby-cover {
    position: fixed;
    inset: 0;
    z-index: 2000;
    background: #000;
  }
  :global(*, *::before, *::after) {
    box-sizing: border-box;
  }

  :global(html.on-panel),
  :global(html.on-panel *) {
    cursor: none !important;
  }
  /* **Nothing on the panel is text to select** (George, 2026-10-18: a long
     touch on the setup network's name offered Copy). Fields a person types
     into keep it. */
  :global(html.on-panel) {
    user-select: none;
    -webkit-user-select: none;
    -webkit-touch-callout: none;
  }
  :global(html.on-panel input),
  :global(html.on-panel textarea) {
    user-select: text;
    -webkit-user-select: text;
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
  /* ADR-0101: room for the mini player, so the last rows are not under it -
     its closed height as MiniPlayer measures it (the home-indicator inset is
     inside that), and 16 px between the last row and its top edge (George,
     2026-10-06). Left at the end of Settings' own scrolling lists, not as
     padding here: padded, the page stopped short and left a bare band above
     the sheet. */
  .remote--mini {
    --foot-clear: calc(var(--mini-closed-h, 160px) + 16px);
  }

  /* ADR-0109, Standard family: Chromium's scale factor makes every screen
     1280 logical px wide; the height is whatever that leaves, and the tokens
     that follow it are recomputed here, where it is known. */
  /* ADR-0109, Bar family: 400 logical px tall and as wide as the screen
     makes it (1280 on 1280x400, 1850 on 1480x320). */
  .panel--bar {
    width: 100vw !important;
  }
  .panel {
    --panel-h: 100vh;
    --art: calc(var(--panel-h) - 300px);
    position: relative;
    width: 1280px;
    height: var(--panel-h);
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
  /* ADR-0122: the kept library, not drawn and not touchable; unlike
     display: none, content-visibility keeps its scroll positions. */
  .screen-layer.is-kept {
    content-visibility: hidden;
    visibility: hidden;
    pointer-events: none;
  }
</style>
