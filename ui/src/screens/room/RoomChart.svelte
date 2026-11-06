<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Room correction's chart (ADR-0175; design/source/29 §5): one speaker, 15 to
  300 Hz on a log axis, ±15 dB about the target's level, or wider in 5 dB
  steps when a curve goes past it (`span`, `chartSpan`). Drawn in this order:
  what the cuts take away, each position, the target (dotted), before (the
  positions' average) and after - measured solid, expected dashed. The lines
  differ by weight and dash as well as colour, so it reads without colour.

  `surface`: the phone's card (200 tall, the legend under it), the panel's
  (fills, a 30 Hz line and the limit named), the bar's (fills, the legend in
  a column at the right).
-->
<script>
  import { between, countWord, path, xAt } from '../../lib/room.svelte.js';

  //: `kind`: 'measured', 'expected', or '' (before and the target only);
  //: `span`: the chart's reach, ± dB, the same for both speakers.
  let { surface = 'phone', freqs = [], speaker = null, kind = 'measured', span = 15 } = $props();

  let w = $state(300);
  let h = $state(200);
  const big = $derived(surface !== 'phone');
  //: Both speakers have no after until the check measures them.
  const after = $derived(kind && speaker?.after?.length ? speaker.after : null);
  const shown = $derived(after ? kind : '');
  const d = $derived(speaker ? {
    gap: after ? between(freqs, speaker.before, after, w, h, span) : '',
    pos: speaker.positions.map((p) => path(freqs, p, w, h, span)).join(''),
    target: path(freqs, speaker.target, w, h, span),
    before: path(freqs, speaker.before, w, h, span),
    after: after ? path(freqs, after, w, h, span) : '',
  } : null);
  //: The ±10 and 0 lines' places on the reach.
  const at = (v) => `${(((span - v) / (2 * span)) * 100).toFixed(2)}%`;
  const count = $derived(countWord(speaker?.positions?.length ?? 0));
  const hz = $derived(surface === 'bar' ? [20, 50, 100] : surface === 'panel' ? [20, 30, 50, 100, 200] : [20, 50, 100, 200]);
  const grid = $derived(surface === 'panel' ? [20, 30, 50, 100, 200] : [20, 50, 100, 200]);
</script>

{#snippet sample(which)}
  <svg class="sample" width={big ? 26 : 22} height="10" viewBox="0 0 {big ? 26 : 22} 10" aria-hidden="true">
    {#if which === 'before'}
      <path d="M1 5h{big ? 24 : 20}" class="l-before" />
    {:else if which === 'pos'}
      <path d="M1 3h{big ? 24 : 20}M1 7h{big ? 24 : 20}" class="l-pos-sample" />
    {:else if which === 'target'}
      <path d="M2 5h{big ? 23 : 19}" class="l-target" />
    {:else}
      <path d="M1 5h{big ? 25 : 21}" class="l-after" class:is-expected={shown === 'expected'} />
    {/if}
  </svg>
{/snippet}

<div class="chart chart--{surface}">
  <div class="plotrow">
    <div class="ygut">
      {#if surface === 'panel'}<span class="ylab ylab--unit" style="top:0">dB</span>{/if}
      <span class="ylab" style="top:{at(10)}">+10</span>
      <span class="ylab ylab--zero" style="top:50%">0</span>
      <span class="ylab" style="top:{at(-10)}">−10</span>
    </div>
    <div class="plot" bind:clientWidth={w} bind:clientHeight={h}>
      <div class="hline" style="top:{at(10)}"></div>
      <div class="hline" style="top:{at(-10)}"></div>
      {#each grid as f (f)}
        <div class="vline" class:vline--faint={f === 30} style="left:{xAt(f)}"></div>
      {/each}
      <div class="limit" style="left:{xAt(250)}"></div>
      {#if surface === 'panel'}<span class="limit__label">250 Hz limit</span>{/if}
      <div class="zero"></div>
      {#if d}
        <svg viewBox="0 0 {w} {h}" class="lines" aria-hidden="true">
          {#if d.gap}<path d={d.gap} class="l-gap" />{/if}
          <path d={d.pos} class="l-pos" />
          <path d={d.target} class="l-target" />
          <path d={d.before} class="l-before" />
          {#if d.after}<path d={d.after} class="l-after" class:is-expected={shown === 'expected'} />{/if}
        </svg>
      {/if}
    </div>
    {#if surface === 'bar'}
      <div class="legend legend--col">
        <span class="key">{@render sample('before')}Before</span>
        <span class="key">{@render sample('pos')}Positions</span>
        <span class="key">{@render sample('target')}Target</span>
        {#if shown}<span class="key">{@render sample('after')}{shown === 'expected' ? 'Expected' : 'After'}</span>{/if}
      </div>
    {/if}
  </div>
  <div class="xrow">
    {#each hz as f (f)}<span class="xlab" style="left:{xAt(f)}">{f}</span>{/each}
    {#if surface === 'bar'}
      <span class="xlab xlab--limit" style="left:{xAt(250)}">250</span>
    {:else}
      <span class="xlab xlab--unit">Hz</span>
    {/if}
  </div>
  {#if surface !== 'bar'}
    <div class="legend">
      <span class="key">{@render sample('before')}Before, average of {count}</span>
      <span class="key">{@render sample('pos')}Each position</span>
      <span class="key">{@render sample('target')}Target</span>
      {#if shown === 'measured'}<span class="key">{@render sample('after')}After, measured</span>{/if}
      {#if shown === 'expected'}<span class="key">{@render sample('after')}After, expected</span>{/if}
      {#if surface === 'phone'}<span class="key"><span class="hatch"></span>Above 250 Hz, left alone</span>{/if}
    </div>
  {/if}
</div>

<style>
  .chart {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .chart--panel,
  .chart--bar {
    flex: 1;
  }
  .plotrow {
    display: flex;
    height: 200px;
  }
  .chart--panel .plotrow,
  .chart--bar .plotrow {
    flex: 1;
    min-height: 0;
    height: auto;
  }
  .chart--panel .plotrow {
    margin-top: 18px;
  }
  .ygut {
    width: 30px;
    flex-shrink: 0;
    position: relative;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--ink-quiet);
    text-align: right;
  }
  .chart--panel .ygut {
    width: 40px;
    font-size: 13px;
  }
  .chart--bar .ygut {
    width: 38px;
    font-size: 14px;
  }
  .ylab {
    position: absolute;
    right: 6px;
    transform: translateY(-50%);
  }
  .chart--panel .ylab,
  .chart--bar .ylab {
    right: 8px;
  }
  .ylab--zero {
    color: var(--ink-strong);
  }
  .plot {
    flex: 1;
    min-width: 0;
    position: relative;
  }
  .hline,
  .zero {
    position: absolute;
    left: 0;
    right: 0;
    height: 1px;
    background: var(--rc-grid);
  }
  .zero {
    top: 50%;
    background: var(--rc-zero);
  }
  .vline {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;
    background: var(--rc-grid);
  }
  .vline--faint {
    background: var(--c-ink-04);
  }
  .limit {
    position: absolute;
    top: 0;
    bottom: 0;
    right: 0;
    border-left: 1px dashed var(--rc-limit-edge);
    background: repeating-linear-gradient(135deg, var(--rc-limit-hatch) 0 1px, transparent 1px 6px);
  }
  .chart--panel .limit,
  .chart--bar .limit {
    background: repeating-linear-gradient(135deg, var(--rc-limit-hatch) 0 1px, transparent 1px 7px);
  }
  .limit__label {
    position: absolute;
    top: 8px;
    right: calc(6.1% + 8px);
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.06em;
    color: var(--ink-muted);
    white-space: nowrap;
  }
  .lines {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    overflow: visible;
    pointer-events: none;
  }
  path {
    fill: none;
    stroke-linejoin: round;
  }
  .l-gap {
    fill: var(--rc-cut-fill);
    stroke: none;
  }
  .l-pos {
    stroke: var(--rc-position);
    stroke-width: 1px;
  }
  .l-pos-sample {
    stroke: var(--c-ink-32);
    stroke-width: 1px;
  }
  .l-target {
    stroke: var(--rc-target);
    stroke-width: var(--rc-stroke-target);
    stroke-dasharray: var(--rc-dash-target);
    stroke-linecap: round;
  }
  .l-before {
    stroke: var(--rc-before);
    stroke-width: var(--rc-stroke-before);
  }
  .l-after {
    stroke: var(--rc-after);
    stroke-width: var(--rc-stroke-after);
  }
  .l-after.is-expected {
    stroke-dasharray: var(--rc-dash-expected);
  }
  .chart--panel .l-pos,
  .chart--bar .l-pos,
  .chart--panel .l-pos-sample,
  .chart--bar .l-pos-sample {
    stroke-width: 1.25px;
  }
  .chart--panel .l-target,
  .chart--bar .l-target {
    stroke-width: var(--rc-stroke-target-lg);
    stroke-dasharray: var(--rc-dash-target-lg);
  }
  .chart--panel .l-before,
  .chart--bar .l-before {
    stroke-width: var(--rc-stroke-before-lg);
  }
  .chart--panel .l-after,
  .chart--bar .l-after {
    stroke-width: var(--rc-stroke-after-lg);
  }
  .chart--panel .l-after.is-expected,
  .chart--bar .l-after.is-expected {
    stroke-dasharray: var(--rc-dash-expected-lg);
  }
  .xrow {
    position: relative;
    height: 22px;
    margin-left: 30px;
    flex-shrink: 0;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--ink-quiet);
  }
  .chart--panel .xrow {
    height: 28px;
    margin-left: 40px;
    font-size: 14px;
    color: var(--ink-muted);
  }
  .chart--bar .xrow {
    height: 24px;
    margin-left: 38px;
    margin-right: 150px;
    font-size: 14px;
    color: var(--ink-muted);
  }
  .xlab {
    position: absolute;
    top: 6px;
    transform: translateX(-50%);
  }
  .chart--panel .xlab {
    top: 8px;
  }
  .chart--bar .xlab {
    top: 4px;
  }
  .xlab--unit {
    left: auto;
    right: 0;
    transform: none;
    color: var(--ink-strong);
  }
  .xlab--limit {
    color: var(--ink-strong);
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    padding: 10px 4px 2px 10px;
    font-size: 13px;
    color: var(--c-ink-78);
  }
  .chart--panel .legend {
    gap: 8px 22px;
    padding: 12px 0 0 10px;
    font-size: 15px;
    flex-shrink: 0;
  }
  .legend--col {
    width: 150px;
    flex-shrink: 0;
    flex-direction: column;
    flex-wrap: nowrap;
    justify-content: center;
    gap: 9px;
    padding: 0 0 0 16px;
    font-size: 15px;
  }
  .key {
    display: flex;
    align-items: center;
    gap: 7px;
    white-space: nowrap;
  }
  .chart--panel .key,
  .legend--col .key {
    gap: 8px;
  }
  .sample {
    flex-shrink: 0;
  }
  .hatch {
    width: 14px;
    height: 12px;
    flex-shrink: 0;
    border-left: 1px dashed var(--rc-limit-edge);
    background: repeating-linear-gradient(135deg, var(--c-ink-28) 0 1px, transparent 1px 4px);
    display: block;
  }
</style>
