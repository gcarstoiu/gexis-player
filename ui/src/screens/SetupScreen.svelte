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
  import { setupPassword } from '../lib/state.js';

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
      <p class="lead">This screen shows when the player moves to your network.</p>
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
      <p class="lead">Put your phone back on {setup?.target ?? 'your Wi-Fi'} too.</p>
    {:else if step === 'done'}
      {@const f = setup.finished ?? {}}
      {@const lib = f.library ?? {}}
      <div class="big-icon">
        <svg viewBox="0 0 64 64" width="120" height="120" aria-hidden="true">
          <path d="M16 33 L28 45 L49 21" fill="none" stroke="currentColor" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </div>
      <h1 class="huge">{f.name ?? 'gexis'} is on {f.ssid ?? 'your network'}</h1>
      <!-- George, 2026-09-29: the Lyrion server, looked for once the player
           can see the home network. -->
      <p class="lead" class:lead--warn={lib.state === 'none' || lib.state === 'several'}>
        {#if lib.state === 'found'}Found your Lyrion server, {lib.name}.
        {:else if lib.state === 'given'}Lyrion: {lib.address}
        {:else if lib.state === 'several'}Found {lib.names?.length} Lyrion servers ({lib.names?.join(', ')}). Choose one in Settings.
        {:else}No Lyrion server found. Spotify Connect and Bluetooth work without one; choose a server in Settings later.
        {/if}
      </p>
      {#if f.restarting}<p class="lead">Restarting to take its new name…</p>{/if}
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
  .lead--warn { color: var(--accent-warn); }
  .detail {
    margin: 0;
    font-family: var(--font-mono);
    font-size: 20px;
    color: var(--ink-quiet);
    max-width: 60ch;
  }

  .pair {
    display: flex;
    align-items: center;
    gap: 56px;
    text-align: left;
  }
  .qr {
    width: 340px;
    height: 340px;
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
  @keyframes pulse { 50% { opacity: 0.5; } }
</style>
