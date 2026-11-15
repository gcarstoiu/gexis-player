<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  A Radio page's scrolling column, under the header and over the mini
  strip. `bar`: the 4 px scrollbar the favourites list draws, 14 from the
  right (P08) - drawn here rather than left to the browser's, which the
  panel's Chromium may not show; elsewhere none, as the library's lists.
-->
<script>
  let { children, padding = '20px 40px', gap = '4px', bar = false, el = $bindable(null) } = $props();

  //: The artboard's track: 34 under the header, 26 over the strip.
  const TRACK_TOP = 34;
  const TRACK_BOTTOM = 26;
  let thumb = $state(null);
  function place() {
    if (!el) return;
    const { scrollTop, scrollHeight, clientHeight } = el;
    if (scrollHeight <= clientHeight + 1) {
      thumb = null;
      return;
    }
    const track = clientHeight - TRACK_TOP - TRACK_BOTTOM;
    const h = Math.max(32, Math.round((track * clientHeight) / scrollHeight));
    const y = Math.round(((track - h) * scrollTop) / (scrollHeight - clientHeight));
    thumb = { h, y };
  }
  $effect(() => {
    if (!bar || !el) return;
    place();
    const watch = new ResizeObserver(place);
    watch.observe(el);
    const rows = new MutationObserver(place);
    rows.observe(el, { childList: true });
    return () => {
      watch.disconnect();
      rows.disconnect();
    };
  });
</script>

<div class="scroll" style:padding style:gap bind:this={el} data-radio-scroll data-dpad-start
  onscroll={bar ? place : undefined}>
  {@render children()}
</div>
{#if bar && thumb}
  <div class="track" aria-hidden="true">
    <div class="thumb" style:height="{thumb.h}px" style:transform="translateY({thumb.y}px)"></div>
  </div>
{/if}

<style>
  .scroll {
    position: absolute;
    inset: 0;
    overflow-y: auto;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    scrollbar-width: none;
    overscroll-behavior: contain;
    touch-action: pan-y;
  }
  .scroll::-webkit-scrollbar {
    display: none;
  }
  .track {
    position: absolute;
    right: 14px;
    top: 34px;
    bottom: 26px;
    width: 4px;
    border-radius: 2px;
    background: var(--c-ink-08);
    pointer-events: none;
  }
  .thumb {
    width: 4px;
    border-radius: 2px;
    background: var(--c-ink-40);
  }
</style>
