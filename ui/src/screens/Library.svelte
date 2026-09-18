<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The library (ADR-0038), Phase 7 step 4: the root. Ported from
  source/Now Playing.dc.html, where the library is a layer over now playing:
  the root's five cards and the New Music strip, the header with Back and Home
  below the root, the mini strip while a renderer is active, and the waiting
  services while none is (ADR-0033: Home is the no-renderer screen).

  Screens below the root arrive in later steps; until then their cards carry
  data-unwired="phase-7" and do nothing.

  Mounted only while open, and animated in and out by Svelte rather than
  left in the page at opacity 0: on the panel, the closed layer with its
  blurred backdrop kept covering now playing in black (George, 2026-09-17),
  while the idle screen, which is removed when it closes, never did.
-->
<script>
  import { libraryRoot, loadAlbum, libraryAction } from '../lib/library.js';
  import MiniStrip from './MiniStrip.svelte';
  import WaitingServices from './WaitingServices.svelte';

  let {
    active,
    metadata,
    volume,
    controls = [],
    availability = {},
    onclose,
    onsettings,
    onvolume,
  } = $props();

  // Where in the library the panel is; [] is the root. Each entry is a
  // screen below it: `{ kind: 'album', id, label }` today.
  let path = $state([]);
  let album = $state(null);
  let busy = $state(null);

  async function openAlbum(id, label) {
    busy = id;
    try {
      // Fetched and decoded before the screen changes, so the album page
      // arrives whole rather than filling in (George, 2026-09-17).
      album = await loadAlbum(id);
      path = [{ kind: 'album', id, label }];
    } catch (err) {
      console.info('library:', err.message);
    } finally {
      busy = null;
    }
  }

  async function play(kind, id) {
    try {
      await libraryAction(kind, id, 'play');
    } catch (err) {
      // LMS unreachable, or a rescan took the id away: the panel stays put
      // rather than pretending something started.
      console.info('library:', err.message);
    }
  }

  // Loaded once when the panel starts, covers and all (lib/library.js), so
  // opening Home draws the cards and the strip together.
  const counts = $derived($libraryRoot.counts);
  const albums = $derived($libraryRoot.albums);

  let failed = $state(new Set());
  const markFailed = (url) => (failed = new Set(failed).add(url));

  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

  const here = $derived(path.length ? path[path.length - 1] : null);
  const title = $derived(here ? (album?.title ?? here.label) : 'Library');
  // The design puts the album's artist where a deeper path would put its
  // parents.
  const crumb = $derived(
    here?.kind === 'album' ? (album?.artist ?? '') : path.slice(0, -1).map((p) => p.label).join('  /  '),
  );

  function back() {
    if (!path.length) {
      onclose?.();
      return;
    }
    path = path.slice(0, -1);
    if (!path.length) album = null;
  }

  const mmss = (s) => {
    const whole = Math.max(0, Math.round(s ?? 0));
    return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`;
  };

  // The New Music strip fades whichever edge has more to scroll to. Which
  // edge that is comes from two sentinels watched by an IntersectionObserver,
  // not from a scroll handler: reading scrollLeft/scrollWidth as the strip
  // moves forces the browser to lay it out again on every frame, and the
  // strip scrolled unevenly on the panel (George, 2026-09-17). Nothing in
  // this component now runs per scroll frame.
  let fadeL = $state(false);
  let fadeR = $state(false);
  let scroller = $state(null);
  let startMark = $state(null);
  let endMark = $state(null);

  $effect(() => {
    const root = scroller;
    const marks = [startMark, endMark].filter(Boolean);
    if (!root || marks.length !== 2) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.target === startMark) fadeL = !entry.isIntersecting;
          else fadeR = !entry.isIntersecting;
        }
      },
      { root, threshold: 0.99 },
    );
    for (const mark of marks) observer.observe(mark);
    return () => observer.disconnect();
  });

  const mask = $derived(
    'linear-gradient(90deg,' +
      (fadeL ? 'transparent 0,rgba(0,0,0,0.35) 22px,#000 88px,' : '#000 0,') +
      (fadeR ? '#000 calc(100% - 88px),rgba(0,0,0,0.35) calc(100% - 22px),transparent 100%)' : '#000 100%)'),
  );

</script>

<!-- The design animates this in over 260ms (opacity 220ms, transform 10px).
     Not animated at all here: on the panel every version of it blinked, since
     the screens are transparent over a shared backdrop (App.svelte). -->
<div class="library">
  <!-- Weave and bleed are the panel's, drawn once (PanelBackground.svelte). -->
  <div class="veil"></div>

  {#if path.length}
    <div class="header">
      {#if path.length > 1}
        <button class="round" type="button" aria-label="Home" onclick={() => (path = [])}>
          <span class="i-tiles"><i></i><i></i><i></i><i></i></span>
        </button>
      {/if}
      <button class="round" type="button" aria-label="Back" onclick={back}>
        <span class="i-back"></span>
      </button>
      <div class="heading">
        <span class="heading__title">{title}</span>
        <span class="heading__crumb">{crumb}</span>
      </div>
    </div>
  {/if}

  <div class="content">
    {#if path.length === 0}
      <div class="root">
        <div class="cards">
          <button class="card card--browse" type="button" disabled data-unwired="phase-7">
            <span class="glyph glyph--bars"><i style="height:26px"></i><i style="height:44px"></i><i style="height:32px"></i><i style="height:39px"></i></span>
            <span>
              <span class="card__name">Browse</span>
              <span class="card__count">{counts ? plural(counts.albums, 'album', 'albums') : ''}</span>
            </span>
          </button>

          <button class="card card--artists" type="button" disabled data-unwired="phase-7">
            <span class="glyph glyph--dots"><i></i><i></i><i></i></span>
            <span>
              <span class="card__name">Artists</span>
              <span class="card__count">{counts ? plural(counts.artists, 'artist', 'artists') : ''}</span>
            </span>
          </button>

          <button class="card card--playlists" type="button" disabled data-unwired="phase-7">
            <span class="glyph glyph--list">
              <span><i></i><b style="width:44px"></b></span>
              <span><i></i><b style="width:32px"></b></span>
              <span><i></i><b style="width:38px"></b></span>
            </span>
            <span>
              <span class="card__name">Playlists</span>
              <span class="card__count">{counts ? plural(counts.playlists, 'playlist', 'playlists') : ''}</span>
            </span>
          </button>

          <button class="card card--radio" type="button" disabled data-unwired="phase-7">
            <span class="glyph glyph--waves"><i></i><b></b><b></b></span>
            <span>
              <span class="card__name">Radio</span>
              <!-- The design's station count has no source in the radio tree
                   (ADR-0038); a missing field is not drawn. -->
              <span class="card__count"></span>
            </span>
          </button>

          <button class="card card--settings" type="button" onclick={onsettings}>
            <span class="glyph glyph--sliders"><i></i><b></b><i></i><b></b></span>
            <span>
              <span class="card__name">Settings</span>
              <span class="card__count">Device and sources</span>
            </span>
          </button>
        </div>

        <div class="new">
          <div class="new__head">
            <span class="new__label">New Music</span>
            <span class="new__rule"></span>
          </div>
          <!-- The mask sits on this wrapper, which does not scroll: on the
               scroller itself it is re-applied to the moving content. -->
          <div class="new__mask" style:mask-image={mask} style:-webkit-mask-image={mask}>
          <div class="new__scroll" bind:this={scroller}>
            <span class="mark" bind:this={startMark}></span>
            {#each albums as tile (tile.id)}
              <button
                class="album"
                class:is-busy={busy === tile.id}
                type="button"
                onclick={() => openAlbum(tile.id, tile.title)}
              >
                <span class="album__art">
                  {#if tile.artwork && !failed.has(tile.artwork)}
                    <img src={tile.artwork} alt="" onerror={() => markFailed(tile.artwork)} />
                  {/if}
                </span>
                <span class="album__title">{tile.title ?? ''}</span>
                <span class="album__artist">{tile.artist ?? ''}</span>
              </button>
            {/each}
            <span class="mark" bind:this={endMark}></span>
          </div>
          </div>
        </div>
      </div>
    {:else if here?.kind === 'album' && album}
      <div class="albumpage">
        <div class="albumpage__side">
          <div class="albumpage__art">
            {#if album.artwork && !failed.has(album.artwork)}
              <img src={album.artwork} alt="" onerror={() => markFailed(album.artwork)} />
            {/if}
          </div>
          <div>
            <div class="albumpage__title">{album.title ?? ''}</div>
            <div class="albumpage__meta">
              {[album.artist, album.year].filter(Boolean).join('  \u00b7  ')}
            </div>
          </div>
          <button class="playall" type="button" onclick={() => play('album', album.id)}>
            <span class="playall__glyph"></span>
            <span class="playall__label">Play album</span>
          </button>
        </div>

        <div class="tracks">
          <div class="tracks__head">
            <span class="tracks__label">Tracks</span>
            <span class="tracks__count">{album.tracks.length}</span>
          </div>
          <div class="tracks__list">
            <!-- Row actions (play now, add to queue, add to playlist) are
                 step 7; a row is display-only until then. -->
            {#each album.tracks as track (track.id)}
              <div class="track">
                <span class="track__num">{track.tracknum ?? ''}</span>
                <span class="track__title">{track.title ?? ''}</span>
                <span class="track__time">{track.duration ? mmss(track.duration) : ''}</span>
              </div>
            {/each}
          </div>
        </div>
      </div>
    {/if}
  </div>

  {#if active}
    <div class="strip">
      <MiniStrip {active} {metadata} {volume} {controls} onopen={onclose} {onvolume} />
    </div>
  {:else}
    <WaitingServices {availability} />
  {/if}
</div>

<style>
  .library {
    position: absolute;
    inset: 0;
    z-index: 10;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    color: var(--ink);
    user-select: none;
  }

  .veil {
    position: absolute;
    inset: 0;
    background: radial-gradient(130% 105% at 20% 42%, rgba(20, 33, 42, 0.62), rgba(13, 21, 28, 0.93));
  }

  button {
    font: inherit;
    color: inherit;
    border: none;
    padding: 0;
    text-align: left;
  }

  .header {
    position: relative;
    height: var(--header-h);
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 0 40px;
    border-bottom: 1px solid rgba(233, 238, 242, 0.09);
  }
  .round {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: var(--ink-fill);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  /* Shrinks rather than filling grey - see now playing's buttons. */
  .round:active {
    transform: scale(0.95);
  }
  .i-tiles {
    width: 22px;
    height: 22px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 3.5px;
  }
  .i-tiles i {
    border-radius: 2px;
    background: var(--ink-strong);
  }
  .i-back {
    width: 14px;
    height: 14px;
    border-left: 3px solid var(--ink);
    border-bottom: 3px solid var(--ink);
    transform: rotate(45deg);
    margin-left: 11px;
  }
  .heading {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: baseline;
    gap: 12px;
  }
  .heading__title,
  .heading__crumb {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .heading__title {
    font-size: var(--t-h3);
    font-weight: 700;
    letter-spacing: -0.01em;
  }
  .heading__crumb {
    font-family: var(--font-mono);
    font-size: var(--t-meta);
    letter-spacing: 0.08em;
    color: var(--ink-quiet);
  }

  .content {
    position: relative;
    flex: 1;
    min-height: 0;
    display: flex;
  }

  .root {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 30px;
    box-sizing: border-box;
    position: relative;
    padding: 30px 60px;
  }
  .cards {
    display: grid;
    gap: 26px;
    flex-shrink: 0;
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
  .card {
    --card: 233, 238, 242;
    border-radius: var(--r-card);
    background: rgba(var(--card), 0.1);
    border: 1px solid rgba(var(--card), 0.3);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 26px 24px;
    box-sizing: border-box;
    height: 200px;
  }
  .card:not(:disabled):active {
    background: rgba(var(--card), 0.24);
  }
  .card--browse { --card: 126, 214, 188; }
  .card--artists { --card: 159, 180, 232; }
  .card--playlists { --card: 242, 164, 143; }
  .card--radio {
    background: rgba(233, 238, 242, 0.055);
    border-color: rgba(233, 238, 242, 0.16);
  }
  .card--settings {
    background: rgba(233, 238, 242, 0.04);
    border-color: rgba(233, 238, 242, 0.12);
  }
  .card--settings:active {
    background: rgba(233, 238, 242, 0.16);
  }
  .card__name {
    display: block;
    font-size: var(--t-h2);
    font-weight: 700;
    letter-spacing: var(--track-tight);
    color: var(--ink);
  }
  .card__count {
    display: block;
    min-height: 1.3em;
    font-family: var(--font-mono);
    font-size: 14px;
    letter-spacing: 0.06em;
    margin-top: 8px;
    white-space: nowrap;
  }
  .card--browse .card__count { color: rgba(126, 214, 188, 0.85); }
  .card--artists .card__count { color: rgba(159, 180, 232, 0.9); }
  .card--playlists .card__count { color: rgba(242, 164, 143, 0.9); }
  .card--radio .card__count { color: var(--ink-muted); }
  .card--settings .card__count { color: var(--ink-quiet); }

  .glyph {
    height: 44px;
    display: flex;
  }
  .glyph--bars {
    align-items: flex-end;
    gap: 7px;
  }
  .glyph--bars i {
    width: 8px;
    border-radius: 3px;
    background: var(--accent-lms);
  }
  .glyph--dots {
    align-items: center;
  }
  .glyph--dots i {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    flex-shrink: 0;
    background: rgba(159, 180, 232, 0.95);
  }
  .glyph--dots i:nth-child(2) {
    background: rgba(159, 180, 232, 0.6);
    margin-left: -11px;
  }
  .glyph--dots i:nth-child(3) {
    background: rgba(159, 180, 232, 0.32);
    margin-left: -11px;
  }
  .glyph--list {
    flex-direction: column;
    justify-content: center;
    gap: 6px;
  }
  .glyph--list > span {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .glyph--list i {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent-artist);
  }
  .glyph--list b {
    height: 4px;
    border-radius: 2px;
    background: var(--accent-artist);
  }
  .glyph--list > span:nth-child(2) i,
  .glyph--list > span:nth-child(2) b {
    background: rgba(242, 164, 143, 0.7);
  }
  .glyph--list > span:nth-child(3) i,
  .glyph--list > span:nth-child(3) b {
    background: rgba(242, 164, 143, 0.45);
  }
  .glyph--waves {
    align-items: center;
    gap: 7px;
  }
  .glyph--waves i {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: rgba(233, 238, 242, 0.85);
    flex-shrink: 0;
  }
  .glyph--waves b {
    width: 14px;
    height: 26px;
    border-right: 3px solid rgba(233, 238, 242, 0.6);
    border-radius: 0 26px 26px 0;
    flex-shrink: 0;
    box-sizing: content-box;
  }
  .glyph--waves b:last-child {
    height: 38px;
    border-right-color: rgba(233, 238, 242, 0.34);
    border-radius: 0 38px 38px 0;
    margin-left: -2px;
  }
  /* The design centres a 30px square in the 44px glyph row: 7px down. */
  .glyph--sliders {
    display: block;
    position: relative;
    width: 30px;
  }
  .glyph--sliders b {
    position: absolute;
    left: 0;
    right: 0;
    height: 3px;
    border-radius: 2px;
    background: rgba(233, 238, 242, 0.38);
  }
  .glyph--sliders b:nth-of-type(1) { top: 14px; }
  .glyph--sliders b:nth-of-type(2) { top: 27px; }
  .glyph--sliders i {
    position: absolute;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: rgba(233, 238, 242, 0.92);
    z-index: 1;
  }
  .glyph--sliders i:nth-of-type(1) { left: 17px; top: 11px; }
  .glyph--sliders i:nth-of-type(2) { left: 4px; top: 24px; }

  .new {
    flex-shrink: 0;
    min-width: 0;
  }
  .new__head {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 15px;
  }
  .new__label {
    font-family: var(--font-mono);
    font-size: var(--t-label);
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: rgba(233, 238, 242, 0.62);
  }
  .new__rule {
    flex: 1;
    height: 1px;
    background: rgba(233, 238, 242, 0.12);
  }
  .new__mask {
    /* Its own layer, so the mask is rasterised once rather than with every
       frame of the scroll underneath it. */
    will-change: transform;
  }
  .new__scroll {
    display: flex;
    gap: 20px;
    overflow-x: auto;
    padding: 0 30px 4px;
    margin: 0 -30px;
    scrollbar-width: none;
    /* Keep the strip's painting to itself, and let the compositor scroll it
       without waiting on anything else on the screen. */
    contain: content;
    touch-action: pan-x;
    overscroll-behavior-x: contain;
  }
  /* 1px sentinels at each end: visible means that end is reached, which is
     what decides the fade (see the observer above). */
  .mark {
    flex: 0 0 1px;
    align-self: stretch;
  }
  .new__scroll::-webkit-scrollbar {
    display: none;
  }
  .album {
    width: 176px;
    flex-shrink: 0;
    background: none;
    display: block;
  }
  .album__art {
    display: block;
    width: 176px;
    height: 176px;
    border-radius: 14px;
    overflow: hidden;
    position: relative;
    background: var(--bg-well);
    border: 1px solid var(--ink-line);
    box-sizing: border-box;
  }
  .album__art img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .album__title,
  .album__artist {
    display: block;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .album__title {
    font-size: var(--t-body-sm);
    font-weight: 600;
    color: var(--ink);
    margin-top: 11px;
  }
  .album__artist {
    font-size: var(--t-meta);
    /* The design's 0.55 is under its own 4.5:1 floor for 15px text
       (tokens.css); --ink-quiet is that floor. */
    color: var(--ink-quiet);
    margin-top: 3px;
  }

  .album.is-busy {
    opacity: 0.6;
  }

  /* The album page, ported from the design's own block. */
  .albumpage {
    flex: 1;
    min-width: 0;
    display: flex;
    min-height: 0;
    gap: 34px;
    padding: 26px 40px 30px;
    box-sizing: border-box;
  }
  .albumpage__side {
    width: 264px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }
  .albumpage__art {
    width: 264px;
    height: 264px;
    border-radius: var(--r-lg);
    overflow: hidden;
    position: relative;
    background: var(--bg-well);
    border: 1px solid var(--ink-line);
    flex-shrink: 0;
  }
  .albumpage__art img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .albumpage__title {
    font-size: 24px;
    font-weight: 700;
    color: var(--ink);
    line-height: 1.2;
    text-wrap: pretty;
  }
  .albumpage__meta {
    font-family: var(--font-mono);
    font-size: var(--t-meta);
    color: rgba(233, 238, 242, 0.62);
    margin-top: 8px;
  }
  .playall {
    height: 58px;
    border-radius: var(--r-lg);
    background: rgba(126, 214, 188, 0.14);
    border: 1px solid rgba(126, 214, 188, 0.36);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 14px;
    flex-shrink: 0;
  }
  .playall:active {
    transform: scale(0.97);
  }
  .playall__glyph {
    width: 0;
    height: 0;
    border-left: 14px solid var(--accent-lms);
    border-top: 9px solid transparent;
    border-bottom: 9px solid transparent;
    flex-shrink: 0;
  }
  .playall__label {
    font-size: var(--t-body);
    font-weight: 700;
    color: var(--ink);
  }

  .tracks {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .tracks__head {
    height: 36px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 10px;
    border-bottom: 1px solid rgba(233, 238, 242, 0.08);
    margin-bottom: 8px;
  }
  .tracks__label,
  .tracks__count {
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
  }
  .tracks__label {
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: rgba(233, 238, 242, 0.5);
  }
  .tracks__count {
    color: rgba(233, 238, 242, 0.62);
    margin-left: auto;
  }
  .tracks__list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 2px;
    scrollbar-width: none;
    /* As on the New Music strip: keep the list's painting to itself and
       nothing per scroll frame (Finding 032). */
    contain: content;
    touch-action: pan-y;
  }
  .tracks__list::-webkit-scrollbar {
    display: none;
  }
  .track {
    height: 52px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 0 16px;
    border-radius: 10px;
  }
  .track__num {
    font-family: var(--font-mono);
    font-size: var(--t-meta);
    color: rgba(233, 238, 242, 0.62);
    width: 26px;
    flex-shrink: 0;
  }
  .track__title {
    flex: 1;
    min-width: 0;
    font-size: var(--t-body);
    font-weight: 600;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .track__time {
    font-family: var(--font-mono);
    font-size: 16px;
    color: rgba(233, 238, 242, 0.62);
    flex-shrink: 0;
  }

  .strip {
    flex-shrink: 0;
  }
</style>
