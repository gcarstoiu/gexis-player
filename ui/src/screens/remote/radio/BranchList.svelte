<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  design/source/31 (`BranchRow`, H06): genres, countries and languages on
  the phone - rows 54 tall, the name, the count with a thousands separator
  and a chevron. A tap opens the branch; there is nothing to select. Groups
  may carry a kicker (*Your country*, *Every country · A to Z*).
-->
<script>
  import { count } from '../../../lib/radio.js';
  import { RADIO } from './glyphs.js';

  let { groups = [], onopen = () => {} } = $props();
</script>

<div class="list">
  {#each groups as group, g (g)}
    {#if group.kicker}<div class="kicker">{group.kicker}</div>{/if}
    {#each group.items as item (item.key)}
      <button class="branch" type="button" onclick={() => onopen(item)}>
        <span class="name">{item.name}</span>
        <span class="count">{count(item.stations)}</span>
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d={RADIO.chevron} /></svg>
      </button>
    {/each}
  {/each}
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
  .kicker {
    padding: 10px 14px 4px;
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .branch {
    flex-shrink: 0;
    width: 100%;
    height: 54px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 8px 0 14px;
    border: 0;
    border-radius: var(--r-md);
    background: none;
    color: var(--ink);
    font-family: var(--font-ui);
    text-align: left;
    cursor: pointer;
  }
  .branch:active {
    background: var(--ink-fill);
  }
  .name {
    flex: 1;
    min-width: 0;
    font-size: 17px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .count {
    flex-shrink: 0;
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--ink-quiet);
  }
  svg {
    flex-shrink: 0;
    fill: none;
    stroke: var(--ink-tab-off);
    stroke-width: 2.4;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
</style>
