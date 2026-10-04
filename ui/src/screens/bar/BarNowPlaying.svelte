<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Now playing on a bar (ADR-0109, Bar family): one strip, 400 logical px
  tall and as wide as the screen (1200-2000). From Claude Design's round 2,
  `design/source/13b/Bar Frame.dc.html` (variant strip, sr main, pull down)
  and `Bar States.dc.html` (strip-*, lyr-*), where round 2 wins over round 1.

  Behaviour is now playing's (NowPlaying.svelte) wherever George's answers to
  the round-2 review say the bar matches the panel
  (design/briefs/13b-round2-review.md §1):
  - **5: progress as the panel shows it**, Bluetooth included - a bar with a
    position fills; without one it is the panel's faded separator and the
    times are hidden, never a bar stuck at zero.
  - **6: lyrics match the panel**: the switch is always there, and the words
    have the panel's Lyrics-tab states - looking, instrumental, synced,
    plain, none, and the error with Retry.
  - **8: a plugin with no mark** shows its initial in a ring (SourceMark).

  What a bar drops is dropped by design (ADR-0109 decision 7): the Artist and
  Release tabs. Home, the visualiser and the volume live in the pull-down
  tray (BarTray.svelte), which App.svelte mounts over every screen.
-->
<script>
  import SourceMark from '../../lib/SourceMark.svelte';
  import QueueRail from '../QueueRail.svelte';
  import { retryEnrichment, trackEnrichment } from '../../lib/enrichment.js';
  import { sendTransport } from '../../lib/state.js';
  import { playhead, mmss } from '../../lib/playhead.svelte.js';
  import { playToggle } from '../../lib/playToggle.svelte.js';
  import { parseSynced, sungOf, activeAt, anchorOf } from '../../lib/lyrics.js';
  import { pull, bandDrag, TRAY_H } from './tray.svelte.js';

  // The props App.svelte gives NowPlaying, so the two are interchangeable.
  // `onhome` and `onvisualisation` are the tray's on a bar; they are accepted
  // here so App can pass one set to either screen.
  let { active, metadata, volume, controls = [], available = [], shuffle = null, repeat = null, queue = null, onvolume, onvisualisation, onhome, onartist, rootless = false } = $props();
  const artistLinked = $derived(!!onartist);

  const transport = $derived(metadata?.transport ?? null);
  const enrichment = $derived($trackEnrichment);
  const info = $derived(enrichment.enrichment);

  // Artwork as the panel takes it: the renderer's, then enrichment's (ADR-0012,
  // additive only), and a URL that fails falls back to the placeholder.
  let failedArtwork = $state(null);
  const artwork = $derived.by(() => {
    const supplied = metadata?.artwork;
    if (supplied && supplied !== failedArtwork) return supplied;
    const found = info?.album_art;
    return found && found !== failedArtwork ? found : null;
  });

  const head = playhead(() => metadata);
  const toggle = playToggle(() => transport, () => active);
  const hasPlayPause = $derived(controls.includes('play') && controls.includes('pause'));
  //: **Removed, not disabled, when it cannot work** (design: *unsupported
  //: controls are removed*; round 2: Bluetooth has no shuffle or repeat).
  //: Gated on what the renderer says is available, never on its name - a
  //: Bluetooth phone that reports shuffle gets the button. The panel keeps a
  //: declared control and dims it (ADR-0037 §3); on a bar the transport is
  //: the one row of controls, and a dimmed button there is room taken by
  //: something that does nothing.
  const can = (what) => controls.includes(what) && available.includes(what);
  const NEXT_REPEAT = { off: 'all', all: 'one', one: 'off' };
  async function skip(command, body) {
    try {
      await sendTransport(command, body);
    } catch (err) {
      console.info('transport:', err.message);
    }
  }

  const year = $derived(metadata?.year ?? info?.released ?? null);

  // The queue is LMS's alone, as on the panel.
  const lmsOnly = $derived(active === 'lms');
  const upNext = $derived(Math.max(0, (queue?.items?.length ?? 0) - (queue?.index ?? 0) - 1));
  let queueOpen = $state(false);
  $effect(() => {
    if (!lmsOnly) queueOpen = false;
  });

  // ---- lyrics: the panel's Lyrics tab, drawn the bar's way ----------------
  //: The switch replaces the title block with the words; it stays on across
  //: tracks, like a tab the panel leaves open.
  let lyricsOn = $state(false);
  const synced = $derived(parseSynced(info?.lyrics_synced));
  const sung = $derived(sungOf(synced));
  const activeLine = $derived(synced.length ? activeAt(synced, head.elapsed) : -1);
  const anchor = $derived(anchorOf(sung, activeLine));
  const singing = $derived(anchor >= 0 && sung[anchor]?.src === activeLine);
  //: Three fixed slots - the line before, the one sung, the one after - so a
  //: line at either end of the song leaves its slot empty rather than moving
  //: the others up.
  const slots = $derived(
    sung.length ? [anchor - 1, anchor, anchor + 1].map((n) => ({ n, text: sung[n]?.text ?? '' })) : [],
  );
  const plainLines = $derived((info?.lyrics ?? '').split('\n'));
  //: The panel's order of precedence (NowPlaying.svelte, Lyrics tab).
  const lyricsState = $derived(
    enrichment.state === 'loading' ? 'loading'
      : info?.instrumental ? 'instrumental'
      : sung.length ? 'synced'
      : info?.lyrics ? 'plain'
      : enrichment.state === 'error' ? 'error'
      : 'none',
  );

  // ---- the pull-down band ---------------------------------------------------
  //: **The control under the finger wins.** Round 2 left two overlaps open
  //: (13b-round2-review.md §2): the 44px band runs across the strip's top
  //: edge and the lyrics switch starts 32px down, so their top 12px overlap.
  //: The switch sits above the band (z-index), so a touch on it is the
  //: switch's; the band only takes touches outside controls. The same rule
  //: settles the tray's slider against its close band (BarTray.svelte).
  const band = bandDrag(1, {
    onmove: (travel) => (pull.offset = travel),
    onend: ({ tap, travel, cancelled }) => {
      pull.offset = null;
      if (cancelled) return;
      // A tap opens it as well as a drag past a third of the way.
      if (tap || travel > TRAY_H * 0.35) onvolume?.();
    },
  });
</script>

<div
  class="strip"
  style:--src-accent={`var(--accent-${active}, var(--accent-lms))`}
  data-source={active ?? 'lms'}
  data-transport={transport ?? 'none'}
  data-artwork={artwork ? 'ok' : 'none'}
  data-position={head.hasPosition ? 'ok' : 'none'}
  data-lyrics={lyricsOn ? lyricsState : 'off'}
>
  <div class="strip__veil"></div>
  <div class="strip__accent"></div>

  <div class="strip__body">
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

    <div class="main">
      <div class="head">
        <div class="meta">
          {#if !lyricsOn}
            <div class="title" class:is-empty={!metadata?.title}>{metadata?.title ?? ''}</div>
            <div class="metaline">
              {#if artistLinked}
                <button class="artist artist--link" class:is-empty={!metadata?.artist} type="button"
                  disabled={!metadata?.artist} onclick={() => onartist(metadata.artist)}
                >{metadata?.artist ?? ''}</button>
              {:else}
                <span class="artist" class:is-empty={!metadata?.artist}>{metadata?.artist ?? ''}</span>
              {/if}
              <span class="album" class:is-empty={!metadata?.album}>{metadata?.album ?? ''}</span>
              {#if year}<span class="year">{year}</span>{/if}
            </div>
          {:else}
            <!-- Title and artist on one line; the review found the design's
                 title here had no ellipsis, so both carry one. -->
            <div class="lyrhead">
              <span class="lyrhead__title">{metadata?.title ?? ''}</span>
              <span class="lyrhead__artist">{metadata?.artist ?? ''}</span>
            </div>
            {#if lyricsState === 'loading'}
              <div class="skel"><span></span><span></span><span></span></div>
            {:else if lyricsState === 'instrumental'}
              <div class="lyrnote">Instrumental</div>
            {:else if lyricsState === 'synced'}
              <div class="synced">
                {#each slots as slot (slot.n)}
                  <div class="synced__line" class:is-now={slot.n === anchor && singing} class:is-near={slot.n !== anchor}>{slot.text}</div>
                {/each}
              </div>
              <div class="credit">From {info.lyrics_source}</div>
            {:else if lyricsState === 'plain'}
              <!-- Static - no line is lit, because nothing says which is
                   sung - and scrollable, as the panel's tab is: a song is
                   longer than four lines. -->
              <div class="plain">
                {#each plainLines as line, i (i)}<div class="plain__line">{line}</div>{/each}
              </div>
              <div class="credit">From {info.lyrics_source}</div>
            {:else if lyricsState === 'error'}
              <div class="offline">
                <span>Lyrics unavailable. Your library is unaffected.</span>
                <button class="offline__retry" type="button" onclick={retryEnrichment}>Retry</button>
              </div>
            {:else}
              <div class="lyrnote">No lyrics found for this track.</div>
            {/if}
          {/if}
        </div>

        <span class="mark"><SourceMark source={active} size={30} color="var(--src-accent)" /></span>

        <button class="lyrswitch" class:is-on={lyricsOn} type="button" aria-label="Lyrics" aria-pressed={lyricsOn}
          onclick={() => (lyricsOn = !lyricsOn)}>
          <i></i><i></i><i></i>
        </button>
      </div>

      <div class="progress">
        <span class="progress__time">{mmss(head.elapsed)}</span>
        <div class="progress__track">
          <div class="progress__fill" style:--pos={`${head.percent}%`}></div>
        </div>
        <span class="progress__time">-{mmss((head.duration ?? 0) - head.elapsed)}</span>
      </div>

      <div class="transport">
        <div></div>
        <div class="transport__mid">
          {#if can('shuffle')}
            <button class="btn btn--toggle" class:is-on={shuffle === true} type="button" aria-label="Shuffle" aria-pressed={shuffle === true}
              onclick={() => skip('shuffle', { on: shuffle !== true })}>
              <span class="i-shuffle"><i></i><i></i><i></i><i></i><b></b><b></b></span>
            </button>
          {/if}
          {#if can('previous')}
            <button class="btn btn--lg" type="button" aria-label="Previous" onclick={() => skip('previous')}><span class="i-prev"></span></button>
          {/if}
          {#if hasPlayPause}
            <button class="btn btn--play" type="button" data-shows={toggle.shows} aria-label={toggle.shows === 'playing' ? 'Pause' : 'Play'} onclick={toggle.toggle}>
              <span class="i-play"></span><span class="i-pause"></span>
            </button>
          {/if}
          {#if can('next')}
            <button class="btn btn--lg" type="button" aria-label="Next" onclick={() => skip('next')}><span class="i-next"></span></button>
          {/if}
          {#if can('repeat')}
            <button class="btn btn--toggle" class:is-on={repeat === 'all' || repeat === 'one'} type="button" aria-label={`Repeat ${repeat ?? 'off'}`}
              onclick={() => skip('repeat', { mode: NEXT_REPEAT[repeat ?? 'off'] })}>
              <span class="i-repeat"><i></i><i></i><i></i><i></i><b></b><b></b>{#if repeat === 'one'}<span class="i-repeat__one">1</span>{/if}</span>
            </button>
          {/if}
        </div>
        <div class="transport__right">
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

  <!-- The tray's handle and the 44px band that pulls it: drag down, or tap. -->
  <div class="pullband" role="button" tabindex="-1" aria-label="Controls"
    onpointerdown={band.down} onpointermove={band.move} onpointerup={band.up} onpointercancel={band.cancel}></div>
  <div class="handle"></div>

  {#if lmsOnly}
    <QueueRail open={queueOpen} {queue} onclose={() => (queueOpen = false)} />
  {/if}
</div>

<style>
  .strip {
    position: relative;
    width: 100%;
    height: var(--panel-h);
    overflow: hidden;
    user-select: none;
  }
  .strip__veil {
    position: absolute;
    pointer-events: none;
    inset: 0;
    background: radial-gradient(130% 105% at 20% 42%, rgba(22, 36, 46, 0.3), rgba(14, 23, 30, 0.86));
  }
  /* A solid rule in the source's accent on a bar (Bar Frame, Bar States). */
  .strip__accent {
    position: absolute;
    inset: 0 0 auto 0;
    height: 3px;
    z-index: 3;
    background: var(--src-accent);
  }

  .strip__body {
    position: absolute;
    inset: 0;
    display: flex;
    gap: 36px;
    padding: 32px 40px;
  }

  .art {
    position: relative;
    width: 336px;
    height: 336px;
    flex-shrink: 0;
    border-radius: 20px;
    overflow: hidden;
    background: var(--bg-well);
    box-shadow: 0 20px 48px rgba(0, 0, 0, 0.5);
  }
  .art img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
  .art::after {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 20px;
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
    pointer-events: none;
  }
  /* The panel's placeholder at the strip's size (Bar States, strip-pending). */
  .art__empty {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 18px;
    background: linear-gradient(160deg, rgba(126, 214, 188, 0.07), rgba(242, 164, 143, 0.06));
  }
  .art__glyph {
    width: 96px;
    height: 96px;
    border-radius: var(--r-circle);
    border: 2px solid color-mix(in oklab, var(--accent-lms) 40%, transparent);
    display: grid;
    place-items: center;
  }
  .art__glyph::before {
    content: '';
    width: 24px;
    height: 24px;
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

  .main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .head {
    display: flex;
    align-items: flex-start;
    gap: 20px;
    min-height: 0;
  }
  .meta {
    flex: 1;
    min-width: 0;
  }

  .title {
    font-size: 42px;
    line-height: 1.06;
    font-weight: 700;
    letter-spacing: var(--track-tight);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  /* Artist at most 62% of the line, the album the rest, the year kept
     (round 2, *Strip*). **Larger than the design, the year straight after
     the album** (George, 2026-10-04, on the bars: "increase the size of
     artist, album and year. Track title should stay the same ... the year
     ... should just come after the album, not at the end of the line"). */
  .metaline {
    display: flex;
    align-items: baseline;
    gap: 14px;
    margin-top: 12px;
    min-width: 0;
  }
  .artist {
    font-size: 36px;
    font-weight: 600;
    color: var(--accent-artist);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex-shrink: 1;
    min-width: 0;
    max-width: 62%;
  }
  /* The panel's link: 44px tall to the finger, no taller to the eye. */
  .artist--link {
    font: inherit;
    font-size: 36px;
    font-weight: 600;
    border: none;
    background: none;
    padding: 6px 0;
    margin: -6px 0;
    text-align: left;
  }
  .artist--link:active:not(:disabled) { color: #f8c4b4; }
  .album {
    font-size: 32px;
    color: rgba(233, 238, 242, 0.6);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex: 0 1 auto;
    min-width: 0;
  }
  .year {
    font-family: var(--font-mono);
    font-size: 28px;
    color: var(--ink-quiet);
    white-space: nowrap;
    flex-shrink: 0;
  }
  .is-empty { visibility: hidden; }

  /* ---- lyrics ---- */
  .lyrhead {
    display: flex;
    align-items: baseline;
    gap: 12px;
    min-width: 0;
  }
  .lyrhead__title {
    font-size: 24px;
    font-weight: 700;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex-shrink: 1;
    min-width: 0;
  }
  .lyrhead__artist {
    font-size: 20px;
    font-weight: 600;
    color: var(--accent-artist);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex-shrink: 1;
    min-width: 0;
    max-width: 62%;
  }
  .synced {
    margin-top: 10px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .synced__line {
    font-size: 26px;
    line-height: 1.3;
    min-height: 1.3em;
    font-weight: 500;
    color: rgba(233, 238, 242, 0.85);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: color 320ms ease, opacity 320ms ease;
  }
  .synced__line.is-near { opacity: 0.42; }
  .synced__line.is-now {
    font-weight: 700;
    color: var(--accent-artist);
  }
  .plain {
    margin-top: 10px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    height: 104px;
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-width: none;
    touch-action: pan-y;
    -webkit-mask-image: linear-gradient(180deg, #000 70%, transparent 100%);
    mask-image: linear-gradient(180deg, #000 70%, transparent 100%);
  }
  .plain::-webkit-scrollbar { display: none; }
  /* A 26px pitch: what the design shows, where its four lines are squeezed
     into the 104px box (its lines shrink as flex items; these do not). */
  .plain__line {
    font-size: 22px;
    line-height: 24px;
    min-height: 24px;
    color: rgba(233, 238, 242, 0.85);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex-shrink: 0;
  }
  .credit {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.1em;
    color: var(--ink-quiet);
    margin-top: 8px;
  }
  .skel {
    margin-top: 16px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .skel span {
    display: block;
    height: 18px;
    border-radius: 5px;
    background: rgba(233, 238, 242, 0.1);
    animation: barSkel 1500ms ease-in-out infinite;
  }
  .skel span:nth-child(1) { width: 62%; }
  .skel span:nth-child(2) { width: 80%; animation-delay: 150ms; }
  .skel span:nth-child(3) { width: 48%; animation-delay: 300ms; }
  @keyframes barSkel {
    50% { opacity: 0.45; }
  }
  .lyrnote {
    margin-top: 14px;
    font-size: 22px;
    color: var(--ink-quiet);
  }
  /* The panel's error row, with Retry at the bar's 44px floor. */
  .offline {
    margin-top: 14px;
    max-width: 760px;
    display: flex;
    align-items: center;
    gap: 14px;
    min-height: 60px;
    border-radius: 14px;
    background: rgba(233, 238, 242, 0.05);
    border: 1px solid rgba(233, 238, 242, 0.12);
    padding: 0 8px 0 18px;
  }
  .offline span {
    flex: 1;
    min-width: 0;
    font-size: 18px;
    color: var(--ink-muted);
  }
  .offline__retry {
    display: inline-flex;
    align-items: center;
    height: 44px;
    padding: 0 18px;
    border-radius: 10px;
    background: rgba(159, 180, 232, 0.16);
    border: 1px solid rgba(159, 180, 232, 0.35);
    font-family: var(--font-mono);
    font-size: var(--t-label);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent-bluetooth);
    flex-shrink: 0;
  }
  .offline__retry:active { background: rgba(159, 180, 232, 0.3); }

  .mark {
    height: 30px;
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }

  /* Three bars; on, the artist coral (Bar Frame's lyrBg / lyrLine / lyrInk).
     Above the pull band: see `band` in the script. */
  .lyrswitch {
    position: relative;
    z-index: 5;
    width: 60px;
    height: 60px;
    flex-shrink: 0;
    border-radius: 50%;
    padding: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 5px;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.12);
    --lyr-ink: rgba(233, 238, 242, 0.66);
  }
  .lyrswitch.is-on {
    background: rgba(242, 164, 143, 0.16);
    border-color: rgba(242, 164, 143, 0.45);
    --lyr-ink: var(--accent-artist);
  }
  .lyrswitch:active { transform: scale(0.95); }
  .lyrswitch i {
    display: block;
    width: 24px;
    height: 3px;
    border-radius: 2px;
    background: var(--lyr-ink);
  }
  .lyrswitch i:nth-child(2) { width: 18px; }

  /* ---- progress: the panel's, laid out the bar's way ---- */
  .progress {
    margin-top: auto;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .progress__time {
    font-family: var(--font-mono);
    font-size: 16px;
    letter-spacing: 0.04em;
    color: rgba(233, 238, 242, 0.62);
    flex-shrink: 0;
  }
  .progress__track {
    flex: 1;
    position: relative;
    height: 10px;
    border-radius: var(--r-pill);
    background: rgba(233, 238, 242, 0.13);
    overflow: hidden;
  }
  /* Translated, not resized (Finding 057), as on the panel. */
  .progress__fill {
    position: absolute;
    inset: 0;
    border-radius: var(--r-pill);
    background: var(--src-accent);
    transform: translateX(calc(var(--pos, 0%) - 100%));
    transition: transform 400ms linear;
    will-change: transform;
  }
  /* No position: the panel's faded separator, times hidden but holding
     their room, so it never reads as a bar stuck at zero. */
  .strip[data-position='none'] .progress__fill { display: none; }
  .strip[data-position='none'] .progress__track {
    background: linear-gradient(
      90deg,
      rgba(233, 238, 242, 0),
      rgba(233, 238, 242, 0.15) 16%,
      rgba(233, 238, 242, 0.15) 84%,
      rgba(233, 238, 242, 0)
    );
  }
  .strip[data-position='none'] .progress__time { visibility: hidden; }

  /* ---- transport ---- */
  .transport {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    margin-top: 22px;
  }
  .transport__mid { display: flex; align-items: center; gap: 22px; }
  .transport__right { justify-self: end; display: flex; align-items: center; }

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
  .btn:active { transform: scale(0.95); }
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
  .i-shuffle { position: relative; width: 32px; height: 28px; display: block; }
  .i-shuffle i,
  .i-shuffle b { position: absolute; display: block; background: var(--toggle-ink); }
  .i-shuffle i:nth-child(1) { left: 0.5px; top: 13.5px; width: 17px; height: 3px; border-radius: 2px; transform: rotate(-54.5deg); }
  .i-shuffle i:nth-child(2) { left: 0.5px; top: 13.5px; width: 17px; height: 3px; border-radius: 2px; transform: rotate(54.5deg); }
  .i-shuffle i:nth-child(3) { left: 13px; top: 6.5px; width: 11px; height: 3px; }
  .i-shuffle i:nth-child(4) { left: 13px; top: 20.5px; width: 11px; height: 3px; }
  .i-shuffle b {
    background: none;
    width: 0;
    height: 0;
    border-left: 8px solid var(--toggle-ink);
    border-top: 5px solid transparent;
    border-bottom: 5px solid transparent;
  }
  .i-shuffle b:nth-child(5) { left: 24px; top: 3px; }
  .i-shuffle b:nth-child(6) { left: 24px; top: 17px; }

  .i-repeat { position: relative; width: 26px; height: 26px; display: block; }
  .i-repeat i,
  .i-repeat b { position: absolute; display: block; }
  .i-repeat i { background: var(--toggle-ink); border-radius: 1px; }
  .i-repeat i:nth-child(1) { left: 3px; top: 3px; width: 15px; height: 3px; }
  .i-repeat i:nth-child(2) { left: 3px; top: 3px; width: 3px; height: 14px; }
  .i-repeat i:nth-child(3) { left: 20px; top: 9px; width: 3px; height: 14px; }
  .i-repeat i:nth-child(4) { left: 8px; top: 20px; width: 15px; height: 3px; }
  .i-repeat b { width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; }
  .i-repeat b:nth-child(5) { left: 17.5px; top: 2px; border-top: 7px solid var(--toggle-ink); }
  .i-repeat b:nth-child(6) { left: 0.5px; top: 17px; border-bottom: 7px solid var(--toggle-ink); }
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

  .btn--queue {
    background: rgba(159, 180, 232, 0.12);
    border: 1px solid rgba(159, 180, 232, 0.3);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 5px;
    position: relative;
  }
  .btn--queue i { width: 26px; height: 3px; border-radius: 2px; background: var(--accent-bluetooth); }
  .btn--queue i:last-of-type { width: 15px; }
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
  }

  /* ---- the pull band ---- */
  .pullband {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    height: 44px;
    z-index: 4;
    touch-action: none;
  }
  .handle {
    position: absolute;
    left: 50%;
    top: 12px;
    width: 88px;
    height: 6px;
    margin-left: -44px;
    border-radius: 3px;
    background: rgba(233, 238, 242, 0.42);
    z-index: 4;
    pointer-events: none;
  }
</style>
