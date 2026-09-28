<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **First-time setup, on the phone** (design/source/Setup.dc.html,
  screens.md §13; ADR-0031 as amended; ADR-0104).

  The design's steps, with the changes the amendment made to them:
  - **Network** saves the choice and does not test it. With one radio the join
    can only happen after the setup network is down, which is after this page
    is gone. A wrong password brings setup back with the reason, and the page
    opens on this step again (amendment 5).
  - **Music** has no server discovery: over the setup network the player
    cannot see the home network (amendment 4). An optional address instead.
  - **Time** has no clock format: nothing in Settings stores one yet.
  - **Display** sets the existing Headless row (ADR-0077); it starts on what
    the display connector says.

  **The core keeps the answers.** Each Continue saves the step, so a page that
  drops (Finding 099 saw one) or a phone that comes back after a failed join
  resumes where it was. The password is never handed back.
-->
<script>
  import { onMount } from 'svelte';
  import mark from '../assets/gexis-mark.svg';

  let { setup } = $props();

  const STEPS = [
    ['wifi', 'Network', '#8fc4d8'],
    ['name', 'Name', '#e8a0b4'],
    ['tz', 'Time', '#c8a2d8'],
    ['out', 'Output', '#7ed6bc'],
    ['music', 'Music', '#9fb4e8'],
    ['display', 'Display', '#8fd9a8'],
    ['review', 'Review', '#f2a48f']
  ];
  const last = STEPS.length;

  let step = $state(-1);
  let loaded = $state(false);
  let saving = $state(false);
  let problem = $state(null);

  // The answers, as the design names them.
  let ssid = $state(null);
  let hidden = $state(false);
  let manualSsid = $state('');
  let pw = $state('');
  let showPw = $state(false);
  let hasPassword = $state(false);
  let joinError = $state(null);
  //: Back after a failed join: only the network was wrong, so Continue on
  //: Network goes straight to Review (George, 2026-09-28).
  let retrying = $state(false);
  let name = $state('gexis');
  let tz = $state(null);
  let tzMode = $state('auto');
  let tzRegion = $state(null);
  let out = $state(null);
  let lms = $state('');
  let spotify = $state(true);
  let bt = $state(true);
  let headless = $state(false);

  // What the device offers.
  let nets = $state([]);
  let scan = $state('scanning');
  let outputs = $state([]);
  let zones = $state([]);
  let tick = $state(new Date());
  let finished = $state(false);

  const id = $derived(step >= 0 && step < last ? STEPS[step][0] : null);
  const accent = $derived(step >= 0 && step < last ? STEPS[step][2] : '#7ed6bc');
  const overLan = $derived(setup?.network === 'online');
  const picked = $derived(ssid === '__other' ? manualSsid.trim() : ssid);
  const pickedNet = $derived(nets.find((n) => n.name === ssid) ?? null);
  const secured = $derived(ssid === '__other' ? true : (pickedNet?.secured ?? true));

  //: `device_name.sanitise`, as the address will be. Accents fold, case
  //: drops, the rest becomes hyphens; 63 is one DNS label.
  function slugOf(v) {
    return (v || '')
      .normalize('NFKD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9-]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 63);
  }
  const slug = $derived(slugOf(name) || 'gexis');
  const shownName = $derived((name || '').trim() || 'gexis');

  const wifiValid = $derived(
    (overLan && !ssid) ||
      (!!picked && (!secured || pw.length >= 8 || (hasPassword && !pw)))
  );
  function valid() {
    switch (id) {
      case 'wifi': return wifiValid;
      case 'name': return slugOf(name).length > 1;
      case 'tz': return !!tz;
      default: return true;
    }
  }

  async function json(url, opts) {
    const r = await fetch(url, opts);
    const body = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(body.error || `${url}: ${r.status}`);
    return body;
  }

  async function rescan() {
    scan = 'scanning';
    try {
      nets = (await json('/setup/networks')).items ?? [];
    } catch {
      nets = [];
    }
    scan = 'done';
  }

  function rowsOf(settings) {
    const rows = {};
    const walk = (o) => {
      if (Array.isArray(o)) o.forEach(walk);
      else if (o && typeof o === 'object') {
        if (o.key && o.type) rows[o.key] = o;
        Object.values(o).forEach(walk);
      }
    };
    walk(settings);
    return rows;
  }

  onMount(() => {
    const clock = setInterval(() => (tick = new Date()), 1000);
    (async () => {
      let saved = {};
      let rows = {};
      try { saved = await json('/setup/answers'); } catch { /* a fresh start */ }
      try { rows = rowsOf(await json('/settings')); } catch { /* defaults below */ }
      outputs = rows.output_device?.options ?? [];
      zones = rows.timezone?.options ?? [];
      let phoneTz = null;
      try { phoneTz = Intl.DateTimeFormat().resolvedOptions().timeZone || null; } catch { /* none */ }
      // A new device starts from the phone's clock; one being set up again
      // from what it already has. Saved answers win over both.
      name = saved.name ?? rows.device_name?.value ?? 'gexis';
      tz = saved.timezone ?? (setup?.needed ? phoneTz : rows.timezone?.value) ?? phoneTz;
      if (tz && zones.length && !zones.includes(tz)) tz = null;
      tzMode = tz ? 'auto' : 'region';
      out = saved.output ?? rows.output_device?.value ?? outputs[0] ?? null;
      lms = saved.lms ?? (setup?.needed ? '' : (rows.lms_server?.value ?? ''));
      spotify = saved.spotify ?? rows.spotify_enabled?.value ?? true;
      bt = saved.bluetooth ?? rows.bt_enabled?.value ?? true;
      headless = saved.headless ?? (setup?.needed ? !setup?.panel : !!rows.headless?.value);
      hidden = !!saved.hidden;
      hasPassword = !!saved.has_password;
      joinError = saved.error ?? null;
      if (saved.ssid) {
        ssid = hidden ? '__other' : saved.ssid;
        if (hidden) manualSsid = saved.ssid;
      }
      const at = STEPS.findIndex((s) => s[0] === saved.step);
      retrying = !!joinError;
      step = joinError ? 0 : at >= 0 ? at : -1;
      loaded = true;
      rescan();
    })();
    return () => clearInterval(clock);
  });

  function answersFor(stepId) {
    switch (stepId) {
      case 'wifi': {
        const a = { ssid: picked || null, hidden: ssid === '__other' };
        if (pw) a.password = pw;
        else if (!secured) a.password = null;
        return a;
      }
      case 'name': return { name: (name || '').trim() };
      case 'tz': return { timezone: tz };
      case 'out': return { output: out };
      case 'music': return { lms: lms.trim() || null, spotify, bluetooth: bt };
      case 'display': return { headless };
      default: return {};
    }
  }

  async function saveStep(nextStep) {
    const a = answersFor(id);
    a.step = nextStep >= 0 && nextStep < last ? STEPS[nextStep][0] : 'review';
    saving = true;
    problem = null;
    try {
      const saved = await json('/setup/answers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(a)
      });
      hasPassword = saved.has_password;
      joinError = saved.error ?? null;
      if (id === 'wifi') pw = '';
      return true;
    } catch (err) {
      problem = err.message;
      return false;
    } finally {
      saving = false;
    }
  }

  async function next() {
    if (saving || !valid()) return;
    if (step < 0) {
      step = 0;
      return;
    }
    if (id === 'review') {
      await finish();
      return;
    }
    const to = retrying && id === 'wifi' ? last - 1 : step + 1;
    if (await saveStep(to)) step = to;
  }

  async function finish() {
    saving = true;
    problem = null;
    try {
      await json('/setup/finish', { method: 'POST' });
      finished = true;
    } catch (err) {
      problem = err.message;
    } finally {
      saving = false;
    }
  }

  const fmt = (d, zone) => {
    try {
      return new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: zone }).format(d);
    } catch {
      return '--:--';
    }
  };
  const regions = $derived([...new Set(zones.map((z) => (z.includes('/') ? z.split('/')[0] : z)))]);
  const cities = $derived(zones.filter((z) => (z.includes('/') ? z.split('/')[0] : z) === tzRegion));
  const tzLabel = $derived(
    tz ? `${tz.split('/').slice(-1)[0].replace(/_/g, ' ')} · ${tz.includes('/') ? tz.split('/')[0] : tz}` : 'Not detected'
  );

  const review = $derived([
    ['Network', picked || (overLan ? 'Ethernet only' : 'Not set'), 0],
    ['Name', `${shownName} · ${slug}.local`, 1],
    ['Time zone', tz || 'Not set', 2],
    ['Output', out || 'Not set', 3],
    ['Library', lms.trim() || 'Found once on your network', 4],
    ['Services', [spotify ? 'Spotify Connect' : null, bt ? 'Bluetooth' : null].filter(Boolean).join(' · ') || 'Lyrion only', 4],
    ['Display', headless ? 'Headless' : 'Panel attached', 5]
  ]);
</script>

<div class="page">
  <div class="shell">
    <header>
      <img class="mark" src={mark} alt="" width="34" height="34" />
      <span class="crumb">
        {step < 0 ? 'First-time setup' : step >= last || finished ? 'Almost done' : `Step ${step + 1} of ${last} · ${STEPS[step][1]}`}
      </span>
      {#if setup?.ssid}<span class="over">Over {setup.ssid}</span>{/if}
    </header>

    {#if step >= 0 && step < last && !finished}
      <div class="progress"><div style="width:{Math.round(((step + (valid() ? 1 : 0.35)) / last) * 100)}%; background:{accent}"></div></div>
    {/if}

    <div class="grid" class:grid--rail={step >= 0 && step < last && !finished}>
      {#if step >= 0 && step < last && !finished}
        <nav class="rail">
          {#each STEPS as s, n}
            <button class="rail-item" class:cur={n === step} disabled={n > step} onclick={() => (step = n)}>
              <span class="rail-bar" style="background:{s[2]}; opacity:{n <= step ? 1 : 0.45}"></span>
              <span class="rail-label">{s[1]}</span>
              {#if n < step}<span class="tick"></span>{/if}
            </button>
          {/each}
        </nav>
      {/if}

      <main>
        {#if !loaded}
          <div class="row-spin"><span class="spin" style="border-top-color:#8fc4d8"></span><span>Opening setup</span></div>
        {:else if finished}
          <section class="pane">
            <h1 class="hero">{shownName} is {picked ? 'joining your network' : 'set up'}</h1>
            {#if picked}
              <p class="lead">This page is served by the player over its own Wi-Fi, so it stops here. Reconnect this phone to <strong>{picked}</strong>, then open the address below.</p>
            {/if}
            <div class="addr-card">
              <div class="label">Open in any browser</div>
              <div class="addr">http://{slug}.local:8090</div>
            </div>
            <div class="note-card" style="--bar: {headless ? '#e0a758' : '#7ed6bc'}">
              <span class="bar"></span>
              <span>{headless
                ? 'Nothing is drawn on the device, so this address is the only way in. Write it down before you close the page.'
                : 'If the password is not accepted, the player opens its setup network again within about a minute. Join it, and this page picks up where you left off.'}</span>
            </div>
          </section>
        {:else if step < 0}
          <section class="pane">
            <h1 class="hero">Set up <span class="word">gexis</span></h1>
            <p class="lead">
              {overLan
                ? 'Nothing here leaves your network: the player is the only thing this page is talking to.'
                : "You are connected to the player's own Wi-Fi. Nothing here leaves the room: the device is the only thing this page is talking to."}
            </p>
            <div class="cards">
              <div class="info"><span class="bar" style="background:#8fc4d8"></span><span><b>About two minutes</b><small>Six questions. Every one of them can be changed later in Settings.</small></span></div>
              {#if !overLan}
                <div class="info"><span class="bar" style="background:#7ed6bc"></span><span><b>Keep this phone handy</b><small>When setup finishes, the player leaves its own Wi-Fi for yours and this page stops working. That is by design, not a fault.</small></span></div>
              {/if}
            </div>
          </section>
        {:else}
          <div class="eyebrow" style="color:{accent}"><span class="dot" style="background:{accent}"></span>{STEPS[step][1]}<span class="rule"></span></div>

          {#if id === 'wifi'}
            <section class="pane">
              <div>
                <h1>Join your network</h1>
                <p class="sub">{overLan
                  ? 'The player is on your network by cable. Add Wi-Fi as well, or leave it on the cable.'
                  : 'The player has one radio, so it can host this page or use your network, never both.'}</p>
              </div>

              {#if joinError}
                <div class="warn"><span class="bang">!</span><span>Could not join {joinError.ssid}. {joinError.reason} Type the password again.</span></div>
              {/if}

              {#if !ssid}
                {#if scan === 'scanning'}
                  <div class="row-spin"><span class="spin" style="border-top-color:#8fc4d8"></span><span>Looking for networks</span></div>
                {:else}
                  <div class="list">
                    {#each nets as n (n.name)}
                      <button class="net" onclick={() => { ssid = n.name; pw = ''; hasPassword = false; manualSsid = ''; }}>
                        <span class="bars">{#each [1, 2, 3, 4] as b}<span style="height:{2 + b * 4}px; background:{b <= n.bars ? '#8fc4d8' : 'rgba(233,238,242,0.22)'}"></span>{/each}</span>
                        <span class="grow"><span class="nm">{n.name}</span><span class="meta">{n.secured ? 'Secured' : 'Open'}</span></span>
                        <span class="chev"></span>
                      </button>
                    {/each}
                    <button class="net" onclick={() => { ssid = '__other'; pw = ''; hasPassword = false; }}>
                      <span class="grow"><span class="nm">Other network</span><span class="meta">A hidden network, typed by name</span></span>
                      <span class="chev"></span>
                    </button>
                    <button class="ghost" onclick={rescan}>Scan again</button>
                  </div>
                {/if}
              {:else}
                <div class="picked">
                  <span class="grow"><b>{ssid === '__other' ? 'Other network' : ssid}</b><small>{secured ? 'Secured' : 'Open'}</small></span>
                  <button class="chip" onclick={() => { ssid = null; pw = ''; hasPassword = false; }}>Change</button>
                </div>
                {#if ssid === '__other'}
                  <label class="field"><span class="label">Network name</span>
                    <input type="text" bind:value={manualSsid} placeholder="Exactly as your router spells it" autocomplete="off" spellcheck="false" />
                  </label>
                {/if}
                {#if secured}
                  <label class="field"><span class="label">Password</span>
                    <span class="pw">
                      <input type={showPw ? 'text' : 'password'} bind:value={pw} placeholder={hasPassword ? 'Saved — type to replace it' : 'Network password'} autocomplete="off" spellcheck="false" />
                      <button type="button" class="chip in" onclick={() => (showPw = !showPw)}>{showPw ? 'Hide' : 'Show'}</button>
                    </span>
                    <span class="hint">{hasPassword && !pw ? 'Saved. The player tries it at the end of setup.' : 'At least 8 characters. The player tries it at the end of setup.'}</span>
                  </label>
                {:else}
                  <span class="hint">This network is open — no password needed.</span>
                {/if}
              {/if}
            </section>
          {:else if id === 'name'}
            <section class="pane">
              <div>
                <h1>Name the player</h1>
                <p class="sub">One name for everything. There is no per-service override, so pick one you will recognise in a list of speakers.</p>
              </div>
              <label class="field"><span class="label">Device name</span>
                <input type="text" bind:value={name} placeholder="Living room" autocomplete="off" spellcheck="false" style="border-color:{slugOf(name).length > 1 ? '' : 'rgba(224,167,88,0.55)'}" />
                <span class="hint" style="color:{slugOf(name).length > 1 ? '' : '#e0a758'}">{slugOf(name).length > 1
                  ? 'Letters, numbers and hyphens become the address; the name keeps its capitals everywhere else.'
                  : 'Needs at least two letters or numbers.'}</span>
              </label>
              <div class="table">
                <div class="thead">Becomes</div>
                {#each [['Address', `http://${slug}.local`], ['Lyrion player', shownName], ['Spotify Connect', shownName], ['Bluetooth', shownName]] as p}
                  <div class="trow"><span class="what">{p[0]}</span><span class="val">{p[1]}</span></div>
                {/each}
              </div>
            </section>
          {:else if id === 'tz'}
            <section class="pane">
              <div>
                <h1>Set the clock</h1>
                <p class="sub">The idle screen is mostly a clock, so this is worth getting right.</p>
              </div>
              {#if tzMode === 'auto'}
                <div class="tz">
                  <div class="grow"><div class="label">{setup?.needed ? 'Read from this phone' : 'The player’s time zone'}</div><div class="tz-name">{tzLabel}</div></div>
                  <div class="clock">{fmt(tick, tz || 'UTC')}</div>
                </div>
                <button class="ghost" onclick={() => { tzMode = 'region'; tzRegion = null; }}>Choose by hand</button>
              {:else if tzMode === 'region'}
                <div class="list">
                  <div class="back-row"><button class="back" aria-label="Back" onclick={() => (tzMode = 'auto')}><span></span></button><span class="label">Region</span></div>
                  {#each regions as r}
                    <button class="net" onclick={() => { tzRegion = r; tzMode = 'city'; }}><span class="grow nm">{r}</span><span class="chev"></span></button>
                  {/each}
                </div>
              {:else}
                <div class="list">
                  <div class="back-row"><button class="back" aria-label="Back" onclick={() => (tzMode = 'region')}><span></span></button><span class="label">{tzRegion}</span></div>
                  {#each cities as z}
                    <button class="net" class:sel={tz === z} onclick={() => { tz = z; tzMode = 'auto'; }}>
                      <span class="grow nm">{z.split('/').slice(1).join(' / ').replace(/_/g, ' ') || z}</span>
                      <span class="time">{fmt(tick, z)}</span>
                    </button>
                  {/each}
                </div>
              {/if}
            </section>
          {:else if id === 'out'}
            <section class="pane">
              <div>
                <h1>Choose the output</h1>
                <p class="sub">What the player should send audio to. Stored by name, because card numbers move between boots.</p>
              </div>
              <div class="list">
                {#each outputs as o}
                  <button class="net" class:sel={out === o} onclick={() => (out = o)}>
                    <span class="radio" class:on={out === o}><span></span></span>
                    <span class="grow nm">{o}</span>
                  </button>
                {/each}
              </div>
            </section>
          {:else if id === 'music'}
            <section class="pane">
              <div>
                <h1>Find your library</h1>
                <p class="sub">{overLan
                  ? 'The player finds Lyrion servers on your network by itself. Typing an address is the fallback.'
                  : 'Over its own Wi-Fi the player cannot see your network, so it looks for servers once it is on it. If you know the address, it can go here.'}</p>
              </div>
              <label class="field"><span class="label">Lyrion server (optional)</span>
                <input type="text" bind:value={lms} placeholder="192.168.1.10:9000" autocomplete="off" spellcheck="false" inputmode="url" />
                <span class="hint">No server yet? Leave this alone. Spotify Connect and Bluetooth work without one.</span>
              </label>
              <div class="list">
                <div class="label pad">Also switch on</div>
                {#each [['Spotify Connect', `The player appears in Spotify as ${shownName}.`, spotify, () => (spotify = !spotify)], ['Bluetooth', 'Phones can pair and send audio directly.', bt, () => (bt = !bt)]] as v}
                  <button class="net" onclick={v[3]}>
                    <span class="grow"><span class="nm">{v[0]}</span><span class="meta plain">{v[1]}</span></span>
                    <span class="toggle" class:on={v[2]}><span></span></span>
                  </button>
                {/each}
              </div>
            </section>
          {:else if id === 'display'}
            <section class="pane">
              <div>
                <h1>Is a screen attached?</h1>
                <p class="sub">The panel is the player's own display. Without one, everything runs from a phone or a browser.</p>
              </div>
              <div class="disp">
                <button class="dcard" class:sel={!headless} onclick={() => (headless = false)}>
                  <span class="art"><span class="art-panel"></span></span>
                  <b>Panel attached</b><small>Now Playing, browse and settings run on the device's own screen.</small>
                </button>
                <button class="dcard" class:sel={headless} onclick={() => (headless = true)}>
                  <span class="art"><span class="art-off"></span></span>
                  <b>Headless</b><small>No local screen. The display stays off and nothing is drawn.</small>
                </button>
              </div>
              {#if headless}
                <div class="warn"><span class="bang">!</span><span>The panel is where the player shows its setup network if it starts without one. Headless, that fallback is gone — write down the address on the last page.</span></div>
              {/if}
            </section>
          {:else if id === 'review'}
            <section class="pane">
              <div>
                <h1>Check it over</h1>
                <p class="sub">Finishing writes all of this to the player and moves it to your network.</p>
              </div>
              <div class="table">
                {#each review as r}
                  <div class="trow"><span class="what">{r[0]}</span><span class="val grow">{r[1]}</span><button class="chip" onclick={() => (step = r[2])}>Change</button></div>
                {/each}
              </div>
            </section>
          {/if}
        {/if}

        {#if problem}
          <div class="warn"><span class="bang">!</span><span>{problem}</span></div>
        {/if}

        {#if loaded && !finished}
          <div class="foot">
            {#if step > 0}<button class="ghost" onclick={() => (step -= 1)}>Back</button>{/if}
            <button class="primary" style="--c:{accent}" disabled={!valid() || saving} onclick={next}>
              {step < 0 ? 'Start' : id === 'review' ? 'Finish and connect' : 'Continue'}
            </button>
          </div>
        {/if}
      </main>
    </div>
  </div>
</div>

<style>
  .page {
    min-height: 100%;
    color: var(--ink);
    background:
      radial-gradient(130% 105% at 20% 42%, rgba(20, 33, 42, 0.72), rgba(13, 21, 28, 0.96)),
      repeating-linear-gradient(38deg, var(--bg-weave-a) 0 48px, var(--bg-weave-b) 48px 96px);
    background-attachment: fixed;
  }
  .shell {
    max-width: 1000px;
    margin: 0 auto;
    padding: 28px 20px 44px;
  }
  @media (min-width: 720px) {
    .shell { padding: 46px 40px 64px; }
  }
  header { display: flex; align-items: center; gap: 16px; min-width: 0; }
  .mark { width: 34px; height: 34px; flex-shrink: 0; }
  .crumb, .over, .label, .thead, .eyebrow {
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .crumb { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .over { display: none; letter-spacing: 0.14em; }
  @media (min-width: 720px) { .over { display: block; } }

  .progress { height: 3px; border-radius: 2px; background: var(--ink-line); margin-top: 22px; overflow: hidden; }
  .progress div { height: 100%; transition: width 260ms cubic-bezier(0.32, 0.72, 0, 1); }

  .grid { margin-top: 26px; display: grid; gap: 34px; grid-template-columns: minmax(0, 1fr); }
  .rail { display: none; }
  @media (min-width: 720px) {
    .grid--rail { grid-template-columns: 220px minmax(0, 1fr); }
    .rail { display: flex; flex-direction: column; gap: 2px; position: sticky; top: 34px; align-self: start; }
  }
  .rail-item {
    all: unset; display: flex; align-items: center; gap: 15px; min-height: 56px; padding: 0 15px;
    border-radius: 13px; cursor: pointer; color: rgba(233, 238, 242, 0.6);
  }
  .rail-item.cur { background: rgba(233, 238, 242, 0.08); color: var(--ink); }
  .rail-item:disabled { cursor: default; }
  .rail-bar { width: 4px; height: 30px; border-radius: 2px; flex-shrink: 0; }
  .rail-label { flex: 1; font-size: 16px; font-weight: 600; }
  .tick { width: 13px; height: 7px; border-left: 2.5px solid #7ed6bc; border-bottom: 2.5px solid #7ed6bc; transform: rotate(-45deg); margin-top: -3px; }

  main { min-width: 0; }
  .eyebrow { display: flex; align-items: center; gap: 11px; margin-bottom: 20px; font-size: 13px; }
  .dot { width: 9px; height: 9px; border-radius: 50%; }
  .rule { flex: 1; height: 1px; background: var(--ink-line); }

  .pane { display: flex; flex-direction: column; gap: 22px; animation: fade 260ms cubic-bezier(0.32, 0.72, 0, 1); }
  @keyframes fade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
  @keyframes spin { to { transform: rotate(360deg); } }
  h1 { margin: 0; font-weight: 800; letter-spacing: -0.015em; line-height: 1.15; font-size: 26px; }
  .hero { font-size: 30px; letter-spacing: -0.02em; line-height: 1.1; }
  @media (min-width: 720px) { h1 { font-size: 32px; } .hero { font-size: 40px; } }
  .word { font-weight: 600; }
  .lead { margin: 0; font-size: 17px; line-height: 1.55; color: var(--ink-muted); max-width: 52ch; }
  .sub { margin: 10px 0 0; font-size: 16px; line-height: 1.5; color: rgba(233, 238, 242, 0.66); max-width: 50ch; }

  .cards, .list { display: flex; flex-direction: column; gap: 6px; }
  .cards { gap: 10px; }
  .info, .note-card {
    display: flex; align-items: flex-start; gap: 14px; padding: 16px 18px; border-radius: 16px;
    background: rgba(255, 255, 255, 0.05); border: 1px solid var(--ink-line);
  }
  .info b { display: block; font-size: 17px; font-weight: 600; }
  .info small { display: block; font-size: 15px; line-height: 1.45; color: var(--ink-quiet); margin-top: 5px; }
  .bar { width: 4px; align-self: stretch; border-radius: 2px; flex-shrink: 0; background: var(--bar, #7ed6bc); }
  .note-card { font-size: 15px; line-height: 1.5; color: var(--ink-muted); }

  .net, .picked {
    all: unset; box-sizing: border-box; display: flex; align-items: center; gap: 16px; min-height: 66px;
    padding: 12px 18px; border-radius: 14px; background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--ink-line); cursor: pointer;
  }
  .net:active { transform: scale(0.99); background: rgba(233, 238, 242, 0.1); }
  .net.sel { background: rgba(126, 214, 188, 0.1); border-color: rgba(126, 214, 188, 0.45); }
  .picked { cursor: default; }
  .picked b { display: block; font-size: 17px; font-weight: 700; }
  .picked small, .meta { display: block; font-family: var(--font-mono); font-size: 13px; letter-spacing: 0.04em; margin-top: 4px; color: var(--ink-quiet); }
  .meta.plain { font-family: var(--font-ui); font-size: 14px; letter-spacing: 0; line-height: 1.4; }
  .grow { flex: 1; min-width: 0; }
  .nm { display: block; font-size: 17px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .bars { width: 26px; height: 20px; display: flex; align-items: flex-end; gap: 3px; flex-shrink: 0; }
  .bars span { width: 4px; border-radius: 1px; display: block; }
  .chev { width: 11px; height: 11px; border-right: 2.5px solid rgba(233, 238, 242, 0.42); border-top: 2.5px solid rgba(233, 238, 242, 0.42); transform: rotate(45deg); flex-shrink: 0; }
  .time { font-family: var(--font-mono); font-size: 14px; color: var(--ink-quiet); }

  .field { display: flex; flex-direction: column; gap: 9px; }
  input {
    width: 100%; box-sizing: border-box; height: 58px; border-radius: 14px; background: rgba(8, 12, 16, 0.6);
    border: 1px solid rgba(233, 238, 242, 0.18); padding: 0 18px; font-family: var(--font-mono);
    font-size: 16px; color: var(--ink); outline: none;
  }
  input:focus { border-color: var(--c, #8fc4d8); }
  input::placeholder { color: rgba(233, 238, 242, 0.38); }
  .pw { position: relative; display: block; }
  .pw input { padding-right: 96px; }
  .hint { font-size: 14px; line-height: 1.45; color: var(--ink-quiet); }

  .chip, .ghost, .back {
    all: unset; box-sizing: border-box; cursor: pointer; border-radius: 999px; font-weight: 700;
    background: var(--ink-fill); border: 1px solid rgba(233, 238, 242, 0.16);
  }
  .chip { padding: 8px 16px; font-size: 14px; }
  .chip.in { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); }
  .ghost { align-self: flex-start; padding: 12px 22px; font-size: 15px; }
  .back { width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; }
  .back span { width: 10px; height: 10px; border-left: 2.5px solid var(--ink); border-bottom: 2.5px solid var(--ink); transform: rotate(45deg); margin-left: 4px; }
  .back-row { display: flex; align-items: center; gap: 14px; padding: 0 2px 6px; }
  .pad { padding: 8px 2px 4px; }

  .table { display: flex; flex-direction: column; gap: 1px; border-radius: 16px; overflow: hidden; border: 1px solid var(--ink-line); }
  .thead { padding: 14px 18px; background: rgba(255, 255, 255, 0.05); }
  .trow { display: flex; align-items: center; flex-wrap: wrap; gap: 16px; padding: 14px 18px; background: rgba(255, 255, 255, 0.03); min-height: 34px; }
  .what { flex-shrink: 0; width: 132px; font-size: 15px; color: var(--ink-quiet); }
  .val { font-size: 17px; font-weight: 600; word-break: break-word; }

  .tz { display: flex; align-items: center; flex-wrap: wrap; gap: 16px; padding: 20px; border-radius: 16px; background: rgba(255, 255, 255, 0.05); border: 1px solid var(--ink-line); }
  .tz-name { font-size: 22px; font-weight: 700; margin-top: 8px; word-break: break-word; }
  .clock { font-family: var(--font-mono); font-size: 28px; font-weight: 600; }

  .radio, .toggle { flex-shrink: 0; display: flex; align-items: center; }
  .radio { width: 24px; height: 24px; border-radius: 50%; border: 2px solid rgba(233, 238, 242, 0.42); justify-content: center; }
  .radio.on { border-color: #7ed6bc; }
  .radio.on span { width: 11px; height: 11px; border-radius: 50%; background: #7ed6bc; }
  .toggle { width: 58px; height: 30px; border-radius: 999px; background: var(--ink-fill); border: 1px solid rgba(233, 238, 242, 0.18); position: relative; }
  .toggle span { position: absolute; left: 3px; width: 24px; height: 24px; border-radius: 50%; background: rgba(233, 238, 242, 0.55); transition: left 160ms; }
  .toggle.on { background: #7ed6bc; border-color: #7ed6bc; }
  .toggle.on span { left: 31px; background: #0d151c; }

  .disp { display: grid; gap: 12px; grid-template-columns: minmax(0, 1fr); }
  @media (min-width: 720px) { .disp { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  .dcard { all: unset; box-sizing: border-box; cursor: pointer; padding: 22px; border-radius: 18px; background: rgba(255, 255, 255, 0.05); border: 1px solid var(--ink-line); }
  .dcard.sel { background: rgba(143, 217, 168, 0.12); border-color: rgba(143, 217, 168, 0.5); }
  .dcard b { display: block; font-size: 19px; font-weight: 700; margin-top: 18px; }
  .dcard small { display: block; font-size: 15px; line-height: 1.45; color: rgba(233, 238, 242, 0.66); margin-top: 7px; }
  .art { width: 100%; aspect-ratio: 16 / 10; border-radius: 10px; background: rgba(8, 12, 16, 0.5); border: 2px solid rgba(233, 238, 242, 0.22); display: flex; align-items: center; justify-content: center; }
  .dcard.sel .art { border-color: #8fd9a8; }
  .art-panel { width: 42%; height: 6px; border-radius: 3px; background: currentColor; opacity: 0.4; }
  .art-off { width: 34px; height: 2px; border-radius: 2px; background: currentColor; opacity: 0.4; transform: rotate(-38deg); }
  .dcard.sel .art-panel, .dcard.sel .art-off { background: #8fd9a8; opacity: 1; }

  .warn {
    display: flex; align-items: flex-start; gap: 14px; padding: 14px 16px; border-radius: 14px;
    background: rgba(224, 167, 88, 0.1); border: 1px solid rgba(224, 167, 88, 0.4); font-size: 15px; line-height: 1.45;
  }
  .bang { width: 22px; height: 22px; border-radius: 50%; background: #e0a758; color: #0d151c; font-weight: 800; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }

  .row-spin { display: flex; align-items: center; gap: 16px; padding: 20px 4px; font-size: 17px; font-weight: 600; }
  .spin { width: 30px; height: 30px; border-radius: 50%; border: 3px solid rgba(233, 238, 242, 0.14); animation: spin 900ms linear infinite; flex-shrink: 0; }

  .addr-card { padding: 20px; border-radius: 16px; background: rgba(255, 255, 255, 0.05); border: 1px solid var(--ink-line); }
  .addr { font-family: var(--font-mono); font-size: 23px; font-weight: 600; margin-top: 10px; word-break: break-all; }
  @media (min-width: 720px) { .addr { font-size: 30px; } }

  .foot { display: flex; align-items: center; gap: 12px; margin-top: 30px; }
  .foot .ghost { align-self: center; }
  .primary {
    all: unset; box-sizing: border-box; flex: 1; text-align: center; cursor: pointer; padding: 17px 24px;
    border-radius: 999px; font-size: 17px; font-weight: 800; background: var(--c); color: var(--ink-on-accent);
  }
  .primary:disabled { opacity: 0.4; cursor: default; }
</style>
