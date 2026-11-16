<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  design/source/31 (H11-H12): the favourites in edit on the phone. Each row
  has a grip at its left and the coral minus at its right. A finger on the
  grip drags the row - lifted 10 px and scaled to 1.02, on the panel's
  ground with a shadow and the accent's ring - and the others make room;
  let go, the new order is the player's. The minus removes at once (the
  page says so, with Undo). Near the list's top or foot, a drag scrolls it.
-->
<script>
  import { untrack } from 'svelte';
  import StationLogo from '../../../lib/StationLogo.svelte';
  import { RADIO } from './glyphs.js';
  import { rowMeta } from './words.js';

  let { stations = [], onorder = () => {}, onremove = () => {} } = $props();

  let order = $state([]);
  let drag = $state(null); // { id, from, to, dy, y, scroll, pitch, pointer }
  $effect(() => {
    const now = stations;
    untrack(() => {
      if (!drag) order = now;
    });
  });

  let listEl = $state(null);
  const LIFT = 10;
  const EDGE = 56;
  const SPEED = 8;
  let rolling = null;

  function grab(event, index) {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    event.preventDefault();
    const row = event.currentTarget.closest('.slot');
    event.currentTarget.setPointerCapture?.(event.pointerId);
    drag = {
      id: order[index].id, from: index, to: index, dy: 0, y: event.clientY, at: event.clientY,
      scroll: listEl.scrollTop, pitch: row.offsetHeight + 2, pointer: event.pointerId,
    };
  }
  function place() {
    if (!drag) return;
    drag.dy = drag.at - drag.y + (listEl.scrollTop - drag.scroll);
    drag.to = Math.max(0, Math.min(order.length - 1, drag.from + Math.round(drag.dy / drag.pitch)));
  }
  function move(event) {
    if (!drag || event.pointerId !== drag.pointer) return;
    drag.at = event.clientY;
    place();
    const r = listEl.getBoundingClientRect();
    const step = event.clientY < r.top + EDGE ? -SPEED : event.clientY > r.bottom - EDGE ? SPEED : 0;
    roll(step);
  }
  function roll(step) {
    cancelAnimationFrame(rolling);
    rolling = null;
    if (!step) return;
    const frame = () => {
      if (!drag) return;
      listEl.scrollTop += step;
      place();
      rolling = requestAnimationFrame(frame);
    };
    rolling = requestAnimationFrame(frame);
  }
  function drop(event) {
    if (!drag || event.pointerId !== drag.pointer) return;
    roll(0);
    const { from, to } = drag;
    drag = null;
    if (from === to) return;
    const next = [...order];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    order = next;
    onorder(next.map((s) => s.id));
  }
  function shift(index) {
    if (!drag || index === drag.from) return 0;
    const { from, to, pitch } = drag;
    if (from < to && index > from && index <= to) return -pitch;
    if (from > to && index >= to && index < from) return pitch;
    return 0;
  }
</script>

<div class="list" bind:this={listEl} class:is-dragging={!!drag}>
  {#each order as station, i (station.id)}
    {@const lifted = drag?.id === station.id}
    <div class="slot" class:is-lifted={lifted}
         style:transform={lifted ? `translateY(${drag.dy - LIFT}px) scale(1.02)` : `translateY(${shift(i)}px)`}>
      <div class="row">
        <span class="grip" role="button" tabindex="-1" aria-label="Drag to move"
              onpointerdown={(e) => grab(e, i)} onpointermove={move} onpointerup={drop} onpointercancel={drop}>
          <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d={RADIO.grip} /></svg>
        </span>
        <StationLogo src={station.logo} size={44} radius="var(--station-logo-phone-radius)" mark={20} />
        <div class="text">
          <span class="name">{station.name}</span>
          <span class="meta">{rowMeta(station)}</span>
        </div>
        <button class="remove" type="button" aria-label="Remove" onclick={() => onremove(station)}>
          <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d={RADIO.minus} /></svg>
        </button>
      </div>
    </div>
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
  .slot {
    position: relative;
    flex-shrink: 0;
    border-radius: var(--r-14);
    transition: transform 160ms ease;
  }
  .is-dragging .slot.is-lifted {
    transition: none;
  }
  .slot.is-lifted {
    z-index: 2;
    background: var(--bg-panel);
    box-shadow: 0 14px 30px var(--c-black-55), 0 0 0 1px var(--c-lms-45);
  }
  .row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 9px 6px 9px 8px;
  }
  .grip {
    width: 30px;
    align-self: stretch;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    touch-action: none;
    cursor: grab;
  }
  .grip svg {
    fill: none;
    stroke: var(--ink-muted);
    stroke-width: 2.4;
    stroke-linecap: round;
  }
  .text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .name {
    font-size: 17px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .meta {
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--c-ink-62);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .remove {
    width: 40px;
    height: 40px;
    flex-shrink: 0;
    box-sizing: border-box;
    padding: 0;
    border-radius: 50%;
    background: var(--remove-ground);
    border: 1px solid var(--remove-line);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }
  .remove:active {
    transform: scale(0.95);
  }
  .remove svg {
    fill: none;
    stroke: var(--accent-artist);
    stroke-width: 3;
    stroke-linecap: round;
  }
</style>
