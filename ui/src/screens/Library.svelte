<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The library (ADR-0038). Ported from source/Now Playing.dc.html, where the
  library is a layer over now playing: the root's five cards and the New
  Music strip, the header with Back and Home below the root, the mini strip
  while a renderer is active, and the waiting services while none is
  (ADR-0033: Home is the no-renderer screen), then the screens below the
  root - albums, artists, Browse, playlists and radio.

  Mounted only while open, and animated in and out by Svelte rather than
  left in the page at opacity 0: on the panel, the closed layer with its
  blurred backdrop kept covering now playing in black (George, 2026-09-17),
  while the idle screen, which is removed when it closes, never did.
-->
<script>
  import { tick, untrack } from 'svelte';

  import {
    foldedName,
    libraryRoot,
    loadAlbum,
    loadAlbumTracks,
    loadArtistAlbums,
    loadArtistGenres,
    loadArtistPhotos,
    loadArtistInfo,
    artistPhotos,
    artistsCached,
    playlistsCached,
    loadPlaylists,
    loadPlaylist,
    prefetchArtistPhotos,
    browseRadio,
    radioPlay,
    libraryAction,
  } from '../lib/library.js';
  import { afterPaint, revealing } from '../lib/chunks.svelte.js';
  import { inView, watchScroller } from '../lib/window.svelte.js';
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
    //: An artist name to open on arrival - now playing's artist line links
    //: here (the design's `onNpArtist`). A name rather than an id, because
    //: the panel holds no LMS ids and the artist list it already has can
    //: resolve one.
    openArtistNamed = null,
  } = $props();

  // Where in the library the panel is; [] is the root. Each entry is a
  // screen below it: `{ kind: 'album', id, label }` today.
  let path = $state([]);
  let album = $state(null);
  let artists = $state([]);
  let artist = $state(null);
  let genres = $state([]);
  let discography = $state([]);
  let busy = $state(null);

  // The design's own: initials from the first two words, and one of four
  // tints chosen by a hash of the name, so an artist keeps the same colour.
  const TINTS = [
    'rgba(126, 214, 188, 0.16)',
    'rgba(159, 180, 232, 0.18)',
    'rgba(242, 164, 143, 0.16)',
    'rgba(233, 238, 242, 0.08)',
  ];
  function initialsOf(name) {
    return (name ?? '')
      .split(/[\s\u2019']+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((word) => word[0])
      .join('')
      .toUpperCase();
  }
  function tintOf(name) {
    let h = 0;
    for (let i = 0; i < (name ?? '').length; i++) h = (h * 31 + name.charCodeAt(i)) % 997;
    return TINTS[h % TINTS.length];
  }

  //: **Long lists are built a screenful at a time** (ADR-0065). One per
  //: list, because each has its own length and its own moment of arriving.
  //: A playlist still builds a screenful at a time (ADR-0065); it paints in
  //: 104ms and is not worth windowing. The artist grid and the browse pane
  //: are windowed instead (ADR-0067).
  const playlistReveal = revealing(() => playlist?.items?.length ?? 0, () => where);

  //: **A home card says it was pressed** (George, 2026-09-24: the cards
  //: give nothing back on a tap, *"Radio has a tapping animation. The rest
  //: do not"*). Radio only looked alive because its screen is a skeleton
  //: that paints at once, where the others held the panel's last frame
  //: while the new screen was built.
  //:
  //: `:active` alone is not enough here: a quick tap can begin and end
  //: inside one frame, and the frame that would have shown it is the one
  //: spent opening the next screen. So the press is held long enough to be
  //: painted, and **the screen is opened a painted frame later** - the
  //: feedback goes out first, and the work follows it.
  const PRESS_MS = 130;
  let pressed = $state(null);
  let unpressing = null;

  function press(what) {
    clearTimeout(unpressing);
    pressed = what;
  }

  function lift() {
    clearTimeout(unpressing);
    unpressing = setTimeout(() => (pressed = null), PRESS_MS);
  }

  /** Runs `go` once the pressed frame is on the screen. */
  function opening(go) {
    afterPaint(go);
  }

  const RAIL = ['#', ...'ABCDEFGHIJKLMNOPQRSTUVWXYZ'];
  // Grouped by the letter the core folded for us (ADR-0038 §1a), keeping
  // LMS's own order within each group.
  const groups = $derived.by(() => {
    const buckets = new Map();
    for (const a of artists) {
      const letter = a.letter ?? '#';
      if (!buckets.has(letter)) buckets.set(letter, []);
      buckets.get(letter).push(a);
    }
    return RAIL.filter((l) => buckets.has(l)).map((letter) => ({
      letter,
      id: `letter-${letter === '#' ? 'num' : letter}`,
      items: buckets.get(letter),
    }));
  });
  const railLetters = $derived(
    RAIL.map((ch) => ({ ch, group: groups.find((g) => g.letter === ch) ?? null })),
  );

  //: **The grid builds only the groups on screen** (ADR-0067). 917 cards
  //: cost about 1.3ms each to create and lay out, and nothing in a card
  //: accounts for it (Finding 064) - so the grid holds one or two of its 27
  //: letter groups and a spacer stands in for the rest.
  const COLS = 6;
  //: The gap between rows of cards, and between one group and the next -
  //: `.group__cards { gap: 26px 20px }` and
  //: `.group + .group .group__head { padding-top: 26px }`.
  const ROW_GAP = 26;
  const GROUP_GAP = 26;
  //: How much beyond the window to build, so a flick has somewhere to land
  //: before the next frame catches up. One screen either side.
  const OVERSCAN = 700;

  const gridScroll = watchScroller();
  const paneScroll = watchScroller();

  //: A header's and a card's height, read from the panel rather than
  //: assumed: a card is `aspect-ratio: 1` in a six-column grid, so its
  //: height is the panel's width divided by six, less the gaps.
  let sizes = $state(null);
  //: Plain, not state: read inside the effect that sets `sizes`, and an
  //: effect that reads what it writes wakes itself (LESSONS 31).
  let measured = false;

  function measure() {
    const head = grid?.querySelector('.group__head');
    const card = grid?.querySelector('.artist');
    if (!head || !card) return;
    sizes = { head: head.offsetHeight, card: card.offsetHeight };
    measured = true;
  }

  $effect(() => {
    // Re-measured when the list changes shape, never per scroll.
    void groups.length;
    void gridScroll.view;
    if (!grid) return;
    if (!measured) afterPaint(measure);
  });

  //: Every group's top and height, without building any of them.
  const gridBlocks = $derived.by(() => {
    if (!sizes) return [];
    const out = [];
    let y = 0;
    for (const [at, group] of groups.entries()) {
      const rows = Math.ceil(group.items.length / COLS);
      const height =
        (at ? GROUP_GAP : 0) +
        sizes.head +
        rows * sizes.card +
        Math.max(0, rows - 1) * ROW_GAP;
      out.push({ top: y, height, group });
      y += height;
    }
    return out;
  });

  //: Before the first measurement there is nothing to compute with, so the
  //: grid draws **one header and two rows of cards** - enough to measure
  //: both and no more. Three whole groups was the first try, and "A" alone
  //: can be a hundred artists: it put the screen change back to 300ms from
  //: 150 (2026-09-24).
  const shownGroups = $derived.by(() => {
    if (!sizes || !gridBlocks.length) {
      const first = groups[0];
      return first ? [{ ...first, items: first.items.slice(0, COLS * 2) }] : [];
    }
    const { from, to } = inView(gridBlocks, gridScroll.top, gridScroll.view || 600, OVERSCAN);
    return gridBlocks.slice(from, to + 1).map((b) => b.group);
  });
  //: **The browse screen's artist pane, the simple case** (ADR-0067): one
  //: row height, 917 of them, a 250px window. Measured the same way, since
  //: a row's height is the design's and not this component's to know.
  let rowSize = $state(null);
  let rowMeasured = false;
  let pane = $state(null);

  function measureRow() {
    const row = pane?.querySelector('.row');
    if (!row) return;
    // **The pitch, not the height.** `.pane__list` is a flex column with a
    // 1px gap, so 917 rows are 917px taller than 917 row heights - the
    // pane computed 42,214px where the list measures 43,108 (2026-09-24).
    const gap = parseFloat(getComputedStyle(pane).rowGap) || 0;
    rowSize = row.offsetHeight + gap;
    rowMeasured = true;
  }

  $effect(() => {
    void artists.length;
    void paneScroll.view;
    if (!pane) return;
    if (!rowMeasured) afterPaint(measureRow);
  });

  const paneBlocks = $derived.by(() => {
    if (!rowSize) return [];
    return artists.map((entry, at) => ({ top: at * rowSize, height: rowSize, entry }));
  });
  const paneWindow = $derived.by(() => {
    if (!rowSize || !paneBlocks.length) {
      return { rows: artists.slice(0, 24), above: 0, below: 0 };
    }
    const { from, to, above, below } = inView(
      paneBlocks,
      paneScroll.top,
      paneScroll.view || 250,
      OVERSCAN,
    );
    return { rows: paneBlocks.slice(from, to + 1).map((b) => b.entry), above, below };
  });

  const gridSpace = $derived.by(() => {
    if (!sizes || !gridBlocks.length) return { above: 0, below: 0 };
    const { above, below } = inView(gridBlocks, gridScroll.top, gridScroll.view || 600, OVERSCAN);
    return { above, below };
  });

  let grid = $state(null);
  // Each pane's scroller, so a new selection starts at the top of the next
  // pane rather than wherever the previous list was left (George,
  // 2026-09-18).
  function jumpTo(group) {
    // **Arithmetic, not a DOM query** (ADR-0067). The group being jumped to
    // is usually not built - that is the point of windowing - so there is
    // nothing to measure. `gridBlocks` knows where it would be.
    const block = gridBlocks.find((b) => b.group.letter === group.letter);
    if (!grid || !block) return;
    grid.scrollTop = Math.max(0, block.top);
  }

  // LMS's own artist photos, where the server has the plugin (ADR-0040 §1).
  // Keyed by `<id>` for the grid and `<id>@300` for the page. A server
  // without the plugin answers null for everything and the circles keep
  // their initials, which is not a failure state.
  //: Kept in `lib/library.js`, so closing the library does not throw away
  //: every face it has already fetched (George, 2026-09-18).
  const photos = $derived($artistPhotos);
  //: What the artist page shows beside its discography.
  let artistInfo = $state({ state: 'idle', for: null, found: null, popular: [] });
  //: The biography is clamped until it is asked for, so the rest of the
  //: page is not pushed off the screen by it.
  let bioOpen = $state(false);

  //: **Fanart first, then LMS's own plugin** (George, 2026-09-18). The data
  //: already preferred fanart; the page was still reading only the plugin's
  //: photo store, so an artist the plugin has nothing for - 2Pac - showed
  //: initials next to a picture the daemon had already found.
  const artistPicture = $derived(
    artistInfo.found?.artist_image ?? photos[`${artist?.id}@300`] ?? null,
  );

  //: Hard-wrapped text with blank lines between paragraphs is what both
  //: sources give; rendered as one string the browser collapses all of it
  //: into a single blob (George, 2026-09-18).
  //: LMS's plugin hands back the whole article for some artists - 56,573
  //: characters for 2Pac. Opened in full that is a few hundred paragraphs
  //: of DOM on a panel that already drops frames (Finding 034), and nobody
  //: reads an encyclopaedia on a hi-fi. The opening is what is shown.
  const BIO_PARAGRAPHS = 12;

  //: **How much About is allowed** (George, 2026-09-18): as much as fits
  //: while the first row of albums still shows a quarter of itself. A fixed
  //: height was wrong in both directions - it hid the text on a short
  //: biography and hid the discography on a long one.
  const ALBUM_PEEK = 0.25;
  //: Never so little that About is pointless.

  let aboutEl = $state(null);
  let columnEl = $state(null);
  //: Whether there is anything under the fold. Measured in `fitAbout`.
  let bioClipped = $state(false);

  //: Tapping the text folds and unfolds it, which is what a finger reaches
  //: for. More/Less went the next day - George: *"tapping in the text works
  //: perfectly as a toggle and the bottom fade indicates that there is more
  //: to be read"* - so the fade is the only signal and is drawn only when
  //: there is something under it. The block answers the keyboard too: panel
  //: and phone take the same input.
  function foldKey(event, toggle) {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    toggle();
  }

  /** **Only the fade now** (ADR-0074). This used to measure the slack
   *  between where the first album row sat and where it should sit, and
   *  size About by it - which is what the held region does directly, and
   *  what the biography's own `flex` does inside it. What is left is the
   *  question the measurement cannot answer from geometry alone: is there
   *  more text than the box shows, and so should the fade be drawn?
   */
  function fitAbout() {
    if (!aboutEl || bioOpen) return;
    bioClipped = aboutEl.scrollHeight > aboutEl.clientHeight + 2;
    if (artistInfo.state === 'ready' && !decided) {
      // **The paragraphs' own height, not `scrollHeight`.** A box never
      // reports a scroll height smaller than itself, so a one-line
      // biography in a 400px box said it filled it - and every artist held
      // (2026-09-25). The text is what is being asked about.
      const paras = [...aboutEl.querySelectorAll('.artistmeta__para')];
      const text = paras.length
        ? paras[paras.length - 1].getBoundingClientRect().bottom -
          paras[0].getBoundingClientRect().top
        : 0;
      fills = text >= aboutEl.clientHeight - 4;
      decided = true;
    }
  }

  $effect(() => {
    // Re-measured when the page's contents change, never per frame
    // (Finding 032: nothing runs per scroll frame).
    void paragraphs;
    void releases;
    void artistInfo.popular;
    if (bioOpen) return;
    const frame = requestAnimationFrame(() => untrack(fitAbout));
    return () => cancelAnimationFrame(frame);
  });

  //: **The discography's place is held while About is still loading**
  //: (ADR-0074). The biography and Popular arrive about 1.8s after the
  //: page, and the discography was sitting at 105px until they did and at
  //: 478 afterwards - a 373px shove, measured, and the same 373 whether the
  //: artist had five popular tracks and a short life story or no popular
  //: tracks and a long one, because `fitAbout` clamps the biography to
  //: whatever is left.
  //:
  //: So the height is not guessed: it is the one `fitAbout` aims at - the
  //: first album card at `clientHeight - cardHeight * ALBUM_PEEK` - and the
  //: discography is already on the page to be measured against it.
  //: How tall the About region will be once it has something in it
  //: (ADR-0074), measured while it is still a skeleton and then kept - so
  //: the biography and Popular arrive *into* a box that is already the
  //: right size rather than growing one under the discography.
  let hold = $state(0);

  //: **Whether this artist's biography is long enough to fill the space.**
  //: Decided once, when the lookup comes back, and not revisited - the
  //: answer changes the height it was measured in, so asking twice
  //: oscillates for a biography that sits near the boundary.
  let fills = $state(false);
  //: **Held until the question has been asked.** `fills` starting false made
  //: the region compress the moment the lookup returned, and the biography
  //: was then measured against the *compressed* box - where any text fills
  //: it, so everything held (2026-09-25).
  let decided = $state(false);

  //: Held while there is something coming, and afterwards only if what came
  //: can fill it. An artist whose lookup failed, who has no biography, or
  //: whose biography is two lines long lets the page close up - George,
  //: 2026-09-25: *"in the likelihood the info doesn't come then it can
  //: compress, but that is a less likely event."* A one-line life story
  //: stretched over 400px of nothing is the same fault as a short Popular
  //: list leaving a hole.
  const holding = $derived(
    artistInfo.state === 'loading' ||
      (artistInfo.state === 'ready' && !!artistInfo.found?.biography && (!decided || fills)),
  );

  $effect(() => {
    const waiting = artistInfo.state === 'loading';
    void releases;
    void artist?.id;
    if (!waiting || !columnEl) return;
    const frame = requestAnimationFrame(() => {
      const card = columnEl?.querySelector('.disc');
      const region = columnEl?.querySelector('.artistmeta__region');
      if (!card || !region) return;
      const column = columnEl.getBoundingClientRect();
      const first = card.getBoundingClientRect();
      // The place `fitAbout` aims the first album card at.
      const want = columnEl.clientHeight - first.height * ALBUM_PEEK;
      // **The card's own top, as `fitAbout` measures it.** Measuring where
      // `.releases` starts instead counted the release heading twice and
      // left the discography 40px low (2026-09-25).
      const have = first.top - column.top + columnEl.scrollTop;
      // Written, never read here: an effect that reads what it writes wakes
      // itself (LESSONS 31).
      hold = Math.max(0, Math.round(region.getBoundingClientRect().height + want - have));
    });
    return () => cancelAnimationFrame(frame);
  });

  const paragraphs = $derived.by(() => {
    const text = artistInfo.found?.biography ?? '';
    return text
      .split(/\n\s*\n/)
      .map((block) => block.replace(/\s*\n\s*/g, ' ').trim())
      .filter(Boolean)
      .slice(0, BIO_PARAGRAPHS);
  });
  let photoQueue = new Set();
  let photoTimer = null;

  function wantPhoto(id) {
    if ($artistPhotos[id] !== undefined || photoQueue.has(id)) return;
    photoQueue.add(id);
    // Coalesced: a scroll reveals cards one at a time, and one request per
    // card would be 917 of them.
    clearTimeout(photoTimer);
    photoTimer = setTimeout(async () => {
      // Small batches on purpose: an artist the plugin has not looked up
      // costs it 500-900 ms upstream (hardware, 2026-09-18), so 20 at a
      // time appear in a few seconds where 80 would appear in forty.
      const ids = [...photoQueue].slice(0, 20);
      photoQueue = new Set([...photoQueue].slice(20));
      await loadArtistPhotos(ids);
      if (photoQueue.size) wantPhoto([...photoQueue][0]);
    }, 120);
  }

  /** Asks for a card's photo once it is on screen (or nearly).
   *
   *  **One per card, and that is not what a card costs.** Finding 064
   *  measured the grid with a single shared observer, and with none at all:
   *  both within noise of all 917. The cost is the elements, which is
   *  ADR-0067's answer, and there are now a few dozen of them. */
  function artistCard(node, id) {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) wantPhoto(id);
      },
      { root: node.closest('.grid__scroll'), rootMargin: '300px' },
    );
    observer.observe(node);
    return { destroy: () => observer.disconnect() };
  }

  async function openArtists() {
    busy = 'artists';
    try {
      artists = await artistsCached();
      // **Every portrait, before the grid wants them** (ADR-0068). Not
      // awaited: the grid opens now and fills in behind itself, where it
      // used to discover twenty at a time as cards came into view.
      prefetchArtistPhotos(artists.map((entry) => entry.id));
      path = [{ kind: 'artists', label: 'Artists' }];
    } catch (err) {
      console.info('library:', err.message);
    } finally {
      busy = null;
    }
  }

  //: Arriving from Now Playing's artist name, the page is two fetches away -
  //: the artist list, then the discography. Without this the home grid paints
  //: for that whole second and the panel looks like it went to the wrong
  //: screen and corrected itself. Initialised from the prop rather than set
  //: in the effect, because an effect runs after the first paint.
  let resolvingArtist = $state(!!openArtistNamed);

  //: **Every list opens at the top.** A scroller keeps its offset when its
  //: contents are replaced, so walking into a radio category landed halfway
  //: down a list nobody had seen, and stepping back landed somewhere else
  //: again (George, on the panel, 2026-09-21). The token is whatever
  //: identifies the page; the action resets when it changes.
  //:
  //: Reset twice - now, and after the next frame - because the rows are
  //: often still arriving when the token moves, and a scroller with no
  //: content yet has nothing to scroll.
  //: **Where a list was left**, so going into an artist and back out again
  //: lands where you were rather than at the top (George, 2026-09-25).
  //: Module-level would outlive a rescan; this lives as long as the library
  //: screen does, which is as long as the places it remembers.
  const leftAt = new Map();

  //: Saved from the scroller this component already watches, rather than a
  //: second listener on the same element.
  $effect(() => {
    const at = gridScroll.top;
    const page = where;
    if (page) leftAt.set(page, at);
  });

  //: **Coming back to the library root forgets where the lists were.**
  //: George asked for the grid to hold its place across going into an
  //: artist and out again; opening Artists afresh from the home screen is a
  //: different journey and starts at the top, where the A's are.
  $effect(() => {
    if (path.length === 0) leftAt.clear();
  });

  /** Puts a scroller back where it was, or at the top if it has not been
   *  here before. */
  function keepPlace(node, token) {
    let key = token;
    let frame;
    const put = () => {
      const at = leftAt.get(key) ?? 0;
      node.scrollTop = at;
      cancelAnimationFrame(frame);
      // A second go once the spacers have their height: the windowed grid
      // is only as tall as its arithmetic after the first frame.
      frame = requestAnimationFrame(() => (node.scrollTop = at));
    };
    put();
    return {
      update(next) {
        key = next;
        put();
      },
      destroy: () => cancelAnimationFrame(frame),
    };
  }

  function fromTop(node, _token) {
    let frame;
    const reset = () => {
      node.scrollTop = 0;
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => (node.scrollTop = 0));
    };
    reset();
    return { update: reset, destroy: () => cancelAnimationFrame(frame) };
  }

  //: What "a different page" means for the scrollers above.
  const where = $derived(path.map((p) => `${p.kind}:${p.id ?? p.handle ?? p.label}`).join('/'));

  //: The home grid is on screen - not merely "no page has been opened",
  //: which is also true while an artist page is on its way.
  const atHome = $derived(path.length === 0 && !resolvingArtist);

  /** Opens the artist page for a name, if this library has that artist. */
  async function openArtistByName(name) {
    const wanted = foldedName(name);
    if (!wanted) {
      resolvingArtist = false;
      return;
    }
    resolvingArtist = true;
    try {
      const all = await artistsCached();
      artists = all;
      const match = all.find((a) => foldedName(a.name) === wanted);
      if (match) await openArtist(match);
    } catch (err) {
      console.info('library:', err.message);
    } finally {
      resolvingArtist = false;
    }
  }

  $effect(() => {
    const name = openArtistNamed;
    if (name) untrack(() => openArtistByName(name));
  });

  //: Radio categories are read by colour and silhouette before they are read
  //: by word (design/screens.md §8), so each carries its own shape and tint.
  //: Anything LMS reports that is not here - and every station row - falls
  //: back to arcs in #8fc4d8.
  const RADIO_LOOK = {
    'Radio Now Playing': ['arcs', '#7ed6bc'],
    'My Presets': ['star', '#e0a758'],
    'Local Radio': ['pin', '#9fb4e8'],
    Music: ['note', '#f2a48f'],
    Sports: ['ball', '#7ed6bc'],
    News: ['lines', '#b0bcc4'],
    Talk: ['mic', '#c8a2d8'],
    'By Location': ['globe', '#8fc4d8'],
    'By Language': ['speech', '#9fb4e8'],
    // The design lists Rss among its shapes and assigns it no tint, so it
    // takes the fallback's - inventing one would be a colour nothing chose.
    Rss: ['rss', '#8fc4d8'],
  };
  const RADIO_FALLBACK = ['arcs', '#8fc4d8'];
  const radioLook = (label) => RADIO_LOOK[label] ?? RADIO_FALLBACK;

  /** Re-request the artist's network half. The discography is not touched:
   *  it came off the disk and an error never takes the local half away
   *  (design/screens.md §6). */
  function retryArtistInfo() {
    const entry = artist;
    if (!entry) return;
    artistInfo = { state: 'loading', for: entry.id, found: null, popular: [] };
    bioOpen = false;
    loadArtistInfo(entry.id, entry.name).then((answer) => {
      if (artistInfo.for !== entry.id) return;
      artistInfo = {
        state: answer ? 'ready' : 'error',
        for: entry.id,
        found: answer?.enrichment ?? null,
        popular: answer?.popular ?? [],
      };
    });
  }

  /** What the New Music strip leaves behind an album so Back reaches the
   *  artist, which is where the design says it goes from either route.
   *
   *  A tile carries the artist's *name*, not an id - the strip is a list of
   *  albums - so the entry records the name and `back()` resolves it. Opening
   *  the artist eagerly here would load a discography, a biography and a
   *  photo for a page nobody may visit. */
  const artistPath = (name) => (name ? [{ kind: 'artist', byName: name, label: name }] : []);

  async function openArtist(entry) {
    busy = entry.id;
    try {
      discography = await loadArtistAlbums(entry.id);
      artist = entry;
      // Genres come off the library, not the network, so they arrive with the
      // page rather than with the biography. An artist with none simply has
      // no pills - nothing is reserved for them.
      genres = [];
      loadArtistGenres(entry.id)
        .then((found) => { if (artist?.id === entry.id) genres = found ?? []; })
        .catch(() => {});
      path = [...path, { kind: 'artist', id: entry.id, label: entry.name }];
      // The page's disc is 262px, the grid's card 132px, so the page asks
      // for its own size rather than stretching the grid's thumbnail.
      if ($artistPhotos[`${entry.id}@300`] === undefined) loadArtistPhotos([entry.id], 300);
      // About and Similar artists: ADR-0038 §2 left them undrawn "until
      // Phase 8", and this is Phase 8. Fetched beside the discography
      // rather than before it, so the page arrives without waiting on a
      // biography that takes a second (Finding 035).
      artistInfo = { state: 'loading', for: entry.id, found: null, popular: [] };
      bioOpen = false;
      fills = false;
      decided = false;
      loadArtistInfo(entry.id, entry.name).then((answer) => {
        if (artistInfo.for !== entry.id) return;
        artistInfo = {
          state: answer ? 'ready' : 'error',
          for: entry.id,
          found: answer?.enrichment ?? null,
          popular: answer?.popular ?? [],
        };
      });
    } catch (err) {
      console.info('library:', err.message);
    } finally {
      busy = null;
    }
  }

  // The design groups a discography by release type; LMS's own values are
  // kept as they come (ADR-0038 §1a), and the albums are newest first, so
  // the groups follow the newest album in each.
  const releases = $derived.by(() => {
    const out = [];
    for (const album of discography) {
      const label = album.release_type ?? 'Other';
      let group = out.find((g) => g.label === label);
      if (!group) out.push((group = { label, items: [] }));
      group.items.push(album);
    }
    return out;
  });

  async function openAlbum(id, label, from = null) {
    busy = id;
    try {
      // Fetched and decoded before the screen changes, so the album page
      // arrives whole rather than filling in (George, 2026-09-17).
      album = await loadAlbum(id);
      revealed = null;
      path = [...(from ?? []), { kind: 'album', id, label }];
    } catch (err) {
      console.info('library:', err.message);
    } finally {
      busy = null;
    }
  }

  // Browse's three panes: the artist chosen, its albums, and the album's
  // tracks (design/screens.md §4).
  let chosenArtist = $state(null);
  let browseAlbums = $state([]);
  let chosenAlbum = $state(null);
  let browseTracks = $state([]);
  //: Which row has its actions showing - one at a time, as the design has it.
  let revealed = $state(null);

  let playlists = $state([]);
  let picker = $state(null); // { kind, id, label } while choosing a playlist
  let toast = $state(null);
  let toastTimer;

  function flash(message) {
    clearTimeout(toastTimer);
    toast = message;
    toastTimer = setTimeout(() => (toast = null), 2600);
  }

  let playlist = $state(null);

  // Radio: the panel holds handles the core issued and nothing else
  // (ADR-0038 §5). A folder pushes a level; a station plays.
  let radio = $state(null);

  async function openRadio(handle = null, label = 'Radio', push = true) {
    busy = handle ?? 'radio';
    try {
      const page = await browseRadio(handle);
      radio = page;
      revealed = null;
      if (!push) return;
      path = handle
        ? [...path, { kind: 'radio', handle, label }]
        : [{ kind: 'radio', handle: null, label: 'Radio' }];
    } catch (err) {
      flash(err.message);
      console.info('radio:', err.message);
    } finally {
      busy = null;
    }
  }

  async function playStation(row, action = 'play') {
    try {
      await radioPlay(row.handle, action);
      flash(action === 'play' ? `Playing ${row.label}` : `${row.label} added to the queue`);
    } catch (err) {
      flash(err.message);
      console.info('radio:', err.message);
    }
  }

  async function openPlaylists() {
    busy = 'playlists';
    try {
      playlists = await playlistsCached();
      revealed = null;
      path = [{ kind: 'playlists', label: 'Playlists' }];
    } catch (err) {
      console.info('library:', err.message);
    } finally {
      busy = null;
    }
  }

  async function openPlaylist(entry) {
    busy = entry.id;
    try {
      playlist = await loadPlaylist(entry.id);
      revealed = null;
      path = [...path, { kind: 'playlist', id: entry.id, label: entry.name }];
    } catch (err) {
      console.info('library:', err.message);
    } finally {
      busy = null;
    }
  }

  const playlistMeta = $derived.by(() => {
    if (!playlist) return '';
    const minutes = Math.round(
      (playlist.items ?? []).reduce((total, t) => total + (t.duration ?? 0), 0) / 60,
    );
    const tracks = `${playlist.count} ${playlist.count === 1 ? 'track' : 'tracks'}`;
    return minutes ? `${tracks}  ·  ${minutes} min` : tracks;
  });

  async function openBrowse() {
    busy = 'browse';
    try {
      if (!artists.length) artists = await artistsCached();
      chosenArtist = null;
      browseAlbums = [];
      chosenAlbum = null;
      browseTracks = [];
      revealed = null;
      path = [{ kind: 'browse', label: 'Browse' }];
    } catch (err) {
      console.info('library:', err.message);
    } finally {
      busy = null;
    }
  }

  async function chooseArtist(entry) {
    revealed = `artist-${entry.id}`;
    chosenArtist = entry;
    chosenAlbum = null;
    browseTracks = [];
    try {
      browseAlbums = await loadArtistAlbums(entry.id);
    } catch (err) {
      console.info('library:', err.message);
    }
  }

  async function chooseAlbum(entry) {
    revealed = `album-${entry.id}`;
    chosenAlbum = entry;
    try {
      browseTracks = (await loadAlbumTracks(entry.id)).tracks;
    } catch (err) {
      console.info('library:', err.message);
    }
  }

  async function act(kind, id, action, label, playlistId = null) {
    // Adding to a playlist is one LMS call per track - 87 tracks took 8 s
    // (measured 2026-09-18), and LMS has no bulk form - so say it is
    // working rather than letting the tap look ignored.
    if (action === 'playlist') flash(`Adding ${label}…`);
    try {
      await libraryAction(kind, id, action, playlistId);
      flash(
        action === 'play'
          ? `Playing ${label}`
          : action === 'add'
            ? `${label} added to the queue`
            : `${label} added`,
      );
    } catch (err) {
      // LMS unreachable, or a rescan took the id away: say so rather than
      // leaving the tap looking like it worked.
      flash(err.message);
      console.info('library:', err.message);
    }
  }

  const play = (kind, id, label = '') => act(kind, id, 'play', label);

  async function openPicker(kind, id, label) {
    picker = { kind, id, label };
    try {
      playlists = await loadPlaylists();
    } catch (err) {
      console.info('library:', err.message);
    }
  }

  async function addToPlaylist(playlist) {
    const target = picker;
    picker = null;
    if (!target) return;
    await act(target.kind, target.id, 'playlist', `${target.label} → ${playlist.name}`, playlist.id);
    // The chooser's counts are stale once something has been added.
    loadPlaylists()
      .then((rows) => (playlists = rows))
      .catch(() => {});
  }

  // Loaded once when the panel starts, covers and all (lib/library.js), so
  // opening Home draws the cards and the strip together.
  const counts = $derived($libraryRoot.counts);
  const albums = $derived($libraryRoot.albums);
  //: The strip under the cards, whichever of the three `home_strip` names
  //: (9h). The daemon picks the shape; this draws it.
  const strip = $derived($libraryRoot.strip);
  const stripArtists = $derived(strip?.artists ?? []);
  const stripLabel = $derived(
    strip?.shape === 'Most played artists'
      ? 'Most played'
      : strip?.shape === 'Recently played artists'
        ? 'Recently played'
        : 'New Music'
  );
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
    if (!path.length) {
      album = null;
      radio = null;
      return;
    }
    // Radio holds one level at a time, so stepping back re-reads the level
    // above from the handle that opened it.
    const top = path[path.length - 1];
    if (top.kind === 'radio') {
      // **The items go with the path, not after it.** Going forward the
      // path is pushed last, so the level on screen stays its own until
      // the new one arrives. Going back the path moves first, and the
      // items left behind are drawn against it - coming back to the nine
      // categories, the level just left rendered as cards for the length
      // of a fetch (George, on the panel, 2026-09-21).
      radio = null;
      openRadio(top.handle, top.label, false);
    }
    // An artist entry `artistPath` synthesised: the page behind it was never
    // opened, so there is nothing to fall back to. Resolve the name now.
    // `openArtistByName` pushes its own entry, so drop this placeholder.
    else if (top.kind === 'artist' && top.byName) {
      path = path.slice(0, -1);
      album = null;
      openArtistByName(top.byName);
    }
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
        <button
          class="round"
          class:is-pressed={pressed === 'lib-home'}
          type="button"
          aria-label="Home"
          onpointerdown={() => press('lib-home')}
          onpointerup={lift}
          onpointercancel={lift}
          onclick={() => opening(() => (path = []))}
        >
          <span class="i-tiles"><i></i><i></i><i></i><i></i></span>
        </button>
      {/if}
      <button
          class="round"
          class:is-pressed={pressed === 'lib-back'}
          type="button"
          aria-label="Back"
          onpointerdown={() => press('lib-back')}
          onpointerup={lift}
          onpointercancel={lift}
          onclick={() => opening(back)}
        >
        <span class="i-back"></span>
      </button>
      <div class="heading">
        <span class="heading__title">{title}</span>
        <span class="heading__crumb">{crumb}</span>
      </div>
    </div>
  {/if}

  <div class="content">
    {#if resolvingArtist && path.length === 0}
      <!-- The artist page on its way. Its own head, so the screen that
           appears is the one that was asked for. -->
      <div class="artistpage">
        <div class="artistpage__side">
          <span class="artist__disc artist__disc--big" style:background={tintOf(openArtistNamed ?? '')}>
            <span class="artist__initials artist__initials--big">{initialsOf(openArtistNamed ?? '')}</span>
          </span>
          <div>
            <div class="artistpage__name">{openArtistNamed ?? ''}</div>
            <div class="artistpage__meta">Opening…</div>
          </div>
        </div>
        <div class="artistright">
          <div class="skel"><span></span><span></span><span></span></div>
        </div>
      </div>
    {:else if atHome}
      <div class="root">
        <div class="cards">
          <button
            class="card card--browse"
            class:is-pressed={pressed === 'browse'}
            type="button"
            onpointerdown={() => press('browse')}
            onpointerup={lift}
            onpointercancel={lift}
            onclick={() => opening(openBrowse)}
          >
            <span class="glyph glyph--bars"><i style="height:26px"></i><i style="height:44px"></i><i style="height:32px"></i><i style="height:39px"></i></span>
            <span>
              <span class="card__name">Browse</span>
              <span class="card__count">{counts ? plural(counts.albums, 'album', 'albums') : ''}</span>
            </span>
          </button>

          <button
            class="card card--artists"
            class:is-pressed={pressed === 'artists'}
            type="button"
            onpointerdown={() => press('artists')}
            onpointerup={lift}
            onpointercancel={lift}
            onclick={() => opening(openArtists)}
          >
            <span class="glyph glyph--dots"><i></i><i></i><i></i></span>
            <span>
              <span class="card__name">Artists</span>
              <span class="card__count">{counts ? plural(counts.artists, 'artist', 'artists') : ''}</span>
            </span>
          </button>

          <button
            class="card card--playlists"
            class:is-pressed={pressed === 'playlists'}
            type="button"
            onpointerdown={() => press('playlists')}
            onpointerup={lift}
            onpointercancel={lift}
            onclick={() => opening(openPlaylists)}
          >
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

          <button
            class="card card--radio"
            class:is-pressed={pressed === 'radio'}
            type="button"
            onpointerdown={() => press('radio')}
            onpointerup={lift}
            onpointercancel={lift}
            onclick={() => opening(() => openRadio())}
          >
            <span class="glyph glyph--waves"><i></i><b></b><b></b></span>
            <span>
              <span class="card__name">Radio</span>
              <!-- The design's station count has no source in the radio tree
                   (ADR-0038); a missing field is not drawn. -->
              <span class="card__count"></span>
            </span>
          </button>

          <button
            class="card card--settings"
            class:is-pressed={pressed === 'settings'}
            type="button"
            onpointerdown={() => press('settings')}
            onpointerup={lift}
            onpointercancel={lift}
            onclick={() => opening(onsettings)}
          >
            <span class="glyph glyph--sliders"><i></i><b></b><i></i><b></b></span>
            <span>
              <span class="card__name">Settings</span>
              <span class="card__count">Device and sources</span>
            </span>
          </button>
        </div>

        <div class="new">
          <div class="new__head">
            <span class="new__label">{stripLabel}</span>
            <span class="new__rule"></span>
          </div>
          <!-- The mask sits on this wrapper, which does not scroll: on the
               scroller itself it is re-applied to the moving content. -->
          <div class="new__mask" style:mask-image={mask} style:-webkit-mask-image={mask}>
          <div class="new__scroll" bind:this={scroller}>
            <span class="mark" bind:this={startMark}></span>
            <!-- The same strip in two shapes: albums as large thumbnails,
                 artists as the round disc the grid already draws, captioned
                 with how many albums they have. **Not with when they last
                 played**, which the design asks for and LMS does not hold
                 (Finding 044). -->
            {#each stripArtists as who (who.id)}
              <button
                class="face"
                class:is-busy={busy === `artist-${who.id}`}
                type="button"
                onclick={() => openArtist(who)}
              >
                <span class="artist__disc face__disc" style:background={tintOf(who.name)} use:artistCard={who.id}>
                  {#if photos[who.id] && !failed.has(photos[who.id])}
                    <img
                      class="artist__photo"
                      src={photos[who.id]}
                      alt=""
                      onerror={() => markFailed(photos[who.id])}
                    />
                  {:else}
                    <span class="artist__initials">{initialsOf(who.name)}</span>
                  {/if}
                </span>
                <span class="album__title">{who.name}</span>
                <span class="album__artist">{plural(who.albums ?? 0, 'album', 'albums')}</span>
              </button>
            {/each}
            {#each albums as tile (tile.id)}
              <button
                class="album"
                class:is-busy={busy === tile.id}
                type="button"
                onclick={() => openAlbum(tile.id, tile.title, artistPath(tile.artist))}
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
    {:else if here?.kind === 'radio' && radio && here.handle === null}
      <!-- The nine top-level categories are a three-up card grid; every level
           below is the same dense single column as the rest of the library,
           because station and track lists run long (design/screens.md §8). -->
      <div class="rgrid" use:fromTop={where}>
        {#each radio.items as row (row.handle)}
          {@const look = radioLook(row.label)}
          <button
            class="rcard"
            class:is-busy={busy === row.handle}
            type="button"
            style:--tint={look[1]}
            onclick={() => (row.kind === 'folder' ? openRadio(row.handle, row.label) : playStation(row))}
          >
            <span class="rdisc rdisc--card">
              <span class="rglyph rglyph--{look[0]}"><i></i><i></i><i></i></span>
            </span>
            <!-- Name and count sit on one line, not stacked: the design puts
                 the label at `flex:1` and the meta beside it, right-aligned
                 (George, on the panel, 2026-09-21). -->
            <span class="rcard__name">{row.label}</span>
            {#if row.subtitle}
              <span class="rcard__meta">{row.subtitle}</span>
            {/if}
          </button>
        {:else}
          <div class="pane__empty">Nothing here</div>
        {/each}
      </div>
    {:else if here?.kind === 'radio' && !radio}
      <!-- Between levels: the one being left is gone, the one being
           returned to has not arrived. -->
      <div class="lists">
        {#each [1, 2, 3, 4, 5, 6] as n (n)}
          <div class="skelrow"></div>
        {/each}
      </div>
    {:else if here?.kind === 'radio' && radio}
      <div class="lists" use:fromTop={where}>
        {#each radio.items as row (row.handle)}
          {@const look = row.kind === 'station' ? RADIO_FALLBACK : radioLook(row.label)}
          <div class="plrow" class:is-busy={busy === row.handle}>
            <button
              class="plrow__hit"
              type="button"
              onclick={() => (row.kind === 'folder' ? openRadio(row.handle, row.label) : playStation(row))}
            >
              <!-- A tinted disc carrying the category's own shape, drawn in
                   CSS - no icon font, no SVG. The rows below the top level
                   get one too, at 46px; only their tint is the fallback when
                   LMS reports a category this table does not name. -->
              <span
                class="rdisc"
                style:--tint={look[1]}
              >
                <span class="rglyph rglyph--{look[0]}"><i></i><i></i><i></i></span>
              </span>
              <span class="plrow__text">
                <span class="plrow__name">{row.label}</span>
                {#if row.subtitle}
                  <span class="plrow__meta">{row.subtitle}</span>
                {/if}
              </span>
            </button>
            {#if row.kind === 'station'}
              <span class="row__actions">
                <button class="act act--play" type="button" aria-label="Play now" onclick={() => playStation(row)}><span class="act__play"></span></button>
                <button class="act" type="button" aria-label="Add to queue" onclick={() => playStation(row, 'add')}><span class="act__queue"><i></i><i></i><i></i></span></button>
              </span>
            {/if}
          </div>
        {:else}
          <div class="pane__empty">Nothing here</div>
        {/each}
      </div>
    {:else if here?.kind === 'playlists'}
      <div class="lists">
        {#each playlists as entry (entry.id)}
          <div class="plrow" class:is-busy={busy === entry.id}>
            <button class="plrow__hit" type="button" onclick={() => openPlaylist(entry)}>
              <span class="plrow__glyph"><i></i><i></i><i></i></span>
              <span class="plrow__text">
                <span class="plrow__name">{entry.name}</span>
                <span class="plrow__meta">{entry.tracks} {entry.tracks === 1 ? 'track' : 'tracks'}</span>
              </span>
            </button>
            <span class="row__actions">
              <button class="act act--play" type="button" aria-label="Play now" onclick={() => play('playlist', entry.id, entry.name)}><span class="act__play"></span></button>
              <button class="act" type="button" aria-label="Add to queue" onclick={() => act('playlist', entry.id, 'add', entry.name)}><span class="act__queue"><i></i><i></i><i></i></span></button>
              <button class="act" type="button" aria-label="Add to playlist" onclick={() => openPicker('playlist', entry.id, entry.name)}><span class="act__plus"></span></button>
            </span>
          </div>
        {:else}
          <div class="pane__empty">No playlists in the library</div>
        {/each}
      </div>
    {:else if here?.kind === 'playlist' && playlist}
      <div class="lists">
        <div class="playall__bar">
          <button class="playall playall--wide" type="button" onclick={() => play('playlist', playlist.id, playlist.name)}>
            <span class="playall__glyph"></span>
            <span class="playall__label">Play all</span>
          </button>
          <button class="shuffle" type="button" aria-label="Shuffle all" onclick={() => act('playlist', playlist.id, 'shuffle', playlist.name)}>
            <span class="i-shuffle"><i></i><i></i><b></b><b></b></span>
          </button>
          <span class="group__rule"></span>
          <span class="playall__meta">{playlistMeta}</span>
        </div>
        {#each playlist.items.slice(0, playlistReveal.shown) as entry, index (entry.id)}
          <div class="row row--wide">
            <button class="row__hit" type="button" onclick={() => (revealed = revealed === `pltrack-${index}` ? null : `pltrack-${index}`)}>
              <span class="row__num">{index + 1}</span>
              <span class="row__label">{entry.title}</span>
              <span class="row__artist">{entry.artist ?? ''}</span>
              {#if revealed !== `pltrack-${index}`}
                <span class="row__meta">{entry.duration ? mmss(entry.duration) : ''}</span>
              {/if}
            </button>
            {#if revealed === `pltrack-${index}`}
              <span class="row__actions">
                <button class="act act--play" type="button" aria-label="Play now" onclick={() => play('track', entry.id, entry.title)}><span class="act__play"></span></button>
                <button class="act" type="button" aria-label="Add to queue" onclick={() => act('track', entry.id, 'add', entry.title)}><span class="act__queue"><i></i><i></i><i></i></span></button>
                <button class="act" type="button" aria-label="Add to playlist" onclick={() => openPicker('track', entry.id, entry.title)}><span class="act__plus"></span></button>
              </span>
            {/if}
          </div>
        {/each}
      </div>
    {:else if here?.kind === 'browse'}
      <div class="browse">
        <div class="browse__top">
          <div class="pane">
            <div class="pane__head">
              <span class="pane__label">Artist</span>
              <span class="pane__count">{artists.length}</span>
            </div>
            <div
              class="pane__list"
              bind:this={pane}
              use:fromTop={where}
              use:paneScroll.attach
            >
              <div class="grid__space" style:height="{paneWindow.above}px"></div>
              {#each paneWindow.rows as entry (entry.id)}
                <div class="row" class:is-on={chosenArtist?.id === entry.id}>
                  <button class="row__hit" type="button" onclick={() => chooseArtist(entry)}>
                    <span class="row__label">{entry.name}</span>
                  </button>
                  {#if revealed === `artist-${entry.id}`}
                    <span class="row__actions">
                      <button class="act act--play" type="button" aria-label="Play now" onclick={() => play('artist', entry.id, entry.name)}><span class="act__play"></span></button>
                      <button class="act" type="button" aria-label="Add to queue" onclick={() => act('artist', entry.id, 'add', entry.name)}><span class="act__queue"><i></i><i></i><i></i></span></button>
                      <button class="act" type="button" aria-label="Add to playlist" onclick={() => openPicker('artist', entry.id, entry.name)}><span class="act__plus"></span></button>
                    </span>
                  {/if}
                </div>
              {/each}
              <div class="grid__space" style:height="{paneWindow.below}px"></div>
            </div>
          </div>

          <div class="pane">
            <div class="pane__head">
              <span class="pane__label">Album</span>
              <span class="pane__count">{browseAlbums.length}</span>
            </div>
            <div class="pane__list" use:fromTop={chosenArtist?.id ?? where}>
              {#each browseAlbums as entry (entry.id)}
                <div class="row" class:is-on={chosenAlbum?.id === entry.id}>
                  <!-- Newest first, with the year beside the title, like
                       the discography (George, 2026-09-18). -->
                  <button class="row__hit" type="button" onclick={() => chooseAlbum(entry)}>
                    <span class="row__label">
                      {entry.title}{entry.year ? ` (${entry.year})` : ''}
                    </span>
                  </button>
                  {#if revealed === `album-${entry.id}`}
                    <span class="row__actions">
                      <button class="act act--play" type="button" aria-label="Play now" onclick={() => play('album', entry.id, entry.title)}><span class="act__play"></span></button>
                      <button class="act" type="button" aria-label="Add to queue" onclick={() => act('album', entry.id, 'add', entry.title)}><span class="act__queue"><i></i><i></i><i></i></span></button>
                      <button class="act" type="button" aria-label="Add to playlist" onclick={() => openPicker('album', entry.id, entry.title)}><span class="act__plus"></span></button>
                    </span>
                  {/if}
                </div>
              {:else}
                <div class="pane__empty">{chosenArtist ? 'No albums' : 'Pick an artist'}</div>
              {/each}
            </div>
          </div>
        </div>

        <div class="pane">
          <div class="pane__head">
            <span class="pane__label">Tracks</span>
            <span class="pane__count">{browseTracks.length}</span>
          </div>
          <div class="pane__list" use:fromTop={chosenAlbum?.id ?? where}>
            {#each browseTracks as entry (entry.id)}
              <div class="row">
                <button class="row__hit" type="button" onclick={() => (revealed = revealed === `track-${entry.id}` ? null : `track-${entry.id}`)}>
                  <span class="row__num">{entry.tracknum ?? ''}</span>
                  <span class="row__label">{entry.title}</span>
                  {#if revealed !== `track-${entry.id}`}
                    <span class="row__meta">{entry.duration ? mmss(entry.duration) : ''}</span>
                  {/if}
                </button>
                {#if revealed === `track-${entry.id}`}
                  <span class="row__actions">
                    <button class="act act--play" type="button" aria-label="Play now" onclick={() => play('track', entry.id, entry.title)}><span class="act__play"></span></button>
                    <button class="act" type="button" aria-label="Add to queue" onclick={() => act('track', entry.id, 'add', entry.title)}><span class="act__queue"><i></i><i></i><i></i></span></button>
                    <button class="act" type="button" aria-label="Add to playlist" onclick={() => openPicker('track', entry.id, entry.title)}><span class="act__plus"></span></button>
                  </span>
                {/if}
              </div>
            {:else}
              <div class="pane__empty">{chosenAlbum ? 'No tracks' : 'Pick an album'}</div>
            {/each}
          </div>
        </div>
      </div>
    {:else if here?.kind === 'artists'}
      <div class="grid">
        <div
          class="grid__scroll"
          bind:this={grid}
          use:keepPlace={where}
          use:gridScroll.attach
        >
          <div class="grid__space" style:height="{gridSpace.above}px"></div>
          {#each shownGroups as group (group.letter)}
            <div class="group">
              <div class="group__head" id={group.id}>
                <span class="group__letter">{group.letter}</span>
                <span class="group__rule"></span>
                <span class="group__count">{group.items.length}</span>
              </div>
              <div class="group__cards">
                {#each group.items as entry (entry.id)}
                  <button
                    class="artist"
                    class:is-busy={busy === entry.id}
                    type="button"
                    onclick={() => openArtist(entry)}
                  >
                    <!-- LMS's plugin has a photo for most artists on
                         George's server; the initial stands in where it has
                         none, or where a server has no plugin at all
                         (ADR-0040 §1, amending ADR-0038 §2). -->
                    <span class="artist__disc" style:background={tintOf(entry.name)} use:artistCard={entry.id}>
                      {#if photos[entry.id] && !failed.has(photos[entry.id])}
                        <img
                          class="artist__photo"
                          src={photos[entry.id]}
                          alt=""
                          loading="lazy"
                          onerror={() => markFailed(photos[entry.id])}
                        />
                      {:else}
                        <span class="artist__initials">{initialsOf(entry.name)}</span>
                      {/if}
                    </span>
                    <span class="artist__name">{entry.name}</span>
                  </button>
                {/each}
              </div>
            </div>
          {/each}
          <div class="grid__space" style:height="{gridSpace.below}px"></div>
        </div>
        <div class="rail">
          {#each railLetters as letter (letter.ch)}
            <button
              class="rail__key"
              class:is-empty={!letter.group}
              type="button"
              disabled={!letter.group}
              onclick={() => letter.group && jumpTo(letter.group)}
            >{letter.ch}</button>
          {/each}
        </div>
      </div>
    {:else if here?.kind === 'artist' && artist}
      <div class="artistpage">
        <div class="artistpage__side">
          <span class="artist__disc artist__disc--big" style:background={tintOf(artist.name)}>
            {#if artistPicture && !failed.has(artistPicture)}
              <img
                class="artist__photo"
                src={artistPicture}
                alt=""
                onerror={() => markFailed(artistPicture)}
              />
            {:else}
              <span class="artist__initials artist__initials--big">{initialsOf(artist.name)}</span>
            {/if}
          </span>
          <div>
            <div class="artistpage__name">{artist.name}</div>
            {#if genres.length}
              <div class="artistpage__tags">
                {#each genres as g (g)}
                  <span class="gtag">{g}</span>
                {/each}
              </div>
            {/if}
            <div class="artistpage__meta">
              {discography.length} {discography.length === 1 ? 'album' : 'albums'}
            </div>
          </div>
          <div class="artistpage__buttons">
            <button class="playall playall--grow" type="button" onclick={() => play('artist', artist.id, artist.name)}>
              <span class="playall__glyph"></span>
              <span class="playall__label">Play</span>
            </button>
            <button class="shuffle" type="button" aria-label="Shuffle" onclick={() => act('artist', artist.id, 'shuffle', artist.name)}>
              <span class="i-shuffle"><i></i><i></i><b></b><b></b></span>
            </button>
          </div>
        </div>

        <!-- The design's right column: About, Popular, the discography,
             then Similar artists - all of it one scroller. -->
        <div class="artistright" bind:this={columnEl} use:fromTop={where}>
          <!-- **The region is held, not a gap after it** (ADR-0074). A
               spacer between About and the discography had to shrink as
               About filled, and the two were measured a frame apart - so
               the discography flicked one way and then the other. A
               `min-height` on the region itself simply does not move: what
               arrives fills it. -->
          <div
            class="artistmeta__region"
            class:is-held={holding && hold}
            style:min-height={holding && hold ? `${hold}px` : null}
          >
            <div class="sect">
              <span class="sect__label">About</span>
              <span class="sect__rule"></span>
              {#if artistInfo.state === 'loading'}
                <span class="sect__note">Loading…</span>
              {:else if artistInfo.state === 'error'}
                <span class="sect__note sect__note--offline">Offline</span>
              {/if}
            </div>
            {#if artistInfo.state === 'loading'}
              <div class="skel"><span></span><span></span><span></span></div>
            {:else if artistInfo.found?.biography}
              <!-- Clamped, so Popular and the discography are still on
                   screen under it (George, 2026-09-18). Tapping opens the
                   rest; not a nested scroller, which is what made the
                   discography move under a finger meant for the column.

                   **Clamped from the first frame it exists** (ADR-0074).
                   The clamp used to be gated on `bioClipped`, which is what
                   `fitAbout` concludes *after* measuring - so a biography
                   rendered at its full natural height, 1,500px and more,
                   until the next frame, flinging the discography down the
                   column and back. It depended on the artist before it,
                   which is why one never opened before was worse (George,
                   2026-09-25). `bioClipped` still decides the fade, which
                   is a question about the text rather than the space. -->
              <!-- No More/Less: tapping the text is the control, and the
                   fade says there is more (George, 2026-09-21). Which means
                   the fade must not appear over a biography that is already
                   whole - `bioClipped` is what keeps it honest. -->
              <div
                class="artistmeta__bio"
                class:is-clamped={!bioOpen && bioClipped}
                class:is-open={bioOpen}
                role="button"
                tabindex="0"
                aria-expanded={bioOpen}
                bind:this={aboutEl}
                onclick={() => (bioOpen = !bioOpen)}
                onkeydown={(e) => foldKey(e, () => (bioOpen = !bioOpen))}
              >
                {#each paragraphs as para, i (i)}
                  <p class="artistmeta__para">{para}</p>
                {/each}
              </div>
              <!-- The credit is the licence's term, not decoration
                   (ADR-0040 §4). -->
              <div class="artistmeta__credit">
                <span>From {artistInfo.found.biography_source}</span>
              </div>
            {:else if artistInfo.state === 'error'}
              <!-- The state was already computed and never branched on, so an
                   offline artist read "Nothing found for this artist." - which
                   says the library is empty rather than that the network is.
                   design/screens.md §6 names this as the frequent slip. -->
              <div class="offline">
                <span class="offline__text">Artist details unavailable offline. Your library is unaffected.</span>
                <button class="offline__retry" type="button" onclick={retryArtistInfo}>Retry</button>
              </div>
            {:else}
              <div class="artistmeta__none">Nothing found for this artist.</div>
            {/if}


          {#if artistInfo.popular.length}
            <div class="sect">
              <span class="sect__label">Popular</span>
              <span class="sect__rule"></span>
              <span class="sect__note">On this device</span>
            </div>
            <div class="popular">
              {#each artistInfo.popular as track, i (track.id)}
                <button class="poprow" type="button" onclick={() => play('track', track.id, track.title)}>
                  <span class="poprow__n">{i + 1}</span>
                  <span class="poprow__title">{track.title}</span>
                  {#if track.duration}<span class="poprow__dur">{mmss(track.duration)}</span>{/if}
                </button>
              {/each}
            </div>
          {/if}

          </div>

          <div class="releases">
          {#each releases as group (group.label)}
            <div class="release">
              <div class="release__head">
                <span class="release__label">{group.label}</span>
                <span class="group__rule"></span>
                <span class="release__count">{group.items.length}</span>
              </div>
              <div class="release__row">
                {#each group.items as entry (entry.id)}
                  <button
                    class="disc"
                    class:is-busy={busy === entry.id}
                    type="button"
                    onclick={() => openAlbum(entry.id, entry.title, path)}
                  >
                    <span class="disc__art">
                      {#if entry.artwork && !failed.has(entry.artwork)}
                        <img src={entry.artwork} alt="" onerror={() => markFailed(entry.artwork)} />
                      {/if}
                    </span>
                    <span class="disc__title">{entry.title ?? ''}</span>
                    <span class="disc__year">{entry.year ?? ''}</span>
                  </button>
                {/each}
              </div>
            </div>
          {/each}
          </div>

          {#if artistInfo.found?.similar?.length || artistInfo.state === 'error'}
            <div class="sect">
              <span class="sect__label">Similar artists</span>
              <span class="sect__rule"></span>
              {#if artistInfo.state === 'error'}
                <span class="sect__note sect__note--offline">Offline</span>
              {/if}
            </div>
            {#if artistInfo.state === 'error'}
              <div class="artistmeta__none">Not available offline.</div>
            {:else}
              <div class="artistmeta__similar">
                {#each artistInfo.found.similar as name (name)}
                  <span class="artistmeta__chip">{name}</span>
                {/each}
              </div>
            {/if}
          {/if}
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
          <button class="playall" type="button" onclick={() => play('album', album.id, album.title)}>
            <span class="playall__glyph"></span>
            <span class="playall__label">Play album</span>
          </button>
          <!-- The design stacks two actions full-width here; only Play album
               was built. Everywhere else in the library an album can be
               queued from its row, so the album's own page was the one place
               you could open it and not be able to. -->
          <button class="playall playall--queue" type="button" onclick={() => act('album', album.id, 'add', album.title)}>
            <span class="act__queue"><i></i><i></i><i></i></span>
            <span class="playall__label">Add to queue</span>
          </button>
        </div>

        <div class="tracks">
          <div class="tracks__head">
            <span class="tracks__label">Tracks</span>
            <span class="tracks__count">{album.tracks.length}</span>
          </div>
          <div class="tracks__list" use:fromTop={where}>
            {#each album.tracks as track (track.id)}
              <div class="track">
                <button class="track__hit" type="button" onclick={() => (revealed = revealed === `albumtrack-${track.id}` ? null : `albumtrack-${track.id}`)}>
                  <span class="track__num">{track.tracknum ?? ''}</span>
                  <span class="track__title">{track.title ?? ''}</span>
                  {#if revealed !== `albumtrack-${track.id}`}
                    <span class="track__time">{track.duration ? mmss(track.duration) : ''}</span>
                  {/if}
                </button>
                {#if revealed === `albumtrack-${track.id}`}
                  <span class="row__actions">
                    <button class="act act--play" type="button" aria-label="Play now" onclick={() => play('track', track.id, track.title)}><span class="act__play"></span></button>
                    <button class="act" type="button" aria-label="Add to queue" onclick={() => act('track', track.id, 'add', track.title)}><span class="act__queue"><i></i><i></i><i></i></span></button>
                    <button class="act" type="button" aria-label="Add to playlist" onclick={() => openPicker('track', track.id, track.title)}><span class="act__plus"></span></button>
                  </span>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      </div>
    {/if}
  </div>

  {#if picker}
    <div class="sheet__scrim" role="presentation" onclick={() => (picker = null)}></div>
    <div class="sheet">
      <div class="sheet__head">
        <div class="sheet__kicker">Add to playlist</div>
        <div class="sheet__title">{picker.label}</div>
      </div>
      <div class="sheet__list">
        <!-- Creating playlists is not supported (ADR-0038 §3), so the
             design's "New playlist" row is not drawn. -->
        {#each playlists as playlist (playlist.id)}
          <button class="sheet__row" type="button" onclick={() => addToPlaylist(playlist)}>
            <span class="sheet__name">{playlist.name}</span>
            <span class="sheet__count">{playlist.tracks}</span>
          </button>
        {:else}
          <div class="pane__empty">No playlists in the library</div>
        {/each}
      </div>
    </div>
  {/if}

  {#if toast}
    <div class="toast">{toast}</div>
  {/if}

  {#if active}
    <div class="strip">
      <MiniStrip {active} {metadata} {volume} {controls} onopen={onclose} {onvolume} />
    </div>
  {:else if atHome}
    <!-- The three renderers belong to the home screen, where "nothing is
         playing and here is what could be" is the whole message. Under a
         discography or a playlist it is a footer about something else
         (George, on the panel, 2026-09-21). -->
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
    /* Without this a button that sets no background of its own gets the
       browser's - the Popular rows came out as white blocks (George,
       2026-09-18). Every other button here happened to set one. */
    background: none;
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
  /* Held long enough to be painted (ADR-0066): a quick tap can begin and
     end inside one frame, and that frame is the one spent changing screen. */
  .round:active,
  .round.is-pressed {
    transform: scale(0.95);
    background: var(--ink-fill-press, rgba(233, 238, 242, 0.14));
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
    transition:
      transform 110ms cubic-bezier(0.2, 0.8, 0.2, 1),
      background 110ms linear,
      border-color 110ms linear;
  }
  .card:not(:disabled):active,
  .card.is-pressed {
    background: rgba(var(--card), 0.24);
    border-color: rgba(var(--card), 0.55);
    transform: scale(0.975);
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
  /* The artist shape of the strip: the grid's own disc at the album tile's
     width, so the two shapes leave the row exactly the same height. */
  .face {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
    width: 168px;
    background: none;
    border: 0;
    padding: 0;
    color: inherit;
    text-align: center;
    transition: transform var(--dur-fast) var(--ease);
  }
  .face:active {
    transform: scale(0.95);
  }
  .face__disc {
    width: 168px;
    height: 168px;
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

  /* Playlists, and one playlist's tracks: the design's list view. */
  .lists {
    flex: 1;
    min-width: 0;
    overflow-y: auto;
    padding: 28px 40px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    gap: 8px;
    scrollbar-width: none;
    contain: content;
    touch-action: pan-y;
  }
  .lists::-webkit-scrollbar {
    display: none;
  }
  .plrow {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
    border-radius: 14px;
    padding-right: 12px;
  }
  .plrow.is-busy {
    opacity: 0.6;
  }
  .plrow__hit {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px 14px;
    background: none;
  }
  .plrow__glyph {
    width: 54px;
    height: 54px;
    border-radius: 11px;
    background: rgba(242, 164, 143, 0.14);
    border: 1px solid rgba(242, 164, 143, 0.3);
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 5px;
    padding: 0 12px;
    box-sizing: border-box;
    flex-shrink: 0;
  }
  .plrow__glyph--radio {
    background: rgba(233, 238, 242, 0.055);
    border-color: rgba(233, 238, 242, 0.16);
    align-items: center;
    padding: 0;
  }
  .plrow__glyph--radio.is-station {
    background: rgba(126, 214, 188, 0.12);
    border-color: rgba(126, 214, 188, 0.3);
  }
  .i-waves {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .i-waves i {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: rgba(233, 238, 242, 0.85);
    flex-shrink: 0;
  }
  /* A mast with two arcs over it - the design's tower. */
  .i-tower {
    position: relative;
    width: 24px;
    height: 26px;
    display: block;
  }
  .i-tower::before {
    content: '';
    position: absolute;
    left: 10px;
    top: 8px;
    width: 4px;
    height: 18px;
    border-radius: 1px;
    background: var(--accent-lms);
  }
  .i-tower::after {
    content: '';
    position: absolute;
    left: 6px;
    top: 0;
    width: 12px;
    height: 12px;
    border: 2.5px solid var(--accent-lms);
    border-bottom-color: transparent;
    border-radius: 50%;
    box-sizing: border-box;
  }

  .plrow__glyph i {
    height: 3px;
    border-radius: 2px;
    background: var(--accent-artist);
  }
  .plrow__glyph i:nth-child(2) {
    background: rgba(242, 164, 143, 0.7);
    width: 70%;
  }
  .plrow__glyph i:nth-child(3) {
    background: rgba(242, 164, 143, 0.45);
    width: 85%;
  }
  .plrow__text {
    flex: 1;
    min-width: 0;
    text-align: left;
  }
  .plrow__name {
    display: block;
    font-size: 20px;
    font-weight: 700;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .plrow__meta {
    display: block;
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--ink-quiet);
    margin-top: 4px;
  }

  .playall__bar {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
    margin-bottom: 14px;
  }
  .playall--wide {
    height: 56px;
    padding: 0 26px;
    border-radius: 15px;
    flex-shrink: 0;
  }
  .row--wide {
    height: 52px;
  }
  .row__artist {
    font-size: 14px;
    color: var(--ink-quiet);
    flex-shrink: 0;
    max-width: 320px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  /* Shuffle, beside Play: the design's crossed arrows. */
  .shuffle {
    width: 62px;
    height: 56px;
    border-radius: 15px;
    background: rgba(233, 238, 242, 0.06);
    border: 1px solid rgba(233, 238, 242, 0.14);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .shuffle:active {
    transform: scale(0.95);
  }
  .i-shuffle {
    position: relative;
    width: 24px;
    height: 21px;
    display: block;
  }
  .i-shuffle i {
    position: absolute;
    left: 0;
    width: 24px;
    height: 2.5px;
    border-radius: 2px;
    background: rgba(233, 238, 242, 0.9);
  }
  .i-shuffle i:nth-child(1) {
    top: 3px;
    transform: rotate(25deg);
  }
  .i-shuffle i:nth-child(2) {
    bottom: 3px;
    transform: rotate(-25deg);
  }
  .i-shuffle b {
    position: absolute;
    right: 0;
    width: 7px;
    height: 7px;
    border-right: 2.5px solid rgba(233, 238, 242, 0.9);
  }
  .i-shuffle b:nth-of-type(1) {
    top: 0;
    border-top: 2.5px solid rgba(233, 238, 242, 0.9);
    transform: rotate(45deg);
  }
  .i-shuffle b:nth-of-type(2) {
    bottom: 0;
    border-bottom: 2.5px solid rgba(233, 238, 242, 0.9);
    transform: rotate(-45deg);
  }
  .artistpage__buttons {
    display: flex;
    gap: 9px;
    flex-shrink: 0;
  }
  .playall--grow {
    flex: 1;
  }

  .playall__meta {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--ink-quiet);
    flex-shrink: 0;
  }

  /* Browse: three panes, ported from the design's own block. */
  .browse {
    flex: 1;
    min-width: 0;
    min-height: 0;
    display: grid;
    grid-template-rows: 288px 1fr;
    gap: 12px;
    padding: 20px 30px 22px;
    box-sizing: border-box;
  }
  .browse__top {
    display: grid;
    grid-template-columns: 1fr 1.25fr;
    gap: 12px;
    min-height: 0;
  }
  .pane {
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.045);
    border: 1px solid rgba(233, 238, 242, 0.09);
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
  }
  .pane__head {
    height: 36px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 16px;
    border-bottom: 1px solid rgba(233, 238, 242, 0.08);
  }
  .pane__label,
  .pane__count {
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
  }
  .pane__label {
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: rgba(233, 238, 242, 0.5);
  }
  .pane__count {
    color: var(--ink-quiet);
    margin-left: auto;
  }
  .pane__list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 5px;
    display: flex;
    flex-direction: column;
    gap: 1px;
    scrollbar-width: none;
    /* Finding 032: nothing per scroll frame, painting kept inside. */
    contain: content;
    touch-action: pan-y;
  }
  .pane__list::-webkit-scrollbar {
    display: none;
  }
  .pane__empty {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 18px;
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--ink-quiet);
    text-align: center;
  }

  .row {
    display: flex;
    align-items: center;
    height: 46px;
    flex-shrink: 0;
    border-radius: 10px;
    padding-right: 10px;
  }
  .row.is-on {
    background: rgba(159, 180, 232, 0.14);
  }
  .row__hit {
    flex: 1;
    min-width: 0;
    height: 100%;
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 0 14px;
    background: none;
  }
  .row__num {
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--ink-quiet);
    width: 24px;
    flex-shrink: 0;
    text-align: left;
  }
  .row__label {
    flex: 1;
    min-width: 0;
    font-size: var(--t-body-sm);
    font-weight: 600;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    text-align: left;
  }
  .row__meta {
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--ink-quiet);
    flex-shrink: 0;
  }
  /* The design reveals these on the active row only, one row at a time. */
  .row__actions {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }
  .act {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    background: rgba(233, 238, 242, 0.06);
    border: 1px solid rgba(233, 238, 242, 0.14);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-sizing: border-box;
  }
  .act:active {
    transform: scale(0.95);
  }
  .act--play {
    background: rgba(126, 214, 188, 0.13);
    border-color: rgba(126, 214, 188, 0.32);
  }
  .act__play {
    width: 0;
    height: 0;
    border-left: 11px solid var(--accent-lms);
    border-top: 7px solid transparent;
    border-bottom: 7px solid transparent;
    margin-left: 2px;
  }
  .act__queue {
    width: 15px;
    height: 12px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
  .act__queue i {
    height: 2.5px;
    border-radius: 2px;
    background: rgba(233, 238, 242, 0.9);
  }
  .act__queue i:last-child {
    width: 9px;
  }
  .act__plus {
    width: 15px;
    height: 15px;
    position: relative;
  }
  .act__plus::before,
  .act__plus::after {
    content: '';
    position: absolute;
    border-radius: 2px;
    background: rgba(233, 238, 242, 0.9);
  }
  .act__plus::before {
    left: 0;
    top: 6px;
    width: 15px;
    height: 2.5px;
  }
  .act__plus::after {
    left: 6px;
    top: 0;
    width: 2.5px;
    height: 15px;
  }

  /* The design's action sheet, at its "pick a playlist" step. */
  .sheet__scrim {
    position: absolute;
    inset: 0;
    z-index: 34;
    background: var(--bg-scrim);
  }
  .sheet {
    position: absolute;
    z-index: 35;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 640px;
    background: var(--bg-panel);
    border: 1px solid rgba(126, 214, 188, 0.22);
    border-radius: 26px;
    padding: 28px 32px 30px;
    box-sizing: border-box;
    box-shadow: 0 34px 90px rgba(0, 0, 0, 0.6);
  }
  .sheet__head {
    margin-bottom: 22px;
    min-width: 0;
  }
  .sheet__kicker {
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .sheet__title {
    font-size: 25px;
    font-weight: 700;
    color: var(--ink);
    margin-top: 5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .sheet__list {
    max-height: 246px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
    scrollbar-width: none;
  }
  .sheet__list::-webkit-scrollbar {
    display: none;
  }
  .sheet__row {
    height: 62px;
    flex-shrink: 0;
    border-radius: 14px;
    background: rgba(233, 238, 242, 0.06);
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 0 22px;
  }
  .sheet__row:active {
    background: rgba(233, 238, 242, 0.16);
  }
  .sheet__name {
    flex: 1;
    min-width: 0;
    font-size: var(--t-body);
    font-weight: 600;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    text-align: left;
  }
  .sheet__count {
    font-family: var(--font-mono);
    font-size: 14px;
    color: var(--ink-quiet);
    flex-shrink: 0;
  }

  .toast {
    position: absolute;
    z-index: 33;
    left: 50%;
    bottom: 132px;
    transform: translateX(-50%);
    max-width: 700px;
    padding: 12px 22px;
    border-radius: var(--r-pill);
    background: rgba(8, 12, 16, 0.86);
    border: 1px solid var(--ink-line);
    font-size: var(--t-body-sm);
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* The artist grid, ported from the design's own block. */
  .grid {
    flex: 1;
    min-width: 0;
    display: flex;
    min-height: 0;
  }
  .grid__scroll {
    flex: 1;
    min-width: 0;
    overflow-y: auto;
    position: relative;
    padding: 24px 22px 30px 40px;
    box-sizing: border-box;
    scrollbar-width: none;
    /* Finding 032: keep the list's painting to itself, nothing per frame. */
    contain: content;
    touch-action: pan-y;
  }
  .grid__scroll::-webkit-scrollbar {
    display: none;
  }
  /* `content-visibility: auto` was tried here and taken out again: with
     the off-screen groups only estimated, the jump rail landed inside the
     previous letter, and correcting over the next frames did not converge
     (measured on the device, 2026-09-18). All 917 cards are laid out; if
     that proves too slow, the answer is rendering only the rows on screen,
     which is the deferred scrolling investigation. */
  .group__head {
    display: flex;
    align-items: center;
    gap: 14px;
    padding-bottom: 13px;
  }
  .group + .group .group__head {
    padding-top: 26px;
  }
  .group__letter {
    font-family: var(--font-mono);
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.18em;
    color: var(--accent-bluetooth);
    flex-shrink: 0;
  }
  .group__rule {
    flex: 1;
    height: 1px;
    background: var(--ink-line);
  }
  .group__count {
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
    letter-spacing: 0.1em;
    color: var(--ink-quiet);
    flex-shrink: 0;
  }
  /* What stands in for the groups that are not built (ADR-0067). */
  .grid__space {
    flex-shrink: 0;
  }
  .group__cards {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 26px 20px;
  }
  .artist {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 11px;
    min-width: 0;
    background: none;
  }
  .artist:active {
    opacity: 0.62;
  }
  .artist.is-busy {
    opacity: 0.62;
  }
  .artist__disc {
    width: 100%;
    aspect-ratio: 1;
    border-radius: 50%;
    overflow: hidden;
    position: relative;
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.14);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .artist__photo {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .artist__initials {
    font-size: 40px;
    font-weight: 700;
    letter-spacing: 0.02em;
    color: var(--ink-quiet);
  }
  .artist__name {
    width: 100%;
    min-width: 0;
    text-align: center;
    font-size: 16px;
    font-weight: 600;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .rail {
    width: 58px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: space-between;
    padding: 10px 0;
    box-sizing: border-box;
    overflow: hidden;
    border-left: 1px solid rgba(233, 238, 242, 0.07);
  }
  .rail__key {
    width: 44px;
    flex: 1 1 0;
    min-height: 0;
    max-height: 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 7px;
    background: none;
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: rgba(233, 238, 242, 0.9);
  }
  .rail__key:active {
    background: rgba(159, 180, 232, 0.24);
  }
  /* A letter with no artists stays visible but inert (design/screens.md). */
  .rail__key.is-empty {
    color: rgba(233, 238, 242, 0.22);
  }

  /* The artist page: name and discography only until Phase 8. */
  .artistpage {
    flex: 1;
    min-width: 0;
    display: flex;
    min-height: 0;
    gap: 30px;
    padding: 24px 40px 26px;
    box-sizing: border-box;
  }
  /* What the artist page draws below the buttons: the design's About and
     Similar artists blocks, filled by Phase 8's enrichment. */
  /* The design's right column on the artist page: About, Popular, the
     discography and Similar artists, scrolling together. */
  .artistright {
    flex: 1;
    min-width: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 14px;
    overflow-y: auto;
    scrollbar-width: none;
    touch-action: pan-y;
  }
  .artistright::-webkit-scrollbar { display: none; }
  /* Nothing in this column shrinks. It is a scroller, so an item that can
     shrink will: About was the only one that could, and a long biography
     with a full discography under it was squeezed to *zero* height - the
     text was there, in a box no pixels tall (George, 2026-09-18). */
  .artistright > * {
    flex-shrink: 0;
  }

  .popular {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .poprow {
    height: 46px;
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 0 12px;
    border-radius: 10px;
    flex-shrink: 0;
  }
  .poprow:active { background: var(--ink-fill-press); }
  .poprow__n {
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--ink-quiet);
    width: 16px;
    flex-shrink: 0;
  }
  .poprow__title {
    flex: 1;
    min-width: 0;
    text-align: left;
    font-size: var(--t-body-sm);
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .poprow__dur {
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--ink-quiet);
    flex-shrink: 0;
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
    animation: libSkel 1500ms ease-in-out infinite;
  }
  .skel span:nth-child(1) { width: 100%; }
  .skel span:nth-child(2) { width: 94%; animation-delay: 90ms; }
  .skel span:nth-child(3) { width: 56%; animation-delay: 180ms; }
  @keyframes libSkel {
    0%, 100% { opacity: 0.55; }
    50% { opacity: 1; }
  }
  .artistmeta__bio {
    font-size: 16px;
    line-height: 1.5;
    color: var(--ink-body);
    text-wrap: pretty;
    display: flex;
    flex-direction: column;
    gap: 10px;
    width: 100%;
  }
  /* **The biography takes whatever the region has left** (ADR-0074). The
     region is held at the height it will have, which is what stops the
     discography moving - and that left `fitAbout` nothing to measure, so an
     artist with three popular tracks instead of five got a short biography
     and a hole under it (George, 2026-09-25). Flexing, the text fills the
     space instead of the space sitting empty. */
  .artistmeta__region.is-held .artistmeta__bio:not(.is-open) {
    flex: 1 1 0;
    min-height: 64px;
    overflow: hidden;
  }
  .artistmeta__para {
    margin: 0;
  }
  /* A height, not a line clamp: `-webkit-line-clamp` needs
     `display: -webkit-box`, which takes only one block of text - with
     paragraphs inside it showed nothing at all. The fade says there is
     more without pretending to count lines. */
  .artistmeta__bio.is-clamped {
    /* The height itself is measured: see fitAbout(). */
    overflow: hidden;
    -webkit-mask-image: linear-gradient(180deg, #000 58%, transparent 100%);
    mask-image: linear-gradient(180deg, #000 58%, transparent 100%);
  }
  /* One flex item holding About and Popular, with the column's own gap
     inside it so nothing looks different (ADR-0074). */
  .artistmeta__region {
    display: flex;
    flex-direction: column;
    gap: 14px;
    flex-shrink: 0;
  }
  .artistmeta__credit {
    display: flex;
    align-items: center;
    gap: 14px;
    font-family: var(--font-mono);
    font-size: var(--t-micro);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .artistmeta__none {
    font-size: var(--t-body-sm);
    color: var(--ink-quiet);
  }
  .artistmeta__similar {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
  }
  .artistmeta__chip {
    display: inline-flex;
    align-items: center;
    height: 28px;
    padding: 0 11px;
    border-radius: 8px;
    background: rgba(159, 180, 232, 0.14);
    border: 1px solid rgba(159, 180, 232, 0.3);
    font-size: 14px;
    color: var(--accent-bluetooth);
    white-space: nowrap;
  }

  .artistpage__side {
    width: 262px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .artist__disc--big {
    width: 262px;
    height: 262px;
  }
  .artist__initials--big {
    font-size: 76px;
  }
  .artistpage__name {
    font-size: var(--t-h3);
    font-weight: 700;
    letter-spacing: -0.01em;
    color: var(--ink);
    line-height: 1.15;
    text-wrap: pretty;
  }
  .artistpage__meta {
    font-family: var(--font-mono);
    font-size: 14px;
    color: var(--ink-quiet);
    margin-top: 7px;
  }

  .releases {
    /* Inside `.artistright` now, which does the scrolling: two nested
       scrollers meant the discography moved under a finger meant for the
       column. */
    min-width: 0;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 20px;
    scrollbar-width: none;
    contain: content;
    touch-action: pan-y;
  }
  .releases::-webkit-scrollbar { display: none; }
  .release {
    display: flex;
    flex-direction: column;
    gap: 11px;
    flex-shrink: 0;
  }
  .release__head {
    display: flex;
    align-items: baseline;
    gap: 12px;
    flex-shrink: 0;
  }
  .release__label,
  .release__count {
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
    text-transform: uppercase;
    flex-shrink: 0;
  }
  .release__label {
    letter-spacing: 0.22em;
    color: var(--ink-quiet);
  }
  .release__count {
    font-size: var(--t-micro);
    letter-spacing: 0.14em;
    color: rgba(126, 214, 188, 0.78);
  }
  /* A wrapping grid, not a sideways scroller. The design is
     `repeat(auto-fill, minmax(132px, 1fr))` with an 18px/16px gap: every
     release in a group is on screen at once and the column scrolls as a
     whole, where a per-group horizontal scroller hid albums behind an edge
     and put a second scroll direction inside a vertical list. */
  .release__row {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
    gap: 18px 16px;
    contain: content;
  }
  /* The grid track sizes the tile now (min 132px, stretching to fill), so a
     fixed width would leave a ragged right edge on a 1fr column. */
  .disc {
    min-width: 0;
    background: none;
    display: block;
  }
  .disc:active,
  .disc.is-busy {
    opacity: 0.6;
  }
  .disc__art {
    display: block;
    width: 100%;
    aspect-ratio: 1;
    border-radius: 11px;
    overflow: hidden;
    position: relative;
    background: var(--bg-well);
    border: 1px solid var(--ink-line);
    box-sizing: border-box;
  }
  .disc__art img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .disc__title,
  .disc__year {
    display: block;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .disc__title {
    font-size: var(--t-meta);
    font-weight: 600;
    color: var(--ink);
    margin-top: 9px;
  }
  .disc__year {
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
    color: var(--ink-quiet);
    margin-top: 2px;
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
  /* The album page's second action. Quieter than Play album - it is the
     alternative, not the primary - so it takes the neutral ground the
     design gives a secondary button rather than the LMS accent. */
  .playall--queue {
    background: var(--ink-fill);
    border-color: var(--ink-line);
    margin-top: 10px;
  }
  .playall--queue .act__queue {
    display: flex;
    flex-direction: column;
    gap: 3px;
    flex-shrink: 0;
  }
  .playall--queue .act__queue i {
    display: block;
    width: 18px;
    height: 2px;
    border-radius: 1px;
    background: var(--accent-bluetooth);
  }
  .playall--queue .act__queue i:last-child { width: 11px; }

  /* The artist page's network-error row (design/screens.md §6). The local
     half - the discography - keeps its own kicker and its albums, because
     those came off the disk: the region blanks, never the screen. */
  .offline {
    display: flex;
    align-items: center;
    gap: 14px;
    height: 52px;
    border-radius: 14px;
    background: rgba(233, 238, 242, 0.05);
    border: 1px solid rgba(233, 238, 242, 0.12);
    padding: 0 18px;
    flex-shrink: 0;
  }
  .offline__text {
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
    border: 1px solid rgba(159, 180, 232, 0.35);
    border-radius: 9px;
    background: rgba(159, 180, 232, 0.16);
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--accent-bluetooth);
    flex-shrink: 0;
  }
  .offline__retry:active { transform: scale(0.95); }
  /* Coral, so a section that failed is legible as failed at a glance rather
     than reading as one that happens to be empty. */
  .sect__note--offline { color: var(--accent-artist); }

  /* Genre pills under the artist's name. The design wraps them at 8px and
     tints them with the LMS accent, because they come off the library rather
     than from a lookup. */
  .artistpage__tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 14px;
  }
  .gtag {
    font-size: var(--t-label);
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 6px 13px;
    border-radius: var(--r-pill);
    background: rgba(126, 214, 188, 0.14);
    border: 1px solid rgba(126, 214, 188, 0.3);
    color: var(--accent-lms);
  }


  /* ── radio: ten shapes, each in a tinted disc ──────────────────────────
     The grid is read by colour and silhouette before it is read by word
     (design/screens.md §8), so every category carries its own glyph and its
     own tint. All ten are CSS geometry - this panel has no icon font, and the
     SVG mark smears below ~40px. `--tint` comes from the markup. */
  /* The design's own container, line for line: `flex:1; min-width:0;
     overflow-y:auto; padding:28px 40px; box-sizing:border-box; display:grid;
     align-content:start`. **`flex: 1` is what was missing** - a grid with
     `flex: 0 1 auto` inside `.content`'s flex row sizes its three columns to
     their text instead of to the screen, which is what the wrong cards were.
     The padding was missing before that, out of the same attribute I had
     already read twice. */
  .rgrid {
    flex: 1;
    min-width: 0;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px;
    align-content: start;
    overflow-y: auto;
    /* The same inset every other list has. Without it the cards ran to the
       screen edge while the level below them sat 40px in, which is what
       "the layout is broken" looked like. */
    padding: 28px 40px;
    box-sizing: border-box;
    scrollbar-width: none;
    touch-action: pan-y;
  }
  .rgrid::-webkit-scrollbar { display: none; }
  .skelrow {
    flex-shrink: 0;
    height: 60px;
    border-radius: 14px;
    background: rgba(233, 238, 242, 0.05);
    animation: libSkel 1500ms ease-in-out infinite;
  }
  .skelrow:nth-child(2) { animation-delay: 90ms; }
  .skelrow:nth-child(3) { animation-delay: 180ms; }
  .skelrow:nth-child(4) { animation-delay: 270ms; }
  .skelrow:nth-child(5) { animation-delay: 360ms; }
  .skelrow:nth-child(6) { animation-delay: 450ms; }
  /* **No press feedback on a row.** The design gives none - only the
     action buttons inside one carry `style-active` - and two faults came
     of adding it (George, on the panel, 2026-09-21). A row that reveals
     its actions dimmed its own title on the way, which read as the title
     flashing. And a row that replaces the list under the finger leaves the
     *next* list's row sitting in `:active`, so tapping one radio category
     lit up a different one for as long as the finger stayed down. The
     reveal, or the new list, is the feedback. */
  .rcard {
    display: flex;
    align-items: center;
    gap: 18px;
    /* The design declares it on the row and on the disc, and there is no
       global reset here - without it the 1px border puts the card at 98px
       and the disc at 56px. */
    box-sizing: border-box;
    height: 96px;
    padding: 0 26px;
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--ink-line);
    text-align: left;
    min-width: 0;
  }
  .rcard.is-busy { opacity: 0.6; }
  .rcard .rdisc--card { margin-left: -8px; }
  .rcard__name {
    flex: 1;
    min-width: 0;
    font-size: 22px;
    font-weight: 600;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .rcard__meta {
    font-family: var(--font-mono);
    font-size: 16px;
    color: rgba(233, 238, 242, 0.62);
    flex-shrink: 0;
  }

  /* Ground at 14% of the tint, border at 30%, glyph at full strength. */
  /* A rounded square on a row, a circle on a card - the design's
     `icoRadius: rs === 'card' ? '50%' : '13px'`. */
  .rdisc {
    box-sizing: border-box;
    width: 46px;
    height: 46px;
    border-radius: 13px;
    background: color-mix(in srgb, var(--tint) 14%, transparent);
    border: 1px solid color-mix(in srgb, var(--tint) 30%, transparent);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .rdisc--card { width: 54px; height: 54px; border-radius: var(--r-circle); }

  .rglyph { display: block; position: relative; color: var(--tint); }
  .rglyph i { display: block; position: absolute; background: currentColor; }

  /* arcs - the fallback, and Radio Now Playing */
  .rglyph--arcs { width: 20px; height: 20px; }
  .rglyph--arcs i {
    left: 50%; bottom: 1px; background: none;
    border: 2px solid currentColor; border-bottom-color: transparent;
    border-left-color: transparent; border-right-color: transparent;
    border-radius: 50%; transform: translateX(-50%);
  }
  .rglyph--arcs i:nth-child(1) { width: 8px; height: 8px; }
  .rglyph--arcs i:nth-child(2) { width: 15px; height: 15px; }
  .rglyph--arcs i:nth-child(3) { width: 22px; height: 22px; }

  /* star */
  .rglyph--star { width: 20px; height: 20px; }
  .rglyph--star i:nth-child(1) {
    inset: 0; background: currentColor;
    clip-path: polygon(50% 0, 61% 35%, 98% 35%, 68% 57%, 79% 92%, 50% 70%, 21% 92%, 32% 57%, 2% 35%, 39% 35%);
  }
  .rglyph--star i:nth-child(2), .rglyph--star i:nth-child(3) { display: none; }

  /* pin */
  .rglyph--pin { width: 16px; height: 21px; }
  .rglyph--pin i:nth-child(1) {
    inset: 0 0 5px 0; border-radius: 50% 50% 50% 50% / 55% 55% 45% 45%;
  }
  .rglyph--pin i:nth-child(2) {
    left: 50%; top: 13px; width: 2px; height: 8px; transform: translateX(-50%);
  }
  .rglyph--pin i:nth-child(3) {
    left: 50%; top: 5px; width: 6px; height: 6px; border-radius: 50%;
    transform: translateX(-50%); background: var(--bg-base);
  }

  /* note */
  .rglyph--note { width: 18px; height: 20px; }
  .rglyph--note i:nth-child(1) { left: 0; bottom: 0; width: 9px; height: 7px; border-radius: 50%; }
  .rglyph--note i:nth-child(2) { left: 7px; top: 0; width: 2px; height: 16px; }
  .rglyph--note i:nth-child(3) { left: 7px; top: 0; width: 11px; height: 2px; transform: skewY(14deg); transform-origin: left; }

  /* ball */
  .rglyph--ball { width: 20px; height: 20px; }
  .rglyph--ball i:nth-child(1) {
    inset: 0; background: none; border: 2px solid currentColor; border-radius: 50%;
  }
  .rglyph--ball i:nth-child(2) { left: 50%; top: 1px; width: 2px; height: 18px; transform: translateX(-50%); }
  .rglyph--ball i:nth-child(3) { top: 50%; left: 1px; height: 2px; width: 18px; transform: translateY(-50%); }

  /* lines */
  .rglyph--lines { width: 20px; height: 16px; }
  .rglyph--lines i { left: 0; height: 2px; border-radius: 1px; }
  .rglyph--lines i:nth-child(1) { top: 0; width: 20px; }
  .rglyph--lines i:nth-child(2) { top: 7px; width: 20px; }
  .rglyph--lines i:nth-child(3) { top: 14px; width: 12px; }

  /* mic */
  .rglyph--mic { width: 16px; height: 21px; }
  .rglyph--mic i:nth-child(1) { left: 4px; top: 0; width: 8px; height: 12px; border-radius: 4px; }
  .rglyph--mic i:nth-child(2) {
    left: 1px; top: 9px; width: 14px; height: 7px; background: none;
    border: 2px solid currentColor; border-top-color: transparent;
    border-radius: 0 0 8px 8px;
  }
  .rglyph--mic i:nth-child(3) { left: 50%; bottom: 0; width: 2px; height: 4px; transform: translateX(-50%); }

  /* globe */
  .rglyph--globe { width: 20px; height: 20px; }
  .rglyph--globe i:nth-child(1) { inset: 0; background: none; border: 2px solid currentColor; border-radius: 50%; }
  .rglyph--globe i:nth-child(2) { top: 50%; left: 0; width: 20px; height: 2px; transform: translateY(-50%); }
  .rglyph--globe i:nth-child(3) {
    left: 50%; top: 0; width: 10px; height: 20px; background: none;
    border: 2px solid currentColor; border-radius: 50%; transform: translateX(-50%);
  }

  /* speech */
  .rglyph--speech { width: 20px; height: 18px; }
  .rglyph--speech i:nth-child(1) {
    left: 0; top: 0; width: 20px; height: 14px; background: none;
    border: 2px solid currentColor; border-radius: 6px;
  }
  .rglyph--speech i:nth-child(2) {
    left: 4px; bottom: 0; width: 6px; height: 6px;
    clip-path: polygon(0 0, 100% 0, 0 100%);
  }
  .rglyph--speech i:nth-child(3) { display: none; }

  /* rss - for the feed categories LMS may report */
  .rglyph--rss { width: 18px; height: 18px; }
  .rglyph--rss i:nth-child(1) { left: 0; bottom: 0; width: 5px; height: 5px; border-radius: 50%; }
  .rglyph--rss i:nth-child(2) {
    left: 0; bottom: 0; width: 11px; height: 11px; background: none;
    border: 2px solid currentColor; border-radius: 0 0 0 100%;
    border-top-color: transparent; border-right-color: transparent;
    transform: rotate(-90deg); transform-origin: left bottom;
  }
  .rglyph--rss i:nth-child(3) {
    left: 0; bottom: 0; width: 17px; height: 17px; background: none;
    border: 2px solid currentColor; border-radius: 0 0 0 100%;
    border-top-color: transparent; border-right-color: transparent;
    transform: rotate(-90deg); transform-origin: left bottom;
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
    padding-right: 10px;
    border-radius: 10px;
  }
  /* The row is the hit target; the actions sit beside it when revealed, as
     on every other track list. */
  .track__hit {
    flex: 1;
    min-width: 0;
    height: 100%;
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 0 16px;
    background: none;
  }
  .track__num {
    font-family: var(--font-mono);
    font-size: var(--t-meta);
    color: rgba(233, 238, 242, 0.62);
    width: 26px;
    flex-shrink: 0;
    text-align: left;
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
    text-align: left;
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
