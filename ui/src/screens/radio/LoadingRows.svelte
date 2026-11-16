<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- **A list loading** (design/source/31, P16): *LOADING…*, then skeleton
     rows - a logo's tile and two bars - where the stations will be. -->
<script>
  let { rows = 4 } = $props();
  //: The artboard's bar lengths, in turn.
  const WIDTHS = [[300, 200], [220, 170], [270, 190], [240, 160]];
</script>

<div class="loading" role="status">LOADING…</div>
{#each Array.from({ length: rows }, (_, i) => WIDTHS[i % WIDTHS.length]) as [a, b], i (i)}
  <div class="skel" aria-hidden="true">
    <span class="skel__tile"></span>
    <span class="skel__lines">
      <span class="skel__line skel__line--1" style:width="{a}px"></span>
      <span class="skel__line skel__line--2" style:width="{b}px"></span>
    </span>
  </div>
{/each}

<style>
  .loading {
    padding: 8px 14px 2px;
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.2em;
    color: var(--ink-quiet);
    flex-shrink: 0;
  }
  .skel {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 11px 12px 11px 14px;
    flex-shrink: 0;
  }
  .skel__tile {
    width: 46px;
    height: 46px;
    border-radius: var(--station-logo-row-radius);
    background: var(--skeleton-tile);
    flex-shrink: 0;
  }
  .skel__lines {
    display: flex;
    flex-direction: column;
    gap: 9px;
  }
  .skel__line {
    display: block;
    border-radius: var(--r-pill);
  }
  .skel__line--1 {
    height: 14px;
    background: var(--skeleton-line-1);
  }
  .skel__line--2 {
    height: 10px;
    background: var(--skeleton-line-2);
  }
</style>
