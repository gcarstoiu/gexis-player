<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0156: a Home Assistant dashboard on the screen. The room's dashboard,
  full screen and every part of it the dashboard's own: no layer over it to
  take the first touch, as the idle page has. The only part that is not
  Home Assistant's is the edge tab that dismisses it (George, 2026-10-21:
  "Edge tab").

  The core checks the address first, as it does for the idle page: a frame
  cannot say why it is blank. When it cannot be shown - no address, no
  answer, or Home Assistant refusing to be framed - the screen says what to
  set and where, never a blank page (decision 8: the user sets it in Home
  Assistant; the player changes nothing there).
-->
<script>
  import { onMount } from 'svelte';

  let { ondismiss } = $props();

  //: The core's answer: `{url, embeddable, message}`; null while asking.
  let check = $state(null);
  let loaded = $state(false);

  onMount(async () => {
    try {
      const r = await fetch('/panel/dashboard', { cache: 'no-store' });
      check = r.ok ? await r.json() : { embeddable: false, message: 'The player could not check the dashboard.' };
    } catch {
      check = { embeddable: false, message: 'The player could not check the dashboard.' };
    }
  });
</script>

<div class="dash" role="presentation" data-dpad-layer data-dpad-frame
  ondpadback={(event) => { event.preventDefault(); ondismiss?.(); }}>
  {#if check?.embeddable}
    <iframe
      class="dash__page"
      class:is-loaded={loaded}
      src={check.url}
      title="Home Assistant dashboard"
      data-real-input
      sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
      onload={() => (loaded = true)}
    ></iframe>
  {:else if check}
    <div class="dash__said">
      <span class="dash__title">The dashboard can't be shown</span>
      <span class="dash__why">{check.message}</span>
      <button class="dash__close" type="button" onclick={() => ondismiss?.()}>Close</button>
    </div>
  {/if}

  <!-- The edge tab: the one part of the screen that is not the dashboard's. -->
  <button class="tab" type="button" aria-label="Close the dashboard" onclick={() => ondismiss?.()}>
    <span class="tab__face"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7l10 10M17 7 7 17" /></svg></span>
  </button>
</div>

<style>
  /* Below the volume drawer (12-13), which still comes over it on a change
     from elsewhere; above every screen (5). The idle screen (20) and the
     takeover (30) are not drawn while it is up. */
  .dash {
    position: fixed;
    inset: 0;
    z-index: 11;
    background: var(--bg-panel, #0b1014);
  }
  .dash__page {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    border: 0;
    opacity: 0;
    background: transparent;
  }
  .dash__page.is-loaded { opacity: 1; }
  .dash__said {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 14px;
    padding: 0 96px;
    text-align: center;
    color: var(--ink, #e9eef2);
  }
  .dash__title { font-size: 24px; font-weight: 700; }
  .dash__why { max-width: 760px; font-size: 18px; line-height: 1.4; color: rgba(233, 238, 242, 0.72); }
  .dash__close {
    margin-top: 6px;
    height: 48px;
    padding: 0 28px;
    border: 1px solid rgba(233, 238, 242, 0.24);
    border-radius: 999px;
    background: rgba(233, 238, 242, 0.06);
    color: inherit;
    font: inherit;
    font-size: 17px;
    font-weight: 600;
  }
  /* A touch target taller and wider than what it shows, at the right edge's
     middle: within reach on a bar 320 px high as on a 16:9 screen. */
  .tab {
    position: absolute;
    right: 0;
    top: 50%;
    width: 44px;
    height: 104px;
    margin-top: -52px;
    padding: 0;
    border: 0;
    background: none;
    display: flex;
    align-items: center;
    justify-content: flex-end;
  }
  .tab__face {
    width: 30px;
    height: 84px;
    border-radius: 14px 0 0 14px;
    background: rgba(11, 16, 20, 0.78);
    border: 1px solid rgba(233, 238, 242, 0.22);
    border-right: 0;
    display: grid;
    place-items: center;
  }
  .tab svg {
    width: 18px;
    height: 18px;
    fill: none;
    stroke: rgba(233, 238, 242, 0.9);
    stroke-width: 2.2;
    stroke-linecap: round;
  }
</style>
