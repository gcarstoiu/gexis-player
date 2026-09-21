<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The mini strip (design/screens.md §2), ported from source/Now Playing.dc.html:
  at the bottom of every screen but now playing, while a renderer is active.
  Tapping it opens now playing; its own play/pause and volume do not.
-->
<script>
  import { enrichedArtwork } from '../lib/enrichment.js';
  import VolumeIcon from '../lib/VolumeIcon.svelte';
  import SourceMark from '../lib/SourceMark.svelte';
  import { playhead, mmss } from '../lib/playhead.svelte.js';
  import { playToggle } from '../lib/playToggle.svelte.js';

  let { active, metadata, volume, controls = [], onopen, onvolume } = $props();

  const LABELS = { lms: 'LMS', spotify: 'Spotify', bluetooth: 'Bluetooth' };

  const transport = $derived(metadata?.transport ?? null);
  const head = playhead(() => metadata);
  const toggle = playToggle(() => transport, () => active);
  const hasPlayPause = $derived(controls.includes('play') && controls.includes('pause'));

  let failedArtwork = $state(null);
  //: What the renderer sent, and only then what enrichment found - the
  //: same rule as now playing (ADR-0012 is additive-only). Bluetooth often
  //: sends no cover at all, and the strip showed nothing while the cover
  //: had already been looked up (George, 2026-09-18).
  const artwork = $derived.by(() => {
    const supplied = metadata?.artwork;
    if (supplied && supplied !== failedArtwork) return supplied;
    return $enrichedArtwork && $enrichedArtwork !== failedArtwork ? $enrichedArtwork : null;
  });

  let pressed = $state(false);
  // The strip's press feedback covers everything but its own buttons.
  const guard = (e) => e.stopPropagation();
  const own = (fn) => (e) => {
    e.stopPropagation();
    fn?.();
  };
</script>

<div
  class="mini"
  class:is-pressed={pressed}
  style:--src-accent={`var(--accent-${active}, var(--accent-lms))`}
  role="button"
  tabindex="0"
  aria-label="Open now playing"
  onclick={onopen}
  onkeydown={(e) => e.key === 'Enter' && onopen?.()}
  onpointerdown={() => (pressed = true)}
  onpointerup={() => (pressed = false)}
  onpointerleave={() => (pressed = false)}
  onpointercancel={() => (pressed = false)}
>
  <div class="hairline" class:is-hidden={!head.hasPosition}>
    <div class="hairline__fill" style:width={`${head.percent.toFixed(2)}%`}></div>
  </div>

  <div class="left">
    <div class="thumb">
      {#if artwork}
        <img src={artwork} alt="" onerror={() => (failedArtwork = artwork)} />
      {/if}
    </div>
    <div class="text">
      <div class="title">{metadata?.title ?? ''}</div>
      <div class="artist">{metadata?.artist ?? ''}</div>
    </div>
  </div>

  <span class="badge">
    <span class="badge__icon" class:is-playing={transport === 'playing'}>
      <SourceMark source={active} size={28} color="var(--src-accent)" />
    </span>
    {LABELS[active] ?? active}
  </span>

  <div class="right">
    <div class="elapsed" class:is-hidden={!head.hasPosition}>{mmss(head.elapsed)}</div>
    <button
      class="vol"
      type="button"
      aria-label="Volume"
      disabled={!volume}
      onpointerdown={guard}
      onclick={own(onvolume)}
    >
      <VolumeIcon percent={volume?.percent ?? null} muted={!!volume?.muted} />
    </button>
    {#if hasPlayPause}
      <button
        class="play"
        type="button"
        data-shows={toggle.shows}
        aria-label={toggle.shows === 'playing' ? 'Pause' : 'Play'}
        onpointerdown={guard}
        onclick={own(toggle.toggle)}
      >
        {#if toggle.shows === 'playing'}
          <span class="i-pause"><i></i><i></i></span>
        {:else}
          <span class="i-play"></span>
        {/if}
      </button>
    {/if}
  </div>
</div>

<style>
  .mini {
    position: relative;
    height: 104px;
    flex-shrink: 0;
    border-top: 1px solid rgba(233, 238, 242, 0.09);
    background: rgba(18, 29, 37, 0.82);
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 20px;
    padding: 0 40px;
    color: var(--ink);
    user-select: none;
    transform-origin: 50% 100%;
    transition: transform 90ms ease;
  }
  /* The design lightens the whole bar on press, which read as a flash on
     the panel (George, 2026-09-17). It shrinks instead, like the buttons -
     from its bottom edge, so the bar stays seated on it. */
  .mini.is-pressed {
    transform: scale(0.995);
  }

  .hairline {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    height: 2px;
    background: rgba(233, 238, 242, 0.08);
  }
  .hairline__fill {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    background: var(--src-accent);
    opacity: 0.6;
    transition: width 400ms linear;
  }
  .is-hidden {
    visibility: hidden;
  }

  .left {
    display: flex;
    align-items: center;
    gap: 20px;
    min-width: 0;
  }
  .thumb {
    width: 64px;
    height: 64px;
    border-radius: 12px;
    overflow: hidden;
    position: relative;
    flex-shrink: 0;
    background: var(--bg-well);
  }
  .thumb img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .text {
    min-width: 0;
  }
  .title,
  .artist {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .title {
    font-size: 20px;
    font-weight: 700;
  }
  .artist {
    font-size: 16px;
    color: var(--accent-artist);
    margin-top: 4px;
  }

  /* Mark and word only. The pill ground, border and padding were removed
     on 2026-09-21, the same change Now Playing's source mark took in 9b -
     the design draws neither as a pill, and two different treatments of one
     renderer on two surfaces is the kind of thing only a diff notices. */
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 13px;
    color: var(--src-accent);
    font-family: var(--font-mono);
    font-size: 21px;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    white-space: nowrap;
    flex-shrink: 0;
  }
  .badge__icon {
    display: flex;
    align-items: center;
  }
  .badge__icon.is-playing {
    animation: pulse 2.4s ease-in-out infinite;
  }
  @keyframes pulse {
    0%,
    100% { opacity: 1; }
    50% { opacity: 0.35; }
  }

  .right {
    display: flex;
    align-items: center;
    gap: 20px;
    justify-self: end;
    flex-shrink: 0;
  }
  .elapsed {
    font-family: var(--font-mono);
    font-size: 16px;
    color: rgba(233, 238, 242, 0.5);
    flex-shrink: 0;
  }

  .vol,
  .play {
    border: none;
    padding: 0;
    color: inherit;
    font: inherit;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    border-radius: 50%;
  }
  .vol {
    width: 56px;
    height: 56px;
    background: var(--ink-fill);
  }
  .vol:active {
    transform: scale(0.95);
  }
  .play {
    width: 64px;
    height: 64px;
    background: var(--play-fill);
    box-shadow: 0 0 18px rgba(242, 164, 143, 0.22), 0 8px 20px rgba(242, 164, 143, 0.32);
  }
  .play:active {
    transform: scale(0.95);
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
