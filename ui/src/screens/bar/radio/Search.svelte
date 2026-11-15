<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **Search on a bar** (design/source/31, pick 4; B12, B13): the field, 760
  x 60 at the top, typed with a keyboard or from the phone as the panel's
  other fields (ADR-0121), and beside it how many were found; the results
  in two rows under it, as you type. Nothing found: a grey disc and what to
  try. Under two letters the core finds nothing to look for, so the page
  says how to start (the panel's words, RadioSearch.svelte).
-->
<script>
  import StationCards from './StationCards.svelte';
  import Icon from '../../radio/Icon.svelte';
  import { searchStations, count } from '../../../lib/radio.js';

  let { playingId = null, isFavourite, onheart, onplay, onunreachable, onkept } = $props();

  let text = $state('');
  let field = $state(null);

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

  let found = $state(null);
  const aside = $derived(
    query && found?.n ? `${found.end ? count(found.n) : `${count(found.n)}+`} ${found.n === 1 ? 'station' : 'stations'} · type with a keyboard, or on your phone` : '',
  );

  //: Focused as it opens, so text typed on the phone lands in it from the
  //: tap that opened it (ADR-0121)...
  function focusOnOpen(node) {
    requestAnimationFrame(() => node.focus({ preventScroll: true }));
  }
  //: ...and kept there through a tap on a result, so more typing still lands in it.
  function keepTyping() {
    requestAnimationFrame(() => field?.focus({ preventScroll: true }));
  }
</script>

{#snippet state(head, note, under = false)}
  <div class="state" class:state--under={under}>
    <span class="state__disc"><Icon name="search" size={28} /></span>
    <div class="state__text">
      <span class="state__head">{head}</span>
      <span class="state__note">{note}</span>
    </div>
  </div>
{/snippet}

{#snippet nothing(failed)}
  <!-- A search the directory could not answer: the banner says so. -->
  {#if !failed}{@render state(`No station is called “${query}”`, 'Search looks at station names. Try fewer letters, or look under By genre.', true)}{/if}
{/snippet}

<div class="search" role="presentation" onpointerup={keepTyping}>
  <div class="top">
    <label class="field">
      <span class="field__glyph"><Icon name="search" size={22} /></span>
      <input class="field__in" type="search" bind:this={field} bind:value={text} use:focusOnOpen
        autocomplete="off" spellcheck="false" aria-label="Search stations" />
      {#if text}
        <button class="field__clear" type="button" aria-label="Clear" onclick={() => { text = ''; field?.focus(); }}>
          <Icon name="clear" size={18} width={2.4} />
        </button>
      {/if}
    </label>
    {#if aside}<span class="aside">{aside}</span>{/if}
  </div>

  {#if !query}
    {@render state('Type a station’s name', 'With a keyboard, or on your phone. Results come as you type.')}
  {:else}
    <div class="results">
      <StationCards {load} key={query} align="start" rowGap={12} {playingId} {isFavourite} {onheart} {onplay}
        {onunreachable} {onkept} oncount={(c) => (found = c)} empty={nothing} />
    </div>
  {/if}
</div>

<style>
  .search {
    position: absolute;
    inset: 0;
  }
  .top {
    position: absolute;
    left: 32px;
    right: 32px;
    top: 22px;
    display: flex;
    align-items: center;
    gap: 20px;
  }
  .field {
    width: 760px;
    max-width: 100%;
    height: 60px;
    box-sizing: border-box;
    border-radius: var(--r-pill);
    padding: 0 10px 0 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    background: var(--c-dark-101a21-55);
    border: 1px solid var(--c-ink-14);
    flex-shrink: 0;
  }
  .field:focus-within {
    border-color: var(--c-lms-55);
  }
  .field__glyph {
    color: var(--ink-muted);
    display: flex;
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
    border-radius: var(--r-circle);
    border: 0;
    padding: 0;
    background: var(--ink-fill);
    color: var(--ink-muted);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .aside {
    min-width: 0;
    font-family: var(--font-mono);
    font-size: 14px;
    letter-spacing: 0.06em;
    color: var(--ink-quiet);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  /* B12: two rows from y 116. */
  .results {
    position: absolute;
    left: 0;
    right: 0;
    top: 116px;
    bottom: 0;
  }
  /* B13: a grey disc (68), 28/700 and 19, in the room under the field. */
  .state {
    position: absolute;
    left: 32px;
    right: 32px;
    top: 110px;
    bottom: 0;
    display: flex;
    align-items: center;
    gap: 22px;
  }
  /* Nothing found is drawn by the results' row, which starts at 116. */
  .state--under {
    left: 32px;
    top: -6px;
  }
  .state__disc {
    width: 68px;
    height: 68px;
    border-radius: var(--r-circle);
    box-sizing: border-box;
    flex-shrink: 0;
    background: var(--c-ink-14);
    border: 1px solid var(--c-ink-30);
    color: var(--ink);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .state__text {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
  }
  .state__head {
    font-size: 28px;
    font-weight: 700;
  }
  .state__note {
    font-size: 19px;
    color: var(--ink-muted);
  }
</style>
