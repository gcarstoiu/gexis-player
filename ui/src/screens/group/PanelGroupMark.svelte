<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The grouped mark on the panel's Now Playing** (ADR-0166; design/source/22,
  3a): a chip naming the other players - *with Kitchen, Study*, past two
  *+ 3* - in the group's accent whatever the source. Tapping it opens the
  group, in the volume drawer. Where it sits is the screen's to say.
-->
<script>
  import GroupGlyph from '../../lib/GroupGlyph.svelte';
  import { withText } from '../../lib/group.svelte.js';

  let { g, onopen, height = 44 } = $props();
  const text = $derived(withText(g));
</script>

<button class="mark" type="button" style:--mark-h={`${height}px`} aria-label={`Grouped ${text[0]}${text[1]}`} onclick={onopen}>
  <GroupGlyph size={height >= 44 ? 20 : 18} ink="var(--group-ink)" />
  <span class="names">{text[0]}</span>
  {#if text[1]}<span class="more">{text[1]}</span>{/if}
</button>

<style>
  .mark {
    font: inherit;
    height: var(--mark-h);
    max-width: 100%;
    border-radius: calc(var(--mark-h) / 2);
    box-sizing: border-box;
    padding: 0 18px 0 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    background: var(--mark-ground);
    border: 1px solid var(--mark-line);
    font-size: 16px;
    font-weight: 600;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
  }
  .mark:active { transform: scale(0.97); }
  .names { min-width: 0; overflow: hidden; text-overflow: ellipsis; }
  .more { flex-shrink: 0; }
</style>
