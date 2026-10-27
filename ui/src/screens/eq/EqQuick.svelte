<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The equaliser's quick change (ADR-0162; design/source/20, EQ Quick): the
  setting in use, the others to change it to, on and off, and Edit, which
  opens the editor. In the panel's volume drawer (`drawer`), the bar's tray's
  second band (`bartray`) and the phone's pull-up tray (`phonetray`).

  The settings are chips in one sideways row - presets, then the owner's after
  a rule - opening scrolled to the one in use; Custom comes first. Off, or
  while DSD stands the equaliser aside, the row is dimmed.
-->
<script>
  import { equaliser, quickNote, setEqualiser, stateLine } from '../../lib/equaliser.svelte.js';

  let { host = 'drawer', onedit } = $props();

  const eq = $derived($equaliser);
  const on = $derived(!!eq?.on);
  const lit = $derived(on && !eq?.dsd);
  const line = $derived(eq ? stateLine(eq) : null);
  const told = $derived(eq ? quickNote(eq) : null);
  let busy = $state(false);
  let error = $state(null);

  const chips = $derived.by(() => {
    if (!eq) return [];
    const out = [];
    if (eq.sel === 'custom') out.push({ key: 'custom', name: 'Custom', custom: true });
    for (const p of eq.presets) out.push(p);
    eq.own.forEach((o, i) => out.push({ ...o, rule: i === 0 }));
    return out;
  });

  async function choose(key) {
    if (!lit || key === 'custom' || key === eq.sel) return;
    error = null;
    try {
      await setEqualiser({ sel: key });
    } catch (e) {
      error = e.message;
    }
  }
  async function toggle() {
    if (!eq || busy) return;
    busy = true;
    error = null;
    try {
      await setEqualiser({ on: !eq.on });
    } catch (e) {
      error = e.message;
    } finally {
      busy = false;
    }
  }

  function toSelected(node) {
    requestAnimationFrame(() => {
      const t = node.querySelector('[data-sel="1"]');
      if (!t) return;
      const r = node.getBoundingClientRect();
      const scale = r.width / (node.offsetWidth || r.width);
      const d = (t.getBoundingClientRect().left - r.left) / scale;
      if (d + t.offsetWidth > node.clientWidth - 40) node.scrollLeft += d - 120;
    });
  }
</script>

{#snippet chipRow()}
  <div class="chips" class:is-dim={!lit} use:toSelected>
    {#each chips as c (c.key)}
      {@const sel = eq.sel === c.key}
      {#if c.rule}<span class="rule"></span>{/if}
      <button type="button" class="chip" class:is-sel={sel} data-sel={sel ? '1' : '0'} aria-pressed={sel}
              onclick={() => choose(c.key)}>
        {#if c.custom}<span class="chip__dot"></span>{/if}{c.name}
      </button>
    {/each}
  </div>
{/snippet}

{#snippet noteLine()}
  {#if error}
    <div class="note is-amber">{error}</div>
  {:else if told.text}
    <div class="note" class:is-amber={told.amber}>{told.text}</div>
  {/if}
{/snippet}

{#snippet edit()}
  <button type="button" class="edit" onclick={() => onedit?.()}>Edit<span class="edit__chev"></span></button>
{/snippet}

{#snippet toggleSwitch()}
  <span class="switch" class:is-on={on}><span></span></span>
{/snippet}

{#if eq}
  {#if host === 'drawer'}
    <div class="drawer">
      <div class="divider"></div>
      <div class="top">
        <div class="top__text">
          <div class="title">Equaliser</div>
          <div class="state" class:is-amber={line.amber}>{line.text}</div>
        </div>
        {@render edit()}
        <button type="button" class="power power--alone" aria-label="Equaliser" aria-pressed={on} onclick={toggle}>
          {@render toggleSwitch()}
        </button>
      </div>
      {@render chipRow()}
      {@render noteLine()}
    </div>
  {:else if host === 'bartray'}
    <div class="bartray">
      <button type="button" class="power power--bar" aria-label="Equaliser" aria-pressed={on} onclick={toggle}>
        <span class="power__state" class:is-on={on}>{on ? 'On' : 'Off'}</span>
        {@render toggleSwitch()}
      </button>
      <div class="bartray__mid">
        {@render chipRow()}
        {@render noteLine()}
      </div>
      {@render edit()}
    </div>
  {:else}
    <div class="phonetray">
      <div class="phead">
        <span class="phead__label">Equaliser</span>
        <span class="phead__rule"></span>
        <button type="button" class="pill" onclick={() => onedit?.()}>Edit<span class="pill__chev"></span></button>
        <button type="button" class="pill pill--power" class:is-on={on} aria-pressed={on} onclick={toggle}>
          {on ? 'On' : 'Off'}
        </button>
      </div>
      {@render chipRow()}
      {@render noteLine()}
    </div>
  {/if}
{/if}

<style>
  .divider {
    height: 1px;
    background: rgba(233, 238, 242, 0.1);
    margin: 26px 0 22px;
  }
  .top {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .top__text {
    flex: 1;
    min-width: 0;
  }
  .title {
    font-size: 19px;
    font-weight: 600;
  }
  .state {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.06em;
    margin-top: 5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: rgba(233, 238, 242, 0.72);
  }
  .is-amber {
    color: #e0a758 !important;
  }
  .edit {
    height: 58px;
    padding: 0 18px 0 22px;
    border-radius: 15px;
    box-sizing: border-box;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.14);
    display: flex;
    align-items: center;
    gap: 12px;
    font: inherit;
    font-size: 17px;
    font-weight: 600;
    color: var(--ink);
    flex-shrink: 0;
  }
  .edit__chev {
    width: 9px;
    height: 9px;
    border-right: 2.5px solid rgba(233, 238, 242, 0.6);
    border-top: 2.5px solid rgba(233, 238, 242, 0.6);
    transform: rotate(45deg);
    margin-left: -2px;
  }
  .power {
    height: 58px;
    padding: 0 12px;
    border-radius: 15px;
    box-sizing: border-box;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(233, 238, 242, 0.1);
    display: flex;
    align-items: center;
    gap: 14px;
    flex-shrink: 0;
    color: inherit;
  }
  /* The drawer's switch alone, without the box round it, as the phone's EQ
     sheet (George, 2026-10-27); the touch is still 58 px tall. */
  .power--alone {
    background: none;
    border: 0;
    margin-right: -12px;
  }
  .edit:active,
  .power:active,
  .chip:active,
  .pill:active {
    transform: scale(0.95);
  }
  .switch {
    width: 60px;
    height: 34px;
    border-radius: 17px;
    position: relative;
    box-sizing: border-box;
    display: block;
    background: rgba(233, 238, 242, 0.08);
    border: 1px solid rgba(233, 238, 242, 0.16);
  }
  .switch span {
    position: absolute;
    top: 3px;
    left: 3px;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    display: block;
    background: rgba(233, 238, 242, 0.6);
    transition: left 140ms ease;
  }
  .switch.is-on {
    background: rgba(126, 214, 188, 0.32);
    border-color: rgba(126, 214, 188, 0.5);
  }
  .switch.is-on span {
    left: 29px;
    background: #7ed6bc;
  }

  .chips {
    display: flex;
    gap: 10px;
    margin-top: 18px;
    overflow-x: auto;
    scrollbar-width: none;
    -webkit-mask-image: linear-gradient(90deg, #000 0, #000 calc(100% - 64px), transparent 100%);
    mask-image: linear-gradient(90deg, #000 0, #000 calc(100% - 64px), transparent 100%);
    touch-action: pan-x;
  }
  .chips::-webkit-scrollbar {
    display: none;
  }
  .chips.is-dim {
    opacity: 0.4;
    pointer-events: none;
  }
  .rule {
    width: 1px;
    align-self: stretch;
    margin: 10px 4px;
    background: rgba(233, 238, 242, 0.16);
    flex-shrink: 0;
  }
  .chip {
    flex-shrink: 0;
    height: 56px;
    padding: 0 22px;
    border-radius: 14px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 10px;
    font: inherit;
    font-size: 17px;
    font-weight: 600;
    white-space: nowrap;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.14);
    color: var(--ink);
  }
  .chip.is-sel {
    background: rgba(126, 214, 188, 0.16);
    border-color: rgba(126, 214, 188, 0.55);
    color: #7ed6bc;
  }
  .chip__dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #e0a758;
    flex-shrink: 0;
  }
  .note {
    font-size: 15px;
    line-height: 1.4;
    margin-top: 16px;
    text-wrap: pretty;
    color: rgba(233, 238, 242, 0.6);
  }

  /* -- the bar's tray: its second band -- */
  .bartray {
    display: flex;
    align-items: center;
    gap: 16px;
    height: 100%;
  }
  .power--bar {
    height: 60px;
    padding: 0 12px 0 18px;
  }
  .power__state {
    font-family: var(--font-mono);
    font-size: 15px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    width: 40px;
    text-align: left;
    color: rgba(233, 238, 242, 0.72);
  }
  .power__state.is-on {
    color: #7ed6bc;
  }
  .bartray__mid {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .bartray .chips {
    margin-top: 0;
    -webkit-mask-image: linear-gradient(90deg, #000 0, #000 calc(100% - 88px), transparent 100%);
    mask-image: linear-gradient(90deg, #000 0, #000 calc(100% - 88px), transparent 100%);
  }
  .bartray .chip {
    height: 60px;
    padding: 0 24px;
    border-radius: 15px;
    font-size: 18px;
  }
  .bartray .rule {
    margin: 12px 4px;
  }
  .bartray .note {
    margin-top: 0;
    line-height: 1.3;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .bartray .edit {
    height: 60px;
    padding: 0 20px 0 24px;
    font-size: 18px;
  }

  /* -- the phone's tray -- */
  .phonetray {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .phead {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 2px;
  }
  .phead__label {
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: rgba(233, 238, 242, 0.6);
  }
  .phead__rule {
    flex: 1;
    height: 1px;
    background: rgba(233, 238, 242, 0.1);
  }
  .pill {
    height: 32px;
    padding: 0 10px 0 12px;
    border-radius: var(--r-pill);
    border: 1px solid rgba(233, 238, 242, 0.1);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 6px;
    background: transparent;
    font: inherit;
    font-size: 13px;
    font-weight: 600;
    color: var(--ink);
  }
  .pill__chev {
    width: 7px;
    height: 7px;
    border-right: 2px solid rgba(233, 238, 242, 0.6);
    border-top: 2px solid rgba(233, 238, 242, 0.6);
    transform: rotate(45deg);
  }
  .pill--power {
    padding: 0 12px;
  }
  .pill--power.is-on {
    background: rgba(126, 214, 188, 0.16);
    border-color: #7ed6bc;
    color: #7ed6bc;
  }
  .phonetray .chips {
    margin: 0 -16px;
    padding: 0 16px;
    gap: 6px;
    -webkit-mask-image: linear-gradient(90deg, transparent 0, #000 16px, #000 calc(100% - 40px), transparent 100%);
    mask-image: linear-gradient(90deg, transparent 0, #000 16px, #000 calc(100% - 40px), transparent 100%);
  }
  .phonetray .chip {
    height: 44px;
    padding: 0 16px;
    border-radius: 12px;
    gap: 8px;
    font-size: 15px;
  }
  .phonetray .rule {
    margin: 10px 3px;
  }
  .phonetray .note {
    margin-top: 0;
    font-size: 14px;
  }
</style>
