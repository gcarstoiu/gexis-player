<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  design/source/31 (`DirectoryBanner`, H04): the station directory cannot be
  reached. *kept*: the lists are the last day's; *none*: nothing is kept,
  and browsing is dimmed while the favourites still play. Retry asks again.
-->
<script>
  import { RADIO } from './glyphs.js';

  let { kind = 'kept', onretry = () => {}, retrying = false } = $props();
</script>

<div class="banner" role="status">
  <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
    {#each RADIO.cloudOff as d (d)}<path {d} />{/each}
  </svg>
  <span class="words">
    {kind === 'none'
      ? 'Can’t reach the station directory, and nothing from the last day is kept. Your favourites still play.'
      : 'Can’t reach the station directory. Lists show the last day.'}
  </span>
  <button type="button" disabled={retrying} onclick={onretry}>Retry</button>
</div>

<style>
  .banner {
    flex-shrink: 0;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 8px 10px 12px;
    border-radius: var(--r-14);
    background: var(--directory-ground);
    border: 1px solid var(--directory-line);
  }
  svg {
    flex-shrink: 0;
    fill: none;
    stroke: var(--accent-warn);
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .words {
    flex: 1;
    min-width: 0;
    font-size: 13px;
    line-height: 1.35;
  }
  button {
    flex-shrink: 0;
    height: 34px;
    padding: 0 12px;
    border-radius: var(--r-17);
    border: 1px solid var(--c-warn-50);
    background: transparent;
    color: var(--accent-warn);
    font: 700 13px var(--font-ui);
    cursor: pointer;
  }
  button:disabled {
    opacity: 0.5;
  }
</style>
