<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **Internet radio on the panel** (ADR-0180; design/source/31, P01-P20): the
  Radio screen and what opens from it - the favourites in their order,
  Popular here, By genre, By country, By language, a branch's stations, and
  Search. Its own header (Back, the title, the search field) and its own
  steps, one over the other; Back takes one off, and from the top leaves.

  Two homes. With Lyrion on, the library's Radio card opens it inside the
  library (Library.svelte), whose mini strip it shares, and *Lyrion's radio*
  opens Lyrion's tree there. With Lyrion off or its navigation off, the
  waiting screen's Radio button opens it as a screen of its own
  (`standalone`, App.svelte), with the mini strip at its foot while
  something plays (decided while drawing #1).
-->
<script>
  import { onMount } from 'svelte';
  import RadioRoot from './RadioRoot.svelte';
  import FavouritesList from './FavouritesList.svelte';
  import StationList from './StationList.svelte';
  import BranchList from './BranchList.svelte';
  import RadioSearch from './RadioSearch.svelte';
  import DirectoryBanner from './DirectoryBanner.svelte';
  import Scroll from './Scroll.svelte';
  import Icon from './Icon.svelte';
  import MiniStrip from '../MiniStrip.svelte';
  import { pressing } from '../../lib/press.svelte.js';
  import {
    addFavourite,
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
    volume = null,
    controls = [],
    //: A screen of its own (Lyrion off): its veil, and the mini strip while something plays.
    standalone = false,
    //: *Lyrion's radio* among Browse's cards.
    lyrion = false,
    onback,
    //: Home on a page under the top: the library's root inside the library;
    //: otherwise (null) Radio's own top.
    onhome = null,
    onlyrion = null,
    //: The mini strip's tap: Now Playing.
    onopen = null,
    onvolume = null,
  } = $props();

  // ── where in Radio the screen is ─────────────────────────────────────
  //: [] is the top. Each step: `{kind}` - favourites, popular, genres,
  //: countries, languages, search - or `{kind: 'list', by, value, label,
  //: total, under}` for a branch's stations.
  let stack = $state([]);
  const page = $derived(stack.at(-1) ?? null);
  const press = pressing();

  function go(step) {
    stack = [...stack, step];
  }
  function back() {
    if (stack.length) stack = stack.slice(0, -1);
    else onback?.();
  }
  function home() {
    if (onhome) onhome();
    else stack = [];
  }

  // ── the directory and the favourites ─────────────────────────────────
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

  //: The station sounding (or about to): its tile says PLAYING, its row Playing.
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

  // ── the header ───────────────────────────────────────────────────────
  //: Popular here's country, by name: *Radio · Germany*.
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
  };
  const title = $derived(page ? (page.kind === 'list' ? page.label : TITLES[page.kind]) : 'Radio');
  const crumb = $derived(
    !page ? '' : page.kind === 'list' ? `Radio · ${page.under}` : page.kind === 'popular' && countryName ? `Radio · ${countryName}` : 'Radio',
  );

  let text = $state('');
  let field = $state(null);
  function openSearch() {
    text = '';
    go({ kind: 'search' });
  }
  //: Focused as it opens, so text typed on the phone lands in it from the
  //: tap that opened it (ADR-0121), as Lyrion's search field...
  function focusOnOpen(node) {
    requestAnimationFrame(() => node.focus({ preventScroll: true }));
  }
  //: ...and kept there through a tap on a result, so more typing still
  //: lands in it (P19: a row selected, the field still focused).
  function keepTyping() {
    requestAnimationFrame(() => field?.focus({ preventScroll: true }));
  }

  const BRANCH = { genres: ['genre', 'By genre'], countries: ['country', 'By country'], languages: ['language', 'By language'] };
  function openBranch(kind, row) {
    const [by, under] = BRANCH[kind];
    go({ kind: 'list', by, value: by === 'country' ? row.code : row.name, label: row.label ?? row.name, total: row.stations ?? null, under });
  }

  const bannerShown = $derived(
    (!page && (directory === 'kept' || directory === 'none')) || (page && page.kind !== 'favourites' && directory === 'none'),
  );
</script>

<div class="radio" class:radio--standalone={standalone}>
  {#if standalone}<div class="veil"></div>{/if}

  <div class="header">
    <button class="round" class:is-pressed={press.is('back')} type="button" aria-label="Back" data-dpad-back
      onpointerdown={() => press.down('back')} onpointerup={press.up} onpointercancel={press.up}
      onclick={() => press.act(back)}>
      <span class="i-back"></span>
    </button>
    {#if page?.kind === 'search'}
      <label class="field field--search">
        <span class="field__glyph"><Icon name="search" size={22} /></span>
        <input class="field__in" type="search" bind:this={field} bind:value={text} use:focusOnOpen
          autocomplete="off" spellcheck="false" aria-label="Search stations" />
        {#if text}
          <button class="field__clear" type="button" aria-label="Clear" onclick={() => { text = ''; field?.focus(); }}>
            <Icon name="clear" size={18} width={2.4} />
          </button>
        {/if}
      </label>
    {:else}
      {#if page}
        <button class="round" class:is-pressed={press.is('home')} type="button" aria-label="Home"
          onpointerdown={() => press.down('home')} onpointerup={press.up} onpointercancel={press.up}
          onclick={() => press.act(home)}>
          <span class="i-tiles"><i></i><i></i><i></i><i></i></span>
        </button>
      {/if}
      <div class="heading">
        <span class="heading__title">{title}</span>
        {#if crumb}<span class="heading__crumb">{crumb}</span>{/if}
      </div>
      {#if !page}
        <button class="field field--open" type="button" onclick={openSearch}>
          <span class="field__glyph"><Icon name="search" size={22} /></span>
          <span class="field__hint">Search stations</span>
        </button>
      {/if}
    {/if}
  </div>

  {#if bannerShown}
    <div class="banner">
      <DirectoryBanner kind={directory} busy={retrying} onretry={retry} />
    </div>
  {/if}

  <div class="body" role="presentation" onpointerup={page?.kind === 'search' ? keepTyping : undefined}>
    {#key reread}
      {#if !page}
        <div class="top" data-dpad-start>
          <RadioRoot
            favourites={favs}
            {playingId}
            {directory}
            {lyrion}
            onall={() => go({ kind: 'favourites' })}
            onplay={playFav}
            onheart={toggleFavourite}
            onbrowse={(kind) => go({ kind })}
            onlyrion={() => onlyrion?.()}
          />
        </div>
      {:else if page.kind === 'favourites'}
        <FavouritesList favourites={favs ?? []} {playingId} onplay={playFav} />
      {:else if page.kind === 'popular'}
        <Scroll>
          <StationList load={(offset) => loadPopular(offset)} label="Popular here" {playingId} {isFavourite}
            onheart={toggleFavourite} onplay={play} onunreachable={unreachable} onkept={kept} />
        </Scroll>
      {:else if page.kind === 'genres' || page.kind === 'countries' || page.kind === 'languages'}
        <BranchList kind={page.kind} country={overview?.country ?? null} onopen={(row) => openBranch(page.kind, row)}
          onunreachable={unreachable} onkept={kept} />
      {:else if page.kind === 'list'}
        {@const step = page}
        <Scroll>
          <StationList load={(offset) => loadStations({ [step.by]: step.value, offset })} key={`${step.by}:${step.value}`}
            label={step.label} total={step.total} {playingId} {isFavourite} onheart={toggleFavourite} onplay={play}
            onunreachable={unreachable} onkept={kept} />
        </Scroll>
      {:else if page.kind === 'search'}
        <RadioSearch {text} {playingId} {isFavourite} onheart={toggleFavourite} onplay={play}
          onunreachable={unreachable} onkept={kept} />
      {/if}
    {/key}
  </div>

  {#if standalone && active}
    <div class="strip">
      <MiniStrip {active} {metadata} {volume} {controls} {onopen} {onvolume} />
    </div>
  {/if}
</div>

<style>
  .radio {
    position: relative;
    flex: 1;
    min-width: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    color: var(--ink);
  }
  .radio--standalone {
    position: absolute;
    inset: 0;
    z-index: 10;
    overflow: hidden;
  }
  .veil {
    position: absolute;
    inset: 0;
    background: var(--cover-veil-strong);
  }

  button {
    font: inherit;
    color: inherit;
    border: none;
    background: none;
    padding: 0;
    text-align: left;
  }

  /* The library's header (Library.svelte), as the design draws it. */
  .header {
    position: relative;
    height: var(--header-h);
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 20px;
    padding: 0 40px;
    box-sizing: border-box;
    border-bottom: 1px solid var(--c-ink-09);
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
  .round:active,
  .round.is-pressed {
    transform: scale(0.95);
    background: var(--ink-fill-press, var(--c-ink-14));
  }
  .i-back {
    width: 14px;
    height: 14px;
    border-left: 3px solid var(--ink);
    border-bottom: 3px solid var(--ink);
    transform: translateX(4.2px) rotate(45deg);
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

  /* The search field (`SearchField`): in the top's header, a way into
     Search; on Search, the field itself, the width of the header. */
  .field {
    height: 56px;
    box-sizing: border-box;
    border-radius: var(--r-pill);
    padding: 0 10px 0 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    background: var(--c-ground-55);
    border: 1px solid var(--c-ink-14);
    flex-shrink: 0;
  }
  .field--open {
    width: 430px;
  }
  .field--open:active {
    transform: scale(0.98);
  }
  .field--search {
    height: 64px;
    flex: 1;
    min-width: 0;
    max-width: 1100px;
  }
  .field--search:focus-within {
    border-color: var(--c-lms-55);
  }
  .field__glyph {
    color: var(--ink-muted);
    display: flex;
  }
  .field__hint {
    flex: 1;
    min-width: 0;
    font-size: 19px;
    color: var(--ink-quiet);
    white-space: nowrap;
    overflow: hidden;
  }
  .field__in {
    flex: 1;
    min-width: 0;
    appearance: none;
    background: none;
    border: 0;
    outline: none;
    padding: 0;
    font: inherit;
    font-size: 20px;
    font-weight: 600;
    color: var(--ink);
    caret-color: var(--accent-lms);
  }
  .field__in::-webkit-search-cancel-button {
    display: none;
  }
  .field__clear {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--ink-fill);
    color: var(--ink-muted);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  /* The directory out of reach: 12 under the header; what is below moves
     down 76 (P04). */
  .banner {
    position: relative;
    padding: 12px 40px 4px;
    flex-shrink: 0;
  }

  .body {
    position: relative;
    flex: 1;
    min-height: 0;
  }
  .top {
    position: absolute;
    inset: 0;
  }
  .strip {
    position: relative;
    flex-shrink: 0;
  }
</style>
