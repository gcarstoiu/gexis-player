<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0176: a page from Home Assistant on the screen, for a while - live
  cameras when the doorbell rings. Over everything the panel shows for the
  music, the idle screen and the dashboard included; nothing of the
  player's on it (P3). A page to look at: sandboxed as the idle page is,
  with a layer over it that takes any touch and closes it, and the touch
  does nothing else (George, 2026-11-07: any touch). A key does the same.

  The address comes from the core, to the panel only: it is not on /state,
  which anything on the network can read (P2). `seq` changes when there is
  a page to load - a new one, or the same one at a new address.
-->
<script>
  import { onMount } from 'svelte';

  let { seq, onclose } = $props();

  let url = $state(null);
  let loaded = $state(false);

  $effect(() => {
    seq;
    loaded = false;
    let gone = false;
    fetch('/panel/page', { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : null))
      .then((answer) => { if (!gone) url = answer?.shown ? (answer.url ?? null) : null; })
      .catch(() => {});
    return () => { gone = true; };
  });

  // What the page covers stops moving, as under the idle screen: a running
  // animation underneath keeps the Pi's browser compositing (Finding 118),
  // and live video needs the processor (Finding 142).
  onMount(() => {
    document.documentElement.classList.add('page-up');
    return () => document.documentElement.classList.remove('page-up');
  });

  function touched(event) {
    event.preventDefault();
    event.stopPropagation();
    onclose?.('touch');
  }

  // A keyboard's key (a remote's arrive through the core, which closes the
  // page itself): the D-pad's own handler passes it by under a cover.
  function pressed(event) {
    if (!event.isTrusted) return;
    event.preventDefault();
    onclose?.('key');
  }
</script>

<svelte:window onkeydowncapture={pressed} />

<div class="ha-page" role="presentation" data-ha-page data-dpad-cover>
  {#if url}
    <!-- No allow-top-navigation: a page that frame-busts must not navigate the kiosk away. -->
    <iframe
      class="ha-page__frame"
      class:is-loaded={loaded}
      src={url}
      title="A page from Home Assistant"
      tabindex="-1"
      sandbox="allow-scripts allow-same-origin"
      onload={() => (loaded = true)}
    ></iframe>
  {/if}
  <!-- Above the frame, which would otherwise swallow the touch. -->
  <div class="ha-page__touch" role="presentation" onpointerdown={touched}></div>
</div>

<style>
  :global(html.page-up body *:not(.ha-page):not(.ha-page *)) {
    animation-play-state: paused !important;
  }
  /* Over the idle screen (20), the dashboard (11) and a takeover (30, not
     drawn while this is up); under setup (31), pairing (32), Keep this
     screen? (33) and the update, which stay over it, and the standby
     cover. */
  .ha-page {
    position: fixed;
    inset: 0;
    z-index: 30;
    background: #000;
  }
  .ha-page__frame {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    border: 0;
    opacity: 0;
    background: transparent;
    pointer-events: none;
  }
  .ha-page__frame.is-loaded {
    opacity: 1;
    transition: opacity 0.2s;
  }
  .ha-page__touch {
    position: absolute;
    inset: 0;
  }
</style>
