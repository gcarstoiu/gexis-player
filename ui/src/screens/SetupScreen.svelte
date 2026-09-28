<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The panel during setup** (ADR-0104 §5, ADR-0031 as amended).

  Setup runs on the phone and only there (George, 2026-09-28: *"It is meant
  only for phone as the setting up device"*). This screen shows the way in -
  the setup network, its password, the page's address, and a QR code for each
  - and takes no input (ADR-0029). Nothing in the design draws it, so it is
  built from the design's own parts: the gexis mark and the mono crumb of
  Setup's header, its step accents on the cards, its type.

  **The QR codes are dark on light.** The panel is dark everywhere else, but an
  inverted code is one some phone cameras do not read, and this is the one
  screen where a code that does not scan is a device nobody can set up.

  **The password comes from `/setup/status`, not the state broadcast**, which
  every phone reads: the core gives it to a loopback caller only.
-->
<script>
  import { encode } from 'uqr';
  import mark from '../assets/gexis-mark.svg';
  import { setupPassword } from '../lib/state.js';

  let { setup } = $props();

  const open = $derived(setup?.network === 'open');
  //: A new device on Ethernet: the page is on the ordinary network and there
  //: is no setup network to join (ADR-0031 amendment 8).
  const overLan = $derived(setup?.needed && setup?.network === 'online' && !!setup?.address);

  let password = $state(null);
  $effect(() => {
    if (!open) {
      password = null;
      return;
    }
    let cancelled = false;
    // Fetched again whenever the network reopens: a restart may have made it
    // for a panel that has since been unplugged, and the core knows which.
    setupPassword()
      .then((p) => { if (!cancelled) password = p; })
      .catch(() => {});
    return () => { cancelled = true; };
  });

  //: The Wi-Fi QR format: `\`, `;`, `,`, `:` and `"` are escaped in both
  //: fields, which a made-up password never contains but a future one might.
  const esc = (v) => String(v ?? '').replace(/([\\;,:"])/g, '\\$1');
  const joinText = $derived(open && password ? `WIFI:T:WPA;S:${esc(setup.ssid)};P:${esc(password)};;` : null);

  //: One path per code: a square per dark module, drawn with a four-module
  //: quiet zone, which is what a camera needs to find the code at all.
  function qrPath(text) {
    const { data, size } = encode(text, { ecc: 'M' });
    let d = '';
    for (let y = 0; y < size; y++)
      for (let x = 0; x < size; x++) if (data[y][x]) d += `M${x + 4} ${y + 4}h1v1h-1z`;
    return { d, extent: size + 8 };
  }
  //: The address as a person types it: a phone's browser takes
  //: `10.42.0.1:8090` as it is, and the scheme and slash cost a line on the
  //: first trial. The QR code carries the full address.
  const shown = (url) => String(url ?? '').replace(/^https?:\/\//, '').replace(/\/$/, '');

  const joinQr = $derived(joinText ? qrPath(joinText) : null);
  const pageQr = $derived(setup?.address ? qrPath(setup.address) : null);

  const heading = $derived(
    setup?.needed ? 'Set up' : 'gexis cannot reach its Wi-Fi'
  );
  const lead = $derived(
    setup?.needed
      ? 'Setup runs on your phone. This screen only shows it the way in.'
      : 'Join its setup network from your phone to choose another. It also looks for yours every five minutes.'
  );
</script>

<div class="setup" role="status" aria-live="polite">
  <header>
    <img class="mark" src={mark} alt="" width="38" height="38" />
    <span class="crumb">{setup?.needed ? 'First-time setup' : 'Setup network'}</span>
    {#if open}<span class="over">Over {setup.ssid}</span>{/if}
  </header>

  <h1>{heading}{#if setup?.needed}&nbsp;<span class="word">gexis</span>{/if}</h1>
  <p class="lead">{lead}</p>

  {#if open}
    <div class="cards">
      <section class="card" style="--accent: #8fc4d8">
        <span class="bar"></span>
        <div class="body">
          <div class="eyebrow">1 · Join this Wi-Fi</div>
          <div class="pair">
            {#if joinQr}
              <svg class="qr" viewBox="0 0 {joinQr.extent} {joinQr.extent}" shape-rendering="crispEdges" aria-label="QR code to join {setup.ssid}">
                <rect width={joinQr.extent} height={joinQr.extent} fill="#e9eef2" />
                <path d={joinQr.d} fill="#101a21" />
              </svg>
            {:else}
              <div class="qr qr--empty"></div>
            {/if}
            <dl>
              <dt>Network</dt>
              <dd class="mono">{setup.ssid}</dd>
              <dt>Password</dt>
              <dd class="mono">{password ?? '…'}</dd>
            </dl>
          </div>
          <p class="note">Your phone may say this network has no internet. Stay connected.</p>
        </div>
      </section>

      <section class="card" style="--accent: #7ed6bc">
        <span class="bar"></span>
        <div class="body">
          <div class="eyebrow">2 · Open the setup page</div>
          <div class="pair">
            {#if pageQr}
              <svg class="qr" viewBox="0 0 {pageQr.extent} {pageQr.extent}" shape-rendering="crispEdges" aria-label="QR code to open {setup.address}">
                <rect width={pageQr.extent} height={pageQr.extent} fill="#e9eef2" />
                <path d={pageQr.d} fill="#101a21" />
              </svg>
            {/if}
            <dl>
              <dt>Address</dt>
              <dd class="mono nowrap">{shown(setup.address)}</dd>
            </dl>
          </div>
          <p class="note">Once your phone is on the setup network.</p>
        </div>
      </section>
    </div>
  {:else if overLan}
    <div class="cards cards--one">
      <section class="card" style="--accent: #7ed6bc">
        <span class="bar"></span>
        <div class="body">
          <div class="eyebrow">Open the setup page</div>
          <div class="pair">
            <svg class="qr" viewBox="0 0 {pageQr.extent} {pageQr.extent}" shape-rendering="crispEdges" aria-label="QR code to open {setup.address}">
              <rect width={pageQr.extent} height={pageQr.extent} fill="#e9eef2" />
              <path d={pageQr.d} fill="#101a21" />
            </svg>
            <dl>
              <dt>Address</dt>
              <dd class="mono nowrap">{shown(setup.address)}</dd>
            </dl>
          </div>
          <p class="note">From a phone on the same network as this player.</p>
        </div>
      </section>
    </div>
  {:else if setup?.network === 'joining'}
    <p class="state">Your Wi-Fi is back in range. Joining it…</p>
  {:else if setup?.network === 'failed'}
    <p class="state state--warn">The setup network did not start{setup.reason ? `: ${setup.reason}` : '.'}</p>
  {:else}
    <p class="state">Starting setup…</p>
  {/if}
</div>

<style>
  .setup {
    position: absolute;
    inset: 0;
    /* Above the handoff (30), below a pairing request (32), which is the one
       thing that still has to be answered on this glass. */
    z-index: 31;
    padding: 44px 56px;
    display: flex;
    flex-direction: column;
    color: var(--ink);
    /* Opaque: the screen it covers read through it on the first trial. The
       design's scrim over its own ground colour. */
    background:
      radial-gradient(130% 105% at 20% 42%, rgba(20, 33, 42, 0.72), rgba(13, 21, 28, 0.96)),
      var(--bg-base);
  }

  header {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .mark {
    width: 38px;
    height: 38px;
    flex-shrink: 0;
  }
  .crumb,
  .over,
  .eyebrow,
  dt {
    font-family: var(--font-mono);
    font-size: var(--t-label);
    letter-spacing: var(--track-label);
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .crumb {
    flex: 1;
  }

  h1 {
    margin: 30px 0 0;
    font-size: 40px;
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1.1;
  }
  .word {
    font-weight: 600;
  }
  .lead {
    margin: 12px 0 0;
    font-size: var(--t-body);
    line-height: 1.5;
    color: var(--ink-muted);
    max-width: 60ch;
  }

  .cards {
    margin-top: 30px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 22px;
    flex: 1;
    min-height: 0;
  }
  .cards--one {
    grid-template-columns: minmax(0, 620px);
  }
  .card {
    display: flex;
    gap: 16px;
    padding: 22px 24px;
    border-radius: var(--r-lg);
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--ink-line);
    min-width: 0;
  }
  .bar {
    width: 4px;
    border-radius: 2px;
    background: var(--accent);
    flex-shrink: 0;
  }
  .body {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .eyebrow {
    color: var(--accent);
  }
  .pair {
    margin-top: 18px;
    display: flex;
    gap: 24px;
    align-items: center;
  }
  .qr {
    width: 236px;
    height: 236px;
    flex-shrink: 0;
    border-radius: var(--r-md);
  }
  .qr--empty {
    background: var(--ink-fill);
  }
  dl {
    margin: 0;
    min-width: 0;
  }
  dd {
    margin: 6px 0 20px;
    font-size: var(--t-h3);
    font-weight: 700;
    overflow-wrap: anywhere;
  }
  dd:last-child {
    margin-bottom: 0;
  }
  .nowrap {
    white-space: nowrap;
  }
  .mono {
    font-family: var(--font-mono);
    letter-spacing: 0.02em;
  }
  .note {
    margin: auto 0 0;
    padding-top: 16px;
    font-size: var(--t-body-sm);
    line-height: 1.45;
    color: var(--ink-quiet);
  }

  .state {
    margin-top: 40px;
    font-size: var(--t-h3);
    font-weight: 600;
  }
  .state--warn {
    color: var(--accent-warn);
  }
</style>
