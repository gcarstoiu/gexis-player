<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  One member in the bar tray's group band (ADR-0166; design/source/22,
  `Multiroom Panel.dc.html`, bar, `gvRows`): 330 x 116, its name and tag,
  Remove, and its own level - mute, slider (track 8, knob 32) and value - or
  the locked row with Fixed volume, or *Not reachable*.
-->
<script>
  import VolumeIcon from '../../lib/VolumeIcon.svelte';
  import { LevelSender, removePlayer, setMemberMute, setMemberVolume } from '../../lib/group.svelte.js';
  import { track } from './panelSlider.js';

  //: `onerror(text)`: a refusal, for the tray's toast.
  let { m, g, onerror = () => {} } = $props();

  const lead = $derived(m.leads && !g.silent);
  const tag = $derived(!m.reachable ? 'Off' : lead ? 'Leads' : m.me ? 'This one' : m.fixed ? 'Fixed' : '');
  const canRemove = $derived(m.reachable && !m.me && !m.leads);

  //: The level while a finger moves it, drawn before the member's answer.
  let local = $state(null);
  let held = false;
  const sender = new LevelSender((percent) => setMemberVolume(m.id, percent),
    (error) => onerror(`Volume not changed: ${error.message}`));
  const level = $derived(local ?? m.volume ?? 0);
  const muted = $derived(m.muted);

  //: A tap, or a move along the slider, sets the level - not a swipe up
  //: or down that began on it (panelSlider.js).
  const drag = track((percent, first) => {
    held = true;
    // Moving a muted member's level unmutes it (the design's `setOne`).
    if (first && muted) setMemberMute(m.id, false).catch(() => {});
    local = percent;
    sender.send(local);
  }, () => up());
  let upTimer;
  function up() {
    held = false;
    // The member's own report takes over once it arrives.
    clearTimeout(upTimer);
    upTimer = setTimeout(() => { if (!held) local = null; }, 1200);
  }
  function step(delta) {
    local = Math.max(0, Math.min(100, level + delta));
    sender.send(local);
    up();
  }
  async function toggleMute() {
    try {
      await setMemberMute(m.id, !muted);
    } catch (error) {
      onerror(`Mute not changed: ${error.message}`);
    }
  }
  async function remove() {
    try {
      await removePlayer(m.id);
    } catch (error) {
      onerror(error.message);
    }
  }
  const muteOffered = $derived(!m.fixed || m.fixed_mute !== null);
</script>

<div class="card">
  <div class="top">
    <span class="name">{m.name}</span>
    {#if tag}<span class="tag" class:is-lead={tag === 'Leads'}>{tag}</span>{/if}
    {#if canRemove}
      <button class="remove" type="button" aria-label={`Remove ${m.name}`} onclick={remove}>
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
      </button>
    {/if}
  </div>
  {#if !m.reachable}
    <span class="off">Not reachable</span>
  {:else}
    <div class="levelrow">
      <button class="mute" type="button" aria-label={muted ? `Unmute ${m.name}` : `Mute ${m.name}`}
        disabled={!muteOffered} onclick={toggleMute}>
        <!-- The design's glyph: two arcs lit, the third faint. -->
        <span class="glyph"><VolumeIcon percent={50} muted={false} /></span>
        {#if muted}<span class="slash"></span>{/if}
      </button>
      {#if m.fixed}
        <span class="fixed"><span class="lock"><i></i><b></b></span><span class="fixed__text">Fixed output</span></span>
      {:else}
        <div class="slider" role="slider" tabindex="-1" aria-label={`${m.name} volume`}
          aria-valuemin="0" aria-valuemax="100" aria-valuenow={level} data-step="2"
          ondpadstep={(event) => step(event.detail.step * 2)}
          onpointerdown={drag.down} onpointermove={drag.move} onpointerup={drag.up} onpointercancel={drag.up}>
          <div class="rail" data-dpad-box>
            <div class="fill" class:is-muted={muted} style:width={`${level}%`}></div>
            <div class="knob" style:left={`${level}%`} data-dpad-knob></div>
          </div>
        </div>
        <span class="value">{muted ? 'Off' : level}</span>
      {/if}
    </div>
  {/if}
</div>

<style>
  .card {
    flex-shrink: 0;
    width: 330px;
    height: 116px;
    border-radius: var(--r-18);
    background: var(--c-white-04);
    border: 1px solid var(--ink-line);
    box-sizing: border-box;
    padding: 10px 12px 10px 18px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    text-transform: none;
    letter-spacing: normal;
    color: var(--ink);
  }
  .top {
    display: flex;
    align-items: center;
    gap: 10px;
    min-height: 40px;
  }
  .name {
    flex: 1;
    min-width: 0;
    font-size: 18px;
    font-weight: 700;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .tag {
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    white-space: nowrap;
    flex-shrink: 0;
    color: var(--ink-quiet);
  }
  .tag.is-lead { color: var(--group-ink); }
  .remove {
    width: 44px;
    height: 44px;
    border: 0;
    padding: 0;
    border-radius: 50%;
    flex-shrink: 0;
    display: grid;
    place-items: center;
    background: var(--ink-fill);
    color: var(--c-ink-85);
  }
  .remove:active { transform: scale(0.95); }
  .levelrow {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .mute {
    position: relative;
    width: 48px;
    height: 48px;
    flex-shrink: 0;
    display: grid;
    place-items: center;
    margin-left: -8px;
    border: 0;
    padding: 0;
    background: none;
  }
  .mute:disabled { opacity: 0.4; }
  .glyph { transform: scale(0.8); display: block; }
  .slash {
    position: absolute;
    left: 50%;
    top: 50%;
    width: 30px;
    height: 3px;
    margin: -1.5px 0 0 -15px;
    border-radius: 2px;
    transform: rotate(-38deg);
    background: var(--accent-warn);
  }
  .slider {
    flex: 1;
    min-width: 0;
    height: 48px;
    display: flex;
    align-items: center;
    touch-action: none;
  }
  .rail {
    width: 100%;
    height: 8px;
    border-radius: var(--r-pill);
    background: var(--c-ink-15);
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
  .fill.is-muted { background: var(--c-lms-35); }
  .knob {
    position: absolute;
    top: 50%;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    transform: translate(-50%, -50%);
    background: var(--ink);
    box-shadow: 0 3px 10px var(--c-black-45);
  }
  .value {
    font-family: var(--font-mono);
    font-size: 20px;
    font-weight: 700;
    width: 46px;
    text-align: right;
    flex-shrink: 0;
  }
  .fixed {
    flex: 1;
    min-width: 0;
    height: 48px;
    border-radius: var(--r-14);
    background: var(--c-ink-05);
    border: 1px solid var(--c-ink-12);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 14px;
  }
  /* The design's padlock: the shackle drawn, the body filled. */
  .lock { position: relative; width: 22px; height: 26px; flex-shrink: 0; display: block; }
  .lock i {
    position: absolute;
    left: 4px;
    top: 0;
    width: 14px;
    height: 12px;
    border: 2.5px solid var(--c-ink-70);
    border-bottom: none;
    border-radius: var(--r-7) var(--r-7) 0 0;
    box-sizing: border-box;
    display: block;
  }
  .lock b {
    position: absolute;
    left: 0;
    bottom: 0;
    width: 22px;
    height: 15px;
    border-radius: var(--r-4);
    background: var(--c-ink-70);
    display: block;
  }
  .fixed__text {
    flex: 1;
    min-width: 0;
    font-size: 17px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .off {
    height: 48px;
    border-radius: var(--r-14);
    border: 1px dashed var(--ink-fill-press);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    padding: 0 16px;
    font-size: 17px;
    color: var(--ink-quiet);
  }
</style>
