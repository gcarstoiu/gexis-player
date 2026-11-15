<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **A way into Radio on a bar** (design/source/31, `CategoryTile`, pick 8a;
  B01-B04): 196 x 300 on its tint at 0.13 with a 0.32 line, §8's disc (54),
  the name - a step down past eleven letters - and what it holds. A tap
  opens it. `off`: the directory out of reach with nothing kept - at 0.4 and
  inert (B04).
-->
<script>
  import Icon from '../../radio/Icon.svelte';
  import HeartIcon from '../../../lib/HeartIcon.svelte';
  import SourceMark from '../../../lib/SourceMark.svelte';
  import { pressing } from '../../../lib/press.svelte.js';

  //: `glyph`: heart, pin, note, globe, speech, search, or lyrion (Lyrion's mark).
  let { glyph, label, meta = '', tint, off = false, onopen } = $props();
  const press = pressing();
</script>

<button class="tile" class:is-pressed={press.is('tile')} class:is-off={off} type="button" inert={off}
  style:--tint={tint}
  onpointerdown={() => press.down('tile')} onpointerup={press.up} onpointercancel={press.up}
  onclick={() => press.act(onopen)}>
  <span class="disc">
    {#if glyph === 'heart'}
      <HeartIcon filled size={24} />
    {:else if glyph === 'lyrion'}
      <SourceMark source="lms" size={23} color="var(--accent-lms)" />
    {:else}
      <Icon name={glyph} size={24} />
    {/if}
  </span>
  <span class="text">
    <span class="name" class:name--long={label.length > 11}>{label}</span>
    {#if meta}<span class="meta">{meta}</span>{/if}
  </span>
</button>

<style>
  .tile {
    width: calc(196px * max(1, var(--text-scale, 1)));
    height: 300px;
    flex-shrink: 0;
    border-radius: var(--r-xl);
    background: color-mix(in srgb, var(--tint) 13%, transparent);
    border: 1px solid color-mix(in srgb, var(--tint) 32%, transparent);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 22px;
    box-sizing: border-box;
    color: var(--ink);
    font: inherit;
    text-align: left;
    transition:
      transform 110ms cubic-bezier(0.2, 0.8, 0.2, 1),
      background 110ms linear,
      border-color 110ms linear;
  }
  .tile:active,
  .tile.is-pressed {
    background: color-mix(in srgb, var(--tint) 24%, transparent);
    border-color: color-mix(in srgb, var(--tint) 55%, transparent);
    transform: scale(0.975);
  }
  .tile.is-off {
    opacity: 0.4;
  }
  /* §8's disc: the tint at --radio-glyph-ground, its line at --radio-glyph-line. */
  .disc {
    width: 54px;
    height: 54px;
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
  .text {
    display: block;
    min-width: 0;
  }
  .name {
    display: block;
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.01em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .name--long {
    font-size: 23px;
  }
  .meta {
    display: block;
    margin-top: 8px;
    font-family: var(--font-mono);
    font-size: 14px;
    color: color-mix(in srgb, var(--tint) 90%, transparent);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
