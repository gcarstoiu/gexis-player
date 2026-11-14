<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **A list of stations from the directory** (design/source/31; P11, P15-P17,
  P19): *Popular here*, a genre's, a country's or a language's, or what a
  search found. Pages of 50 (the core's `end` says the last), the next read
  as the list nears its foot; *LOADING…* and skeleton rows while a page is
  on its way, and the list's end with how many it held.
-->
<script>
  import { untrack } from 'svelte';
  import StationRow from './StationRow.svelte';
  import LoadingRows from './LoadingRows.svelte';
  import ListEnd from './ListEnd.svelte';
  import { count } from '../../lib/radio.js';

  let {
    //: `(offset) => Promise<{stations, end, reachable}>`.
    load,
    //: What makes this a different list (a new search's text): it starts again.
    key = null,
    //: The list's name for its end: *End of Jazz*.
    label = '',
    //: How many stations the branch said it has, for the kicker; null: none drawn.
    total = null,
    //: Search's kicker instead: *Stations · 23* and how to type.
    searching = false,
    query = '',
    playingId = null,
    isFavourite,
    onheart,
    onplay,
    //: The directory answered 503: nothing kept (the banner's `none`).
    onunreachable,
    //: The directory answered from the last day's lists (`reachable: false`).
    onkept,
    //: Search's own empty and nothing-found states take the list's place.
    empty = null,
  } = $props();

  let stations = $state([]);
  let end = $state(false);
  let loading = $state(false);
  let failed = $state(false);
  let selected = $state(null);
  let ticket = 0;

  async function more() {
    if (loading || end) return;
    const mine = ticket;
    loading = true;
    try {
      const page = await load(stations.length);
      if (mine !== ticket) return;
      stations = [...stations, ...(page.stations ?? [])];
      end = page.end !== false;
      if (page.reachable === false) onkept?.();
    } catch (err) {
      if (mine !== ticket) return;
      failed = true;
      end = true;
      if (err.unreachable) onunreachable?.();
      console.info('radio:', err.message);
    } finally {
      if (mine === ticket) loading = false;
    }
  }

  $effect(() => {
    void key;
    untrack(() => {
      ticket += 1;
      stations = [];
      end = false;
      failed = false;
      loading = false;
      selected = null;
      more();
    });
  });

  //: The next page is read while the last rows are still a screen away.
  let sentinel = $state(null);
  $effect(() => {
    if (!sentinel) return;
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) more();
    }, { root: sentinel.closest('[data-radio-scroll]'), rootMargin: '0px 0px 600px 0px' });
    observer.observe(sentinel);
    return () => observer.disconnect();
  });

  const shownTotal = $derived(end && !failed ? stations.length : null);
  const searchCount = $derived(end ? count(stations.length) : `${count(stations.length)}+`);
</script>

{#if searching && stations.length}
  <div class="kicker kicker--search">
    <span class="kicker__label">Stations · {searchCount}</span>
    <span class="kicker__aside">Type with a keyboard, or on your phone</span>
  </div>
{:else if !searching && total != null}
  <div class="kicker">
    <span class="kicker__label">{count(total)} stations</span>
  </div>
{/if}

{#if empty && !loading && stations.length === 0}
  {@render empty(failed)}
{:else}
  {#each stations as station (station.id)}
    <StationRow
      {station}
      {query}
      selected={selected === station.id}
      playing={playingId === station.id}
      favourite={isFavourite(station)}
      onselect={() => (selected = selected === station.id ? null : station.id)}
      onplay={() => {
        selected = null;
        onplay(station);
      }}
      onheart={() => onheart(station)}
    />
  {/each}
  {#if loading}
    <LoadingRows rows={stations.length ? 2 : 4} />
  {:else if end && !failed && stations.length && label}
    <ListEnd text={`End of ${label} · ${count(shownTotal)} ${shownTotal === 1 ? 'station' : 'stations'}`} />
  {/if}
  {#if !end}<span class="sentinel" bind:this={sentinel}></span>{/if}
{/if}

<style>
  .kicker {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 0 12px 6px 14px;
    flex-shrink: 0;
  }
  .kicker--search {
    padding-bottom: 8px;
  }
  .kicker__label {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .kicker__aside {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.06em;
    color: var(--ink-quiet);
  }
  .sentinel {
    display: block;
    height: 1px;
    flex-shrink: 0;
  }
</style>
