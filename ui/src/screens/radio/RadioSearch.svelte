<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **Search** (design/source/31, pick 4; P18-P20): results as you type, the
  matched letters in the accent. The field is the header's (RadioScreen),
  typed with a keyboard or from the phone as the panel's other fields
  (ADR-0121). Under two letters the core finds nothing to look for, so the
  page says how to start rather than that nothing was found.
-->
<script>
  import StationList from './StationList.svelte';
  import Scroll from './Scroll.svelte';
  import Icon from './Icon.svelte';
  import { searchStations } from '../../lib/radio.js';

  let { text = '', playingId = null, isFavourite, onheart, onplay, onunreachable, onkept } = $props();

  //: Asked when typing pauses, as Lyrion's search is.
  const PAUSE_MS = 300;
  let query = $state('');
  $effect(() => {
    const words = text.trim().replace(/\s+/g, ' ');
    if (words.length < 2) {
      query = '';
      return;
    }
    const timer = setTimeout(() => (query = words), PAUSE_MS);
    return () => clearTimeout(timer);
  });
  const load = (offset) => searchStations(query, offset);
</script>

{#snippet state(head, note, found)}
  <div class="state">
    <span class="state__disc"><Icon name="search" size={30} /></span>
    <div class="state__head" class:state__head--found={found}>{head}</div>
    <div class="state__note">{note}</div>
  </div>
{/snippet}

{#snippet nothing(failed)}
  <!-- A search the directory could not answer: the banner says so. -->
  {#if !failed}{@render state(`No station is called “${query}”`, 'Search looks at station names. Try fewer letters, or look under By genre.', true)}{/if}
{/snippet}

{#if !query}
  {@render state('Type a station’s name', 'With a keyboard, or on your phone. Results come as you type.', false)}
{:else}
  <Scroll padding="22px 40px">
    <StationList {load} key={query} searching {query} {playingId} {isFavourite} {onheart} {onplay}
      {onunreachable} {onkept} empty={nothing} />
  </Scroll>
{/if}

<style>
  .state {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 14px;
    text-align: center;
  }
  .state__disc {
    width: 72px;
    height: 72px;
    border-radius: var(--r-circle);
    box-sizing: border-box;
    background: var(--c-ink-14);
    border: 1px solid var(--c-ink-30);
    color: var(--ink);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .state__head {
    font-size: 28px;
    font-weight: 700;
  }
  .state__head--found {
    font-size: 30px;
  }
  .state__note {
    font-size: 19px;
    color: var(--ink-muted);
    max-width: 640px;
  }
</style>
