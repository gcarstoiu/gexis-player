<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **By genre, By country, By language** (design/source/31; P12-P14): the
  directory's branches in two columns, each with its count. Genres A to Z;
  languages most stations first; countries with *Your country* first, then
  every country A to Z beside a jump rail whose letters with no country are
  faint and inert.
-->
<script>
  import BranchRow from './BranchRow.svelte';
  import Scroll from './Scroll.svelte';
  import { loadCountries, loadGenres, loadLanguages, count } from '../../lib/radio.js';

  let { kind, country = null, onopen, onunreachable, onkept } = $props();

  let rows = $state(null);
  let failed = $state(false);

  //: The directory's names are lower case (`hip hop`); the design writes *Hip hop*.
  const named = (name) => (name ? name[0].toLocaleUpperCase('en') + name.slice(1) : '');
  const letterOf = (name) => {
    const c = (name ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '')[0]?.toUpperCase() ?? '';
    return /[A-Z]/.test(c) ? c : '#';
  };

  $effect(() => {
    const k = kind;
    rows = null;
    failed = false;
    const read = k === 'genres' ? loadGenres() : k === 'countries' ? loadCountries() : loadLanguages();
    read
      .then((body) => {
        if (k !== kind) return;
        if (body.reachable === false) onkept?.();
        const list = body[k] ?? [];
        if (k === 'languages') rows = [...list].sort((a, b) => (b.stations ?? 0) - (a.stations ?? 0));
        else rows = [...list].sort((a, b) => named(a.name).localeCompare(named(b.name), 'en'));
      })
      .catch((err) => {
        if (k !== kind) return;
        failed = true;
        rows = [];
        if (err.unreachable) onunreachable?.();
        console.info('radio:', err.message);
      });
  });

  const mine = $derived(kind === 'countries' && rows ? rows.find((r) => r.code === country) ?? null : null);
  const RAIL = ['#', ...'ABCDEFGHIJKLMNOPQRSTUVWXYZ'];
  const letters = $derived(new Set((rows ?? []).map((r) => letterOf(r.name))));

  let list = $state(null);
  function jump(letter) {
    const row = list?.querySelector(`[data-letter="${letter}"]`);
    const scroller = list?.closest('[data-radio-scroll]');
    if (!row || !scroller) return;
    const top = row.getBoundingClientRect().top - scroller.getBoundingClientRect().top + scroller.scrollTop;
    scroller.scrollTop = Math.max(0, top - 52);
  }
  const firstOf = $derived.by(() => {
    const seen = new Set();
    const out = new Set();
    for (const r of rows ?? []) {
      const l = letterOf(r.name);
      if (!seen.has(l)) {
        seen.add(l);
        out.add(r);
      }
    }
    return out;
  });
</script>

<Scroll padding={kind === 'countries' ? '20px 72px 20px 40px' : '20px 40px'} gap="0">
  {#if rows === null}
    <div class="kicker" role="status">LOADING…</div>
  {:else if kind === 'countries'}
    {#if mine}
      <div class="kicker">Your country</div>
      <div class="grid">
        <BranchRow name={mine.name} stations={mine.stations} onopen={() => onopen(mine)} />
      </div>
      <div class="gap"></div>
    {/if}
    {#if rows.length}
      <div class="kicker">Every country · A to Z</div>
      <div class="grid" bind:this={list}>
        {#each rows as row (row.code ?? row.name)}
          <span class="cell" data-letter={firstOf.has(row) ? letterOf(row.name) : null}>
            <BranchRow name={row.name} stations={row.stations} onopen={() => onopen(row)} />
          </span>
        {/each}
      </div>
    {/if}
  {:else if rows.length}
    <div class="kicker">
      {kind === 'genres'
        ? `${count(rows.length)} genres · stations in each`
        : `${count(rows.length)} languages, most stations first`}
    </div>
    <div class="grid">
      {#each rows as row (row.name)}
        <BranchRow name={named(row.name)} stations={row.stations} onopen={() => onopen({ ...row, label: named(row.name) })} />
      {/each}
    </div>
  {/if}
</Scroll>
{#if kind === 'countries' && rows?.length}
  <div class="rail" aria-label="Jump to a letter">
    {#each RAIL as letter (letter)}
      <button class="rail__key" class:is-empty={!letters.has(letter)} type="button" data-dpad-ring="none"
        disabled={!letters.has(letter)} onclick={() => jump(letter)}>{letter}</button>
    {/each}
  </div>
{/if}

<style>
  .kicker {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink-quiet);
    margin-bottom: 10px;
    flex-shrink: 0;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 2px 24px;
    flex-shrink: 0;
  }
  .cell {
    display: grid;
    min-width: 0;
  }
  .gap {
    height: 28px;
    flex-shrink: 0;
  }
  /* The jump rail: 28 wide, 14 from the right, from under the header to
     over the mini strip's place. */
  .rail {
    position: absolute;
    right: 14px;
    top: 16px;
    bottom: 14px;
    width: 28px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
  .rail__key {
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 600;
    line-height: 19px;
    color: var(--ink-strong);
    text-align: center;
    background: none;
    border: 0;
    padding: 0;
  }
  .rail__key.is-empty {
    color: var(--c-ink-28);
  }
  .rail__key:global([data-dpad-focus]) {
    color: var(--accent-lms);
  }
</style>
