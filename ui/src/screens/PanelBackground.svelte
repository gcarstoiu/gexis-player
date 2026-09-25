<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The panel's backdrop: the design's diagonal weave and the current
  artwork's blurred bleed, drawn once behind every screen.

  Each screen used to carry its own copy, so every screen change built two
  large blurred layers again - a 70px blur over the whole panel and a 72px
  blur of the artwork. George, 2026-09-17: screen changes did not feel
  smooth, and neither sizing the artwork nor the CPU governor visibly helped.
  Screens now draw only their own veil and content over this, which is why
  exactly one of them is mounted at a time (App.svelte).
-->
<script>
  let { artwork = null } = $props();

  // A failed URL falls back to the weave alone, as the screens do for their
  // own artwork.
  let failed = $state(null);
  const src = $derived(artwork && artwork !== failed ? artwork : null);
</script>

<div class="bg" aria-hidden="true">
  <div class="weave"></div>
  {#if src}
    <img class="bleed" {src} alt="" onerror={() => (failed = artwork)} />
  {/if}
</div>

<style>
  .bg {
    position: absolute;
    inset: 0;
    z-index: 0;
    overflow: hidden;
    background: var(--bg-base);
    pointer-events: none;
    /* **A compositor layer of its own** (ADR-0060). The two blurs below
       cost nothing while the panel is still and everything during a
       scroll: a blur is re-evaluated over the region a frame damages, and
       a scroll damages the whole scroller. Promoted, the blur is rastered
       once and reused. The artist grid goes 27.8 -> 52.9 fps, as good as
       deleting the background, and the panel is pixel-identical - maximum
       difference 2 of 255 (Finding 061).

       Not `contain: paint`, which clips rather than promotes and does not
       help (26.6 fps), and not `translateZ(0)`, which is the same idea
       said less plainly and measured slightly worse. */
    will-change: transform;
  }
  .weave {
    position: absolute;
    inset: -90px;
    background: repeating-linear-gradient(38deg, var(--bg-weave-a) 0 48px, var(--bg-weave-b) 48px 96px);
    filter: blur(70px);
    transform: scale(1.14);
  }
  .bleed {
    position: absolute;
    inset: -120px;
    width: calc(100% + 240px);
    height: calc(100% + 240px);
    object-fit: cover;
    filter: blur(72px) saturate(1.7);
    transform: scale(1.12);
  }
</style>
