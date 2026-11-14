<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **Popular here's country** (ADR-0180; design/source/31 S02, S04): every
  country tzdata names, the one chosen first and the rest A to Z, each with
  its count of stations when the directory gave one. A dialog on the panel,
  a bottom sheet on a phone. A tap writes at once; Done, the scrim or Back
  closes. *From your time zone* is the core's tag on the country the row
  falls back to (`defaultTag`).
-->
<script>
  import { untrack } from 'svelte';
  import { count } from '../lib/radio.js';
  import { SheetPull } from './remote/sheetPull.svelte.js';

  //: `row`: the `radio_country` row. `listing`: `/stations/countries`'
  //: `{countries}` once read, for the counts. `onpick(code)` writes it and
  //: says whether it was taken.
  let { row, listing = null, phone = false, onpick, onclose } = $props();

  const pull = new SheetPull(() => onclose());
  let query = $state('');
  let chosen = $state(null);
  const selected = $derived(chosen ?? row.value);
  // Let go once the stored value has caught up.
  $effect(() => {
    if (chosen !== null && row.value === chosen) chosen = null;
  });

  // The order is the one the sheet opened with: a tap does not move a row.
  const first = untrack(() => row.value);
  const codes = $derived.by(() => {
    const all = row.options ?? [];
    return all.includes(first) ? [first, ...all.filter((c) => c !== first)] : all;
  });
  const listed = $derived(new Map((listing?.countries ?? []).map((c) => [c.code, c])));
  const fold = (text) => String(text ?? '').normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const shown = $derived.by(() => {
    const q = fold(query.trim());
    return codes
      .map((code) => ({ code, name: row.optionLabels?.[code] ?? code, tag: row.optionTags?.[code] ?? null,
                        stations: listed.get(code)?.stations ?? null, also: listed.get(code)?.name }))
      .filter((c) => !q || fold(c.name).includes(q) || fold(c.also).includes(q));
  });

  async function pick(code) {
    if (code === selected) return;
    chosen = code;
    if (!(await onpick(code)) && chosen === code) chosen = null;
  }
</script>

<div class="cs-scrim" role="presentation" onclick={onclose}></div>
<div class="cs" class:cs--phone={phone} class:is-pulled={pull.pull !== null} role="dialog" aria-label={row.label}
  style:transform={phone && pull.pull !== null ? `translateY(${pull.pull}px)` : null}
  ondpadback={(event) => { event.preventDefault(); onclose(); }}>
  <div class="cs__top" role="presentation" onpointerdown={phone ? pull.grab : null} onpointermove={phone ? pull.drag : null}
    onpointerup={phone ? (e) => pull.release(e) : null} onpointercancel={phone ? (e) => pull.release(e, true) : null}
    onclickcapture={phone ? pull.notTapped : null}>
    {#if phone}<span class="cs__grab" aria-hidden="true"></span>{/if}
    <div class="cs__head">
      <span class="cs__title">{row.label}</span>
      {#if !phone}<button class="cs__done" type="button" data-dpad-back onclick={onclose}>Done</button>{/if}
    </div>
    {#if row.note}<div class="cs__note">{row.note}</div>{/if}
  </div>
  <label class="cs__search" role="search">
    <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.3" /><path d="M15.3 15.3l5.2 5.2" /></svg>
    <input type="text" bind:value={query} placeholder="Search countries" aria-label="Search countries"
      autocomplete="off" autocapitalize="off" spellcheck="false" />
  </label>
  <div class="cs__list" role="radiogroup" aria-label={row.label} data-noscrollbar data-dpad-start>
    {#each shown as c (c.code)}
      <button class="cs__row" class:is-on={c.code === selected} type="button" role="radio"
        aria-checked={c.code === selected} onclick={() => pick(c.code)}>
        <span class="cs__radio"><span></span></span>
        <span class="cs__name">{c.name}{#if phone && c.tag}<span class="cs__tag">{c.tag}</span>{/if}</span>
        {#if !phone && c.tag}<span class="cs__tag">{c.tag}</span>{/if}
        {#if c.stations != null}
          <span class="cs__count">{phone ? count(c.stations) : `${count(c.stations)} ${c.stations === 1 ? 'station' : 'stations'}`}</span>
        {/if}
      </button>
    {:else}
      {#if query.trim()}<p class="cs__none">No country is called “{query.trim()}”</p>{/if}
    {/each}
  </div>
</div>

<style>
  /* Over Settings as its other sheets are (the scrim's 24, the sheet's 25). */
  .cs-scrim {
    position: absolute;
    inset: 0;
    z-index: 24;
    background: var(--bg-scrim);
  }
  /* S02: 760 wide, 60 from the top; a long list scrolls inside. */
  .cs {
    position: absolute;
    z-index: 25;
    left: 50%;
    top: 60px;
    transform: translateX(-50%);
    width: min(760px, calc(100% - 44px));
    max-height: calc(100% - 120px);
    box-sizing: border-box;
    padding: 26px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    color: var(--ink);
    background: var(--bg-panel);
    border: 1px solid var(--c-ink-14);
    border-radius: var(--r-xl);
    box-shadow: 0 30px 70px var(--c-black-55);
  }
  /* The bar's sheets fill its height (ADR-0109). */
  :global(.panel--bar) .cs {
    top: 12px;
    bottom: 12px;
    max-height: none;
    padding: 18px 20px 14px;
    gap: 12px;
  }
  .cs__top {
    display: flex;
    flex-direction: column;
    gap: 14px;
    flex-shrink: 0;
  }
  .cs__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }
  .cs__title {
    font-size: 25px;
    font-weight: 700;
  }
  .cs__done {
    height: 48px;
    padding: 0 22px;
    border-radius: var(--r-card);
    border: 1px solid var(--c-lms-45);
    background: var(--c-lms-14);
    color: var(--accent-lms);
    font: inherit;
    font-size: 17px;
    font-weight: 700;
    white-space: nowrap;
    flex-shrink: 0;
  }
  .cs__note {
    font-size: 16px;
    color: var(--ink-muted);
  }
  .cs__search {
    height: 52px;
    flex-shrink: 0;
    box-sizing: border-box;
    padding: 0 10px 0 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    border-radius: var(--r-26);
    background: var(--c-dark-101a21-55);
    border: 1px solid var(--c-ink-14);
  }
  .cs__search svg {
    width: 22px;
    height: 22px;
    flex-shrink: 0;
    fill: none;
    stroke: var(--ink-muted);
    stroke-width: 2;
    stroke-linecap: round;
  }
  .cs__search input {
    flex: 1;
    min-width: 0;
    padding: 0;
    border: 0;
    outline: none;
    background: none;
    color: var(--ink);
    font: inherit;
    font-size: 19px;
  }
  .cs__search input::placeholder {
    color: var(--ink-quiet);
  }
  .cs__list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .cs__row {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 14px;
    height: 58px;
    width: 100%;
    box-sizing: border-box;
    padding: 0 16px;
    border: 0;
    border-radius: var(--r-md);
    background: transparent;
    color: var(--ink);
    font: inherit;
    text-align: left;
  }
  .cs__row.is-on {
    background: var(--c-lms-12);
  }
  .cs__radio {
    width: 22px;
    height: 22px;
    flex-shrink: 0;
    box-sizing: border-box;
    border-radius: 50%;
    border: 2px solid var(--c-ink-40);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .cs__radio span {
    display: none;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--accent-lms);
  }
  .is-on .cs__radio {
    border-color: var(--accent-lms);
  }
  .is-on .cs__radio span {
    display: block;
  }
  .cs__name {
    flex: 1;
    min-width: 0;
    font-size: 18px;
    font-weight: 600;
  }
  .cs__tag {
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--accent-lms);
    white-space: nowrap;
  }
  .cs__count {
    min-width: 110px;
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--ink-quiet);
    white-space: nowrap;
    text-align: right;
  }
  .cs__none {
    margin: 0;
    padding: 18px 16px;
    font-size: 17px;
    color: var(--ink-muted);
  }

  /* S04: a bottom sheet, its tag under the name and the count alone. */
  .cs--phone {
    left: 0;
    right: 0;
    bottom: 0;
    top: 94px;
    width: auto;
    max-height: none;
    transform: none;
    padding: 12px 16px max(12px, env(safe-area-inset-bottom));
    gap: 12px;
    border: 0;
    border-top: 1px solid var(--c-ink-12);
    border-radius: var(--r-28) var(--r-28) 0 0;
    box-shadow: none;
    transition: transform 200ms ease;
  }
  .cs--phone.is-pulled {
    transition: none;
  }
  .cs--phone .cs__top {
    gap: 12px;
    touch-action: none;
  }
  .cs__grab {
    align-self: center;
    width: 44px;
    height: 5px;
    border-radius: 3px;
    background: var(--c-ink-30);
  }
  .cs--phone .cs__title {
    font-size: 21px;
    font-weight: 800;
  }
  .cs--phone .cs__note {
    margin-top: -6px;
    font-size: 14px;
  }
  .cs--phone .cs__search {
    height: 48px;
    border-radius: var(--r-card);
  }
  .cs--phone .cs__row {
    height: 52px;
    gap: 12px;
    padding: 0 12px;
  }
  .cs--phone .cs__name {
    font-size: 16px;
  }
  .cs--phone .cs__tag {
    display: block;
    font-size: 11px;
    font-weight: 400;
  }
  .cs--phone .cs__count {
    min-width: 0;
    font-size: 12px;
  }
</style>
