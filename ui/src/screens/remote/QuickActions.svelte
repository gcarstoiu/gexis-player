<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0164 D4: the quick actions (design/source/21): Standby and the idle
  screen at the left, Playing and Room at the right. The one the screen
  shows, and Standby while it is on, are lit; in standby the views drop to
  0.45, and any of them wakes the screen. Offered as the mini player offered
  them (C7): the idle screen only while it is switched on, Room only with a
  dashboard set, Playing only with something playing.
-->
<script>
  import { active, panel } from '../../lib/state.js';
  import { settingValues } from '../../lib/settings.js';
  import { showing, standby, view } from './commands.js';
  import { STROKED } from './icons.js';

  let { onsay = () => {}, ontouch = () => {} } = $props();

  const hasDashboard = $derived(!!($settingValues.dashboard_url ?? '').trim() && $settingValues.dashboard_button !== false);
  const idleOn = $derived($settingValues.idle_enabled === true);
  const off = $derived(!!$panel.standby);
  const lit = (which) => !off && $showing === which;

  function go(which) {
    ontouch();
    view(which, (text) => onsay(text));
  }
</script>

<div class="actions">
  <button class="act" class:is-on={off} type="button" aria-label={off ? 'Screen on' : 'Standby'} aria-pressed={off}
          onclick={() => { ontouch(); standby(!off); }}>
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d={STROKED.standby} /></svg>
  </button>
  {#if idleOn}
    <button class="act" class:is-on={lit('idle')} class:is-dim={off} type="button" aria-label="Idle screen"
            aria-pressed={lit('idle')} onclick={() => go('idle')}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d={STROKED.idle} /></svg>
    </button>
  {/if}
  <span class="gap"></span>
  <button class="act" class:is-on={lit('playing')} class:is-dim={off} type="button" aria-label="Playing"
          aria-pressed={lit('playing')} disabled={!$active} onclick={() => go('playing')}>
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d={STROKED.playing} /></svg>
  </button>
  {#if hasDashboard}
    <button class="act" class:is-on={lit('room')} class:is-dim={off} type="button" aria-label="Room"
            aria-pressed={lit('room')} onclick={() => go('room')}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d={STROKED.room} /></svg>
    </button>
  {/if}
</div>

<style>
  .actions {
    flex-shrink: 0;
    display: flex;
    gap: 8px;
    margin-top: 14px;
  }
  .gap {
    flex: 1;
  }
  .act {
    width: var(--remote-button);
    height: var(--remote-button);
    border-radius: var(--remote-button-radius);
    flex-shrink: 0;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    cursor: pointer;
    background: var(--remote-button-ground);
    border: 1px solid var(--remote-button-line);
    color: #e9eef2;
  }
  .act:active {
    transform: scale(0.97);
  }
  .act.is-on {
    background: var(--remote-select);
    border-color: var(--remote-button-on-line);
    color: #7ed6bc;
  }
  .act.is-dim {
    opacity: 0.45;
  }
  .act:disabled {
    opacity: 0.38;
    cursor: default;
  }
  svg {
    width: 22px;
    height: 22px;
    flex-shrink: 0;
    fill: none;
    stroke: currentColor;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
</style>
