<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The phone's picture of the bands (ADR-0162; design/source/20, P01): the same
  line and fill as the panel's, 104 px tall, a ring dot at each band, the
  bands' names under it. The bands are set in the rows below it (EqRows).
-->
<script>
  import { ridge } from '../../lib/equaliser.svelte.js';

  let { levels, bands, drag = -1 } = $props();

  const path = $derived(ridge(levels, 200));
  const id = `eqp${Math.random().toString(36).slice(2, 8)}`;
</script>

<div class="curve">
  <div class="edge" style:top="0"></div>
  <div class="edge" style:top="100%"></div>
  <svg viewBox="0 0 1000 200" preserveAspectRatio="none" aria-hidden="true">
    <defs>
      <linearGradient id={id} gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="200">
        <stop offset="0" stop-color="#f2b35e" stop-opacity="0.95" />
        <stop offset="0.3" stop-color="#ef8f7a" stop-opacity="0.75" />
        <stop offset="0.5" stop-color="#ef8f7a" stop-opacity="0.26" />
        <stop offset="0.5" stop-color="#7fb0dc" stop-opacity="0.26" />
        <stop offset="0.7" stop-color="#7f9fe6" stop-opacity="0.75" />
        <stop offset="1" stop-color="#a48ce8" stop-opacity="0.95" />
      </linearGradient>
    </defs>
    <path d={path.area} fill={`url(#${id})`} />
    <path d={path.line} fill="none" stroke="#f4f1ea" stroke-width="2" stroke-linejoin="round"
          vector-effect="non-scaling-stroke" />
  </svg>
  <div class="zeroline"></div>
  {#each levels as g, i (i)}
    <span class="dot" class:is-dragging={drag === i}
          style:left={`${(i + 0.5) * 10}%`} style:top={`${((12 - g) / 24) * 100}%`}></span>
  {/each}
</div>
<div class="labels">
  {#each bands as label (label)}
    <div>{label}</div>
  {/each}
</div>

<style>
  .curve {
    position: relative;
    height: 104px;
    margin: 0 2px;
  }
  .edge {
    position: absolute;
    left: 0;
    right: 0;
    height: 1px;
    background: rgba(233, 238, 242, 0.05);
  }
  svg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    overflow: visible;
    pointer-events: none;
  }
  .zeroline {
    position: absolute;
    left: 0;
    right: 0;
    top: 50%;
    height: 1px;
    background: rgba(233, 238, 242, 0.3);
  }
  .dot {
    position: absolute;
    width: 12px;
    height: 12px;
    margin: -6px 0 0 -6px;
    border-radius: 50%;
    box-sizing: border-box;
    border: 2px solid #f4f1ea;
    background: #0d151c;
  }
  .dot.is-dragging {
    background: #f4f1ea;
  }
  .labels {
    display: flex;
    margin: 6px 2px 0;
  }
  .labels div {
    flex: 1;
    min-width: 0;
    text-align: center;
    font-family: var(--font-mono);
    font-size: 11px;
    color: rgba(233, 238, 242, 0.6);
  }
</style>
