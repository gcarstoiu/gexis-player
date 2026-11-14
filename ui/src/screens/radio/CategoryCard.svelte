<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **A Browse card on the panel's Radio screen** (design/source/31,
  `CategoryCard`, P01): §8's tinted disc and the category's name. A tap
  opens it, nothing else.
-->
<script>
  import Icon from './Icon.svelte';
  import SourceMark from '../../lib/SourceMark.svelte';
  import { pressing } from '../../lib/press.svelte.js';

  //: `glyph`: pin, note, globe, speech, or lyrion (Lyrion's mark).
  let { glyph, label, tint, onopen } = $props();
  const press = pressing();
</script>

<button class="card" class:is-pressed={press.is('card')} type="button" style:--tint={tint}
  onpointerdown={() => press.down('card')} onpointerup={press.up} onpointercancel={press.up}
  onclick={() => press.act(onopen)}>
  <span class="disc">
    {#if glyph === 'lyrion'}
      <SourceMark source="lms" size={19} color="var(--accent-lms)" />
    {:else}
      <Icon name={glyph} size={20} />
    {/if}
  </span>
  <span class="name">{label}</span>
</button>

<style>
  .card {
    height: 88px;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 0 26px 0 18px;
    box-sizing: border-box;
    border-radius: var(--r-18);
    background: var(--c-white-05);
    border: 1px solid var(--ink-line);
    color: var(--ink);
    font: inherit;
    text-align: left;
  }
  .card:active,
  .card.is-pressed {
    transform: scale(0.97);
  }
  /* §8's disc: the tint at --radio-glyph-ground, its line at --radio-glyph-line. */
  .disc {
    width: 46px;
    height: 46px;
    border-radius: var(--r-circle);
    box-sizing: border-box;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--tint);
    background: color-mix(in srgb, var(--tint) 14%, transparent);
    border: 1px solid color-mix(in srgb, var(--tint) 30%, transparent);
  }
  .name {
    flex: 1;
    min-width: 0;
    font-size: 19px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
