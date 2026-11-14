<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The favourites on a bar, in their order** (design/source/31, pick 3b;
  B05-B08): numbered cards, down then across. A selected one has Play,
  Earlier and Later - no edit mode, as on the panel (FavouritesList.svelte,
  whose order and removal this keeps). The heart takes a station out at
  once; its card stays where it was, the name struck through, with Undo in
  the heart's place, until the page is left. None yet: the dashed plate
  (B06).
-->
<script>
  import Sideways from './Sideways.svelte';
  import StationCard from './StationCard.svelte';
  import HeartIcon from '../../../lib/HeartIcon.svelte';
  import { addFavourite, orderFavourites, refreshFavourites, removeFavourite } from '../../../lib/radio.js';

  let { favourites = [], playingId = null, onplay } = $props();

  let selected = $state(null);
  //: The removed, each with the place it had: `{station, at}`.
  let ghosts = $state([]);
  //: An order asked for and not yet back from the core, so a move shows at once.
  let pending = $state(null);

  const ghostIds = $derived(new Set(ghosts.map((g) => g.station.id)));
  const real = $derived.by(() => {
    const byId = new Map(favourites.map((s) => [s.id, s]));
    const order = pending ? pending.filter((id) => byId.has(id)) : favourites.map((s) => s.id);
    // A station another surface added since the order was asked for comes last.
    for (const s of favourites) if (!order.includes(s.id)) order.push(s.id);
    return order.map((id) => byId.get(id)).filter((s) => !ghostIds.has(s.id));
  });
  $effect(() => {
    if (pending && favourites.map((s) => s.id).join() === pending.join()) pending = null;
  });
  const cards = $derived.by(() => {
    const out = real.map((station) => ({ station, removed: false }));
    for (const g of [...ghosts].sort((a, b) => a.at - b.at)) {
      out.splice(Math.min(g.at, out.length), 0, { station: g.station, removed: true });
    }
    return out;
  });

  async function order(ids) {
    pending = ids;
    try {
      await orderFavourites(ids);
      await refreshFavourites();
    } catch (err) {
      pending = null;
      console.info('radio:', err.message);
    }
  }
  function move(station, by) {
    const ids = real.map((s) => s.id);
    const i = ids.indexOf(station.id);
    const j = i + by;
    if (i < 0 || j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j], ids[i]];
    order(ids);
  }
  async function remove(station, at) {
    if (selected === station.id) selected = null;
    ghosts = [...ghosts, { station, at }];
    try {
      await removeFavourite(station.id);
      await refreshFavourites();
    } catch (err) {
      ghosts = ghosts.filter((g) => g.station.id !== station.id);
      console.info('radio:', err.message);
    }
  }
  async function undo(station) {
    const ghost = ghosts.find((g) => g.station.id === station.id);
    if (!ghost) return;
    // Its place among the stations still there: the cards before it, less
    // the other removed ones.
    const before = cards.slice(0, cards.findIndex((c) => c.station.id === station.id)).filter((c) => !c.removed);
    const ids = real.map((s) => s.id);
    ids.splice(before.length, 0, station.id);
    try {
      await addFavourite(station);
      ghosts = ghosts.filter((g) => g.station.id !== station.id);
      await order(ids);
    } catch (err) {
      console.info('radio:', err.message);
    }
  }
</script>

{#if cards.length}
  <Sideways>
    <div class="grid">
      {#each cards as card, i (card.station.id)}
        {@const at = real.indexOf(card.station)}
        <StationCard
          station={card.station}
          num={i + 1}
          removed={card.removed}
          favourite
          selected={selected === card.station.id}
          playing={playingId === card.station.id}
          moves={{ earlier: at > 0 ? () => move(card.station, -1) : null, later: at < real.length - 1 ? () => move(card.station, 1) : null }}
          onselect={() => (selected = selected === card.station.id ? null : card.station.id)}
          onplay={() => {
            selected = null;
            onplay(card.station);
          }}
          onheart={() => remove(card.station, i)}
          onundo={() => undo(card.station)}
        />
      {/each}
    </div>
  </Sideways>
{:else}
  <div class="none">
    <div class="empty">
      <span class="empty__disc"><HeartIcon size={32} ink="var(--favourite)" /></span>
      <div class="empty__text">
        <span class="empty__head">No favourites yet</span>
        <span class="empty__note">Tap the heart on any station to keep it here, in your own order. Next and Previous then step through them.</span>
      </div>
    </div>
  </div>
{/if}

<style>
  .grid {
    display: grid;
    grid-auto-flow: column;
    grid-template-rows: repeat(2, 120px);
    grid-auto-columns: max-content;
    gap: 16px;
  }
  /* B06: a dashed plate 900 x 240, 32 right of the side column. */
  .none {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    padding-left: 32px;
  }
  .empty {
    width: 900px;
    max-width: calc(100% - 32px);
    height: 240px;
    box-sizing: border-box;
    border-radius: var(--r-xl);
    border: 1.5px dashed var(--favourites-empty-line);
    display: flex;
    align-items: center;
    gap: 26px;
    padding: 0 36px;
  }
  .empty__disc {
    width: 80px;
    height: 80px;
    border-radius: var(--r-circle);
    box-sizing: border-box;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(var(--c-favourite-rgb), 0.14);
    border: 1px solid rgba(var(--c-favourite-rgb), 0.3);
  }
  .empty__text {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-width: 0;
  }
  .empty__head {
    font-size: 26px;
    font-weight: 700;
  }
  .empty__note {
    font-size: 19px;
    line-height: 1.45;
    color: var(--ink-muted);
  }
</style>
