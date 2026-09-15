<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Idle screen, Phase 4 step 4d (ADR-0019, ADR-0033). An overlay: whatever
  was underneath stays mounted, so dismissing it returns there. Shows the
  configured page when the daemon says it can be embedded; otherwise, and
  while that page loads, the design's drifting clock.
-->
<script>
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';

  let { ondismiss } = $props();

  let page = $state(null);
  let pageLoaded = $state(false);
  let now = $state(new Date());
  let spot = $state(randomSpot());

  function randomSpot() {
    return { x: Math.round(29 + Math.random() * 42), y: Math.round(24 + Math.random() * 52) };
  }

  onMount(() => {
    fetch('/idle')
      .then((r) => (r.ok ? r.json() : null))
      .then((result) => (page = result?.embeddable ? result.url : null))
      .catch(() => (page = null));

    const id = setInterval(() => {
      now = new Date();
      if (now.getSeconds() === 0) spot = randomSpot();
    }, 1000);
    return () => clearInterval(id);
  });

  const pad = (n) => String(n).padStart(2, '0');
</script>

<div class="idle" transition:fade={{ duration: 520 }}>
  <div class="clock" style:left={`${spot.x}%`} style:top={`${spot.y}%`}>
    <span class="clock__hm">{pad(now.getHours())}:{pad(now.getMinutes())}</span>
    <span class="clock__s">{pad(now.getSeconds())}</span>
  </div>

  {#if page}
    <!-- No allow-top-navigation: a page that frame-busts must not navigate the kiosk away from this UI. -->
    <iframe
      class="page"
      class:page--loaded={pageLoaded}
      src={page}
      title="Idle page"
      sandbox="allow-scripts allow-same-origin"
      onload={() => (pageLoaded = true)}
    ></iframe>
  {/if}

  <!-- Above the iframe, which would otherwise swallow the touch. -->
  <div class="touch" role="presentation" onpointerdown={ondismiss}></div>
</div>

<style>
  .idle {
    position: fixed;
    top: 0;
    left: 0;
    width: 1280px;
    height: 800px;
    z-index: 20;
    overflow: hidden;
    background: rgba(11, 18, 24, 0.93);
  }

  .clock {
    position: absolute;
    display: flex;
    align-items: baseline;
    gap: 14px;
    font-family: var(--font-mono);
    font-weight: 300;
    letter-spacing: -0.02em;
    white-space: nowrap;
    transform: translate(-50%, -50%);
    transition:
      left 1400ms cubic-bezier(0.4, 0, 0.2, 1),
      top 1400ms cubic-bezier(0.4, 0, 0.2, 1);
  }
  .clock__hm {
    font-size: var(--t-hero);
    line-height: 1;
    color: rgba(233, 238, 242, 0.82);
  }
  .clock__s {
    font-size: 58px;
    line-height: 1;
    color: rgba(126, 214, 188, 0.55);
  }

  .page {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    border: 0;
    opacity: 0;
    transition: opacity 520ms ease;
  }
  .page--loaded {
    opacity: 1;
  }

  .touch {
    position: absolute;
    inset: 0;
  }
</style>
