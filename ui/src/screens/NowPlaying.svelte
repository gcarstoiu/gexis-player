<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Now playing, Phase 4 step 4c: display only. Ported from
  design/now-playing.html; the styles are that file's, trimmed to what this
  screen uses. Controls render for the layout but are disabled and carry
  data-unwired="<phase>" until the phase that wires them.
-->
<script>
  import spotifyMark from '../assets/icon-spotify.png';
  import bluetoothMark from '../assets/icon-bluetooth.png';
  import { untrack } from 'svelte';

  import VolumeIcon from '../lib/VolumeIcon.svelte';
  import QueueRail from './QueueRail.svelte';

  import { sendTransport } from '../lib/state.js';
  import { playhead, mmss } from '../lib/playhead.svelte.js';
  import { playToggle } from '../lib/playToggle.svelte.js';

  let { active, metadata, volume, controls = [], available = [], shuffle = null, repeat = null, queue = null, onvolume, onvisualisation, onhome } = $props();

  const SOURCES = {
    lms: { label: 'LMS', mark: null },
    spotify: { label: 'Spotify', mark: spotifyMark },
    bluetooth: { label: 'Bluetooth', mark: bluetoothMark },
  };
  const source = $derived(SOURCES[active] ?? { label: active, mark: null });

  const transport = $derived(metadata?.transport ?? null);

  // An artwork URL that fails to load falls back to the pending glyph.
  let failedArtwork = $state(null);
  const artwork = $derived(
    metadata?.artwork && metadata.artwork !== failedArtwork ? metadata.artwork : null,
  );

  const head = playhead(() => metadata);

  // ADR-0037: shown when the renderer has the command.
  const hasPlayPause = $derived(controls.includes('play') && controls.includes('pause'));

  // The icon flips on press; see playToggle.svelte.js.
  const toggle = playToggle(() => transport, () => active);

  // Shuffle and repeat show what the renderer reports (LMS answers in about
  // 0.5 s, Finding 028), so unlike play they do not flip on press. Repeat
  // steps off -> all -> one, the design's order.
  const NEXT_REPEAT = { off: 'all', all: 'one', one: 'off' };

  async function skip(command, body) {
    try {
      await sendTransport(command, body);
    } catch (err) {
      console.info('transport:', err.message);
    }
  }

  // The queue is LMS-only in the design; shuffle and repeat follow the
  // renderer's declaration (ADR-0037).
  const lmsOnly = $derived(active === 'lms');

  // The badge counts what is still to come, not the track playing now -
  // the rail's own "Up next" (the design's `queueCount`).
  const upNext = $derived(Math.max(0, (queue?.items?.length ?? 0) - (queue?.index ?? 0) - 1));

  // The Artist tab (ADR-0040). Fetched when the tab is opened, never on the
  // screen's path: a biography took 386-1005 ms from LMS's own plugin and
  // seconds through MusicBrainz (Findings 035, 036), and now playing must
  // render without it (ADR-0012).
  let tab = $state('track');
  let artistInfo = $state({ state: 'idle', for: null, enrichment: null });

  const initialsOf = (name) =>
    (name ?? '')
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((word) => word[0].toUpperCase())
      .join('') || '?';

  async function loadArtistInfo(force = false) {
    const who = metadata?.artist ?? '';
    if (!who) return;
    if (!force && artistInfo.for === who && artistInfo.state !== 'error') return;
    artistInfo = { state: 'loading', for: who, enrichment: null };
    try {
      const response = await fetch('/enrichment');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const body = await response.json();
      // By the time a lookup returns the track may have changed; the reply
      // says which artist it is about, so a late answer is dropped rather
      // than shown against the wrong name.
      if ((metadata?.artist ?? '') !== who) return;
      artistInfo = { state: 'ready', for: who, enrichment: body.enrichment };
    } catch (err) {
      console.info('enrichment:', err.message);
      artistInfo = { state: 'error', for: who, enrichment: null };
    }
  }

  $effect(() => {
    const who = metadata?.artist ?? '';
    if (tab === 'artist' && who) untrack(() => loadArtistInfo());
  });

  let queueOpen = $state(false);
  // Leaving LMS takes the rail's subject with it.
  $effect(() => {
    if (!lmsOnly) queueOpen = false;
  });
</script>

<div
  class="screen"
  style:--src-accent={`var(--accent-${active}, var(--accent-lms))`}
  data-transport={transport ?? 'none'}
  data-artwork={artwork ? 'ok' : 'none'}
  data-position={head.hasPosition ? 'ok' : 'none'}
>
  <!-- The weave and the artwork's bleed are drawn once for the whole panel
       (PanelBackground.svelte); this screen keeps only its own veil. -->
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
        <div class="tabs" role="tablist" aria-label="Track detail">
          <button class="tab" type="button" role="tab" aria-selected={tab === 'track'} onclick={() => (tab = 'track')}>Track</button>
          <button class="tab" type="button" role="tab" aria-selected="false" aria-disabled="true" disabled data-unwired="phase-8">Lyrics</button>
          <button class="tab" type="button" role="tab" aria-selected={tab === 'artist'} onclick={() => (tab = 'artist')}>Artist</button>
          <button class="tab" type="button" role="tab" aria-selected="false" aria-disabled="true" disabled data-unwired="phase-8">Release</button>
        </div>

        <div class="panel">
          {#if tab === 'track'}
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
          {:else}
            <div class="artisttab">
              <div class="artisttab__head">
                <span class="artisttab__disc">
                  {#if artistInfo.enrichment?.artist_image}
                    <img src={artistInfo.enrichment.artist_image} alt="" />
                  {:else}
                    <span class="artisttab__initials">{initialsOf(metadata?.artist)}</span>
                  {/if}
                </span>
                <span class="artisttab__name">{metadata?.artist ?? ''}</span>
              </div>

              <div class="sect">
                <span class="sect__label">About</span>
                <span class="sect__rule"></span>
                {#if artistInfo.state === 'loading'}<span class="sect__note">Looking…</span>{/if}
              </div>

              {#if artistInfo.state === 'loading'}
                <!-- The design's skeleton: the layout must not jump when the
                     text arrives, so the space is held. -->
                <div class="skel"><span></span><span></span><span></span></div>
              {:else if artistInfo.enrichment?.biography}
                <div class="bio">{artistInfo.enrichment.biography}</div>
                <!-- Wikipedia's CC BY-SA and MusicBrainz's CC BY-NC-SA both
                     require the credit beside the text (ADR-0040 §4). -->
                <div class="credit">From {artistInfo.enrichment.biography_source}</div>
              {:else if artistInfo.state === 'error'}
                <div class="offline">
                  <span>Artist details unavailable. Your library is unaffected.</span>
                  <button class="offline__retry" type="button" onclick={() => loadArtistInfo(true)}>Retry</button>
                </div>
              {:else}
                <div class="sect__empty">Nothing found for this artist.</div>
              {/if}

              {#if artistInfo.enrichment?.similar?.length}
                <div class="sect">
                  <span class="sect__label">Similar artists</span>
                  <span class="sect__rule"></span>
                </div>
                <div class="similar">
                  {#each artistInfo.enrichment.similar as name (name)}
                    <span class="similar__chip">{name}</span>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}
        </div>
      </div>
    </div>

    <div class="spacer"></div>

    <div class="footer">
      <div class="progress">
        <div class="progress__rail">
          <div class="progress__track">
            <div class="progress__fill" style:--pos={`${head.percent}%`}></div>
          </div>
        </div>
        <div class="progress__times">
          <span>{mmss(head.elapsed)}</span><span>-{mmss((head.duration ?? 0) - head.elapsed)}</span>
        </div>
      </div>

      <div class="bar">
        <div class="bar__left">
          <button class="btn" type="button" aria-label="Home" onclick={onhome}>
            <span class="i-tiles"><i></i><i></i><i></i><i></i></span>
          </button>
          <button class="btn" type="button" aria-label="Visualization" onclick={onvisualisation}>
            <span class="i-meter">
              <i style="height:12px"></i><i style="height:22px"></i><i style="height:16px"></i><i style="height:8px"></i>
            </span>
          </button>
        </div>

        <div class="bar__mid">
          {#if controls.includes('shuffle')}
            <button class="btn btn--toggle" class:is-on={shuffle === true} type="button" aria-label="Shuffle" aria-pressed={shuffle === true} disabled={!available.includes('shuffle')} onclick={() => skip('shuffle', { on: shuffle !== true })}>
              <span class="i-shuffle"><i></i><i></i><i></i><i></i><b></b><b></b></span>
            </button>
          {/if}
          {#if controls.includes('previous')}
            <!-- ADR-0037 §3: has it but cannot work now - shown, disabled. -->
            <button class="btn btn--lg" type="button" aria-label="Previous" disabled={!available.includes('previous')} onclick={() => skip('previous')}>
              <span class="i-prev"></span>
            </button>
          {/if}
          {#if hasPlayPause}
            <button class="btn btn--play" type="button" data-shows={toggle.shows} aria-label={toggle.shows === 'playing' ? 'Pause' : 'Play'} onclick={toggle.toggle}>
              <span class="i-play"></span><span class="i-pause"></span>
            </button>
          {/if}
          {#if controls.includes('next')}
            <button class="btn btn--lg" type="button" aria-label="Next" disabled={!available.includes('next')} onclick={() => skip('next')}>
              <span class="i-next"></span>
            </button>
          {/if}
          {#if controls.includes('repeat')}
            <button class="btn btn--toggle" class:is-on={repeat === 'all' || repeat === 'one'} type="button" aria-label={`Repeat ${repeat ?? 'off'}`} disabled={!available.includes('repeat')} onclick={() => skip('repeat', { mode: NEXT_REPEAT[repeat ?? 'off'] })}>
              <span class="i-repeat"><i></i><i></i><i></i><i></i><b></b><b></b>{#if repeat === 'one'}<span class="i-repeat__one">1</span>{/if}</span>
            </button>
          {/if}
        </div>

        <div class="bar__right">
          <button class="btn" type="button" aria-label="Volume" disabled={!volume} onclick={onvolume}>
            <VolumeIcon percent={volume?.percent ?? null} muted={!!volume?.muted} />
          </button>
          {#if lmsOnly}
            <button class="btn btn--queue" type="button" aria-label="Queue" onclick={() => (queueOpen = true)}>
              <i></i><i></i><i></i>
              {#if upNext}<span class="btn__badge">{upNext}</span>{/if}
            </button>
          {/if}
        </div>
      </div>
    </div>
  </div>

  {#if lmsOnly}
    <QueueRail open={queueOpen} {queue} onclose={() => (queueOpen = false)} />
  {/if}
</div>

<style>
  .screen {
    position: relative;
    width: 1280px;
    height: 800px;
    overflow: hidden;
    user-select: none;
  }

  .screen__veil {
    position: absolute;
    pointer-events: none;
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

  /* The Artist tab (ADR-0040), ported from the design's About and Similar
     blocks. It occupies the same box as the track block, so switching tabs
     moves nothing else on the screen. */
  .artisttab {
    min-height: 238px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .artisttab__head {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-shrink: 0;
  }
  .artisttab__disc {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    overflow: hidden;
    position: relative;
    flex-shrink: 0;
    background: var(--ink-fill);
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.14);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .artisttab__disc img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .artisttab__initials {
    font-family: var(--font-mono);
    font-size: 22px;
    font-weight: 700;
    color: var(--ink-muted);
  }
  .artisttab__name {
    font-size: var(--t-artist);
    font-weight: 700;
    color: var(--accent-artist);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .sect {
    display: flex;
    align-items: baseline;
    gap: 12px;
    flex-shrink: 0;
  }
  .sect__label {
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .sect__rule {
    flex: 1;
    height: 1px;
    background: var(--ink-line);
  }
  .sect__note {
    font-family: var(--font-mono);
    font-size: var(--t-micro);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--ink-quiet);
    flex-shrink: 0;
  }
  .sect__empty {
    font-size: var(--t-body-sm);
    color: var(--ink-quiet);
  }

  .skel {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .skel span {
    display: block;
    height: 13px;
    border-radius: 4px;
    background: rgba(233, 238, 242, 0.09);
    animation: npSkel 1500ms ease-in-out infinite;
  }
  .skel span:nth-child(1) { width: 100%; }
  .skel span:nth-child(2) { width: 96%; animation-delay: 90ms; }
  .skel span:nth-child(3) { width: 58%; animation-delay: 180ms; }
  @keyframes npSkel {
    0%, 100% { opacity: 0.55; }
    50% { opacity: 1; }
  }

  .bio {
    max-height: 128px;
    overflow-y: auto;
    font-size: 17px;
    line-height: 1.5;
    color: var(--ink-body);
    text-wrap: pretty;
    scrollbar-width: none;
    touch-action: pan-y;
  }
  .bio::-webkit-scrollbar { display: none; }

  .credit {
    font-family: var(--font-mono);
    font-size: var(--t-micro);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }

  .offline {
    display: flex;
    align-items: center;
    gap: 14px;
    height: 52px;
    border-radius: 14px;
    background: rgba(233, 238, 242, 0.05);
    border: 1px solid rgba(233, 238, 242, 0.12);
    padding: 0 18px;
  }
  .offline span {
    flex: 1;
    min-width: 0;
    font-size: 16px;
    color: var(--ink-muted);
  }
  .offline__retry {
    display: inline-flex;
    align-items: center;
    height: 36px;
    padding: 0 15px;
    border-radius: 9px;
    background: rgba(159, 180, 232, 0.16);
    border: 1px solid rgba(159, 180, 232, 0.35);
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent-bluetooth);
    flex-shrink: 0;
  }
  .offline__retry:active { background: rgba(159, 180, 232, 0.3); }

  .similar {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .similar__chip {
    display: inline-flex;
    align-items: center;
    height: 30px;
    padding: 0 12px;
    border-radius: 9px;
    background: rgba(159, 180, 232, 0.14);
    border: 1px solid rgba(159, 180, 232, 0.3);
    font-size: 15px;
    color: var(--accent-bluetooth);
    white-space: nowrap;
  }

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
  /* Pressed by shrinking, like play and the transport buttons (George,
     2026-09-16/17: the design's grey press fill reads as a flash). */
  .btn:not(:disabled):active {
    transform: scale(0.95);
  }
  /* Cannot work right now (ADR-0037 §3). The design dims an unavailable tab
     to 0.4; the same here. Unwired scaffolding keeps its own look. */
  .btn:disabled:not([data-unwired]) {
    opacity: 0.4;
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
  .btn--play[data-shows='playing'] .i-play,
  .btn--play:not([data-shows='playing']) .i-pause { display: none; }

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

  /* Shuffle and repeat, off and on - the design's values. */
  .btn--toggle {
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.12);
    --toggle-ink: rgba(233, 238, 242, 0.66);
  }
  .btn--toggle.is-on {
    background: rgba(126, 214, 188, 0.16);
    border-color: rgba(126, 214, 188, 0.42);
    --toggle-ink: #7ed6bc;
  }
  /* Pressed by shrinking, like play (George, 2026-09-17: the design's grey
     press fill read as a flash here too). The fill stays what the state is. */
  .btn--toggle:not(:disabled):active,
  .btn--lg:not(:disabled):active {
    transform: scale(0.95);
  }
  .btn--toggle:not(:disabled):active { background: rgba(233, 238, 242, 0.07); }
  .btn--toggle.is-on:not(:disabled):active { background: rgba(126, 214, 188, 0.16); }
  .btn--lg:not(:disabled):active { background: rgba(233, 238, 242, 0.09); }
  .btn--toggle .i-shuffle i,
  .btn--toggle .i-repeat i { background: var(--toggle-ink); }
  .btn--toggle .i-shuffle b { border-left-color: var(--toggle-ink); }
  .btn--toggle .i-repeat b:nth-child(5) { border-top-color: var(--toggle-ink); }
  .btn--toggle .i-repeat b:nth-child(6) { border-bottom-color: var(--toggle-ink); }
  .i-repeat__one {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 700;
    line-height: 1;
    color: var(--toggle-ink);
  }

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
  .btn__badge {
    position: absolute;
    top: -3px;
    right: -3px;
    min-width: 24px;
    height: 24px;
    padding: 0 6px;
    border-radius: 999px;
    background: var(--accent-bluetooth);
    color: var(--ink-on-accent);
    font-family: var(--font-mono);
    font-size: var(--t-label);
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
  }
  .btn--queue i { width: 26px; height: 3px; border-radius: 2px; background: var(--accent-bluetooth); }
  .btn--queue i:last-of-type { width: 15px; }
</style>
