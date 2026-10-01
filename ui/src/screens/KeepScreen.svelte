<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **Keep this screen?** (ADR-0109 decision 5; design round 2,
  `design/source/13b/Keep This Screen.dc.html`). Shown on the panel after a
  screen or a rotation is chosen and the player has restarted on it. Keep is a
  touch on the panel itself, so it proves the picture and the touch input
  together (review decision 2: the panel only). With no touch before the
  countdown ends the player goes back to the previous screen.

  **Not wired yet.** The core side - the countdown, the revert, the state that
  says this is showing - does not exist. This component only draws it and
  calls back; `secondsLeft` is the caller's clock, as the pairing frame's
  countdown is the agent's, so the two can never disagree.

  Both families from one file, as the design draws them:
  - **Standard:** a kicker with the mark, the title at 72, the model at 32,
    an amber pill for an untested model, *Go back now* (74) left of *Keep*
    (96), and the countdown in mono at 20.
  - **Bar:** the words at the left - title 56, model 26 on one line, the
    untested line plain amber at 20, the countdown at 18 - and a 260 px
    column at the right with *Keep* (110) above *Go back now* (74).
  - **Both:** an 8 px bar along the bottom drains with the countdown.

  A rotation-only change says so (review decision 4): *Keep this rotation?*
  and *Going back to 0° in n s*.
-->
<script>
  import mark from '../assets/gexis-mark.svg';
  import { screen } from '../lib/family.svelte.js';
  import { pressing } from '../lib/press.svelte.js';

  let {
    model = '',
    previous = '',
    untested = false,
    secondsLeft = 30,
    total = 30,
    rotationOnly = false,
    onkeep,
    onrevert,
  } = $props();

  const bar = $derived(screen.family === 'bar');
  const title = $derived(rotationOnly ? 'Keep this rotation?' : 'Keep this screen?');
  const back = $derived(rotationOnly ? previous || '0°' : previous);
  const left = $derived(Math.max(0, Math.ceil(secondsLeft)));
  const drained = $derived(total > 0 ? Math.max(0, Math.min(100, (secondsLeft / total) * 100)) : 0);
  const press = pressing();
</script>

{#snippet warnIcon(size)}
  <svg viewBox="0 0 64 64" width={size} height={size} aria-hidden="true">
    <path d="M32 7 L60 56 H4 Z" fill="none" stroke="currentColor" stroke-width="5" stroke-linejoin="round" />
    <path d="M32 24 V39" stroke="currentColor" stroke-width="5.5" stroke-linecap="round" />
    <circle cx="32" cy="47.5" r="3.4" fill="currentColor" />
  </svg>
{/snippet}

{#snippet keep()}
  <button
    class="btn btn--keep"
    class:is-pressed={press.is('keep')}
    type="button"
    onpointerdown={() => press.down('keep')}
    onpointerup={press.up}
    onpointercancel={press.up}
    onclick={() => press.act(() => onkeep?.())}
  >Keep</button>
{/snippet}

{#snippet revert()}
  <button
    class="btn btn--back"
    class:is-pressed={press.is('back')}
    type="button"
    onpointerdown={() => press.down('back')}
    onpointerup={press.up}
    onpointercancel={press.up}
    onclick={() => press.act(() => onrevert?.())}
  >Go back now</button>
{/snippet}

<div class="keep" class:keep--bar={bar} role="dialog" aria-label={title}>
  <div class="drain"><div class="drain__left" style:width={`${drained}%`}></div></div>

  <header class="kicker">
    <img src={mark} alt="" width={bar ? 32 : 40} height={bar ? 32 : 40} />
    <span>Screen</span>
  </header>

  {#if bar}
    <div class="row">
      <div class="words">
        <div class="title">{title}</div>
        {#if model}<div class="model">{model}</div>{/if}
        {#if untested}<div class="untested">This model has not been tested with gexis</div>{/if}
        <div class="count">Going back to {back} in {left} s</div>
      </div>
      <div class="actions">
        {@render keep()}
        {@render revert()}
      </div>
    </div>
  {:else}
    <div class="stack">
      <div class="title">{title}</div>
      {#if model}<div class="model">{model}</div>{/if}
      {#if untested}
        <div class="pill">{@render warnIcon(34)}<span>This model has not been tested with gexis</span></div>
      {/if}
      <div class="actions">
        {@render revert()}
        {@render keep()}
      </div>
      <div class="count">Going back to {back} in {left} s</div>
    </div>
  {/if}
</div>

<style>
  .keep {
    position: absolute;
    inset: 0;
    z-index: 33;
    overflow: hidden;
    color: var(--ink);
    background:
      radial-gradient(130% 105% at 20% 42%, rgba(20, 33, 42, 0.72), rgba(13, 21, 28, 0.96)),
      var(--bg-base);
    user-select: none;
  }
  .drain {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 8px;
    background: rgba(233, 238, 242, 0.08);
  }
  .drain__left {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    background: var(--accent-lms);
    transition: width 1s linear;
  }

  .kicker {
    position: absolute;
    left: 56px;
    right: 56px;
    top: 30px;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .kicker img {
    display: block;
  }
  .kicker span {
    font-family: var(--font-mono);
    font-size: 16px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .keep--bar .kicker {
    left: 40px;
    right: 40px;
    top: 22px;
    gap: 14px;
  }
  .keep--bar .kicker span {
    font-size: 15px;
  }

  .btn {
    font: inherit;
    color: inherit;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: transform 120ms ease;
  }
  .btn.is-pressed {
    transform: scale(0.96);
  }
  .btn--keep {
    border: 0;
    border-radius: 24px;
    background: var(--accent-lms);
    color: var(--ink-on-accent);
    font-size: 32px;
    font-weight: 800;
    box-shadow: 0 12px 30px rgba(126, 214, 188, 0.3);
  }
  .btn--back {
    height: 74px;
    border-radius: 18px;
    background: var(--ink-fill);
    border: 1px solid rgba(233, 238, 242, 0.16);
    font-weight: 700;
  }

  /* Standard */
  .stack {
    position: absolute;
    inset: 96px 56px 60px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 22px;
  }
  .stack .title {
    font-size: 72px;
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1.05;
  }
  .stack .model {
    font-size: 32px;
    line-height: 1.3;
    color: var(--ink-body);
  }
  .pill {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 14px 24px;
    border-radius: 16px;
    font-size: 24px;
    color: var(--accent-warn);
    background: color-mix(in srgb, var(--accent-warn) 12%, transparent);
    border: 2px solid color-mix(in srgb, var(--accent-warn) 45%, transparent);
  }
  .pill svg {
    flex-shrink: 0;
  }
  .stack .actions {
    display: flex;
    align-items: center;
    gap: 20px;
    margin-top: 14px;
  }
  .stack .btn--back {
    padding: 0 40px;
    font-size: 24px;
  }
  .stack .btn--keep {
    height: 96px;
    padding: 0 64px;
  }
  .stack .count {
    margin-top: 6px;
    font-family: var(--font-mono);
    font-size: 20px;
    letter-spacing: 0.04em;
    color: var(--ink-muted);
  }

  /* Bar */
  .row {
    position: absolute;
    inset: 66px 56px 40px;
    display: flex;
    align-items: center;
    gap: 48px;
  }
  .words {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .row .title {
    font-size: 56px;
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1.05;
  }
  .row .model {
    font-size: 26px;
    line-height: 1.3;
    color: var(--ink-body);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .untested {
    font-size: 20px;
    color: var(--accent-warn);
  }
  .row .count {
    margin-top: 6px;
    font-family: var(--font-mono);
    font-size: 18px;
    letter-spacing: 0.04em;
    color: var(--ink-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .row .actions {
    display: flex;
    flex-direction: column;
    gap: 14px;
    flex-shrink: 0;
    width: 260px;
  }
  .row .btn--keep {
    height: 110px;
  }
  .row .btn--back {
    font-size: 22px;
  }
</style>
