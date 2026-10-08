<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The Cable row's sheet** (ADR-0123): the cable at a glance, and its
  address - Automatic (DHCP) or Manual. `port="wifi"` is the same form under
  the connected Wi-Fi network's details (decision 2), whose own lines already
  say what `facts` would. A manual address is checked as typed
  by the core, and kept only once confirmed from it within 60 s: CableKeep
  shows the question on every page while it waits.
-->
<script>
  import { onDestroy, onMount } from 'svelte';

  let { port = 'cable', facts = true } = $props();
  const url = port === 'wifi' ? '/network/wifi/address' : '/network/cable';

  let cable = $state(null);
  let method = $state('auto');
  let address = $state('');
  let gateway = $state('');
  let dns = $state('');
  let saving = $state(false);
  let error = $state(null);
  let told = $state(null);
  let touched = false;

  async function read() {
    try {
      const r = await fetch(url);
      if (!r.ok) throw new Error();
      cable = await r.json();
      if (!touched) {
        method = cable.method;
        address = cable.address ?? '';
        gateway = cable.gateway ?? '';
        dns = (cable.dns ?? []).join(' ');
      }
    } catch {
      /* changing address: the next read says */
    }
  }

  let timer;
  onMount(() => {
    read();
    timer = setInterval(read, 4000);
  });
  onDestroy(() => clearInterval(timer));

  const edit = () => (touched = true);
  const changed = $derived(
    !!cable &&
      (method !== cable.method ||
        (method === 'manual' &&
          (address.trim() !== (cable.address ?? '') || gateway.trim() !== (cable.gateway ?? '') ||
            dns.trim().split(/[\s,]+/).filter(Boolean).join(' ') !== (cable.dns ?? []).join(' '))))
  );
  const ready = $derived(method === 'auto' || (address.includes('/') && gateway.trim() && dns.trim()));

  async function save() {
    saving = true;
    error = null;
    try {
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(method === 'manual'
          ? { method, address: address.trim(), gateway: gateway.trim(), dns: dns.trim().split(/[\s,]+/).filter(Boolean) }
          : { method }),
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(body.error ?? 'The address was not saved. Try again.');
      told = body;
      touched = false;
    } catch (e) {
      error = e.message;
    } finally {
      saving = false;
    }
  }
</script>

<div class="cable">
  {#if !cable}
    <p class="cable__text">Reading the cable…</p>
  {:else}
    {#if facts}
    <dl class="cable__facts">
      <div><dt>Link</dt><dd>{cable.link ? `Connected${cable.speed ? ` · ${cable.speed} Mb/s` : ''}` : 'No link'}</dd></div>
      <div><dt>Address</dt><dd>{cable.address ?? '-'}</dd></div>
      <div><dt>Gateway</dt><dd>{cable.gateway ?? '-'}</dd></div>
      <div><dt>DNS</dt><dd>{cable.dns?.length ? cable.dns.join(' · ') : '-'}</dd></div>
    </dl>
    {/if}

    {#if told || cable.pending}
      <p class="cable__text cable__text--warn">
        Waiting to be kept: open <span class="addr">http://{(told ?? cable.pending).address ?? 'the new address'}:8090</span>
        and keep it there within 60 seconds, or the old address comes back.
      </p>
    {:else}
      <div class="seg" role="radiogroup" aria-label="Address">
        <button type="button" class:on={method === 'auto'} onclick={() => { method = 'auto'; edit(); }}>Automatic</button>
        <button type="button" class:on={method === 'manual'} onclick={() => { method = 'manual'; edit(); }}>Manual</button>
      </div>
      {#if method === 'manual'}
        <label class="field"><span>Address, with its prefix</span>
          <input type="text" inputmode="decimal" bind:value={address} oninput={edit} placeholder="192.168.1.20/24" autocomplete="off" spellcheck="false" />
        </label>
        <label class="field"><span>Gateway</span>
          <input type="text" inputmode="decimal" bind:value={gateway} oninput={edit} placeholder="192.168.1.1" autocomplete="off" spellcheck="false" />
        </label>
        <label class="field"><span>DNS, one or two</span>
          <input type="text" bind:value={dns} oninput={edit} placeholder="192.168.1.1 9.9.9.9" autocomplete="off" spellcheck="false" />
        </label>
        <p class="cable__text cable__text--quiet">After Save, the player is at the new address. Keep it from there within 60 seconds, or the old one comes back.</p>
      {/if}
      {#if error}<p class="cable__text cable__text--warn">{error}</p>{/if}
      <button type="button" class="cable__save" disabled={!changed || !ready || saving} onclick={save}>
        {saving ? 'Saving…' : 'Save'}
      </button>
    {/if}
  {/if}
</div>

<style>
  .cable {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .cable__facts {
    display: grid;
    gap: 6px;
    margin: 0;
  }
  .cable__facts div {
    display: flex;
    gap: 12px;
    font-size: 15px;
  }
  .cable__facts dt {
    flex: 0 0 82px;
    color: var(--ink-dim, #9fb0bd);
  }
  .cable__facts dd {
    margin: 0;
    font-family: var(--font-mono);
    overflow-wrap: anywhere;
  }
  .cable__text {
    margin: 0;
    font-size: 15px;
    line-height: 1.45;
  }
  .cable__text--warn {
    color: var(--accent-warn);
  }
  .cable__text--quiet {
    color: var(--ink-dim, #9fb0bd);
  }
  .addr {
    font-family: var(--font-mono);
    overflow-wrap: anywhere;
  }
  .seg {
    display: flex;
    gap: 6px;
    padding: 4px;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.06);
  }
  .seg button {
    flex: 1;
    height: 44px;
    border-radius: 10px;
    border: none;
    font-size: 16px;
    font-weight: 600;
    color: var(--ink);
    background: transparent;
  }
  .seg button.on {
    background: rgba(126, 214, 188, 0.2);
    color: #7ed6bc;
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 14px;
    color: var(--ink-dim, #9fb0bd);
  }
  .field input {
    height: 48px;
    padding: 0 14px;
    border-radius: 12px;
    border: 1px solid rgba(233, 238, 242, 0.18);
    background: rgba(255, 255, 255, 0.05);
    color: var(--ink);
    font-family: var(--font-mono);
    font-size: 16px;
  }
  .cable__save {
    height: 52px;
    border-radius: 14px;
    border: 1px solid rgba(126, 214, 188, 0.45);
    background: rgba(126, 214, 188, 0.14);
    color: #7ed6bc;
    font-size: 17px;
    font-weight: 600;
  }
  .cable__save:disabled {
    opacity: 0.45;
  }
</style>
