<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **A genre, a country or a language** (design/source/31, `BranchRow`;
  P12-P14): its name, how many stations it has, a chevron. A tap opens its
  stations; there is nothing to select.
-->
<script>
  import Icon from './Icon.svelte';
  import { count } from '../../lib/radio.js';
  import { pressing } from '../../lib/press.svelte.js';

  let { name, stations = null, onopen } = $props();
  const press = pressing();
</script>

<button class="branch" class:is-pressed={press.is('row')} type="button"
  onpointerdown={() => press.down('row')} onpointerup={press.up} onpointercancel={press.up}
  onclick={() => press.act(onopen)}>
  <span class="branch__name">{name}</span>
  {#if stations != null}<span class="branch__count">{count(stations)}</span>{/if}
  <span class="branch__chev"><Icon name="chevron" size={20} width={2.4} /></span>
</button>

<style>
  .branch {
    height: 60px;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 0 14px 0 18px;
    border-radius: var(--r-14);
    background: transparent;
    border: 0;
    color: var(--ink);
    font: inherit;
    text-align: left;
  }
  .branch:active,
  .branch.is-pressed {
    background: var(--ink-fill);
  }
  .branch__name {
    flex: 1;
    min-width: 0;
    font-size: 19px;
    font-weight: 600;
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
