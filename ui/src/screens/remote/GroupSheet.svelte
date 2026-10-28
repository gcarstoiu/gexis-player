<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0166 D6, design/source/22 (*Phone: group volume*): built as the EQ
  sheet is. *Group volume*, the sub-line, the *All* slider - which moves
  every Variable member the same share of its own way from where they were
  when the drag began, and unmutes them - a rule, then each member's own
  row: a slider with its mute inside, the locked row for a Fixed one (its
  mute where the output has a control to silence), *Not reachable* for one
  that is off. The note under them names the Fixed members. A swipe down closes it, as the
  handle and the scrim do.
-->
<script>
  import { onDestroy } from 'svelte';
  import { FILLED } from './icons.js';
  import {
    LevelSender, dragStart, fixedNote, group, groupLevel, levelsSub, setGroupMute, setMemberMute,
    setMemberVolume, stepped,
  } from '../../lib/group.svelte.js';
  import { SheetPull } from './sheetPull.svelte.js';

  let { open = false, onclose = () => {}, onsay = () => {} } = $props();

  const g = $derived($group);
  const sheet = new SheetPull(() => onclose());
  const told = (error) => onsay(`Not changed: ${error.message}`);

  //: A slider let go keeps the finger's levels for SETTLE_MS, as the
  //: panel's do: the core's answer arrives through every member's /state,
  //: and the knob would jump back to the old levels first.
  const SETTLE_MS = 1500;
  const timers = {};
  function settleLater(key, clear) {
    clearTimeout(timers[key]);
    timers[key] = setTimeout(clear, SETTLE_MS);
  }
  onDestroy(() => Object.values(timers).forEach(clearTimeout));

  // ── The *All* slider ───────────────────────────────────────────────────
  const allSender = new LevelSender(groupLevel, told);
  let allDrag = $state(null); // { from, target, el, up }
  const variable = $derived((g?.members ?? []).filter((m) => m.reachable && !m.fixed && m.volume != null));
  const allFixed = $derived(!!g && variable.length === 0);
  const allLevel = $derived(allDrag ? Math.round(allDrag.target) : (g?.level ?? 0));
  const allMuted = $derived(!allDrag && !!g?.muted);

  function ratio(event, el) {
    const r = el.getBoundingClientRect();
    return Math.max(0, Math.min(1, (event.clientX - r.left) / r.width));
  }
  function allDown(event) {
    event.stopPropagation();
    if (!g || allFixed) return;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    allDrag = { from: dragStart(g), target: 0, el: event.currentTarget };
    allMove(event);
  }
  function allMove(event) {
    if (!allDrag || allDrag.up) return;
    allDrag.target = ratio(event, allDrag.el) * 100;
    allSender.send(allDrag.target, allDrag.from);
  }
  function allUp() {
    if (!allDrag) return;
    allDrag.up = true;
    const drag = allDrag;
    settleLater('all', () => { if (allDrag === drag) allDrag = null; });
  }

  // ── A member's own row ─────────────────────────────────────────────────
  const memberSender = new LevelSender(setMemberVolume, told);
  let memberDrag = $state(null); // { id, level, el, up }
  function levelOf(m) {
    if (memberDrag?.id === m.id) return memberDrag.level;
    if (allDrag && m.id in allDrag.from) return stepped(allDrag.from, allDrag.target)[m.id];
    return m.volume ?? 0;
  }
  function memberDown(event, m) {
    event.stopPropagation();
    event.currentTarget.setPointerCapture?.(event.pointerId);
    memberDrag = { id: m.id, level: m.volume ?? 0, el: event.currentTarget };
    if (m.muted) setMemberMute(m.id, false).catch(told);
    memberMove(event);
  }
  function memberMove(event) {
    if (!memberDrag || memberDrag.up) return;
    memberDrag.level = Math.round(ratio(event, memberDrag.el) * 100);
    memberSender.send(memberDrag.id, memberDrag.level);
  }
  function memberUp() {
    if (!memberDrag) return;
    memberDrag.up = true;
    const drag = memberDrag;
    settleLater('member', () => { if (memberDrag === drag) memberDrag = null; });
  }
  function tagOf(m) {
    if (!m.reachable) return 'Off';
    if (m.leads && !g.silent) return 'Leads';
    if (m.fixed) return 'Fixed';
    return m.me ? 'This one' : '';
  }
</script>

<div class="scrim" class:is-open={open} role="presentation" onclick={onclose}></div>
<div class="sheet" class:is-open={open} class:is-pulled={sheet.pull !== null} role="dialog" aria-label="Group volume"
     aria-hidden={!open} inert={!open} style:transform={sheet.pull !== null ? `translateY(${sheet.pull}px)` : null}
     onpointerdown={sheet.grab} onpointermove={sheet.drag} onpointerup={(e) => sheet.release(e)}
     onpointercancel={(e) => sheet.release(e, true)} onclickcapture={sheet.notTapped}>
  <button class="handle" type="button" aria-label="Close" onclick={onclose}></button>
  {#if g}
    <div class="head">
      <div class="title">Group volume</div>
      <div class="sub">{levelsSub(g)}</div>
    </div>
    <div class="all">
      <span class="all__name">All</span>
      <div class="all__bar" role="slider" tabindex="0" aria-label="Group volume" aria-valuemin="0" aria-valuemax="100"
           aria-valuenow={allLevel} onpointerdown={allDown} onpointermove={allMove} onpointerup={allUp}
           onpointercancel={allUp}>
        <span class="fill" class:is-muted={allMuted} style:width={`${allFixed ? 0 : allLevel}%`}></span>
        <span class="value" class:is-dark={!allMuted && allLevel > 86}>{allFixed ? 'Fixed' : allMuted ? 'Off' : allLevel}</span>
      </div>
    </div>
    <div class="rule"></div>
    <div class="rows">
      {#each g.members as m (m.id)}
        {@const level = levelOf(m)}
        {@const muted = m.muted && memberDrag?.id !== m.id && !(allDrag && m.id in allDrag.from)}
        <div class="member">
          <span class="who">
            <span class="who__name">{m.name}</span>
            <span class="who__tag" class:is-lead={m.leads && !g.silent}>{tagOf(m)}</span>
          </span>
          {#if !m.reachable}
            <span class="off">Not reachable</span>
          {:else if m.fixed}
            <div class="fixed" class:has-mute={m.fixed_mute !== null} aria-label="Fixed output">
              {#if m.fixed_mute !== null}
                <button class="mute mute--fixed" type="button" aria-label={m.fixed_mute ? 'Unmute' : 'Mute'}
                        aria-pressed={m.fixed_mute} onclick={() => setMemberMute(m.id, !m.fixed_mute).catch(told)}>
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d={m.fixed_mute ? FILLED.muted : FILLED.speaker} /></svg>
                </button>
              {/if}
              <span class="lock" aria-hidden="true"><span class="lock__shackle"></span><span class="lock__body"></span></span>
              <span class="fixed__text">Fixed output</span>
            </div>
          {:else}
            <div class="bar" role="slider" tabindex="0" aria-label={`${m.name} volume`} aria-valuemin="0"
                 aria-valuemax="100" aria-valuenow={muted ? 0 : level}
                 onpointerdown={(e) => memberDown(e, m)} onpointermove={memberMove} onpointerup={memberUp}
                 onpointercancel={memberUp}>
              <span class="fill" class:is-muted={muted} style:width={`${level}%`}></span>
              <button class="mute" class:is-dark={!muted && level > 14} type="button" aria-label={muted ? 'Unmute' : 'Mute'}
                      aria-pressed={muted} onpointerdown={(e) => e.stopPropagation()}
                      onclick={() => setMemberMute(m.id, !m.muted).catch(told)}>
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d={muted ? FILLED.muted : FILLED.speaker} /></svg>
              </button>
              <span class="value" class:is-dark={!muted && level > 86}>{muted ? 'Off' : level}</span>
            </div>
          {/if}
        </div>
      {/each}
    </div>
    <div class="note">{fixedNote(g)}</div>
  {/if}
</div>

<style>
  .scrim {
    position: absolute;
    inset: 0;
    z-index: 52;
    background: rgba(4, 8, 10, 0.55);
    opacity: 0;
    pointer-events: none;
    transition: opacity 260ms ease;
  }
  .scrim.is-open {
    opacity: 1;
    pointer-events: auto;
  }
  .sheet {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 53;
    max-height: calc(100% - 40px);
    box-sizing: border-box;
    background: #16232c;
    border-top: 1px solid rgba(233, 238, 242, 0.16);
    border-radius: 24px 24px 0 0;
    padding: 10px 16px calc(22px + env(safe-area-inset-bottom, 0px));
    display: flex;
    flex-direction: column;
    gap: 12px;
    box-shadow: 0 -10px 32px rgba(0, 0, 0, 0.6);
    transform: translateY(calc(100% + 24px));
    transition: transform var(--remote-slide);
    /* Down is the sheet's, as on the EQ sheet; the rows scroll their own way. */
    touch-action: pan-x;
  }
  .sheet.is-open {
    transform: translateY(0);
  }
  .sheet.is-pulled {
    transition: none;
  }
  .handle {
    align-self: center;
    flex-shrink: 0;
    width: 52px;
    height: 20px;
    margin: -8px 0;
    padding: 0;
    border: 0;
    background: none;
    cursor: pointer;
    position: relative;
  }
  .handle::after {
    content: '';
    position: absolute;
    left: 8px;
    top: 8px;
    width: 36px;
    height: 4px;
    border-radius: 2px;
    background: rgba(233, 238, 242, 0.24);
  }
  .head {
    flex-shrink: 0;
  }
  .title {
    font-size: 19px;
    font-weight: 700;
  }
  .sub {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.06em;
    margin-top: 4px;
    color: rgba(233, 238, 242, 0.72);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .all {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .all__name {
    width: 104px;
    flex-shrink: 0;
    font-size: 15px;
    font-weight: 700;
    color: var(--group-ink);
  }
  .all__bar,
  .bar {
    position: relative;
    flex: 1;
    min-width: 0;
    border-radius: 12px;
    background: rgba(233, 238, 242, 0.08);
    overflow: hidden;
    cursor: pointer;
    touch-action: none;
    outline: none;
  }
  .all__bar {
    height: 44px;
    border: 1px solid rgba(126, 214, 188, 0.35);
    box-sizing: border-box;
  }
  .bar {
    height: 36px;
  }
  .fill {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    background: #7ed6bc;
  }
  .fill.is-muted {
    opacity: 0.35;
  }
  .value {
    position: absolute;
    right: 16px;
    top: 0;
    bottom: 0;
    display: flex;
    align-items: center;
    font-family: var(--font-mono);
    font-size: 16px;
    font-weight: 600;
    pointer-events: none;
    color: #e9eef2;
  }
  .value.is-dark {
    color: var(--remote-vol-ink-on-fill);
  }
  .rule {
    flex-shrink: 0;
    height: 1px;
    background: rgba(233, 238, 242, 0.1);
  }
  .rows {
    min-height: 0;
    overflow-y: auto;
    touch-action: pan-y;
    scrollbar-width: none;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .rows::-webkit-scrollbar {
    display: none;
  }
  .member {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 40px;
  }
  .who {
    width: 104px;
    flex-shrink: 0;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .who__name {
    font-size: 15px;
    font-weight: 700;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .who__tag {
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    white-space: nowrap;
    color: rgba(233, 238, 242, 0.6);
  }
  .who__tag:empty {
    display: none;
  }
  .who__tag.is-lead {
    color: var(--group-ink);
  }
  .mute {
    position: absolute;
    left: 4px;
    top: 2px;
    width: 32px;
    height: 32px;
    border-radius: 10px;
    border: 0;
    padding: 0;
    background: none;
    display: grid;
    place-items: center;
    cursor: pointer;
    color: #e9eef2;
  }
  .mute.is-dark {
    color: var(--remote-vol-ink-on-fill);
  }
  .mute svg {
    width: 24px;
    height: 24px;
    fill: currentColor;
  }
  .fixed {
    position: relative;
    flex: 1;
    min-width: 0;
    height: 36px;
    border-radius: 12px;
    background: rgba(233, 238, 242, 0.05);
    border: 1px solid rgba(233, 238, 242, 0.12);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 0 12px;
  }
  .fixed.has-mute {
    padding-left: 44px;
  }
  .mute--fixed {
    left: 3px;
    top: 1px;
  }
  .lock {
    position: relative;
    width: 14px;
    height: 16px;
    flex-shrink: 0;
    display: block;
  }
  .lock__shackle {
    position: absolute;
    left: 2px;
    top: 0;
    width: 10px;
    height: 8px;
    border: 2px solid rgba(233, 238, 242, 0.7);
    border-bottom: none;
    border-radius: 5px 5px 0 0;
    box-sizing: border-box;
    display: block;
  }
  .lock__body {
    position: absolute;
    left: 0;
    bottom: 0;
    width: 14px;
    height: 9px;
    border-radius: 2.5px;
    background: rgba(233, 238, 242, 0.7);
    display: block;
  }
  .fixed__text {
    flex: 1;
    min-width: 0;
    font-size: 14px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .off {
    flex: 1;
    min-width: 0;
    height: 36px;
    border-radius: 12px;
    border: 1px dashed rgba(233, 238, 242, 0.16);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    padding: 0 14px;
    font-size: 14px;
    color: rgba(233, 238, 242, 0.6);
  }
  .note {
    flex-shrink: 0;
    font-size: 14px;
    line-height: 1.4;
    color: rgba(233, 238, 242, 0.6);
    text-wrap: pretty;
  }
</style>
