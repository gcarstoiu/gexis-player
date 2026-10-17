<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **First use, part 2: make it yours** (ADR-0149; Phase 14, `ph-first-use`;
  Claude Design's `Setup Prototype.dc.html`, the screens after Joining).

  On the phone, from the home network, at the player's own address: how you
  listen, then what the screen shows. **Nothing is written until Finish**,
  except what a step does there and then - Plexamp's download and its claim
  code, a Bluetooth phone accepted, a network share added - so Back and
  the review change only the page's answers. Finish sends the answers as
  settings in one request; the core writes them, switches on what downloads
  and follows it (ADR-0128), and this page shows that to the end.

  The path follows the design's `p2Path()`; a step opened from the review
  goes back to it.
-->
<script>
  import { onMount } from 'svelte';
  import mark from '../assets/gexis-mark.svg';
  import lyrionIcon from '../assets/icon-lyrion.svg';
  import spotifyIcon from '../assets/icon-spotify.png';
  import btIcon from '../assets/icon-bluetooth.png';
  import PanelPreview from './personalise/PanelPreview.svelte';
  import { loadSettings, settingValues, settingsDevice, listItems, listAction, writeSetting } from '../lib/settings.js';
  import { pairing, components, settling, answerPairing, personaliseLater } from '../lib/state.js';

  let { onclose } = $props();

  //: Section accents (the design's `C`).
  const C = { music: '#b0bcc4', lyr: '#9fb4e8', fold: '#f2a48f', browse: '#8fd9a8', spo: '#7ed6bc', bt: '#d8c88f',
              scr: '#c8a2d8', idle: '#e8a0b4', stby: '#8fc4d8', plex: '#e0a758', rev: '#7ed6bc' };
  const STEP = { listen: ['Listen', C.music], mix: ['Listen', C.music], lyrion: ['Lyrion', C.lyr], folders: ['Folders', C.fold],
                 plexamp: ['Plexamp', C.plex], plexsign: ['Plex sign-in', C.plex], browse: ['Browse', C.browse],
                 spotify: ['Spotify', C.spo], bluetooth: ['Bluetooth', C.bt], visualiser: ['Visualiser', C.scr],
                 wait: ['While it waits', C.idle], idle: ['When idle', C.idle], standby: ['Standby', C.stby], review: ['Review', C.rev] };
  const NAV = [['ext', 'Extended', 'Full Lyrion navigation, including apps.'], ['simple', 'Simple', 'Library browse, artists, playlists and radio from Lyrion.'], ['off', 'Off', 'Only what’s playing.']];
  const SKINS = [['vu', 'VU meters'], ['viz', 'Spectrum'], ['vs', 'VU meters + spectrum'], ['turn', 'Turntables'], ['tape', 'Tapes'], ['all', 'All']];
  const CORPUS = { vu: 'VU meters', viz: 'Spectrum', vs: 'VU meters + spectrum', turn: 'Turntables', tape: 'Tapes', all: 'All' };
  const ANIM = { turn: ['Animate turntables', 'The record turns and the tonearm follows the track.'], tape: ['Animate tapes', 'The reels turn.'], all: ['Animate turntables and tapes', 'Records and reels turn.'] };
  const BGS = ['Gexis wallpapers', 'Artist pictures', 'Black'], WBGS = ['Gexis wallpapers', 'Black'], STYLES = ['Calm', 'Colourful', 'Psychedelic'];
  const AFTER = [2, 10, 30];
  const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const HOURS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0')), QUARTERS = ['00', '15', '30', '45'];
  const KNAV = { ext: 'lib', simple: 'simple', off: 'now' };

  // -- the answers ----------------------------------------------------------
  let loaded = $state(false);
  let first = $state(true);
  let screen = $state('listen');
  let ret = $state(null);
  let skipped = $state({});
  let preset = $state(null);
  let mix = $state({ lyr: true, plex: false, spo: true, bt: true });
  let lyr = $state({ state: 'looking', server: null });
  let lyrWhere = $state('here');
  let lyrAddrOpen = $state(false);
  let lyrAddr = $state('');
  let browse = $state('ext');
  let plexOn = $state(false);
  let plexSkipped = $state(false);
  let plexState = $state('code');
  let claim = $state('');
  let claimError = $state(null);
  let spotify = $state(true);
  let bt = $state(true);
  let trusted = $state([]);
  let vizOn = $state(true);
  let vizAfter = $state(10);
  let skin = $state('vu');
  let animate = $state(true);
  let rpm = $state(33);
  let waitClock = $state(true);
  let waitBg = $state('Gexis wallpapers');
  let styles = $state(['Calm', 'Colourful']);
  let wallStyle = $state('Calm');
  let idleOn = $state(true);
  let idleBg = $state('Gexis wallpapers');
  let clock = $state(true);
  let weather = $state(false);
  let loc = $state('');
  let standby = $state(false);
  let ivs = $state([{ from: '23:00', until: '07:00', days: DAYS.slice() }]);
  let ivPick = $state(null);
  //: Network shares: the saved ones, and the step of adding one.
  let shares = $state([]);
  let shareStep = $state(null);
  let shareServers = $state([]);
  let shareSrv = $state(null);
  let shareFound = $state([]);
  let shareUser = $state('');
  let sharePw = $state('');
  let shareAddr = $state('');
  let shareError = $state(null);
  //: Finishing: the core's answer, then the downloads it follows.
  let finishing = $state(false);
  let finished = $state(null);
  let finishError = $state(null);
  let putOff = $state(false);

  const name = $derived(($settingsDevice.name || 'the player').trim());
  const net = $derived(typeof $settingValues.wifi === 'string' && $settingValues.wifi ? $settingValues.wifi : 'your network');
  const headless = $derived($settingValues.headless === true);
  const time = $derived(new Date().toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: $settingValues.clock_format === '12 h' }));

  // The design's derived flags (`d(s)`).
  const isLyr = $derived(preset === 'mine' || (preset === 'custom' && mix.lyr));
  const isPlex = $derived(preset === 'plex' || (preset === 'custom' && mix.plex));
  const isSpo = $derived(preset !== 'custom' || mix.spo);
  const isBt = $derived(preset !== 'custom' || mix.bt);
  const waitShown = $derived(!isLyr || browse === 'off');
  const here = $derived(isLyr && lyr.state !== 'found' && lyrWhere === 'here');
  const marks = $derived([isLyr && 'lyr', isPlex && 'plex', isSpo && 'spo', isBt && 'bt'].filter(Boolean));
  const path = $derived.by(() => {
    const p = ['listen'];
    if (preset === 'custom') p.push('mix');
    if (isLyr && lyr.state !== 'found') { p.push('lyrion'); if (lyrWhere === 'here') p.push('folders'); }
    if (isLyr && !headless) p.push('browse');
    if (isPlex) { p.push('plexamp'); if (!plexSkipped) p.push('plexsign'); }
    if (isSpo) p.push('spotify');
    if (isBt) p.push('bluetooth');
    if (!headless) p.push('visualiser', ...(waitShown ? ['wait'] : []), 'idle', 'standby');
    return p;
  });
  const rail = $derived([...new Set(path.map((x) => STEP[x][0]))]);
  const stepName = $derived(STEP[screen]?.[0] ?? '');
  const accent = $derived(STEP[screen]?.[1] ?? C.rev);
  const at = $derived(rail.indexOf(stepName));
  const crumb = $derived(ret === 'review' ? `Review · ${stepName}` : at >= 0 ? `Step ${at + 1} of ${rail.length}` : 'Make it yours');

  // Plexamp's download, as the core reports it (ADR-0100).
  const plex = $derived($components?.plexamp ?? null);
  const plexPct = $derived(!plex ? 0 : plex.state === 'installed' ? 100
    : plex.total ? Math.min(99, Math.round(((plex.received ?? 0) / plex.total) * 100))
      : plex.share != null ? Math.min(99, Math.round(plex.share * 100)) : plexOn ? 2 : 0);
  const plexIn = $derived(plex?.state === 'installed');

  // -- loading --------------------------------------------------------------
  function pick(value, options, fallback) {
    return options.includes(value) ? value : fallback;
  }
  function nearestAfter(minutes) {
    const m = Number(minutes) || 10;
    return AFTER.reduce((a, b) => (Math.abs(b - m) < Math.abs(a - m) ? b : a));
  }
  function fromSettings(v) {
    spotify = v.spotify_enabled !== false;
    bt = v.bt_enabled !== false;
    browse = v.lms_library === false ? 'off' : v.lms_extended_nav ? 'ext' : 'simple';
    vizAfter = nearestAfter(v.viz_timeout);
    skin = Object.keys(CORPUS).find((k) => CORPUS[k] === v.skin_corpus) ?? 'vu';
    animate = v.skin_motion !== false;
    rpm = v.record_speed === '45 rpm' ? 45 : 33;
    waitClock = v.waiting_clock !== false;
    waitBg = v.waiting_background === 'Black' ? 'Black' : 'Gexis wallpapers';
    if (Array.isArray(v.wallpaper_styles) && v.wallpaper_styles.length) styles = v.wallpaper_styles.filter((s) => STYLES.includes(s));
    if (!styles.length) styles = ['Calm'];
    wallStyle = styles[0];
    idleBg = pick(v.idle_background, BGS, 'Gexis wallpapers');
    clock = v.idle_clock !== false;
    loc = v.weather_location ?? '';
    standby = v.standby_schedule === true;
    if (Array.isArray(v.standby_times) && v.standby_times.length) ivs = structuredClone(v.standby_times);
    // **A new player starts from part 2's own defaults** (the design's):
    // the visualiser and the idle screen on, the weather off until a place
    // is given. Asked again from Settings, it starts from what the player has.
    vizOn = first ? true : v.visualiser_skins === true;
    idleOn = first ? true : v.idle_enabled === true;
    weather = first ? false : v.idle_weather === true && !!loc;
    plexOn = v['plexamp.enabled'] === true;
  }

  async function lookForLyrion() {
    lyr = { state: 'looking', server: null };
    const got = await listItems('lms_server');
    const found = (got.items ?? []).filter((i) => !String(i.meta ?? '').startsWith('This player'));
    const current = found.find((i) => i.state === 'current');
    const server = current ?? found[0] ?? null;
    lyr = server ? { state: 'found', server: { name: server.name, address: server.address ?? server.name } } : { state: 'none', server: null };
  }
  async function loadShares() {
    const got = await listItems('lyrion-server.shares');
    const items = got.items ?? [];
    shares = items.filter((i) => !i.server);
    shareServers = items.filter((i) => i.server);
  }
  async function loadTrusted() {
    const got = await listItems('bt_trusted');
    trusted = got.items ?? [];
  }

  onMount(async () => {
    loadSettings();
    try {
      const r = await fetch('/personalise');
      if (r.ok) first = (await r.json()).first !== false;
    } catch { /* a first run is assumed */ }
    lookForLyrion();
    loadTrusted();
  });
  let seeded = false;
  $effect(() => {
    const v = $settingValues;
    if (seeded || !Object.keys(v).length) return;
    seeded = true;
    fromSettings(v);
    loaded = true;
  });

  // -- moving ----------------------------------------------------------------
  function go(id, back = null) {
    screen = id;
    ret = back;
    ivPick = null;
    if (id === 'folders' && !shares.length && !shareServers.length) loadShares();
    if (id === 'bluetooth') loadTrusted();
    if (typeof window !== 'undefined') window.scrollTo({ top: 0 });
  }
  function advance(skip = false) {
    skipped = { ...skipped, [screen]: skip };
    if (ret === 'review') {
      if (['listen', 'mix', 'lyrion', 'plexamp'].includes(screen)) {
        const nx = path.slice(path.indexOf(screen) + 1).find((x) => ['mix', 'lyrion', 'folders', 'browse', 'plexamp', 'plexsign'].includes(x));
        if (nx) return go(nx, 'review');
      }
      return go('review');
    }
    const i = path.indexOf(screen);
    if (screen === 'review') return finish();
    go(i >= 0 && i < path.length - 1 ? path[i + 1] : 'review');
  }
  function back() {
    if (ret) return go(ret);
    const i = path.indexOf(screen);
    if (screen === 'review') return go(path[path.length - 1]);
    if (i > 0) go(path[i - 1]);
  }

  // -- the steps that act at once --------------------------------------------
  async function downloadPlexamp() {
    plexOn = true;
    plexSkipped = false;
    const r = await writeSetting('plexamp.enabled', true);
    if (!r.ok) {
      plexOn = false;
      claimError = 'Plexamp could not start downloading. Try again, or skip and add it later in Settings.';
      return;
    }
    advance();
  }
  async function sendClaim() {
    claimError = null;
    const code = claim.trim();
    if (!code) return;
    const r = await writeSetting('plexamp.claim_token', code);
    if (r.ok) plexState = 'ok';
    else claimError = 'Plexamp did not take that code. Get a new one and paste it straight away.';
  }
  async function forgetPhone(item) {
    await listAction('bt_trusted', { name: item.address ?? item.name, action: 'forget' });
    loadTrusted();
  }
  async function answer(accept) {
    await answerPairing(accept).catch(() => {});
    setTimeout(loadTrusted, 1500);
  }
  async function scanShares() {
    shareStep = 'scan';
    shareError = null;
    await loadShares();
    shareStep = 'list';
  }
  async function showShares(server, user = null, password = null) {
    shareError = null;
    const r = await listAction('lyrion-server.shares', { name: server.name, action: 'browse', server: server.server, user, password });
    if (r.login) {
      shareSrv = server;
      shareStep = 'login';
      if (user) shareError = 'That user or password was not accepted.';
      return;
    }
    if (!r.ok) {
      shareError = r.error ?? 'Could not read its shares.';
      return;
    }
    shareSrv = { ...server, user, password };
    shareFound = r.items ?? [];
    shareStep = 'browse';
  }
  async function addShare(address, user, password) {
    shareError = null;
    const r = await listAction('lyrion-server.shares', { name: address, action: 'add', user: user ?? (address.startsWith('//') ? 'guest' : null), password: password ?? null });
    if (!r.ok) {
      shareError = r.error ?? 'Could not add it. Check the address and try again.';
      return;
    }
    shareStep = null;
    shareAddr = '';
    shareUser = '';
    sharePw = '';
    loadShares();
  }

  // -- the wallpaper styles: at least one, the preview on the one just picked --
  function toggleStyle(x) {
    const on = styles.includes(x);
    if (on && styles.length === 1) return;
    const next = on ? styles.filter((y) => y !== x) : STYLES.filter((y) => y === x || styles.includes(y));
    const i = STYLES.indexOf(x);
    wallStyle = !on ? x : wallStyle !== x ? wallStyle : [...STYLES.slice(i + 1), ...STYLES.slice(0, i)].find((y) => next.includes(y)) ?? x;
    styles = next;
  }

  // -- standby intervals ------------------------------------------------------
  function setIv(i, f) { ivs = ivs.map((x, k) => (k === i ? { ...x, ...f(x) } : x)); }
  function setTime(i, which, part, v) { setIv(i, (x) => { const [h, m] = x[which].split(':'); return { [which]: part === 'h' ? `${v}:${m}` : `${h}:${v}` }; }); }
  function toggleDay(i, d) {
    const days = ivs[i].days;
    if (days.includes(d) && days.length === 1) return;
    setIv(i, (x) => ({ days: x.days.includes(d) ? x.days.filter((y) => y !== d) : DAYS.filter((y) => y === d || x.days.includes(y)) }));
  }
  function removeIv(i) {
    ivPick = null;
    ivs = ivs.filter((_, k) => k !== i);
    if (!ivs.length) standby = false;
  }
  function flipStandby() {
    standby = !standby;
    ivPick = null;
    if (standby && !ivs.length) ivs = [{ from: '22:00', until: '06:00', days: DAYS.slice() }];
  }
  const daysSaid = (days) => {
    const on = DAYS.filter((d) => days.includes(d));
    return on.length === 7 ? 'every day' : on.join() === 'Mon,Tue,Wed,Thu,Fri' ? 'Mon–Fri' : on.join() === 'Sat,Sun' ? 'weekends' : on.join(', ');
  };
  const ivSaid = (list) => (!list.length ? 'None' : list.length > 1 ? `${list.length} times` : `${list[0].from}–${list[0].until} · ${daysSaid(list[0].days)}`);

  // -- finishing ---------------------------------------------------------------
  //: **The answers as settings** (ADR-0149's table, with the design's steps):
  //: only what part 2 asked, and only what this player has a step for.
  function answersAsSettings() {
    const s = { spotify_enabled: isSpo && spotify, bt_enabled: isBt && bt, lms_enabled: isLyr };
    if (isLyr) {
      if (lyr.state === 'found') s.lms_server = lyr.server.address;
      else if (lyrAddrOpen && lyrAddr.trim()) s.lms_server = lyrAddr.trim();
      else if (here && $settingsDevice.address) s.lms_server = `${$settingsDevice.address}:9000`;
      if (!headless) {
        s.lms_extended_nav = browse === 'ext';
        s.lms_library = browse !== 'off';
      }
    }
    //: **Plugins are only ever switched on here** (decided 2026-10-18): a
    //: preset that leaves one out must not uninstall what the player already
    //: has - asked again from Settings, "Streaming only" would have removed
    //: Plexamp and its sign-in. Removing one stays a choice in Settings ->
    //: Plugins.
    if (here) s['lyrion-server.enabled'] = true;
    if (isPlex && plexOn) s['plexamp.enabled'] = true;
    if (!headless) {
      Object.assign(s, {
        visualiser_skins: vizOn, viz_timeout: vizAfter, skin_corpus: CORPUS[skin], skin_motion: animate,
        record_speed: rpm === 45 ? '45 rpm' : '33 rpm',
        waiting_clock: waitClock, waiting_background: waitBg, waiting_wallpaper_styles: styles,
        idle_enabled: idleOn, idle_background: idleBg, wallpaper_styles: styles, idle_clock: clock,
        idle_weather: weather && !!loc.trim(), standby_schedule: standby && ivs.length > 0,
        standby_times: ivs
      });
      if (loc.trim()) s.weather_location = loc.trim();
    }
    return s;
  }
  async function finish() {
    finishing = true;
    finishError = null;
    try {
      const r = await fetch('/personalise/finish', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: answersAsSettings() })
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(body.error ?? `HTTP ${r.status}`);
      finished = body;
      screen = 'done';
    } catch (err) {
      finishError = "The player didn't take the answers. Check this phone is on the player's network, then try again.";
      console.warn('personalise: finish failed:', err?.message);
    } finally {
      finishing = false;
    }
  }
  async function later() {
    await personaliseLater().catch(() => {});
    putOff = true;
    screen = 'later';
  }

  // -- what Finish shows: each install, followed (ADR-0128) --
  function itemOf(id) { return $settling?.items?.find((i) => i.id === id) ?? null; }
  function pctOf(item) {
    if (!item) return 0;
    if (item.state === 'done') return 100;
    if (item.total) return Math.min(99, Math.round(((item.received ?? 0) / item.total) * 100));
    if (item.share != null) return Math.min(99, Math.round(item.share * 100));
    return 3;
  }
  function doneOf(id) {
    const item = itemOf(id);
    if (item) return item.state === 'done';
    // Nothing followed any more: settled, and gone from the record.
    return !!finished && finished.waiting?.includes(id) && !$settling;
  }

  const looks = $derived(isLyr ? { kind: KNAV[browse] } : { kind: 'wait', marks, clock: waitClock, black: waitBg === 'Black' });
  const idleLook = $derived(idleOn ? { kind: 'clock', clock, weather, black: idleBg === 'Black', bg: idleBg === 'Artist pictures' ? 'artist' : 'wall', style: wallStyle }
    : waitShown ? { kind: 'wait', marks, clock: waitClock, black: waitBg === 'Black', style: wallStyle } : { kind: KNAV[browse] });
  const waitLook = $derived({ kind: 'wait', marks, clock: waitClock, black: waitBg === 'Black', style: wallStyle });

  const canNext = $derived(
    screen === 'listen' ? !!preset
      : screen === 'idle' ? !(idleOn && weather && !loc.trim())
        : screen === 'plexsign' ? false
          : true
  );
  const nextLabel = $derived(ret === 'review' ? 'Save' : screen === 'review' ? 'Finish' : 'Next');
</script>

{#snippet note(tone, title, text)}
  <div class="note note--{tone}"><span class="note__bar"></span><span>{#if title}<b>{title}</b>{/if}<small>{text}</small></span></div>
{/snippet}
{#snippet status(state, text, meta = null)}
  <div class="status">
    {#if state === 'spin'}<span class="spin"></span>{:else if state === 'ok'}<span class="tick">✓</span>{:else}<span class="dot"></span>{/if}
    <span><b>{text}</b>{#if meta}<small>{meta}</small>{/if}</span>
  </div>
{/snippet}
{#snippet srcIcon(k, size = 18)}
  {#if k === 'lyr'}<img src={lyrionIcon} alt="" width={size} height={size} />
  {:else if k === 'spo'}<img src={spotifyIcon} alt="" width={size} height={size} />
  {:else if k === 'bt'}<img src={btIcon} alt="" width={size} height={size} />
  {:else}<span class="p-mark" style="width:{size}px;height:{size}px">P</span>{/if}
{/snippet}
{#snippet sources(list)}
  <span class="srcs">
    {#each list as k (k)}<span class="src">{@render srcIcon(k, 16)}{{ lyr: 'Lyrion', plex: 'Plexamp', spo: 'Spotify', bt: 'Bluetooth' }[k]}</span>{/each}
  </span>
{/snippet}
{#snippet radio(on, label, noteText, fn, extra = null)}
  <button type="button" class="row" class:on onclick={fn}>
    <span class="radio" class:on><span></span></span>
    <span class="row__text"><b>{label}</b>{#if noteText}<small>{noteText}</small>{/if}{#if extra}{@render extra()}{/if}</span>
  </button>
{/snippet}
{#snippet toggle(on, label, noteText, fn, icon = null)}
  <button type="button" class="row" onclick={fn} aria-pressed={on}>
    {#if icon}<span class="row__icon">{@render srcIcon(icon, 20)}</span>{/if}
    <span class="row__text"><b>{label}</b>{#if noteText}<small>{noteText}</small>{/if}</span>
    <span class="switch" class:on><span></span></span>
  </button>
{/snippet}
{#snippet pills(head, opts, sel, fn, multi = false)}
  <div class="pills">
    <div class="head">{head}{#if multi}<span class="any"> · pick any</span>{/if}</div>
    <div class="pills__row">
      {#each opts as x (x)}
        {@const on = multi ? sel.includes(x) : x === sel}
        <button type="button" class="pill" class:pill--multi={multi} class:on style="--a:{accent}" onclick={() => fn(x)}>
          {#if multi}<span class="box">{on ? '✓' : ''}</span>{/if}{typeof x === 'number' ? `${x} min` : x}
        </button>
      {/each}
    </div>
  </div>
{/snippet}
{#snippet prog(label, pct, st = null, ok = false)}
  <div class="card prog">
    <div class="prog__top"><b>{label}</b><span class:prog--done={pct >= 100}>{pct >= 100 ? 'Done' : `${pct}%`}</span></div>
    <div class="prog__bar"><span style="width:{pct}%; background:{pct >= 100 ? C.rev : C.plex}"></span></div>
    {#if st}<div class="prog__st"><span class="box" class:ok>{ok ? '✓' : ''}</span>{st}</div>{/if}
  </div>
{/snippet}
{#snippet preview(look)}
  {#if !headless}<PanelPreview head={`${name}’s screen`} {time} player={name} place={loc.split(',')[0]} {rpm} {animate} style={wallStyle} {...look} />{/if}
{/snippet}

<div class="page">
  <div class="col">
    <header>
      <img class="mark" src={mark} alt="" width="30" height="30" />
      <span class="crumb" style="color:{['done', 'later'].includes(screen) ? C.rev : accent}">{['done', 'later'].includes(screen) ? 'Make it yours' : crumb}</span>
    </header>
    {#if at >= 0 && !['done', 'later'].includes(screen)}
      <div class="progress"><span style="width:{Math.round(((at + 0.65) / rail.length) * 100)}%; background:{accent}"></span></div>
    {/if}

    {#if !loaded}
      {@render status('spin', 'Opening')}
    {:else if screen === 'listen'}
      <h1>How will you listen?</h1>
      <p class="sub">Pick the closest. Change anything after.</p>
      <div class="list">
        {#snippet mineExtra()}
          {@render sources(['lyr', 'spo', 'bt'])}
          {#if lyr.state === 'found'}
            <span class="tile-foot"><span class="tile-dot" style="background:#7ed6bc"></span>Lyrion found on {net}<em>{lyr.server.name !== lyr.server.address ? `${lyr.server.name} · ` : ''}{lyr.server.address}</em></span>
          {:else if lyr.state === 'none'}
            <span class="tile-foot"><span class="tile-dot"></span>No Lyrion found on {net}<em>Set it up on the next screen</em></span>
          {:else}
            <span class="tile-foot"><span class="spin spin--small"></span>Looking for Lyrion on {net}</span>
          {/if}
        {/snippet}
        {#snippet plexExtra()}{@render sources(['plex', 'spo', 'bt'])}{/snippet}
        {#snippet streamExtra()}{@render sources(['spo', 'bt'])}{/snippet}
        {@render radio(preset === 'mine', 'My music + streaming', '', () => (preset = 'mine'), mineExtra)}
        {@render radio(preset === 'plex', 'Plex + streaming', '', () => (preset = 'plex'), plexExtra)}
        {@render radio(preset === 'stream', 'Streaming only', '', () => (preset = 'stream'), streamExtra)}
      </div>
      <div class="head">Or mix your own</div>
      <div class="list">
        {#snippet ownExtra()}{@render sources(['lyr', 'plex', 'spo', 'bt'])}{/snippet}
        {@render radio(preset === 'custom', 'My own mix', 'Choose from any of these on the next screen.', () => (preset = 'custom'), ownExtra)}
      </div>
    {:else if screen === 'mix'}
      <h1>My own mix</h1>
      <div class="head">Your own music</div>
      <div class="list">
        {@render toggle(mix.lyr, 'Lyrion', 'Browse your files on the screen.', () => (mix = { ...mix, lyr: !mix.lyr }), 'lyr')}
        {@render toggle(mix.plex, 'Plexamp', 'Your Plex library, from its app.', () => (mix = { ...mix, plex: !mix.plex }), 'plex')}
        <div class="row row--ghost"><span class="row__text"><b>Library service</b><small>The next one lands here.</small></span><span class="tag">Next phase</span></div>
      </div>
      <div class="head">Streaming</div>
      <div class="list">
        {@render toggle(mix.spo, 'Spotify', '', () => (mix = { ...mix, spo: !mix.spo }), 'spo')}
        {@render toggle(mix.bt, 'Bluetooth', '', () => (mix = { ...mix, bt: !mix.bt }), 'bt')}
      </div>
      {#if !mix.lyr && !mix.plex && !mix.spo && !mix.bt}
        {@render note('warn', 'Nothing to play', `With none of these, ${name} has nothing to play from.`)}
      {/if}
    {:else if screen === 'lyrion'}
      <h1>Where should Lyrion run?</h1>
      <div class="card status-card">
        {@render status('none', `No Lyrion found on ${net}`)}
        {#if lyrAddrOpen}
          <label class="field"><span>Server address</span><input bind:value={lyrAddr} placeholder="192.0.2.31:9000" autocomplete="off" /><small>{name} uses this address, and Settings can change it later.</small></label>
        {:else}
          <button type="button" class="link" onclick={() => (lyrAddrOpen = true)}>Add its address</button>
        {/if}
      </div>
      <div class="where">
        {#each [['here', 'On this player'], ['pc', 'On a computer or NAS']] as w (w[0])}
          <button type="button" class="where__opt" class:on={lyrWhere === w[0]} onclick={() => (lyrWhere = w[0])}>
            <span class="radio" class:on={lyrWhere === w[0]}><span></span></span>{w[1]}
          </button>
        {/each}
      </div>
      <div class="split">
        <div><div class="head">{name} does</div>{#each lyrWhere === 'here' ? ['Installs Lyrion', 'Adds your folders', 'Runs the first scan'] : ['Finds it and plays from it'] as t (t)}<p>{t}</p>{/each}</div>
        <div><div class="head">{lyrWhere === 'here' ? 'Later, in Lyrion' : 'You, on that machine'}</div>{#each lyrWhere === 'here' ? ['Rescan after adding music', 'Everything else'] : ['Install Lyrion', 'Add your music', 'Run the scans'] as t (t)}<p>{t}</p>{/each}</div>
      </div>
      {#if lyrWhere !== 'here'}<div class="card addr"><small>Get Lyrion at</small><b>lyrion.org</b></div>{/if}
    {:else if screen === 'folders'}
      <h1>Where is your music?</h1>
      <p class="sub">Lyrion reads all of these.</p>
      <div class="head">Lyrion reads</div>
      <div class="list">
        <div class="row"><span class="row__text"><b>Music folder</b><small>On the player, shared on {net}.</small></span><span class="tag tag--ok">Always</span></div>
        <div class="row"><span class="row__text"><b>USB drive</b><small>Any plugged into the player.</small></span><span class="tag tag--ok">Always</span></div>
      </div>
      {#if shares.length && !shareStep}
        <div class="head">Network shares</div>
        <div class="list">{#each shares as s (s.address ?? s.name)}<div class="row"><span class="row__text"><b>{s.name}</b>{#if s.meta}<small>{s.meta}</small>{/if}</span><span class="tag tag--ok">Added</span></div>{/each}</div>
      {/if}
      {#if !shareStep}
        <button type="button" class="btn" onclick={scanShares}>{shares.length ? 'Add another share' : 'Add a network share'}</button>
      {:else if shareStep === 'scan'}
        {@render status('spin', 'Looking for shares', 'Servers that announce themselves answer within a few seconds.')}
      {:else if shareStep === 'list'}
        <div class="head">Network shares</div>
        <div class="list">
          {#each shareServers as s (s.name)}
            <button type="button" class="row" onclick={() => showShares(s)}><span class="row__text"><b>{s.name}</b><small>{s.server?.host}</small></span><span class="chev"></span></button>
          {:else}
            <div class="row"><span class="row__text"><small>No servers announced themselves.</small></span></div>
          {/each}
        </div>
        <p class="p">Not in the list? Some servers do not announce themselves - add the share by its address.</p>
        <button type="button" class="btn" onclick={() => (shareStep = 'addr')}>Add by address</button>
        <button type="button" class="btn btn--ghost" onclick={() => (shareStep = null)}>Cancel</button>
      {:else if shareStep === 'login'}
        {@render note('info', `Sign in to ${shareSrv?.name}`, 'It shows its shares only to a user it knows. The same user and password are used to mount the one you choose.')}
        <label class="field"><span>User</span><input bind:value={shareUser} autocomplete="off" /></label>
        <label class="field"><span>Password</span><input type="password" bind:value={sharePw} /></label>
        <button type="button" class="btn" onclick={() => showShares(shareSrv, shareUser.trim(), sharePw)}>Show shares</button>
        <button type="button" class="btn btn--ghost" onclick={() => (shareStep = 'list')}>Back</button>
      {:else if shareStep === 'browse'}
        <div class="head">Shares on {shareSrv?.name}</div>
        <div class="list">
          {#each shareFound as f (f.address)}
            <button type="button" class="row" onclick={() => addShare(f.address, shareSrv?.user, shareSrv?.password)}><span class="row__text"><b>{f.name}</b><small>{f.address}</small></span><span class="chev"></span></button>
          {:else}
            <div class="row"><span class="row__text"><small>{shareSrv?.name} shows no shares to this user.</small></span></div>
          {/each}
        </div>
        <p class="p">Tap one to add it.</p>
        <button type="button" class="btn btn--ghost" onclick={() => (shareStep = 'list')}>Back</button>
      {:else if shareStep === 'addr'}
        {@render note('info', 'Add a share', 'A folder on a NAS or a computer. SMB needs a user and password; NFS needs only the address.')}
        <label class="field"><span>Address</span><input bind:value={shareAddr} placeholder="//nas/music or nas:/music" autocomplete="off" /></label>
        <label class="field"><span>User (SMB)</span><input bind:value={shareUser} autocomplete="off" /></label>
        <label class="field"><span>Password (SMB)</span><input type="password" bind:value={sharePw} /></label>
        <button type="button" class="btn" onclick={() => shareAddr.trim() && addShare(shareAddr.trim(), shareUser.trim() || null, sharePw || null)}>Add</button>
        <button type="button" class="btn btn--ghost" onclick={() => (shareStep = 'list')}>Back</button>
      {/if}
      {#if shareError}{@render note('warn', '', shareError)}{/if}
      <p class="p">These become Lyrion’s music folders when it installs.</p>
    {:else if screen === 'browse'}
      <h1>Browse on the screen</h1>
      <p class="sub">A Lyrion app on your phone works with any of these.</p>
      {@render preview({ kind: KNAV[browse] })}
      <div class="list">{#each NAV as n (n[0])}{@render radio(browse === n[0], n[1], n[2], () => (browse = n[0]))}{/each}</div>
    {:else if screen === 'plexamp'}
      <h1>Plexamp</h1>
      <p class="sub">Your Plex library, played on {name}.</p>
      {#if plexOn}
        {@render prog(plexIn ? 'Plexamp is in' : 'Downloading Plexamp', plexPct)}
      {:else}
        <div class="list"><div class="row"><span class="row__icon">{@render srcIcon('plex', 20)}</span><span class="row__text"><b>Plexamp</b><small>From Plex, downloaded to the player.</small></span></div></div>
        <ol class="num"><li>Download Plexamp</li><li>Sign in to Plex with a claim code</li></ol>
        <p class="p">Skip, and add Plexamp later from Settings → Plugins.</p>
      {/if}
      {#if claimError}{@render note('warn', '', claimError)}{/if}
    {:else if screen === 'plexsign'}
      <h1>Sign in to Plex</h1>
      <p class="sub">Get a claim code from plex.tv while Plexamp downloads, then paste it here.</p>
      {@render prog(plexIn ? 'Plexamp is installed' : 'Downloading Plexamp', plexPct)}
      <a class="btn" href="https://plex.tv/claim" target="_blank" rel="noopener">Open plex.tv/claim</a>
      {#if plexState === 'ok'}
        {@render note('info', '', 'Paste the claim code here within four minutes.')}
        <label class="field"><span>Claim code</span><input value={claim} readonly /></label>
        {@render status('ok', `${name} has its claim code`, 'Plexamp signs in with it')}
        <p class="p">Open Plexamp on your phone and pick {name} as the player.</p>
      {:else}
        {#if claimError}
          {@render note('warn', 'That code has run out', 'Claim codes last four minutes. Get a new one and paste it straight away.')}
        {:else}
          {@render note('info', '', plexIn ? 'Paste the claim code here within four minutes.' : 'A claim code lasts four minutes. Paste it here once Plexamp is installed.')}
        {/if}
        <label class="field"><span>Claim code</span><input bind:value={claim} placeholder={plexIn ? 'claim-…' : 'Opens once Plexamp is installed'} readonly={!plexIn} autocomplete="off" /></label>
        <p class="p">Or skip, and sign in later from Settings → Plugins → Plexamp.{plexIn ? '' : ' The download carries on.'}</p>
      {/if}
    {:else if screen === 'spotify'}
      <h1>Spotify</h1>
      <p class="sub">Built in. {name} appears in the Spotify app on your phone.</p>
      <div class="list">{@render toggle(spotify, 'Spotify Connect', '', () => (spotify = !spotify), 'spo')}</div>
      {#if spotify}
        <div class="card cast">
          <div class="cast__phone"><small>Connect to a device</small><span>This phone</span><span class="cast__on">{@render srcIcon('spo', 14)}{name}</span></div>
          <p>Tap the devices icon, then {name}.</p>
        </div>
      {/if}
    {:else if screen === 'bluetooth'}
      <h1>Bluetooth</h1>
      <p class="sub">Any phone can play to {name} over Bluetooth. Pair one now, or later from Settings.</p>
      {#if $pairing?.state === 'asking' && bt}
        <div class="card code">
          <small>{$pairing.device ?? 'A phone'} wants to pair</small>
          <b>{($pairing.code ?? '').length === 6 ? `${$pairing.code.slice(0, 3)} ${$pairing.code.slice(3)}` : ($pairing.code ?? '')}</b>
          <p>Check it matches your phone, then accept.</p>
        </div>
      {:else}
        <div class="list">{@render toggle(bt, 'Enabled', '', () => (bt = !bt), 'bt')}</div>
        {#if !bt}
          {@render note('info', '', `Phones can’t find ${name}. Turn it on any time in Settings → Bluetooth.`)}
        {:else}
          {#if $pairing?.state === 'accepted'}{@render status('ok', `${$pairing.device ?? 'The phone'} is paired`)}{:else}{@render status('spin', 'Waiting for a phone', `Tap ${name} in its Bluetooth list`)}{/if}
          {#if trusted.length}
            <div class="head">Paired</div>
            <div class="list">{#each trusted as t (t.address ?? t.name)}<div class="row"><span class="row__text"><b>{t.name}</b>{#if t.meta}<small>{t.meta}</small>{/if}</span><button type="button" class="link" onclick={() => forgetPhone(t)}>Forget</button></div>{/each}</div>
          {/if}
        {/if}
      {/if}
    {:else if screen === 'visualiser'}
      <h1>While music plays</h1>
      <p class="sub">What the screen shows with the music.</p>
      {@render preview(vizOn ? { kind: skin } : { kind: isLyr ? KNAV[browse] : 'now' })}
      <div class="list">{@render toggle(vizOn, 'Visualiser', 'Takes the screen while music plays.', () => (vizOn = !vizOn))}</div>
      {#if vizOn}
        {@render pills('Starts after', AFTER, vizAfter, (x) => (vizAfter = x))}
        <div class="head">Skins</div>
        <div class="skins">
          {#each SKINS as x (x[0])}
            <button type="button" class="skin" class:on={skin === x[0]} style="--a:{accent}" onclick={() => (skin = x[0])}>
              <PanelPreview kind={x[0]} {rpm} animate={false} />
              <span>{x[1]}</span>
            </button>
          {/each}
        </div>
        {#if ANIM[skin]}<div class="list">{@render toggle(animate, ANIM[skin][0], ANIM[skin][1], () => (animate = !animate))}</div>{/if}
        {#if (skin === 'turn' || skin === 'all') && animate}
          <div class="seg"><div class="head">Record speed</div><div class="seg__row">{#each [33, 45] as r (r)}<button type="button" class:on={rpm === r} style="--a:{accent}" onclick={() => (rpm = r)}>{r} rpm</button>{/each}</div></div>
        {/if}
        {@render note('info', '', 'How each skin moves and reacts to the music is in Settings → Display → Visualiser.')}
      {/if}
    {:else if screen === 'wait'}
      <h1>While it waits</h1>
      <p class="sub">The screen shows the sources over a picture until something plays.</p>
      {@render preview(waitLook)}
      <div class="list">{@render toggle(waitClock, 'Clock', 'Time, date and the player’s name.', () => (waitClock = !waitClock))}</div>
      {@render pills('Background', WBGS, waitBg, (x) => (waitBg = x))}
      {#if waitBg === 'Gexis wallpapers'}
        {@render pills('Wallpaper styles', STYLES, styles, toggleStyle, true)}
        {@render note('info', '', 'A free Pixabay key unlocks more wallpapers. Add it later in Settings → Display.')}
      {/if}
    {:else if screen === 'idle'}
      <h1>When nothing plays</h1>
      <p class="sub">What the screen shows after a while with no music and no touch.</p>
      {@render preview(idleLook)}
      <div class="list">{@render toggle(idleOn, 'Idle screen', 'After 5 min with no music.', () => (idleOn = !idleOn))}</div>
      {#if idleOn}
        {@render pills('Background', BGS, idleBg, (x) => (idleBg = x))}
        {#if idleBg === 'Gexis wallpapers'}
          {@render pills('Wallpaper styles', STYLES, styles, toggleStyle, true)}
          {@render note('info', '', 'A free Pixabay key unlocks more wallpapers. Add it later in Settings → Display.')}
        {/if}
        <div class="list">
          {@render toggle(clock, 'Clock', '', () => (clock = !clock))}
          {@render toggle(weather, 'Weather', '', () => (weather = !weather))}
        </div>
        {#if weather}<label class="field"><span>Weather location</span><input bind:value={loc} placeholder="e.g. Lisbon, Portugal" autocomplete="off" /></label>{/if}
      {/if}
    {:else if screen === 'standby'}
      <h1>Off at night?</h1>
      <p class="sub">The screen turns off at set hours when nothing plays.</p>
      {@render preview(standby ? { kind: 'off' } : idleLook)}
      <div class="list">{@render toggle(standby, 'Night standby', 'The screen turns off.', flipStandby)}</div>
      {#if standby}
        <div class="ivs">
          {#each ivs as iv, i (i)}
            <div class="card iv">
              <div class="iv__times">
                {#each [['from', 'From'], ['until', 'Until']] as [w, label] (w)}
                  <button type="button" class="iv__time" class:on={ivPick?.i === i && ivPick?.which === w} onclick={() => (ivPick = ivPick?.i === i && ivPick?.which === w ? null : { i, which: w })}><small>{label}</small>{iv[w]}</button>
                {/each}
                <button type="button" class="link" onclick={() => removeIv(i)}>Remove</button>
              </div>
              {#if ivPick?.i === i}
                {@const [hh, mm] = iv[ivPick.which].split(':')}
                <div class="grid24">{#each HOURS as h (h)}<button type="button" class:on={h === hh} onclick={() => setTime(i, ivPick.which, 'h', h)}>{h}</button>{/each}</div>
                <div class="grid4">{#each QUARTERS as q (q)}<button type="button" class:on={q === mm} onclick={() => setTime(i, ivPick.which, 'm', q)}>:{q}</button>{/each}</div>
              {/if}
              <div class="days">{#each DAYS as d (d)}<button type="button" class:on={iv.days.includes(d)} onclick={() => toggleDay(i, d)}>{d}</button>{/each}</div>
            </div>
          {/each}
          <button type="button" class="btn btn--ghost" disabled={ivs.length >= 6} onclick={() => { ivPick = null; ivs = [...ivs, { from: '22:00', until: '06:00', days: DAYS.slice() }]; }}>Add standby time</button>
        </div>
      {/if}
    {:else if screen === 'review'}
      <h1>Your setup</h1>
      <p class="sub">Tap a row to change it.</p>
      {@render preview(looks)}
      {@const music = preset === 'mine' ? (lyr.state === 'found' ? `Lyrion · found on ${net}` : lyrWhere === 'here' ? 'Lyrion, on this player' : 'Lyrion, on another machine')
        : preset === 'stream' ? 'Streaming only' : preset === 'plex' ? 'Plexamp' : [isLyr && 'Lyrion', isPlex && 'Plexamp'].filter(Boolean).join(' · ') || 'No library'}
      <div class="list">
        {#snippet hub(label, meta, id, tag = null)}
          <button type="button" class="row" onclick={() => go(id, 'review')}>
            <span class="row__text"><b>{label}</b><small>{meta}</small></span>
            {#if tag}<span class="tag" class:tag--ok={tag[1] === 'ok'} class:tag--warn={tag[1] === 'warn'}>{tag[0]}</span>{:else if skipped[id]}<span class="tag">Skipped</span>{/if}
            <span class="chev"></span>
          </button>
        {/snippet}
        {@render hub('Music', music, 'listen')}
        {#if here}{@render hub('Folders', ['Music folder', 'USB', ...shares.map((s) => s.name)].join(' · '), 'folders')}{/if}
        {#if isLyr && !headless}{@render hub('Browse', NAV.find((n) => n[0] === browse)[1], 'browse')}{/if}
        {#if isPlex}{@render hub('Plex', !plexOn ? 'Not installed · later, from Settings' : plexState === 'ok' ? 'Claim code given' : `${plexIn ? 'Installed' : 'Downloading'} · sign in later`, plexOn ? 'plexsign' : 'plexamp', !plexOn ? ['Skipped', 'plain'] : plexState === 'ok' ? ['Signed in', 'ok'] : ['Later', 'warn'])}{/if}
        {#if isSpo}{@render hub('Spotify', spotify ? 'On' : 'Off', 'spotify')}{/if}
        {#if isBt}{@render hub('Bluetooth', !bt ? 'Off' : trusted.length ? trusted.map((t) => t.name).join(' · ') : 'On · no phone yet', 'bluetooth', trusted.length && bt ? ['Paired', 'ok'] : null)}{/if}
        {#if !headless}
          {@render hub('Visualiser', vizOn ? SKINS.find((x) => x[0] === skin)[1] : 'Off', 'visualiser')}
          {#if waitShown}{@render hub('While it waits', [waitBg, waitClock && 'Clock'].filter(Boolean).join(' · '), 'wait')}{/if}
          {@render hub('When idle', idleOn ? [idleBg, clock && 'Clock', weather && 'Weather'].filter(Boolean).join(' · ') : 'Off', 'idle')}
          {@render hub('Standby', standby ? ivSaid(ivs) : 'Off', 'standby')}
        {/if}
      </div>
      {#if here}<p class="p">Lyrion installs and scans your folders when you finish.</p>{/if}
      {#if finishError}{@render note('warn', '', finishError)}{/if}
    {:else if screen === 'done'}
      <div class="party" aria-hidden="true"><span class="party__badge">✓</span><span class="note1">♪</span><span class="note2">♫</span></div>
      <h1 class="hero">{name} is ready</h1>
      {#if here}
        {@const done = doneOf('lyrion-server')}
        <div class="head">Lyrion</div>
        {@render prog(done ? 'Installed' : 'Installing', done ? 100 : pctOf(itemOf('lyrion-server')), done ? 'Folders added, scan started' : null, true)}
        {#if done}{@render note('info', '', 'A large library can take hours to scan. Music shows up as Lyrion finds it.')}{/if}
      {/if}
      {#if isPlex && plexOn}
        {@const done = doneOf('plexamp') || plexIn}
        <div class="head">Plexamp</div>
        {@render prog(done ? 'Installed' : 'Downloading', done ? 100 : Math.max(plexPct, pctOf(itemOf('plexamp'))), done ? (plexState === 'ok' ? 'Claim code given to Plex' : 'Not signed in yet') : null, plexState === 'ok')}
        {#if done}{@render note('info', '', plexState === 'ok' ? 'Your Plex library plays from the Plexamp app.' : 'Sign in from Settings → Plugins → Plexamp when you’re ready.')}{/if}
      {/if}
      {#if !headless && vizOn}
        {@const done = doneOf('skins')}
        <div class="head">Visualiser</div>
        {@render prog(done ? 'Installed' : 'Installing skins', done ? 100 : pctOf(itemOf('skins')), done ? 'Skins ready' : null, true)}
        {#if done}{@render note('info', '', `The visualiser starts after ${vizAfter} min of music.`)}{/if}
      {/if}
      {#if $settling?.items?.some((i) => i.state === 'failed')}
        {@render note('warn', 'Something did not finish', 'Try it again from Settings → Plugins; everything else is set.')}
      {/if}
      {#if finished?.failed?.length}
        {@render note('warn', 'A few answers were not taken', 'They are as they were in Settings, where they can be set by hand.')}
      {/if}
      <hr />
      {@render note('ok', '', 'Everything you set up here can be run again or changed in Settings → System → Personalise.')}
    {:else if screen === 'later'}
      <div class="party party--quiet" aria-hidden="true"><span class="party__badge">✓</span></div>
      <h1 class="hero">Kept the defaults</h1>
      <p class="sub">Spotify and Bluetooth are on, and nothing else is installed{lyr.state === 'found' ? `; Lyrion plays from ${lyr.server.name}` : ''}.</p>
      {@render note('ok', '', 'All of it is in Settings → System → Personalise.')}
    {/if}

    {#if loaded}
      <footer>
        {#if screen === 'done' || screen === 'later'}
          <button type="button" class="next" style="--a:{C.rev}" onclick={() => onclose?.()}>Close</button>
        {:else}
          {#if ret || path.indexOf(screen) > 0 || screen === 'review'}<button type="button" class="ghost" onclick={back}>Back</button>{/if}
          {#if screen === 'listen' && !ret}
            <button type="button" class="ghost" onclick={later}>Do it later</button>
          {:else if screen === 'plexamp' && !plexOn}
            <button type="button" class="ghost" onclick={() => { plexSkipped = true; advance(true); }}>Skip</button>
          {:else if screen === 'plexsign'}
            <button type="button" class="ghost" onclick={() => advance(true)}>Skip</button>
          {:else if !['listen', 'mix', 'review'].includes(screen) && !ret}
            <button type="button" class="ghost" onclick={() => advance(true)}>Skip</button>
          {/if}
          {#if $pairing?.state === 'asking' && screen === 'bluetooth' && bt}
            <button type="button" class="ghost" onclick={() => answer(false)}>Decline</button>
            <button type="button" class="next" style="--a:{accent}" onclick={() => answer(true)}>Accept</button>
          {:else if screen === 'plexamp' && !plexOn}
            <button type="button" class="next" style="--a:{accent}" onclick={downloadPlexamp}>Download</button>
          {:else if screen === 'plexsign' && plexState !== 'ok'}
            <button type="button" class="next" style="--a:{accent}" disabled={!plexIn || !claim.trim()} onclick={sendClaim}>Claim</button>
          {:else}
            <button type="button" class="next" style="--a:{accent}" disabled={(!canNext && screen !== 'plexsign') || finishing} onclick={() => advance(false)}>{finishing ? 'Finishing…' : nextLabel}</button>
          {/if}
        {/if}
      </footer>
    {/if}
  </div>
</div>

<style>
  .page {
    min-height: 100vh;
    min-height: 100dvh;
    background: #0c1014;
    color: #e9eef2;
    font-family: var(--font-ui);
    display: flex;
    justify-content: center;
  }
  .col {
    width: 100%;
    max-width: 440px;
    box-sizing: border-box;
    padding: 24px 20px 120px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  header { display: flex; align-items: center; gap: 14px; }
  .crumb { font-family: var(--font-mono); font-size: 12px; letter-spacing: 0.2em; text-transform: uppercase; }
  .progress { height: 3px; border-radius: 2px; background: rgba(233, 238, 242, 0.1); overflow: hidden; }
  .progress span { display: block; height: 100%; border-radius: 2px; transition: width 0.3s ease; }
  h1 { margin: 6px 0 0; font-size: 26px; font-weight: 800; line-height: 1.15; text-wrap: balance; }
  h1.hero { font-size: 30px; }
  .sub, .p { margin: 0; font-size: 16px; line-height: 1.5; color: rgba(233, 238, 242, 0.72); }
  .p { font-size: 14px; }
  .head { font-family: var(--font-mono); font-size: 11.5px; letter-spacing: 0.2em; text-transform: uppercase; color: rgba(233, 238, 242, 0.55); margin-top: 6px; }
  .head .any { letter-spacing: 0.05em; text-transform: none; font-family: var(--font-ui); }
  .list { display: flex; flex-direction: column; gap: 8px; }
  .card, .row {
    border-radius: 15px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(233, 238, 242, 0.1);
    box-sizing: border-box;
  }
  .card { padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; }
  .row {
    display: flex; align-items: center; gap: 14px; width: 100%; padding: 14px 16px;
    color: inherit; font: inherit; text-align: left;
  }
  button.row { cursor: pointer; }
  .row.on { background: rgba(126, 214, 188, 0.08); border-color: rgba(126, 214, 188, 0.5); }
  .row--ghost { border-style: dashed; opacity: 0.6; }
  .row__text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
  .row__text b { font-size: 17px; font-weight: 700; }
  .row__text small { font-size: 14px; color: rgba(233, 238, 242, 0.6); line-height: 1.35; }
  .row__icon { width: 36px; height: 36px; border-radius: 10px; display: grid; place-items: center; background: rgba(233, 238, 242, 0.06); flex-shrink: 0; }
  .radio { width: 22px; height: 22px; border-radius: 50%; border: 2px solid rgba(233, 238, 242, 0.35); display: grid; place-items: center; flex-shrink: 0; box-sizing: border-box; }
  .radio span { width: 10px; height: 10px; border-radius: 50%; background: #7ed6bc; display: none; }
  .radio.on { border-color: #7ed6bc; }
  .radio.on span { display: block; }
  .switch { width: 50px; height: 28px; border-radius: 999px; background: rgba(233, 238, 242, 0.18); position: relative; flex-shrink: 0; transition: background 0.2s; }
  .switch span { position: absolute; top: 3px; left: 3px; width: 22px; height: 22px; border-radius: 50%; background: #e9eef2; transition: transform 0.2s; }
  .switch.on { background: #7ed6bc; }
  .switch.on span { transform: translateX(22px); background: #0d151c; }
  .srcs { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
  .src { display: inline-flex; align-items: center; gap: 6px; padding: 5px 10px 5px 7px; border-radius: 999px; background: rgba(233, 238, 242, 0.07); border: 1px solid rgba(233, 238, 242, 0.1); font-size: 13px; font-weight: 600; }
  .p-mark { display: inline-grid; place-items: center; border-radius: 50%; border: 1.5px solid currentColor; font-size: 10px; font-weight: 800; box-sizing: border-box; }
  .tile-foot { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(233, 238, 242, 0.1); font-size: 13.5px; font-weight: 600; }
  .tile-foot em { font-style: normal; font-family: var(--font-mono); font-size: 12px; color: rgba(233, 238, 242, 0.55); }
  .tile-dot { width: 7px; height: 7px; border-radius: 50%; background: rgba(233, 238, 242, 0.4); }
  .tag { font-family: var(--font-mono); font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; padding: 4px 9px; border-radius: 999px; background: rgba(233, 238, 242, 0.08); color: rgba(233, 238, 242, 0.7); flex-shrink: 0; }
  .tag--ok { background: rgba(126, 214, 188, 0.14); color: #7ed6bc; }
  .tag--warn { background: rgba(224, 167, 88, 0.14); color: #e0a758; }
  .chev { width: 9px; height: 9px; border-right: 2px solid rgba(233, 238, 242, 0.45); border-top: 2px solid rgba(233, 238, 242, 0.45); transform: rotate(45deg); flex-shrink: 0; }
  .note { display: flex; gap: 14px; padding: 14px 16px; border-radius: 15px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(233, 238, 242, 0.1); }
  .note__bar { width: 4px; border-radius: 2px; background: #8fc4d8; flex-shrink: 0; }
  .note--ok .note__bar { background: #7ed6bc; }
  .note--warn { background: rgba(224, 167, 88, 0.08); border-color: rgba(224, 167, 88, 0.35); }
  .note--warn .note__bar { background: #e0a758; }
  .note span { display: flex; flex-direction: column; gap: 4px; }
  .note b { font-size: 16px; }
  .note small { font-size: 14.5px; line-height: 1.45; color: rgba(233, 238, 242, 0.75); }
  .status { display: flex; align-items: center; gap: 14px; padding: 12px 2px; }
  .status b { font-size: 16px; }
  .status small { display: block; font-size: 14px; color: rgba(233, 238, 242, 0.6); }
  .status .dot { width: 9px; height: 9px; border-radius: 50%; background: rgba(233, 238, 242, 0.4); flex-shrink: 0; }
  .tick { width: 24px; height: 24px; border-radius: 50%; background: #7ed6bc; color: #0d151c; display: grid; place-items: center; font-weight: 800; font-size: 14px; flex-shrink: 0; }
  .spin { width: 22px; height: 22px; border-radius: 50%; border: 3px solid rgba(233, 238, 242, 0.15); border-top-color: #7ed6bc; animation: spin 0.9s linear infinite; flex-shrink: 0; box-sizing: border-box; }
  .spin--small { width: 14px; height: 14px; border-width: 2px; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .field { display: flex; flex-direction: column; gap: 6px; }
  .field span { font-size: 14px; font-weight: 700; color: rgba(233, 238, 242, 0.8); }
  .field small { font-size: 13px; color: rgba(233, 238, 242, 0.55); }
  .field input { font: inherit; font-size: 17px; color: #e9eef2; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(233, 238, 242, 0.18); border-radius: 12px; padding: 13px 14px; }
  .field input:focus { outline: none; border-color: #7ed6bc; }
  .field input[readonly] { opacity: 0.55; }
  .btn { display: flex; justify-content: center; align-items: center; min-height: 50px; border-radius: 999px; border: 1px solid rgba(233, 238, 242, 0.2); background: rgba(233, 238, 242, 0.07); color: #e9eef2; font: inherit; font-size: 16px; font-weight: 700; text-decoration: none; cursor: pointer; }
  .btn--ghost { background: transparent; }
  .btn:disabled { opacity: 0.45; }
  .link { background: none; border: 0; padding: 0; color: #9fb4e8; font: inherit; font-size: 15px; font-weight: 700; cursor: pointer; align-self: flex-start; }
  .status-card { gap: 6px; }
  .where { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .where__opt { display: flex; align-items: center; gap: 10px; padding: 14px; border-radius: 15px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(233, 238, 242, 0.1); color: inherit; font: inherit; font-size: 15px; font-weight: 700; text-align: left; }
  .where__opt.on { border-color: rgba(126, 214, 188, 0.5); background: rgba(126, 214, 188, 0.08); }
  .split { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .split p { margin: 6px 0 0; font-size: 14.5px; }
  .addr small { font-size: 12px; color: rgba(233, 238, 242, 0.55); }
  .addr b { font-family: var(--font-mono); font-size: 18px; }
  .num { margin: 0; padding-left: 22px; display: flex; flex-direction: column; gap: 8px; font-size: 15.5px; }
  .prog__top { display: flex; justify-content: space-between; align-items: baseline; }
  .prog__top span { font-family: var(--font-mono); font-size: 13px; color: #e0a758; }
  .prog__top .prog--done { color: #7ed6bc; }
  .prog__bar { height: 5px; border-radius: 3px; background: rgba(233, 238, 242, 0.1); overflow: hidden; }
  .prog__bar span { display: block; height: 100%; border-radius: 3px; transition: width 0.4s ease; }
  .prog__st { display: flex; align-items: center; gap: 8px; font-size: 14px; color: rgba(233, 238, 242, 0.85); }
  .box { width: 16px; height: 16px; border-radius: 5px; border: 1.5px solid rgba(233, 238, 242, 0.45); display: inline-grid; place-items: center; font-size: 11px; font-weight: 800; box-sizing: border-box; }
  .box.ok { background: #7ed6bc; border-color: #7ed6bc; color: #0d151c; }
  .pills__row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
  .pill { min-height: 42px; padding: 0 16px; border-radius: 999px; border: 1px solid rgba(233, 238, 242, 0.14); background: rgba(255, 255, 255, 0.05); color: #e9eef2; font: inherit; font-size: 15px; font-weight: 700; display: inline-flex; align-items: center; gap: 8px; cursor: pointer; }
  .pill.on { background: var(--a); border-color: var(--a); color: #0d151c; }
  .pill--multi { border-radius: 10px; border-color: rgba(233, 238, 242, 0.22); background: transparent; }
  .pill--multi.on { background: rgba(233, 238, 242, 0.08); border-color: var(--a); color: #e9eef2; }
  .pill--multi.on .box { background: var(--a); border-color: var(--a); color: #0d151c; }
  .skins { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
  .skin { display: flex; flex-direction: column; gap: 6px; padding: 6px; border-radius: 12px; border: 1px solid rgba(233, 238, 242, 0.1); background: rgba(255, 255, 255, 0.04); color: inherit; font: inherit; font-size: 12.5px; font-weight: 700; cursor: pointer; }
  .skin.on { border-color: var(--a); background: rgba(200, 162, 216, 0.1); }
  .seg__row { display: flex; gap: 4px; padding: 4px; margin-top: 8px; border-radius: 999px; background: rgba(233, 238, 242, 0.07); }
  .seg__row button { flex: 1; min-height: 38px; border: 0; border-radius: 999px; background: transparent; color: #e9eef2; font: inherit; font-weight: 700; }
  .seg__row button.on { background: var(--a); color: #0d151c; }
  .cast { align-items: stretch; }
  .cast__phone { display: flex; flex-direction: column; gap: 6px; padding: 12px; border-radius: 12px; background: #121212; font-size: 14px; }
  .cast__phone small { color: rgba(233, 238, 242, 0.55); font-size: 12px; }
  .cast__on { display: flex; align-items: center; gap: 8px; color: #1ed760; font-weight: 700; }
  .cast p { margin: 0; font-size: 14.5px; color: rgba(233, 238, 242, 0.75); }
  .code { align-items: center; text-align: center; padding: 22px 16px; }
  .code small { font-size: 15px; color: rgba(233, 238, 242, 0.75); }
  .code b { font-family: var(--font-mono); font-size: 46px; letter-spacing: 0.08em; color: #d8c88f; }
  .code p { margin: 0; font-size: 14.5px; color: rgba(233, 238, 242, 0.7); }
  .ivs { display: flex; flex-direction: column; gap: 10px; }
  .iv__times { display: flex; align-items: center; gap: 8px; }
  .iv__time { flex: 1; display: flex; flex-direction: column; align-items: flex-start; gap: 2px; padding: 10px 12px; border-radius: 12px; border: 1px solid rgba(233, 238, 242, 0.1); background: rgba(233, 238, 242, 0.04); color: #e9eef2; font: inherit; font-size: 20px; font-weight: 800; font-variant-numeric: tabular-nums; }
  .iv__time small { font-size: 11px; font-weight: 700; color: rgba(233, 238, 242, 0.55); }
  .iv__time.on { border-color: #7ed6bc; color: #7ed6bc; }
  .grid24 { display: grid; grid-template-columns: repeat(6, 1fr); gap: 5px; }
  .grid4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; }
  .grid24 button, .grid4 button, .days button { min-height: 38px; border-radius: 9px; border: 1px solid rgba(233, 238, 242, 0.1); background: rgba(233, 238, 242, 0.07); color: rgba(233, 238, 242, 0.82); font: inherit; font-size: 14px; font-variant-numeric: tabular-nums; }
  .grid24 button.on, .grid4 button.on, .days button.on { background: rgba(126, 214, 188, 0.16); border-color: #7ed6bc; color: #7ed6bc; font-weight: 700; }
  .days { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
  .days button { font-size: 12px; padding: 0; }
  .party { position: relative; height: 120px; display: grid; place-items: center; }
  .party__badge { width: 76px; height: 76px; border-radius: 50%; background: #7ed6bc; color: #0d151c; display: grid; place-items: center; font-size: 38px; font-weight: 800; box-shadow: 0 0 0 0 rgba(126, 214, 188, 0.5); animation: ring 2.2s ease-out infinite; }
  .party .note1, .party .note2 { position: absolute; font-size: 22px; color: #9fb4e8; animation: rise 3s ease-in infinite; }
  .party .note1 { left: 30%; }
  .party .note2 { right: 30%; animation-delay: 1.4s; color: #e8a0b4; }
  .party--quiet .party__badge { animation: none; }
  @keyframes ring { 0% { box-shadow: 0 0 0 0 rgba(126, 214, 188, 0.45); } 100% { box-shadow: 0 0 0 26px rgba(126, 214, 188, 0); } }
  @keyframes rise { 0% { transform: translateY(30px); opacity: 0; } 30% { opacity: 1; } 100% { transform: translateY(-40px); opacity: 0; } }
  hr { width: 100%; border: 0; border-top: 1px solid rgba(233, 238, 242, 0.1); margin: 6px 0; }
  footer {
    position: fixed; left: 0; right: 0; bottom: 0;
    display: flex; justify-content: center; gap: 10px;
    padding: 14px max(20px, calc((100vw - 440px) / 2 + 20px)) calc(14px + env(safe-area-inset-bottom, 0px));
    background: linear-gradient(180deg, rgba(12, 16, 20, 0), #0c1014 30%);
  }
  .ghost { min-height: 56px; padding: 0 20px; border-radius: 999px; border: 1px solid rgba(233, 238, 242, 0.18); background: rgba(233, 238, 242, 0.05); color: #e9eef2; font: inherit; font-size: 16px; font-weight: 700; cursor: pointer; }
  .next { flex: 1; min-height: 56px; border-radius: 999px; border: 0; background: var(--a); color: #0d151c; font: inherit; font-size: 18px; font-weight: 800; cursor: pointer; }
  .next:disabled { opacity: 0.4; cursor: default; }
  @media (prefers-reduced-motion: reduce) {
    .spin, .party__badge, .party .note1, .party .note2 { animation: none; }
  }
</style>
