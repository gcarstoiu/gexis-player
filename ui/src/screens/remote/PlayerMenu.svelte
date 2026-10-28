<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0164: the player menu (design/source/21, *Player menu*), from the
  picker: *Gexis players*, this one first with its check, then the others on
  the network (`/players`, ADR-0136), each with what it is doing. Another
  opens its own page in the same tab (C1), which closes everything here.

  ADR-0166, design/source/22 (1a): **Join and Remove on each row.** Grouped,
  the top of the list is the group: its head (*Grouped · 3 players* and what
  plays), its members - the leader tagged *Leads*, Remove on the others but
  this one - the leader gone's note, and Leave group (not for the leader) and
  Undo group; then *Other players*, each with Join. A player older than
  multiroom has no Join and says why.

  ADR-0166 decision 11 (George, 2026-10-28): **another group shows as a
  group** - its players together, its leader tagged, what it plays - in the
  block's shape, neutral rather than this group's teal; joined whole with
  *Join this group* from a player in no group, never raided a player at a
  time.
-->
<script>
  import mark from '../../assets/gexis-mark.svg';
  import { said } from './commands.js';
  import { FILLED } from './icons.js';
  import GroupGlyph from '../../lib/GroupGlyph.svelte';
  import {
    enterGroup, group, groupHead, groupSub, joinPlayer, joinable, leaveGroup, memberStatus, othersByGroup, otherStatus,
    removePlayer, silentNote,
  } from '../../lib/group.svelte.js';

  let { open = false, me = null, others = [], here = null, onclose = () => {}, onundo = () => {}, onsay = () => {} } = $props();

  const g = $derived($group);
  const inGroup = $derived(new Set((g?.members ?? []).map((m) => m.id)));
  const split = $derived(othersByGroup(others, inGroup));
  const rest = $derived(split.loose);
  const otherGroups = $derived(split.groups);
  const leading = $derived(!!g?.members.find((m) => m.me)?.leads);
  //: Joined from here and not yet in the group: said at once.
  let joining = $state(new Set());
  $effect(() => {
    if (!joining.size) return;
    const still = new Set([...joining].filter((id) => !inGroup.has(id)));
    if (still.size !== joining.size) joining = still;
  });

  const told = (what) => (error) => onsay(`${what}: ${error.message}`);
  function join(event, p) {
    event.preventDefault();
    event.stopPropagation();
    joining = new Set([...joining, p.id]);
    joinPlayer(p.id).catch((error) => {
      joining = new Set([...joining].filter((id) => id !== p.id));
      told('Not joined')(error);
    });
  }
  function remove(event, m) {
    event.preventDefault();
    event.stopPropagation();
    removePlayer(m.id).catch(told('Not removed'));
  }
  function leave() {
    leaveGroup().catch(told('Not left'));
  }
  //: Another group asked to take this player, until this player is in it.
  let entering = $state(null);
  $effect(() => {
    if (g && entering) entering = null;
  });
  function enter(event, og) {
    event.preventDefault();
    event.stopPropagation();
    entering = og.id;
    enterGroup(og.leader).catch((error) => {
      entering = null;
      told('Not joined')(error);
    });
  }
</script>

{#snippet act(label, isJoin, onclick)}
  <button class="act" class:is-join={isJoin} type="button" {onclick}>{label}</button>
{/snippet}

{#if open}
  <div class="scrim" role="presentation" onclick={onclose}></div>
  <div class="menu" role="dialog" aria-label="Gexis players">
    <div class="head">Gexis players</div>
    {#if g}
      <div class="group">
        <div class="group__head">
          <GroupGlyph size={20} ink="var(--group-ink)" />
          <span class="text">
            <span class="group__title">{groupHead(g)}</span>
            <span class="state">{groupSub(g)}</span>
          </span>
        </div>
        {#each g.members as m (m.id)}
          <svelte:element this={m.me || !m.reachable || !m.url ? 'div' : 'a'} class="row row--member"
                          class:is-current={m.me} class:is-off={!m.reachable}
                          href={m.me || !m.reachable ? undefined : m.url}>
            <img src={mark} alt="" />
            <span class="text">
              <span class="name">{m.name}{#if m.leads && !g.silent}<span class="leads">Leads</span>{/if}</span>
              <span class="state" class:is-joining={m.joining} class:is-off={!m.reachable}>{memberStatus(g, m)}</span>
            </span>
            {#if m.me}
              <svg class="check" viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.check} /></svg>
            {:else if m.reachable && !m.leads}
              {@render act('Remove', false, (e) => remove(e, m))}
            {/if}
          </svelte:element>
        {/each}
        {#if g.silent}<div class="note">{silentNote(g)}</div>{/if}
        <div class="group__buttons">
          {#if !leading}<button class="wide" type="button" onclick={leave}>Leave group</button>{/if}
          <button class="wide wide--undo" type="button" onclick={onundo}>Undo group</button>
        </div>
      </div>
      {#if rest.length || otherGroups.length}<div class="head head--others">Other players</div>{/if}
    {:else}
      <div class="row is-current">
        <img src={mark} alt="" />
        <span class="text">
          <span class="name">{here?.name ?? me?.name ?? 'This player'}</span>
          <span class="state">{here?.state ?? said(me)}</span>
        </span>
        <svg class="check" viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.check} /></svg>
      </div>
    {/if}
    {#each otherGroups as og (og.id)}
      <div class="group group--other">
        <div class="group__head">
          <GroupGlyph size={20} ink="var(--ink-quiet)" />
          <span class="text">
            <span class="group__title">{og.title}</span>
            <span class="state">{og.status}</span>
          </span>
        </div>
        {#each og.members as m (m.id)}
          <svelte:element this={m.url ? 'a' : 'div'} class="row row--member" class:is-off={!m.listed}
                          href={m.url ?? undefined}>
            <img src={mark} alt="" />
            <span class="text">
              <span class="name">{m.name}{#if m.leads && m.listed}<span class="leads leads--other">Leads</span>{/if}</span>
              {#if !m.listed}<span class="state is-off">Not reachable</span>{/if}
            </span>
          </svelte:element>
        {/each}
        {#if !g && og.canEnter}
          <div class="group__buttons">
            <button class="wide wide--join" type="button" disabled={entering === og.id} onclick={(e) => enter(e, og)}>
              {entering === og.id ? 'Joining · catching up' : 'Join this group'}
            </button>
          </div>
        {/if}
      </div>
    {/each}
    {#each rest as p (p.url)}
      <a class="row row--other" href={p.url}>
        <img src={mark} alt="" />
        <span class="text">
          <span class="name">{p.name}</span>
          <span class="state" class:is-joining={joining.has(p.id)}>{joining.has(p.id) ? 'Joining · catching up' : otherStatus(p)}</span>
        </span>
        {#if joinable(p) && !joining.has(p.id)}
          {@render act('Join', true, (e) => join(e, p))}
        {/if}
      </a>
    {/each}
  </div>
{/if}

<style>
  .scrim {
    position: absolute;
    inset: 0;
    z-index: 30;
    background: rgba(4, 8, 10, 0.45);
  }
  .menu {
    position: absolute;
    z-index: 31;
    left: 16px;
    right: 16px;
    top: calc(72px + env(safe-area-inset-top, 0px));
    background: #16232c;
    border: 1px solid rgba(233, 238, 242, 0.14);
    border-radius: 18px;
    box-shadow: 0 18px 48px rgba(0, 0, 0, 0.55);
    padding: 8px 0;
    max-height: calc(100% - 96px);
    overflow-y: auto;
    scrollbar-width: none;
  }
  .menu::-webkit-scrollbar {
    display: none;
  }
  .head {
    padding: 8px 18px 6px;
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: rgba(233, 238, 242, 0.6);
  }
  .head--others {
    padding: 6px 18px 4px;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 64px;
    padding: 0 18px;
    color: #e9eef2;
    text-decoration: none;
    cursor: pointer;
  }
  /* The design's: a row that may hold a button keeps 12 at the right, a
     member's row 10 inside the group block. */
  .row--other {
    padding: 0 12px 0 18px;
  }
  .row--member {
    padding: 0 10px 0 12px;
  }
  .row.is-current {
    background: rgba(233, 238, 242, 0.05);
    cursor: default;
  }
  .row.is-off {
    cursor: default;
  }
  .row.is-off img,
  .row.is-off .text {
    opacity: var(--group-off-opacity);
  }
  img {
    width: 30px;
    height: 30px;
    display: block;
    flex-shrink: 0;
  }
  .text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 1px;
  }
  .name {
    font-size: 16px;
    font-weight: 700;
    line-height: 1.25;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }
  .leads {
    display: inline-block;
    vertical-align: 2px;
    margin-left: 8px;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 400;
    line-height: 1;
    letter-spacing: var(--group-leads-tracking);
    text-transform: uppercase;
    padding: 4px 6px;
    border-radius: 6px;
    background: var(--group-leads-ground);
    color: var(--group-ink);
  }
  .state {
    font-size: 13px;
    color: rgba(233, 238, 242, 0.72);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .state.is-joining {
    color: var(--group-ink);
  }
  .state.is-off {
    color: rgba(233, 238, 242, 0.6);
  }
  .check {
    width: 22px;
    height: 22px;
    flex-shrink: 0;
    fill: #7ed6bc;
  }
  .act {
    flex-shrink: 0;
    height: 44px;
    padding: 0 14px;
    border-radius: 12px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    font-family: var(--font-ui);
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.14);
    color: #e9eef2;
  }
  .act.is-join {
    background: var(--group-join-ground);
    border-color: var(--group-join-line);
    color: var(--group-ink);
  }
  .act:active {
    transform: scale(0.95);
  }
  .group {
    margin: 4px 8px 8px;
    border-radius: 14px;
    background: var(--group-ground);
    border: 1px solid var(--group-line);
    padding: 12px 0 10px;
    overflow: hidden;
  }
  .group__head {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 12px 6px;
  }
  .group__title {
    font-size: 14px;
    font-weight: 700;
    color: var(--group-ink);
  }
  .note {
    padding: 6px 12px 2px;
    font-size: 13px;
    line-height: 1.4;
    color: var(--group-undo-ink);
    text-wrap: pretty;
  }
  .group__buttons {
    display: flex;
    gap: 8px;
    padding: 8px 10px 0;
  }
  .wide {
    flex: 1;
    height: 44px;
    border-radius: 12px;
    box-sizing: border-box;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.14);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-ui);
    font-size: 15px;
    font-weight: 700;
    white-space: nowrap;
    cursor: pointer;
    color: #e9eef2;
  }
  .wide--undo {
    color: var(--group-undo-ink);
  }
  /* Another group (decision 11): the block's shape, neutral, not ours. */
  .group--other {
    background: rgba(233, 238, 242, 0.04);
    border-color: rgba(233, 238, 242, 0.12);
  }
  .group--other .group__title {
    color: var(--ink);
  }
  /* Its players carry a name only (the head says what they play). */
  .group--other .row--member {
    min-height: 48px;
  }
  .leads--other {
    background: rgba(233, 238, 242, 0.08);
    color: var(--ink-muted);
  }
  .wide--join {
    background: var(--group-join-ground);
    border-color: var(--group-join-line);
    color: var(--group-ink);
  }
  .wide--join:disabled {
    cursor: default;
    opacity: 0.8;
  }
  .wide:active {
    transform: scale(0.97);
  }
</style>
