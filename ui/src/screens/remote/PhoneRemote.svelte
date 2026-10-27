<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0164: the phone's remote (design/source/21). The player picker and the
  Remote / Settings switch on top; under them the two pages side by side,
  the pair sliding a page at a time: Remote - with a screen, now playing, the
  touch area, the quick actions and the volume row; without one, a large
  cover, a seek bar and larger transport - and Settings as it is, without the
  mini player, mounted on its first visit. Over them the player menu and the
  EQ sheet. Behind them the panel's background: the weave, the blurred cover
  where there is one, the veil (D9).

  For a player with a screen, the touchpad's socket (ADR-0121) is open while
  Remote shows: the trackpad and its strips go over it, and the panel says
  over it when its pointer or its ring is on a text field and when one has
  focus, so the phone's own keyboard can type there (D7, C5).
-->
<script>
  import { onMount, untrack } from 'svelte';
  import { active, metadata, sources } from '../../lib/state.js';
  import { settingValues, settingsDevice } from '../../lib/settings.js';
  import { openTouchpad } from '../../lib/touchpad.js';
  import Settings from '../Settings.svelte';
  import mark from '../../assets/gexis-mark.svg';
  import RemoteScreen from './RemoteScreen.svelte';
  import RemoteNoScreen from './RemoteNoScreen.svelte';
  import PlayerMenu from './PlayerMenu.svelte';
  import EqSheet from './EqSheet.svelte';
  import { said } from './commands.js';
  import { FILLED } from './icons.js';

  let { openRow = null, onrowopened = null } = $props();

  const hasScreen = $derived($settingValues.headless !== true);

  //: C4: the cover, here for the background too; one that fails to load is
  //: the pending glyph's, and no blur behind it.
  let failedArt = $state(null);
  const artwork = $derived($active && $metadata?.artwork && $metadata.artwork !== failedArt ? $metadata.artwork : null);

  // ── The pages ───────────────────────────────────────────────────────────
  let page = $state('remote');
  let settingsSeen = $state(false);
  let settingsRow = $state(null);
  function toSettings(row = null) {
    settingsSeen = true;
    settingsRow = row;
    eqOpen = false;
    menuOpen = false;
    stopTyping();
    page = 'settings';
  }
  //: A row asked for from outside (a new screen's *Choose*) opens Settings on it.
  $effect(() => {
    const row = openRow;
    if (row) untrack(() => toSettings(row));
  });

  // ── The player picker ───────────────────────────────────────────────────
  let menuOpen = $state(false);
  let me = $state(null);
  let others = $state([]);
  //: The last list, remembered on this phone (ADR-0136, George 2026-10-11),
  //: so the menu has its players at once and the fresh answer replaces them.
  const KEPT = 'gexis.players';
  async function loadPlayers() {
    try {
      const response = await fetch('/players');
      if (!response.ok) return;
      const body = await response.json();
      me = body.self;
      others = body.others ?? [];
      try {
        localStorage.setItem(KEPT, JSON.stringify({ self: me, others }));
      } catch {
        // Not kept: the next visit waits for the answer.
      }
    } catch {
      // No list: this player alone.
    }
  }
  onMount(() => {
    try {
      const kept = JSON.parse(localStorage.getItem(KEPT) ?? 'null');
      if (kept) {
        me = kept.self ?? null;
        others = kept.others ?? [];
      }
    } catch {
      // Nothing kept.
    }
    loadPlayers();
  });
  const sourceName = $derived($sources?.[$active]?.name ?? $active);
  const here = $derived({
    name: $settingsDevice.name || me?.name || 'gexis',
    state: said({ transport: $active ? $metadata?.transport : null, renderer: sourceName }),
  });
  function toggleMenu() {
    menuOpen = !menuOpen;
    if (menuOpen) loadPlayers();
  }

  // ── The pad ─────────────────────────────────────────────────────────────
  //: C8: the one last used on this phone, Trackpad the first time; with
  //: Phone touchpad off, the D-pad alone.
  const PAD_KEPT = 'gexis.remote.pad';
  const padAllowed = $derived($settingValues.phone_touchpad !== false);
  let chosenPad = $state(readPad());
  function readPad() {
    try {
      return localStorage.getItem(PAD_KEPT) === 'dpad' ? 'dpad' : 'touch';
    } catch {
      return 'touch';
    }
  }
  function choosePad(p) {
    chosenPad = p;
    try {
      localStorage.setItem(PAD_KEPT, p);
    } catch {
      // Kept for this visit only.
    }
  }
  const pad = $derived(padAllowed ? chosenPad : 'dpad');

  // ── The socket, and typing (C5) ─────────────────────────────────────────
  let socket = $state(null);
  //: What the panel said in advance: its pointer over a text field, its
  //: ring on one.
  let overField = false;
  let ringField = false;
  let typeEl = $state(null);
  let typed = '';
  $effect(() => {
    if (!(hasScreen && padAllowed && page === 'remote')) return;
    const s = openTouchpad((message) => {
      if (message.t === 'over') overField = !!message.field;
      else if (message.t === 'ring') ringField = !!message.field;
      else if (message.t === 'focus' && !message.field) stopTyping();
      // ADR-0157: a character the player's keyboard layout cannot type.
      else if (message.t === 'untyped') say('Some characters could not be typed on the player');
    });
    socket = s;
    return () => {
      s.close();
      socket = null;
      overField = false;
      ringField = false;
      stopTyping();
    };
  });

  //: **The keyboard opens inside the touch** that taps or sends OK (ADR-0121
  //: §4), the one moment a browser allows it.
  function beforeTap() {
    if (overField) keyboard();
  }
  function beforeOk() {
    if (ringField) keyboard();
  }
  function keyboard() {
    if (!typeEl) return;
    typeEl.value = '';
    typed = '';
    // Not scrolled to: its caret is taller than the field, and the browser
    // moved the whole remote up for it.
    typeEl.focus({ preventScroll: true });
  }
  function stopTyping() {
    typed = '';
    if (typeEl) {
      typeEl.value = '';
      typeEl.blur();
    }
  }
  /** What changed in the hidden field, sent as text and backspaces, so a
   *  keyboard's suggestions and corrections arrive as the panel needs them. */
  function typedInput() {
    const now = typeEl.value;
    let same = 0;
    while (same < typed.length && same < now.length && typed[same] === now[same]) same += 1;
    for (let i = same; i < typed.length; i += 1) socket?.send({ t: 'key', key: 'Backspace' });
    if (now.length > same) socket?.send({ t: 'text', text: now.slice(same) });
    typed = now;
  }
  function typedKey(event) {
    if (event.key === 'Enter') {
      event.preventDefault();
      socket?.send({ t: 'key', key: 'Enter' });
    }
  }

  // ── The EQ sheet, and what is said ──────────────────────────────────────
  let eqOpen = $state(false);
  let told = $state(null);
  let toldTimer;
  function say(text) {
    told = text;
    clearTimeout(toldTimer);
    toldTimer = setTimeout(() => (told = null), 2500);
  }
</script>

<div class="remote">
  <div class="weave" aria-hidden="true"></div>
  {#if artwork}<img class="blur" src={artwork} alt="" aria-hidden="true" />{/if}
  <div class="veil" aria-hidden="true"></div>

  <div class="column">
    <div class="top">
      <button class="picker" type="button" aria-label="Choose a player" aria-expanded={menuOpen} onclick={toggleMenu}>
        <img src={mark} alt="" />
        <span class="picker__text">
          <span class="picker__name">{here.name}</span>
          <span class="picker__state">{here.state}</span>
        </span>
        <svg class="picker__chev" class:is-open={menuOpen} viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.chevron} /></svg>
      </button>
      <div class="pages-switch">
        <span class="pages-switch__ind" style:transform={page === 'settings' ? 'translateX(56px)' : 'none'}></span>
        <button class="seg" class:is-on={page === 'remote'} type="button" aria-label="Remote" aria-pressed={page === 'remote'}
                onclick={() => { page = 'remote'; menuOpen = false; }}>
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <rect x="7" y="2.5" width="10" height="19" rx="3" /><circle cx="12" cy="8" r="2" /><path d="M10.5 14h3M10.5 17.5h3" />
          </svg>
        </button>
        <button class="seg" class:is-on={page === 'settings'} type="button" aria-label="Settings" aria-pressed={page === 'settings'}
                onclick={() => toSettings()}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.settings} fill="currentColor" /></svg>
        </button>
      </div>
    </div>

    <div class="pages">
      <div class="track" style:transform={page === 'settings' ? 'translateX(-50%)' : 'none'}>
        <div class="page page--remote" inert={page !== 'remote'}>
          {#if hasScreen}
            <RemoteScreen {artwork} onartfailed={(a) => (failedArt = a)} {pad} onpad={choosePad} padSwitch={padAllowed}
                          {socket} onok={beforeOk} ontap={beforeTap}
                          onsay={say} oneq={() => { eqOpen = true; stopTyping(); }} />
          {:else}
            <RemoteNoScreen {artwork} onartfailed={(a) => (failedArt = a)} onsay={say} oneq={() => (eqOpen = true)} />
          {/if}
        </div>
        <div class="page page--settings" inert={page !== 'settings'}>
          {#if settingsSeen}
            <Settings openRow={settingsRow} onrowopened={() => { settingsRow = null; onrowopened?.(); }} switcher={false} />
          {/if}
        </div>
      </div>
    </div>

    {#if told}<div class="told" role="status">{told}</div>{/if}

    <input
      class="type"
      bind:this={typeEl}
      type="text"
      autocomplete="off"
      autocorrect="off"
      spellcheck="false"
      aria-label="Text for the player's screen"
      oninput={typedInput}
      onkeydown={typedKey}
    />

    <PlayerMenu open={menuOpen} {me} {others} {here} onclose={() => (menuOpen = false)} />
    <EqSheet open={eqOpen} onclose={() => (eqOpen = false)} onedit={() => toSettings('equaliser')} />
  </div>
</div>

<style>
  .remote {
    position: fixed;
    inset: 0;
    overflow: hidden;
    background: #101a21;
    font-family: var(--font-ui);
    color: #e9eef2;
    -webkit-tap-highlight-color: transparent;
    user-select: none;
    -webkit-user-select: none;
  }
  .weave {
    position: absolute;
    inset: -90px;
    background: var(--remote-weave);
    filter: blur(70px);
    transform: scale(1.14);
    pointer-events: none;
  }
  .blur {
    position: absolute;
    inset: -120px;
    width: calc(100% + 240px);
    height: calc(100% + 240px);
    object-fit: cover;
    filter: blur(72px) saturate(1.7);
    transform: scale(1.12);
    pointer-events: none;
  }
  .veil {
    position: absolute;
    inset: 0;
    background: var(--remote-veil);
    pointer-events: none;
  }
  /* C10: the design's column, at most 412 px wide on a larger screen. */
  .column {
    position: relative;
    height: 100%;
    max-width: var(--remote-max-width);
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    padding-top: env(safe-area-inset-top, 0px);
    padding-bottom: env(safe-area-inset-bottom, 0px);
    box-sizing: border-box;
  }
  .top {
    position: relative;
    flex-shrink: 0;
    padding: 10px 16px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .picker {
    flex: 1;
    min-width: 0;
    height: 54px;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(233, 238, 242, 0.1);
    box-sizing: border-box;
    padding: 0 8px 0 10px;
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    color: inherit;
    font: inherit;
    text-align: left;
  }
  .picker:active {
    background: rgba(255, 255, 255, 0.07);
  }
  .picker img {
    width: 30px;
    height: 30px;
    display: block;
    flex-shrink: 0;
  }
  .picker__text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .picker__name {
    font-size: 16px;
    font-weight: 700;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .picker__state {
    font-size: 12px;
    color: rgba(233, 238, 242, 0.72);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .picker__chev {
    width: 22px;
    height: 22px;
    flex-shrink: 0;
    fill: rgba(233, 238, 242, 0.72);
    transition: transform 160ms ease;
  }
  .picker__chev.is-open {
    transform: rotate(180deg);
  }
  .pages-switch {
    position: relative;
    display: flex;
    height: 54px;
    padding: 3px;
    border-radius: 16px;
    box-sizing: border-box;
    background: var(--remote-control-ground);
    border: 1px solid var(--remote-control-line);
    flex-shrink: 0;
  }
  .pages-switch__ind {
    position: absolute;
    left: 3px;
    top: 3px;
    width: 56px;
    height: 46px;
    border-radius: 13px;
    background: var(--remote-select);
    transition: transform var(--remote-slide);
    pointer-events: none;
  }
  .seg {
    position: relative;
    width: 56px;
    border: 0;
    padding: 0;
    background: none;
    display: grid;
    place-items: center;
    cursor: pointer;
    color: rgba(233, 238, 242, 0.72);
    transition: color 200ms ease;
  }
  .seg.is-on {
    color: #7ed6bc;
  }
  .seg svg {
    width: 22px;
    height: 22px;
  }
  .pages {
    position: relative;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }
  .track {
    position: absolute;
    left: 0;
    top: 0;
    width: 200%;
    height: 100%;
    display: flex;
    transition: transform var(--remote-page);
  }
  .page {
    position: relative;
    width: 50%;
    height: 100%;
    overflow: hidden;
  }
  /* C10: shorter than its floors, Remote scrolls under the top bar. */
  .page--remote {
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-width: none;
  }
  .page--remote::-webkit-scrollbar {
    display: none;
  }
  /* Settings keeps its own text selection, for the fields typed into. */
  .page--settings {
    user-select: text;
    -webkit-user-select: text;
  }
  .told {
    position: absolute;
    left: 16px;
    right: 16px;
    bottom: calc(76px + env(safe-area-inset-bottom, 0px));
    padding: 10px 14px;
    border-radius: 12px;
    background: #16232c;
    border: 1px solid rgba(233, 238, 242, 0.14);
    font-size: 14px;
    color: var(--accent-warn);
    z-index: 20;
  }
  /* Focusable, so the phone's keyboard opens for it, and out of sight; at
     the top, where a keyboard coming up never covers it. */
  .type {
    position: absolute;
    left: 0;
    top: 0;
    width: 1px;
    height: 1px;
    opacity: 0;
    border: 0;
    padding: 0;
    font-size: 16px;
    pointer-events: none;
  }
</style>
