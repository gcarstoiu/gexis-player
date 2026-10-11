<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **Switching between players on the phone** (ADR-0136). George, 2026-10-11:
  *"Simple switch with status and renderer connected."*

  A button at the right end of the *Settings* line, when another player is on
  the network (George, 2026-10-11: larger, in line with the title). It opens
  the players, this one first and marked, each
  with what it is doing; choosing another opens its page in the same tab. The
  list comes from this player (`/players`): the browser does not reach across
  addresses itself.
-->
<script>
  import { onMount } from 'svelte';

  let me = $state(null);
  let others = $state([]);
  let open = $state(false);

  function said(p) {
    if (p.transport === 'playing') return p.renderer ? `Playing · ${p.renderer}` : 'Playing';
    if (p.transport === 'paused') return p.renderer ? `Paused · ${p.renderer}` : 'Paused';
    return p.renderer ? `Stopped · ${p.renderer}` : 'Idle';
  }

  async function load() {
    try {
      const response = await fetch('/players');
      if (!response.ok) return;
      const body = await response.json();
      me = body.self;
      others = body.others ?? [];
    } catch {
      // No list is no switcher.
    }
  }

  function show() {
    open = true;
    load();
  }

  onMount(load);
</script>

{#if others.length}
  <button class="switch" type="button" aria-haspopup="dialog" aria-label="Other players" onclick={show}>
    <span class="switch__face">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4v14M7 18l-3-3M7 18l3-3M17 20V6M17 6l-3 3M17 6l3 3" /></svg>
    </span>
  </button>
{/if}

{#if open}
  <div class="scrim" role="presentation" onclick={() => (open = false)}></div>
  <div class="sheet" role="dialog" aria-label="Players">
    <div class="sheet__title">Players</div>
    <div class="list">
      {#if me}
        <div class="player is-current">
          <span class="player__text">
            <span class="player__name">{me.name}</span>
            <span class="player__status">{said(me)}</span>
          </span>
          <span class="player__here">This player</span>
        </div>
      {/if}
      {#each others as p (p.url)}
        <a class="player" href={p.url}>
          <span class="player__text">
            <span class="player__name">{p.name}</span>
            <span class="player__status">{said(p)}</span>
          </span>
          <span class="chev" aria-hidden="true"></span>
        </a>
      {/each}
    </div>
    <button class="close" type="button" onclick={() => (open = false)}>Close</button>
  </div>
{/if}

<style>
  /* A square to balance the title (George, 2026-10-11), drawn at 34 px and
     tappable at the touch floor, 44 px. */
  .switch {
    flex-shrink: 0;
    width: var(--touch-min, 44px);
    height: var(--touch-min, 44px);
    margin-right: -5px;
    padding: 0;
    display: grid;
    place-items: center;
    border: 0;
    background: none;
    cursor: pointer;
  }
  .switch__face {
    width: 34px;
    height: 34px;
    display: grid;
    place-items: center;
    border-radius: var(--r-sm, 8px);
    border: 1px solid var(--ink-line);
    background: var(--ink-fill);
  }
  .switch svg {
    width: 20px;
    height: 20px;
    fill: none;
    stroke: var(--accent-lms);
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .scrim {
    position: fixed;
    inset: 0;
    z-index: 60;
    background: var(--bg-scrim);
  }
  .sheet {
    position: fixed;
    left: 16px;
    right: 16px;
    top: 50%;
    transform: translateY(-50%);
    z-index: 61;
    max-height: calc(100% - 64px);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 24px;
    border-radius: var(--r-xl);
    background: var(--bg-panel);
    border: 1px solid var(--ink-line);
    box-shadow: 0 30px 70px rgba(0, 0, 0, 0.5);
  }
  .sheet__title {
    font-size: 22px;
    font-weight: 700;
    color: var(--ink);
  }
  .list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .player {
    display: flex;
    align-items: center;
    gap: 14px;
    min-height: 64px;
    padding: 12px 16px;
    border-radius: var(--r-lg);
    border: 1px solid var(--ink-line);
    background: var(--ink-fill);
    color: var(--ink);
    text-decoration: none;
  }
  .player.is-current {
    border-color: var(--accent-lms);
    background: rgba(126, 214, 188, 0.1);
  }
  .player__text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .player__name {
    font-size: 17px;
    font-weight: 600;
  }
  .player__status {
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--ink-quiet);
  }
  .player__here {
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: var(--track-label);
    text-transform: uppercase;
    color: var(--accent-lms);
  }
  .chev {
    width: 10px;
    height: 10px;
    border-right: 2px solid var(--ink-quiet);
    border-top: 2px solid var(--ink-quiet);
    transform: rotate(45deg);
    flex-shrink: 0;
  }
  .close {
    min-height: 52px;
    border-radius: var(--r-lg);
    border: 1px solid var(--ink-line);
    background: var(--ink-fill);
    color: var(--ink);
    font: inherit;
    font-size: 17px;
    font-weight: 600;
  }
</style>
