<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0164: the EQ sheet (design/source/21, *Sheets*), from the volume row's
  EQ button. *Equaliser*, the setting in use, the switch; the settings as
  chips that scroll sideways - Phase 20's presets, a rule, the owner's, with
  Custom first while it is the one in use - applied at a tap; the note; and
  *Edit bands in Settings*. The note is Phase 20's (C6): the design's
  sentence with the volume giving the lowering back (ADR-0162 C17).
-->
<script>
  import { equaliser, note, setEqualiser, stateLine } from '../../lib/equaliser.svelte.js';

  let { open = false, onclose = () => {}, onedit = () => {} } = $props();

  const eq = $derived($equaliser);
  const on = $derived(!!eq?.on);
  const lit = $derived(on && !eq?.dsd);
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

  //: Opened on the one in use.
  let row = $state(null);
  $effect(() => {
    if (!open || !row) return;
    requestAnimationFrame(() => {
      const t = row.querySelector('[data-sel="1"]');
      if (!t) return;
      const d = t.offsetLeft - row.scrollLeft;
      if (d + t.offsetWidth > row.clientWidth - 40 || d < 16) row.scrollLeft = t.offsetLeft - 120;
    });
  });
</script>

<div class="scrim" class:is-open={open} role="presentation" onclick={onclose}></div>
<div class="sheet" class:is-open={open} role="dialog" aria-label="Equaliser" aria-hidden={!open} inert={!open}>
  <button class="handle" type="button" aria-label="Close" onclick={onclose}></button>
  {#if eq}
    <div class="head">
      <div class="head__text">
        <div class="title">Equaliser</div>
        <div class="state" class:is-amber={stateLine(eq).amber}>{stateLine(eq).text}</div>
      </div>
      <button class="power" type="button" aria-label="Equaliser on or off" aria-pressed={on} onclick={toggle}>
        <span class="track" class:is-on={on}><span class="knob"></span></span>
      </button>
    </div>
    <div class="chips" class:is-dim={!lit} bind:this={row}>
      {#each chips as c (c.key)}
        {@const sel = eq.sel === c.key}
        {#if c.rule}<span class="rule"></span>{/if}
        <button type="button" class="chip" class:is-sel={sel} data-sel={sel ? '1' : '0'} aria-pressed={sel}
                onclick={() => choose(c.key)}>{#if c.custom}<span class="chip__dot"></span>{/if}{c.name}</button>
      {/each}
    </div>
    <div class="note" class:is-amber={!!error || note(eq).amber}>{error ?? note(eq).text}</div>
    <button class="edit" type="button" onclick={onedit}>Edit bands in Settings<span class="edit__chev"></span></button>
  {/if}
</div>

<style>
  .scrim {
    position: absolute;
    inset: 0;
    z-index: 50;
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
    z-index: 51;
    background: #16232c;
    border-top: 1px solid rgba(233, 238, 242, 0.16);
    border-radius: 24px 24px 0 0;
    padding: 10px 16px calc(22px + env(safe-area-inset-bottom, 0px));
    display: flex;
    flex-direction: column;
    gap: 14px;
    box-shadow: 0 -10px 32px rgba(0, 0, 0, 0.6);
    transform: translateY(calc(100% + 24px));
    transition: transform var(--remote-slide);
  }
  .sheet.is-open {
    transform: translateY(0);
  }
  /* Drawn 36 x 4, touched 52 x 20. */
  .handle {
    align-self: center;
    width: 52px;
    height: 20px;
    margin: -8px 0;
    padding: 0;
    border: 0;
    background: none;
    display: grid;
    place-items: center;
    cursor: pointer;
  }
  .handle::before {
    content: '';
    width: 36px;
    height: 4px;
    border-radius: 2px;
    background: rgba(233, 238, 242, 0.24);
  }
  .head {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .head__text {
    flex: 1;
    min-width: 0;
  }
  .title {
    font-size: 19px;
    font-weight: 700;
  }
  .state {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.06em;
    margin-top: 4px;
    color: rgba(233, 238, 242, 0.72);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .state.is-amber,
  .note.is-amber {
    color: var(--accent-warn);
  }
  .power {
    height: 48px;
    padding: 0 10px;
    border-radius: 14px;
    box-sizing: border-box;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(233, 238, 242, 0.1);
    display: flex;
    align-items: center;
    cursor: pointer;
    flex-shrink: 0;
  }
  .track {
    width: 56px;
    height: 32px;
    border-radius: 16px;
    position: relative;
    box-sizing: border-box;
    display: block;
    background: rgba(233, 238, 242, 0.08);
    border: 1px solid rgba(233, 238, 242, 0.16);
    transition: background 140ms ease;
  }
  .track.is-on {
    background: rgba(126, 214, 188, 0.32);
    border-color: rgba(126, 214, 188, 0.5);
  }
  .knob {
    position: absolute;
    top: 3px;
    left: 3px;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: block;
    background: rgba(233, 238, 242, 0.6);
    transition: left 140ms ease;
  }
  .track.is-on .knob {
    left: 27px;
    background: #7ed6bc;
  }
  .chips {
    display: flex;
    gap: 6px;
    overflow-x: auto;
    scrollbar-width: none;
    margin: 0 -16px;
    padding: 0 16px;
    -webkit-mask-image: linear-gradient(90deg, transparent 0, #000 16px, #000 calc(100% - 40px), transparent 100%);
    mask-image: linear-gradient(90deg, transparent 0, #000 16px, #000 calc(100% - 40px), transparent 100%);
    transition: opacity 160ms ease;
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
    margin: 10px 3px;
    background: rgba(233, 238, 242, 0.16);
    flex-shrink: 0;
  }
  .chip {
    flex-shrink: 0;
    height: 44px;
    padding: 0 16px;
    border-radius: 12px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    font: inherit;
    font-size: 15px;
    font-weight: 600;
    white-space: nowrap;
    cursor: pointer;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.12);
    color: #e9eef2;
  }
  /* Custom, Phase 20's: a dot before the name. */
  .chip__dot {
    width: 7px;
    height: 7px;
    margin-right: 8px;
    border-radius: 50%;
    background: #e0a758;
    flex-shrink: 0;
  }
  .chip.is-sel {
    background: rgba(126, 214, 188, 0.16);
    border-color: rgba(126, 214, 188, 0.55);
    color: #7ed6bc;
  }
  .note {
    font-size: 14px;
    line-height: 1.4;
    color: rgba(233, 238, 242, 0.6);
    text-wrap: pretty;
  }
  .edit {
    height: 48px;
    border-radius: 14px;
    box-sizing: border-box;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.14);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    font: inherit;
    font-size: 16px;
    font-weight: 600;
    color: #e9eef2;
    cursor: pointer;
  }
  .edit:active {
    transform: scale(0.98);
  }
  .edit__chev {
    width: 8px;
    height: 8px;
    border-right: 2px solid rgba(233, 238, 242, 0.6);
    border-top: 2px solid rgba(233, 238, 242, 0.6);
    transform: rotate(45deg);
    display: block;
  }
</style>
