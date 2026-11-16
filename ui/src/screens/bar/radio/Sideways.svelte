<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **A Radio page's sideways row** on a bar (design/source/31, B01-B13): the
  bar's scroller (sideways.svelte.js - a finger natively, a mouse by drag),
  from 32 px right of the side column, fading before the rail - 110 px on
  Radio's tiles, 140 on the lists - only while there is more beyond.
  `onnear` is called as the end comes within a screen's reach, for the
  next page.
-->
<script>
  import { untrack } from 'svelte';
  import { dragScroll, watchSideways } from '../sideways.svelte.js';

  let {
    children,
    fade = 140,
    //: Where the row sits in the page's height: centred (the lists) or at its top.
    align = 'center',
    onnear = null,
    el = $bindable(null),
  } = $props();

  const side = watchSideways();
  //: The design's fade at the end; a short one at the start once scrolled,
  //: so a card does not stop dead against the side column.
  const mask = $derived(
    'linear-gradient(90deg,' +
      (side.moreBefore ? 'transparent 0,#000 32px,' : '#000 0,') +
      (side.moreAfter ? `#000 calc(100% - ${fade}px),transparent 100%)` : '#000 100%)'),
  );

  const NEAR = 900;
  $effect(() => {
    // Read every time the row moves or grows: a page short of the width
    // asks for the next one at once.
    const left = side.left;
    const view = side.view;
    void side.moreAfter;
    if (!onnear || !el || !view) return;
    // Untracked: what the caller reads to decide is not this effect's to
    // follow (LESSONS 31).
    if (el.scrollWidth - (left + view) < NEAR) untrack(onnear);
  });
</script>

<div class="row" class:row--start={align === 'start'} style:mask-image={mask} style:-webkit-mask-image={mask}>
  <div class="scroll" bind:this={el} use:side.attach use:dragScroll data-dpad-start>
    {@render children()}
  </div>
</div>

<style>
  .row {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-width: 0;
    /* Its own layer, so the mask is rasterised once rather than with every
       frame of the scroll under it (BarLibrary's `.mask`). */
    will-change: transform;
  }
  .row--start {
    justify-content: flex-start;
  }
  .scroll {
    display: flex;
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: none;
    touch-action: pan-x;
    overscroll-behavior-x: contain;
    padding: 0 32px;
    scroll-padding: 0 32px;
  }
  .scroll::-webkit-scrollbar {
    display: none;
  }
</style>
