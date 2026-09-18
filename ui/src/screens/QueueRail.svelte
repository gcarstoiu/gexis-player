<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The queue rail on now playing (ADR-0038 §1), ported from
  `design/source/Now Playing.dc.html` - its header with Clear, its source
  row as the way to pick a playlist, its rows and its empty state. LMS only:
  the other two renderers hand us a stream and have no queue
  (design/README.md's source table).

  Like the design, the list starts at the track playing now: the rail
  answers "what is next", and LMS keeps the tracks already played behind it.
  Positions sent to the core stay absolute, because that is what LMS's own
  `playlist index` and `playlist delete` take.
-->
<script>
  import { libraryAction, loadPlaylists } from '../lib/library.js';

  let { open, queue, onclose } = $props();

  let switcher = $state(false);
  let playlists = $state([]);
  let failed = $state(new Set());

  const index = $derived(queue?.index ?? 0);
  //: The track playing now, then what follows it.
  const rows = $derived((queue?.items ?? []).slice(index));
  //: What "Up next" counts: the rest, not the one already playing.
  const rest = $derived(rows.slice(1));
  const minutes = $derived(
    Math.max(1, Math.round(rest.reduce((n, item) => n + (item.duration ?? 0), 0) / 60)),
  );
  const meta = $derived(
    rest.length ? `${rest.length} ${rest.length === 1 ? 'track' : 'tracks'}  ·  ${minutes} min left` : 'Nothing queued',
  );
  //: With nothing queued the row stops claiming a source and becomes the
  //: way to pick one (the design's own wording). LMS reports the playlist a
  //: queue came from until the queue is changed, and says when it has been
  //: (Finding 029 §7) - so a queue built by hand has no source to name.
  const hasSource = $derived(rows.length > 0 && !!queue?.name);
  const sourceKicker = $derived(hasSource ? (queue.modified ? 'Started from' : 'Playing from') : 'Play from');
  const sourceName = $derived(hasSource ? queue.name : 'Choose a playlist');
  const sourceAction = $derived(hasSource ? 'Change' : 'Browse');

  const pad = (n) => String(n).padStart(2, '0');

  const mmss = (s) => {
    const whole = Math.max(0, Math.round(s ?? 0));
    return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`;
  };

  async function queueAction(at, action) {
    try {
      await libraryAction('queue', at, action);
    } catch (err) {
      console.info('queue:', err.message);
    }
  }

  async function openSwitcher() {
    switcher = true;
    try {
      playlists = await loadPlaylists();
    } catch (err) {
      console.info('queue:', err.message);
    }
  }

  async function playPlaylist(playlist) {
    switcher = false;
    try {
      await libraryAction('playlist', playlist.id, 'play');
    } catch (err) {
      console.info('queue:', err.message);
    }
  }
</script>

<div class="scrim" class:is-open={open} role="presentation" onclick={onclose}></div>

<div class="rail" class:is-open={open} inert={!open}>
  <div class="rail__head">
    <div class="rail__headtext">
      <div class="rail__kicker">Up next</div>
      <div class="rail__meta">{meta}</div>
    </div>
    {#if rows.length}
      <!-- Clearing acts at once and leaves the rail open, so the emptied
           queue and the way to refill it are both still in front of you. -->
      <button class="clear" type="button" onclick={() => queueAction(0, 'clear')}>Clear</button>
    {/if}
  </div>

  <button class="source" type="button" onclick={openSwitcher}>
    <span class="source__glyph"><i></i><i></i><i></i></span>
    <span class="source__text">
      <span class="source__kicker">{sourceKicker}</span>
      <span class="source__name">{sourceName}</span>
    </span>
    <span class="source__action">{sourceAction}</span>
  </button>

  <div class="rail__list">
    {#each rows as item, offset (index + offset)}
      <div class="qrow" class:is-now={offset === 0}>
        <button class="qrow__hit" type="button" onclick={() => offset && queueAction(index + offset, 'play')}>
          <span class="qrow__num">{offset === 0 ? '▶' : pad(offset)}</span>
          <span class="qrow__art">
            {#if item.artwork && !failed.has(item.artwork)}
              <img src={item.artwork} alt="" onerror={() => (failed = new Set(failed).add(item.artwork))} />
            {/if}
          </span>
          <span class="qrow__text">
            <span class="qrow__title">{item.title ?? ''}</span>
            <span class="qrow__artist">{item.artist ?? ''}</span>
          </span>
          {#if offset === 0}
            <span class="qrow__now">Playing</span>
          {:else if item.duration}
            <span class="qrow__dur">{mmss(item.duration)}</span>
          {/if}
        </button>
        <button class="qrow__remove" type="button" aria-label="Remove" onclick={() => queueAction(index + offset, 'remove')}>
          <span></span><span></span>
        </button>
      </div>
    {:else}
      <div class="empty">
        <div class="empty__glyph"><i></i><i></i><i></i></div>
        <div class="empty__title">Queue is empty</div>
        <div class="empty__text">Pick a playlist or add tracks from the library and they will line up here.</div>
      </div>
    {/each}
  </div>
</div>

<!-- The source sheet: the design's "Play from / Choose a source". Only the
     library's own playlists, because creating one is not offered anywhere
     (ADR-0038 §3). -->
<div class="sw-scrim" class:is-open={switcher} role="presentation" onclick={() => (switcher = false)}></div>
<div class="sw" class:is-open={switcher} inert={!switcher}>
  <div class="sw__kicker">Play from</div>
  <div class="sw__title">Choose a source</div>
  <div class="sw__list">
    {#each playlists as playlist (playlist.id)}
      <button
        class="sw__row"
        class:is-current={hasSource && playlist.name === queue.name}
        type="button"
        onclick={() => playPlaylist(playlist)}
      >
        <span class="sw__glyph"><i></i><i></i><i></i></span>
        <span class="sw__text">
          <span class="sw__name">{playlist.name}</span>
          <span class="sw__meta">{playlist.tracks} tracks</span>
        </span>
        {#if hasSource && playlist.name === queue.name}
          <span class="sw__current">Playing</span>
        {/if}
      </button>
    {:else}
      <div class="empty__text">No playlists in the library</div>
    {/each}
  </div>
</div>

<style>
  /* Each screen carries its own reset (the styles are scoped per
     component): without it every row here drew the browser's default
     button chrome - system font, grey border, a box round the text
     (George, 2026-09-18: "there is no styling to the queue"). */
  button {
    font: inherit;
    color: inherit;
    border: none;
    padding: 0;
    background: none;
    text-align: left;
  }

  .scrim,
  .sw-scrim {
    position: absolute;
    inset: 0;
    background: var(--bg-scrim);
    backdrop-filter: blur(3px);
    opacity: 0;
    pointer-events: none;
    /* Hidden, not merely transparent, once the close has played: a layer
       that still draws behind the panel cost us a black screen once
       (docs/LESSONS.md, the library overlay). */
    visibility: hidden;
    transition: opacity 200ms ease, visibility 0s linear 200ms;
  }
  .scrim {
    z-index: 36;
  }
  .sw-scrim {
    z-index: 38;
    background: rgba(8, 12, 16, 0.66);
    backdrop-filter: blur(4px);
  }
  .scrim.is-open,
  .sw-scrim.is-open {
    opacity: 1;
    pointer-events: auto;
    visibility: visible;
    transition: opacity 200ms ease;
  }

  .rail {
    position: absolute;
    z-index: 37;
    top: 0;
    bottom: 0;
    right: 0;
    width: 470px;
    background: var(--bg-panel);
    border-left: 1px solid rgba(159, 180, 232, 0.22);
    padding: 26px 26px 28px;
    box-sizing: border-box;
    box-shadow: -30px 0 80px rgba(0, 0, 0, 0.5);
    display: flex;
    flex-direction: column;
    transform: translateX(100%);
    visibility: hidden;
    transition: transform 240ms cubic-bezier(0.2, 0.8, 0.2, 1), visibility 0s linear 240ms;
  }
  .rail.is-open {
    transform: translateX(0);
    visibility: visible;
    transition: transform 240ms cubic-bezier(0.2, 0.8, 0.2, 1);
  }

  .rail__head {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 18px;
    flex-shrink: 0;
  }
  .rail__headtext {
    flex: 1;
    min-width: 0;
  }
  .rail__kicker {
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
    letter-spacing: var(--track-label);
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .rail__meta {
    font-size: 22px;
    font-weight: 700;
    color: var(--ink);
    margin-top: 4px;
  }
  .clear {
    display: inline-flex;
    align-items: center;
    height: 44px;
    padding: 0 18px;
    border-radius: 11px;
    background: var(--ink-fill);
    border: 1px solid rgba(233, 238, 242, 0.16);
    font-family: var(--font-mono);
    font-size: var(--t-label);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--ink-strong);
    flex-shrink: 0;
  }
  .clear:active {
    background: var(--ink-fill-press);
  }

  .source {
    flex-shrink: 0;
    height: 66px;
    border-radius: 15px;
    background: rgba(159, 180, 232, 0.1);
    border: 1px solid rgba(159, 180, 232, 0.28);
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 0 20px;
    margin-bottom: 16px;
  }
  .source:active {
    background: rgba(159, 180, 232, 0.24);
  }
  .source__glyph,
  .sw__glyph {
    width: 40px;
    height: 40px;
    border-radius: 9px;
    background: rgba(242, 164, 143, 0.14);
    border: 1px solid rgba(242, 164, 143, 0.3);
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 4px;
    padding: 0 9px;
    box-sizing: border-box;
    flex-shrink: 0;
  }
  .source__glyph i,
  .sw__glyph i {
    height: 2.5px;
    border-radius: 2px;
    background: var(--accent-artist);
  }
  .source__glyph i:nth-child(2),
  .sw__glyph i:nth-child(2) {
    background: rgba(242, 164, 143, 0.7);
    width: 70%;
  }
  .source__glyph i:nth-child(3),
  .sw__glyph i:nth-child(3) {
    background: rgba(242, 164, 143, 0.45);
    width: 85%;
  }
  .source__text {
    flex: 1;
    min-width: 0;
  }
  .source__kicker {
    display: block;
    font-family: var(--font-mono);
    font-size: var(--t-micro);
    letter-spacing: var(--track-label);
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .source__name {
    display: block;
    font-size: var(--t-body);
    font-weight: 700;
    color: var(--ink);
    margin-top: 3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .source__action {
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent-bluetooth);
    flex-shrink: 0;
  }

  .rail__list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 3px;
    scrollbar-width: none;
    contain: content;
    touch-action: pan-y;
  }
  .rail__list::-webkit-scrollbar {
    display: none;
  }

  .qrow {
    height: 60px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    border-radius: 12px;
    padding-right: 8px;
  }
  .qrow.is-now {
    background: rgba(126, 214, 188, 0.14);
  }
  .qrow__hit {
    flex: 1;
    min-width: 0;
    height: 100%;
    display: flex;
    align-items: center;
    gap: 15px;
    padding: 0 14px;
  }
  .qrow__hit:active {
    opacity: 0.62;
  }
  .qrow__num {
    font-family: var(--font-mono);
    font-size: 14px;
    color: rgba(233, 238, 242, 0.55);
    width: 24px;
    flex-shrink: 0;
  }
  .is-now .qrow__num {
    color: var(--accent-lms);
  }
  .qrow__art {
    width: 42px;
    height: 42px;
    border-radius: 8px;
    overflow: hidden;
    position: relative;
    flex-shrink: 0;
    background: var(--bg-well);
    box-shadow: inset 0 0 0 1px var(--ink-line);
  }
  .qrow__art img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .qrow__text {
    flex: 1;
    min-width: 0;
  }
  .qrow__title,
  .qrow__artist {
    display: block;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .qrow__title {
    font-size: 18px;
    font-weight: 600;
    color: var(--ink);
  }
  .is-now .qrow__title {
    color: var(--accent-lms);
  }
  .qrow__artist {
    font-size: 14px;
    color: rgba(233, 238, 242, 0.55);
    margin-top: 2px;
  }
  .qrow__now {
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent-lms);
    flex-shrink: 0;
  }
  .qrow__dur {
    font-family: var(--font-mono);
    font-size: 14px;
    color: rgba(233, 238, 242, 0.5);
    flex-shrink: 0;
  }
  .qrow__remove {
    position: relative;
    width: 44px;
    height: 44px;
    border-radius: 12px;
    background: var(--ink-fill);
    border: 1px solid rgba(233, 238, 242, 0.14);
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .qrow__remove:active {
    background: rgba(242, 164, 143, 0.26);
  }
  .qrow__remove span {
    position: absolute;
    width: 15px;
    height: 2.5px;
    border-radius: 2px;
    background: rgba(233, 238, 242, 0.75);
  }
  .qrow__remove span:first-child {
    transform: rotate(45deg);
  }
  .qrow__remove span:last-child {
    transform: rotate(-45deg);
  }

  .empty {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 14px;
    padding: 40px 0;
  }
  .empty__glyph {
    width: 46px;
    height: 38px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    opacity: 0.4;
  }
  .empty__glyph i {
    height: 5px;
    border-radius: 3px;
    background: rgba(233, 238, 242, 0.7);
  }
  .empty__glyph i:last-child {
    width: 26px;
  }
  .empty__title {
    font-size: var(--t-body);
    font-weight: 600;
    color: var(--ink-strong);
  }
  .empty__text {
    font-size: 16px;
    color: rgba(233, 238, 242, 0.55);
    text-align: center;
    max-width: 360px;
    text-wrap: pretty;
  }

  .sw {
    position: absolute;
    z-index: 39;
    left: 50%;
    top: 50%;
    width: 660px;
    max-height: 80%;
    background: var(--bg-panel);
    border: 1px solid rgba(126, 214, 188, 0.22);
    border-radius: 26px;
    padding: 28px 30px 30px;
    box-sizing: border-box;
    box-shadow: 0 34px 90px rgba(0, 0, 0, 0.6);
    display: flex;
    flex-direction: column;
    transform: translate(-50%, -50%) scale(0.94);
    opacity: 0;
    pointer-events: none;
    visibility: hidden;
    transition: transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1), opacity 180ms ease,
      visibility 0s linear 220ms;
  }
  .sw.is-open {
    transform: translate(-50%, -50%) scale(1);
    opacity: 1;
    pointer-events: auto;
    visibility: visible;
    transition: transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1), opacity 180ms ease;
  }
  .sw__kicker {
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
    letter-spacing: var(--track-label);
    text-transform: uppercase;
    color: var(--ink-quiet);
    flex-shrink: 0;
  }
  .sw__title {
    font-size: 25px;
    font-weight: 700;
    color: var(--ink);
    margin: 5px 0 20px;
    flex-shrink: 0;
  }
  .sw__list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 9px;
    scrollbar-width: none;
  }
  .sw__list::-webkit-scrollbar {
    display: none;
  }
  .sw__row {
    height: 72px;
    flex-shrink: 0;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.045);
    border: 1px solid rgba(233, 238, 242, 0.09);
    display: flex;
    align-items: center;
    gap: 17px;
    padding: 0 20px;
  }
  .sw__row:active {
    background: rgba(233, 238, 242, 0.16);
  }
  .sw__row.is-current {
    background: rgba(126, 214, 188, 0.12);
    border-color: rgba(126, 214, 188, 0.34);
  }
  .sw__text {
    flex: 1;
    min-width: 0;
  }
  .sw__name {
    display: block;
    font-size: 20px;
    font-weight: 700;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .sw__row.is-current .sw__name {
    color: var(--accent-lms);
  }
  .sw__meta {
    display: block;
    font-size: 15px;
    color: var(--ink-quiet);
    margin-top: 3px;
  }
  .sw__current {
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent-lms);
    flex-shrink: 0;
  }
</style>
