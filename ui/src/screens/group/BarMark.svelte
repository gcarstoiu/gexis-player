<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The grouped mark on the bar's Now Playing (ADR-0166; design/source/22,
  3a): a chip 36 tall, radius 18, the glyph and *with Kitchen, Study* (past
  two names, *+ 3*). Hidden when not grouped; a tap opens the tray on the
  group's band.
-->
<script>
  import GroupGlyph from '../../lib/GroupGlyph.svelte';
  import { group, withText } from '../../lib/group.svelte.js';

  let { onopen } = $props();
  const words = $derived(withText($group));
</script>

{#if $group}
  <div class="mark">
    <button class="chip" type="button" aria-label={`Grouped ${words[0]}${words[1]}`} onclick={onopen}>
      <GroupGlyph size={18} ink="var(--group-ink)" />
      <span class="text">{words[0]}</span>
      {#if words[1]}<span class="more">{words[1]}</span>{/if}
    </button>
  </div>
{/if}

<style>
  .mark {
    display: flex;
    justify-content: center;
    min-width: 0;
  }
  .chip {
    height: 36px;
    max-width: 100%;
    border-radius: 18px;
    box-sizing: border-box;
    padding: 0 18px 0 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    background: var(--mark-ground);
    border: 1px solid var(--mark-line);
    font: inherit;
    font-size: 16px;
    font-weight: 600;
    letter-spacing: normal;
    text-transform: none;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
  }
  .chip:active { transform: scale(0.97); }
  .text {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .more { flex-shrink: 0; }
</style>
