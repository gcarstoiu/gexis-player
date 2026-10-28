<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0164: the EQ sheet (design/source/21, *Sheets*), from the volume row's
  EQ button. *Equaliser*, the setting in use, the switch; the settings as
  chips that scroll sideways - Phase 20's presets, a rule, the owner's, with
  Custom first while it is the one in use - applied at a tap; the note; and
  *Edit bands in Settings*. The note is Phase 20's (C6): the design's
  sentence with the volume giving the lowering back (ADR-0162 C17).
  A swipe down closes it too (George, 2026-10-27), as the handle and the
  scrim do.
-->
<script>
  import { equaliser, note, setEqualiser, stateLine } from '../../lib/equaliser.svelte.js';

  let { open = false, onclose = () => {}, onedit = () => {} } = $props();

  const eq = $derived($equaliser);
  //: **The switch moves at once** (George, 2026-10-28: slow to react): the
  //: core takes seconds to put the equaliser in the chain or out, so the new
  //: position shows from the press, and goes back only if it is refused.
  let wanted = $state(null);
  let wantedTimer;
  const on = $derived(wanted ?? !!eq?.on);
  $effect(() => {
    if (wanted !== null && !!eq?.on === wanted) wanted = null;
  });
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
    wanted = !on;
    clearTimeout(wantedTimer);
    // Never held for good: what the core says wins in the end.
    wantedTimer = setTimeout(() => (wanted = null), 15000);
    try {
      await setEqualiser({ on: wanted });
    } catch (e) {
      error = e.message;
      wanted = null;
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

  // ── The swipe down ──────────────────────────────────────────────────────
  //: Below this a gesture has not said what it is yet; past it a sideways
  //: one is the chips' scroll and a downward one pulls the sheet.
  const DECIDE_AT = 12;
  //: Pulled further than this, or flicked, the sheet closes; short of it, it
  //: goes back.
  const CLOSE_AT = 80;
  const FLICK = 0.5; // px/ms, downwards
  //: The gesture in progress; nothing draws from it.
  let gesture = null;
  //: How far the finger has pulled the sheet down, while it does.
  let pull = $state(null);
  //: A pull ends with a click on whatever it started on; this is when the
  //: last one ended, so that click is not a tap.
  let pulled = 0;

  function grab(event) {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    gesture = { id: event.pointerId, x: event.clientX, y: event.clientY, trail: [], decided: false };
  }
  function drag(event) {
    if (!gesture || event.pointerId !== gesture.id) return;
    const dx = event.clientX - gesture.x;
    const dy = event.clientY - gesture.y;
    if (!gesture.decided) {
      if (Math.max(Math.abs(dx), Math.abs(dy)) <= DECIDE_AT) return;
      if (dy <= 0 || Math.abs(dx) > dy) {
        gesture = null;
        return;
      }
      gesture.decided = true;
      event.currentTarget.setPointerCapture(event.pointerId);
    }
    pull = Math.max(0, dy);
    // Its last 100 ms, for the speed it is let go at.
    const trail = gesture.trail;
    trail.push([event.timeStamp, pull]);
    while (trail.length > 2 && event.timeStamp - trail[0][0] > 100) trail.shift();
  }
  function release(event, cancelled = false) {
    if (!gesture || event.pointerId !== gesture.id) return;
    const { decided, trail } = gesture;
    gesture = null;
    const [t0, y0] = trail[0] ?? [0, 0];
    const [t1, y1] = trail.at(-1) ?? [0, 0];
    // A finger that stopped before it let go did not flick.
    const v = event.timeStamp - t1 > 100 || t1 <= t0 ? 0 : (y1 - y0) / (t1 - t0);
    if (!decided) return;
    pulled = Date.now();
    if (!cancelled && (pull > CLOSE_AT || v > FLICK)) onclose();
    pull = null;
  }
  function notTapped(event) {
    if (Date.now() - pulled > 320) return;
    event.stopPropagation();
    event.preventDefault();
  }
</script>

<div class="scrim" class:is-open={open} role="presentation" onclick={onclose}></div>
<div class="sheet" class:is-open={open} class:is-pulled={pull !== null} role="dialog" aria-label="Equaliser"
     aria-hidden={!open} inert={!open} style:transform={pull !== null ? `translateY(${pull}px)` : null}
     onpointerdown={grab} onpointermove={drag} onpointerup={(e) => release(e)}
     onpointercancel={(e) => release(e, true)} onclickcapture={notTapped}>
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
    /* Sideways is the chips' scroll; down is the sheet's. */
    touch-action: pan-x;
  }
  .sheet.is-open {
    transform: translateY(0);
  }
  /* Where the finger is. */
  .sheet.is-pulled {
    transition: none;
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
  /* The switch alone, without the drawing's box round it (George,
     2026-10-27); the touch is still 48 px tall. */
  .power {
    height: 48px;
    padding: 0 10px;
    margin-right: -10px;
    box-sizing: border-box;
    background: none;
    border: 0;
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
    /* Its own, as a scroller: the sheet's does not reach inside it. */
    touch-action: pan-x;
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
