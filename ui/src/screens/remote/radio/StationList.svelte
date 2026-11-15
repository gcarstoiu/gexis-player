<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  design/source/31 (H05, H07, H09): a list of the directory's stations on
  the phone - Popular here, a genre, a country, a language, search's
  results - fifty at a time, the next fifty asked for as the list nears its
  end, *LOADING…* and the skeleton rows while they come. With nothing kept
  from the last day, the banner and Retry in its place.
-->
<script>
  import { untrack } from 'svelte';
  import StationRow from './StationRow.svelte';
  import Loading from './Loading.svelte';
  import DirectoryBanner from './DirectoryBanner.svelte';

  let {
    //: (offset) => the route's answer: `{stations, end, reachable}`.
    load,
    //: A new key starts the list again (search's text).
    key = '',
    match = '',
    selected = null,
    isPlaying = () => false,
    isFavourite = (s) => !!s.favourite,
    onselect = () => {},
    onplay = () => {},
    onheart = () => {},
    //: 'ok' | 'kept' | 'none', as the answers say.
    ondirectory = () => {},
    onsay = () => {},
    //: What the list holds so far, and whether its end has come.
    count = $bindable(0),
    done = $bindable(false),
  } = $props();

  let stations = $state([]);
  let end = $state(false);
  let loading = $state(false);
  let unreachable = $state(false);
  let asked = 0;
  const NEAR_END_PX = 400;

  $effect(() => {
    void key;
    untrack(restart);
  });

  function restart() {
    asked += 1;
    stations = [];
    end = false;
    unreachable = false;
    loading = false;
    done = false;
    count = 0;
    more();
  }

  async function more() {
    if (loading || end) return;
    const mine = asked;
    loading = true;
    try {
      const body = await load(stations.length);
      if (mine !== asked) return;
      const seen = new Set(stations.map((s) => s.id));
      stations = [...stations, ...(body.stations ?? []).filter((s) => !seen.has(s.id))];
      end = body.end !== false || !(body.stations ?? []).length;
      ondirectory(body.reachable === false ? 'kept' : 'ok');
    } catch (error) {
      if (mine !== asked) return;
      end = true;
      if (error.unreachable) {
        unreachable = true;
        ondirectory('none');
      } else {
        onsay(error.message);
      }
    } finally {
      if (mine === asked) {
        loading = false;
        count = stations.length;
        done = end;
      }
    }
  }

  function scrolled(event) {
    const el = event.currentTarget;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_END_PX) more();
  }
</script>

<div class="list" onscroll={scrolled}>
  {#if unreachable}
    <div class="none"><DirectoryBanner kind="none" onretry={restart} /></div>
  {/if}
  {#each stations as station (station.id)}
    <StationRow {station} {match} selected={selected === station.id} playing={isPlaying(station)}
                favourite={isFavourite(station)} onselect={() => onselect(station)} onplay={() => onplay(station)}
                onheart={() => onheart(station)} />
  {/each}
  {#if loading}<Loading />{/if}
</div>

<style>
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
  .none {
    padding: 0 6px 8px;
  }
</style>
