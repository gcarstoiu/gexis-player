<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0180 decision 4, design/source/31 (`AddStationSheet`, H13-H15): a
  station the directory does not have, added by its address. The player
  plays it out loud first (George, 2026-11-14); kept only if it sounds, and
  then it goes on playing. The sheet waits for that answer - *Checking ·
  playing it on Living Room* - and says when it did not play. The phone types
  with its own keyboard.
-->
<script>
  import { addByAddress } from '../../../lib/radio.js';
  import { SheetPull } from '../sheetPull.svelte.js';
  import { RADIO } from './glyphs.js';

  let { open = false, player = 'the player', onclose = () => {}, onadded = () => {}, onsay = () => {} } = $props();

  let url = $state('');
  let name = $state('');
  //: form | checking | failed
  let phase = $state('form');
  let urlFocused = $state(false);
  let asked = 0;
  const sheet = new SheetPull(() => close());

  $effect(() => {
    if (!open) return;
    url = '';
    name = '';
    phase = 'form';
    asked += 1;
  });

  const ready = $derived(/^https?:\/\/\S+$/i.test(url.trim()) && name.trim().length > 0);

  async function check() {
    if (!ready || phase === 'checking') return;
    const mine = ++asked;
    phase = 'checking';
    document.activeElement?.blur?.();
    try {
      const body = await addByAddress(url.trim(), name.trim());
      if (mine !== asked) return;
      onadded(body.station);
    } catch (error) {
      if (mine !== asked) return;
      if (error.status === 422 || error.status === 400) {
        phase = 'failed';
      } else {
        phase = 'form';
        onsay(error.message);
      }
    }
  }
  function close() {
    asked += 1;
    onclose();
  }
</script>

<div class="scrim" class:is-open={open} role="presentation" onclick={close}></div>
<div class="sheet" class:is-open={open} class:is-pulled={sheet.pull !== null} role="dialog" aria-label="Add a station"
     aria-hidden={!open} inert={!open} style:transform={sheet.pull !== null ? `translateY(${sheet.pull}px)` : null}
     onpointerdown={sheet.grab} onpointermove={sheet.drag} onpointerup={(e) => sheet.release(e)}
     onpointercancel={(e) => sheet.release(e, true)} onclickcapture={sheet.notTapped}>
  <button class="grabber" type="button" aria-label="Close" onclick={close}></button>
  <div class="title">Add a station</div>
  {#if phase === 'form'}
    <div class="note">For a station the directory does not have. {player} plays it for a moment first, to check it works.</div>
  {/if}
  <label class="field">
    <span class="label">Address</span>
    <input class="input input--url" class:is-focused={urlFocused} class:is-failed={phase === 'failed'} type="url"
           inputmode="url" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false"
           enterkeyhint="next" bind:value={url} disabled={phase === 'checking'}
           onfocus={() => (urlFocused = true)} onblur={() => (urlFocused = false)}
           oninput={() => { if (phase === 'failed') phase = 'form'; }} />
  </label>
  <label class="field">
    <span class="label">Name</span>
    <input class="input input--name" type="text" autocomplete="off" enterkeyhint="done" bind:value={name}
           disabled={phase === 'checking'} onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); check(); } }} />
  </label>
  {#if phase === 'checking'}
    <div class="checking" role="status">
      <svg class="spin" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><path d={RADIO.spinner} /></svg>
      <span>Checking · playing it on {player}</span>
    </div>
  {:else if phase === 'failed'}
    <div class="failed" role="alert">
      <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
        {#each RADIO.warn as d (d)}<path {d} />{/each}<circle cx="12" cy="16.9" r="0.6" />
      </svg>
      <span class="failed__words">
        <span class="failed__title">It did not play</span>
        <span class="failed__text">Nothing came from that address that the player can play. Check it, or try again.</span>
      </span>
    </div>
  {/if}
  <div class="buttons" class:is-form={phase === 'form'}>
    <button class="button" type="button" onclick={close}>Cancel</button>
    <button class="button button--go" type="button" disabled={!ready || phase === 'checking'} onclick={check}>
      {phase === 'failed' ? 'Try again' : 'Check and add'}
    </button>
  </div>
</div>

<style>
  .scrim {
    position: absolute;
    inset: 0;
    z-index: 52;
    background: var(--bg-scrim);
    opacity: 0;
    pointer-events: none;
    transition: opacity 260ms ease;
  }
  .scrim.is-open {
    opacity: 1;
    pointer-events: auto;
  }
  /* Bottom-anchored, sized by what it holds, with the drawing's air under
     the buttons (H13: the sheet from y 330 on an 844 phone). */
  .sheet {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 53;
    max-height: calc(100% - 40px);
    overflow-y: auto;
    box-sizing: border-box;
    padding: 12px 20px calc(24px + 102px + env(safe-area-inset-bottom, 0px));
    display: flex;
    flex-direction: column;
    gap: 16px;
    border-radius: var(--r-28) var(--r-28) 0 0;
    background: var(--bg-panel);
    border-top: 1px solid var(--c-ink-12);
    box-shadow: 0 -18px 48px var(--c-black-45);
    transform: translateY(calc(100% + 24px));
    transition: transform var(--remote-slide);
    touch-action: pan-x;
  }
  .sheet.is-open {
    transform: translateY(0);
  }
  .sheet.is-pulled {
    transition: none;
  }
  .grabber {
    align-self: center;
    flex-shrink: 0;
    position: relative;
    width: 60px;
    height: 21px;
    margin: -8px 0;
    padding: 0;
    border: 0;
    background: none;
    cursor: pointer;
  }
  .grabber::after {
    content: '';
    position: absolute;
    left: 8px;
    top: 8px;
    width: 44px;
    height: 5px;
    border-radius: 3px;
    background: var(--c-ink-30);
  }
  .title {
    font-size: 24px;
    font-weight: 800;
  }
  .note {
    font-size: 15px;
    line-height: 1.45;
    color: var(--ink-muted);
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 7px;
  }
  .label {
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--ink-muted);
  }
  .input {
    width: 100%;
    height: 50px;
    box-sizing: border-box;
    padding: 0 14px;
    border-radius: var(--r-14);
    border: 1px solid var(--c-ink-16);
    background: var(--c-ink-05);
    color: var(--ink);
    outline: none;
    user-select: text;
    -webkit-user-select: text;
  }
  .input:disabled {
    opacity: 1;
    -webkit-text-fill-color: var(--ink);
  }
  .input--url {
    font: 600 14px var(--font-mono);
  }
  .input--name {
    font: 600 17px var(--font-ui);
  }
  .input--name:focus,
  .input--url.is-focused {
    border-color: var(--c-lms-60);
  }
  .input--url.is-failed {
    border-color: var(--c-warn-80);
  }
  .checking {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 16px;
    border-radius: var(--r-14);
    background: var(--c-lms-10);
    border: 1px solid var(--c-lms-35);
    font-size: 16px;
    font-weight: 700;
    color: var(--accent-lms);
  }
  .checking svg {
    flex-shrink: 0;
    fill: none;
    stroke: currentColor;
    stroke-width: 3;
    stroke-linecap: round;
  }
  .spin {
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  .failed {
    display: flex;
    gap: 12px;
    padding: 14px 16px;
    border-radius: var(--r-14);
    background: var(--directory-ground);
    border: 1px solid var(--c-warn-45);
  }
  .failed svg {
    flex-shrink: 0;
    fill: none;
    stroke: var(--accent-warn);
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .failed circle {
    fill: var(--accent-warn);
  }
  .failed__words {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .failed__title {
    font-size: 16px;
    font-weight: 800;
    color: var(--accent-warn);
  }
  .failed__text {
    font-size: 14px;
    line-height: 1.4;
    color: var(--ink-strong);
  }
  .buttons {
    display: flex;
    gap: 10px;
  }
  .buttons.is-form {
    margin-top: 4px;
  }
  .button {
    flex: 1;
    height: 52px;
    box-sizing: border-box;
    border-radius: var(--r-lg);
    border: 1px solid var(--c-ink-16);
    background: var(--ink-fill);
    color: var(--ink);
    font: 800 17px var(--font-ui);
    cursor: pointer;
  }
  .button--go {
    border-color: transparent;
    background: var(--c-lms-90);
    color: var(--ink-on-accent);
  }
  .button:disabled {
    opacity: 0.4;
    cursor: default;
  }
  .button:not(:disabled):active {
    transform: scale(0.98);
  }
</style>
