<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **A station on a bar** (design/source/31, `StationCard`; B05-B13): 430 x
  120 with its logo (72), name, meta and heart (52). As every leaf row, the
  first tap selects it and shows Play; only Play plays (George, 2026-11-14).
  The heart acts at once, selected or not.

  In Favourites (`num`): 440 wide, numbered, a 64 logo, the heart 48; a
  selected one has Play, Earlier and Later (decided while drawing #4 - the
  cards run down then across, so up and down are not where they move). A
  removed one keeps its place, the name struck through, Undo where the
  heart was.
-->
<script>
  import StationLogo from '../../../lib/StationLogo.svelte';
  import HeartIcon from '../../../lib/HeartIcon.svelte';
  import Icon from '../../radio/Icon.svelte';
  import { stationMeta } from '../../../lib/radio.js';

  let {
    station,
    num = null,
    selected = false,
    playing = false,
    favourite = false,
    removed = false,
    //: Favourites' moves: `{earlier, later}`, each a function or null at an end.
    moves = null,
    onselect,
    onplay,
    onheart,
    onundo,
  } = $props();

  const fav = $derived(num != null);
  //: The bars' playing meta: *Playing · FLAC 1411* (B05, B09).
  const playingMeta = $derived(['Playing', [station.codec, station.bitrate].filter(Boolean).join(' ')].filter(Boolean).join(' · '));
</script>

<!-- `is-revealed`: the phone's pointer leaves a card alone while its actions show (PanelPointer). -->
<div class="card" class:card--fav={fav} class:is-selected={selected && !removed} class:is-revealed={selected && !removed}
  data-station={station.id}>
  <button class="hit" type="button" aria-pressed={selected} disabled={removed} onclick={onselect}>
    {#if fav}<span class="num">{num}</span>{/if}
    {#if fav}
      <StationLogo src={station.logo} size={64} radius="var(--r-14)" mark={29} />
    {:else}
      <StationLogo src={station.logo} size={72} radius="var(--station-logo-card-bar-radius)" mark={33} />
    {/if}
    <span class="text">
      <span class="name" class:is-removed={removed}>{station.name}</span>
      {#if playing && !removed}
        <span class="meta meta--playing"><Icon name="meter" size={14} width={2.6} />{playingMeta}</span>
      {:else}
        <span class="meta">{stationMeta(station)}</span>
      {/if}
    </span>
  </button>
  <span class="acts">
    {#if selected && !removed}
      <button class="act act--play" type="button" aria-label="Play" onclick={onplay}>
        <Icon name="play" size={fav ? 22 : 24} />
      </button>
      {#if moves}
        <button class="act act--move" type="button" aria-label="Move earlier" disabled={!moves.earlier} onclick={moves.earlier}>
          <Icon name="up" size={22} width={2.4} />
        </button>
        <button class="act act--move" type="button" aria-label="Move later" disabled={!moves.later} onclick={moves.later}>
          <Icon name="down" size={22} width={2.4} />
        </button>
      {/if}
    {/if}
    {#if removed}
      <button class="undo" type="button" onclick={onundo}>Undo</button>
    {:else}
      <button class="heart" type="button" aria-label={favourite ? 'Remove from favourites' : 'Add to favourites'}
        aria-pressed={favourite} onclick={onheart}>
        <HeartIcon filled={favourite} size={fav ? 24 : 26} />
      </button>
    {/if}
  </span>
</div>

<style>
  .card {
    width: calc(430px * max(1, var(--text-scale, 1)));
    height: 120px;
    flex-shrink: 0;
    box-sizing: border-box;
    border-radius: var(--r-20);
    background: var(--c-ink-5_5);
    border: 1px solid var(--c-ink-16);
    display: flex;
    align-items: center;
    padding-right: 12px;
    min-width: 0;
  }
  .card--fav {
    width: calc(440px * max(1, var(--text-scale, 1)));
    padding-right: 10px;
  }
  .card.is-selected {
    background: var(--row-selected);
    border-color: var(--c-lms-45);
  }
  .hit {
    flex: 1;
    min-width: 0;
    align-self: stretch;
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 0 0 0 20px;
    border: 0;
    background: none;
    color: inherit;
    font: inherit;
    text-align: left;
  }
  .card--fav .hit {
    gap: 14px;
    padding-left: 16px;
  }
  .hit:disabled {
    cursor: default;
  }
  .card:not(.is-selected):has(.hit:active) {
    background: var(--c-ink-12);
  }
  .num {
    width: 18px;
    flex-shrink: 0;
    text-align: right;
    font-family: var(--font-mono);
    font-size: 14px;
    color: var(--ink-quiet);
  }
  .text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }
  .name {
    font-size: 21px;
    font-weight: 700;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
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
    font-size: 14px;
    color: var(--ink-quiet);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .meta--playing {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--accent-lms);
  }
  /* The lists: Play and the heart 16 apart, as the card's own gap; in
     Favourites the four sit 6 apart. */
  .acts {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-shrink: 0;
    padding-left: 16px;
  }
  .card--fav .acts {
    gap: 6px;
    padding-left: 14px;
  }
  .act {
    width: 48px;
    height: 48px;
    border-radius: var(--r-md);
    box-sizing: border-box;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .card--fav .act {
    width: 44px;
    height: 44px;
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
  /* Earlier on the first card, Later on the last. */
  .act:disabled {
    opacity: 0.4;
  }
  .heart {
    width: 52px;
    height: 52px;
    border-radius: var(--r-circle);
    background: none;
    border: 0;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .card--fav .heart {
    width: 48px;
    height: 48px;
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
