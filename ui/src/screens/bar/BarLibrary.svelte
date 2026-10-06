<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The library on a bar (ADR-0109, Bar family): 400 logical px tall and
  1200-2000 wide. App.svelte mounts it in place of Library.svelte on a bar,
  with the same props, and it keeps Library's data, paths and actions - only
  the drawing is the bar's.

  From Claude Design's 13b handoff (`design/BUNDLE-README.md`), round 2
  winning over round 1:
  - `design/source/13b/Bar Frame.dc.html` (variant home2, layout c): the
    home's six cards and the 124 px rail (BarRail.svelte);
  - `Bar Library.dc.html`: Browse, Artists, New Music, Playlists, Radio, the
    artist page (`artist2`) and the album page (`album2`), Settings;
  - `Bar States.dc.html`: the rail with nothing playing, the Artists jump
    strip, a playlist's tracks, radio folders and stations in one grid, the
    toast and a sheet on a bar.

  **What a bar drops is dropped by design** (ADR-0109 decision 7, George
  2026-09-30): the biography, Popular, similar artists and the artist's tags.
  Round 2's artist page still drew *Top tracks* and tags; neither is drawn
  here.

  **Per-row actions are the panel's** (George, 2026-10-01, revising decision
  7's per-row part): a tap on a row reveals Play now, Add to queue and Add to
  playlist, one row at a time, as Library.svelte does - Browse's artist,
  album and track rows, the album page's tracks and a playlist's tracks. Add
  to playlist opens Library.svelte's playlist picker, drawn as a bar's sheet.
-->
<script>
  import RadioGlyph from '../../lib/RadioGlyph.svelte';
  import { untrack } from 'svelte';

  import {
    foldedName,
    libraryRoot,
    loadAlbum,
    loadAlbumTracks,
    loadArtistAlbums,
    loadArtistPhotos,
    loadArtistInfo,
    artistPhotos,
    artistsCached,
    playlistsCached,
    loadPlaylist,
    prefetchArtistPhotos,
    browseRadio,
    radioPlay,
    libraryAction,
    loadPlaylists,
  } from '../../lib/library.js';
  import { afterPaint, revealing } from '../../lib/chunks.svelte.js';
  import { screen } from '../../lib/family.svelte.js';
  import Settings from '../Settings.svelte';
  import BarRail from './BarRail.svelte';
  import JumpStrip from './JumpStrip.svelte';
  import Glyph from '../../lib/Glyph.svelte';
  import { settingValues } from '../../lib/settings.js';
  import { menuTiles, loadMenuTiles, browseMenu, menuAct, menuLetters as menuLetters_ } from '../../lib/menus.js';
  import { MY_MUSIC, levelLayout } from '../../lib/lyrionLooks.js';
  import LyrionLevel from '../LyrionLevel.svelte';
  import LyrionSearch from '../LyrionSearch.svelte';
  import { dragScroll, watchSideways, edgeMask } from './sideways.svelte.js';

  // Library.svelte's props, so App can hand either screen the same set.
  // `volume`, `availability`, `onvolume` and `onsettings` are the panel's:
  // on a bar the tray carries the volume, the rail stands where the waiting
  // services stood, and Settings opens in the content area.
  let {
    active,
    metadata,
    volume = null,
    controls = [],
    availability = {},
    onclose,
    onsettings = null,
    onvolume = null,
    openArtistNamed = null,
  } = $props();

  // ---- where the library is ------------------------------------------------
  //: Library.svelte's path: [] is the home, each entry a screen below it.
  //: Two kinds are the bar's own: `new` (the home strip, which is a card
  //: here) and `settings`.
  let path = $state([]);
  let album = $state(null);
  let artists = $state([]);
  let artist = $state(null);
  let discography = $state([]);
  let busy = $state(null);

  const here = $derived(path.length ? path[path.length - 1] : null);
  const where = $derived(path.map((p) => `${p.kind}:${p.id ?? p.handle ?? p.label}`).join('/'));
  //: Navigation clears a revealed row (Library.svelte clears it in each
  //: opener; here every change of page does, Back and Home included).
  $effect(() => {
    where;
    untrack(() => (revealed = null));
  });

  //: Library.svelte's: arriving from Now Playing's artist name is two
  //: fetches away, and the home must not paint in between.
  let resolvingArtist = $state(untrack(() => !!openArtistNamed));
  const atHome = $derived(path.length === 0 && !resolvingArtist);

  // ---- the width's own rules -------------------------------------------------
  const W = $derived(screen.width);
  //: Round 2, *Ends*: a home card under 190 px wide steps its type down -
  //: (W - 124 rail - 72 padding - 100 gaps) / 6 < 190, so below 1436.
  const narrow = $derived((W - 296) / 6 < 190);
  //: Bar States' radio grid: two columns, three above 1500.
  const radioCols = $derived(W > 1500 ? 3 : 2);

  // ---- the design's initials and tints (Library.svelte) ----------------------
  const TINTS = [
    'rgba(126, 214, 188, 0.16)',
    'rgba(159, 180, 232, 0.18)',
    'rgba(242, 164, 143, 0.16)',
    'rgba(233, 238, 242, 0.08)',
  ];
  function initialsOf(name) {
    return (name ?? '')
      .split(/[\s’']+/)
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
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  const mmss = (s) => {
    const whole = Math.max(0, Math.round(s ?? 0));
    return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`;
  };
  const minutesOf = (tracks) =>
    Math.round((tracks ?? []).reduce((total, t) => total + (t.duration ?? 0), 0) / 60);

  // ---- a press that is painted before the work (ADR-0066) ------------------
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
  const opening = (go) => afterPaint(go);

  // ---- photos ------------------------------------------------------------
  const photos = $derived($artistPhotos);
  let failed = $state(new Set());
  const markFailed = (url) => (failed = new Set(failed).add(url));

  //: Only the picture is taken from the artist lookup: fanart first, then
  //: LMS's plugin, as on the panel (Library.svelte, George 2026-09-18). The
  //: biography, Popular and similar artists it also carries are not drawn
  //: on a bar.
  let artistImage = $state({ for: null, url: null });
  const artistPicture = $derived(
    (artistImage.for === artist?.id ? artistImage.url : null) ?? photos[`${artist?.id}@600`] ?? null,
  );

  // ---- toasts --------------------------------------------------------------
  let toast = $state(null);
  let toastTimer;
  function flash(message) {
    clearTimeout(toastTimer);
    toast = message;
    toastTimer = setTimeout(() => (toast = null), 2600);
  }

  async function act(kind, id, action, label, playlistId = null) {
    // Library.svelte's: adding to a playlist is one LMS call per track (87
    // tracks took 8 s, 2026-09-18), so say it is working.
    if (action === 'playlist') flash(`Adding ${label}…`);
    try {
      await libraryAction(kind, id, action, playlistId);
      flash(action === 'play' ? `Playing ${label}` : action === 'add' ? `${label} added to the queue` : `${label} added`);
    } catch (err) {
      // LMS unreachable, or a rescan took the id away (Library.svelte).
      flash(err.message);
      console.info('library:', err.message);
    }
  }
  const play = (kind, id, label = '') => act(kind, id, 'play', label);

  // ---- a row's actions, and the playlist picker (Library.svelte) ------------
  //: Which row has its actions showing - one at a time, as on the panel.
  let revealed = $state(null);
  const toggle = (key) => (revealed = revealed === key ? null : key);
  let picker = $state(null); // { kind, id, label } while choosing a playlist

  async function openPicker(kind, id, label) {
    picker = { kind, id, label };
    try {
      playlists = await loadPlaylists();
    } catch (err) {
      console.info('library:', err.message);
    }
  }

  async function addToPlaylist(entry) {
    const target = picker;
    picker = null;
    if (!target) return;
    await act(target.kind, target.id, 'playlist', `${target.label} → ${entry.name}`, entry.id);
    // The chooser's counts are stale once something has been added.
    loadPlaylists()
      .then((rows) => (playlists = rows))
      .catch(() => {});
  }

  const isPlaying = (track) => active === 'lms' && metadata?.track_id != null && String(track.id) === String(metadata.track_id);

  // ---- artists ---------------------------------------------------------------
  async function openArtists() {
    busy = 'artists';
    try {
      artists = await artistsCached();
      prefetchArtistPhotos(artists.map((entry) => entry.id));
      path = [{ kind: 'artists', label: 'Album Artists' }];
    } catch (err) {
      console.info('library:', err.message);
    } finally {
      busy = null;
    }
  }

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

  //: Library.svelte's: an album opened from the home strip carries its
  //: artist's name so Back reaches the artist.
  const artistPath = (name) => (name ? [{ kind: 'artist', byName: name, label: name }] : []);

  async function openArtist(entry) {
    busy = entry.id;
    try {
      discography = await loadArtistAlbums(entry.id);
      artist = entry;
      path = [...path, { kind: 'artist', id: entry.id, label: entry.name }];
      if ($artistPhotos[`${entry.id}@600`] === undefined) loadArtistPhotos([entry.id], 600);
      artistImage = { for: entry.id, url: null };
      loadArtistInfo(entry.id, entry.name).then((answer) => {
        if (artistImage.for !== entry.id) return;
        artistImage = { for: entry.id, url: answer?.enrichment?.artist_image ?? null };
      });
    } catch (err) {
      console.info('library:', err.message);
    } finally {
      busy = null;
    }
  }

  async function openAlbum(id, label, from = null) {
    busy = id;
    try {
      album = await loadAlbum(id);
      path = [...(from ?? []), { kind: 'album', id, label }];
    } catch (err) {
      console.info('library:', err.message);
    } finally {
      busy = null;
    }
  }

  // ---- browse --------------------------------------------------------------
  let chosenArtist = $state(null);
  let browseAlbums = $state([]);
  let chosenAlbum = $state(null);
  let browseTracks = $state([]);

  async function openBrowse() {
    busy = 'browse';
    try {
      if (!artists.length) artists = await artistsCached();
      chosenArtist = null;
      browseAlbums = [];
      chosenAlbum = null;
      browseTracks = [];
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

  //: **The artist pane builds only the rows on screen** (ADR-0067): 917 of
  //: them at the design's 52 px and 2 px gap, a 54 px pitch.
  const ROW = 54;
  const OVERSCAN = 400;
  let paneTop = $state(0);
  let paneView = $state(260);
  function watchPane(node) {
    let frame = null;
    const read = () => {
      frame = null;
      paneTop = node.scrollTop;
      paneView = node.clientHeight;
    };
    read();
    const onScroll = () => {
      if (frame === null) frame = requestAnimationFrame(read);
    };
    node.addEventListener('scroll', onScroll, { passive: true });
    return {
      destroy() {
        node.removeEventListener('scroll', onScroll);
        if (frame !== null) cancelAnimationFrame(frame);
      },
    };
  }
  const paneWindow = $derived.by(() => {
    const from = Math.max(0, Math.floor((paneTop - OVERSCAN) / ROW));
    const to = Math.min(artists.length, Math.ceil((paneTop + paneView + OVERSCAN) / ROW));
    return {
      rows: artists.slice(from, to),
      above: from * ROW,
      below: Math.max(0, (artists.length - to) * ROW),
    };
  });

  // ---- playlists -------------------------------------------------------------
  let playlists = $state([]);
  let playlist = $state(null);

  async function openPlaylists() {
    busy = 'playlists';
    try {
      playlists = await playlistsCached();
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
      path = [...path, { kind: 'playlist', id: entry.id, label: entry.name }];
    } catch (err) {
      console.info('library:', err.message);
    } finally {
      busy = null;
    }
  }

  //: A playlist builds a screenful at a time (ADR-0065), as on the panel.
  const playlistReveal = revealing(() => playlist?.items?.length ?? 0, () => where);

  const playlistMeta = $derived.by(() => {
    if (!playlist) return '';
    const minutes = minutesOf(playlist.items);
    const tracks = plural(playlist.count, 'track', 'tracks');
    return minutes ? `${tracks} · ${minutes} min` : tracks;
  });

  // ---- radio ---------------------------------------------------------------
  //: The panel holds handles the core issued and nothing else (ADR-0038 §5).
  let radio = $state(null);

  async function openRadio(handle = null, label = 'Radio', push = true) {
    busy = handle ?? 'radio';
    try {
      const page = await browseRadio(handle);
      radio = page;
      if (!push) return;
      path = handle ? [...path, { kind: 'radio', handle, label }] : [{ kind: 'radio', handle: null, label: 'Radio' }];
    } catch (err) {
      flash(err.message);
      console.info('radio:', err.message);
    } finally {
      busy = null;
    }
  }

  async function playStation(row) {
    try {
      await radioPlay(row.handle, 'play');
      flash(`Playing ${row.label}`);
    } catch (err) {
      flash(err.message);
      console.info('radio:', err.message);
    }
  }

  //: The radio's crumb: the levels above this one, as Bar States draws it
  //: ("Radio · By location"); at the top, what the level holds.
  const radioCrumb = $derived.by(() => {
    if (!radio || here?.kind !== 'radio') return '';
    if (here.handle !== null) {
      return path
        .slice(0, -1)
        .filter((p) => p.kind === 'radio')
        .map((p) => p.label)
        .join(' · ');
    }
    const items = radio.items ?? [];
    const stations = items.filter((r) => r.kind === 'station').length;
    return stations === items.length ? plural(stations, 'station', 'stations') : plural(items.length, 'category', 'categories');
  });

  // ---- the home strip, which is a card on a bar ----------------------------
  const counts = $derived($libraryRoot.counts);
  const albums = $derived($libraryRoot.albums);
  const strip = $derived($libraryRoot.strip);
  const stripArtists = $derived(strip?.artists ?? []);
  //: Named by `home_strip`, as the panel's strip heading is.
  const stripLabel = $derived(
    strip?.shape === 'Most played artists'
      ? 'Most played'
      : strip?.shape === 'Recently played artists'
        ? 'Recently played'
        : 'New Music',
  );
  const openNew = () => (path = [{ kind: 'new', label: stripLabel }]);


  // ---- ADR-0118: Lyrion's own menus, behind Extended navigation ---------------
  //: Library.svelte's, drawn the bar's way: LyrionLevel and LyrionSearch in
  //: their bar mode, the title and Play all in the head column, the letter
  //: strip at the content's foot (the handover's §Frame — Bar).
  $effect(() => {
    if ($settingValues.lms_extended_nav === true) loadMenuTiles();
    else menuTiles.set([]);
  });
  const tileFor = (key) => $menuTiles.find((t) => t.key === key) ?? null;
  //: A category an app adds sits just before Apps (ADR-0118 A).
  const otherTiles = $derived($menuTiles.filter((t) => t.key === 'other'));

  let menu = $state(null);
  let menuFailed = $state(null);
  let menuLetters = $state({});
  let menuMore = false;
  //: The 1850 layout (1480 x 320 shown at 0.8).
  const wide = $derived(W > 1500);

  function ctxFor(row, parent = {}) {
    const mine = row?.id && MY_MUSIC[row.id];
    const app = row?.hint === 'app';
    return {
      from: row?.handle ? row : null,
      opens: mine ? mine[3] : null,
      appTop: app,
      app: app ? row.label : parent.app ?? null,
      appLogo: app ? row.image : parent.appLogo ?? null,
    };
  }

  async function openMenu(handle, label, push = true, ctx = {}) {
    if (push) path = [...path, { kind: 'menu', handle, label, ctx }];
    const level = path[path.length - 1];
    menu = null;
    menuFailed = null;
    menuLetters = {};
    try {
      const got = await browseMenu(handle);
      if (path[path.length - 1] !== level) return;
      menu = { ...got, handle };
      // The strip, for lists Lyrion files by letter (the handover's note 6).
      const lettered = got.items.filter((r) => ['artist', 'genre', 'album'].includes(r.hint)).length;
      if (got.count > 30 && lettered >= got.items.length * 0.6) {
        // Pending (null): the rail or strip takes its place at once, so the
        // list does not move when the index arrives (George, 2026-10-06).
        menuLetters = null;
        menuLetters_(handle)
          .then((body) => { if (path[path.length - 1] === level) menuLetters = body.letters ?? {}; })
          .catch(() => { if (path[path.length - 1] === level) menuLetters = {}; });
      }
    } catch (err) {
      if (path[path.length - 1] === level) menuFailed = err.message;
      console.info('menus:', err.message);
    }
  }

  function openMenuTile(tile) {
    path = [];
    openMenu(tile.handle, tile.key === 'apps' ? 'Apps' : tile.label, true, {
      apps: tile.key === 'apps',
      favourites: tile.key === 'favorites',
    });
  }

  async function openMenuRow(row) {
    // My Music's Search is the field itself, running its five searches
    // together (the handover's note 4).
    if (row.id === 'myMusicSearch') {
      try {
        const got = await browseMenu(row.handle);
        const rows = got.items.filter((r) => r.kind === 'search');
        path = [...path, { kind: 'menusearch', label: row.label, rows, ctx: here?.ctx ?? {} }];
      } catch (err) {
        flash(err.message);
      }
      return;
    }
    openMenu(row.handle, row.label, true, ctxFor(row, here?.ctx ?? {}));
  }

  function openSearchEntry(row) {
    path = [...path, { kind: 'menusearch', label: row.label, rows: [row], ctx: here?.ctx ?? {} }];
  }

  async function moreMenu() {
    if (!menu || menuMore || (menu.start ?? 0) + menu.items.length >= menu.count) return;
    menuMore = true;
    const showing = menu;
    try {
      const next = await browseMenu(showing.handle, (showing.start ?? 0) + showing.items.length);
      if (menu === showing) menu = { ...showing, items: [...showing.items, ...next.items] };
    } catch (err) {
      console.info('menus:', err.message);
    } finally {
      menuMore = false;
    }
  }

  async function earlierMenu() {
    if (!menu || menuMore || !(menu.start > 0)) return;
    menuMore = true;
    const showing = menu;
    const from = Math.max(0, showing.start - 100);
    try {
      const prev = await browseMenu(showing.handle, from, showing.start - from);
      if (menu === showing) menu = { ...showing, start: from, items: [...prev.items, ...showing.items] };
    } catch (err) {
      console.info('menus:', err.message);
    } finally {
      menuMore = false;
    }
  }

  async function jumpMenu(letter, position) {
    if (!menu || position == null) return;
    const showing = menu;
    try {
      const got = await browseMenu(showing.handle, position);
      if (menu === showing) menu = { ...showing, start: position, items: got.items };
    } catch (err) {
      console.info('menus:', err.message);
    }
  }

  async function doMenu(row, action) {
    try {
      await menuAct(row.handle, action);
      flash(action === 'play' ? `Playing ${row.label}` : action === 'next' ? `${row.label} plays next` : `${row.label} added to the queue`);
    } catch (err) {
      flash(err.message);
      console.info('menus:', err.message);
    }
  }

  //: The search field, typed on the phone; on a bar it is the content's.
  let searchText = $state('');
  $effect(() => {
    here;
    untrack(() => (searchText = ''));
  });

  //: Play all in the head column, for the lists that play whole (the
  //: handover's §6: "Play all and Shuffle sit in the head column").
  const menuLayout = $derived(here?.kind === 'menu' ? levelLayout(menu, here.ctx ?? {}, { loading: !menu && !menuFailed, failed: menuFailed }) : null);
  const playAllLabel = $derived(
    !['tracks', 'folder'].includes(menuLayout) || !here?.ctx?.from?.can?.includes('play')
      ? null
      : menuLayout === 'folder' && (here.ctx.from.hint === 'folder' || here.ctx.opens === 'folder') ? 'Play folder' : 'Play all',
  );

  const MENU_NOUNS = { artist: 'artists', album: 'albums', genre: 'genres', year: 'years', work: 'works' };
  const fmtCount = (n) => Number(n).toLocaleString('en-GB');
  //: Library.svelte's crumb: where the level was opened from, and how many.
  const menuCrumb = $derived.by(() => {
    if (here?.kind === 'menusearch') return path.length > 1 ? path[path.length - 2].label : '';
    if (here?.kind !== 'menu') return null;
    const parent = path.length > 1 ? path[path.length - 2].label : '';
    if (!menu) return [parent, menuFailed ? '' : 'Loading…'].filter(Boolean).join(' · ');
    const one = (n, noun) => `${fmtCount(n)} ${n === 1 ? noun.replace(/s$/, '') : noun}`;
    if (menu.node) return one(menu.count, 'views');
    if (menu.items.every((r) => r.kind === 'text')) return parent;
    const hint = menu.items.find((r) => r.hint)?.hint;
    const tracks = menu.items.some((r) => r.kind === 'play' && r.subtitle) || here.ctx?.from?.kind === 'container';
    const noun = here.ctx?.apps ? 'apps' : MENU_NOUNS[hint] ?? (tracks ? 'tracks' : 'items');
    const whole = menu.items.length >= menu.count;
    const shown = menu.items.filter((r) => (tracks ? r.kind === 'play' : r.kind !== 'text'));
    const n = !shown.some((r) => r.label) ? 0 : whole ? shown.length : menu.count;
    if (!n) return parent;
    return [parent, one(n, noun)].filter(Boolean).join(' · ');
  });

  // ---- settings, in the content area ---------------------------------------
  const openSettingsHere = () => (path = [{ kind: 'settings', label: 'Settings' }]);

  // ---- back ----------------------------------------------------------------
  function back() {
    if (!path.length) {
      onclose?.();
      return;
    }
    path = path.slice(0, -1);
    if (!path.length) {
      album = null;
      radio = null;
      menu = null;
      return;
    }
    const top = path[path.length - 1];
    if (top.kind === 'menu') {
      // As Radio: the level above is read again from its handle.
      openMenu(top.handle, top.label, false, top.ctx);
      return;
    }
    if (top.kind === 'menusearch') return;
    if (top.kind === 'radio') {
      radio = null;
      openRadio(top.handle, top.label, false);
    } else if (top.kind === 'artist' && top.byName) {
      path = path.slice(0, -1);
      album = null;
      openArtistByName(top.byName);
    }
  }
  const home = () => (path = []);

  // ---- the left column -------------------------------------------------------
  const title = $derived(here?.kind === 'playlist' ? (playlist?.name ?? here.label) : (here?.label ?? ''));
  const crumb = $derived.by(() => {
    switch (here?.kind) {
      case 'browse':
        return counts ? plural(counts.albums, 'album', 'albums') : '';
      case 'artists':
        return plural(artists.length, 'artist', 'artists');
      case 'playlists':
        return plural(playlists.length, 'playlist', 'playlists');
      case 'playlist':
        return playlistMeta;
      case 'new':
        return stripArtists.length ? plural(stripArtists.length, 'artist', 'artists') : plural(albums.length, 'album', 'albums');
      case 'radio':
        return radioCrumb;
      case 'menu':
      case 'menusearch':
        return menuCrumb ?? '';
      default:
        return '';
    }
  });
  //: The artist and album pages have the photo or cover in its place, and
  //: Settings brings its own head.
  const hero = $derived(
    (resolvingArtist && path.length === 0) ||
      (here?.kind === 'artist' && !!artist) ||
      (here?.kind === 'album' && !!album),
  );
  const column = $derived(!!here && !hero && here.kind !== 'settings');

  // ---- sideways lists --------------------------------------------------------
  const side = watchSideways();
  const mask = $derived(edgeMask(side.moreBefore, side.moreAfter));

  //: **Where a list was left**, so going into an artist and back lands where
  //: you were (Library.svelte, George 2026-09-25); forgotten at the home.
  const leftAt = new Map();
  $effect(() => {
    const at = side.left;
    const page = untrack(() => where);
    if (page) leftAt.set(page, at);
  });
  $effect(() => {
    if (path.length === 0) leftAt.clear();
  });
  function keepPlace(node, token) {
    let frame;
    const put = (key) => {
      const at = leftAt.get(key) ?? 0;
      node.scrollLeft = at;
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => (node.scrollLeft = at));
    };
    put(token);
    return {
      update: put,
      destroy: () => cancelAnimationFrame(frame),
    };
  }
  function fromTop(node, _token) {
    let frame;
    const reset = () => {
      node.scrollTop = 0;
      node.scrollLeft = 0;
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        node.scrollTop = 0;
        node.scrollLeft = 0;
      });
    };
    reset();
    return { update: reset, destroy: () => cancelAnimationFrame(frame) };
  }

  // ---- the artists row and its jump strip ------------------------------------
  //: 200 px circles, 30 apart (Bar States, lib-artists): a 230 px pitch.
  const PITCH = 230;
  let artistRow = $state(null);
  const artistWindow = $derived.by(() => {
    const over = 900;
    const from = Math.max(0, Math.floor((side.left - over) / PITCH));
    const to = Math.min(artists.length, Math.ceil((side.left + (side.view || 1000) + over) / PITCH));
    return { rows: artists.slice(from, to), before: from * PITCH, after: Math.max(0, (artists.length - to) * PITCH) };
  });

  //: The jump strip (JumpStrip.svelte): where each letter starts in the row.
  const firstAt = $derived.by(() => {
    const at = {};
    artists.forEach((a, i) => {
      const l = a.letter ?? '#';
      if (!(l in at)) at[l] = i;
    });
    return at;
  });
  const letterOn = $derived(
    artists[Math.min(artists.length - 1, Math.floor((side.left + PITCH / 2) / PITCH))]?.letter ?? '#',
  );
  function jump(letter) {
    const at = firstAt[letter];
    if (at == null || !artistRow) return;
    artistRow.scrollLeft = at * PITCH;
  }
</script>

<div class="barlib" data-screen={hero ? (here?.kind ?? 'artist') : (here?.kind ?? 'home')}>
  <div class="veil"></div>

  {#snippet backButtons(over)}
    <div class="nav" class:nav--over={over}>
      <button
        class="round"
        class:is-pressed={pressed === 'lib-back'}
        type="button"
        aria-label="Back"
        onpointerdown={() => press('lib-back')}
        onpointerup={lift}
        onpointercancel={lift}
        onclick={() => opening(back)}
      ><span class="i-back"></span></button>
      {#if path.length > 1}
        <button
          class="round"
          class:is-pressed={pressed === 'lib-home'}
          type="button"
          aria-label="Home"
          onpointerdown={() => press('lib-home')}
          onpointerup={lift}
          onpointercancel={lift}
          onclick={() => opening(home)}
        ><span class="i-tiles"><i></i><i></i><i></i><i></i></span></button>
      {/if}
    </div>
  {/snippet}

  {#snippet heroPanel(picture, name, meta, round)}
    <div class="hero">
      {#if picture && !failed.has(picture)}
        <img class="hero__img" src={picture} alt="" onerror={() => markFailed(picture)} />
      {:else if round}
        <div class="hero__none" style:background={tintOf(name)}><span>{initialsOf(name)}</span></div>
      {:else}
        <div class="hero__none hero__none--cover"></div>
      {/if}
      <div class="hero__shade"></div>
      <div class="hero__side"></div>
      {@render backButtons(true)}
      <div class="hero__text">
        <div class="hero__name">{name}</div>
        <div class="hero__meta">{meta}</div>
      </div>
    </div>
  {/snippet}

  <div class="frame">
    {#if column}
      <div class="side">
        {@render backButtons(false)}
        <div class="side__title">
          {#if here?.ctx?.appLogo}<img class="side__app" src={here.ctx.appLogo} alt="" />{/if}{title}
        </div>
        <div class="side__crumb">{crumb}</div>
        {#if playAllLabel}
          <button class="side__play" type="button" onclick={() => doMenu(here.ctx.from, 'play')}><span class="side__tri"></span>{playAllLabel}</button>
        {/if}
      </div>
    {/if}

    {#if resolvingArtist && path.length === 0}
      {@render heroPanel(null, openArtistNamed ?? '', 'Opening…', true)}
    {:else if here?.kind === 'artist' && artist}
      {@render heroPanel(artistPicture, artist.name, plural(discography.length, 'album', 'albums'), true)}
    {:else if here?.kind === 'album' && album}
      {@render heroPanel(album.artwork, album.title ?? '', [album.artist, album.year].filter(Boolean).join(' · '), false)}
    {/if}

    <div class="main">
      {#if resolvingArtist && path.length === 0}
        <div class="page">
          <div class="skel"><span></span><span></span><span></span></div>
        </div>
      {:else if atHome}
        <!-- Six across (Bar Frame, home2 / c): the panel's five cards and its
             home strip, which on a bar is a card of its own. -->
        {#snippet menuCard(tile, look)}
          <!-- ADR-0118: a tile Extended navigation adds (Library.svelte's). -->
          <button class="card card--{look}" class:is-pressed={pressed === tile.id} class:is-busy={busy === tile.handle} type="button"
            onpointerdown={() => press(tile.id)} onpointerup={lift} onpointercancel={lift} onclick={() => opening(() => openMenuTile(tile))}>
            {#if look === 'mymusic'}
              <span class="glyph"><Glyph name="Shelf" ink="#8fc4d8" size={44} /></span>
            {:else if look === 'favorites'}
              <span class="glyph"><Glyph name="Heart" ink="#e8a0b4" size={40} /></span>
            {:else if look === 'apps'}
              <span class="glyph"><Glyph name="Dots" ink="#c8a2d8" size={40} /></span>
            {:else}
              <span class="glyph"><Glyph name="Folder" ink="#b0bcc4" size={40} /></span>
            {/if}
            <span class="card__text">
              <span class="card__name">{look === 'apps' ? 'Apps' : tile.label}</span>
              <span class="card__count">{look === 'mymusic' ? (tile.count != null ? `${tile.count} views` : '') : look === 'apps' ? (tile.count != null ? plural(tile.count, 'app', 'apps') : '') : look === 'favorites' ? (tile.count ? plural(tile.count, 'item', 'items') : tile.count === 0 ? 'Empty' : '') : 'From Lyrion'}</span>
            </span>
          </button>
        {/snippet}
        <div class="home" class:is-narrow={narrow && !$menuTiles.length}>
          <div class="cards" class:cards--more={$menuTiles.length > 0} use:dragScroll>
            {#if tileFor('mymusic')}{@render menuCard(tileFor('mymusic'), 'mymusic')}{/if}
            <button class="card card--browse" class:is-pressed={pressed === 'browse'} class:is-busy={busy === 'browse'} type="button"
              onpointerdown={() => press('browse')} onpointerup={lift} onpointercancel={lift} onclick={() => opening(openBrowse)}>
              <span class="glyph glyph--bars"><i style="height:26px"></i><i style="height:44px"></i><i style="height:32px"></i><i style="height:39px"></i></span>
              <span class="card__text">
                <span class="card__name">Browse</span>
                <span class="card__count">{counts ? plural(counts.albums, 'album', 'albums') : ''}</span>
              </span>
            </button>
            <button class="card card--artists" class:is-pressed={pressed === 'artists'} class:is-busy={busy === 'artists'} type="button"
              onpointerdown={() => press('artists')} onpointerup={lift} onpointercancel={lift} onclick={() => opening(openArtists)}>
              <span class="glyph glyph--dots"><i></i><i></i><i></i></span>
              <span class="card__text">
                <!-- Album Artists, not Artists: My Music has All Artists too
                     (George, 2026-10-06). -->
                <span class="card__name card__name--long">Album Artists</span>
                <span class="card__count">{counts ? plural(counts.artists, 'artist', 'artists') : ''}</span>
              </span>
            </button>
            <button class="card card--playlists" class:is-pressed={pressed === 'playlists'} class:is-busy={busy === 'playlists'} type="button"
              onpointerdown={() => press('playlists')} onpointerup={lift} onpointercancel={lift} onclick={() => opening(openPlaylists)}>
              <span class="glyph glyph--list">
                <span><i></i><b style="width:44px"></b></span>
                <span><i></i><b style="width:32px"></b></span>
                <span><i></i><b style="width:38px"></b></span>
              </span>
              <span class="card__text">
                <span class="card__name">Playlists</span>
                <span class="card__count">{counts ? plural(counts.playlists, 'playlist', 'playlists') : ''}</span>
              </span>
            </button>
            {#if tileFor('favorites')}{@render menuCard(tileFor('favorites'), 'favorites')}{/if}
            <button class="card card--new" class:is-pressed={pressed === 'new'} type="button"
              onpointerdown={() => press('new')} onpointerup={lift} onpointercancel={lift} onclick={() => opening(openNew)}>
              <span class="glyph glyph--stack"><i></i><i></i><i></i></span>
              <span class="card__text">
                <span class="card__name">{stripLabel}</span>
                <span class="card__count"></span>
              </span>
            </button>
            <button class="card card--radio" class:is-pressed={pressed === 'radio'} class:is-busy={busy === 'radio'} type="button"
              onpointerdown={() => press('radio')} onpointerup={lift} onpointercancel={lift} onclick={() => opening(() => openRadio())}>
              <span class="glyph glyph--waves"><i></i><b></b><b></b></span>
              <span class="card__text">
                <span class="card__name">Radio</span>
                <!-- No station count: the radio tree has none (ADR-0038). -->
                <span class="card__count"></span>
              </span>
            </button>
            {#each otherTiles as tile (tile.handle)}{@render menuCard(tile, 'other')}{/each}
            {#if tileFor('apps')}{@render menuCard(tileFor('apps'), 'apps')}{/if}
            <button class="card card--settings" class:is-pressed={pressed === 'settings'} type="button"
              onpointerdown={() => press('settings')} onpointerup={lift} onpointercancel={lift} onclick={() => opening(openSettingsHere)}>
              <span class="glyph glyph--sliders"><b></b><b></b><i></i><i></i></span>
              <span class="card__text">
                <span class="card__name">Settings</span>
                <span class="card__count">Device and sources</span>
              </span>
            </button>
          </div>
        </div>
      {:else if here?.kind === 'menu'}
        <LyrionLevel
          bar
          {wide}
          page={menu}
          ctx={here.ctx ?? {}}
          letters={menuLetters}
          {busy}
          loading={!menu && !menuFailed}
          failed={menuFailed}
          onopen={openMenuRow}
          onact={doMenu}
          onsearchentry={openSearchEntry}
          onjump={jumpMenu}
          onmore={moreMenu}
          onearlier={earlierMenu}
          onretry={() => openMenu(here.handle, here.label, false, here.ctx)}
        />
      {:else if here?.kind === 'menusearch'}
        <LyrionSearch bar {wide} rows={here.rows} bind:text={searchText} ctx={here.ctx ?? {}} onopen={openMenuRow} onact={doMenu} />
      {:else if here?.kind === 'settings'}
        <div class="settings">
          <Settings onback={home} embedded />
        </div>
      {:else if here?.kind === 'new'}
        <div class="rowpage">
          <div class="mask" style:mask-image={mask} style:-webkit-mask-image={mask}>
            <div class="sideways sideways--tiles" class:sideways--round={stripArtists.length > 0} use:side.attach use:dragScroll use:keepPlace={where}>
              {#each stripArtists as who (who.id)}
                <button class="tile tile--round" class:is-busy={busy === who.id} type="button" onclick={() => openArtist(who)}>
                  <span class="disc disc--220" style:background={tintOf(who.name)}>
                    {#if photos[who.id] && !failed.has(photos[who.id])}
                      <img src={photos[who.id]} alt="" onerror={() => markFailed(photos[who.id])} />
                    {:else}
                      <span class="disc__initials">{initialsOf(who.name)}</span>
                    {/if}
                  </span>
                  <span class="tile__title">{who.name}</span>
                  <span class="tile__sub">{plural(who.albums ?? 0, 'album', 'albums')}</span>
                </button>
              {/each}
              {#each albums as tile (tile.id)}
                <button class="tile" class:is-busy={busy === tile.id} type="button"
                  onclick={() => openAlbum(tile.id, tile.title, [...path, ...artistPath(tile.artist)])}>
                  <span class="art art--250">
                    {#if tile.artwork && !failed.has(tile.artwork)}
                      <img src={tile.artwork} alt="" onerror={() => markFailed(tile.artwork)} />
                    {/if}
                  </span>
                  <span class="tile__title">{tile.title ?? ''}</span>
                  <span class="tile__sub">{tile.artist ?? ''}</span>
                </button>
              {/each}
            </div>
          </div>
        </div>
      {:else if here?.kind === 'artists'}
        <div class="artists">
          <div class="mask" style:mask-image={mask} style:-webkit-mask-image={mask}>
            <div class="sideways sideways--artists" bind:this={artistRow} use:side.attach use:dragScroll use:keepPlace={where}>
              <span class="spacer" style:width="{artistWindow.before}px"></span>
              {#each artistWindow.rows as entry (entry.id)}
                <button class="tile tile--artist" class:is-busy={busy === entry.id} type="button" onclick={() => openArtist(entry)}>
                  <span class="disc disc--200" style:background={tintOf(entry.name)}>
                    {#if photos[entry.id] && !failed.has(photos[entry.id])}
                      <img src={photos[entry.id]} alt="" onerror={() => markFailed(photos[entry.id])} />
                    {:else}
                      <span class="disc__initials">{initialsOf(entry.name)}</span>
                    {/if}
                  </span>
                  <span class="tile__title">{entry.name}</span>
                  <!-- The design's album count has no source in the artist
                       list (ADR-0038); its line is kept, so the row sits
                       where the design puts it. -->
                  <span class="tile__sub" aria-hidden="true">&nbsp;</span>
                </button>
              {/each}
              <span class="spacer" style:width="{artistWindow.after}px"></span>
            </div>
          </div>
          <JumpStrip have={(l) => l in firstAt} on={letterOn} onpick={jump} />
        </div>
      {:else if here?.kind === 'browse'}
        <div class="browse">
          <div class="pane">
            <div class="pane__head"><span class="pane__label">Artists</span></div>
            <div class="pane__list" use:watchPane use:fromTop={where}>
              <div style:height="{paneWindow.above}px" class="pane__space"></div>
              {#each paneWindow.rows as entry (entry.id)}
                <div class="prow" class:is-on={chosenArtist?.id === entry.id}>
                  <button class="prow__hit" type="button" onclick={() => chooseArtist(entry)}>
                    <span class="prow__label">{entry.name}</span>
                  </button>
                  {#if revealed === `artist-${entry.id}`}
                    <span class="acts">
                      <button class="act act--play" type="button" aria-label="Play now" onclick={() => play('artist', entry.id, entry.name)}><span class="act__play"></span></button>
                      <button class="act" type="button" aria-label="Add to queue" onclick={() => act('artist', entry.id, 'add', entry.name)}><span class="act__queue"><i></i><i></i><i></i></span></button>
                      <button class="act" type="button" aria-label="Add to playlist" onclick={() => openPicker('artist', entry.id, entry.name)}><span class="act__plus"></span></button>
                    </span>
                  {/if}
                </div>
              {/each}
              <div style:height="{paneWindow.below}px" class="pane__space"></div>
            </div>
          </div>
          <div class="pane pane--albums">
            <div class="pane__head"><span class="pane__label">Albums</span></div>
            <div class="pane__list" use:fromTop={chosenArtist?.id ?? where}>
              {#each browseAlbums as entry (entry.id)}
                <div class="prow" class:is-on={chosenAlbum?.id === entry.id}>
                  <button class="prow__hit" type="button" onclick={() => chooseAlbum(entry)}>
                    <span class="prow__label">{entry.title}</span>
                    {#if entry.year && revealed !== `album-${entry.id}`}<span class="prow__meta">{entry.year}</span>{/if}
                  </button>
                  {#if revealed === `album-${entry.id}`}
                    <span class="acts">
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
          <div class="pane pane--tracks">
            <div class="pane__head"><span class="pane__label">Tracks</span></div>
            <div class="pane__list" use:fromTop={chosenAlbum?.id ?? where}>
              {#each browseTracks as entry (entry.id)}
                <div class="prow" class:is-on={isPlaying(entry)}>
                  <button class="prow__hit" type="button" onclick={() => toggle(`track-${entry.id}`)}>
                    <span class="prow__label">{entry.title}</span>
                    {#if entry.duration && revealed !== `track-${entry.id}`}<span class="prow__meta">{mmss(entry.duration)}</span>{/if}
                  </button>
                  {#if revealed === `track-${entry.id}`}
                    <span class="acts">
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
      {:else if here?.kind === 'playlists'}
        <div class="rowpage">
          <div class="mask" style:mask-image={mask} style:-webkit-mask-image={mask}>
            <div class="sideways sideways--lists" use:side.attach use:dragScroll use:keepPlace={where}>
              {#each playlists as entry (entry.id)}
                <button class="plcard" class:is-busy={busy === entry.id} type="button" onclick={() => openPlaylist(entry)}>
                  <span class="glyph glyph--list">
                    <span><i></i><b style="width:44px"></b></span>
                    <span><i></i><b style="width:32px"></b></span>
                    <span><i></i><b style="width:38px"></b></span>
                  </span>
                  <span>
                    <span class="plcard__name">{entry.name}</span>
                    <span class="plcard__count">{plural(entry.tracks, 'track', 'tracks')}</span>
                  </span>
                </button>
              {:else}
                <div class="empty">No playlists in the library</div>
              {/each}
            </div>
          </div>
        </div>
      {:else if here?.kind === 'playlist' && playlist}
        <!-- Bar States, lib-playlist: Play and Shuffle, then the tracks in
             six rows that run sideways (decision 12). -->
        <div class="plpage">
          <div class="plpage__actions">
            <button class="btn btn--play" type="button" onclick={() => play('playlist', playlist.id, playlist.name)}>
              <span class="i-tri"></span><span class="btn__label btn__label--accent">Play</span>
            </button>
            <button class="btn" type="button" onclick={() => act('playlist', playlist.id, 'shuffle', playlist.name)}>
              <span class="btn__label">Shuffle</span>
            </button>
          </div>
          <div class="mask" style:mask-image={mask} style:-webkit-mask-image={mask}>
            <div class="sideways sideways--grid" use:side.attach use:dragScroll use:fromTop={where}>
              {#each playlist.items.slice(0, playlistReveal.shown) as entry, index (`${index}:${entry.id}`)}
                <div class="trow trow--two" class:is-on={isPlaying(entry)}>
                  <button class="trow__hit" type="button" onclick={() => toggle(`pltrack-${index}`)}>
                    <span class="trow__num">{String(index + 1).padStart(2, '0')}</span>
                    <span class="trow__text">
                      <span class="trow__title">{entry.title}</span>
                      <span class="trow__artist">{entry.artist ?? ''}</span>
                    </span>
                    {#if revealed !== `pltrack-${index}`}
                      <span class="trow__dur">{entry.duration ? mmss(entry.duration) : ''}</span>
                    {/if}
                  </button>
                  {#if revealed === `pltrack-${index}`}
                    <span class="acts">
                      <button class="act act--play" type="button" aria-label="Play now" onclick={() => play('track', entry.id, entry.title)}><span class="act__play"></span></button>
                      <button class="act" type="button" aria-label="Add to queue" onclick={() => act('track', entry.id, 'add', entry.title)}><span class="act__queue"><i></i><i></i><i></i></span></button>
                      <button class="act" type="button" aria-label="Add to playlist" onclick={() => openPicker('track', entry.id, entry.title)}><span class="act__plus"></span></button>
                    </span>
                  {/if}
                </div>
              {/each}
            </div>
          </div>
        </div>
      {:else if here?.kind === 'radio' && !radio}
        <div class="radio" style:--cols={radioCols}>
          <div class="sideways sideways--radio">
            {#each [1, 2, 3, 4] as n (n)}<div class="rcard rcard--skel"></div>{/each}
          </div>
        </div>
      {:else if here?.kind === 'radio' && radio}
        <!-- Bar States, lib-folder: folders and stations in one grid, a
             folder with a chevron. Two rows that run sideways, like every
             other long list on a bar (round 2 left the direction open). -->
        <div class="radio" style:--cols={radioCols}>
          <div class="mask" style:mask-image={mask} style:-webkit-mask-image={mask}>
            <div class="sideways sideways--radio" class:is-one-row={(radio.items?.length ?? 0) <= radioCols}
              use:side.attach use:dragScroll use:fromTop={where}>
              {#each radio.items as row (row.handle)}
                <button class="rcard" class:is-busy={busy === row.handle} type="button"
                  onclick={() => (row.kind === 'folder' ? openRadio(row.handle, row.label) : playStation(row))}>
                  <!-- The standard screen's shape and tint for the category
                       (George, 2026-10-04). -->
                  <RadioGlyph label={row.label} station={row.kind === 'station'} card />
                  <span class="rcard__text">
                    <span class="rcard__name">{row.label}</span>
                    {#if row.subtitle}<span class="rcard__meta">{row.subtitle}</span>{/if}
                  </span>
                  {#if row.kind === 'folder'}<span class="i-chev"></span>{/if}
                </button>
              {:else}
                <div class="empty">Nothing here</div>
              {/each}
            </div>
          </div>
        </div>
      {:else if here?.kind === 'artist' && artist}
        <!-- artist2: Play / Shuffle, then the albums as 200 px tiles. -->
        <div class="artistpage">
          <div class="btnrow">
            <button class="btn btn--play" type="button" onclick={() => play('artist', artist.id, artist.name)}>
              <span class="i-tri"></span><span class="btn__label">Play</span>
            </button>
            <button class="btn" type="button" onclick={() => act('artist', artist.id, 'shuffle', artist.name)}>
              <span class="btn__label">Shuffle</span>
            </button>
          </div>
          <div class="mask" style:mask-image={mask} style:-webkit-mask-image={mask}>
            <div class="sideways sideways--discs" use:side.attach use:dragScroll use:fromTop={where}>
              {#each discography as entry (entry.id)}
                <button class="tile tile--200" class:is-busy={busy === entry.id} type="button" onclick={() => openAlbum(entry.id, entry.title, path)}>
                  <span class="art art--200">
                    {#if entry.artwork && !failed.has(entry.artwork)}
                      <img src={entry.artwork} alt="" onerror={() => markFailed(entry.artwork)} />
                    {/if}
                  </span>
                  <span class="tile__title">{entry.title ?? ''}</span>
                  <span class="tile__sub">{entry.year ?? ''}</span>
                </button>
              {/each}
            </div>
          </div>
        </div>
      {:else if here?.kind === 'album' && album}
        <!-- album2: Play album and Add to queue over the track list. -->
        <div class="albumpage">
          <div class="btnrow">
            <button class="btn btn--play" type="button" onclick={() => play('album', album.id, album.title)}>
              <span class="i-tri"></span><span class="btn__label">Play album</span>
            </button>
            <button class="btn" type="button" onclick={() => act('album', album.id, 'add', album.title)}>
              <span class="i-plus"></span><span class="btn__label">Add to queue</span>
            </button>
            <span class="btnrow__meta">{album.tracks.length}{minutesOf(album.tracks) ? ` · ${minutesOf(album.tracks)} min` : ''}</span>
          </div>
          <div class="tracks" use:fromTop={where}>
            {#each album.tracks as track (track.id)}
              <div class="trow" class:is-on={isPlaying(track)}>
                <button class="trow__hit" type="button" onclick={() => toggle(`albumtrack-${track.id}`)}>
                  <span class="trow__num">{track.tracknum ? String(track.tracknum).padStart(2, '0') : ''}</span>
                  <span class="trow__title trow__title--19">{track.title ?? ''}</span>
                  {#if revealed !== `albumtrack-${track.id}`}
                    <span class="trow__dur trow__dur--16">{track.duration ? mmss(track.duration) : ''}</span>
                  {/if}
                </button>
                {#if revealed === `albumtrack-${track.id}`}
                  <span class="acts">
                    <button class="act act--play" type="button" aria-label="Play now" onclick={() => play('track', track.id, track.title)}><span class="act__play"></span></button>
                    <button class="act" type="button" aria-label="Add to queue" onclick={() => act('track', track.id, 'add', track.title)}><span class="act__queue"><i></i><i></i><i></i></span></button>
                    <button class="act" type="button" aria-label="Add to playlist" onclick={() => openPicker('track', track.id, track.title)}><span class="act__plus"></span></button>
                  </span>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      {/if}

      {#if toast}
        <div class="toast">{toast}</div>
      {/if}
    </div>

    <BarRail {active} {metadata} {controls} onopen={onclose} />

    {#if picker}
      <!-- Library.svelte's playlist picker, as a bar's sheet: over the
           content area beside the rail, full height less 12 px, min(760,
           width - 48) wide (Settings.svelte's `.panel--bar` sheet). -->
      <div class="over">
        <div class="sheet__scrim" role="presentation" onclick={() => (picker = null)}></div>
        <div class="sheet" role="dialog" aria-label="Add to playlist">
          <div class="sheet__head">
            <div class="sheet__kicker">Add to playlist</div>
            <div class="sheet__title">{picker.label}</div>
          </div>
          <div class="sheet__list">
            <!-- Creating playlists is not supported (ADR-0038 §3). -->
            {#each playlists as entry (entry.id)}
              <button class="sheet__row" type="button" onclick={() => addToPlaylist(entry)}>
                <span class="sheet__name">{entry.name}</span>
                <span class="sheet__count">{entry.tracks}</span>
              </button>
            {:else}
              <div class="empty">No playlists in the library</div>
            {/each}
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .barlib {
    position: absolute;
    inset: 0;
    z-index: 10;
    overflow: hidden;
    color: var(--ink);
    user-select: none;
  }
  /* **Now Playing's veil** (George, 2026-10-04, "A"): the darker one this
     had muted the artwork's colours, and the tiles read as well without it. */
  .veil {
    position: absolute;
    inset: 0;
    background: radial-gradient(130% 105% at 20% 42%, rgba(22, 36, 46, 0.3), rgba(14, 23, 30, 0.86));
  }
  button {
    font: inherit;
    color: inherit;
    border: none;
    background: none;
    padding: 0;
    text-align: left;
  }
  .frame {
    position: absolute;
    inset: 0;
    display: flex;
  }
  .main {
    position: relative;
    flex: 1;
    min-width: 0;
    display: flex;
    min-height: 0;
  }
  .is-busy {
    opacity: 0.6;
  }

  /* ---- the left column: 220 px, Back and Home, title, count ---- */
  .side {
    width: 220px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 28px 24px;
    box-sizing: border-box;
    border-right: 1px solid rgba(233, 238, 242, 0.09);
    min-height: 0;
  }
  .nav {
    display: flex;
    gap: 10px;
    flex-shrink: 0;
  }
  .nav--over {
    position: absolute;
    left: 24px;
    top: 24px;
    z-index: 2;
  }
  .round {
    width: var(--ctl);
    height: var(--ctl);
    border-radius: 50%;
    background: var(--ink-fill);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .nav--over .round {
    background: rgba(13, 21, 28, 0.55);
  }
  .round:active,
  .round.is-pressed {
    transform: scale(0.95);
    background: var(--ink-fill-press);
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
  /* The panel's chevron, its ink centred after the turn (Library.svelte). */
  .i-back {
    width: 14px;
    height: 14px;
    border-left: 3px solid var(--ink);
    border-bottom: 3px solid var(--ink);
    transform: translateX(4.2px) rotate(45deg);
  }
  .side__title {
    margin-top: 8px;
    font-size: var(--t-h3);
    font-weight: 700;
    letter-spacing: -0.01em;
    line-height: 1.15;
    overflow-wrap: anywhere;
    display: -webkit-box;
    -webkit-line-clamp: 4;
    line-clamp: 4;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .side__crumb {
    font-family: var(--font-mono);
    font-size: var(--t-meta);
    letter-spacing: 0.06em;
    color: var(--ink-quiet);
  }
  /* ADR-0118: an app's logo before its title, and Play all at the foot of
     a track list (the handover's §Frame — Bar). */
  .side__app {
    width: 30px;
    height: 30px;
    border-radius: 8px;
    object-fit: cover;
    vertical-align: -5px;
    margin-right: 10px;
  }
  .side__play {
    margin-top: auto;
    height: 56px;
    border-radius: 15px;
    background: rgba(126, 214, 188, 0.14);
    border: 1px solid rgba(126, 214, 188, 0.36);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    font: inherit;
    font-size: 18px;
    font-weight: 700;
    color: var(--ink);
    white-space: nowrap;
    cursor: pointer;
  }
  .side__play:active { transform: scale(0.96); }
  .side__tri {
    width: 0;
    height: 0;
    border-left: 13px solid var(--accent-lms);
    border-top: 8px solid transparent;
    border-bottom: 8px solid transparent;
  }

  /* ---- the photo or cover, 400 x 400, full height ---- */
  .hero {
    position: relative;
    width: 400px;
    height: 400px;
    flex-shrink: 0;
    overflow: hidden;
    background: var(--bg-well);
  }
  .hero__img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .hero__none {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .hero__none span {
    font-size: 120px;
    font-weight: 700;
    letter-spacing: 0.02em;
    color: var(--ink-quiet);
    margin-bottom: 60px;
  }
  .hero__none--cover {
    background: linear-gradient(160deg, rgba(126, 214, 188, 0.07), rgba(242, 164, 143, 0.06));
  }
  .hero__shade {
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(13, 21, 28, 0.45) 0, rgba(13, 21, 28, 0) 30%, rgba(13, 21, 28, 0) 55%, rgba(13, 21, 28, 0.88) 100%);
  }
  .hero__side {
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, rgba(13, 21, 28, 0) 70%, rgba(13, 21, 28, 0.6) 100%);
  }
  .hero__text {
    position: absolute;
    left: 28px;
    right: 28px;
    bottom: 26px;
  }
  .hero__name {
    font-size: var(--t-h1);
    font-weight: 800;
    letter-spacing: var(--track-tight);
    line-height: 1.1;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .hero__meta {
    margin-top: 8px;
    font-family: var(--font-mono);
    font-size: var(--t-meta);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: rgba(233, 238, 242, 0.75);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* ---- the home: six cards ---- */
  .home {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 0 36px;
    --t-card: 26px;
    --t-card-sub: 14px;
    --card-pad: 22px 20px;
  }
  /* Round 2, *Ends*: under 190 px a card steps its type down. */
  .home.is-narrow {
    --t-card: 21px;
    --t-card-sub: 12px;
    --card-pad: 20px 14px;
  }
  .cards {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 20px;
    height: 220px;
    flex-shrink: 0;
  }
  .card {
    --card: 233, 238, 242;
    min-width: 0;
    height: 100%;
    border-radius: var(--r-card);
    background: rgba(var(--card), 0.1);
    border: 1px solid rgba(var(--card), 0.3);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: var(--card-pad);
    box-sizing: border-box;
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
  .card--new,
  .card--radio {
    background: rgba(233, 238, 242, 0.055);
    border-color: rgba(233, 238, 242, 0.16);
  }
  .card--settings {
    background: rgba(233, 238, 242, 0.04);
    border-color: rgba(233, 238, 242, 0.12);
  }
  .card__text {
    display: block;
    min-width: 0;
  }
  .card__name {
    display: block;
    font-size: var(--t-card);
    font-weight: 700;
    letter-spacing: var(--track-tight);
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .card__count {
    display: block;
    min-height: 1.3em;
    font-family: var(--font-mono);
    font-size: var(--t-card-sub);
    letter-spacing: 0.02em;
    margin-top: 8px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .card--browse .card__count { color: rgba(126, 214, 188, 0.85); }
  .card--artists .card__count { color: rgba(159, 180, 232, 0.9); }
  .card--playlists .card__count { color: rgba(242, 164, 143, 0.9); }
  .card--settings .card__count { color: var(--ink-quiet); }
  /* ADR-0118: the tiles Extended navigation adds, and the row they make,
     196 x 300 and sideways (the handover's §1, Bar). */
  .cards--more {
    grid-template-columns: none;
    grid-auto-flow: column;
    grid-auto-columns: 196px;
    height: 300px;
    --t-card-sub: 13px;
    overflow-x: auto;
    overscroll-behavior-x: contain;
    scrollbar-width: none;
    touch-action: pan-x;
    padding-right: 72px;
    mask-image: linear-gradient(90deg, #000 0, #000 calc(100% - 72px), transparent 100%);
  }
  .cards--more::-webkit-scrollbar { display: none; }
  .card--mymusic { --card: 143, 196, 216; }
  .card--favorites { --card: 232, 160, 180; }
  .card--apps { --card: 200, 162, 216; }
  .card--other { --card: 176, 188, 196; border-style: dashed; border-color: rgba(176, 188, 196, 0.4); background: rgba(176, 188, 196, 0.08); }
  .card--mymusic .card__count { color: rgba(143, 196, 216, 0.9); }
  .card--favorites .card__count { color: rgba(232, 160, 180, 0.9); }
  .card--apps .card__count { color: rgba(200, 162, 216, 0.9); }
  .card--other .card__count { color: rgba(176, 188, 196, 0.95); }
  .card.is-busy { opacity: 0.6; }
  /* Two words in a 196 px card: a step down rather than an ellipsis. */
  .card__name--long { font-size: calc(var(--t-card) * 0.82); }

  .glyph {
    height: 44px;
    display: flex;
    flex-shrink: 0;
  }
  .glyph--bars { align-items: flex-end; gap: 7px; }
  .glyph--bars i { width: 8px; border-radius: 3px; background: var(--accent-lms); }
  .glyph--dots { align-items: center; }
  .glyph--dots i {
    width: 34px;
    height: 34px;
    border-radius: 50%;
    flex-shrink: 0;
    background: rgba(159, 180, 232, 0.95);
  }
  .glyph--dots i:nth-child(2) { background: rgba(159, 180, 232, 0.6); margin-left: -11px; }
  .glyph--dots i:nth-child(3) { background: rgba(159, 180, 232, 0.32); margin-left: -11px; }
  .glyph--list { flex-direction: column; justify-content: center; gap: 6px; }
  .glyph--list > span { display: flex; align-items: center; gap: 8px; }
  .glyph--list i { width: 6px; height: 6px; border-radius: 50%; background: var(--accent-artist); }
  .glyph--list b { height: 4px; border-radius: 2px; background: var(--accent-artist); }
  .glyph--list > span:nth-child(2) i,
  .glyph--list > span:nth-child(2) b { background: rgba(242, 164, 143, 0.7); }
  .glyph--list > span:nth-child(3) i,
  .glyph--list > span:nth-child(3) b { background: rgba(242, 164, 143, 0.45); }
  /* Bar Frame's New Music mark: three squares, stacked. */
  .glyph--stack { align-items: center; position: relative; }
  .glyph--stack i { position: absolute; width: 28px; height: 28px; border-radius: 6px; box-sizing: border-box; }
  .glyph--stack i:nth-child(1) { left: 0; top: 10px; border: 2.5px solid rgba(233, 238, 242, 0.34); }
  .glyph--stack i:nth-child(2) { left: 10px; top: 6px; border: 2.5px solid rgba(233, 238, 242, 0.6); background: rgba(16, 26, 33, 0.6); }
  .glyph--stack i:nth-child(3) { left: 20px; top: 4px; background: rgba(233, 238, 242, 0.85); }
  .glyph--waves { align-items: center; gap: 7px; }
  .glyph--waves i { width: 14px; height: 14px; border-radius: 50%; background: rgba(233, 238, 242, 0.85); flex-shrink: 0; }
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
  .glyph--sliders { display: block; position: relative; width: 30px; }
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

  /* ---- Settings in the content area ---- */
  .settings {
    flex: 1;
    min-width: 0;
    position: relative;
  }

  /* ---- sideways rows ---- */
  .mask {
    /* Its own layer, so the mask is rasterised once rather than with every
       frame of the scroll under it (Library.svelte's strip). */
    will-change: transform;
    min-width: 0;
  }
  .sideways {
    display: flex;
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: none;
    touch-action: pan-x;
    overscroll-behavior-x: contain;
  }
  .sideways::-webkit-scrollbar { display: none; }
  .rowpage {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  .sideways--tiles {
    gap: 22px;
    padding: 0 32px;
  }
  .sideways--round { gap: 30px; }
  .sideways--lists {
    gap: 22px;
    padding: 0 32px;
    align-items: center;
  }

  .tile {
    width: 250px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  .tile:active .art,
  .tile:active .disc { transform: scale(0.98); }
  .tile--round { width: 220px; text-align: center; align-items: center; }
  .tile--artist { width: 200px; margin-right: 30px; text-align: center; align-items: center; }
  .tile--200 { width: 200px; }
  .tile__title,
  .tile__sub {
    width: 100%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .tile__title {
    margin-top: 12px;
    font-size: 18px;
    font-weight: 600;
  }
  .tile__sub {
    margin-top: 3px;
    font-size: var(--t-meta);
    color: var(--ink-quiet);
  }
  .art {
    position: relative;
    display: block;
    border-radius: var(--r-lg);
    overflow: hidden;
    background: var(--bg-well);
    border: 1px solid rgba(233, 238, 242, 0.1);
    box-sizing: border-box;
    flex-shrink: 0;
    transition: transform 90ms ease;
  }
  .art--250 { width: 250px; height: 250px; }
  .art--200 { width: 200px; height: 200px; }
  .art img,
  .disc img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .disc {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    overflow: hidden;
    border: 1px solid rgba(233, 238, 242, 0.1);
    box-sizing: border-box;
    flex-shrink: 0;
    transition: transform 90ms ease;
  }
  .disc--220 { width: 220px; height: 220px; }
  .disc--200 { width: 200px; height: 200px; }
  .disc__initials {
    font-size: 52px;
    font-weight: 700;
    letter-spacing: 0.02em;
    color: var(--ink-quiet);
  }
  .spacer {
    flex-shrink: 0;
    display: block;
    height: 1px;
  }
  .empty,
  .pane__empty {
    padding: 14px 12px;
    font-size: var(--t-body-sm);
    color: var(--ink-quiet);
  }

  /* ---- Artists: the row and the jump strip (Bar States, lib-artists) ---- */
  .artists {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 26px;
    padding: 0 32px;
  }
  .sideways--artists {
    padding-right: 58px;
  }

  /* ---- Browse: three panes (Bar Library, browse) ---- */
  .browse {
    flex: 1;
    min-width: 0;
    display: flex;
    gap: 12px;
    padding: 24px;
    box-sizing: border-box;
  }
  .pane {
    flex: 1;
    min-width: 0;
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.045);
    border: 1px solid rgba(233, 238, 242, 0.09);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .pane--albums { flex: 1.25; }
  .pane--tracks { flex: 1.1; }
  .pane__head {
    height: 40px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    padding: 0 16px;
    border-bottom: 1px solid rgba(233, 238, 242, 0.08);
  }
  .pane__label {
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
    letter-spacing: var(--track-label);
    text-transform: uppercase;
    color: var(--ink-tab-off);
  }
  .pane__list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 6px;
    scrollbar-width: none;
    touch-action: pan-y;
    overscroll-behavior: contain;
  }
  .pane__list::-webkit-scrollbar { display: none; }
  .pane__space { flex-shrink: 0; }
  .prow {
    height: 52px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    border-radius: 10px;
    min-width: 0;
  }
  /* The row is the hit target; its actions sit beside it when revealed. */
  .prow__hit {
    flex: 1;
    min-width: 0;
    height: 100%;
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 0 12px;
    border-radius: 10px;
  }
  .prow.is-on {
    background: rgba(126, 214, 188, 0.14);
    color: var(--accent-lms);
  }
  .prow__hit:active { background: rgba(233, 238, 242, 0.08); }
  .prow__label {
    flex: 1;
    min-width: 0;
    font-size: 18px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .prow__meta {
    font-family: var(--font-mono);
    font-size: 14px;
    color: rgba(233, 238, 242, 0.62);
    flex-shrink: 0;
  }

  /* ---- Playlists: 250 px cards (Bar Library, playlists) ---- */
  .plcard {
    width: 250px;
    height: 250px;
    flex-shrink: 0;
    border-radius: var(--r-card);
    background: rgba(242, 164, 143, 0.1);
    border: 1px solid rgba(242, 164, 143, 0.3);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 26px 24px;
    box-sizing: border-box;
    min-width: 0;
  }
  .plcard:active {
    background: rgba(242, 164, 143, 0.24);
    transform: scale(0.98);
  }
  .plcard .glyph--list { height: auto; }
  .plcard__name {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    overflow-wrap: anywhere;
    font-size: var(--t-h3);
    font-weight: 700;
    letter-spacing: var(--track-tight);
  }
  .plcard__count {
    display: block;
    margin-top: 8px;
    font-family: var(--font-mono);
    font-size: 14px;
    letter-spacing: 0.06em;
    color: rgba(242, 164, 143, 0.9);
  }

  /* ---- the 58 px buttons ---- */
  .btn {
    height: 58px;
    padding: 0 22px;
    border-radius: var(--r-lg);
    background: rgba(233, 238, 242, 0.06);
    border: 1px solid rgba(233, 238, 242, 0.16);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    box-sizing: border-box;
    flex-shrink: 0;
  }
  .btn--play {
    background: rgba(126, 214, 188, 0.14);
    border-color: rgba(126, 214, 188, 0.36);
  }
  .btn:active { transform: scale(0.97); }
  .btn__label {
    font-size: var(--t-body);
    font-weight: 700;
    white-space: nowrap;
  }
  .btn__label--accent { color: var(--accent-lms); }
  .i-tri {
    width: 0;
    height: 0;
    border-left: 14px solid var(--accent-lms);
    border-top: 9px solid transparent;
    border-bottom: 9px solid transparent;
  }
  .i-plus {
    position: relative;
    width: 17px;
    height: 17px;
  }
  .i-plus::before,
  .i-plus::after {
    content: '';
    position: absolute;
    border-radius: 2px;
    background: rgba(233, 238, 242, 0.9);
  }
  .i-plus::before { left: 0; top: 7px; width: 17px; height: 3px; }
  .i-plus::after { left: 7px; top: 0; width: 3px; height: 17px; }
  .btnrow {
    display: flex;
    gap: 10px;
    flex-shrink: 0;
    align-items: center;
    min-width: 0;
  }
  .btnrow__meta {
    margin-left: auto;
    font-family: var(--font-mono);
    font-size: 14px;
    color: rgba(233, 238, 242, 0.62);
    white-space: nowrap;
  }

  /* ---- a playlist (Bar States, lib-playlist) ---- */
  .plpage {
    flex: 1;
    min-width: 0;
    display: flex;
    gap: 28px;
    padding: 28px 0 28px 32px;
    box-sizing: border-box;
  }
  .plpage__actions {
    width: 170px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    gap: 10px;
  }
  .plpage__actions .btn { padding: 0; }
  .plpage .mask {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  .sideways--grid {
    display: grid;
    grid-auto-flow: column;
    grid-template-rows: repeat(6, 52px);
    /* 420, not the design's 300: a revealed row's three 44 px actions left
       the title about five characters (George, 2026-10-01: "Let's do A"). */
    grid-auto-columns: 420px;
    gap: 2px 16px;
    padding-right: 32px;
  }
  .trow {
    height: 52px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    border-radius: 10px;
    min-width: 0;
  }
  .trow__hit {
    flex: 1;
    min-width: 0;
    height: 100%;
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 0 14px;
    border-radius: 10px;
  }
  .trow--two .trow__hit { gap: 14px; padding: 0 12px; }
  .trow.is-on {
    background: rgba(126, 214, 188, 0.14);
    color: var(--accent-lms);
  }
  .trow__hit:active { background: rgba(233, 238, 242, 0.08); }
  .trow__num {
    width: 26px;
    flex-shrink: 0;
    font-family: var(--font-mono);
    font-size: var(--t-meta);
    color: rgba(233, 238, 242, 0.62);
  }
  .trow__text {
    flex: 1;
    min-width: 0;
  }
  .trow__title,
  .trow__artist {
    display: block;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .trow__title {
    font-size: 18px;
    font-weight: 600;
  }
  .trow__title--19 {
    flex: 1;
    min-width: 0;
    font-size: var(--t-body);
  }
  .trow__artist {
    font-size: 14px;
    color: rgba(233, 238, 242, 0.55);
  }
  .trow__dur {
    flex-shrink: 0;
    font-family: var(--font-mono);
    font-size: var(--t-meta);
    color: rgba(233, 238, 242, 0.62);
  }
  .trow__dur--16 { font-size: 16px; }

  /* ---- Radio: folders and stations in one grid (Bar States, lib-folder) ---- */
  .radio {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 28px 0;
    box-sizing: border-box;
  }
  .sideways--radio {
    display: grid;
    grid-auto-flow: column;
    grid-template-rows: repeat(2, 120px);
    /* A third of the next column shows, so there is plainly more to the
       right (George, 2026-10-04: the tiles filled the width exactly). */
    grid-auto-columns: calc((100% - var(--cols) * 16px) / (var(--cols) + 0.35));
    gap: 16px;
    padding: 0 32px;
    scroll-padding: 0 32px;
  }
  .sideways--radio.is-one-row { grid-template-rows: 120px; }
  .rcard {
    min-width: 0;
    border-radius: 20px;
    background: rgba(233, 238, 242, 0.055);
    border: 1px solid rgba(233, 238, 242, 0.16);
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 0 24px;
    box-sizing: border-box;
  }
  .rcard:active {
    background: rgba(233, 238, 242, 0.12);
    transform: scale(0.98);
  }
  .rcard--skel { animation: rskel 1500ms ease-in-out infinite; }
  @keyframes rskel {
    50% { opacity: 0.45; }
  }
  .rcard__text {
    flex: 1;
    min-width: 0;
  }
  .rcard__name,
  .rcard__meta {
    display: block;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .rcard__name {
    font-size: 21px;
    font-weight: 700;
  }
  .rcard__meta {
    margin-top: 5px;
    font-family: var(--font-mono);
    font-size: 14px;
    color: var(--ink-quiet);
  }
  .i-chev {
    width: 12px;
    height: 12px;
    flex-shrink: 0;
    border-right: 3px solid rgba(233, 238, 242, 0.55);
    border-top: 3px solid rgba(233, 238, 242, 0.55);
    transform: rotate(45deg);
  }

  /* ---- the artist page (artist2) ---- */
  .artistpage {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 22px;
    padding: 28px 0 28px 32px;
    box-sizing: border-box;
  }
  .sideways--discs {
    gap: 22px;
    padding-right: 32px;
  }

  /* ---- the album page (album2) ---- */
  .albumpage {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 24px 28px 24px 32px;
    box-sizing: border-box;
  }
  .tracks {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 2px;
    scrollbar-width: none;
    touch-action: pan-y;
    overscroll-behavior: contain;
  }
  .tracks::-webkit-scrollbar { display: none; }

  .page {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 0 32px;
  }
  .skel {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .skel span {
    display: block;
    height: 18px;
    border-radius: 5px;
    background: rgba(233, 238, 242, 0.1);
    animation: rskel 1500ms ease-in-out infinite;
  }
  .skel span:nth-child(1) { width: 62%; }
  .skel span:nth-child(2) { width: 80%; animation-delay: 150ms; }
  .skel span:nth-child(3) { width: 48%; animation-delay: 300ms; }

  /* ---- a row's actions: Library.svelte's, 44 px rather than the panel's
     40 so each is a bar's touch target ---- */
  .acts {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
    padding-right: 4px;
  }
  .act {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    background: rgba(233, 238, 242, 0.06);
    border: 1px solid rgba(233, 238, 242, 0.14);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-sizing: border-box;
  }
  .act:active { transform: scale(0.95); }
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
  .act__queue i:last-child { width: 9px; }
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
  .act__plus::before { left: 0; top: 6px; width: 15px; height: 2.5px; }
  .act__plus::after { left: 6px; top: 0; width: 2.5px; height: 15px; }

  /* ---- the playlist picker (Library.svelte's sheet), as a bar's sheet:
     the content area beside the 124 px rail, full height less 12 px above
     and below, min(760, width - 48) wide (Settings.svelte, .panel--bar) ---- */
  .over {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    right: 124px;
    z-index: 20;
  }
  .sheet__scrim {
    position: absolute;
    inset: 0;
    background: var(--bg-scrim);
  }
  .sheet {
    position: absolute;
    left: 50%;
    top: 12px;
    bottom: 12px;
    transform: translateX(-50%);
    width: min(760px, 100% - 48px);
    display: flex;
    flex-direction: column;
    gap: 12px;
    background: var(--bg-panel);
    border: 1px solid rgba(126, 214, 188, 0.22);
    border-radius: 20px;
    padding: 18px 20px 14px;
    box-sizing: border-box;
    box-shadow: 0 34px 90px rgba(0, 0, 0, 0.6);
  }
  .sheet__head {
    flex-shrink: 0;
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
    font-size: 22px;
    font-weight: 700;
    color: var(--ink);
    margin-top: 5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .sheet__list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
    scrollbar-width: none;
    touch-action: pan-y;
    overscroll-behavior: contain;
  }
  .sheet__list::-webkit-scrollbar { display: none; }
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
  .sheet__row:active { background: rgba(233, 238, 242, 0.16); }
  .sheet__name {
    flex: 1;
    min-width: 0;
    font-size: var(--t-body);
    font-weight: 600;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .sheet__count {
    font-family: var(--font-mono);
    font-size: 14px;
    color: var(--ink-quiet);
    flex-shrink: 0;
  }

  /* ---- the toast: bottom centre of the content area (Bar States) ---- */
  .toast {
    position: absolute;
    z-index: 8;
    left: 50%;
    bottom: 28px;
    transform: translateX(-50%);
    max-width: calc(100% - 48px);
    padding: 16px 26px;
    border-radius: 14px;
    background: rgba(22, 35, 44, 0.97);
    border: 1px solid rgba(126, 214, 188, 0.3);
    box-shadow: 0 18px 50px rgba(0, 0, 0, 0.5);
    font-size: 18px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    box-sizing: border-box;
    pointer-events: none;
  }
</style>
