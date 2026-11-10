<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Room correction's chart (ADR-0177; design/source/30 §2, George's pick 1d):
  one log axis from 15 Hz to 20 kHz, broken at 250 Hz into two panes, each as
  wide as its share of the axis. The bass on ±15 dB about the target's level,
  or wider in 5 dB steps when a curve goes past it (`span`, `chartSpan`);
  above it ±5 dB. Drawn in this order: what the cuts take away and what is
  raised, each position, the target (dotted, the bass's rise joined to the
  speaker's own slope), before (the positions' average) and after - measured
  solid, expected dashed. The lines differ by weight and dash as well as
  colour, so it reads without colour.

  With *Bass* chosen the upper pane is hatched and after stops at 250 Hz; a
  measurement from before Phase 30 has no curves above it.

  `surface`: the phone's card (the legend under it), the panel's (fills), the
  bar's (fills, no legend).
-->
<script>
  import { BASS_SHARE, countWord, FMAX, FMIN, fill, fx, LIMIT, path } from '../../lib/room.svelte.js';

  //: `kind`: 'measured', 'expected', or '' (before, positions and the target
  //: only); `span`: the bass pane's reach, ± dB, the same for both speakers;
  //: `reach`: 'bass' or 'full'; `range`: how far the measurement was made.
  let { surface = 'phone', freqs = [], speaker = null, kind = 'measured', span = 15, reach = 'full',
    range = 'full', legend = surface !== 'bar' } = $props();

  const big = $derived(surface !== 'phone');
  //: The design's sizes: the captions, the frequency labels, the least room
  //: between two of them, the gap at 250 Hz.
  const Z = $derived(big ? { cap: surface === 'panel' ? 26 : 24, lab: surface === 'panel' ? 21 : 19, minPx: 46, gap: 12 }
    : { cap: 22, lab: 17, minPx: 34, gap: 8 });
  const ABOVE_SPAN = 5;
  const TICKS = [100, 1000, 10000, 20, 50, 200, 500, 2000, 5000, 30];

  let width = $state(340);
  let heights = $state([160, 160]);

  const bassOnly = $derived(range !== 'full');
  const shut = $derived(bassOnly || reach === 'bass');
  //: Both speakers have no after until the check measures them.
  const afterCurve = $derived(!kind || !speaker ? null
    : reach === 'bass' || bassOnly ? (speaker.after_bass?.length ? speaker.after_bass : speaker.after) : speaker.after);
  const after = $derived(afterCurve?.length ? afterCurve : null);
  const shown = $derived(after ? kind : '');
  //: How far each curve goes: a bass-only measurement to 250 Hz, after under
  //: *Bass* too (just past it, so the line meets the pane's edge).
  const curvesTo = $derived(bassOnly ? LIMIT * 1.008 : Infinity);
  const afterTo = $derived(shut ? LIMIT * 1.05 : Infinity);

  const panes = $derived.by(() => {
    const wl = Math.round((width - Z.gap) * BASS_SHARE);
    return [
      { key: 'bass', x0: FMIN, x1: LIMIT, span, w: wl, cap: 'Bass', scale: `±${span} dB` },
      { key: 'above', x0: LIMIT, x1: FMAX, span: ABOVE_SPAN, w: Math.max(0, width - wl - Z.gap), cap: 'Above the bass',
        scale: `±${ABOVE_SPAN} dB` },
    ];
  });

  const label = (f) => (f >= 1000 ? `${f / 1000}k` : String(f));
  function ticks(p) {
    const acc = [];
    for (const f of TICKS) {
      if (f <= p.x0 * 1.06 || f >= p.x1 / 1.06) continue;
      const x = fx(f, p.x0, p.x1) * p.w;
      if (x < 16 || x > p.w - 26) continue;
      if (acc.every((a) => Math.abs(fx(a, p.x0, p.x1) * p.w - x) >= Z.minPx)) acc.push(f);
    }
    return acc.sort((a, b) => a - b);
  }
  //: The level lines: ±20, ±10 and 0 on a ±20 reach and wider; ±10 and 0
  //: on ±15; ±3 and 0 above the bass.
  const levels = (s) => (s >= 20 ? [20, 10, 0, -10, -20] : s >= 10 ? [10, 0, -10] : [3, 0, -3]);
  const top = (v, s) => `${(((s - v) / (2 * s)) * 100).toFixed(3)}%`;
  const pct = (v) => `${(v * 100).toFixed(3)}%`;
  const signed = (v) => (v > 0 ? `+${v}` : v < 0 ? `−${-v}` : '0');

  function drawn(p, i) {
    if (!speaker) return null;
    const w = p.w;
    const h = heights[i] || 1;
    const line = (c, upto = curvesTo) => (c?.length ? path(freqs, c, p, w, h, upto) : '');
    return {
      cut: after ? fill(freqs, speaker.before, after, p, w, h, Math.min(curvesTo, afterTo)) : '',
      raise: after ? fill(freqs, after, speaker.before, p, w, h, Math.min(curvesTo, afterTo)) : '',
      pos: (speaker.positions ?? []).map((c) => line(c)).join(''),
      target: line(speaker.target),
      before: line(speaker.before),
      after: after ? line(after, Math.min(curvesTo, afterTo)) : '',
    };
  }
  const d = $derived(panes.map((p, i) => drawn(p, i)));
  //: *Raised* in the legend only while something is.
  const raised = $derived(!!d[1]?.raise);
  const count = $derived(countWord(speaker?.positions?.length ?? 0));
</script>

{#snippet sample(which)}
  <svg class="sample" width="22" height="10" viewBox="0 0 22 10" aria-hidden="true">
    {#if which === 'before'}
      <path d="M1 5h20" class="l-before" />
    {:else if which === 'pos'}
      <path d="M1 3h20M1 7h20" class="l-pos-sample" />
    {:else if which === 'target'}
      <path d="M2 5h19" class="l-target" />
    {:else if which === 'after'}
      <path d="M1 5h21" class="l-after" class:is-expected={shown === 'expected'} />
    {:else}
      <rect x="0" y="0.5" width="22" height="9" rx="2" class="swatch swatch--{which}" />
    {/if}
  </svg>
{/snippet}

<div class="chart chart--{surface}">
  <div class="panes" bind:clientWidth={width} style="--gap:{Z.gap}px">
    {#each panes as p, i (p.key)}
      <div class="pane" style="width:{p.w}px">
        <div class="cap" style="height:{Z.cap}px"><span>{p.cap}</span><span class="cap__scale">{p.scale}</span></div>
        <div class="plot" bind:clientHeight={heights[i]}>
          {#each ticks(p).filter((f) => f !== LIMIT) as f (f)}
            <div class="vline" style="left:{pct(fx(f, p.x0, p.x1))}"></div>
          {/each}
          {#each levels(p.span) as v (v)}
            <div class="hline" class:hline--zero={v === 0} style="top:{top(v, p.span)}"></div>
            <span class="ylab" class:ylab--zero={v === 0} style="top:{top(v, p.span)}">{signed(v)}</span>
          {/each}
          {#if p.key === 'above' && shut}
            <div class="hatch"></div>
          {/if}
          {#if d[i]}
            <svg viewBox="0 0 {p.w} {heights[i] || 1}" preserveAspectRatio="none" class="lines" aria-hidden="true">
              {#if d[i].cut}<path d={d[i].cut} class="l-cut" />{/if}
              {#if d[i].raise}<path d={d[i].raise} class="l-raise" />{/if}
              <path d={d[i].pos} class="l-pos" />
              <path d={d[i].target} class="l-target" />
              <path d={d[i].before} class="l-before" />
              {#if d[i].after}<path d={d[i].after} class="l-after" class:is-expected={shown === 'expected'} />{/if}
            </svg>
          {/if}
          {#if p.key === 'above' && shut && p.w > 96}
            <div class="note"><span>{bassOnly ? 'Measured to 250 Hz only' : 'Left alone: Bass is chosen'}</span></div>
          {/if}
        </div>
        <div class="xrow" style="height:{Z.lab}px">
          {#if p.key === 'above'}<span class="xlab xlab--strong xlab--start">250</span>{/if}
          {#each ticks(p) as f (f)}<span class="xlab" style="left:{pct(fx(f, p.x0, p.x1))}">{label(f)}</span>{/each}
          {#if p.key === 'above'}<span class="xlab xlab--strong xlab--end">Hz</span>{/if}
        </div>
      </div>
    {/each}
  </div>
  {#if legend}
    <div class="legend">
      <span class="key">{@render sample('before')}{surface === 'phone' ? `Before, average of ${count}` : 'Before'}</span>
      <span class="key">{@render sample('pos')}Each position</span>
      <span class="key">{@render sample('target')}Target</span>
      {#if shown === 'measured'}<span class="key">{@render sample('after')}After, measured</span>{/if}
      {#if shown === 'expected'}<span class="key">{@render sample('after')}After, expected</span>{/if}
      {#if shown}<span class="key">{@render sample('cut')}Cut</span>{/if}
      {#if shown && raised}<span class="key">{@render sample('raise')}Raised</span>{/if}
    </div>
  {/if}
</div>

<style>
  .chart {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 0;
  }
  .chart--panel,
  .chart--bar {
    flex: 1;
  }
  .panes {
    position: relative;
    display: flex;
    gap: var(--gap);
    height: 236px;
  }
  @media (max-width: 379px) {
    .chart--phone .panes {
      height: 250px;
    }
  }
  .chart--panel .panes,
  .chart--bar .panes {
    flex: 1;
    min-height: 0;
    height: auto;
  }
  .pane {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  .cap {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 8px;
    white-space: nowrap;
    overflow: hidden;
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .chart--panel .cap,
  .chart--bar .cap {
    font-size: 12px;
  }
  .cap__scale {
    letter-spacing: 0.02em;
    text-transform: none;
    color: var(--ink);
  }
  .plot {
    position: relative;
    flex: 1;
    min-height: 0;
    border-radius: var(--r-sm);
    overflow: hidden;
    background: var(--rc-pane);
  }
  .vline {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;
    background: var(--rc-grid);
  }
  .hline {
    position: absolute;
    left: 0;
    right: 0;
    height: 1px;
    background: var(--rc-grid);
  }
  .hline--zero {
    background: var(--rc-zero);
  }
  .ylab {
    position: absolute;
    left: 5px;
    transform: translateY(-118%);
    font-family: var(--font-mono);
    font-size: 11px;
    line-height: 1;
    color: var(--ink-quiet);
  }
  .chart--panel .ylab,
  .chart--bar .ylab,
  .chart--panel .xrow,
  .chart--bar .xrow {
    font-size: 13px;
  }
  .ylab--zero {
    color: var(--ink-strong);
  }
  .hatch {
    position: absolute;
    inset: 0;
    border-left: 1px dashed var(--rc-limit-edge);
    background: repeating-linear-gradient(135deg, var(--rc-limit-hatch) 0 1px, transparent 1px 6px);
  }
  .note {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 8px;
    text-align: center;
  }
  .note span {
    padding: 5px 9px;
    border-radius: var(--r-7);
    background: var(--rc-note-ground);
    font-size: 12px;
    line-height: 1.3;
    text-wrap: balance;
    color: var(--ink-strong);
  }
  .chart--panel .note span,
  .chart--bar .note span {
    font-size: 14px;
  }
  .lines {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    pointer-events: none;
  }
  path {
    fill: none;
    stroke-linejoin: round;
  }
  .l-cut {
    fill: var(--rc-cut-fill);
    stroke: none;
  }
  .l-raise {
    fill: var(--rc-raise-fill);
    stroke: none;
  }
  .l-pos {
    stroke: var(--rc-position);
    stroke-width: var(--rc-stroke-position);
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
  .chart--bar .l-pos {
    stroke-width: var(--rc-stroke-position-lg);
  }
  .chart--panel .lines .l-target,
  .chart--bar .lines .l-target {
    stroke-width: var(--rc-stroke-target-lg);
    stroke-dasharray: var(--rc-dash-target-lg);
  }
  .chart--panel .lines .l-before,
  .chart--bar .lines .l-before {
    stroke-width: var(--rc-stroke-before-lg);
  }
  .chart--panel .lines .l-after,
  .chart--bar .lines .l-after {
    stroke-width: var(--rc-stroke-after-lg);
  }
  .chart--panel .lines .l-after.is-expected,
  .chart--bar .lines .l-after.is-expected {
    stroke-dasharray: var(--rc-dash-expected-lg);
  }
  .xrow {
    position: relative;
    flex-shrink: 0;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--ink-quiet);
  }
  .xlab {
    position: absolute;
    bottom: 0;
    line-height: 1;
    white-space: nowrap;
    transform: translateX(-50%);
  }
  .xlab--strong {
    color: var(--ink-strong);
  }
  .xlab--start {
    left: 0;
    transform: none;
  }
  .xlab--end {
    left: 100%;
    transform: translateX(-100%);
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 16px;
    flex-shrink: 0;
    font-size: 13px;
    color: var(--c-ink-78);
  }
  .chart--panel .legend {
    font-size: 15px;
  }
  .key {
    display: flex;
    align-items: center;
    gap: 7px;
    white-space: nowrap;
  }
  .sample {
    flex-shrink: 0;
  }
  .swatch--cut {
    fill: color-mix(in srgb, var(--rc-before) 40%, transparent);
  }
  .swatch--raise {
    fill: color-mix(in srgb, var(--rc-after) 40%, transparent);
  }
</style>
