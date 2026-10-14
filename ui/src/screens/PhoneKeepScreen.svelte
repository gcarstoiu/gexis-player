<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **Keep this screen? on the phone** (ADR-0147 D3; George, 2026-10-13: a TV
  as the screen, answered "From the phone"). A screen with no touch the
  player knows of - a TV, any screen in no list - cannot be pressed, so the
  question the panel draws on it is answered here. Only then: a panel with
  touch still answers on itself (ADR-0109 decision 2), and the core refuses
  a phone's answer otherwise. Not answered within the time, the player goes
  back, as on a panel.

  **Also a listed panel whose touch is not recognised** (Finding 125,
  2026-10-14): many need an SPI ads7846 overlay or a goodtft driver the
  player never installs, so their touch may not work. The panel shows its
  own buttons (`panel_buttons`) and this page answers as well.
-->
<script>
  let { question, secondsLeft = 0, onkeep, onrevert } = $props();

  let busy = $state(false);
  const left = $derived(Math.max(0, Math.ceil(secondsLeft)));

  async function answer(fn) {
    busy = true;
    try {
      await fn?.();
    } finally {
      busy = false;
    }
  }
</script>

<div class="keep" role="alertdialog" aria-label="Keep this screen?">
  <div class="keep__text">
    <b>Keep this screen?</b>
    <span>
      The picture is on {question.model}. Is it showing properly? {question.panel_buttons
        ? 'Answer on the screen, or here if its touch does not respond.'
        : 'It has no touch, so answer here.'}
      Not kept within {left} s, the player goes back to {question.previous ?? "the screen before"}.
    </span>
  </div>
  <div class="keep__buttons">
    <button type="button" class="keep__btn keep__btn--back" disabled={busy} onclick={() => answer(onrevert)}>Go back</button>
    <button type="button" class="keep__btn" disabled={busy} onclick={() => answer(onkeep)}>Keep</button>
  </div>
</div>

<style>
  .keep {
    position: fixed;
    left: 50%;
    top: 16px;
    transform: translateX(-50%);
    z-index: 96;
    width: min(620px, calc(100% - 32px));
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 14px 16px;
    padding: 16px 18px;
    border-radius: 18px;
    background: var(--bg-panel);
    border: 1px solid rgba(224, 167, 88, 0.55);
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
    color: var(--ink);
  }
  .keep__text {
    flex: 1 1 260px;
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
  .keep__buttons {
    display: flex;
    gap: 10px;
    margin-left: auto;
  }
  .keep__btn {
    min-width: 96px;
    height: 48px;
    border-radius: 14px;
    font-size: 16px;
    font-weight: 700;
    color: var(--ink-on-accent);
    background: var(--accent-warn);
    border: none;
  }
  .keep__btn--back {
    color: var(--ink);
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.25);
  }
  .keep__btn:disabled {
    opacity: 0.6;
  }
</style>
