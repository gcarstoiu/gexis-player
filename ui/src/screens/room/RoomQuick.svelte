<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The *Room* control, close to the music (ADR-0175, ADR-0177; design/source/29
  Q01-Q11, design/source/30 1l): beside the equaliser's in the panel's volume
  drawer (`drawer`), the bar's tray (`bartray`) and the phone's volume row
  (`phone`).

  The drawer has one control, *Without · Bass · Full range*: a tap sets it,
  heard at once (Without is *Hear it without*). The tray and the phone stay
  one tap, On and Without - the A/B, kept as set - and name the reach. Off,
  it says so and a tap opens Room correction's page; while DSD plays it is
  dimmed and does nothing; an output never measured has none. A measurement
  from before Phase 30 reaches the bass only: Full range is dimmed.
-->
<script>
  import { room, setRoom } from '../../lib/room.svelte.js';

  let { host = 'drawer', onopen = null } = $props();

  const r = $derived($room);
  const measured = $derived(r?.measured ?? null);
  //: The control moves from the press; the core's word wins in the end.
  let want = $state(null);
  let wantReach = $state(null);
  const without = $derived(want ?? !!r?.without);
  const reach = $derived(wantReach ?? r?.reach ?? 'full');
  $effect(() => {
    if (want !== null && !!r?.without === want) want = null;
    if (wantReach !== null && r?.reach === wantReach) wantReach = null;
  });
  const on = $derived(!!r?.on);
  const dsd = $derived(!!r?.dsd);
  const lit = $derived(on && !dsd);
  const bassOnly = $derived(measured?.range === 'bass');
  let error = $state(null);

  async function send(changes) {
    error = null;
    try {
      await setRoom(changes);
    } catch (e) {
      error = e.message;
      want = null;
      wantReach = null;
    }
  }

  async function tap() {
    if (!on) {
      onopen?.();
      return;
    }
    if (dsd) return;
    want = !without;
    await send({ without: want });
  }

  //: The drawer's three: Without is the A/B, Bass and Full range the reach
  //: (with the A/B off).
  async function choose(k) {
    if (!lit) return;
    if (k === 'without') {
      if (without) return;
      want = true;
      await send({ without: true });
      return;
    }
    if (k === 'full' && bassOnly) return;
    const changes = {};
    if (without) changes.without = false;
    if (reach !== k) changes.reach = k;
    if (!Object.keys(changes).length) return;
    if ('without' in changes) want = false;
    if ('reach' in changes) wantReach = k;
    await send(changes);
  }

  const reachWord = $derived(reach === 'bass' ? 'Bass' : 'Full range');
  const stateLine = $derived(!on ? 'Off · open it to turn it on' : dsd ? 'Stands aside while DSD plays'
    : without ? 'Without · no correction at all' : bassOnly ? 'Bass · measured for the bass only'
      : `${reachWord} · measured ${measured?.day ?? ''}`);
  const pill = $derived(!on ? 'Room · Off' : dsd ? 'Room · DSD' : without ? 'Room · Without' : `Room · ${reachWord}`);
  const chip = $derived(!on ? 'Off' : dsd ? 'DSD' : without ? 'Without' : reach === 'bass' ? 'Bass' : 'Full');
  const selected = $derived(without ? 'without' : reach);
  const SEGS = [['without', 'Without'], ['bass', 'Bass'], ['full', 'Full range']];
</script>

{#snippet glyph(size)}
  <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" stroke-width="2"
       stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="M3 20h18M5 20V9l7-5 7 5v11"></path><path d="M9 15c1-1.5 2-1.5 3 0s2 1.5 3 0"></path>
  </svg>
{/snippet}

{#if measured}
  {#if host === 'drawer'}
    <div class="drawer">
      <div class="divider"></div>
      <div class="top">
        <div class="top__text">
          <div class="title">Room correction</div>
          <div class="state" class:is-amber={lit && without}>{error ?? stateLine}</div>
        </div>
        {#if on}
          <div class="seg" class:is-dim={dsd} role="group" aria-label="Room correction">
            {#each SEGS as [k, name] (k)}
              <button type="button" class="seg__btn seg__btn--{k}" class:is-sel={selected === k}
                      class:is-locked={k === 'full' && bassOnly} aria-pressed={selected === k}
                      disabled={dsd || (k === 'full' && bassOnly)} onclick={() => choose(k)}>{name}</button>
            {/each}
          </div>
        {:else}
          <button type="button" class="open" onclick={() => onopen?.()}>Open<span class="open__chev"></span></button>
        {/if}
      </div>
    </div>
  {:else if host === 'bartray'}
    <button type="button" class="pill" class:is-lit={lit && !without} class:is-without={lit && without} class:is-dim={dsd}
            aria-label="Room correction" aria-pressed={lit && without} onclick={tap}>
      {@render glyph(24)}<span class="pill__text">{pill}</span>
    </button>
  {:else}
    <button type="button" class="chip" class:is-lit={lit && !without} class:is-without={lit && without} class:is-dim={dsd}
            aria-label="Room correction" aria-pressed={lit && without} onclick={tap}>
      {@render glyph(18)}<span class="chip__text">{chip}</span>
    </button>
  {/if}
{/if}

<style>
  .divider {
    height: 1px;
    background: var(--ink-line);
    margin: 24px 0 20px;
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
    color: var(--ink-muted);
  }
  .is-amber {
    color: var(--rc-without);
  }
  .seg {
    flex-shrink: 0;
    display: flex;
    gap: 4px;
    padding: 4px;
    border-radius: var(--r-17);
    background: var(--ink-fill);
  }
  .seg__btn {
    height: 50px;
    padding: 0 20px;
    border-radius: var(--r-13);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    font: inherit;
    font-size: 17px;
    font-weight: 700;
    white-space: nowrap;
    background: transparent;
    border: 1px solid transparent;
    color: var(--ink-muted);
  }
  .seg__btn.is-sel {
    background: var(--c-lms-16);
    border-color: var(--c-lms-55);
    color: var(--accent-lms);
  }
  .seg__btn--without.is-sel {
    background: var(--c-warn-16);
    border-color: var(--c-warn-55);
    color: var(--rc-without);
  }
  .seg__btn.is-locked {
    opacity: 0.4;
  }
  .seg__btn:active {
    transform: scale(0.95);
  }
  .open {
    height: 58px;
    padding: 0 18px 0 22px;
    border-radius: var(--r-15);
    box-sizing: border-box;
    background: var(--ink-fill);
    border: 1px solid var(--c-ink-14);
    display: flex;
    align-items: center;
    gap: 12px;
    font: inherit;
    font-size: 17px;
    font-weight: 600;
    color: var(--ink);
    flex-shrink: 0;
  }
  .open__chev {
    width: 9px;
    height: 9px;
    border-right: 2.5px solid var(--ink-quiet);
    border-top: 2.5px solid var(--ink-quiet);
    transform: rotate(45deg);
    margin-left: -2px;
  }
  .pill {
    position: relative;
    z-index: 1;
    height: 60px;
    padding: 0 22px 0 18px;
    border-radius: var(--r-30);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
    background: var(--ink-fill);
    border: 1px solid var(--c-ink-14);
    color: var(--ink-body);
    font: inherit;
  }
  .pill__text {
    font-size: 19px;
    font-weight: 700;
    white-space: nowrap;
  }
  .chip {
    height: var(--remote-button);
    padding: 0 12px 0 11px;
    border-radius: var(--remote-button-radius);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 6px;
    flex: none;
    background: var(--ink-fill);
    border: 1px solid var(--c-ink-14);
    color: var(--ink-body);
    font: inherit;
  }
  .chip__text {
    font-size: 13px;
    font-weight: 700;
    white-space: nowrap;
  }
  .pill.is-lit,
  .chip.is-lit {
    background: var(--c-lms-12);
    border-color: var(--c-lms-45);
    color: var(--accent-lms);
  }
  .pill.is-without,
  .chip.is-without {
    background: var(--c-warn-12);
    border-color: var(--rc-without-line);
    color: var(--rc-without);
  }
  .is-dim {
    opacity: 0.4;
    pointer-events: none;
  }
  .pill:active,
  .chip:active,
  .open:active {
    transform: scale(0.95);
  }
  @media (max-width: 379px) {
    /* A narrow phone: the glyph carries it, with its colour and its name. */
    .chip__text {
      display: none;
    }
  }
</style>
