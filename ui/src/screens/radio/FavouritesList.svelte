<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The favourites, in their order** (design/source/31, pick 3b; P08-P10).
  Numbered rows. A selected one has Play, Move up and Move down - no edit
  mode on the panel. The heart takes a station out at once; its row stays
  where it was, the name struck through, with Undo in the heart's place,
  until the list is left. Undo puts it back where it was.
-->
<script>
  import StationRow from './StationRow.svelte';
  import Scroll from './Scroll.svelte';
  import { addFavourite, orderFavourites, refreshFavourites, removeFavourite, count } from '../../lib/radio.js';

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
  const rows = $derived.by(() => {
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
    // Its place among the stations still there: the rows above it, less
    // the other removed ones.
    const above = rows.slice(0, rows.findIndex((r) => r.station.id === station.id)).filter((r) => !r.removed);
    const ids = real.map((s) => s.id);
    ids.splice(above.length, 0, station.id);
    try {
      await addFavourite(station);
      ghosts = ghosts.filter((g) => g.station.id !== station.id);
      await order(ids);
    } catch (err) {
      console.info('radio:', err.message);
    }
  }
</script>

<Scroll bar>
  <div class="kicker">
    <span class="kicker__label">{count(rows.length)} {rows.length === 1 ? 'station' : 'stations'} · in your order</span>
    <span class="kicker__aside">Select one to play or move it</span>
  </div>
  {#each rows as row, i (row.station.id)}
    {@const at = real.indexOf(row.station)}
    <StationRow
      station={row.station}
      num={i + 1}
      removed={row.removed}
      favourite
      selected={selected === row.station.id}
      playing={playingId === row.station.id}
      moves={{ up: at > 0 ? () => move(row.station, -1) : null, down: at < real.length - 1 ? () => move(row.station, 1) : null }}
      onselect={() => (selected = selected === row.station.id ? null : row.station.id)}
      onplay={() => {
        selected = null;
        onplay(row.station);
      }}
      onheart={() => remove(row.station, i)}
      onundo={() => undo(row.station)}
    />
  {/each}
</Scroll>

<style>
  .kicker {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 0 12px 6px 14px;
    flex-shrink: 0;
  }
  .kicker__label {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .kicker__aside {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.06em;
    color: var(--ink-quiet);
  }
</style>
