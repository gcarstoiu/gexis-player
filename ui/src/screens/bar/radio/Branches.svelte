<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **By genre, By country, By language on a bar** (design/source/31,
  `BranchRow`; B11): cards 330 x 80 in columns of three, each with its
  count; a tap opens its stations, there is nothing to select. Genres A to
  Z, languages most stations first, countries A to Z with the player's own
  first, as the panel's *Your country* (BranchList.svelte).
-->
<script>
  import Sideways from './Sideways.svelte';
  import Icon from '../../radio/Icon.svelte';
  import { loadCountries, loadGenres, loadLanguages, count } from '../../../lib/radio.js';

  let { kind, country = null, onopen, onunreachable, onkept, oncount = null } = $props();

  let rows = $state(null);

  //: The directory's names are lower case (`hip hop`); the design writes *Hip hop*.
  const named = (name) => (name ? name[0].toLocaleUpperCase('en') + name.slice(1) : '');

  $effect(() => {
    const k = kind;
    rows = null;
    const read = k === 'genres' ? loadGenres() : k === 'countries' ? loadCountries() : loadLanguages();
    read
      .then((body) => {
        if (k !== kind) return;
        if (body.reachable === false) onkept?.();
        const list = body[k] ?? [];
        if (k === 'languages') rows = [...list].sort((a, b) => (b.stations ?? 0) - (a.stations ?? 0));
        else rows = [...list].sort((a, b) => named(a.name).localeCompare(named(b.name), 'en'));
        if (k === 'countries' && country) {
          const mine = rows.find((r) => r.code === country);
          if (mine) rows = [mine, ...rows.filter((r) => r !== mine)];
        }
      })
      .catch((err) => {
        if (k !== kind) return;
        rows = [];
        if (err.unreachable) onunreachable?.();
        console.info('radio:', err.message);
      });
  });

  $effect(() => {
    oncount?.(rows ? rows.length : null);
  });

  const labelOf = (row) => (kind === 'countries' ? row.name : named(row.name));
</script>

{#if rows?.length}
  <Sideways>
    <div class="grid">
      {#each rows as row (row.code ?? row.name)}
        <button class="branch" type="button" onclick={() => onopen({ ...row, label: labelOf(row) })}>
          <span class="branch__name">{labelOf(row)}</span>
          {#if row.stations != null}<span class="branch__count">{count(row.stations)}</span>{/if}
          <span class="branch__chev"><Icon name="chevron" size={20} width={2.4} /></span>
        </button>
      {/each}
    </div>
  </Sideways>
{/if}

<style>
  .grid {
    display: grid;
    grid-auto-flow: column;
    grid-template-rows: repeat(3, 80px);
    grid-auto-columns: calc(330px * max(1, var(--text-scale, 1)));
    gap: 14px 16px;
  }
  .branch {
    min-width: 0;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 14px 0 20px;
    border-radius: var(--r-18);
    background: var(--c-ink-5_5);
    border: 1px solid var(--c-ink-14);
    color: var(--ink);
    font: inherit;
    text-align: left;
  }
  .branch:active {
    background: var(--c-ink-12);
    transform: scale(0.98);
  }
  .branch__name {
    flex: 1;
    min-width: 0;
    font-size: 21px;
    font-weight: 700;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .branch__count {
    font-family: var(--font-mono);
    font-size: 14px;
    color: var(--ink-quiet);
  }
  .branch__chev {
    color: var(--ink-tab-off);
    display: flex;
  }
</style>
