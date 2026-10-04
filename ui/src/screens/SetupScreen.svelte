<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The panel during setup** (ADR-0104 §5, ADR-0031 as amended).

  Setup runs on the phone and only there (George, 2026-09-28: *"It is meant
  only for phone as the setting up device"*). This screen shows the way in and
  follows along, and takes no input (ADR-0029).

  **One step at a time, readable from two metres** (George, 2026-09-29: *"2 QR
  codes on the same screen is a bit much … center each on the screen with
  larger text"*, *"what we display on the panel should be visible at 1 or 2
  meters"*). The steps follow what the core sees:
    join     - nobody on the setup network: its QR code, name and password;
    joined   - a phone just arrived: a large confirmation, briefly;
    page     - a phone is on, the page not yet opened: the page's QR code;
    phone    - the page is open: setup carries on on the phone;
    joining  - the device is leaving for the chosen network.
  **Nothing under 30 px** that has to be read, so it reads at two metres on the
  10" panel; titles at 60, between the track title and the idle clock.

  **Mobile data off** is said on the join and page steps (George: he could not
  reach the page until he turned it off - the phone sent the request over
  mobile data because the setup network has no internet).

  **The QR codes are dark on light**: an inverted code is one some phone
  cameras do not read. **The password comes from `/setup/status`**, which gives
  it to the panel only; the state broadcast never carries it.
-->
<script>
  import { encode } from 'uqr';
  import mark from '../assets/gexis-mark.svg';
  import lyrionMark from '../assets/icon-lyrion.svg';
  import { setupPassword } from '../lib/state.js';
  import { screen } from '../lib/family.svelte.js';
  import { fitText } from '../lib/fit.js';

  let { setup } = $props();

  //: How long "Phone connected" stays before the next step.
  const JOINED_MS = 2500;

  const open = $derived(setup?.network === 'open');
  const overLan = $derived(setup?.needed && setup?.network === 'online' && !!setup?.address);

  let password = $state(null);
  $effect(() => {
    if (!open) {
      password = null;
      return;
    }
    let cancelled = false;
    setupPassword()
      .then((p) => { if (!cancelled) password = p; })
      .catch(() => {});
    return () => { cancelled = true; };
  });

  //: The moment a phone arrives, for the confirmation. Only a change from
  //: none to some counts; a phone that stays does not flash it again.
  let joinedUntil = $state(0);
  let lastPhones = 0;
  let tick = $state(0);
  $effect(() => {
    const phones = open ? (setup?.phones ?? 0) : 0;
    if (lastPhones === 0 && phones > 0) {
      joinedUntil = Date.now() + JOINED_MS;
      const id = setTimeout(() => (tick += 1), JOINED_MS + 50);
      lastPhones = phones;
      return () => clearTimeout(id);
    }
    lastPhones = phones;
  });

  const step = $derived.by(() => {
    tick;
    if (setup?.network === 'done') return 'done';
    if (setup?.network === 'joining') return 'joining';
    if (setup?.network === 'failed') return 'failed-start';
    if (overLan) return 'lan';
    if (!open) return 'starting';
    if ((setup?.phones ?? 0) === 0) return 'join';
    if (Date.now() < joinedUntil) return 'joined';
    return setup?.page_opened ? 'phone' : 'page';
  });

  //: Why setup's end restarts: a new name, a chosen screen (ADR-0109), or both.
  const restartLine = (f) =>
    f.restart_for === 'screen' ? 'Restarting on the chosen screen…'
      : f.restart_for === 'both' ? 'Restarting with its new name, on the chosen screen…'
        : 'Restarting to take its new name…';

  const esc = (v) => String(v ?? '').replace(/([\\;,:"])/g, '\\$1');
  const joinText = $derived(open && password ? `WIFI:T:WPA;S:${esc(setup.ssid)};P:${esc(password)};;` : null);
  function qrPath(text) {
    const { data, size } = encode(text, { ecc: 'M' });
    let d = '';
    for (let y = 0; y < size; y++)
      for (let x = 0; x < size; x++) if (data[y][x]) d += `M${x + 4} ${y + 4}h1v1h-1z`;
    return { d, extent: size + 8 };
  }
  const joinQr = $derived(joinText ? qrPath(joinText) : null);
  const pageQr = $derived(setup?.address ? qrPath(setup.address) : null);
  //: As a person types it: a phone's browser takes `10.42.0.1:8090` as is.
  const shown = (url) => String(url ?? '').replace(/^https?:\/\//, '').replace(/\/$/, '');

  const crumb = $derived(setup?.needed ? 'First-time setup' : 'Setup network');

  //: ADR-0109, Bar family (design `Bar Panels` s-new, s-lost, s-fail,
  //: s-joining; round 2 `Bar States` s-*): the same steps as strips. One QR
  //: code at 300 at the left, the facts beside it, the words at the right;
  //: or a 176 px circle with the title beside it.
  const bar = $derived(screen.family === 'bar');
  const wide = $derived(screen.width > 1500);
  //: A value that must be typed is never cut: it steps down until it fits
  //: its column, and wraps only past the last step.
  const valueSizes = [[44, 1], [40, 1], [36, 1], [32, 1], [28, 1], [24, 1], [22, 1]];
</script>

{#snippet qr(code, label)}
  {#if code}
    <svg class="qr" viewBox="0 0 {code.extent} {code.extent}" shape-rendering="crispEdges" aria-label={label}>
      <rect width={code.extent} height={code.extent} fill="#e9eef2" />
      <path d={code.d} fill="#101a21" />
    </svg>
  {:else}
    <div class="qr qr--empty"></div>
  {/if}
{/snippet}

{#snippet warnIcon(size)}
  <svg viewBox="0 0 64 64" width={size} height={size} aria-hidden="true">
    <path d="M32 7 L60 56 H4 Z" fill="none" stroke="currentColor" stroke-width="5" stroke-linejoin="round" />
    <path d="M32 24 V39" stroke="currentColor" stroke-width="5.5" stroke-linecap="round" />
    <circle cx="32" cy="47.5" r="3.4" fill="currentColor" />
  </svg>
{/snippet}

{#snippet mobileData()}
  <div class="warn">
    {@render warnIcon(44)}
    <span>Turn off <b>mobile data</b> on your phone while you set up</span>
  </div>
{/snippet}

{#snippet barMobileData()}
  <div class="bs__warn">
    {@render warnIcon(28)}
    <span>Turn off <b>mobile data</b> while you set up</span>
  </div>
{/snippet}

{#snippet barHero(icon, title, size, sub)}
  <div class="bs__stage bs__stage--hero">
    <div class="bs__circle" class:bs__circle--warn={icon === 'warn'} class:pulse={icon === 'wifi' || icon === 'mark'}>
      {#if icon === 'tick'}
        <svg viewBox="0 0 64 64" width="96" height="96" aria-hidden="true"><path d="M16 33 L28 45 L49 21" fill="none" stroke="currentColor" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" /></svg>
      {:else if icon === 'phone'}
        <svg viewBox="0 0 64 64" width="88" height="88" aria-hidden="true"><rect x="18" y="5" width="28" height="54" rx="6" fill="none" stroke="currentColor" stroke-width="5" /><path d="M28 51 H36" stroke="currentColor" stroke-width="5" stroke-linecap="round" /></svg>
      {:else if icon === 'wifi'}
        <svg viewBox="0 0 64 64" width="96" height="96" aria-hidden="true">
          <path d="M6 25 A37 37 0 0 1 58 25" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" />
          <path d="M15 34 A24 24 0 0 1 49 34" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" />
          <path d="M24 43 A12 12 0 0 1 40 43" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" />
          <circle cx="32" cy="52" r="4" fill="currentColor" />
        </svg>
      {:else if icon === 'warn'}
        {@render warnIcon(88)}
      {:else}
        <img src={mark} alt="" width="88" height="88" />
      {/if}
    </div>
    <div class="bs__herotext">
      <h1 class="bs__herotitle" style:font-size={`${size}px`}>{title}</h1>
      {#if sub}<p class="bs__herosub">{sub}</p>{/if}
      {#if icon === 'warn' && setup?.reason}<p class="bs__detail">{setup.reason}</p>{/if}
    </div>
    {#if step === 'done'}
      {@const lib = setup.finished?.library ?? {}}
      {#if lib.state && lib.state !== 'unchanged'}
        <div class="bs__lib" class:bs__lib--warn={lib.state === 'none' || lib.state === 'several'}>
          <img src={lyrionMark} alt="" width="78" height="58" />
          <div>
            {#if lib.state === 'found'}
              <b>Found your Lyrion server</b><span>{lib.name}{lib.name !== lib.address ? ` · ${lib.address}` : ''}</span>
            {:else if lib.state === 'given'}
              <b>Lyrion server</b><span>{lib.address}</span>
            {:else if lib.state === 'several'}
              <b>{lib.names?.length} Lyrion servers found</b><span>Choose one in Settings: {lib.names?.join(', ')}</span>
            {:else if lib.state === 'off'}
              <b>Lyrion is off</b><span>Switch it on in Settings any time.</span>
            {:else}
              <b>No Lyrion server found</b><span>Choose one in Settings when it is running.</span>
            {/if}
          </div>
        </div>
      {/if}
    {/if}
  </div>
{/snippet}

{#if bar}
<div class="setup setup--bar" role="status" aria-live="polite">
  <header class="bs__head">
    <img class="bs__mark" src={mark} alt="" width="32" height="32" />
    <span class="crumb bs__crumb grow">{crumb}</span>
    {#if open}<span class="crumb bs__crumb">Over {setup.ssid}</span>{/if}
  </header>

  {#if step === 'join' || step === 'page' || step === 'lan'}
    <div class="bs__stage">
      <div class="bs__qr">
        {#if step === 'join'}
          {@render qr(joinQr, `QR code to join ${setup?.ssid ?? ''}`)}
        {:else}
          {@render qr(pageQr, `QR code to open ${setup?.address ?? ''}`)}
        {/if}
      </div>
      <dl class="bs__facts">
        {#if step === 'join'}
          <dt>Network</dt><dd use:fitText={{ sizes: valueSizes, key: setup?.ssid, nowrapBreak: true }}>{setup?.ssid}</dd>
          <dt>Password</dt><dd use:fitText={{ sizes: valueSizes, key: password, nowrapBreak: true }}>{password ?? '…'}</dd>
        {:else}
          <dt>Or type</dt><dd use:fitText={{ sizes: valueSizes, key: setup?.address, nowrapBreak: true }}>{shown(setup?.address)}</dd>
          {#if step === 'page'}
            <dt>Your phone may say</dt><dd class="bs__small">“No internet”. Stay connected.</dd>
          {/if}
        {/if}
      </dl>
      <div class="bs__words">
        {#if step === 'join' && setup?.failed}
          <div class="bs__failhead">
            {@render warnIcon(64)}
            <h1>Could not join {setup.failed}</h1>
          </div>
          <p>{setup.reason ?? ''} Everything else you entered is kept.</p>
        {:else if step === 'join'}
          <h1>{setup?.needed ? 'Set up gexis' : 'gexis can’t reach its Wi-Fi'}</h1>
          <p>Scan to join{#if setup?.address}, then open <span class="bs__addr">{shown(setup.address)}</span>{/if}</p>
        {:else if step === 'page'}
          <h1>Now open the setup page</h1>
          <p>Scan with the same phone</p>
        {:else}
          <h1>Set up gexis</h1>
          <p>Scan with a phone on the same network as this player</p>
        {/if}
        {#if step !== 'lan'}{@render barMobileData()}{/if}
      </div>
    </div>
  {:else if step === 'joined'}
    {@render barHero('tick', 'Phone connected', 64, null)}
  {:else if step === 'phone'}
    {@render barHero('phone', 'Carry on on your phone', 64, 'Answer the questions on your phone. When you tap Finish, the player joins your Wi-Fi and this screen shows how it goes.')}
  {:else if step === 'joining'}
    {@render barHero('wifi', `Joining ${setup?.target ?? 'your Wi-Fi'}`, 64, `Check your phone is back on ${setup?.target ?? 'your Wi-Fi'}.`)}
  {:else if step === 'done'}
    {@const f = setup.finished ?? {}}
    {@render barHero('tick', `${f.name ?? 'gexis'} is on ${f.ssid ?? 'your network'}`, wide ? 56 : 44, f.restarting ? restartLine(f) : null)}
  {:else if step === 'failed-start'}
    {@render barHero('warn', 'The setup network did not start', 48, 'Trying again in a moment.')}
  {:else}
    {@render barHero('mark', 'Starting setup…', 64, null)}
  {/if}
</div>
{:else}
<div class="setup" role="status" aria-live="polite">
  <header>
    <img class="mark" src={mark} alt="" width="40" height="40" />
    <span class="crumb grow">{crumb}</span>
    {#if open}<span class="crumb">Over {setup.ssid}</span>{/if}
  </header>

  <main class="stage stage--{step}">
    {#if step === 'join'}
      {#if setup?.failed}
        <div class="banner">
          {@render warnIcon(64)}
          <div><b>Could not join {setup.failed}</b><span>{setup.reason ?? ''} Everything else you entered is kept.</span></div>
        </div>
      {:else}
        <h1>{setup?.needed ? 'Set up gexis' : 'gexis can’t reach its Wi-Fi'}</h1>
      {/if}
      <p class="lead">Scan with your phone to join the player’s Wi-Fi</p>
      <div class="pair">
        {@render qr(joinQr, `QR code to join ${setup?.ssid ?? ''}`)}
        <dl>
          <dt>Network</dt><dd>{setup?.ssid}</dd>
          <dt>Password</dt><dd>{password ?? '…'}</dd>
        </dl>
      </div>
      {@render mobileData()}
    {:else if step === 'joined'}
      <div class="big-icon">
        <svg viewBox="0 0 64 64" width="120" height="120" aria-hidden="true">
          <path d="M16 33 L28 45 L49 21" fill="none" stroke="currentColor" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </div>
      <h1 class="huge">Phone connected</h1>
    {:else if step === 'page'}
      <h1>Now open the setup page</h1>
      <p class="lead">Scan with the same phone</p>
      <div class="pair">
        {@render qr(pageQr, `QR code to open ${setup?.address ?? ''}`)}
        <dl>
          <dt>Or type</dt><dd class="nowrap">{shown(setup?.address)}</dd>
          <dt>Your phone may say</dt><dd class="small">“No internet”. Stay connected.</dd>
        </dl>
      </div>
      {@render mobileData()}
    {:else if step === 'phone'}
      <div class="big-icon">
        <svg viewBox="0 0 64 64" width="110" height="110" aria-hidden="true">
          <rect x="18" y="5" width="28" height="54" rx="6" fill="none" stroke="currentColor" stroke-width="5" />
          <path d="M28 51 H36" stroke="currentColor" stroke-width="5" stroke-linecap="round" />
        </svg>
      </div>
      <h1 class="huge">Carry on on your phone</h1>
      <p class="lead">Answer the questions on your phone. When you tap Finish, the player joins your Wi-Fi and this screen shows how it goes.</p>
    {:else if step === 'joining'}
      <div class="big-icon pulse">
        <svg viewBox="0 0 64 64" width="120" height="120" aria-hidden="true">
          <path d="M6 25 A37 37 0 0 1 58 25" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" />
          <path d="M15 34 A24 24 0 0 1 49 34" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" />
          <path d="M24 43 A12 12 0 0 1 40 43" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" />
          <circle cx="32" cy="52" r="4" fill="currentColor" />
        </svg>
      </div>
      <h1 class="huge">Joining {setup?.target ?? 'your Wi-Fi'}</h1>
      <!-- Shorter (George, 2026-10-04): most phones rejoin by themselves; this
           covers the ones that do not. -->
      <p class="lead">Check your phone is back on {setup?.target ?? 'your Wi-Fi'}.</p>
    {:else if step === 'done'}
      {@const f = setup.finished ?? {}}
      {@const lib = f.library ?? {}}
      <div class="big-icon">
        <svg viewBox="0 0 64 64" width="120" height="120" aria-hidden="true">
          <path d="M16 33 L28 45 L49 21" fill="none" stroke="currentColor" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </div>
      <h1 class="huge">{f.name ?? 'gexis'} is on {f.ssid ?? 'your network'}</h1>
      {#if f.restarting}<p class="lead">{restartLine(f)}</p>{/if}
      <!-- George, 2026-09-29: the Lyrion outcome apart from the joining, with
           its own mark and the server's address, so nobody is lost in it. -->
      {#if lib.state && lib.state !== 'unchanged'}
        <div class="lib" class:lib--warn={lib.state === 'none' || lib.state === 'several'}>
          <img src={lyrionMark} alt="" width="97" height="72" />
          <div>
            {#if lib.state === 'found'}
              <b>Found your Lyrion server</b><span>{lib.name}{lib.name !== lib.address ? ` · ${lib.address}` : ''}</span>
            {:else if lib.state === 'given'}
              <b>Lyrion server</b><span>{lib.address}</span>
            {:else if lib.state === 'several'}
              <b>{lib.names?.length} Lyrion servers found</b><span>Choose one in Settings: {lib.names?.join(', ')}</span>
            {:else if lib.state === 'off'}
              <b>Lyrion is off</b><span>Switch it on in Settings any time.</span>
            {:else}
              <b>No Lyrion server found</b><span>Choose one in Settings when it is running.</span>
            {/if}
          </div>
        </div>
      {/if}
    {:else if step === 'lan'}
      <h1>Set up gexis</h1>
      <p class="lead">Scan with a phone on the same network as this player</p>
      <div class="pair">
        {@render qr(pageQr, `QR code to open ${setup?.address ?? ''}`)}
        <dl><dt>Or type</dt><dd class="nowrap">{shown(setup?.address)}</dd></dl>
      </div>
    {:else if step === 'failed-start'}
      <div class="big-icon big-icon--warn">{@render warnIcon(110)}</div>
      <h1>The setup network did not start</h1>
      <p class="lead">Trying again in a moment.</p>
      <p class="detail">{setup?.reason ?? ''}</p>
    {:else}
      <div class="big-icon pulse">
        <img src={mark} alt="" width="110" height="110" />
      </div>
      <h1 class="huge">Starting setup…</h1>
    {/if}
  </main>
</div>
{/if}

<style>
  .setup {
    position: absolute;
    inset: 0;
    /* Above the handoff (30), below a pairing request (32). */
    z-index: 31;
    display: flex;
    flex-direction: column;
    padding: 30px 56px 36px;
    color: var(--ink);
    background:
      radial-gradient(130% 105% at 20% 42%, rgba(20, 33, 42, 0.72), rgba(13, 21, 28, 0.96)),
      var(--bg-base);
  }
  header {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .mark { width: 40px; height: 40px; }
  .crumb {
    font-family: var(--font-mono);
    font-size: 16px;
    letter-spacing: var(--track-label);
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .grow { flex: 1; }

  .stage {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    /* George, 2026-09-29: "everything is a bit compressed". */
    gap: 34px;
    text-align: center;
    min-height: 0;
  }
  .stage--join, .stage--page { gap: 30px; }
  /* A title and the line under it belong together; the rest stands apart. */
  h1 + .lead, .banner + .lead { margin-top: -18px; }
  h1 {
    margin: 0;
    font-size: 60px;
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1.05;
  }
  h1.huge { font-size: 72px; }
  .lead {
    margin: 0;
    font-size: 32px;
    line-height: 1.3;
    color: var(--ink-body);
    text-wrap: balance;
  }
  .lib {
    margin-top: 18px;
    display: flex;
    align-items: center;
    gap: 26px;
    padding: 24px 34px;
    text-align: left;
    border-radius: var(--r-card);
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--ink-line);
  }
  .lib img { flex-shrink: 0; }
  .lib b { display: block; font-size: 34px; font-weight: 700; }
  .lib span { display: block; margin-top: 6px; font-family: var(--font-mono); font-size: 28px; color: var(--ink-body); }
  .lib--warn b { color: var(--accent-warn); }
  /* A sentence now, not the system's line (2026-10-03): the body face. */
  .detail {
    margin: 0;
    font-size: 24px;
    color: var(--ink-quiet);
    max-width: 60ch;
  }

  .pair {
    display: flex;
    align-items: center;
    gap: 56px;
    text-align: left;
  }
  /* ADR-0109: the QR code is what gives up height on a shorter screen (260
     at 720, the 13.3"); at 800 and taller it is the design's 340. The
     tallest step, *Could not join*, just fits at 800. */
  .qr {
    width: min(340px, calc(var(--panel-h) - 460px));
    height: min(340px, calc(var(--panel-h) - 460px));
    border-radius: var(--r-lg);
    flex-shrink: 0;
  }
  .qr--empty { background: var(--ink-fill); }
  dl { margin: 0; }
  dt {
    font-family: var(--font-mono);
    font-size: 18px;
    letter-spacing: var(--track-label);
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  dd {
    margin: 6px 0 26px;
    font-family: var(--font-mono);
    font-size: 48px;
    font-weight: 700;
    letter-spacing: 0.02em;
  }
  dd:last-child { margin-bottom: 0; }
  /* No width cap: it wrapped with room to spare (George, 2026-09-29). */
  dd.small { font-family: var(--font-ui); font-size: 30px; font-weight: 600; letter-spacing: 0; white-space: nowrap; }
  .nowrap { white-space: nowrap; }

  .warn {
    margin-top: 8px;
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 18px 30px;
    border-radius: var(--r-lg);
    font-size: 30px;
    color: var(--accent-warn);
    background: color-mix(in srgb, var(--accent-warn) 12%, transparent);
    border: 2px solid color-mix(in srgb, var(--accent-warn) 45%, transparent);
  }
  .warn b { color: var(--ink); }

  .banner {
    display: flex;
    align-items: center;
    gap: 24px;
    text-align: left;
    color: var(--accent-warn);
  }
  .banner b { display: block; font-size: 54px; font-weight: 800; color: var(--ink); line-height: 1.05; }
  .banner span { display: block; font-size: 30px; color: var(--ink-body); margin-top: 6px; }

  .big-icon {
    width: 220px;
    height: 220px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    --tone: var(--accent-lms);
    color: var(--tone);
    background: color-mix(in srgb, var(--tone) 14%, transparent);
    border: 3px solid color-mix(in srgb, var(--tone) 45%, transparent);
  }
  .big-icon--warn { --tone: var(--accent-warn); }
  .pulse { animation: pulse 1.6s ease-in-out infinite; }

  /* ADR-0109, Bar family: `Bar Panels` s-*, `Bar States` s-*. */
  .setup--bar {
    padding: 0;
    display: block;
  }
  .bs__head {
    position: absolute;
    left: 40px;
    right: 40px;
    top: 22px;
    gap: 14px;
    z-index: 2;
  }
  .bs__mark { width: 32px; height: 32px; display: block; }
  .bs__crumb { font-size: 15px; }
  .bs__stage {
    position: absolute;
    inset: 66px 40px 24px;
    display: flex;
    align-items: center;
    gap: 48px;
  }
  .bs__qr {
    margin-top: -10px;
    flex-shrink: 0;
  }
  .bs__qr .qr {
    width: 300px;
    height: 300px;
    display: block;
  }
  /* Shrinks only as far as its values let it: they step down to fit. */
  .bs__facts {
    flex: 0 1 auto;
    min-width: 0;
  }
  .bs__facts dd {
    margin: 6px 0 22px;
    font-size: 44px;
    line-height: 1.1;
    white-space: nowrap;
  }
  .bs__facts dd:last-child { margin-bottom: 0; }
  .bs__facts dd.bs__small {
    font-family: var(--font-ui);
    font-size: 26px;
    font-weight: 600;
    letter-spacing: 0.02em;
  }
  /* The words keep enough room that "Set up gexis" stays on one line. */
  .bs__words {
    flex: 1 0 260px;
    min-width: 260px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .bs__words h1 {
    font-size: 40px;
    line-height: 1.08;
  }
  .bs__words p {
    margin: 0;
    font-size: 24px;
    line-height: 1.35;
    color: var(--ink-body);
  }
  .bs__addr {
    font-family: var(--font-mono);
    font-weight: 700;
    color: var(--ink);
    white-space: nowrap;
  }
  .bs__failhead {
    display: flex;
    align-items: flex-start;
    gap: 18px;
    color: var(--accent-warn);
  }
  .bs__failhead :global(svg) { flex-shrink: 0; }
  .bs__failhead h1 { color: var(--ink); }
  .bs__warn {
    align-self: flex-start;
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 12px 18px;
    border-radius: 14px;
    font-size: 20px;
    color: var(--accent-warn);
    background: color-mix(in srgb, var(--accent-warn) 12%, transparent);
    border: 2px solid color-mix(in srgb, var(--accent-warn) 45%, transparent);
  }
  .bs__warn :global(svg) { flex-shrink: 0; }
  .bs__warn b { color: var(--ink); }

  .bs__stage--hero {
    justify-content: center;
    text-align: left;
  }
  .bs__circle {
    width: 176px;
    height: 176px;
    border-radius: 50%;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    --tone: var(--accent-lms);
    color: var(--tone);
    background: color-mix(in srgb, var(--tone) 14%, transparent);
    border: 3px solid color-mix(in srgb, var(--tone) 45%, transparent);
  }
  .bs__circle--warn { --tone: var(--accent-warn); }
  .bs__herotext {
    min-width: 0;
    flex-shrink: 1;
  }
  .bs__herotitle {
    font-size: 64px;
    line-height: 1.05;
  }
  .bs__herosub {
    margin: 12px 0 0;
    font-size: 28px;
    line-height: 1.3;
    color: var(--ink-body);
  }
  .bs__detail {
    margin: 12px 0 0;
    font-size: 20px;
    color: var(--ink-quiet);
  }
  .bs__lib {
    display: flex;
    align-items: center;
    gap: 22px;
    padding: 22px 28px;
    border-radius: var(--r-card);
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--ink-line);
    flex-shrink: 0;
    max-width: 440px;
  }
  .bs__lib img { flex-shrink: 0; }
  .bs__lib div { min-width: 0; }
  .bs__lib b { display: block; font-size: 28px; font-weight: 700; }
  .bs__lib span {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    margin-top: 6px;
    font-family: var(--font-mono);
    font-size: 20px;
    color: var(--ink-body);
  }
  .bs__lib--warn b { color: var(--accent-warn); }
  @keyframes pulse { 50% { opacity: 0.5; } }
</style>
