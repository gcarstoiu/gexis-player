<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **A favourite as a preset on the panel's Radio screen** (design/source/31,
  `PresetTile`, pick 1b; P01): the 160 px logo, its number, the name under
  it. The first tap selects it and shows Play and the heart; only Play plays,
  and the heart takes it out of the favourites at once. The tiles only play:
  their order is changed in the list (3b).
-->
<script>
  import StationLogo from '../../lib/StationLogo.svelte';
  import HeartIcon from '../../lib/HeartIcon.svelte';
  import Icon from './Icon.svelte';

  let { station, num, selected = false, playing = false, onselect, onplay, onheart } = $props();
</script>

<!-- `is-revealed` and Play's `act` straight after the tile's button: the
     phone's pointer leaves a tile alone while its actions show (PanelPointer). -->
<div class="tile" class:is-selected={selected} class:is-revealed={selected} data-station={station.id}>
  <button class="tile__hit" type="button" aria-label={station.name} aria-pressed={selected} onclick={onselect}>
    <span class="tile__logo" class:is-playing={playing}>
      <StationLogo src={station.logo} size={160} radius="var(--preset-radius)" mark={74} />
    </span>
    <span class="tile__name">{station.name}</span>
  </button>
  {#if selected}
    <button class="play act" type="button" aria-label="Play" onclick={onplay}><Icon name="play" size={26} /></button>
    <button class="heart" type="button" aria-label="Remove from favourites" aria-pressed="true" onclick={onheart}>
      <HeartIcon filled size={24} />
    </button>
  {/if}
  <span class="badge">{num}</span>
  {#if playing}
    <span class="playing"><Icon name="meter" size={13} width={2.6} />PLAYING</span>
  {/if}
</div>

<style>
  .tile {
    position: relative;
    width: 176px;
    flex-shrink: 0;
    border-radius: var(--r-28);
  }
  .tile.is-selected {
    background: var(--row-selected);
  }
  .tile__hit {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 8px;
    box-sizing: border-box;
    border: 0;
    background: none;
    color: inherit;
    font: inherit;
    text-align: left;
  }
  .tile__logo {
    position: relative;
    display: block;
    width: 160px;
    height: 160px;
    border-radius: var(--preset-radius);
  }
  .tile__logo.is-playing {
    box-shadow: 0 0 0 3px var(--accent-lms);
  }
  .tile__name {
    font-size: 18px;
    font-weight: 700;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    padding: 0 4px;
  }
  .is-selected .tile__name {
    color: var(--accent-lms);
  }
  /* Over the logo: the wrapper's 8 px padding, then the artboard's insets. */
  .badge {
    position: absolute;
    left: 18px;
    top: 18px;
    min-width: 30px;
    height: 30px;
    padding: 0 8px;
    box-sizing: border-box;
    border-radius: var(--r-10);
    background: var(--preset-badge-ground);
    font-family: var(--font-mono);
    font-size: 15px;
    font-weight: 600;
    color: var(--ink);
    display: flex;
    align-items: center;
    justify-content: center;
    pointer-events: none;
  }
  .playing {
    position: absolute;
    right: 18px;
    top: 18px;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 9px;
    border-radius: var(--r-9);
    background: var(--preset-badge-ground);
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--accent-lms);
    pointer-events: none;
  }
  .play {
    position: absolute;
    right: 18px;
    top: 106px;
    width: 52px;
    height: 52px;
    border-radius: var(--r-md);
    background: var(--row-act-ground);
    border: 1px solid var(--row-act-line);
    box-sizing: border-box;
    padding: 0 0 0 2px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--accent-lms);
  }
  .heart {
    position: absolute;
    left: 16px;
    top: 112px;
    width: 48px;
    height: 48px;
    border-radius: var(--r-circle);
    background: var(--preset-badge-ground);
    border: 0;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .play:active,
  .heart:active {
    transform: scale(0.94);
  }
</style>
