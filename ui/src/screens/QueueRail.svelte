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
  import { flip } from 'svelte/animate';
  import { inView, watchScroller } from '../lib/window.svelte.js';

  let { open, queue, onclose } = $props();

  let switcher = $state(false);
  let playlists = $state([]);
  let failed = $state(new Set());

  const index = $derived(queue?.index ?? 0);
  //: The track playing now, then what follows it.
  const rows = $derived((queue?.items ?? []).slice(index));

  //: **Each row with an identity of its own** (ADR-0064). Keyed by position,
  //: removing one track handed every row below it a different track: Svelte
  //: kept the nodes and rewrote their contents, which is 180 titles,
  //: artists and covers for one removal - and the swiped row was never
  //: destroyed, so it animated its way back in wearing the next track
  //: (George, 2026-09-24). The daemon now carries LMS's track id per row.
  //:
  //: A queue may hold the same track twice, and two rows may not share a
  //: key, so the count settles it. That makes a duplicate's key depend on
  //: how many come before it - which is only wrong for the duplicates
  //: themselves, and only when an earlier one is removed.
  const keyed = $derived.by(() => {
    const seen = new Map();
    return rows.map((item, offset) => {
      const id = item.track_id ?? `at:${index + offset}`;
      const nth = (seen.get(id) ?? 0) + 1;
      seen.set(id, nth);
      return { item, offset, at: index + offset, key: `${id}#${nth}` };
    });
  });
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

  //: **The rail builds only the rows on screen** (ADR-0067, extended to the
  //: rail on 2026-09-25). Removing one row renumbers every row below it -
  //: `.qrow__num` is the queue position - so taking a track out of a
  //: 458-track queue rewrote 465 pieces of text and dropped 10-19 % of the
  //: frames, where the same gesture on a 16-track queue drops none.
  const OVERSCAN = 400;
  const railScroll = watchScroller();

  let list = $state(null);
  let pitch = $state(null);
  //: Plain, not state: an effect that reads what it writes wakes itself
  //: (LESSONS 31).
  let pitched = false;

  function measurePitch() {
    const row = list?.querySelector('.qrow');
    if (!row) return;
    // A row's own bottom margin is its share of the spacing, so the pitch
    // is the two together - and the spacers, which have no margin, stand
    // for exactly that many rows.
    const spacing = parseFloat(getComputedStyle(row).marginBottom) || 0;
    pitch = row.offsetHeight + spacing;
    pitched = true;
  }

  $effect(() => {
    void keyed.length;
    void railScroll.view;
    if (!list) return;
    if (!pitched) requestAnimationFrame(() => setTimeout(measurePitch, 0));
  });

  const railWindow = $derived.by(() => {
    if (!pitch || !keyed.length) {
      return { rows: keyed.slice(0, 14), above: 0, below: 0 };
    }
    const blocks = keyed.map((row, at) => ({ top: at * pitch, height: pitch, row }));
    const { from, to, above, below } = inView(
      blocks,
      railScroll.top,
      railScroll.view || 600,
      OVERSCAN,
    );
    return { rows: blocks.slice(from, to + 1).map((b) => b.row), above, below };
  });

  const pad = (n) => String(n).padStart(2, '0');

  //: **How far a row travels before releasing it removes the track**
  //: (ADR-0062). A queue row is 60px tall in a 417px rail, so this is under
  //: a third of the width - far enough that a mis-aimed vertical scroll
  //: never reaches it, short enough to do with a thumb.
  const REMOVE_AT = 96;
  //: Below this a gesture has not said what it is yet. Past it, whichever
  //: axis is larger wins: the list scrolls vertically and a row swipes
  //: horizontally, and one gesture must not do both.
  const DECIDE_AT = 12;

  //: The row being swiped, if any. One at a time - a second finger on
  //: another row is not a thing this rail does. `live` is a finger actually
  //: on it, which is the only time the row must not animate: it is wherever
  //: the finger is. The hint below moves a row with no finger on it.
  let swipe = $state({ key: null, dx: 0, going: false, live: false });

  //: **A key is a position, and positions move.** Removing the track at 7
  //: makes the old 8 the new 7 - so a key left set after a removal belongs
  //: to a different track, and the row that inherits it inherits being
  //: swiped off with *Remove* showing behind it, permanently (George,
  //: 2026-09-24). Any change to the queue's shape ends the gesture.
  //:
  //: Its *shape*, not the queue: the daemon republishes state while a track
  //: plays, and clearing on every one of those would cancel a swipe under
  //: the finger.
  //:
  //: **The length is not enough on its own.** The queue arrives as a window
  //: of `QUEUE_LIMIT` tracks (100, `adapters/lms.py`), so removing one from
  //: a longer queue refills the window from beyond it and the length does
  //: not move - which left the row swiped open over its *Remove* with the
  //: list shifted up behind it (George, 2026-09-24). The last row in the
  //: window is whatever just moved into it, so it changes when the length
  //: cannot.
  const shape = $derived(
    `${queue?.items?.length ?? 0}:${index}:${queue?.items?.at(-1)?.title ?? ''}`,
  );
  //: A removal made anywhere else - a phone, the server - ends a swipe
  //: here too. **This only writes `swipe`.** Reading it as well made the
  //: effect its own trigger and the panel stopped answering (George,
  //: 2026-09-24): an effect that clears state must not also be woken by it.
  $effect(() => {
    void shape;
    swipe = { key: null, dx: 0, going: false, live: false };
  });

  //: **The gesture has nothing to see**, so it is shown once: the first row
  //: that can be removed opens a little and closes again, the first time the
  //: rail is opened with something in it (ADR-0062). Once per run of the
  //: panel - a hint that repeats is a nag.
  let hinted = false;
  let hints = [];
  $effect(() => {
    if (!open || hinted || rows.length < 2) return;
    hinted = true;
    const key = keyed[1]?.key;
    if (!key) return;
    hints = [
      setTimeout(() => (swipe = { key, dx: -70, going: false, live: false }), 480),
      setTimeout(() => (swipe = { key: null, dx: 0, going: false, live: false }), 1500),
    ];
  });
  $effect(() => () => {
    hints.forEach(clearTimeout);
    clearTimeout(settle);
    clearTimeout(flipUntil);
  });
  //: The gesture in progress, which is not state: nothing draws from it,
  //: and it changes on every pointer event.
  let gesture = null;
  //: A swipe ends with a click on the row underneath. This is when the last
  //: one finished, so that click can be ignored.
  let swiped = 0;
  //: Clears a removed row whether or not the queue can show it leaving.
  let settle = null;

  //: **The rows below a removal slide up; the rest of the time they do not.**
  //: Timing the collapse against the queue's return is a race that cannot be
  //: won: the daemon now re-reads the queue itself (ADR-0071) and it comes
  //: back in about 160ms, so a 250ms collapse was cut short and the list
  //: jumped 54px in one step. Animating the *movement* instead is smooth
  //: whenever the update lands.
  //:
  //: Gated, because a windowed list moves its rows on every scroll as the
  //: spacer above them changes - and animating that would fight the scroll.
  const FLIP_MS = 200;
  let flipping = $state(false);
  let flipUntil = null;

  function closingUp() {
    clearTimeout(flipUntil);
    flipping = true;
    flipUntil = setTimeout(() => (flipping = false), 1200);
  }

  function grab(event, key) {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    gesture = { key, id: event.pointerId, x: event.clientX, y: event.clientY, decided: false };
  }

  function drag(event) {
    if (!gesture || event.pointerId !== gesture.id) return;
    const dx = event.clientX - gesture.x;
    const dy = event.clientY - gesture.y;
    if (!gesture.decided) {
      if (Math.abs(dy) > DECIDE_AT && Math.abs(dy) >= Math.abs(dx)) {
        // A scroll. Let the list have it.
        gesture = null;
        return;
      }
      if (Math.abs(dx) <= DECIDE_AT) return;
      gesture.decided = true;
      // Only now, so the list keeps the gesture when it is a scroll.
      event.currentTarget.setPointerCapture(event.pointerId);
      swipe = { key: gesture.key, dx: 0, going: false, live: true };
    }
    // Leftward only: there is nothing on the other side.
    swipe = { ...swipe, dx: Math.min(0, dx) };
  }

  async function release(at) {
    if (!gesture) return;
    const decided = gesture.decided;
    gesture = null;
    if (!decided) return;
    swiped = Date.now();
    if (-swipe.dx < REMOVE_AT) {
      swipe = { key: null, dx: 0, going: false, live: false };
      return;
    }
    // Off the edge, and then gone: the row keeps its own key, so when the
    // queue arrives without it the node is destroyed rather than handed the
    // next track. Nothing to animate back.
    const key = swipe.key;
    swipe = { ...swipe, going: true, live: false };
    closingUp();
    const ok = await queueAction(at, 'remove');
    clearTimeout(settle);
    if (!ok) {
      // Nothing changed, so nothing will clear it: put the row back rather
      // than leave it hanging open over its own Remove.
      swipe = { key: null, dx: 0, going: false, live: false };
      return;
    }
    // The queue clears this through `shape`; this is only the guarantee
    // that it clears at all if the queue never arrives.
    settle = setTimeout(() => {
      if (swipe.key === key) swipe = { key: null, dx: 0, going: false, live: false };
    }, 3000);
  }

  //: The click that ends a swipe is not a tap. 320ms covers the pointerup
  //: and the click that follows it, and nothing a person does on purpose.
  const tapped = () => Date.now() - swiped > 320;

  const mmss = (s) => {
    const whole = Math.max(0, Math.round(s ?? 0));
    return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`;
  };

  async function queueAction(at, action) {
    try {
      await libraryAction('queue', at, action);
      return true;
    } catch (err) {
      console.info('queue:', err.message);
      return false;
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

  <!-- A list, said out loud: the rows carry the swipe handlers, and a
       handler on a bare <div> has no role for anything but a mouse. -->
  <div class="rail__list" role="list" bind:this={list} use:railScroll.attach>
    <div class="qrow__space" style:height="{railWindow.above}px"></div>
    {#each railWindow.rows as { item, offset, at, key } (key)}
      <div
        class="qrow"
        role="listitem"
        class:is-now={offset === 0}
        class:is-swiping={swipe.key === key}
        class:is-dragging={swipe.key === key && swipe.live}
        class:is-going={swipe.key === key && swipe.going}
        style:--dx={swipe.key === key ? `${swipe.dx}px` : '0px'}
        onpointerdown={(event) => grab(event, key)}
        onpointermove={drag}
        onpointerup={() => release(at)}
        onpointercancel={() => release(at)}
        animate:flip={{ duration: flipping ? FLIP_MS : 0 }}
      >
        <!-- What a swipe uncovers. Behind the row, so it needs no layout of
             its own and no space in it. -->
        <span class="qrow__behind" aria-hidden="true">Remove</span>
        <button class="qrow__hit" type="button" onclick={() => tapped() && offset && queueAction(at, 'play')}>
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
        <!-- A swipe has no accessible name and nothing to focus, so the
             action keeps a control - off screen, not absent. -->
        <button class="qrow__away" type="button" aria-label="Remove {item.title ?? 'track'} from the queue"
                onclick={() => queueAction(at, 'remove')}></button>
      </div>
    {:else}
      <div class="empty">
        <div class="empty__glyph"><i></i><i></i><i></i></div>
        <div class="empty__title">Queue is empty</div>
        <div class="empty__text">Pick a playlist or add tracks from the library and they will line up here.</div>
      </div>
    {/each}
    <div class="qrow__space" style:height="{railWindow.below}px"></div>
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
    /* **No `backdrop-filter` here, on purpose.** A live blur of what is
       behind a sheet costs this panel two thirds of its frames: the
       compositor has to draw the backdrop into its own texture and read it
       back every frame, which is the one thing a tile-based GPU cannot
       absorb (Finding 037). Measured on the rail: 15 fps with it, 36
       without. The dimming itself is free - removing the scrim as well
       bought nothing. */
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
    /* **The space between rows belongs to the row**, not to the list. A
       `gap` is the list's, so a row that collapses to nothing still holds
       its gap open until the node is destroyed - which is when the queue
       comes back, about a second later. The list then settled upward by
       exactly 3px, long after the removal looked finished (George,
       2026-09-25; measured 493 -> 433 over 600ms, then 433 -> 430 at
       951ms). As a margin it collapses with the row. */
    scrollbar-width: none;
    contain: content;
    touch-action: pan-y;
  }
  .rail__list::-webkit-scrollbar {
    display: none;
  }

  .qrow {
    height: 60px;
    margin-bottom: 3px;
    flex-shrink: 0;
    /* Only the removal animates it; a row that is simply there must not
       ease into its own height when the list re-renders. */
    transition: none;
    display: flex;
    align-items: center;
    border-radius: 12px;
    padding-right: 8px;
    /* The row swipes; the list scrolls. `pan-y` gives the browser the
       vertical gesture and leaves the horizontal one to this component,
       so neither has to guess (ADR-0062). */
    touch-action: pan-y;
    position: relative;
    overflow: hidden;
  }
  .qrow.is-now {
    --now-tint: rgba(126, 214, 188, 0.14);
  }
  .qrow__hit {
    flex: 1;
    min-width: 0;
    height: 100%;
    display: flex;
    align-items: center;
    gap: 15px;
    padding: 0 14px;
    /* Opaque, so the row covers what a swipe uncovers. `--bg-panel` is the
       rail's own plate, which is also what keeps the background's blur out
       of this scroller's raster (Finding 059). */
    background: var(--bg-panel);
    border-radius: 12px;
    transform: translateX(var(--dx, 0px));
    transition: transform 190ms cubic-bezier(0.2, 0.8, 0.2, 1);
  }
  .is-now .qrow__hit {
    background: linear-gradient(var(--now-tint), var(--now-tint)), var(--bg-panel);
  }
  /* While a finger is on it there is nothing to animate towards: the row is
     wherever the finger is. With no finger - the hint - it animates. */
  .is-dragging .qrow__hit {
    transition: none;
  }
  /* **Short enough to finish before the queue comes back** (ADR-0071). The
     removed row used to be destroyed when LMS's push arrived, about 1.2s
     later, so the collapse had all the time it wanted. Now the daemon
     re-reads the queue itself and it returns in about 160ms - which cut a
     250ms collapse short and made the list jump 54px in one step instead of
     easing (George, 2026-09-25). */
  .is-going .qrow__hit {
    transform: translateX(-100%);
    transition: transform 130ms cubic-bezier(0.4, 0, 1, 1);
  }
  /* And the row closes up behind it, so the list arrives at its new shape
     before the queue does rather than jumping when it lands. */
  /* The row leaves sideways and fades; it no longer collapses its own
     height, because the list closing up is an `animate:flip` on the rows
     below and that is smooth whenever the queue returns. */
  .qrow.is-going {
    opacity: 0;
    transition: opacity 120ms linear;
    pointer-events: none;
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
  /* **Off screen, not gone** (ADR-0062). A swipe has no accessible name
     and nothing to focus; this does, and it costs no paint. */
  .qrow__away {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    padding: 0;
    border: 0;
  }
  .qrow__away:focus-visible {
    position: static;
    width: auto;
    height: 44px;
    clip-path: none;
    padding: 0 14px;
    border-radius: 11px;
    background: var(--ink-fill);
    color: var(--ink-strong);
  }

  /* What stands in for the rows that are not built (ADR-0067). */
  .qrow__space {
    flex-shrink: 0;
  }
  .qrow__behind {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 22px;
    border-radius: 12px;
    background: rgba(242, 164, 143, 0.16);
    font-family: var(--font-mono);
    font-size: var(--t-label);
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent-warm, #f2a48f);
    /* Uncovered rather than faded in: it is already there, the row is
       simply on top of it. Shown only once the gesture has committed to
       being a swipe, so a scroll never flashes it. */
    opacity: 0;
  }
  .is-swiping .qrow__behind {
    opacity: 1;
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
