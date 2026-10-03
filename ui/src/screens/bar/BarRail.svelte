<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The library's mini player on a bar (ADR-0109, Bar family): a 124 px rail on
  the right of every library screen, where the panel has its mini strip.
  From `design/source/13b/Bar Frame.dc.html` (variant home2, layout c) and
  `Bar States.dc.html` (lib-rail-empty), round 2.

  - The cover, 84 px; the renderer's mark, 26; play, 64.
  - Progress is a 3 px line on the rail's inner (left) edge, filling **from
    the bottom**, in the source's accent at 0.8. As on the panel's mini
    strip, it is drawn only when the renderer reports a position.
  - **Nothing playing:** an empty slot, no mark, no progress, and play at
    0.3 and inert (round 2). This is the bar's whole answer to the panel's
    waiting services: the rail is where the renderer would be.

  A tap anywhere but play opens now playing, as the mini strip does.
-->
<script>
  import { enrichedArtwork } from '../../lib/enrichment.js';
  import SourceMark from '../../lib/SourceMark.svelte';
  import { playhead } from '../../lib/playhead.svelte.js';
  import { playToggle } from '../../lib/playToggle.svelte.js';

  let { active, metadata, controls = [], onopen } = $props();

  const transport = $derived(metadata?.transport ?? null);
  const head = playhead(() => metadata);
  const toggle = playToggle(() => transport, () => active);
  const hasPlayPause = $derived(controls.includes('play') && controls.includes('pause'));

  // The mini strip's rule: the renderer's small cover, then enrichment's
  // (ADR-0012, ADR-0070).
  let failedArtwork = $state(null);
  const artwork = $derived.by(() => {
    if (!active) return null;
    const supplied = metadata?.artwork_small || metadata?.artwork;
    if (supplied && supplied !== failedArtwork) return supplied;
    return $enrichedArtwork && $enrichedArtwork !== failedArtwork ? $enrichedArtwork : null;
  });

  let pressed = $state(false);
  const open = () => active && onopen?.();
</script>

<div
  class="rail"
  class:is-empty={!active}
  class:is-pressed={pressed}
  style:--src-accent={`var(--accent-${active}, var(--accent-lms))`}
  role="button"
  tabindex={active ? 0 : -1}
  aria-label="Open now playing"
  aria-disabled={!active}
  data-rail={active ? 'playing' : 'nothing'}
  onclick={open}
  onkeydown={(e) => e.key === 'Enter' && open()}
  onpointerdown={() => (pressed = !!active)}
  onpointerup={() => (pressed = false)}
  onpointerleave={() => (pressed = false)}
  onpointercancel={() => (pressed = false)}
>
  <div class="progress">
    {#if active && head.hasPosition}
      <div class="progress__fill" style:--pos={`${head.percent.toFixed(2)}%`}></div>
    {/if}
  </div>

  <div class="cover">
    {#if artwork}
      <img src={artwork} alt="" onerror={() => (failedArtwork = artwork)} />
    {:else if !active}
      <div class="cover__slot"></div>
    {/if}
  </div>

  <div class="mark">
    {#if active}<SourceMark source={active} size={26} color="var(--src-accent)" />{/if}
  </div>

  <button
    class="play"
    type="button"
    class:is-inert={!active}
    class:is-gone={active && !hasPlayPause}
    disabled={!active || !hasPlayPause}
    data-shows={toggle.shows}
    aria-label={toggle.shows === 'playing' ? 'Pause' : 'Play'}
    onpointerdown={(e) => e.stopPropagation()}
    onclick={(e) => {
      e.stopPropagation();
      toggle.toggle();
    }}
  >
    {#if active && toggle.shows === 'playing'}
      <span class="i-pause"><i></i><i></i></span>
    {:else}
      <span class="i-play"></span>
    {/if}
  </button>
</div>

<style>
  .rail {
    position: relative;
    width: 124px;
    height: 100%;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 28px 0 26px;
    box-sizing: border-box;
    border-left: 1px solid rgba(233, 238, 242, 0.09);
    background: rgba(13, 21, 28, 0.35);
    user-select: none;
  }
  .rail.is-pressed .cover {
    transform: scale(0.96);
  }

  /* The line sits over the rail's own border, as drawn (left -1). */
  .progress {
    position: absolute;
    left: -1px;
    top: 0;
    bottom: 0;
    width: 3px;
    background: rgba(233, 238, 242, 0.08);
    overflow: hidden;
  }
  /* **Translated, not resized** (Finding 057), as the mini strip's hairline:
     a full-height fill moved down by what is still to play. */
  .progress__fill {
    position: absolute;
    inset: 0;
    background: var(--src-accent);
    opacity: 0.8;
    transform: translateY(calc(100% - var(--pos, 0%)));
    transition: transform 400ms linear;
    will-change: transform;
  }

  .cover {
    position: relative;
    width: 84px;
    height: 84px;
    flex-shrink: 0;
    border-radius: var(--r-md);
    overflow: hidden;
    background: var(--bg-well);
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
    transition: transform 90ms ease;
  }
  .cover img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .cover__slot {
    position: absolute;
    inset: 0;
    border-radius: var(--r-md);
    border: 2px dashed rgba(233, 238, 242, 0.22);
  }

  .mark {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 0;
  }

  .play {
    width: 64px;
    height: 64px;
    flex-shrink: 0;
    border: none;
    padding: 0;
    border-radius: 50%;
    background: var(--play-fill);
    color: var(--bg-panel);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 18px rgba(242, 164, 143, 0.22), 0 8px 20px rgba(242, 164, 143, 0.32);
  }
  .play:not(:disabled):active {
    transform: scale(0.95);
  }
  .play.is-inert {
    opacity: 0.3;
  }
  /* A renderer with no play/pause: removed, as on the mini strip, but its
     room kept so the rail does not change shape under it. */
  .play.is-gone {
    visibility: hidden;
  }
  .i-pause {
    display: flex;
    gap: 6px;
  }
  .i-pause i {
    width: 6px;
    height: 23px;
    border-radius: 2px;
    background: var(--bg-panel);
  }
  .i-play {
    width: 0;
    height: 0;
    border-left: 19px solid var(--bg-panel);
    border-top: 12px solid transparent;
    border-bottom: 12px solid transparent;
    margin-left: 5px;
  }
</style>
