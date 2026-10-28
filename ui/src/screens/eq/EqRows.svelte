<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The phone's bands, one row each (ADR-0162; design/source/20, P01-P02): ten
  upright sliders would be under the touch floor across a phone, so each band
  is a sideways slider - 0 in the middle, the fill from it in the band's
  value colour.

  **A press decides within 8 px**, as the phone's volume slider does: mostly
  up or down scrolls the page, mostly sideways slides the band, and a tap sets
  the value where it lands.
-->
<script>
  import { clamp, fmt, valueInk } from '../../lib/equaliser.svelte.js';

  let { levels, bands, drag = -1, disabled = false, onset, onend } = $props();

  const DECIDE = 8;
  let land = null;

  function value(x, el) {
    const r = el.getBoundingClientRect();
    return clamp(((x - r.left) / r.width) * 24 - 12);
  }
  function down(i, event) {
    if (disabled) return;
    land = { i, x: event.clientX, y: event.clientY, way: null, el: event.currentTarget };
  }
  function move(i, event) {
    if (!land || land.i !== i) return;
    if (land.way === null) {
      const dx = event.clientX - land.x;
      const dy = event.clientY - land.y;
      if (Math.max(Math.abs(dx), Math.abs(dy)) < DECIDE) return;
      if (Math.abs(dy) > Math.abs(dx)) {
        land = null;
        return;
      }
      land.way = 'slide';
      land.el.setPointerCapture?.(event.pointerId);
    }
    onset?.(i, value(event.clientX, land.el));
  }
  function up(i) {
    if (land && land.i === i && land.way === null) onset?.(i, value(land.x, land.el));
    const was = land;
    land = null;
    if (was) onend?.();
  }
  function cancel() {
    land = null;
    onend?.();
  }
  function key(i, event) {
    if (disabled) return;
    const delta = event.key === 'ArrowRight' || event.key === 'ArrowUp' ? 1
      : event.key === 'ArrowLeft' || event.key === 'ArrowDown' ? -1 : 0;
    if (!delta) return;
    event.preventDefault();
    stepBand(i, delta);
  }
  //: A key, or a scroll along the band (lib/scrollSlide.js): 1 dB a step.
  function stepBand(i, delta) {
    if (disabled) return;
    onset?.(i, clamp(Math.round(levels[i]) + delta));
    onend?.();
  }
  //: The fill from the middle to the knob, left and width in per cent.
  const fill = (g) => (g >= 0 ? [50, (g / 24) * 100] : [50 + (g / 24) * 100, (-g / 24) * 100]);
</script>

<div class="rows">
  {#each levels as g, i (i)}
    {@const dragging = drag === i}
    {@const [left, width] = fill(g)}
    <div class="row" class:is-dragging={dragging}>
      <span class="label">{bands[i]}</span>
      <div
        class="slider"
        role="slider"
        tabindex="0"
        aria-label={`${bands[i]} Hz`}
        aria-valuemin="-12"
        aria-valuemax="12"
        aria-valuenow={Math.round(g)}
        aria-disabled={disabled}
        data-step="1"
        ondpadstep={(event) => stepBand(i, event.detail.step)}
        onpointerdown={(event) => down(i, event)}
        onpointermove={(event) => move(i, event)}
        onpointerup={() => up(i)}
        onpointercancel={cancel}
        onkeydown={(event) => key(i, event)}
      >
        <span class="track"></span>
        <span class="tick"></span>
        <span class="fill" style:left={`${left}%`} style:width={`${width}%`} style:background={valueInk(g)}></span>
        <span class="knob" class:is-dragging={dragging} style:left={`${50 + (g / 24) * 100}%`}></span>
      </div>
      <span class="value" style:color={dragging ? '#f4f1ea' : valueInk(g)}>{fmt(g)}</span>
    </div>
  {/each}
</div>

<style>
  .rows {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 12px;
    height: 52px;
    padding: 0 12px;
    border-radius: 12px;
  }
  .row.is-dragging {
    background: rgba(126, 214, 188, 0.1);
  }
  .label {
    width: 38px;
    flex-shrink: 0;
    font-family: var(--font-mono);
    font-size: 15px;
    color: rgba(233, 238, 242, 0.82);
  }
  .slider {
    flex: 1;
    min-width: 0;
    align-self: stretch;
    position: relative;
    touch-action: pan-y;
    cursor: ew-resize;
    outline: none;
  }
  .track,
  .tick,
  .fill,
  .knob {
    position: absolute;
    top: 50%;
    display: block;
  }
  .track {
    left: 0;
    right: 0;
    height: 6px;
    margin-top: -3px;
    border-radius: 3px;
    background: rgba(233, 238, 242, 0.14);
  }
  .tick {
    left: 50%;
    width: 2px;
    height: 16px;
    margin: -8px 0 0 -1px;
    border-radius: 1px;
    background: rgba(233, 238, 242, 0.4);
  }
  .fill {
    height: 6px;
    margin-top: -3px;
    border-radius: 3px;
  }
  .knob {
    width: 26px;
    height: 26px;
    margin: -13px 0 0 -13px;
    border-radius: 50%;
    box-sizing: border-box;
    border: 3px solid #f4f1ea;
    background: #0d151c;
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.5);
  }
  .knob.is-dragging {
    background: #f4f1ea;
    box-shadow: 0 0 0 8px rgba(244, 241, 234, 0.18), 0 3px 10px rgba(0, 0, 0, 0.5);
  }
  .value {
    width: 34px;
    flex-shrink: 0;
    text-align: right;
    font-family: var(--font-mono);
    font-size: 15px;
    font-weight: 600;
  }
</style>
