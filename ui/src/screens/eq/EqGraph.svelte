<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The equaliser's ten upright bands, panel and bars (ADR-0162; design/source/20,
  look 3a "Ridge"): the line through every knob, the fill between it and 0 dB,
  the value above each band, the Hz under it. +12 is the box's top edge, 0 the
  middle, -12 the bottom.

  A band is moved anywhere in its column - the whole column is the touch
  target, at least 44 px wide on every screen, though the knob is 34. On the
  D-pad each column is an upright slider: Up and Down move it, Left and Right
  go to its neighbours.
-->
<script>
  import { clamp, fmt, ridge, valueInk } from '../../lib/equaliser.svelte.js';

  let {
    levels,
    bands,
    surface = 'panel',
    drag = -1,
    disabled = false,
    onset,
    onend,
  } = $props();

  //: The knob's travel is the column, inset by this at each end (the design's).
  const pad = $derived(surface === 'bar' ? 24 : 26);
  const path = $derived(ridge(levels));
  const id = `eq${Math.random().toString(36).slice(2, 8)}`;

  let held = -1;

  function at(i, event) {
    const el = event.currentTarget;
    const r = el.getBoundingClientRect();
    const scale = r.height / (el.offsetHeight || r.height);
    const inset = pad * scale;
    onset?.(i, clamp(12 - ((event.clientY - r.top - inset) / (r.height - 2 * inset)) * 24));
  }
  function down(i, event) {
    if (disabled) return;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    held = i;
    at(i, event);
  }
  function move(i, event) {
    if (held === i) at(i, event);
  }
  function up() {
    if (held === -1) return;
    held = -1;
    onend?.();
  }
  function step(i, event) {
    if (disabled) return;
    onset?.(i, clamp(Math.round(levels[i]) + event.detail.step));
    onend?.();
  }
  const top = (g) => `${((12 - g) / 24) * 100}%`;
</script>

<div class="graph" class:graph--bar={surface === 'bar'}>
  <div class="vals">
    <span class="axis axis--label">{surface === 'bar' ? '' : 'dB'}</span>
    {#each levels as g, i (i)}
      {@const dragging = drag === i}
      <div class="val">
        <span class="chip" class:is-on={dragging}
              style:background={dragging ? (Math.round(g) === 0 ? '#e9eef2' : valueInk(g)) : 'transparent'}
              style:color={dragging ? '#0d151c' : valueInk(g)}>{fmt(g)}</span>
      </div>
    {/each}
  </div>

  <div class="box" style:margin={`${pad}px 0`}>
    <div class="axis axis--scale">
      <span style:top="0">+12</span>
      {#if surface !== 'bar'}<span style:top="25%">+6</span>{/if}
      <span class="zero" style:top="50%">0</span>
      {#if surface !== 'bar'}<span style:top="75%">{'−'}6</span>{/if}
      <span style:top="100%">{'−'}12</span>
    </div>
    <div class="plot">
      <div class="edge" style:top="0"></div>
      <div class="edge" style:top="100%"></div>
      <svg viewBox="0 0 1000 240" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id={id} gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="240">
            <stop offset="0" stop-color="#f2b35e" stop-opacity="0.95" />
            <stop offset="0.3" stop-color="#ef8f7a" stop-opacity="0.75" />
            <stop offset="0.5" stop-color="#ef8f7a" stop-opacity="0.26" />
            <stop offset="0.5" stop-color="#7fb0dc" stop-opacity="0.26" />
            <stop offset="0.7" stop-color="#7f9fe6" stop-opacity="0.75" />
            <stop offset="1" stop-color="#a48ce8" stop-opacity="0.95" />
          </linearGradient>
        </defs>
        <path d={path.area} fill={`url(#${id})`} />
        <path d={path.line} fill="none" stroke="#f4f1ea" stroke-width="2.5" stroke-linejoin="round"
              vector-effect="non-scaling-stroke" />
      </svg>
      <div class="zeroline"></div>
      <div class="cols" style:top={`-${pad}px`} style:bottom={`-${pad}px`}>
        {#each levels as g, i (i)}
          {@const dragging = drag === i}
          <div
            class="col"
            class:is-dragging={dragging}
            role="slider"
            tabindex="-1"
            aria-orientation="vertical"
            data-dpad-ring="outside"
            aria-label={`${bands[i]} Hz`}
            aria-valuemin="-12"
            aria-valuemax="12"
            aria-valuenow={Math.round(g)}
            aria-disabled={disabled}
            ondpadstep={(event) => step(i, event)}
            onpointerdown={(event) => down(i, event)}
            onpointermove={(event) => move(i, event)}
            onpointerup={up}
            onpointercancel={up}
          >
            <div class="col__ground"></div>
            <div class="col__centre" style:top={`${pad}px`} style:bottom={`${pad}px`}></div>
            <div class="knob" class:is-dragging={dragging} data-dpad-box
                 style:top={`calc(${pad}px + (100% - ${2 * pad}px) * ${(12 - g) / 24})`}></div>
          </div>
        {/each}
      </div>
    </div>
  </div>

  <div class="hz">
    <span class="axis axis--label">Hz</span>
    {#each bands as label (label)}
      <div class="hz__band">{label}</div>
    {/each}
  </div>
</div>

<style>
  .graph {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    margin-top: 8px;
  }
  .graph--bar {
    margin-top: 0;
  }
  .vals {
    display: flex;
    align-items: flex-end;
    height: 36px;
    flex-shrink: 0;
  }
  .graph--bar .vals {
    height: 30px;
  }
  .axis {
    width: 44px;
    flex-shrink: 0;
    font-family: var(--font-mono);
    font-size: 12px;
    color: rgba(233, 238, 242, 0.6);
  }
  .graph--bar .axis {
    width: 40px;
    font-size: 13px;
  }
  .axis--label {
    letter-spacing: 0.14em;
    padding-bottom: 6px;
  }
  .hz .axis--label {
    padding-bottom: 0;
  }
  .val {
    flex: 1;
    min-width: 0;
    display: flex;
    justify-content: center;
  }
  .chip {
    font-family: var(--font-mono);
    font-size: 17px;
    font-weight: 600;
    line-height: 1;
    padding: 6px 9px;
    border-radius: 9px;
  }
  .graph--bar .chip {
    padding: 5px 8px;
    border-radius: 8px;
  }

  .box {
    flex: 1;
    min-height: 0;
    display: flex;
  }
  .axis--scale {
    position: relative;
  }
  .axis--scale span {
    position: absolute;
    left: 0;
    transform: translateY(-50%);
  }
  .axis--scale .zero {
    color: rgba(233, 238, 242, 0.82);
  }
  .plot {
    flex: 1;
    min-width: 0;
    position: relative;
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
    pointer-events: none;
  }
  .cols {
    position: absolute;
    left: 0;
    right: 0;
    display: flex;
  }
  .col {
    flex: 1;
    min-width: 0;
    position: relative;
    touch-action: none;
    cursor: ns-resize;
  }
  .col__ground {
    position: absolute;
    left: 8px;
    right: 8px;
    top: 0;
    bottom: 0;
    border-radius: 16px;
    background: transparent;
  }
  .graph--bar .col__ground {
    left: 6px;
    right: 6px;
    border-radius: 14px;
  }
  .col.is-dragging .col__ground {
    background: rgba(233, 238, 242, 0.05);
  }
  .col__centre {
    position: absolute;
    left: 50%;
    width: 0;
    border-left: 1px dashed rgba(233, 238, 242, 0.1);
  }
  .knob {
    position: absolute;
    left: 50%;
    width: 34px;
    height: 34px;
    margin: -17px 0 0 -17px;
    border-radius: 50%;
    box-sizing: border-box;
    border: 4px solid #f4f1ea;
    background: #0d151c;
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.5);
  }
  .knob.is-dragging {
    background: #f4f1ea;
    box-shadow: 0 0 0 8px rgba(244, 241, 234, 0.18), 0 3px 10px rgba(0, 0, 0, 0.5);
  }

  .hz {
    display: flex;
    align-items: center;
    height: 24px;
    flex-shrink: 0;
  }
  .graph--bar .hz {
    height: 22px;
  }
  .hz__band {
    flex: 1;
    min-width: 0;
    text-align: center;
    font-family: var(--font-mono);
    font-size: 15px;
    color: rgba(233, 238, 242, 0.72);
  }
  .graph--bar .hz__band {
    font-size: 16px;
  }
</style>
