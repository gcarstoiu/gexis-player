<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Now playing, Phase 4 step 4c: display only. Ported from
  design/now-playing.html; the styles are that file's, trimmed to what this
  screen uses. Controls render for the layout but are disabled and carry
  data-unwired="<phase>" until the phase that wires them.
-->
<script>
  import { untrack } from 'svelte';
  import spotifyMark from '../assets/icon-spotify.png';
  import bluetoothMark from '../assets/icon-bluetooth.png';
  import VolumeIcon from '../lib/VolumeIcon.svelte';

  import { sendTransport } from '../lib/state.js';

  let { active, metadata, volume, controls = [], onvolume, onvisualisation } = $props();

  const SOURCES = {
    lms: { label: 'LMS', mark: null },
    spotify: { label: 'Spotify', mark: spotifyMark },
    bluetooth: { label: 'Bluetooth', mark: bluetoothMark },
  };
  const source = $derived(SOURCES[active] ?? { label: active, mark: null });

  const transport = $derived(metadata?.transport ?? null);
  const playing = $derived(transport === 'playing');

  // An artwork URL that fails to load falls back to the pending glyph.
  let failedArtwork = $state(null);
  const artwork = $derived(
    metadata?.artwork && metadata.artwork !== failedArtwork ? metadata.artwork : null,
  );

  // Position is published at a rate that differs by source, so the bar
  // advances locally and re-anchors only when the published values change —
  // every broadcast repeats the last position, including volume-only ones.
  let anchor = $state({ position: null, duration: null, playing: false, at: 0 });
  let now = $state(performance.now());

  $effect(() => {
    const position = metadata?.position ?? null;
    const duration = metadata?.duration ?? null;
    const a = untrack(() => anchor);
    if (position !== a.position || duration !== a.duration || playing !== a.playing) {
      const at = performance.now();
      anchor = { position, duration, playing, at };
      now = at;
    }
  });

  $effect(() => {
    if (!anchor.playing || anchor.position === null) return;
    const id = setInterval(() => (now = performance.now()), 500);
    return () => clearInterval(id);
  });

  const hasPosition = $derived(anchor.position !== null && !!anchor.duration);
  const elapsed = $derived.by(() => {
    if (!hasPosition) return 0;
    const moved = anchor.playing ? (now - anchor.at) / 1000 : 0;
    return Math.min(anchor.position + moved, anchor.duration);
  });
  const percent = $derived(hasPosition ? (elapsed / anchor.duration) * 100 : 0);

  const fmt = (s) => {
    s = Math.max(0, Math.floor(s));
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  };


  // ADR-0037: shown when the renderer has the command, and the icon is
  // whatever the renderer last reported. Pressing sends; it does not flip.
  const hasPlayPause = $derived(controls.includes('play') && controls.includes('pause'));
  async function togglePlay() {
    try {
      await sendTransport(playing ? 'pause' : 'play');
    } catch (err) {
      console.info('transport:', err.message);
    }
  }

  // Shuffle, repeat and queue are LMS-only in the design. Keyed on the id
  // for now; Phase 6 renders controls from capability declarations instead.
  const lmsOnly = $derived(active === 'lms');
</script>

<div
  class="screen"
  style:--src-accent={`var(--accent-${active}, var(--accent-lms))`}
  data-transport={transport ?? 'none'}
  data-artwork={artwork ? 'ok' : 'none'}
  data-position={hasPosition ? 'ok' : 'none'}
>
  <div class="screen__weave"></div>
  {#if artwork}
    <img class="screen__bleed" src={artwork} alt="" />
  {/if}
  <div class="screen__veil"></div>
  <div class="screen__accent"></div>

  <span class="srcpill">
    <span class="srcpill__icon">
      {#if source.mark}
        <img class="srcpill__mark" src={source.mark} alt="" />
      {:else}
        <span class="i-lyrion"><i></i><i></i><i></i><i></i></span>
      {/if}
    </span>
    {source.label}
  </span>

  <div class="screen__body">
    <div class="top">
      <div class="art">
        {#if artwork}
          <img src={artwork} alt="" onerror={() => (failedArtwork = artwork)} />
        {:else}
          <div class="art__empty">
            <div class="art__glyph"></div>
            <span>artwork pending</span>
          </div>
        {/if}
      </div>

      <div class="meta">
        <div class="tabs" role="tablist" aria-label="Track detail" data-unwired="phase-8">
          <button class="tab" type="button" role="tab" aria-selected="true">Track</button>
          <button class="tab" type="button" role="tab" aria-selected="false" aria-disabled="true" disabled>Lyrics</button>
          <button class="tab" type="button" role="tab" aria-selected="false" aria-disabled="true" disabled>Artist</button>
          <button class="tab" type="button" role="tab" aria-selected="false" aria-disabled="true" disabled>Release</button>
        </div>

        <div class="panel">
          <div class="trackblock">
            <div class="title" class:is-empty={!metadata?.title}>{metadata?.title ?? ''}</div>
            <div class="artistline">
              <span class="artist" class:is-empty={!metadata?.artist}>{metadata?.artist ?? ''}</span>
            </div>
            <div class="albumline">
              <span class="album" class:is-empty={!metadata?.album}>{metadata?.album ?? ''}</span>
              <!-- Release year is not published yet (design/data-contract.md). -->
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="spacer"></div>

    <div class="footer">
      <div class="progress">
        <div class="progress__rail">
          <div class="progress__track">
            <div class="progress__fill" style:--pos={`${percent}%`}></div>
          </div>
        </div>
        <div class="progress__times">
          <span>{fmt(elapsed)}</span><span>-{fmt((anchor.duration ?? 0) - elapsed)}</span>
        </div>
      </div>

      <div class="bar">
        <div class="bar__left">
          <button class="btn" type="button" aria-label="Home" disabled data-unwired="phase-7">
            <span class="i-tiles"><i></i><i></i><i></i><i></i></span>
          </button>
          <button class="btn" type="button" aria-label="Visualization" onclick={onvisualisation}>
            <span class="i-meter">
              <i style="height:12px"></i><i style="height:22px"></i><i style="height:16px"></i><i style="height:8px"></i>
            </span>
          </button>
        </div>

        <div class="bar__mid">
          {#if lmsOnly}
            <button class="btn" type="button" aria-label="Shuffle" disabled data-unwired="phase-6">
              <span class="i-shuffle"><i></i><i></i><i></i><i></i><b></b><b></b></span>
            </button>
          {/if}
          <button class="btn btn--lg" type="button" aria-label="Previous" disabled data-unwired="phase-6">
            <span class="i-prev"></span>
          </button>
          {#if hasPlayPause}
            <button class="btn btn--play" type="button" aria-label={playing ? 'Pause' : 'Play'} onclick={togglePlay}>
              <span class="i-play"></span><span class="i-pause"></span>
            </button>
          {/if}
          <button class="btn btn--lg" type="button" aria-label="Next" disabled data-unwired="phase-6">
            <span class="i-next"></span>
          </button>
          {#if lmsOnly}
            <button class="btn" type="button" aria-label="Repeat" disabled data-unwired="phase-6">
              <span class="i-repeat"><i></i><i></i><i></i><i></i><b></b><b></b></span>
            </button>
          {/if}
        </div>

        <div class="bar__right">
          <button class="btn" type="button" aria-label="Volume" disabled={!volume} onclick={onvolume}>
            <VolumeIcon percent={volume?.percent ?? null} muted={!!volume?.muted} />
          </button>
          {#if lmsOnly}
            <button class="btn btn--queue" type="button" aria-label="Queue" disabled data-unwired="phase-7">
              <i></i><i></i><i></i>
            </button>
          {/if}
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  .screen {
    position: relative;
    width: 1280px;
    height: 800px;
    overflow: hidden;
    background: var(--bg-base);
    user-select: none;
  }

  .screen__weave,
  .screen__veil {
    position: absolute;
    pointer-events: none;
  }
  .screen__weave {
    inset: -90px;
    background: repeating-linear-gradient(38deg, var(--bg-weave-a) 0 48px, var(--bg-weave-b) 48px 96px);
    filter: blur(70px);
    transform: scale(1.14);
  }
  .screen__bleed {
    position: absolute;
    inset: -120px;
    width: calc(100% + 240px);
    height: calc(100% + 240px);
    object-fit: cover;
    filter: blur(72px) saturate(1.7);
    transform: scale(1.12);
    pointer-events: none;
  }
  .screen__veil {
    inset: 0;
    background: radial-gradient(130% 105% at 20% 42%, rgba(22, 36, 46, 0.3), rgba(14, 23, 30, 0.86));
  }

  .screen__accent {
    position: absolute;
    inset: 0 0 auto 0;
    height: 3px;
    background: linear-gradient(90deg, var(--src-accent), var(--accent-artist));
  }

  .srcpill {
    position: absolute;
    top: 38px;
    right: 56px;
    z-index: 6;
    display: inline-flex;
    align-items: center;
    gap: 9px;
    padding: 8px 15px;
    border-radius: var(--r-pill);
    white-space: nowrap;
    font-size: var(--t-label);
    font-weight: 700;
    letter-spacing: var(--track-label);
    text-transform: uppercase;
    color: var(--src-accent);
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid color-mix(in oklab, var(--src-accent) 40%, transparent);
  }
  .srcpill__icon {
    display: flex;
    align-items: center;
  }
  .screen[data-transport='playing'] .srcpill__icon {
    animation: pulse 2.4s ease-in-out infinite;
  }
  @keyframes pulse {
    0%,
    100% { opacity: 1; }
    50% { opacity: 0.35; }
  }
  .srcpill__mark {
    width: 18px;
    height: 18px;
    flex-shrink: 0;
    display: block;
    object-fit: contain;
  }

  /* Four-bar reduction of the Lyrion mark; the SVG smears below ~40px. */
  .i-lyrion {
    display: flex;
    align-items: center;
    gap: 2px;
    height: 17px;
    flex-shrink: 0;
  }
  .i-lyrion i {
    width: 3px;
    border-radius: 2px;
    background: currentColor;
    flex-shrink: 0;
  }
  .i-lyrion i:nth-child(1) { height: 9px; }
  .i-lyrion i:nth-child(2) { height: 17px; }
  .i-lyrion i:nth-child(3) { height: 12px; }
  .i-lyrion i:nth-child(4) { height: 15px; }

  .screen__body {
    position: absolute;
    inset: 0;
    display: grid;
    grid-template-rows: var(--art) 1fr auto;
    padding: var(--pad-screen);
  }

  .top {
    display: grid;
    grid-template-columns: var(--art) minmax(0, 1fr);
    gap: 48px;
    min-height: 0;
  }

  .art {
    position: relative;
    width: var(--art);
    height: var(--art);
    border-radius: var(--r-card);
    overflow: hidden;
    background: var(--bg-well);
    box-shadow: 0 28px 64px rgba(0, 0, 0, 0.5);
  }
  .art img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
  .art::after {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: var(--r-card);
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
    pointer-events: none;
  }

  .art__empty {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 20px;
    background: linear-gradient(160deg, rgba(126, 214, 188, 0.07), rgba(242, 164, 143, 0.06));
  }
  .art__glyph {
    width: 110px;
    height: 110px;
    border-radius: var(--r-circle);
    border: 2px solid color-mix(in oklab, var(--accent-lms) 40%, transparent);
    display: grid;
    place-items: center;
  }
  .art__glyph::before {
    content: '';
    width: 26px;
    height: 26px;
    border-radius: var(--r-circle);
    background: color-mix(in oklab, var(--accent-lms) 45%, transparent);
  }
  .art__empty span {
    font-family: var(--font-mono);
    font-size: var(--t-label);
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }

  .meta {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .tabs {
    display: flex;
    align-items: center;
    gap: 26px;
    align-self: flex-start;
    flex-shrink: 0;
    margin-bottom: 18px;
    border-bottom: 1px solid rgba(233, 238, 242, 0.12);
  }
  .tab {
    font-family: var(--font-mono);
    font-size: var(--t-label);
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    white-space: nowrap;
    color: var(--ink-quiet);
    min-height: var(--touch-min);
    padding: 16px 2px 9px;
    margin-top: -16px;
    border: 0;
    border-bottom: 3px solid transparent;
    background: none;
  }
  .tab[aria-selected='true'] {
    color: var(--ink);
    border-bottom-color: var(--src-accent);
  }
  .tab[aria-disabled='true'] { opacity: 0.4; }

  .panel {
    margin-top: 36px;
    flex: 1;
    min-height: 0;
    position: relative;
  }

  .trackblock { min-height: 238px; }

  .title {
    font-size: var(--t-title);
    line-height: 1.06;
    font-weight: 700;
    letter-spacing: var(--track-tight);
    text-wrap: pretty;
    margin: 0;
    min-height: 124px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .artistline {
    margin-top: 16px;
    min-height: 38px;
  }
  .artist {
    font-size: var(--t-artist);
    line-height: 1.3;
    font-weight: 600;
    color: var(--accent-artist);
    display: inline-block;
    max-width: 100%;
    padding: 7px 0;
    margin: -7px 0;
    vertical-align: top;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .albumline {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-top: 8px;
    min-height: 26px;
  }
  .album {
    font-size: var(--t-body);
    line-height: 1.35;
    color: rgba(233, 238, 242, 0.6);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .is-empty { visibility: hidden; }

  .spacer { min-height: 0; }
  .footer { flex-shrink: 0; }

  .progress__rail {
    position: relative;
    height: 12px;
  }
  .progress__track {
    position: absolute;
    inset: 0;
    border-radius: var(--r-pill);
    background: rgba(233, 238, 242, 0.13);
    overflow: hidden;
  }
  .progress__fill {
    position: absolute;
    inset: 0 auto 0 0;
    width: var(--pos, 0%);
    border-radius: var(--r-pill);
    background: var(--src-accent);
    transition: width 400ms linear;
  }
  .progress__times {
    display: flex;
    justify-content: space-between;
    margin-top: 13px;
    font-family: var(--font-mono);
    font-size: 16px;
    letter-spacing: 0.04em;
    color: rgba(233, 238, 242, 0.62);
  }

  /* No position (Bluetooth): a separator faded at both ends, times hidden,
     so it never reads as a bar stuck at zero. */
  .screen[data-position='none'] .progress__fill { display: none; }
  .screen[data-position='none'] .progress__track {
    background: linear-gradient(
      90deg,
      rgba(233, 238, 242, 0),
      rgba(233, 238, 242, 0.15) 16%,
      rgba(233, 238, 242, 0.15) 84%,
      rgba(233, 238, 242, 0)
    );
  }
  .screen[data-position='none'] .progress__times { visibility: hidden; }

  .bar {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    margin-top: 26px;
  }
  .bar__left { justify-self: start; display: flex; align-items: center; gap: 14px; }
  .bar__mid { justify-self: center; display: flex; align-items: center; gap: 22px; }
  .bar__right { justify-self: end; display: flex; align-items: center; gap: 20px; }

  .btn {
    width: var(--ctl);
    height: var(--ctl);
    border: 0;
    padding: 0;
    border-radius: var(--r-circle);
    background: var(--ink-fill);
    color: var(--ink);
    display: grid;
    place-items: center;
    flex-shrink: 0;
  }
  .btn:not(:disabled):active {
    background: var(--ink-fill-press);
  }
  .btn--lg {
    width: var(--ctl-lg);
    height: var(--ctl-lg);
    background: rgba(233, 238, 242, 0.09);
  }
  .btn--play {
    width: var(--ctl-play);
    height: var(--ctl-play);
    background: var(--play-fill);
    color: var(--ink-on-accent);
    box-shadow: 0 0 22px rgba(242, 164, 143, 0.22), 0 12px 30px rgba(242, 164, 143, 0.35);
  }
  /* The design presses play by shrinking it, not by the other buttons' grey
     fill - which on this one read as a flash (George, 2026-09-16). */
  .btn--play:not(:disabled):active {
    background: var(--play-fill);
    transform: scale(0.95);
  }

  .i-play {
    width: 0;
    height: 0;
    border-left: 30px solid currentColor;
    border-top: 19px solid transparent;
    border-bottom: 19px solid transparent;
    margin-left: 8px;
  }
  .i-pause {
    width: 26px;
    height: 34px;
    background: linear-gradient(to right, currentColor 0 8px, transparent 8px 18px, currentColor 18px 26px);
  }
  .screen[data-transport='playing'] .i-play,
  .screen:not([data-transport='playing']) .i-pause { display: none; }

  .i-prev,
  .i-next { display: flex; align-items: center; }
  .i-prev::before { content: ''; width: 3px; height: 19px; background: currentColor; border-radius: 2px; }
  .i-prev::after {
    content: '';
    width: 0;
    height: 0;
    border-right: 13px solid currentColor;
    border-top: 10px solid transparent;
    border-bottom: 10px solid transparent;
    margin-left: 3px;
  }
  .i-next::before {
    content: '';
    width: 0;
    height: 0;
    border-left: 13px solid currentColor;
    border-top: 10px solid transparent;
    border-bottom: 10px solid transparent;
    margin-right: 3px;
  }
  .i-next::after { content: ''; width: 3px; height: 19px; background: currentColor; border-radius: 2px; }

  .i-tiles {
    width: 22px;
    height: 22px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 3.5px;
  }
  .i-tiles i { border-radius: 3px; background: var(--ink-strong); }
  .i-meter { display: flex; align-items: flex-end; gap: 4px; height: 22px; }
  .i-meter i { width: 4px; border-radius: 2px; background: var(--ink-body); }

  .i-shuffle { position: relative; width: 32px; height: 28px; display: block; }
  .i-shuffle i,
  .i-shuffle b { position: absolute; display: block; background: var(--ink-body); }
  .i-shuffle i:nth-child(1) { left: 0.5px; top: 13.5px; width: 17px; height: 3px; border-radius: 2px; transform: rotate(-54.5deg); }
  .i-shuffle i:nth-child(2) { left: 0.5px; top: 13.5px; width: 17px; height: 3px; border-radius: 2px; transform: rotate(54.5deg); }
  .i-shuffle i:nth-child(3) { left: 13px; top: 6.5px; width: 11px; height: 3px; }
  .i-shuffle i:nth-child(4) { left: 13px; top: 20.5px; width: 11px; height: 3px; }
  .i-shuffle b {
    background: none;
    width: 0;
    height: 0;
    border-left: 8px solid var(--ink-body);
    border-top: 5px solid transparent;
    border-bottom: 5px solid transparent;
  }
  .i-shuffle b:nth-child(5) { left: 24px; top: 3px; }
  .i-shuffle b:nth-child(6) { left: 24px; top: 17px; }

  .i-repeat { position: relative; width: 26px; height: 26px; display: block; }
  .i-repeat i,
  .i-repeat b { position: absolute; display: block; }
  .i-repeat i { background: var(--ink-body); border-radius: 1px; }
  .i-repeat i:nth-child(1) { left: 3px; top: 3px; width: 15px; height: 3px; }
  .i-repeat i:nth-child(2) { left: 3px; top: 3px; width: 3px; height: 14px; }
  .i-repeat i:nth-child(3) { left: 20px; top: 9px; width: 3px; height: 14px; }
  .i-repeat i:nth-child(4) { left: 8px; top: 20px; width: 15px; height: 3px; }
  .i-repeat b { width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; }
  .i-repeat b:nth-child(5) { left: 17.5px; top: 2px; border-top: 7px solid var(--ink-body); }
  .i-repeat b:nth-child(6) { left: 0.5px; top: 17px; border-bottom: 7px solid var(--ink-body); }

  .btn--queue {
    background: rgba(159, 180, 232, 0.12);
    border: 1px solid rgba(159, 180, 232, 0.3);
    flex-direction: column;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    position: relative;
  }
  .btn--queue i { width: 26px; height: 3px; border-radius: 2px; background: var(--accent-bluetooth); }
  .btn--queue i:last-of-type { width: 15px; }
</style>
