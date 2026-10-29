<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **Add players, on the panel** (ADR-0166; design/source/22, 2a-2): the
  drawer's card turned to the other players on the network, each with Join.
  The group's own members are listed with what they do and no button; a
  player that is joining says it is catching up. Over the drawer's own
  scrim, which closes both. Another group is one row (ADR-0166 decision
  11): its players named, its leader first, what it plays, and - from a
  player in no group - *Join this group*; its players are not joined one by
  one.
-->
<script>
  import mark from '../../assets/gexis-mark.svg';
  import GroupGlyph from '../../lib/GroupGlyph.svelte';
  import { enterGroup, joinable, joinPlayer, memberStatus, othersByGroup, otherStatus } from '../../lib/group.svelte.js';

  //: `others`: /players' others; `leader`: whose music they will play.
  let { open, g = null, others = [], leader = '', onback, onflash, onjoined } = $props();

  //: Joins sent and not yet in the group: their rows catch up at once.
  let asked = $state({});

  const inGroup = $derived(new Set((g?.members ?? []).map((m) => m.id)));
  const split = $derived(othersByGroup(others, inGroup));
  //: Another group asked to take this player, until this player is grouped.
  let entering = $state(null);
  $effect(() => {
    if (g && entering) entering = null;
  });
  const rows = $derived([
    ...(g?.members ?? []).filter((m) => !m.me).map((m) => ({
      id: m.id, name: m.name, leads: m.leads && m.reachable, status: memberStatus(g, m),
      joining: m.joining, off: !m.reachable, button: false,
    })),
    ...split.groups.map((og) => ({
      id: `group:${og.id}`, name: og.title, leads: false, group: og,
      status: entering === og.id ? 'Joining · catching up' : `Led by ${og.members[0]?.name} · ${og.status}`,
      joining: entering === og.id, off: false, button: false, enter: !g && og.canEnter && entering !== og.id,
    })),
    ...split.loose.map((p) => ({
      id: p.id ?? p.url, name: p.name, leads: false,
      status: asked[p.id] ? 'Joining · catching up' : otherStatus(p),
      joining: !!asked[p.id], off: false, button: joinable(p) && !asked[p.id], player: p,
    })),
  ]);

  async function enter(row) {
    entering = row.group.id;
    try {
      await enterGroup(row.group.leader);
    } catch (error) {
      entering = null;
      onflash?.(`Not joined: ${error.message}`);
    }
  }

  $effect(() => {
    // A join the group has taken is no longer the panel's to show.
    for (const id of Object.keys(asked)) if (inGroup.has(id)) delete asked[id];
  });

  async function join(row) {
    asked = { ...asked, [row.id]: true };
    try {
      await joinPlayer(row.id);
      onjoined?.();
    } catch (error) {
      const { [row.id]: _, ...rest } = asked;
      asked = rest;
      onflash?.(`${row.name} did not join: ${error.message}`);
    }
  }
</script>

<div class="card" class:is-open={open} role="dialog" aria-label="Add players" aria-hidden={!open} inert={!open}
     ondpadback={(event) => { event.preventDefault(); onback?.(); }}>
  <div class="head">
    <button class="back" type="button" aria-label="Back" data-dpad-back onclick={onback}>
      <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true">
        <path d="M20,11V13H8L13.5,18.5L12.08,19.92L4.16,12L12.08,4.08L13.5,5.5L8,11H20Z" fill="#e9eef2" />
      </svg>
    </button>
    <div class="head__text">
      <div class="title">Add players</div>
      <div class="sub">They play what {leader} plays, in sync. A player that joins stops its own music and catches up in a moment.</div>
    </div>
    <button class="done" type="button" onclick={onback}>Done</button>
  </div>
  <div class="rows">
    {#each rows as row (row.id)}
      <div class="row-wrap">
        <div class="row">
          {#if row.group}
            <span class="mark mark--group"><GroupGlyph size={30} ink="var(--ink-quiet)" /></span>
          {:else}
            <img src={mark} alt="" class="mark" class:is-off={row.off} />
          {/if}
          <div class="text" class:is-off={row.off}>
            <span class="name">{row.name}{#if row.leads}<span class="leads">Leads</span>{/if}</span>
            <span class="status" class:is-joining={row.joining} class:is-quiet={row.off}>{row.status}</span>
          </div>
          {#if row.button}
            <button class="join" type="button" onclick={() => join(row)}>Join</button>
          {:else if row.enter}
            <button class="join" type="button" onclick={() => enter(row)}>Join this group</button>
          {/if}
        </div>
      </div>
    {/each}
  </div>
</div>

<style>
  .card {
    position: absolute;
    left: 50%;
    top: 50%;
    z-index: 15;
    width: 820px;
    max-height: min(760px, calc(100% - 24px));
    background: var(--bg-panel);
    border: 1px solid var(--group-line);
    border-radius: 28px;
    padding: 26px;
    box-sizing: border-box;
    box-shadow: 0 34px 90px rgba(0, 0, 0, 0.6);
    display: flex;
    flex-direction: column;
    gap: 14px;
    transition: transform 240ms cubic-bezier(0.2, 0.8, 0.2, 1), opacity 200ms ease;
    transform: translate(-50%, -50%) scale(0.94);
    opacity: 0;
    pointer-events: none;
  }
  .card.is-open {
    transform: translate(-50%, -50%) scale(1);
    opacity: 1;
    pointer-events: auto;
  }

  .head {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 0 0 0 10px;
  }
  .back {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: rgba(233, 238, 242, 0.07);
    border: 0;
    padding: 0;
    display: grid;
    place-items: center;
    flex-shrink: 0;
    margin-left: -10px;
  }
  .back:active, .done:active, .join:active { transform: scale(0.95); }
  .head__text { flex: 1; min-width: 0; }
  .title { font-size: 25px; font-weight: 700; letter-spacing: -0.01em; }
  .sub { font-size: 15px; margin-top: 4px; color: rgba(233, 238, 242, 0.6); text-wrap: pretty; }
  .done {
    font: inherit;
    height: 56px;
    padding: 0 22px;
    border-radius: 15px;
    box-sizing: border-box;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.14);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 17px;
    font-weight: 600;
    white-space: nowrap;
    flex-shrink: 0;
    color: var(--ink);
  }

  .rows {
    min-height: 0;
    overflow-y: auto;
    scrollbar-width: none;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .rows::-webkit-scrollbar { display: none; }
  .row-wrap { flex-shrink: 0; border-radius: 16px; overflow: hidden; }
  .row {
    display: flex;
    align-items: center;
    gap: 16px;
    min-height: 72px;
    padding: 0 14px 0 18px;
  }
  .mark { width: 34px; height: 34px; display: block; flex-shrink: 0; }
  .mark--group { display: grid; place-items: center; }
  .mark.is-off, .text.is-off { opacity: var(--group-off-opacity); }
  .text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  .name {
    font-size: 19px;
    font-weight: 700;
    line-height: 1.25;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }
  .leads {
    display: inline-block;
    vertical-align: 3px;
    margin-left: 10px;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 400;
    line-height: 1;
    letter-spacing: var(--group-leads-tracking);
    text-transform: uppercase;
    padding: 5px 7px;
    border-radius: 7px;
    background: var(--group-leads-ground);
    color: var(--group-ink);
  }
  .status {
    font-size: 15px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: rgba(233, 238, 242, 0.72);
  }
  .status.is-joining { color: var(--group-ink); }
  .status.is-quiet { color: rgba(233, 238, 242, 0.6); }
  .join {
    font: inherit;
    flex-shrink: 0;
    height: 52px;
    padding: 0 20px;
    border-radius: 14px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    font-size: 17px;
    font-weight: 700;
    background: var(--group-join-ground);
    border: 1px solid var(--group-join-line);
    color: var(--group-ink);
  }
</style>
