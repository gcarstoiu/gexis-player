<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The group volume in the panel's volume drawer** (ADR-0166 D6;
  design/source/22, 2a): grouped, the drawer's volume becomes the group's -
  its head with + Add players, the *All players* slider (the drawer's own big
  one), each member's own row, the note while the leader is gone, and Leave
  group (a member's) and Undo group.
-->
<script>
  import { onDestroy } from 'svelte';
  import GroupGlyph from '../../lib/GroupGlyph.svelte';
  import VolumeIcon from '../../lib/VolumeIcon.svelte';
  import {
    LevelSender, dragStart, groupLevel, leaveGroup, levelsSub, removePlayer, setGroupMute,
    setMemberMute, setMemberVolume, silentNote, stepped,
  } from '../../lib/group.svelte.js';
  import PanelMemberRow from './PanelMemberRow.svelte';
  import { track } from './panelSlider.js';

  let { g, onadd, onundo, onflash } = $props();

  //: **What the sliders show while a finger moves them**, and for a moment
  //: after (as the drawer's own slider settles): the core's answer arrives
  //: through every member's /state and would pull a knob back mid-drag.
  let local = $state({});
  let allLocal = $state(null);
  let settle = null;
  const SETTLE_MS = 1500;
  function settleLater() {
    clearTimeout(settle);
    settle = setTimeout(() => { local = {}; allLocal = null; }, SETTLE_MS);
  }
  onDestroy(() => clearTimeout(settle));

  const fail = (what) => (error) => onflash?.(`${what}: ${error.message}`);
  const allSender = new LevelSender(groupLevel, fail('Group volume not changed'));
  const senders = {};
  const senderOf = (id) => (senders[id] ??= new LevelSender(setMemberVolume, fail('Volume not changed')));

  const variable = $derived(g.members.filter((m) => m.reachable && !m.fixed && m.volume != null));
  const allLevel = $derived(allLocal ?? g.level ?? 0);
  const allText = $derived(!variable.length ? '—' : g.muted ? 'Off' : String(allLevel));
  const levelOf = (m) => local[m.id] ?? m.volume;

  //: The *All* slider's drag starts from the members' levels as they are,
  //: and moves each the same share of its own way (the design's `_gBase`).
  let from = null;
  const allDrag = track((percent, first) => {
    if (!variable.length) return;
    clearTimeout(settle);
    if (first || from == null) from = dragStart(g);
    allLocal = percent;
    local = stepped(from, percent);
    allSender.send(percent, from);
  }, () => { from = null; settleLater(); });
  const DPAD_STEP = 2;
  function allStep(step) {
    if (!variable.length) return;
    const start = dragStart(g);
    // From the level shown: a scroll sends several steps before the
    // members' answer arrives.
    const target = Math.max(0, Math.min(100, allLevel + step * DPAD_STEP));
    allLocal = target;
    local = stepped(start, target);
    allSender.send(target, start);
    settleLater();
  }

  function memberLevel(m, percent) {
    clearTimeout(settle);
    local = { ...local, [m.id]: percent };
    senderOf(m.id).send(m.id, percent);
  }

  const muteAll = () => setGroupMute(!g.muted).catch(fail('Mute not changed'));
  const muteOne = (m) => setMemberMute(m.id, !m.muted).catch(fail('Mute not changed'));
  const remove = (m) => removePlayer(m.id).catch(fail(`${m.name} not removed`));
  const leave = () => leaveGroup().catch(fail('Not left'));

  const me = $derived(g.members.find((m) => m.me));
  const canLeave = $derived(!!me && !me.leads);

  //: Five or more scroll at 256 with a fade (the design's `listMax`): the
  //: fade only while the list scrolls.
  let list = $state(null);
  let overflowing = $state(false);
  $effect(() => {
    if (!list) return;
    const look = () => (overflowing = list.scrollHeight > list.clientHeight + 1);
    look();
    const observer = new ResizeObserver(look);
    observer.observe(list);
    return () => observer.disconnect();
  });
  $effect(() => {
    g.members.length;
    if (list) overflowing = list.scrollHeight > list.clientHeight + 1;
  });
</script>

<div class="head">
  <GroupGlyph size={26} ink="var(--group-ink)" />
  <div class="head__text">
    <div class="head__title">Group volume</div>
    <div class="head__sub">{levelsSub(g)}</div>
  </div>
  <button class="button button--52" type="button" onclick={onadd}><span class="plus">+</span>Add players</button>
</div>

<div class="all">
  <span class="all__name">All players</span>
  <button class="mute" type="button" aria-label={g.muted ? 'Unmute all players' : 'Mute all players'} onclick={muteAll}>
    <VolumeIcon percent={allLevel} muted={g.muted} />
  </button>
  <div class="track" role="slider" tabindex="-1" aria-label="All players volume"
       aria-valuemin="0" aria-valuemax="100" aria-valuenow={allLevel} data-dpad-main data-step={DPAD_STEP}
       ondpadstep={(event) => allStep(event.detail.step)}
       onpointerdown={allDrag.down} onpointermove={allDrag.move} onpointerup={allDrag.up} onpointercancel={allDrag.up}>
    <div class="rail">
      <div class="fill" class:is-muted={g.muted} style:width={`${allLevel}%`}></div>
      <div class="knob" style:left={`${allLevel}%`}></div>
    </div>
  </div>
  <span class="value">{allText}</span>
  <span class="gap"></span>
</div>

<div class="rule"></div>

<div class="list" class:is-faded={overflowing} bind:this={list}>
  {#each g.members as m (m.id)}
    <PanelMemberRow {m} level={levelOf(m)}
                    canremove={m.reachable && !m.me && !m.leads}
                    onlevel={(percent) => memberLevel(m, percent)} ondone={settleLater}
                    onmute={() => muteOne(m)} onremove={() => remove(m)} />
  {/each}
</div>

{#if g.silent}
  <div class="note">{silentNote(g, true)}</div>
{/if}

<div class="actions">
  {#if canLeave}
    <button class="button button--58" type="button" onclick={leave}>Leave group</button>
  {/if}
  <button class="button button--58 button--undo" type="button" onclick={onundo}>Undo group</button>
</div>

<style>
  .head {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 10px;
  }
  .head__text { flex: 1; min-width: 0; }
  .head__title {
    font-size: 19px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .head__sub {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.06em;
    margin-top: 5px;
    color: rgba(233, 238, 242, 0.72);
  }

  .button {
    font: inherit;
    padding: 0 22px;
    border-radius: 15px;
    box-sizing: border-box;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.14);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    font-size: 17px;
    font-weight: 600;
    white-space: nowrap;
    flex-shrink: 0;
    color: var(--ink);
  }
  .button:active { transform: scale(0.95); }
  .button--52 { height: 52px; }
  .button--58 { height: 58px; }
  .button--undo {
    background: var(--group-undo-ground);
    border-color: var(--group-undo-line);
    color: var(--group-undo-ink);
    font-weight: 700;
  }
  .plus { font-size: 24px; font-weight: 400; line-height: 1; margin-top: -2px; }

  .all {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .all__name {
    width: 200px;
    flex-shrink: 0;
    font-size: 17px;
    font-weight: 700;
    color: var(--group-ink);
  }
  .mute {
    position: relative;
    width: 58px;
    height: 58px;
    border-radius: 15px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    border: 0;
    background: transparent;
    color: inherit;
  }
  .mute:active { transform: scale(0.95); }
  .track {
    flex: 1;
    height: 64px;
    display: flex;
    align-items: center;
    min-width: 0;
    touch-action: none;
  }
  .rail {
    width: 100%;
    height: 14px;
    border-radius: var(--r-pill);
    background: rgba(233, 238, 242, 0.14);
    position: relative;
  }
  .fill {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    border-radius: var(--r-pill);
    background: var(--group-ink);
  }
  .fill.is-muted { background: rgba(126, 214, 188, 0.35); }
  .knob {
    position: absolute;
    top: 50%;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    transform: translate(-50%, -50%);
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.45);
    background: var(--ink);
  }
  .value {
    font-family: var(--font-mono);
    font-size: 26px;
    font-weight: 600;
    width: 76px;
    text-align: right;
    flex-shrink: 0;
  }
  .gap { width: 48px; flex-shrink: 0; display: block; }

  .rule {
    flex-shrink: 0;
    height: 1px;
    background: rgba(233, 238, 242, 0.08);
    margin: 8px 0 4px;
  }

  /* Up to four rows (256, the design's `listMax`): five or more scroll here.
     It never gives way below that: on a short panel the drawer scrolls. */
  .list {
    flex-shrink: 0;
    max-height: 256px;
    overflow-y: auto;
    scrollbar-width: none;
    display: flex;
    flex-direction: column;
  }
  .list::-webkit-scrollbar { display: none; }
  .list.is-faded {
    -webkit-mask-image: linear-gradient(180deg, #000 0, #000 calc(100% - 48px), transparent 100%);
    mask-image: linear-gradient(180deg, #000 0, #000 calc(100% - 48px), transparent 100%);
  }

  .note {
    flex-shrink: 0;
    margin-top: 12px;
    font-size: 15px;
    line-height: 1.4;
    color: var(--group-undo-ink);
  }

  .actions {
    flex-shrink: 0;
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 16px;
  }
</style>
