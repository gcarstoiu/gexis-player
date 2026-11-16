<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  design/source/31 (H07): a list still coming - *LOADING…*, then three
  skeleton rows: a 46 tile and two bars, as the panel's.
-->
<script>
  const ROWS = [[200, 140], [170, 120], [210, 150]];
</script>

<div class="loading" role="status">LOADING…</div>
{#each ROWS as [a, b], i (i)}
  <div class="bone" aria-hidden="true">
    <span class="tile"></span>
    <span class="bars">
      <span class="bar1" style:width="{a}px"></span>
      <span class="bar2" style:width="{b}px"></span>
    </span>
  </div>
{/each}

<style>
  .loading {
    padding: 8px 10px 0;
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.2em;
    color: var(--ink-quiet);
  }
  .bone {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 11px 12px 11px 14px;
  }
  .tile {
    width: 46px;
    height: 46px;
    flex-shrink: 0;
    border-radius: var(--r-13);
    background: var(--skeleton-tile);
  }
  .bars {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 9px;
  }
  .bar1,
  .bar2 {
    display: block;
    max-width: 100%;
  }
  .bar1 {
    height: 14px;
    border-radius: var(--r-7);
    background: var(--skeleton-line-1);
  }
  .bar2 {
    height: 10px;
    border-radius: var(--r-5);
    background: var(--skeleton-line-2);
  }
</style>
