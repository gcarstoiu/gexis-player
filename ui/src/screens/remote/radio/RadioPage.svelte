<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0180, design/source/31 §6 (12b, 13; H01-H16, H23-H24): the phone's
  Radio page, between Remote and Settings. Favourites first: the search
  field, the category chips scrolling sideways, then *Favourites · 7* with
  Add by address and Edit over the favourites themselves. The mini player at
  the foot while something plays; the directory's banner when it cannot be
  reached. Its sub-pages - Popular here, genres, countries, languages and
  each one's stations, the favourites and their edit - each have Back.

  Search types with the phone's own keyboard; results come as it types.
  *Lyrion's radio* shows while Lyrion's library is on, as on the panel; the
  phone has no Lyrion browsing of its own, so it opens nothing here.
-->
<script>
  import { onMount, untrack } from 'svelte';
  import { active } from '../../../lib/state.js';
  import { settingValues } from '../../../lib/settings.js';
  import {
    addFavourite, favourites, loadCountries, loadFavourites, loadGenres, loadLanguages, loadOverview, loadPopular,
    loadStations, orderFavourites, playFavourite, playStation, radio, refreshFavourites, removeFavourite,
    searchStations, wantFavourites,
  } from '../../../lib/radio.js';
  import HeartIcon from '../../../lib/HeartIcon.svelte';
  import { FILLED } from '../icons.js';
  import { RADIO } from './glyphs.js';
  import { byName, countryName, named } from './words.js';
  import StationRow from './StationRow.svelte';
  import StationList from './StationList.svelte';
  import BranchList from './BranchList.svelte';
  import SubHeader from './SubHeader.svelte';
  import Loading from './Loading.svelte';
  import DirectoryBanner from './DirectoryBanner.svelte';
  import FavouritesEdit from './FavouritesEdit.svelte';
  import RadioMini from './RadioMini.svelte';

  //: `adding`: Add by address's sheet is open; the remote holds the sheet,
  //: over the whole screen as its other sheets, and calls `added` and
  //: `addClosed` here.
  let { artwork = null, home = 0, adding = $bindable(false), onremote = () => {}, onsay = () => {} } = $props();

  // ── Where the page is ───────────────────────────────────────────────────
  let stack = $state([{ kind: 'root' }]);
  const top = $derived(stack.at(-1));
  let selected = $state(null);
  function go(view) {
    selected = null;
    stack = [...stack, view];
  }
  function back() {
    selected = null;
    if (stack.length > 1) stack = stack.slice(0, -1);
  }
  //: The Radio segment tapped again: the page's top, search closed.
  $effect(() => {
    void home;
    untrack(() => {
      stack = [{ kind: 'root' }];
      selected = null;
      query = '';
      searchEl?.blur();
      adding = false;
    });
  });

  // ── The directory ───────────────────────────────────────────────────────
  //: 'ok', 'kept' (the last day's lists) or 'none' (nothing kept).
  let directory = $state('ok');
  let retrying = $state(false);
  let country = $state(null);
  onMount(async () => {
    wantFavourites();
    try {
      const overview = await loadOverview();
      country = overview.country ?? null;
      if (overview.reachable === false) probe();
    } catch (error) {
      onsay(error.message);
    }
  });
  //: Whether the last day's lists are kept, or the directory answers again:
  //: the first page of Popular here says.
  async function probe() {
    retrying = true;
    try {
      const body = await loadPopular(0);
      directory = body.reachable === false ? 'kept' : 'ok';
    } catch (error) {
      if (error.unreachable) directory = 'none';
    } finally {
      retrying = false;
    }
  }

  // ── Favourites, and the hearts ──────────────────────────────────────────
  //: What a tap asked for shows at once; the next list from the player
  //: (on every change, lib/radio.js) is the truth again.
  let asked = $state({});
  let gone = $state({});
  $effect(() => {
    void $favourites;
    untrack(() => {
      asked = {};
      gone = {};
    });
  });
  const favs = $derived(($favourites ?? []).filter((s) => !gone[s.id]));
  const favIds = $derived(new Set(favs.map((s) => s.id)));
  const isFavourite = (s) => asked[s.id] ?? ($favourites ? favIds.has(s.id) : !!s.favourite);
  const playingId = $derived($active === 'radio' && ['playing', 'connecting', 'reconnecting'].includes($radio?.state)
    ? $radio?.station?.id ?? null : null);
  const isPlaying = (s) => s.id === playingId;

  function select(s) {
    selected = selected === s.id ? null : s.id;
  }
  async function play(s, favourite = false) {
    selected = null;
    try {
      await (favourite ? playFavourite(s.id) : playStation(s));
    } catch (error) {
      onsay(error.message);
    }
  }
  async function heart(s) {
    const was = isFavourite(s);
    asked = { ...asked, [s.id]: !was };
    try {
      await (was ? removeFavourite(s.id) : addFavourite(s));
      refreshFavourites();
    } catch (error) {
      const { [s.id]: _, ...rest } = asked;
      asked = rest;
      onsay(error.message);
    }
  }
  //: In a list of favourites the heart removes, and the page offers Undo.
  async function remove(s) {
    const before = ($favourites ?? []).map((f) => f.id);
    gone = { ...gone, [s.id]: true };
    if (selected === s.id) selected = null;
    try {
      await removeFavourite(s.id);
      tell({ kind: 'removed', station: s, before }, 6000);
      refreshFavourites();
    } catch (error) {
      const { [s.id]: _, ...rest } = gone;
      gone = rest;
      onsay(error.message);
    }
  }
  async function undo() {
    const t = toast;
    toast = null;
    if (t?.kind !== 'removed') return;
    try {
      await addFavourite(t.station);
      const now = ((await loadFavourites()).favourites ?? []).map((f) => f.id);
      const want = [...t.before.filter((id) => now.includes(id)), ...now.filter((id) => !t.before.includes(id))];
      if (want.join() !== now.join()) await orderFavourites(want);
    } catch (error) {
      onsay(error.message);
    } finally {
      refreshFavourites();
    }
  }
  async function reorder(ids) {
    try {
      await orderFavourites(ids);
    } catch (error) {
      onsay(error.message);
    } finally {
      refreshFavourites();
    }
  }

  // ── What the page says (H12, H16) ───────────────────────────────────────
  let toast = $state(null);
  let toastTimer;
  function tell(what, ms) {
    toast = what;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toast = null), ms);
  }

  // ── Add by address (H13-H16) ────────────────────────────────────────────
  //: Over the favourites, as drawn; Cancel goes back to where it was opened.
  function openAdd() {
    if (top.kind !== 'favourites') go({ kind: 'favourites', forAdd: true });
    adding = true;
  }
  export function addClosed() {
    adding = false;
    if (top.forAdd) back();
  }
  export function added(station) {
    adding = false;
    if (top.forAdd) stack = [...stack.slice(0, -1), { kind: 'favourites' }];
    tell({ kind: 'added', name: station?.name ?? '' }, 5000);
    refreshFavourites();
  }

  // ── Search (H08-H10) ────────────────────────────────────────────────────
  let query = $state('');
  let focused = $state(false);
  let searchEl = $state(null);
  const searching = $derived(top.kind === 'root' && (focused || query.length > 0));
  //: Results as it types: asked once the typing pauses, from two letters.
  let typed = $state('');
  $effect(() => {
    const text = query.trim();
    const timer = setTimeout(() => (typed = text), 300);
    return () => clearTimeout(timer);
  });
  let found = $state(0);
  let foundAll = $state(false);
  function clear() {
    query = '';
    typed = '';
    searchEl?.focus();
  }

  // ── The branches: genres, countries, languages ──────────────────────────
  let branches = $state(null);
  let branchesFailed = $state(false);
  let branchesFor = null;
  $effect(() => {
    const kind = top.kind;
    if (!['genres', 'countries', 'languages'].includes(kind)) return;
    untrack(() => loadBranches(kind));
  });
  async function loadBranches(kind) {
    if (branchesFor === kind && branches) return;
    branchesFor = kind;
    branches = null;
    branchesFailed = false;
    try {
      let body;
      if (kind === 'genres') {
        body = await loadGenres();
        if (branchesFor !== kind) return;
        const items = (body.genres ?? []).map((g) => ({ key: g.name, name: named(g.name), stations: g.stations, genre: g.name }));
        items.sort((a, b) => a.name.localeCompare(b.name, 'en'));
        branches = { crumb: `Radio · ${items.length} genres`, groups: [{ items }] };
      } else if (kind === 'countries') {
        body = await loadCountries();
        if (branchesFor !== kind) return;
        const all = (body.countries ?? []).map((c) => ({ key: c.code, name: c.name, stations: c.stations, code: c.code }));
        const mine = all.find((c) => c.code === country);
        const groups = mine ? [{ kicker: 'Your country', items: [{ ...mine, key: `mine-${mine.code}` }] }] : [];
        groups.push({ kicker: 'Every country · A to Z', items: [...all].sort(byName) });
        branches = { crumb: `Radio · ${all.length} countries`, groups };
      } else {
        body = await loadLanguages();
        if (branchesFor !== kind) return;
        const items = (body.languages ?? []).map((l) => ({ key: l.name, name: named(l.name), stations: l.stations, language: l.name }));
        branches = { crumb: `Radio · ${items.length} languages`, groups: [{ items }] };
      }
      directory = body.reachable === false ? 'kept' : 'ok';
    } catch (error) {
      if (branchesFor !== kind) return;
      branchesFor = null;
      if (error.unreachable) {
        branchesFailed = true;
        directory = 'none';
      } else {
        onsay(error.message);
      }
    }
  }
  function openBranch(item) {
    if (top.kind === 'genres') go({ kind: 'genre', name: item.name, genre: item.genre });
    else if (top.kind === 'countries') go({ kind: 'country', name: item.name, code: item.code });
    else go({ kind: 'language', name: item.name, language: item.language });
  }

  // ── The chips (H01): §8's discs ─────────────────────────────────────────
  //: *Lyrion's radio* while Lyrion's library is on (as the panel, ADR-0149).
  const lyrionOn = $derived($settingValues.lms_enabled !== false && $settingValues.lms_library !== false);
  const CHIPS = [
    { key: 'popular', name: 'Popular here', tint: 'bluetooth', glyph: 'pin' },
    { key: 'genres', name: 'By genre', tint: 'artist', glyph: 'note' },
    { key: 'countries', name: 'By country', tint: 'radio', glyph: 'globe' },
    { key: 'languages', name: 'By language', tint: 'display', glyph: 'speech' },
  ];
  const stationsCrumb = (n) => `${n} ${n === 1 ? 'station' : 'stations'}`;
</script>

{#snippet glyph(kind)}
  {#if kind === 'pin'}
    <svg viewBox="0 0 24 24" width="14" height="14" class="stroke" aria-hidden="true"><path d={RADIO.pin} /><circle cx="12" cy="10" r="2.3" /></svg>
  {:else if kind === 'note'}
    <svg viewBox="0 0 24 24" width="14" height="14" class="fill" aria-hidden="true"><path d={FILLED.note} /></svg>
  {:else if kind === 'globe'}
    <svg viewBox="0 0 24 24" width="14" height="14" class="stroke" aria-hidden="true"><circle cx="12" cy="12" r="8.6" /><ellipse cx="12" cy="12" rx="3.8" ry="8.6" /><path d={RADIO.globe} /></svg>
  {:else if kind === 'speech'}
    <svg viewBox="0 0 24 24" width="14" height="14" class="stroke" aria-hidden="true"><path d={RADIO.speech} /></svg>
  {:else}
    <span class="lyrion" aria-hidden="true"><i style:height="6px"></i><i style:height="13px"></i><i style:height="9px"></i><i style:height="11px"></i></span>
  {/if}
{/snippet}

{#snippet done()}
  <button class="done" type="button" onclick={back}>Done</button>
{/snippet}

<div class="radio">
  <div class="body">
    {#if top.kind === 'root'}
      <div class="search" class:is-on={focused} class:is-off={directory === 'none'} role="search"
           inert={directory === 'none'}>
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.3" /><path d={RADIO.search} /></svg>
        <input bind:this={searchEl} bind:value={query} type="search" enterkeyhint="search" autocomplete="off"
               autocapitalize="off" autocorrect="off" spellcheck="false" placeholder="Search stations"
               aria-label="Search stations" onfocus={() => (focused = true)} onblur={() => (focused = false)}
               onkeydown={(e) => { if (e.key === 'Enter') searchEl.blur(); }} />
        {#if query}
          <button class="clear" type="button" aria-label="Clear" onpointerdown={(e) => e.preventDefault()} onclick={clear}>
            <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d={RADIO.clear} /></svg>
          </button>
        {/if}
      </div>

      {#if searching}
        {#if typed.length < 2}
          <div class="hint">
            <span class="hint__title">Type a station’s name</span>
            <span class="hint__text">Results come as you type.</span>
          </div>
        {:else}
          {#if foundAll && found === 0}
            <div class="nothing">
              <span class="nothing__disc"><svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.3" /><path d={RADIO.search} /></svg></span>
              <span class="nothing__title">No station is called “{typed}”</span>
              <span class="nothing__text">Search looks at station names. Try fewer letters, or look under By genre.</span>
            </div>
          {:else if found > 0}
            <div class="kicker kicker--found"><span class="kicker__text">Stations · {found}{foundAll ? '' : '+'}</span></div>
          {/if}
          <StationList load={(offset) => searchStations(typed, offset)} key={typed} match={typed} {selected} {isPlaying}
                       {isFavourite} onselect={select} onplay={(s) => play(s)} onheart={heart} {onsay}
                       ondirectory={(d) => (directory = d)} bind:count={found} bind:done={foundAll} />
        {/if}
      {:else}
        {#if directory !== 'ok'}
          <div class="banner"><DirectoryBanner kind={directory} {retrying} onretry={probe} /></div>
        {/if}
        <div class="chips">
          {#each CHIPS as chip (chip.key)}
            <button class="chip" class:is-off={directory === 'none'} inert={directory === 'none'} type="button"
                    style:--tint="var(--accent-{chip.tint})" style:--tint-rgb="var(--c-{chip.tint}-rgb)"
                    onclick={() => go({ kind: chip.key })}>
              <span class="disc">{@render glyph(chip.glyph)}</span>{chip.name}
            </button>
          {/each}
          {#if lyrionOn}
            <button class="chip" type="button" style:--tint="var(--accent-lms)" style:--tint-rgb="var(--c-lms-rgb)">
              <span class="disc">{@render glyph('lyrion')}</span>Lyrion’s radio
            </button>
          {/if}
        </div>
        <div class="kicker">
          <span class="kicker__text">{favs.length ? `Favourites · ${favs.length}` : 'Favourites'}</span>
          <span class="kicker__acts">
            <button class="pill pill--add" type="button" onclick={openAdd}>
              <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">{#each RADIO.link as d (d)}<path {d} />{/each}</svg>
              Add by address
            </button>
            {#if favs.length}<button class="pill" type="button" onclick={() => go({ kind: 'edit' })}>Edit</button>{/if}
          </span>
        </div>
        {#if $favourites && !favs.length}
          <div class="empty">
            <span class="empty__disc"><HeartIcon size={24} ink="var(--favourite)" /></span>
            <span class="empty__title">No favourites yet</span>
            <span class="empty__text">Tap the heart on any station to keep it here, in your own order. Next and Previous then step through them, like a radio’s presets.</span>
          </div>
        {:else}
          <div class="list">
            {#each favs as station, i (station.id)}
              <StationRow {station} num={i + 1} selected={selected === station.id} playing={isPlaying(station)}
                          favourite={isFavourite(station)} onselect={() => select(station)}
                          onplay={() => play(station, true)} onheart={() => remove(station)} />
            {/each}
          </div>
        {/if}
      {/if}

    {:else if top.kind === 'favourites' || top.kind === 'edit'}
      <SubHeader title="Favourites" crumb={top.kind === 'edit' ? 'Drag to reorder' : top.forAdd && adding ? '' : stationsCrumb(favs.length)}
                 onback={top.kind === 'edit' ? back : () => { adding = false; back(); }}
                 end={top.kind === 'edit' ? done : null} />
      <div class="gap14"></div>
      {#if top.kind === 'edit'}
        <FavouritesEdit stations={favs} onorder={reorder} onremove={remove} />
      {:else}
        <div class="list">
          {#each favs as station, i (station.id)}
            <StationRow {station} num={i + 1} selected={selected === station.id} playing={isPlaying(station)}
                        favourite={isFavourite(station)} onselect={() => select(station)}
                        onplay={() => play(station, true)} onheart={() => remove(station)} />
          {/each}
        </div>
      {/if}

    {:else if top.kind === 'genres' || top.kind === 'countries' || top.kind === 'languages'}
      <SubHeader title={top.kind === 'genres' ? 'By genre' : top.kind === 'countries' ? 'By country' : 'By language'}
                 crumb={branches?.crumb ?? 'Radio'} onback={back} />
      <div class="gap10"></div>
      {#if branchesFailed}
        <div class="banner"><DirectoryBanner kind="none" onretry={() => loadBranches(top.kind)} /></div>
      {:else if branches}
        <BranchList groups={branches.groups} onopen={openBranch} />
      {:else}
        <div class="list"><Loading /></div>
      {/if}

    {:else}
      <SubHeader title={top.kind === 'popular' ? 'Popular here' : top.name}
                 crumb={top.kind === 'popular' ? (country ? `Radio · ${countryName(country)}` : 'Radio')
                   : top.kind === 'genre' ? 'Radio · By genre' : top.kind === 'country' ? 'Radio · By country' : 'Radio · By language'}
                 onback={back} />
      <div class="gap10"></div>
      <StationList key={`${top.kind}:${top.genre ?? top.code ?? top.language ?? ''}`}
                   load={(offset) => top.kind === 'popular' ? loadPopular(offset)
                     : loadStations({ genre: top.genre, country: top.code, language: top.language, offset })}
                   {selected} {isPlaying} {isFavourite} onselect={select} onplay={(s) => play(s)} onheart={heart} {onsay}
                   ondirectory={(d) => (directory = d)} />
    {/if}
  </div>

  {#if $active && !searching}<RadioMini {artwork} onopen={onremote} />{/if}

  {#if toast}
    <div class="toast" class:is-added={toast.kind === 'added'} role="status">
      {#if toast.kind === 'added'}
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d={FILLED.check} /></svg>
        <span class="toast__text"><b>{toast.name}</b> played, and is in your favourites</span>
      {:else}
        <span class="toast__text">Removed <b>{toast.station.name}</b></span>
        <button class="undo" type="button" onclick={undo}>Undo</button>
      {/if}
    </div>
  {/if}
</div>

<style>
  .radio {
    position: relative;
    height: 100%;
    display: flex;
    flex-direction: column;
  }
  .body {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .gap10 {
    flex-shrink: 0;
    height: 10px;
  }
  .gap14 {
    flex-shrink: 0;
    height: 14px;
  }

  /* The search field (H01, H08-H10): 50 tall at the page's top. */
  .search {
    flex-shrink: 0;
    height: 50px;
    margin: 0 16px;
    box-sizing: border-box;
    padding: 0 8px 0 16px;
    display: flex;
    align-items: center;
    gap: 10px;
    border-radius: var(--r-pill);
    background: var(--c-dark-101a21-55);
    border: 1px solid var(--c-ink-14);
  }
  .search.is-on {
    border-color: var(--c-lms-55);
  }
  .search.is-off {
    opacity: 0.4;
  }
  .search > svg {
    flex-shrink: 0;
    fill: none;
    stroke: var(--ink-muted);
    stroke-width: 2;
    stroke-linecap: round;
  }
  .search input {
    flex: 1;
    min-width: 0;
    height: 100%;
    border: 0;
    padding: 0;
    background: none;
    outline: none;
    color: var(--ink);
    caret-color: var(--accent-lms);
    font: 600 17px var(--font-ui);
    user-select: text;
    -webkit-user-select: text;
    -webkit-appearance: none;
    appearance: none;
  }
  .search input::placeholder {
    font-size: 16px;
    font-weight: 400;
    color: var(--ink-quiet);
  }
  .search input::-webkit-search-cancel-button {
    display: none;
  }
  .clear {
    width: 34px;
    height: 34px;
    flex-shrink: 0;
    border: 0;
    padding: 0;
    border-radius: 50%;
    background: var(--ink-fill);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }
  .clear svg {
    fill: none;
    stroke: var(--ink-muted);
    stroke-width: 2.2;
    stroke-linecap: round;
  }
  .hint {
    margin: 34px 24px 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .hint__title {
    font-size: 17px;
    font-weight: 700;
  }
  .hint__text {
    font-size: 15px;
    color: var(--ink-muted);
  }
  .nothing {
    margin: 40px 24px 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .nothing__disc {
    width: 52px;
    height: 52px;
    box-sizing: border-box;
    border-radius: 50%;
    background: var(--c-ink-14);
    border: 1px solid var(--c-ink-30);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .nothing__disc svg {
    fill: none;
    stroke: var(--ink);
    stroke-width: 2;
    stroke-linecap: round;
  }
  .nothing__title {
    margin-top: 6px;
    font-size: 19px;
    font-weight: 700;
  }
  .nothing__text {
    font-size: 15px;
    line-height: 1.45;
    color: var(--ink-muted);
  }

  /* The directory's banner (H04): the chips move down under it. */
  .banner {
    flex-shrink: 0;
    margin: 14px 16px 0;
  }
  .banner + .chips {
    margin-top: 9px;
  }

  /* The chips (`CategoryChip`): 44 tall, scrolling sideways. */
  .chips {
    flex-shrink: 0;
    margin-top: 14px;
    padding: 0 16px;
    display: flex;
    gap: 8px;
    overflow-x: auto;
    overscroll-behavior-x: contain;
    scrollbar-width: none;
  }
  .chips::-webkit-scrollbar {
    display: none;
  }
  .chip {
    flex-shrink: 0;
    height: 44px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 14px 0 6px;
    border-radius: var(--r-xl);
    background: var(--c-white-05);
    border: 1px solid var(--ink-line);
    color: var(--ink);
    font: 600 15px var(--font-ui);
    white-space: nowrap;
    cursor: pointer;
  }
  .chip:active {
    background: var(--c-white-10);
  }
  .chip.is-off {
    opacity: 0.4;
  }
  .disc {
    width: 32px;
    height: 32px;
    flex-shrink: 0;
    box-sizing: border-box;
    border-radius: 50%;
    background: rgba(var(--tint-rgb), var(--radio-glyph-ground));
    border: 1px solid rgba(var(--tint-rgb), var(--radio-glyph-line));
    color: var(--tint);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .disc .stroke {
    fill: none;
    stroke: currentColor;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .disc .fill {
    fill: currentColor;
  }
  .lyrion {
    height: 13px;
    display: flex;
    align-items: center;
    gap: 2px;
  }
  .lyrion i {
    display: block;
    width: 3px;
    border-radius: 3px;
    background: currentColor;
  }

  /* *Favourites · 7*, with Add by address and Edit at its right. */
  .kicker {
    flex-shrink: 0;
    min-height: 36px;
    margin: 20px 16px 4px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .kicker--found {
    min-height: 0;
    margin: 18px 16px 12px 24px;
  }
  .kicker__text {
    min-width: 0;
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .kicker__acts {
    flex-shrink: 0;
    display: flex;
    gap: 8px;
  }
  .pill {
    height: 36px;
    box-sizing: border-box;
    padding: 0 14px;
    border-radius: var(--r-18);
    border: 1px solid var(--c-ink-14);
    background: var(--ink-fill);
    color: var(--ink);
    font: 700 14px var(--font-ui);
    white-space: nowrap;
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
  }
  .pill--add {
    padding: 0 12px 0 8px;
  }
  .pill svg {
    flex-shrink: 0;
    fill: none;
    stroke: var(--ink-muted);
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .pill:active,
  .done:active {
    transform: scale(0.97);
  }

  .list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-width: none;
    padding: 0 10px 10px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .list::-webkit-scrollbar {
    display: none;
  }

  /* No favourites yet (`FavouritesEmpty`, H02). */
  .empty {
    flex-shrink: 0;
    margin: 4px 16px 0;
    box-sizing: border-box;
    padding: 22px 18px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    border-radius: var(--r-18);
    border: 1.5px dashed var(--favourites-empty-line);
  }
  .empty__disc {
    width: 56px;
    height: 56px;
    box-sizing: border-box;
    border-radius: 50%;
    background: rgba(var(--c-favourite-rgb), var(--radio-glyph-ground));
    border: 1px solid rgba(var(--c-favourite-rgb), var(--radio-glyph-line));
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .empty__title {
    font-size: 19px;
    font-weight: 700;
  }
  .empty__text {
    font-size: 15px;
    line-height: 1.45;
    color: var(--ink-muted);
  }

  .done {
    flex-shrink: 0;
    height: 40px;
    padding: 0 14px;
    border-radius: var(--r-20);
    border: 1px solid var(--c-lms-45);
    background: var(--c-lms-14);
    color: var(--accent-lms);
    font: 700 15px var(--font-ui);
    white-space: nowrap;
    cursor: pointer;
  }

  /* The toast (H12, H16): 56 tall, 96 from the foot. */
  .toast {
    position: absolute;
    left: 16px;
    right: 16px;
    bottom: 96px;
    z-index: 40;
    height: 56px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 8px 0 16px;
    border-radius: var(--r-lg);
    background: var(--bg-panel);
    border: 1px solid var(--c-ink-14);
    box-shadow: 0 14px 34px var(--c-black-50);
    font-size: 15px;
  }
  .toast.is-added {
    padding: 0 16px;
    border-color: var(--c-lms-45);
  }
  .toast svg {
    flex-shrink: 0;
    fill: var(--accent-lms);
  }
  .toast__text {
    flex: 1;
    min-width: 0;
    line-height: 1.35;
  }
  .undo {
    flex-shrink: 0;
    height: 40px;
    padding: 0 14px;
    border-radius: var(--r-20);
    border: 1px solid var(--c-lms-45);
    background: var(--c-lms-14);
    color: var(--accent-lms);
    font: 700 15px var(--font-ui);
    white-space: nowrap;
    cursor: pointer;
  }
</style>
