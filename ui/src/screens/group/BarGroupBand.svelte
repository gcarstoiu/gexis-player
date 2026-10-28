<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The bar tray's group band (ADR-0166; design/source/22, 2a, bar,
  `group-band`): 150 tall under the tray's row, as the equaliser's band is.
  The members as cards scrolling sideways with an 88px fade, and a 220
  column with + Add players, Leave (members only) and Undo group.
-->
<script>
  import BarMemberCard from './BarMemberCard.svelte';
  import { leaveGroup } from '../../lib/group.svelte.js';

  let { g, onadd, onundo, onerror = () => {} } = $props();

  const me = $derived(g.members.find((m) => m.me));
  const canLeave = $derived(!!me && !me.leads);
  async function leave() {
    try {
      await leaveGroup();
    } catch (error) {
      onerror(error.message);
    }
  }
</script>

<div class="band">
  <div class="cards" data-pan-x>
    {#each g.members as m (m.id)}
      <BarMemberCard {m} {g} {onerror} />
    {/each}
  </div>
  <div class="column">
    <button class="action" type="button" onclick={onadd}><span class="plus">+</span>Add players</button>
    <div class="pair">
      {#if canLeave}
        <button class="action action--half" type="button" onclick={leave}>Leave</button>
      {/if}
      <button class="action action--half action--undo" type="button" onclick={onundo}>Undo group</button>
    </div>
  </div>
</div>

<style>
  .band {
    position: relative;
    z-index: 1;
    height: 150px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 0 40px;
    box-sizing: border-box;
    border-top: 1px solid rgba(233, 238, 242, 0.08);
    text-transform: none;
    letter-spacing: normal;
    color: var(--ink);
  }
  .cards {
    flex: 1;
    min-width: 0;
    display: flex;
    gap: 12px;
    overflow-x: auto;
    scrollbar-width: none;
    touch-action: pan-x;
    -webkit-mask-image: linear-gradient(90deg, #000 0, #000 calc(100% - 88px), transparent 100%);
    mask-image: linear-gradient(90deg, #000 0, #000 calc(100% - 88px), transparent 100%);
  }
  .cards::-webkit-scrollbar { display: none; }
  .column {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
    width: 220px;
  }
  .pair { display: flex; gap: 10px; }
  .action {
    height: 53px;
    padding: 0 22px;
    border-radius: 15px;
    box-sizing: border-box;
    background: var(--ink-fill);
    border: 1px solid rgba(233, 238, 242, 0.14);
    color: var(--ink);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    font: inherit;
    font-size: 18px;
    font-weight: 600;
    white-space: nowrap;
    flex-shrink: 0;
  }
  .action:active { transform: scale(0.95); }
  .action--half {
    flex: 1;
    padding: 0 10px;
    font-size: 17px;
  }
  .action--undo {
    background: var(--group-undo-ground);
    border-color: var(--group-undo-line);
    color: var(--group-undo-ink);
    font-weight: 700;
  }
  .plus {
    font-size: 24px;
    font-weight: 400;
    line-height: 1;
    margin-top: -2px;
  }
</style>
