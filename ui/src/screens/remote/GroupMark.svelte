<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0166, design/source/22 (3a): the grouped mark on the phone - no chip,
  the glyph and *with Kitchen, Study* (past two names, *+ 3*). A tap opens
  the player list, where the group is. Hidden when not grouped.
-->
<script>
  import GroupGlyph from '../../lib/GroupGlyph.svelte';
  import { group, withText } from '../../lib/group.svelte.js';

  let { onopen = () => {}, gap = 12, after = 0, height = 18 } = $props();
  const g = $derived($group);
  const text = $derived(withText(g));
</script>

{#if g}
  <div class="mark" style:margin-top={`${gap}px`} style:margin-bottom={`${after}px`} style:height={`${height}px`}>
    <button type="button" aria-label={`Grouped ${text[0]}${text[1]}`} onclick={onopen}>
      <GroupGlyph size={16} ink="var(--group-ink)" />
      <span class="with">{text[0]}</span>{#if text[1]}<span class="more">{text[1]}</span>{/if}
    </button>
  </div>
{/if}

<style>
  .mark {
    flex-shrink: 0;
    display: flex;
    justify-content: center;
  }
  button {
    max-width: 100%;
    min-width: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 0 8px;
    border: 0;
    background: none;
    font-family: var(--font-ui);
    font-size: 13px;
    font-weight: 600;
    color: rgba(233, 238, 242, 0.86);
    white-space: nowrap;
    overflow: hidden;
    cursor: pointer;
  }
  .with {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .more {
    flex-shrink: 0;
  }
</style>
