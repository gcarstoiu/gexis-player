<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Now playing, Phase 4 step 4c: display only. Ported from
  design/now-playing.html; the styles are that file's, trimmed to what this
  screen uses. Controls render for the layout but are disabled and carry
  data-unwired="<phase>" until the phase that wires them.
-->
<script>
  import SourceMark from '../lib/SourceMark.svelte';
  import VolumeIcon from '../lib/VolumeIcon.svelte';
  import { retryEnrichment, trackEnrichment } from '../lib/enrichment.js';
  import { artistsCached, foldedName, loadArtistGenres } from '../lib/library.js';
  import QueueRail from './QueueRail.svelte';

  import { sendTransport } from '../lib/state.js';
  import { playhead, mmss } from '../lib/playhead.svelte.js';
  import { playToggle } from '../lib/playToggle.svelte.js';

  let { active, metadata, volume, controls = [], available = [], shuffle = null, repeat = null, queue = null, onvolume, onvisualisation, onhome, onartist } = $props();

  const transport = $derived(metadata?.transport ?? null);

  // An artwork URL that fails to load falls back to the pending glyph.
  let failedArtwork = $state(null);
  //: What the renderer sent, and only then what enrichment found. ADR-0012
  //: is additive-only: a cover looked up from a fuzzy AVRCP string must
  //: never replace one the renderer supplied, it can only fill a hole
  //: (George, 2026-09-18: no artwork at all over Bluetooth).
  const artwork = $derived.by(() => {
    const supplied = metadata?.artwork;
    if (supplied && supplied !== failedArtwork) return supplied;
    const found = artistInfo.enrichment?.album_art;
    return found && found !== failedArtwork ? found : null;
  });

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

  // The Artist, Release and Lyrics tabs (ADR-0040). **The lookup itself
  // lives in lib/enrichment.js**, because the mini strip needs the same
  // answer while this screen is not mounted at all - the library is open
  // exactly when the strip is on show (George, 2026-09-18: no cover on the
  // strip for a Bluetooth track whose cover had been found).
  let tab = $state('track');
  const artistInfo = $derived($trackEnrichment);

  const initialsOf = (name) =>
    (name ?? '')
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((word) => word[0].toUpperCase())
      .join('') || '?';

  const info = $derived(artistInfo.enrichment);

  //: Both sources hard-wrap their text and separate paragraphs with a blank
  //: line. Rendered as one string the browser collapses every one of those
  //: into a single blob (George, 2026-09-18).
  const asParagraphs = (text) =>
    (text ?? '')
      .split(/\n\s*\n/)
      .map((block) => block.replace(/\s*\n\s*/g, ' ').trim())
      .filter(Boolean);
  const bioParagraphs = $derived(asParagraphs(info?.biography));
  const noteParagraphs = $derived(asParagraphs(info?.album_note));

  //: **Clamped with a fade, not scrolled.** The panel already scrolls, and a
  //: second scroller inside it takes the finger meant for the first - the
  //: same reason the artist page clamps its biography. Cut off with no fade
  //: and no control, the text just looked truncated (George, on the panel,
  //: 2026-09-20).
  //:
  //: **The whole block is the tap target and there is no More/Less.** George
  //: took the control away the next day - *"tapping in the text works
  //: perfectly as a toggle and the bottom fade indicates that there is more
  //: to be read"* - which makes the fade the only signal, so it is drawn
  //: only when something is actually under it. A fade over a note that is
  //: already whole would be the lie the control used to cover for.
  const FOLD_MAX = 128;
  let bioOpen = $state(false);
  let noteOpen = $state(false);
  let bioEl = $state(null);
  let noteEl = $state(null);
  let bioClipped = $state(false);
  let noteClipped = $state(false);
  //: `scrollHeight` is the content's height whether or not the clamp is on,
  //: so one test serves both states. Measured after a frame, because the
  //: paragraphs have only just been written into the element.
  //: The block is a tap target, so it answers the keyboard too - the panel
  //: and a phone take the same input, and a keyboard is one of them.
  function foldKey(event, toggle) {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    toggle();
  }
  function clipCheck(el, set) {
    if (!el) {
      set(false);
      return;
    }
    const frame = requestAnimationFrame(() => set(el.scrollHeight > FOLD_MAX + 2));
    return () => cancelAnimationFrame(frame);
  }
  $effect(() => {
    void bioParagraphs, tab;
    return clipCheck(bioEl, (v) => (bioClipped = v));
  });
  $effect(() => {
    void noteParagraphs, tab;
    return clipCheck(noteEl, (v) => (noteClipped = v));
  });
  //: The artist page carries the library's own genres for an artist (9c) and
  //: the design puts the same pills in this tab. LMS answers them by artist
  //: id, so the name a renderer reports has to be resolved through the
  //: library's cached artist list first - usually already in hand, and one
  //: small request when it is not. Fetched when the tab is opened rather
  //: than for every track, because most tracks are never looked at here.
  //:
  //: Nothing found means no pills. **The region blanks, never the screen**
  //: (ADR-0014): a renderer whose artist is not in this library - anything
  //: over Bluetooth or Spotify - simply has none.
  let genres = $state([]);
  $effect(() => {
    const name = metadata?.artist ?? null;
    const open = tab === 'artist';
    genres = [];
    if (!name || !open) return;
    let dropped = false;
    (async () => {
      try {
        const wanted = foldedName(name);
        const match = (await artistsCached()).find((a) => foldedName(a.name) === wanted);
        if (!match) return;
        const found = await loadArtistGenres(match.id);
        if (!dropped) genres = found ?? [];
      } catch (err) {
        console.info('genres:', err.message);
      }
    })();
    return () => {
      dropped = true;
    };
  });

  //: A new track is a new text; neither fold survives it.
  $effect(() => {
    void info;
    bioOpen = false;
    noteOpen = false;
  });

  // An LRC body is `[mm:ss.xx] text` per line. Lines without a stamp are
  // kept - LRCLIB files carry `[ar:]`-style headers and blank beats - but
  // only stamped ones can be followed.
  const LRC = /^\[(\d+):(\d+(?:\.\d+)?)\]\s?(.*)$/;
  const synced = $derived.by(() => {
    const body = info?.lyrics_synced;
    if (!body) return [];
    const out = [];
    for (const line of body.split('\n')) {
      const match = LRC.exec(line.trim());
      if (!match) continue;
      out.push({ at: Number(match[1]) * 60 + Number(match[2]), text: match[3].trim() });
    }
    return out.sort((a, b) => a.at - b.at);
  });
  //: **A stamped line with no words is timing, not a lyric.** LRC bodies use
  //: them for the run-in, for instrumental breaks and for the outro, and
  //: following them literally leaves the panel blank in the middle of a song
  //: and again at the end - which reads as a fault rather than as silence
  //: (George, on the panel, 2026-09-20). So the words are kept apart from the
  //: timing: these are the lines that have any, each remembering where it sat
  //: so the clock can still be followed.
  const sungLines = $derived(synced.map((line, i) => ({ ...line, src: i })).filter((l) => l.text));
  const plainLines = $derived((info?.lyrics ?? '').split('\n'));
  //: The design keeps the compact Track panel while the lookup is running,
  //: so the screen does not jump from the tall block to the short one when
  //: the words arrive.
  const lyricsPending = $derived(artistInfo.state === 'loading');

  // Which synced line is current. The playhead interpolates between pushes
  // (playhead.svelte.js), so this follows the same clock the progress bar
  // does rather than a second one.
  const activeLine = $derived.by(() => {
    if (!synced.length) return -1;
    const at = head.elapsed;
    let index = -1;
    for (let i = 0; i < synced.length; i += 1) {
      if (synced[i].at <= at) index = i;
      else break;
    }
    return index;
  });
  //: Which line the panel rests on: the last one that was sung. Through a
  //: gap - or after the final word - it stays there rather than emptying,
  //: and `singing` is false, so it is shown without the highlight.
  const anchor = $derived.by(() => {
    if (!sungLines.length) return -1;
    let n = 0;
    for (let i = 0; i < sungLines.length; i += 1) {
      if (sungLines[i].src <= activeLine) n = i;
      else break;
    }
    return n;
  });
  const singing = $derived(anchor >= 0 && sungLines[anchor]?.src === activeLine);

  //: The design's compact synced view: **three** lines, one either side of
  //: the current one (2026-09-22, was five). Three at 32px need ~157px, and
  //: the rest of the column goes to the title block above rather than to
  //: more lyric context.
  const window3 = $derived.by(() => {
    if (!sungLines.length) return [];
    const at = Math.max(0, anchor);
    return [at - 1, at, at + 1]
      .filter((n) => n >= 0 && n < sungLines.length)
      .map((n) => ({ ...sungLines[n], n, distance: Math.abs(n - at) }));
  });
  //: The Lyrics tab shows the whole song, not a five-line window, and keeps
  //: the current line in view by translating the list - the design's own
  //: mechanism (`translateY(-(child.offsetTop - lead))`). Measured rather
  //: than computed from a line height, because a long line wraps and stops
  //: being one box tall.
  let lyricsBox = $state(null);
  let lineEls = $state([]);
  let lyricsShift = $state(0);
  $effect(() => {
    // Re-measure when the line changes, when the words change, and when the
    // tab is opened - lyricsBox is null until then.
    const i = anchor, box = lyricsBox, el = lineEls[i];
    if (!box || !el || i < 0) { lyricsShift = 0; return; }
    const lead = box.clientHeight / 2 - el.offsetHeight / 2;
    lyricsShift = Math.min(0, lead - el.offsetTop);
  });

  //: LMS first, enrichment second. See the markup for why the two differ.
  const year = $derived(metadata?.year ?? info?.released ?? null);

  const specs = $derived.by(() => {
    if (!info) return [];
    const out = [];
    if (info.released) out.push(['Released', info.released]);
    if (info.track_count) out.push(['Tracks', String(info.track_count)]);
    if (info.length_s) out.push(['Length', `${Math.round(info.length_s / 60)} min`]);
    if (info.label) out.push(['Label', info.label]);
    return out;
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
  data-source={active ?? 'lms'}
  data-transport={transport ?? 'none'}
  data-artwork={artwork ? 'ok' : 'none'}
  data-position={head.hasPosition ? 'ok' : 'none'}
>
  <!-- The weave and the artwork's bleed are drawn once for the whole panel
       (PanelBackground.svelte); this screen keeps only its own veil. -->
  <div class="screen__veil"></div>
  <div class="screen__accent"></div>

  <!-- **The mark alone, at 32px** (design, 2026-09-22). The word beside it
       went: the accent rule along the top edge and the mark itself already
       say which renderer this is, and a third statement in words was the
       one taking the most room. -->
  <span class="srcpill" class:is-playing={transport === 'playing'}>
    <SourceMark source={active} size={32} color="var(--src-accent)" />
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
          <button class="tab" data-tab="track" type="button" role="tab" aria-selected={tab === 'track'} onclick={() => (tab = 'track')}>Track</button>
          <button class="tab" data-tab="lyrics" type="button" role="tab" aria-selected={tab === 'lyrics'} onclick={() => (tab = 'lyrics')}>Lyrics</button>
          <button class="tab" data-tab="artist" type="button" role="tab" aria-selected={tab === 'artist'} onclick={() => (tab = 'artist')}>Artist</button>
          <button class="tab" data-tab="release" type="button" role="tab" aria-selected={tab === 'release'} onclick={() => (tab = 'release')}>Release</button>
        </div>

        <div class="panel">
          {#if tab === 'track'}
            <!-- One header, whether or not lyrics are there (design/screens.md
                 §1, and design/now-playing.css says it in as many words).
                 Until 2026-09-20 this branched: a 58px title when there were
                 no synced lyrics and a 38px "compact" variant when there
                 were, so the title jumped the moment lyrics arrived. The
                 design deletes the large variant rather than shrinking it -
                 the block is pinned to the top of the panel and the words,
                 when they exist, sit under a hairline below it. -->
            <div class="trackblock">
              <div class="title" class:is-empty={!metadata?.title}>{metadata?.title ?? ''}</div>
              <!-- Artist, album and year share one baseline row. -->
              <div class="metaline">
                <!-- The design links the artist line to that artist's page
                     (`onNpArtist`). -->
                <button
                  class="artist artist--link"
                  class:is-empty={!metadata?.artist}
                  type="button"
                  disabled={!metadata?.artist}
                  onclick={() => onartist?.(metadata.artist)}
                >{metadata?.artist ?? ''}</button>
                <span class="album" class:is-empty={!metadata?.album}>{metadata?.album ?? ''}</span>
                <!-- The release year. LMS first: it carries one per track
                     (songinfo tag `y`) and it is the library's own record.
                     Enrichment's `released` is the fallback - it describes
                     the *release* a lookup matched, so a 1996 track on a 2025
                     compilation reports 2025 there and 1996 here - and it is
                     the only source Spotify and Bluetooth have.
                     Rendered only when there is one, rather than holding an
                     empty slot open. -->
                {#if year}
                  <span class="year">{year}</span>
                {/if}
              </div>

              {#if sungLines.length || lyricsPending}
                <div class="trackblock__rule"></div>
                <!-- The words take whatever height is left and are centred in
                     it: the design positions the compact lyric view against
                     this box rather than giving it a height of its own. -->
                <div class="trackblock__body">
                  {#if sungLines.length}
                    <div class="lyrics lyrics--synced lyrics--fill">
                      {#each window3 as line (line.n)}
                        <div class="lyrics__line" class:is-now={line.distance === 0 && singing} data-distance={line.distance}>
                          {line.text}
                        </div>
                      {/each}
                    </div>
                  {:else}
                    <div class="looking">
                      <div class="looking__bar"></div>
                      <div class="looking__bar"></div>
                      <div class="looking__bar"></div>
                      <div class="looking__label">Looking for lyrics</div>
                    </div>
                  {/if}
                </div>
              {/if}
            </div>
          {:else if tab === 'lyrics'}
            <div class="artisttab">
              <div class="sect">
                <span class="sect__label">Lyrics</span>
                <span class="sect__rule"></span>
                {#if artistInfo.state === 'loading'}<span class="sect__note">Looking…</span>{/if}
              </div>

              {#if artistInfo.state === 'loading'}
                <div class="skel"><span></span><span></span><span></span></div>
              {:else if info?.instrumental}
                <div class="lyrics__none">Instrumental</div>
              {:else if sungLines.length}
                <!-- The whole song, scrolled to the current line. The Track
                     tab shows three lines because it shares the panel with
                     the header; this tab has the panel to itself, so every
                     line is drawn at a flat weight with only the sung one
                     lit - the fade belongs to the window, not here. -->
                <div class="lyrics lyrics--synced lyrics--scroll" bind:this={lyricsBox}>
                  <div class="lyrics__scroller" style:transform={`translateY(${lyricsShift}px)`}>
                    {#each sungLines as line, i (i)}
                      <div
                        class="lyrics__line"
                        class:is-now={i === anchor && singing}
                        bind:this={lineEls[i]}
                      >{line.text}</div>
                    {/each}
                  </div>
                </div>
                <div class="credit">From {info.lyrics_source}</div>
              {:else if info?.lyrics}
                <div class="lyrics lyrics--plain">
                  {#each plainLines as line, i (i)}
                    <div class="lyrics__line">{line}</div>
                  {/each}
                </div>
                <div class="credit">From {info.lyrics_source}</div>
              {:else if artistInfo.state === 'error'}
                <div class="offline">
                  <span>Lyrics unavailable. Your library is unaffected.</span>
                  <button class="offline__retry" type="button" onclick={retryEnrichment}>Retry</button>
                </div>
              {:else}
                <div class="lyrics__none">No lyrics found for this track.</div>
              {/if}
            </div>
          {:else if tab === 'release'}
            <div class="artisttab">
              <div class="artisttab__head">
                <span class="reltab__art">
                  {#if artwork}<img src={artwork} alt="" />{/if}
                </span>
                <span class="reltab__titles">
                  <span class="reltab__name">{metadata?.album ?? 'No album'}</span>
                  <span class="reltab__by">
                    {metadata?.artist ?? ''}{info?.released ? `  ·  ${info.released}` : ''}
                  </span>
                  {#if info?.release_type}
                    <span class="reltab__chips"><span class="reltab__chip">{info.release_type}</span></span>
                  {/if}
                </span>
              </div>

              <div class="sect">
                <span class="sect__label">About this release</span>
                <span class="sect__rule"></span>
                {#if artistInfo.state === 'loading'}<span class="sect__note">Looking…</span>{/if}
              </div>

              {#if artistInfo.state === 'loading'}
                <div class="skel"><span></span><span></span><span></span></div>
              {:else if info?.album_note}
                <div
                  class="bio"
                  class:is-clamped={!noteOpen && noteClipped}
                  style:max-height={noteOpen || !noteClipped ? null : `${FOLD_MAX}px`}
                  role="button"
                  tabindex="0"
                  aria-expanded={noteOpen}
                  bind:this={noteEl}
                  onclick={() => (noteOpen = !noteOpen)}
                  onkeydown={(e) => foldKey(e, () => (noteOpen = !noteOpen))}
                >
                  {#each noteParagraphs as para, i (i)}<p class="bio__para">{para}</p>{/each}
                </div>
                <div class="credit">
                  <span>From {info.album_note_source}</span>
                </div>
              {:else if artistInfo.state === 'error'}
                <div class="offline">
                  <span>Release details unavailable. Your library is unaffected.</span>
                  <button class="offline__retry" type="button" onclick={retryEnrichment}>Retry</button>
                </div>
              {:else}
                <div class="sect__empty">No notes for this release.</div>
              {/if}

              {#if specs.length}
                <div class="specs">
                  {#each specs as [k, v] (k)}
                    <div class="spec"><div class="spec__k">{k}</div><div class="spec__v">{v}</div></div>
                  {/each}
                </div>
              {/if}
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
                <span class="artisttab__titles">
                  <span class="artisttab__name">{metadata?.artist ?? ''}</span>
                  {#if genres.length}
                    <span class="artisttab__tags">
                      {#each genres as g, i (g)}
                        <span class="gtag gtag--{i % 3}">{g}</span>
                      {/each}
                    </span>
                  {/if}
                </span>
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
                <div
                  class="bio"
                  class:is-clamped={!bioOpen && bioClipped}
                  style:max-height={bioOpen || !bioClipped ? null : `${FOLD_MAX}px`}
                  role="button"
                  tabindex="0"
                  aria-expanded={bioOpen}
                  bind:this={bioEl}
                  onclick={() => (bioOpen = !bioOpen)}
                  onkeydown={(e) => foldKey(e, () => (bioOpen = !bioOpen))}
                >
                  {#each bioParagraphs as para, i (i)}<p class="bio__para">{para}</p>{/each}
                </div>
                <!-- Wikipedia's CC BY-SA and MusicBrainz's CC BY-NC-SA both
                     require the credit beside the text (ADR-0040 §4). -->
                <div class="credit">
                  <span>From {artistInfo.enrichment.biography_source}</span>
                </div>
              {:else if artistInfo.state === 'error'}
                <div class="offline">
                  <span>Artist details unavailable. Your library is unaffected.</span>
                  <button class="offline__retry" type="button" onclick={retryEnrichment}>Retry</button>
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

  /* Mark and word only. The pill ground, border and radius were removed from
     the design on 2026-09-19 - the class keeps its name because everything
     that refers to it does, but there is no pill left. */
  .srcpill {
    position: absolute;
    top: 44px;
    right: 56px;
    z-index: 6;
    display: inline-flex;
    align-items: center;
    color: var(--src-accent);
  }
  .srcpill.is-playing {
    animation: pulse 2.4s ease-in-out infinite;
  }
  @keyframes pulse {
    0%,
    100% { opacity: 1; }
    50% { opacity: 0.35; }
  }
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
    gap: 34px;
    align-self: flex-start;
    flex-shrink: 0;
    margin-bottom: 18px;
    border-bottom: 1px solid rgba(233, 238, 242, 0.12);
  }
  .tab {
    font-family: var(--font-mono);
    /* 19px, up from 17 (design, 2026-09-22): the whole meta column grew and
       the tab row grew with it. The 44px target is unchanged - it comes from
       the padding/negative-margin pair, not from the font. */
    font-size: var(--t-body);
    font-weight: 600;
    letter-spacing: var(--track-wide);
    text-transform: uppercase;
    white-space: nowrap;
    color: var(--ink-tab-off);
    min-height: var(--touch-min);
    padding: 16px 2px 9px;
    margin-top: -16px;
    border: 0;
    border-bottom: 3px solid transparent;
    background: none;
  }
  /* Each tab's selected ink and underline are ITS OWN fixed colour, never
     the source accent (design/README.md, "Changed 2026-09-19"). The source
     accent already carries the 3px rule along the top edge and the mark; a
     tab row that also tracked it would say the same thing three times and
     would recolour when the renderer changed, which the tab did not. */
  .tab[aria-selected='true'] { color: var(--ink); }
  .tab[data-tab='track'][aria-selected='true']   { border-bottom-color: var(--ink); }
  .tab[data-tab='lyrics'][aria-selected='true']  { border-bottom-color: var(--accent-artist); }
  .tab[data-tab='artist'][aria-selected='true']  { border-bottom-color: var(--accent-bluetooth); }
  .tab[data-tab='release'][aria-selected='true'] { border-bottom-color: var(--accent-lms); }

  .panel {
    margin-top: 36px;
    flex: 1;
    min-height: 0;
    position: relative;
  }

  /* Pinned to the panel, so the header sits at the top whether or not the
     words are under it. `.metalyrics` and its modifiers are gone with the
     second layout they belonged to. */
  .trackblock {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .trackblock__rule {
    height: 1px;
    background: rgba(233, 238, 242, 0.12);
    margin-top: 20px;
    flex-shrink: 0;
  }
  .trackblock__body {
    flex: 1;
    min-height: 0;
    position: relative;
    overflow: hidden;
    /* The strip is ghosted at both ends, not merely dimmer: transparent to
       opaque over the first 30% and back over the last 30% (design,
       2026-09-22, which widened it from 9%/91%). A static mask, not a
       filter - ADR-0041. */
    -webkit-mask-image: linear-gradient(180deg, transparent 0, #000 30%, #000 70%, transparent 100%);
    mask-image: linear-gradient(180deg, transparent 0, #000 30%, #000 70%, transparent 100%);
  }

  /* The Artist tab (ADR-0040), ported from the design's About and Similar
     blocks. It occupies the same box as the track block, so switching tabs
     moves nothing else on the screen. */
  /* The Artist, Lyrics and Release tabs occupy the same box as .trackblock,
     so switching tabs moves nothing else on the screen.

     **It is pinned and it scrolls**, which it was not before 2026-09-20.
     `min-height: 238px` with no maximum and no overflow meant long content
     simply grew out of the panel and drew over the transport and the progress
     bar underneath it - George saw it on a track whose lyrics are not synced,
     where the whole song renders as one block. The same fault kept the artist
     biography from scrolling: it was not that the text happened to fit, it
     was that anything longer overflowed silently. */
  .artisttab {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    gap: 14px;
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-width: none;
    touch-action: pan-y;
  }
  .artisttab::-webkit-scrollbar { display: none; }
  .artisttab__head {
    display: flex;
    /* Top-aligned, so the disc stays beside the name when genre pills push
       the column taller - the design's own alignment. */
    align-items: flex-start;
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
  .artisttab__titles {
    flex: 1;
    min-width: 0;
  }
  .artisttab__name {
    display: block;
    /* 25px, pinned. This used `--t-artist`, which the 2026-09-22 drop moved
       25 -> 35 for the *Track* header; that drop does not change this panel,
       so the shared token is not allowed to carry it along. */
    font-size: 25px;
    font-weight: 700;
    color: var(--accent-artist);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .artisttab__tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 14px;
  }
  /* The design gives this panel's pills three accents in rotation rather
     than the one the library's artist page uses - a row of them is the only
     colour in the panel, and three reads as a set where one reads as a
     status. */
  .gtag {
    font-size: var(--t-label);
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 6px 13px;
    border-radius: var(--r-pill);
    white-space: nowrap;
  }
  .gtag--0 {
    background: rgba(126, 214, 188, 0.14);
    border: 1px solid rgba(126, 214, 188, 0.3);
    color: var(--accent-lms);
  }
  .gtag--1 {
    background: rgba(242, 164, 143, 0.14);
    border: 1px solid rgba(242, 164, 143, 0.3);
    color: var(--accent-artist);
  }
  .gtag--2 {
    background: rgba(159, 180, 232, 0.14);
    border: 1px solid rgba(159, 180, 232, 0.3);
    color: var(--accent-bluetooth);
  }

  .reltab__art {
    width: 64px;
    height: 64px;
    border-radius: 10px;
    overflow: hidden;
    position: relative;
    flex-shrink: 0;
    background: var(--bg-well);
    box-shadow: inset 0 0 0 1px var(--ink-line);
  }
  .reltab__art img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .reltab__titles {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .reltab__name {
    /* 22px, pinned - see `.artisttab__name`. `--t-lead` went 22 -> 25 for the
       Track header's year and this panel did not change. */
    font-size: 22px;
    font-weight: 700;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .reltab__by {
    font-size: var(--t-body-sm);
    color: var(--ink-quiet);
  }
  .reltab__chips {
    display: flex;
    gap: 7px;
    margin-top: 3px;
  }
  .reltab__chip {
    display: inline-flex;
    align-items: center;
    height: 26px;
    padding: 0 10px;
    border-radius: 8px;
    background: rgba(159, 180, 232, 0.14);
    border: 1px solid rgba(159, 180, 232, 0.3);
    font-family: var(--font-mono);
    font-size: var(--t-micro);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent-bluetooth);
  }

  /* The design's compact Track panel fills the panel rather than sitting in
     a box of its own: the title block keeps its height, the rule follows,
     and the words take everything left over. Given a fixed height instead,
     the five lines are squeezed into the gap (George, 2026-09-18). */
  .artist--link {
    font: inherit;
    color: inherit;
    border: none;
    background: none;
    padding: 9px 0;
    margin: -9px 0;
    text-align: left;
    max-width: 100%;
  }
  .artist--link:active:not(:disabled) { color: #f8c4b4; }

  .lyrics--fill {
    position: absolute;
    inset: 0;
  }

  .looking {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 16px;
    padding-right: 40px;
  }
  .looking__bar {
    height: 19px;
    border-radius: 6px;
    background: rgba(233, 238, 242, 0.09);
    animation: npSkel 1800ms ease-in-out infinite;
    width: 78%;
  }
  .looking__bar:nth-child(2) {
    width: 62%;
    background: rgba(233, 238, 242, 0.07);
    animation-delay: 220ms;
  }
  .looking__bar:nth-child(3) {
    width: 70%;
    background: rgba(233, 238, 242, 0.05);
    animation-delay: 440ms;
  }
  .looking__label {
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--ink-quiet);
    margin-top: 8px;
  }

  .lyrics {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    text-wrap: pretty;
  }
  /* The scrolled full-song view: a fixed window with the list translated
     inside it, so the tab itself does not scroll and the current line stays
     put. `.lyrics--synced` alone (the Track tab) still centres its lines. */
  /* Specificity on purpose: `.lyrics--synced` centres its three lines and is
     written after this rule, so at equal weight it would win here too - and
     a list taller than its box, centred *and* translated, leaves the sung
     line off the top of the screen. That is what made the Lyrics tab look
     empty (George, on the panel, 2026-09-20). */
  .lyrics--synced.lyrics--scroll {
    flex: 1;
    min-height: 0;
    overflow: hidden;
    justify-content: flex-start;
    /* The same 30%/70% ramp the Track strip carries: the design puts it on
       both lyric windows (2026-09-22). The sung line is held at the centre
       of the box, so it is never the one being faded. */
    -webkit-mask-image: linear-gradient(180deg, transparent 0, #000 30%, #000 70%, transparent 100%);
    mask-image: linear-gradient(180deg, transparent 0, #000 30%, #000 70%, transparent 100%);
  }
  .lyrics--scroll .lyrics__line {
    color: var(--ink-lyric-off);
  }
  .lyrics__scroller {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
    transition: transform 320ms ease;
    will-change: transform;
  }
  .lyrics--synced {
    align-items: center;
    justify-content: center;
    /* No gap: the per-line boxes above carry the spacing, and a gap on top
       of them would stack with it. */
    gap: 0;
    text-align: center;
  }
  /* Plain lyrics are the whole song in one block; the tab scrolls them. */
  .lyrics--plain {
    gap: 6px;
    flex: 0 0 auto;
  }

  .lyrics__line {
    font-size: 21px;
    line-height: 1.35;
    font-weight: 500;
    color: var(--ink-strong);
    transition: color 320ms ease, opacity 320ms ease;
  }
  /* In the Lyrics tab each line gets a fixed 70px box and is centred in it
     rather than being sized by its own text, so the window does not jitter
     as lines of different length scroll through it (`minHeight: LINE`). The
     Track tab's strip overrides this below. */
  .lyrics--synced .lyrics__line {
    font-size: 31px;
    font-weight: 500;
    min-height: 70px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  /* Inside the Track tab it is three lines at 32px, spaced by a gap rather
     than by a line box: the strip is centred in what the header leaves and
     each line is its own height (design, 2026-09-22). */
  .lyrics--fill {
    gap: 16px;
  }
  .lyrics--fill .lyrics__line {
    font-size: 32px;
    line-height: 1.3;
    min-height: 0;
    display: block;
    text-wrap: pretty;
  }
  .lyrics--synced .lyrics__line[data-distance='1'] { opacity: 0.42; }
  .lyrics__line.is-now {
    font-weight: 700;
    color: var(--accent-artist);
  }
  .lyrics__none {
    font-size: var(--t-body-sm);
    color: var(--ink-quiet);
  }

  .specs {
    display: flex;
    gap: 26px;
    flex-wrap: wrap;
  }
  .spec__k {
    font-family: var(--font-mono);
    font-size: var(--t-micro);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .spec__v {
    font-size: var(--t-body-sm);
    font-weight: 600;
    color: var(--ink);
    margin-top: 3px;
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
    font-size: 17px;
    line-height: 1.5;
    color: var(--ink-body);
    text-wrap: pretty;
  }
  /* A height with a fade, not a scroller and not `-webkit-line-clamp` -
     which needs `display: -webkit-box` and then shows one paragraph of
     several. The mask says there is more without pretending to count
     lines; the artist page's biography does the same. */
  .bio.is-clamped {
    overflow: hidden;
    -webkit-mask-image: linear-gradient(180deg, #000 58%, transparent 100%);
    mask-image: linear-gradient(180deg, #000 58%, transparent 100%);
  }
  .bio__para {
    margin: 0 0 10px;
  }
  .bio__para:last-child {
    margin-bottom: 0;
  }

  .credit {
    display: flex;
    align-items: center;
    gap: 14px;
    font-family: var(--font-mono);
    font-size: var(--t-micro);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  /* Only drawn when the text is actually cut. The design's own toggle is
     this size and this colour. */

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
    /* No reserved two-line box: the block is pinned to the top of the
       panel and followed by a rule only when there are lyrics, so there is
       nothing below it to hold still. Clamped to two lines at 54px
       (design, 2026-09-22 - it was 38). */
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    flex-shrink: 0;
  }
  /* Artist, album and year on one baseline row. Replaces .artistline and
     .albumline, which stacked them. */
  .metaline {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-top: 12px;
    min-width: 0;
    flex-shrink: 0;
  }
  /* A flex item on .metaline now, not an inline-block on its own line. The
     padding/negative-margin pair keeps the 44px touch target without adding
     height to the row (design/README.md's "Canvas" note). */
  .artist {
    font-size: var(--t-artist);
    font-weight: 600;
    color: var(--accent-artist);
    padding: 9px 0;
    margin: -9px 0;
    flex-shrink: 0;
    max-width: 60%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .album {
    font-size: var(--t-h2);
    line-height: 1.35;
    color: rgba(233, 238, 242, 0.6);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  /* The release year, mono so it reads as a number rather than a word. */
  .year {
    font-family: var(--font-mono);
    font-size: var(--t-lead);
    color: var(--ink-quiet);
    white-space: nowrap;
    flex-shrink: 0;
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
