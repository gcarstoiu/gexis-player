<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The Radio screen's top on the panel** (design/source/31, pick 1b;
  P01-P07): the favourites first, as numbered presets, then Browse. Up to
  seven tiles in one row, fading at its end when there are more than six;
  *All N* opens the list where they are moved (3b). With the directory out
  of reach and nothing kept, Browse is dimmed and inert and the favourites
  still play.
-->
<script>
  import PresetTile from './PresetTile.svelte';
  import CategoryCard from './CategoryCard.svelte';
  import FavouritesEmpty from './FavouritesEmpty.svelte';
  import Icon from './Icon.svelte';
  import { count } from '../../lib/radio.js';
  import { pressing } from '../../lib/press.svelte.js';

  let {
    favourites = null,
    playingId = null,
    //: The directory: 'ok', 'kept' (the last day's lists), 'none', or null before it is known.
    directory = null,
    //: *Lyrion's radio*: only while Lyrion is on and its library navigation is.
    lyrion = false,
    onall,
    onplay,
    onheart,
    onbrowse,
    onlyrion,
  } = $props();

  const TILES = 7;
  const tiles = $derived((favourites ?? []).slice(0, TILES));
  let selected = $state(null);
  const press = pressing();

  //: The design's §8 discs for each way in (design/source/31 README).
  const CARDS = [
    { id: 'popular', label: 'Popular here', glyph: 'pin', tint: 'var(--accent-bluetooth)' },
    { id: 'genres', label: 'By genre', glyph: 'note', tint: 'var(--accent-artist)' },
    { id: 'countries', label: 'By country', glyph: 'globe', tint: 'var(--accent-radio)' },
    { id: 'languages', label: 'By language', glyph: 'speech', tint: 'var(--accent-display)' },
  ];
  const columns = $derived(CARDS.length + (lyrion ? 1 : 0));
</script>

<div class="root">
  <div class="favs">
    <div class="kicker" class:kicker--alone={!favourites?.length}>
      <span class="kicker__label">{favourites?.length ? `Favourites · ${count(favourites.length)}` : 'Favourites'}</span>
      {#if favourites?.length}
        <button class="all" class:is-pressed={press.is('all')} type="button"
          onpointerdown={() => press.down('all')} onpointerup={press.up} onpointercancel={press.up}
          onclick={() => press.act(onall)}>
          All {count(favourites.length)}<span class="all__chev"><Icon name="chevron" size={18} width={2.6} /></span>
        </button>
      {/if}
    </div>
    {#if favourites && !favourites.length}
      <FavouritesEmpty />
    {:else if favourites}
      <div class="tiles" class:tiles--fade={favourites.length > 6}>
        {#each tiles as station, i (station.id)}
          <PresetTile
            {station}
            num={i + 1}
            selected={selected === station.id}
            playing={playingId === station.id}
            onselect={() => (selected = selected === station.id ? null : station.id)}
            onplay={() => {
              selected = null;
              onplay(station);
            }}
            onheart={() => {
              selected = null;
              onheart(station);
            }}
          />
        {/each}
      </div>
    {/if}
  </div>

  <div class="kicker kicker--browse"><span class="kicker__label">Browse</span></div>
  <div class="browse" class:is-off={directory === 'none'} inert={directory === 'none'}
    style:grid-template-columns={`repeat(${columns}, minmax(0, 1fr))`}>
    {#each CARDS as card (card.id)}
      <CategoryCard glyph={card.glyph} label={card.label} tint={card.tint} onopen={() => onbrowse(card.id)} />
    {/each}
    {#if lyrion}
      <CategoryCard glyph="lyrion" label="Lyrion's radio" tint="var(--accent-lms)" onopen={onlyrion} />
    {/if}
  </div>
</div>

<style>
  .root {
    position: absolute;
    inset: 0;
    padding: 24px 40px 0;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
  }
  /* The kicker and the tiles, or the empty plate: Browse's kicker comes
     278 under the favourites' in both. */
  .favs {
    height: 278px;
    flex-shrink: 0;
  }
  .kicker {
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  .kicker--alone {
    align-items: flex-start;
    padding-top: 8px;
    box-sizing: border-box;
  }
  .kicker--browse {
    height: 32px;
    align-items: flex-start;
  }
  .kicker__label {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .all {
    height: 44px;
    padding: 0 12px 0 18px;
    border-radius: var(--r-pill);
    border: 1px solid var(--c-ink-14);
    background: var(--ink-fill);
    color: var(--ink);
    font: inherit;
    font-size: 16px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
  }
  .all:active,
  .all.is-pressed {
    transform: scale(0.96);
  }
  .all__chev {
    color: var(--ink-muted);
    display: flex;
  }
  /* From x 32 to the screen's edge: the wrappers' 8 px padding puts the
     first logo under the kicker. */
  .tiles {
    display: flex;
    gap: 4px;
    margin: 0 -40px 0 -8px;
    overflow: hidden;
  }
  .tiles--fade {
    -webkit-mask-image: linear-gradient(90deg, #000 88%, transparent);
    mask-image: linear-gradient(90deg, #000 88%, transparent);
  }
  .browse {
    display: grid;
    gap: 12px;
  }
  .browse.is-off {
    opacity: 0.4;
  }
</style>
