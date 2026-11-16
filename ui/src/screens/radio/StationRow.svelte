<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **A station in a list on the panel** (design/source/31, `StationRow`, pick
  2a: the library's row with a logo tile; P08-P11, P15-P19). The first tap
  selects it and shows Play, as every leaf row (George, 2026-11-14); only
  Play plays. The heart acts at once, selected or not. In Favourites a
  selected row also has Move up and Move down (3b), and a removed one keeps
  its place with the name struck through and Undo where the heart was.
-->
<script>
  import StationLogo from '../../lib/StationLogo.svelte';
  import HeartIcon from '../../lib/HeartIcon.svelte';
  import { stationMeta } from '../../lib/radio.js';
  import Icon from './Icon.svelte';

  let {
    station,
    //: Favourites number their rows (mono, 22 wide).
    num = null,
    selected = false,
    playing = false,
    favourite = false,
    removed = false,
    //: Search's text: its letters in the name drawn in the accent.
    query = '',
    //: Favourites' moves: `{up, down}`, each a function or null at an end.
    moves = null,
    onselect,
    onplay,
    onheart,
    onundo,
  } = $props();

  const playingMeta = $derived(
    ['Playing', station.codec, station.bitrate ? `${station.bitrate} kb/s` : null].filter(Boolean).join(' · '),
  );
  //: The name in pieces, the matched ones marked (folded for case only).
  const parts = $derived.by(() => {
    const name = station.name ?? '';
    const q = query.trim().toLowerCase();
    if (q.length < 2) return [{ text: name, hit: false }];
    const out = [];
    const low = name.toLowerCase();
    let at = 0;
    for (let i = low.indexOf(q); i >= 0; i = low.indexOf(q, at)) {
      if (i > at) out.push({ text: name.slice(at, i), hit: false });
      out.push({ text: name.slice(i, i + q.length), hit: true });
      at = i + q.length;
    }
    if (at < name.length) out.push({ text: name.slice(at), hit: false });
    return out;
  });
</script>

<!-- `is-revealed`: the phone's pointer leaves a row alone while its actions show (PanelPointer). -->
<div class="row" class:is-selected={selected && !removed} class:is-revealed={selected && !removed} data-station={station.id}>
  <button class="row__hit" type="button" aria-pressed={selected} disabled={removed} onclick={onselect}>
    {#if num != null}<span class="num">{num}</span>{/if}
    <StationLogo src={station.logo} size={46} radius="var(--station-logo-row-radius)" mark={21} />
    <span class="text">
      <span class="name" class:is-removed={removed}>{#each parts as p, i (i)}{#if p.hit}<em>{p.text}</em>{:else}{p.text}{/if}{/each}</span>
      {#if playing && !removed}
        <span class="meta meta--playing"><Icon name="meter" size={15} width={2.6} />{playingMeta}</span>
      {:else}
        <span class="meta">{stationMeta(station)}</span>
      {/if}
    </span>
  </button>
  <span class="acts">
    {#if selected && !removed}
      <button class="act act--play" type="button" aria-label="Play" onclick={onplay}><Icon name="play" size={22} /></button>
      {#if moves}
        <button class="act act--move" type="button" aria-label="Move up" disabled={!moves.up} onclick={moves.up}>
          <Icon name="up" size={22} width={2.4} />
        </button>
        <button class="act act--move" type="button" aria-label="Move down" disabled={!moves.down} onclick={moves.down}>
          <Icon name="down" size={22} width={2.4} />
        </button>
      {/if}
    {/if}
    {#if removed}
      <button class="undo" type="button" onclick={onundo}>Undo</button>
    {:else}
      <button class="heart" type="button" aria-label={favourite ? 'Remove from favourites' : 'Add to favourites'}
        aria-pressed={favourite} onclick={onheart}>
        <HeartIcon filled={favourite} size={24} />
      </button>
    {/if}
  </span>
</div>

<style>
  .row {
    display: flex;
    align-items: center;
    border-radius: var(--r-14);
    flex-shrink: 0;
  }
  .row.is-selected {
    background: var(--row-selected);
  }
  .row__hit {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 11px 0 11px 14px;
    border: 0;
    background: none;
    color: inherit;
    font: inherit;
    text-align: left;
  }
  .row__hit:disabled {
    cursor: default;
  }
  .num {
    width: 22px;
    flex-shrink: 0;
    text-align: right;
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--ink-quiet);
  }
  .text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .name {
    font-size: 19px;
    font-weight: 600;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .name em {
    font-style: normal;
    color: var(--accent-lms);
  }
  .is-selected .name {
    color: var(--accent-lms);
  }
  .name.is-removed {
    color: var(--row-removed-ink);
    text-decoration: line-through;
  }
  .meta {
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--c-ink-62);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .meta--playing {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--accent-lms);
  }
  .acts {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
    padding: 0 12px 0 14px;
  }
  .act {
    width: 44px;
    height: 44px;
    border-radius: var(--r-md);
    box-sizing: border-box;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .act--play {
    background: var(--row-act-ground);
    border: 1px solid var(--row-act-line);
    color: var(--accent-lms);
    padding-left: 2px;
  }
  .act--move {
    background: var(--c-ink-06);
    border: 1px solid var(--c-ink-14);
    color: var(--c-ink-90);
  }
  /* Move up on the first row, Move down on the last. */
  .act:disabled {
    opacity: 0.4;
  }
  .heart {
    width: 48px;
    height: 48px;
    border-radius: var(--r-circle);
    background: none;
    border: 0;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .undo {
    height: 44px;
    padding: 0 22px;
    border-radius: var(--r-pill);
    border: 1px solid var(--c-lms-45);
    background: var(--c-lms-14);
    color: var(--accent-lms);
    font: inherit;
    font-size: 16px;
    font-weight: 700;
    white-space: nowrap;
    flex-shrink: 0;
  }
  .act:not(:disabled):active,
  .heart:active,
  .undo:active {
    transform: scale(0.94);
  }
</style>
