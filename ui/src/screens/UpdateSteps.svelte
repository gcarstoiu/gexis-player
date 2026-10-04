<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0110 §3: every step of an update, listed from the start and marked as
  it goes - the same list in the modal (phone and panel Settings) and on the
  panel's full-screen lock. `large` is the panel's, read from across a room.
-->
<script>
  let { update = null, large = false } = $props();

  //: The updater's six steps (gexis-update STEPS), in the words shown.
  const LABELS = {
    download: 'Download',
    backup: 'Back up',
    stop: 'Stop playback',
    install: 'Install',
    restart: 'Restart the player',
    check: 'Check',
  };

  const steps = $derived(
    Object.keys(LABELS).map((name) => ({
      name,
      label: name === 'restart' && update?.reboot ? 'Restart the device' : LABELS[name],
      state: update?.steps?.[name] ?? 'pending',
    }))
  );
  const share = $derived(Math.max(0, Math.min(1, Number(update?.progress ?? 0))));
</script>

<ol class="steps" class:steps--large={large}>
  {#each steps as s (s.name)}
    <li class="step" data-state={s.state}>
      <span class="step__mark" aria-hidden="true">
        {#if s.state === 'done'}
          <svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
        {:else if s.state === 'failed'}
          <svg viewBox="0 0 24 24"><path d="M7 7l10 10M17 7L7 17" /></svg>
        {/if}
      </span>
      <span class="step__body">
        <span class="step__label">{s.label}</span>
        <!-- A bar for the two long steps: the download, and since
             2026-10-04 the install (George: "Right now it's the longest
             step, but the user is kept in the dark about progress"). -->
        {#if (s.name === 'download' || s.name === 'install') && s.state === 'active'}
          <span class="step__bar"><span style:width={`${Math.round(share * 100)}%`}></span></span>
          <span class="step__pct">{Math.round(share * 100)} %</span>
        {/if}
      </span>
    </li>
  {/each}
</ol>

<style>
  .steps {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .step {
    display: flex;
    align-items: center;
    gap: 14px;
    min-height: 30px;
    color: var(--ink-quiet);
    transition: color var(--dur-fast) var(--ease);
  }
  .step[data-state='active'] { color: var(--ink); }
  .step[data-state='done'] { color: var(--ink-body); }
  .step[data-state='failed'] { color: var(--accent-warn); }

  .step__mark {
    flex-shrink: 0;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    border: 2px solid rgba(233, 238, 242, 0.22);
    display: flex;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
  }
  .step[data-state='active'] .step__mark {
    border-color: var(--accent-lms);
    border-right-color: transparent;
    animation: step-turn 0.9s linear infinite;
  }
  .step[data-state='done'] .step__mark {
    border-color: var(--accent-lms);
    background: rgba(126, 214, 188, 0.16);
  }
  .step[data-state='failed'] .step__mark {
    border-color: var(--accent-warn);
    background: rgba(224, 167, 88, 0.16);
  }
  .step__mark svg {
    width: 16px;
    height: 16px;
    fill: none;
    stroke: currentColor;
    stroke-width: 2.6;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .step[data-state='done'] .step__mark svg { stroke: var(--accent-lms); }

  .step__body {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .step__label {
    font-size: 17px;
    font-weight: 600;
    white-space: nowrap;
  }
  .step__bar {
    flex: 1;
    height: 6px;
    border-radius: 3px;
    background: rgba(233, 238, 242, 0.12);
    overflow: hidden;
  }
  .step__bar span {
    display: block;
    height: 100%;
    background: var(--accent-lms);
    transition: width 0.4s ease;
  }
  .step__pct {
    font-family: var(--font-mono);
    font-size: 14px;
    color: var(--ink-muted);
    min-width: 46px;
    text-align: right;
  }

  /* The panel's lock: read from 1-2 m (IMPLEMENTED-DIFFERENTLY, setup). */
  .steps--large { gap: 20px; }
  .steps--large .step { min-height: 44px; gap: 20px; }
  .steps--large .step__mark { width: 40px; height: 40px; border-width: 3px; }
  .steps--large .step__mark svg { width: 24px; height: 24px; }
  .steps--large .step__label { font-size: 30px; }
  .steps--large .step__bar { height: 10px; border-radius: 5px; }
  .steps--large .step__pct { font-size: 24px; min-width: 76px; }

  @keyframes step-turn {
    to { transform: rotate(360deg); }
  }
</style>
