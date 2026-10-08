<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **A new cable address, waiting to be kept** (ADR-0123): over every page,
  phone and panel, while a change waits. Keep counts from the new address -
  which shows it works - or from the panel; tapped at the old address, it says
  where to open the player instead. Not kept within the time, the old address
  comes back by itself.

  Read again whenever the settings revision moves: the core moves it when a
  change starts, is kept, or runs out.
-->
<script>
  import { onDestroy } from 'svelte';
  import { playback } from '../lib/state.js';

  let pending = $state(null);
  let now = $state(Date.now());
  let answer = $state(null);
  let busy = $state(false);

  async function read() {
    try {
      const r = await fetch('/network/cable');
      if (!r.ok) return;
      pending = (await r.json()).pending ?? null;
      if (!pending) answer = null;
    } catch {
      /* the player is changing address: the next revision says */
    }
  }

  let seen;
  const unsubscribe = playback.subscribe(($s) => {
    const revision = $s?.settings_revision;
    if (revision === undefined || revision === seen) return;
    seen = revision;
    read();
  });
  const tick = setInterval(() => (now = Date.now()), 1000);
  onDestroy(() => {
    unsubscribe();
    clearInterval(tick);
  });

  const left = $derived(pending ? Math.max(0, Math.ceil(pending.until - now / 1000)) : 0);
  const here = $derived(typeof location !== 'undefined' ? location.hostname : '');
  const elsewhere = $derived(pending?.address && here !== pending.address && here !== 'localhost' && here !== '127.0.0.1');

  async function keep() {
    busy = true;
    answer = null;
    try {
      const r = await fetch('/network/keep', { method: 'POST' });
      const body = await r.json().catch(() => ({}));
      if (r.ok) pending = null;
      else answer = body.error ?? 'It could not be kept from here.';
    } catch {
      answer = 'The player did not answer at this address.';
    } finally {
      busy = false;
    }
  }
</script>

{#if pending}
  <div class="keep" role="alertdialog" aria-label="Keep the new cable address?">
    <div class="keep__text">
      <b>Keep the new cable address?</b>
      <span>
        {#if elsewhere}
          Open <span class="addr">http://{pending.address}:8090</span> and keep it there, within {left} s.
        {:else}
          {pending.address ? `The player is at ${pending.address} on the cable.` : 'The player has a new cable address.'}
          Not kept within {left} s, the old address comes back.
        {/if}
      </span>
      {#if answer}<span class="keep__warn">{answer}</span>{/if}
    </div>
    <button type="button" class="keep__btn" disabled={busy} onclick={keep}>Keep</button>
  </div>
{/if}

<style>
  .keep {
    position: fixed;
    left: 50%;
    top: 16px;
    transform: translateX(-50%);
    z-index: 95;
    width: min(620px, calc(100% - 32px));
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px 18px;
    border-radius: 18px;
    background: var(--bg-panel);
    border: 1px solid rgba(224, 167, 88, 0.55);
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
    color: var(--ink);
  }
  .keep__text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 15px;
    line-height: 1.4;
  }
  .keep__text b {
    font-size: 17px;
  }
  .addr {
    font-family: var(--font-mono);
    overflow-wrap: anywhere;
  }
  .keep__warn {
    color: var(--accent-warn);
  }
  .keep__btn {
    flex-shrink: 0;
    min-width: 96px;
    height: 48px;
    border-radius: 14px;
    font-size: 16px;
    font-weight: 700;
    color: var(--ink-on-accent);
    background: var(--accent-warn);
    border: none;
  }
  .keep__btn:disabled {
    opacity: 0.6;
  }
</style>
