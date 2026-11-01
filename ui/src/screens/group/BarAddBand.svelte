<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The bar tray's *Add players* band (ADR-0166; design/source/22, 2a, bar,
  `add-band`): the title and what joining does, the other players as cards
  with Join - a member of this group with its status and no button, one out
  of reach faded - and Done. Another group is one card (ADR-0166 decision
  11): its players named, led by whom, what it plays, and - from a player in
  no group - *Join this group*.
-->
<script>
  import mark from '../../assets/gexis-mark.svg';
  import GroupGlyph from '../../lib/GroupGlyph.svelte';
  import { enterGroup, joinable, joinPlayer, memberStatus, othersByGroup, otherStatus, withoutMe } from '../../lib/group.svelte.js';

  //: `players`: `/players`' others; `here`: this player's own status.
  let { g, players = [], here = null, ondone, onerror = () => {} } = $props();

  const leaderName = $derived(g ? g.members.find((m) => m.leads)?.name : here?.name);
  const sub = $derived(`They play what ${leaderName ?? 'this player'} plays, in sync.`);
  //: Joins asked for and not yet in the group: their button goes at once,
  //: and comes back if the player is taken out again later.
  let asked = $state(new Set());
  $effect(() => {
    const members = new Set((g?.members ?? []).map((m) => m.id));
    if ([...asked].some((id) => members.has(id))) asked = new Set([...asked].filter((id) => !members.has(id)));
  });

  //: Another group asked to take this player, until this player is grouped.
  let entering = $state(null);
  $effect(() => {
    if (g && entering) entering = null;
  });
  const rows = $derived.by(() => {
    const members = new Map((g?.members ?? []).map((m) => [m.id, m]));
    const list = withoutMe(players, here?.id, new Set(members.keys()));
    const split = othersByGroup(list, new Set(members.keys()));
    const out = [];
    for (const og of split.groups) {
      out.push({ id: `group:${og.id}`, name: og.title, group: og, joining: entering === og.id, off: false, join: false,
                 status: entering === og.id ? 'Joining · catching up' : `Led by ${og.members[0]?.name} · ${og.status}`,
                 enter: !g && og.canEnter && entering !== og.id });
    }
    const inOther = new Set(split.groups.flatMap((og) => og.members.map((m) => m.id)));
    for (const p of list) {
      if (inOther.has(p.id)) continue;
      const m = members.get(p.id);
      if (m?.me) continue;
      out.push(m
        ? { id: p.id, name: m.name, status: memberStatus(g, m), joining: m.joining, off: !m.reachable, join: false }
        : { id: p.id, name: p.name, status: otherStatus(p), joining: false, off: false, join: joinable(p) && !asked.has(p.id) });
      members.delete(p.id);
    }
    // A member the network search does not find now: out of reach.
    for (const m of members.values()) {
      if (m.me) continue;
      out.push({ id: m.id, name: m.name, status: memberStatus(g, m), joining: false, off: !m.reachable, join: false });
    }
    return out;
  });

  async function enter(og) {
    entering = og.id;
    try {
      await enterGroup(og.leader);
    } catch (error) {
      entering = null;
      onerror(error.message);
    }
  }

  async function join(id) {
    asked = new Set([...asked, id]);
    try {
      await joinPlayer(id);
    } catch (error) {
      asked = new Set([...asked].filter((x) => x !== id));
      onerror(error.message);
    }
  }
</script>

<div class="band">
  <div class="head">
    <span class="title">Add players</span>
    <span class="sub">{sub}</span>
  </div>
  <div class="cards" data-pan-x>
    {#each rows as r (r.id)}
      <div class="card" class:is-off={r.off}>
        {#if r.group}
          <span class="logo logo--group"><GroupGlyph size={26} ink="var(--ink-quiet)" /></span>
        {:else}
          <img class="logo" src={mark} alt="" />
        {/if}
        <div class="text">
          <span class="name">{r.name}</span>
          <span class="status" class:is-joining={r.joining} class:is-off={r.off}>{r.status}</span>
        </div>
        {#if r.join}
          <button class="join" type="button" aria-label={`Join ${r.name}`} onclick={() => join(r.id)}>Join</button>
        {:else if r.enter}
          <button class="join" type="button" aria-label={`Join the group of ${r.name}`} onclick={() => enter(r.group)}>Join</button>
        {/if}
      </div>
    {/each}
  </div>
  <button class="done" type="button" onclick={ondone}>Done</button>
</div>

<style>
  .band {
    position: relative;
    z-index: 1;
    height: 150px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 0 40px;
    box-sizing: border-box;
    border-top: 1px solid rgba(233, 238, 242, 0.08);
    text-transform: none;
    letter-spacing: normal;
    color: var(--ink);
  }
  .head {
    flex-shrink: 0;
    width: 200px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .title { font-size: 20px; font-weight: 700; }
  .sub { font-size: 15px; line-height: 1.35; color: rgba(233, 238, 242, 0.6); }
  .cards {
    flex: 1;
    min-width: 0;
    display: flex;
    gap: 12px;
    overflow-x: auto;
    scrollbar-width: none;
    touch-action: pan-x;
    -webkit-mask-image: linear-gradient(90deg, #000 0, #000 calc(100% - 88px), transparent 100%);
    mask-image: linear-gradient(90deg, #000 0, #000 calc(100% - 88px), transparent 100%);
  }
  .cards::-webkit-scrollbar { display: none; }
  .card {
    flex-shrink: 0;
    width: 330px;
    height: 116px;
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(233, 238, 242, 0.1);
    box-sizing: border-box;
    padding: 0 12px 0 18px;
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .card.is-off { opacity: var(--group-off-opacity); }
  .logo { width: 34px; height: 34px; display: block; flex-shrink: 0; }
  .logo--group { display: grid; place-items: center; }
  .text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .name {
    font-size: 18px;
    font-weight: 700;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    padding-right: 3px;
  }
  .status {
    font-size: 15px;
    line-height: 1.3;
    color: rgba(233, 238, 242, 0.72);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .status.is-joining { color: var(--group-ink); }
  .status.is-off { color: rgba(233, 238, 242, 0.6); }
  .join {
    flex-shrink: 0;
    height: 56px;
    padding: 0 20px;
    border-radius: 15px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    font: inherit;
    font-size: 18px;
    font-weight: 700;
    background: var(--group-join-ground);
    border: 1px solid var(--group-join-line);
    color: var(--group-ink);
  }
  .join:active,
  .done:active { transform: scale(0.95); }
  .done {
    height: 56px;
    padding: 0 22px;
    border-radius: 15px;
    box-sizing: border-box;
    background: var(--ink-fill);
    border: 1px solid rgba(233, 238, 242, 0.14);
    color: var(--ink);
    display: flex;
    align-items: center;
    justify-content: center;
    font: inherit;
    font-size: 18px;
    font-weight: 600;
    white-space: nowrap;
    flex-shrink: 0;
  }
</style>
