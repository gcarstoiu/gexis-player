<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **Internet radio on a bar** (ADR-0180; design/source/31, pick 8a; B01-B13,
  B31, B32): the Radio screen's ways in as tiles, then each list as two
  sideways rows of cards - Favourites, Popular here, By genre, By country, By
  language, a branch's stations, Search. The bar's frame as built: the side
  column (Back, Home, the title and crumb; the directory's banner at its
  foot) and the rail. Its own steps, one over the other; Back takes one off,
  and from the top leaves.

  Two homes, as the panel's RadioScreen.svelte. With Lyrion on, the
  library's Radio card opens it inside the library (BarLibrary.svelte) and
  *Lyrion's radio* opens Lyrion's tree there, over it. With Lyrion off or
  its navigation off, the waiting screen's Radio button and Now Playing's
  chevron open it as a screen of its own (`standalone`, App.svelte).
-->
<script>
  import { onMount } from 'svelte';
  import BarRail from './BarRail.svelte';
  import CategoryTile from './radio/CategoryTile.svelte';
  import Favourites from './radio/Favourites.svelte';
  import StationCards from './radio/StationCards.svelte';
  import Branches from './radio/Branches.svelte';
  import Search from './radio/Search.svelte';
  import Sideways from './radio/Sideways.svelte';
  import Icon from '../radio/Icon.svelte';
  import { pressing } from '../../lib/press.svelte.js';
  import {
    addFavourite,
    count,
    favourites,
    loadGenres,
    loadOverview,
    loadPopular,
    loadStations,
    playFavourite,
    playStation,
    radio,
    refreshFavourites,
    removeFavourite,
    wantFavourites,
  } from '../../lib/radio.js';

  let {
    active = null,
    metadata = null,
    controls = [],
    //: A screen of its own (Lyrion off): its veil, over what is below.
    standalone = false,
    //: *Lyrion's radio* among the tiles: only while Lyrion and its navigation are on.
    lyrion = false,
    onback,
    //: Home on a page under the top: the library's root inside the library;
    //: otherwise (null) Radio's own top.
    onhome = null,
    onlyrion = null,
    //: The rail's tap: Now Playing.
    onopen = null,
  } = $props();

  // ---- where in Radio the screen is ------------------------------------------
  //: [] is the top. Each step: `{kind}` - favourites, popular, genres,
  //: countries, languages, search - or `{kind: 'list', by, value, label,
  //: under}` for a branch's stations.
  let stack = $state([]);
  const page = $derived(stack.at(-1) ?? null);
  const press = pressing();

  let steps = 0;
  function go(step) {
    stack = [...stack, { ...step, n: ++steps }];
  }
  function back() {
    if (stack.length) stack = stack.slice(0, -1);
    else onback?.();
  }
  function home() {
    if (onhome) onhome();
    else stack = [];
  }

  // ---- the directory and the favourites (RadioScreen.svelte's) ----------------
  let overview = $state(null);
  //: 'ok', 'kept' (the last day's lists), 'none' (nothing kept), or null before it is known.
  let directory = $state(null);
  let retrying = $state(false);
  //: A page read again after Try again.
  let reread = $state(0);

  async function readOverview() {
    try {
      overview = await loadOverview();
    } catch (err) {
      console.info('radio:', err.message);
      return;
    }
    if (overview.reachable !== false) {
      directory = 'ok';
      return;
    }
    // The core says only that the directory did not answer last time;
    // whether the last day's lists are kept, a list says.
    try {
      const probe = await loadGenres();
      directory = probe.reachable === false ? 'kept' : 'ok';
    } catch (err) {
      directory = err.unreachable ? 'none' : 'kept';
    }
  }
  async function retry() {
    retrying = true;
    await readOverview();
    retrying = false;
    reread += 1;
  }
  const kept = () => {
    if (directory !== 'none') directory = 'kept';
  };
  const unreachable = () => (directory = 'none');

  onMount(() => {
    wantFavourites();
    readOverview();
  });

  const favs = $derived($favourites ?? overview?.favourites ?? null);
  const favIds = $derived($favourites ? new Set($favourites.map((s) => s.id)) : null);
  //: A heart tapped shows at once; the core's answer follows.
  let wanted = $state({});
  const isFavourite = (station) => wanted[station.id] ?? (favIds ? favIds.has(station.id) : !!station.favourite);

  async function toggleFavourite(station) {
    const want = !isFavourite(station);
    wanted = { ...wanted, [station.id]: want };
    try {
      if (want) await addFavourite(station);
      else await removeFavourite(station.id);
      await refreshFavourites();
    } catch (err) {
      console.info('radio:', err.message);
    } finally {
      const { [station.id]: _, ...rest } = wanted;
      wanted = rest;
    }
  }

  //: The station sounding (or about to): its card says Playing.
  const playingId = $derived(
    active === 'radio' && $radio?.station && !['stopped', 'not_answering'].includes($radio.state)
      ? $radio.station.id
      : null,
  );
  function play(station) {
    playStation(station).catch((err) => console.info('radio:', err.message));
  }
  function playFav(station) {
    playFavourite(station.id).catch((err) => console.info('radio:', err.message));
  }

  // ---- the side column ---------------------------------------------------------
  //: Popular here's country, by name: *Germany*.
  const countryName = $derived.by(() => {
    const code = overview?.country;
    if (!code) return '';
    try {
      return new Intl.DisplayNames(['en'], { type: 'region' }).of(code) ?? code;
    } catch {
      return code;
    }
  });
  const TITLES = {
    favourites: 'Favourites',
    popular: 'Popular here',
    genres: 'By genre',
    countries: 'By country',
    languages: 'By language',
    search: 'Search',
  };
  const NOUNS = { genres: ['genre', 'genres'], countries: ['country', 'countries'], languages: ['language', 'languages'] };
  //: How many branches a branch page holds, and whether a list's page is on
  //: its way - each for the step that said so, so a page left says nothing.
  let branchCount = $state(null);
  let loadingStep = $state(null);
  const branches = $derived(page && branchCount?.n === page.n ? branchCount.count : null);
  const listLoading = $derived(!!page && loadingStep === page.n);
  const title = $derived(page ? (page.kind === 'list' ? page.label : TITLES[page.kind]) : 'Radio');
  //: B05-B13: *Radio*, *Radio · Germany*, *Radio · 18 genres*, *Radio · By
  //: genre · Loading…*; at the top, none.
  const crumb = $derived.by(() => {
    if (!page) return '';
    const parts = ['Radio'];
    if (page.kind === 'popular' && countryName) parts.push(countryName);
    if (page.kind === 'list') parts.push(page.under);
    if (NOUNS[page.kind] && branches != null) parts.push(`${count(branches)} ${NOUNS[page.kind][branches === 1 ? 0 : 1]}`);
    if ((page.kind === 'popular' || page.kind === 'list') && listLoading) parts.push('Loading…');
    return parts.join(' · ');
  });

  function loading(n, on) {
    if (on) loadingStep = n;
    else if (loadingStep === n) loadingStep = null;
  }

  const BRANCH = { genres: ['genre', 'By genre'], countries: ['country', 'By country'], languages: ['language', 'By language'] };
  function openBranch(kind, row) {
    const [by, under] = BRANCH[kind];
    go({ kind: 'list', by, value: by === 'country' ? row.code : row.name, label: row.label ?? row.name, under });
  }

  //: The banner at the column's foot (B03, B04): at the top whenever the
  //: directory is out of reach; under it, only with nothing kept - and never
  //: over the favourites, which still play.
  const bannerShown = $derived(
    (!page && (directory === 'kept' || directory === 'none')) || (page && page.kind !== 'favourites' && directory === 'none'),
  );

  // ---- the top: the ways in --------------------------------------------------
  //: §8's discs and tints (design/source/31 README); the five that read the
  //: directory are dimmed and inert while nothing of it is kept (B04).
  const tiles = $derived([
    {
      id: 'favourites',
      label: 'Favourites',
      glyph: 'heart',
      tint: 'var(--favourite)',
      meta: favs?.length ? `${count(favs.length)} ${favs.length === 1 ? 'station' : 'stations'}` : '',
    },
    { id: 'popular', label: 'Popular here', glyph: 'pin', tint: 'var(--accent-bluetooth)', meta: countryName, directory: true },
    { id: 'genres', label: 'By genre', glyph: 'note', tint: 'var(--accent-artist)', directory: true },
    { id: 'countries', label: 'By country', glyph: 'globe', tint: 'var(--accent-radio)', directory: true },
    { id: 'languages', label: 'By language', glyph: 'speech', tint: 'var(--accent-display)', directory: true },
    { id: 'search', label: 'Search', glyph: 'search', tint: 'var(--ink)', directory: true },
  ]);
</script>

<div class="barradio" class:barradio--standalone={standalone} data-screen="radio">
  {#if standalone}<div class="veil"></div>{/if}

  <div class="frame">
    <div class="side">
      <div class="nav">
        <button class="round" class:is-pressed={press.is('back')} type="button" aria-label="Back" data-dpad-back
          onpointerdown={() => press.down('back')} onpointerup={press.up} onpointercancel={press.up}
          onclick={() => press.act(back)}><span class="i-back"></span></button>
        {#if page}
          <button class="round" class:is-pressed={press.is('home')} type="button" aria-label="Home"
            onpointerdown={() => press.down('home')} onpointerup={press.up} onpointercancel={press.up}
            onclick={() => press.act(home)}><span class="i-tiles"><i></i><i></i><i></i><i></i></span></button>
        {/if}
      </div>
      <div class="side__title" class:side__title--short={bannerShown}>{title}</div>
      {#if crumb}<div class="side__crumb">{crumb}</div>{/if}

      {#if bannerShown}
        <!-- `DirectoryBanner` in the side column (B03, B04). -->
        <div class="banner" role="status">
          <span class="banner__text">
            <span class="banner__glyph"><Icon name="cloud-off" size={20} /></span>
            <span>{directory === 'none' ? 'Directory unreachable. Favourites still play.' : 'Directory unreachable. Lists from the last day.'}</span>
          </span>
          <button class="banner__retry" type="button" disabled={retrying} onclick={retry}>Try again</button>
        </div>
      {/if}
    </div>

    <div class="main">
      {#key reread}
        {#if !page}
          <Sideways fade={110}>
            <div class="tiles">
              {#each tiles as tile (tile.id)}
                <CategoryTile glyph={tile.glyph} label={tile.label} meta={tile.meta} tint={tile.tint}
                  off={tile.directory && directory === 'none'} onopen={() => go({ kind: tile.id })} />
              {/each}
              {#if lyrion}
                <CategoryTile glyph="lyrion" label="Lyrion's radio" tint="var(--accent-lms)" onopen={() => onlyrion?.()} />
              {/if}
            </div>
          </Sideways>
        {:else if page.kind === 'favourites'}
          {#if favs}<Favourites favourites={favs} {playingId} onplay={playFav} />{/if}
        {:else if page.kind === 'popular'}
          {@const n = page.n}
          <StationCards load={(offset) => loadPopular(offset)} {playingId} {isFavourite} onheart={toggleFavourite}
            onplay={play} onunreachable={unreachable} onkept={kept} onloading={(on) => loading(n, on)} />
        {:else if page.kind === 'genres' || page.kind === 'countries' || page.kind === 'languages'}
          {@const n = page.n}
          {@const kind = page.kind}
          <Branches {kind} country={overview?.country ?? null} onopen={(row) => openBranch(kind, row)}
            onunreachable={unreachable} onkept={kept} oncount={(c) => (branchCount = { n, count: c })} />
        {:else if page.kind === 'list'}
          {@const step = page}
          <StationCards load={(offset) => loadStations({ [step.by]: step.value, offset })} key={`${step.by}:${step.value}`}
            {playingId} {isFavourite} onheart={toggleFavourite} onplay={play} onunreachable={unreachable} onkept={kept}
            onloading={(on) => loading(step.n, on)} />
        {:else if page.kind === 'search'}
          <Search {playingId} {isFavourite} onheart={toggleFavourite} onplay={play} onunreachable={unreachable} onkept={kept} />
        {/if}
      {/key}
    </div>

    <BarRail radio {active} {metadata} {controls} {onopen} />
  </div>
</div>

<style>
  .barradio {
    position: absolute;
    inset: 0;
    overflow: hidden;
    color: var(--ink);
    user-select: none;
  }
  .barradio--standalone {
    z-index: 10;
  }
  /* BarLibrary's veil: Now Playing's, over the panel's one backdrop. */
  .veil {
    position: absolute;
    inset: 0;
    background: var(--cover-veil);
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
  }
  .tiles {
    display: flex;
    gap: 20px;
  }

  /* ---- the side column: BarLibrary's, 220 px ---- */
  .side {
    width: 220px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 28px 24px;
    box-sizing: border-box;
    border-right: 1px solid var(--c-ink-09);
    min-height: 0;
  }
  .nav {
    display: flex;
    gap: 10px;
    flex-shrink: 0;
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
    flex-shrink: 0;
  }
  /* The banner takes the column's foot: a long branch's name keeps two lines. */
  .side__title--short {
    -webkit-line-clamp: 2;
    line-clamp: 2;
  }
  .side__crumb {
    font-family: var(--font-mono);
    font-size: var(--t-meta);
    letter-spacing: 0.06em;
    color: var(--ink-quiet);
  }

  /* ---- the directory out of reach (B03, B04) ---- */
  .banner {
    margin-top: auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
    border-radius: var(--r-14);
    background: var(--directory-ground);
    border: 1px solid var(--directory-line);
    flex-shrink: 0;
  }
  .banner__text {
    display: flex;
    gap: 8px;
    align-items: flex-start;
    font-size: 15px;
    line-height: 1.35;
  }
  .banner__glyph {
    color: var(--accent-warn);
    display: flex;
    flex-shrink: 0;
  }
  .banner__retry {
    height: 40px;
    border-radius: var(--r-pill);
    border: 1px solid var(--c-warn-50);
    background: transparent;
    color: var(--accent-warn);
    font-size: 15px;
    font-weight: 700;
    text-align: center;
  }
  .banner__retry:active {
    transform: scale(0.96);
  }
  .banner__retry:disabled {
    opacity: 0.6;
  }
</style>
