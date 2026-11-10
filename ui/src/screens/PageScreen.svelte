<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0176: a page from Home Assistant on the screen, for a while - live
  cameras when the doorbell rings. Over everything the panel shows for the
  music, the idle screen and the dashboard included; nothing of the
  player's on it (P3). A page to look at: sandboxed as the idle page is,
  with a layer over it that takes any touch and closes it, and the touch
  does nothing else (George, 2026-11-07: any touch). A key does the same.

  The amendment (K3): one page can be kept loaded, framed from the start
  with `visibility: hidden` - laid out at the screen's size, drawing
  nothing, taking no touch (Finding 143) - so a show of its address only
  reveals it. Any other address loads in a frame of its own over it. Every
  close hides it again.

  The addresses come from the core, to the panel only: they are not on
  /state, which anything on the network can read (P2). `seq` changes when
  there is a page to load - a new one, the same one at a new address, or a
  page to keep.
-->
<script>
  let { shown, seq, onclose } = $props();

  let url = $state(null);
  let loaded = $state(false);
  // `{url, n}`: `n` changes when it is to be loaded afresh (K1).
  let preload = $state(null);
  let preloadLoaded = $state(false);

  $effect(() => {
    seq;
    let gone = false;
    fetch('/panel/page', { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : null))
      .then((answer) => {
        if (gone) return;
        // **The page shown stays unless its address changed** (the review
        // of 1.16.1): the kept page renewed or cleared reloaded it.
        const shownUrl = shown && answer?.shown ? (answer.url ?? null) : null;
        if (shownUrl !== url) {
          url = shownUrl;
          loaded = false;
        }
        const next = answer?.preload ?? null;
        if (!next) preload = null;
        else if (next.url !== preload?.url || next.n !== preload?.n) {
          preloadLoaded = false;
          preload = next;
        }
      })
      .catch(() => {});
    return () => { gone = true; };
  });
  // Gone, it takes its address with it: the next page starts from none.
  $effect(() => {
    if (shown) return;
    url = null;
    loaded = false;
  });

  const kept = $derived(shown && !!preload && url === preload.url);

  // What the page covers stops moving, as under the idle screen: a running
  // animation underneath keeps the Pi's browser compositing (Finding 118),
  // and live video needs the processor (Finding 142).
  $effect(() => {
    if (!shown) return;
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
    if (!shown || !event.isTrusted) return;
    event.preventDefault();
    onclose?.('key');
  }
</script>

<svelte:window onkeydowncapture={pressed} />

<div class="ha-page" class:is-shown={shown} role="presentation"
     data-ha-page={shown ? '' : undefined} data-dpad-cover={shown ? '' : undefined}>
  <!-- No allow-top-navigation: a page that frame-busts must not navigate the kiosk away. -->
  {#if preload}
    {#key preload.n}
      <iframe
        class="ha-page__frame"
        class:is-loaded={preloadLoaded}
        class:is-hidden={!kept}
        src={preload.url}
        title="A page from Home Assistant, kept loaded"
        tabindex="-1"
        sandbox="allow-scripts allow-same-origin"
        onload={() => (preloadLoaded = true)}
      ></iframe>
    {/key}
  {/if}
  {#if shown && url && !kept}
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
  {#if shown}
    <!-- Above the frames, which would otherwise swallow the touch. -->
    <div class="ha-page__touch" role="presentation" onpointerdown={touched}></div>
  {/if}
</div>

<style>
  :global(html.page-up body *:not(.ha-page):not(.ha-page *)) {
    animation-play-state: paused !important;
  }
  /* Over the idle screen (20), the dashboard (11) and a takeover (30, not
     drawn while this is up); under setup (31), pairing (32), Keep this
     screen? (33) and the update, which stay over it, and the standby
     cover. Not shown, it is there only for the page kept loaded: nothing
     of it is seen or touched. */
  .ha-page {
    position: fixed;
    inset: 0;
    z-index: 30;
    visibility: hidden;
    pointer-events: none;
  }
  .ha-page.is-shown {
    visibility: visible;
    pointer-events: auto;
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
  .ha-page__frame.is-hidden {
    visibility: hidden;
  }
  .ha-page__touch {
    position: absolute;
    inset: 0;
  }
</style>
