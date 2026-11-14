<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **A list of stations on a bar** (design/source/31; B09, B10, B12): *Popular
  here*, a genre's, a country's or a language's, or what a search found -
  two rows of cards flowing down then across, in pages of 50 (the core's
  `end` says the last), the next read as the row's end comes near. Skeleton
  cards stand where a page is on its way (B10); the side column says
  *Loading…* (`onloading`).
-->
<script>
  import { untrack } from 'svelte';
  import Sideways from './Sideways.svelte';
  import StationCard from './StationCard.svelte';

  let {
    //: `(offset) => Promise<{stations, end, reachable}>`.
    load,
    //: What makes this a different list (a new search's text): it starts again.
    key = null,
    playingId = null,
    isFavourite,
    onheart,
    onplay,
    //: The directory answered 503: nothing kept (the banner's `none`).
    onunreachable,
    //: The directory answered from the last day's lists (`reachable: false`).
    onkept,
    //: Whether a page is on its way, and how many stations so far (`{n, end}`).
    onloading = null,
    oncount = null,
    //: Search's rows start under its field, 12 apart (B12); the lists' are centred, 16 apart.
    align = 'center',
    rowGap = 16,
    //: Search's nothing-found takes the row's place.
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

  $effect(() => {
    onloading?.(loading);
  });
  $effect(() => {
    oncount?.({ n: stations.length, end });
  });

  //: B10: a page on its way fills the rest of the width.
  const skeletons = $derived(loading ? (stations.length ? 4 : 10) : 0);
</script>

{#if empty && !loading && stations.length === 0}
  {@render empty(failed)}
{:else}
  <Sideways {align} onnear={more}>
    <div class="grid" style:row-gap="{rowGap}px">
      {#each stations as station (station.id)}
        <StationCard
          {station}
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
      {#each Array.from({ length: skeletons }, (_, i) => i) as i (i)}
        <div class="skel" aria-hidden="true">
          <span class="skel__tile"></span>
          <span class="skel__lines"><span class="skel__line skel__line--1"></span><span class="skel__line skel__line--2"></span></span>
        </div>
      {/each}
    </div>
  </Sideways>
{/if}

<style>
  .grid {
    display: grid;
    grid-auto-flow: column;
    grid-template-rows: repeat(2, 120px);
    grid-auto-columns: max-content;
    column-gap: 16px;
  }
  /* B10's skeleton card: a 72 tile, bars 16 and 11 tall. */
  .skel {
    width: calc(430px * max(1, var(--text-scale, 1)));
    height: 120px;
    box-sizing: border-box;
    border-radius: var(--r-20);
    background: var(--c-ink-04);
    border: 1px solid var(--c-ink-08);
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 0 20px;
  }
  .skel__tile {
    width: 72px;
    height: 72px;
    border-radius: var(--station-logo-card-bar-radius);
    background: var(--skeleton-tile);
    flex-shrink: 0;
  }
  .skel__lines {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .skel__line {
    display: block;
    border-radius: var(--r-pill);
  }
  .skel__line--1 {
    width: 200px;
    height: 16px;
    background: var(--skeleton-line-1);
  }
  .skel__line--2 {
    width: 140px;
    height: 11px;
    background: var(--skeleton-line-2);
  }
</style>
