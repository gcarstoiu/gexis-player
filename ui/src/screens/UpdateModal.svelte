<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0110 §3: one modal from the check to the end. Checking…, then Up to
  date or *0.2.5 is available* with its notes and Update; if anything plays,
  the warning that playback stops; then every step as it goes, and the
  outcome. A started update finishes (§5): from the steps on there is no
  cancel, only Hide - the update carries on, and Settings shows it again.
  Built from the design system (§7): Settings' centred dialog and its
  buttons.
-->
<script>
  import { onMount } from 'svelte';
  import { update, metadata, connection } from '../lib/state.js';
  import { runSetting } from '../lib/settings.js';
  import UpdateSteps from './UpdateSteps.svelte';
  import ReleaseNotes from './ReleaseNotes.svelte';

  //: `check` runs a check first; `available` opens on the waiting release
  //: (the tile's *Update…*); `progress` reopens an install already running.
  let { start = 'check', onclose } = $props();

  const CHECK_TIMEOUT_MS = 90_000;

  let phase = $state(start === 'progress' ? 'progress' : start === 'check' ? 'checking' : 'answer');
  let askedAt = 0;
  let from = $state($update?.installed ?? null);
  let timedOut = $state(false);

  const u = $derived($update ?? {});
  const playing = $derived($metadata?.transport === 'playing');
  const fresh = $derived(u.at ? Date.parse(u.at) >= askedAt - 2000 : false);

  onMount(() => {
    if (start !== 'check') return;
    askedAt = Date.now();
    runSetting('update_check');
    const id = setTimeout(() => (timedOut = true), CHECK_TIMEOUT_MS);
    return () => clearTimeout(id);
  });

  // The check's answer, once the updater has written one newer than the ask.
  $effect(() => {
    if (phase !== 'checking') return;
    if (fresh && ['current', 'available', 'failed'].includes(u.state)) phase = 'answer';
    else if (timedOut) phase = 'answer';
  });

  // The install's end: done, or failed and back where it was.
  $effect(() => {
    if (phase === 'progress' && !u.active && ['done', 'failed'].includes(u.state) && (fresh || start === 'progress')) {
      phase = 'end';
    }
  });

  function choose() {
    if (playing) phase = 'confirm';
    else go();
  }

  function go() {
    from = u.installed ?? from;
    askedAt = Date.now();
    phase = 'progress';
    runSetting('update_install');
  }

  function close() {
    // A new release replaced the page's own files: load them, rather than
    // go on drawing the old ones against a new core.
    if (phase === 'end' && u.state === 'done' && u.installed && u.installed !== from) {
      location.reload();
      return;
    }
    onclose?.();
  }
</script>

<div class="ask" role="dialog" aria-modal="true" aria-live="polite" aria-label="Update">
  <div class="ask__card">
    {#if phase === 'checking'}
      <div class="ask__title">Checking for updates…</div>
      <span class="task__bar task__bar--busy"><span></span></span>
    {:else if phase === 'answer'}
      {#if timedOut && !fresh}
        <div class="ask__title">Could not check</div>
        <div class="task__text">The device did not answer in time. Try again in a minute.</div>
        <div class="ask__buttons"><button type="button" class="btn btn--confirm" onclick={close}>OK</button></div>
      {:else if u.state === 'available'}
        <div class="ask__title">{u.release} is available</div>
        {#if u.whats_new}
          <div class="notes">
            <ReleaseNotes text={u.whats_new} />
          </div>
        {/if}
        <div class="task__text task__text--quiet">
          This device has {u.installed}. Installing stops playback. The player restarts, and the device too
          if the system needs it.
        </div>
        <div class="ask__buttons">
          <button type="button" class="btn" onclick={close}>Not now</button>
          <button type="button" class="btn btn--confirm" onclick={choose}>Update</button>
        </div>
      {:else if u.state === 'failed'}
        <div class="ask__title">Could not check</div>
        <div class="warn"><span class="warn__mark">!</span><span class="warn__text">{u.message}</span></div>
        <div class="ask__buttons"><button type="button" class="btn btn--confirm" onclick={close}>OK</button></div>
      {:else}
        <div class="ask__title">Up to date</div>
        <div class="task__text">This device has {u.installed}, the newest release.</div>
        <div class="ask__buttons"><button type="button" class="btn btn--confirm" onclick={close}>OK</button></div>
      {/if}
    {:else if phase === 'confirm'}
      <div class="ask__title">Update to {u.release}?</div>
      <div class="warn">
        <span class="warn__mark">!</span>
        <span class="warn__text">Playback stops during the update. Nothing resumes afterwards.</span>
      </div>
      <div class="ask__buttons">
        <button type="button" class="btn" onclick={close}>Cancel</button>
        <button type="button" class="btn btn--confirm" onclick={go}>Continue</button>
      </div>
    {:else if phase === 'progress'}
      <div class="ask__title">Updating to {u.release ?? '…'}</div>
      <UpdateSteps update={u} />
      <div class="task__text task__text--quiet">
        {#if $connection !== 'open'}The player is restarting. Reconnecting…{:else}The update carries on if you close this.{/if}
      </div>
      <div class="ask__buttons"><button type="button" class="btn" onclick={close}>Hide</button></div>
    {:else}
      {#if u.state === 'done'}
        <div class="ask__title">Updated to {u.installed}</div>
        {#if u.whats_new}
          <div class="notes">
            <ReleaseNotes text={u.whats_new} />
          </div>
        {/if}
        <div class="task__text task__text--quiet">Everything is paused or disconnected.</div>
      {:else}
        <div class="ask__title">Did not update</div>
        <UpdateSteps update={u} />
        <div class="warn"><span class="warn__mark">!</span><span class="warn__text">{u.message}</span></div>
      {/if}
      <div class="ask__buttons"><button type="button" class="btn btn--confirm" onclick={close}>OK</button></div>
    {/if}
  </div>
</div>

<style>
  /* Settings' own centred dialog (ADR-0106), its buttons and its warning. */
  .ask {
    position: fixed;
    inset: 0;
    z-index: 60;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
    background: var(--bg-scrim);
  }
  .ask__card {
    width: min(560px, 100%);
    max-height: calc(100% - 32px);
    overflow-y: auto;
    padding: 24px 22px 28px;
    border-radius: var(--r-xl);
    background: var(--bg-panel);
    display: flex;
    flex-direction: column;
    gap: 18px;
    box-sizing: border-box;
  }
  .ask__title {
    font-size: 20px;
    font-weight: 700;
  }
  .task__text {
    font-size: 17px;
    line-height: 1.4;
  }
  .task__text--quiet {
    font-size: 15px;
    color: var(--ink-muted);
  }
  .task__bar {
    display: block;
    height: 6px;
    border-radius: 3px;
    background: rgba(233, 238, 242, 0.12);
    overflow: hidden;
  }
  .task__bar span {
    display: block;
    height: 100%;
    background: var(--accent-lms);
  }
  .task__bar--busy span {
    width: 30%;
    animation: busy 1.2s ease-in-out infinite;
  }
  .notes {
    padding: 14px 16px;
    border-radius: 14px;
    background: rgba(233, 238, 242, 0.05);
    border: 1px solid rgba(233, 238, 242, 0.12);
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .warn {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 16px 18px;
    border-radius: 14px;
    background: rgba(224, 167, 88, 0.12);
    border: 1px solid rgba(224, 167, 88, 0.42);
  }
  .warn__mark {
    flex-shrink: 0;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: var(--accent-warn);
    color: var(--bg-panel);
    font-weight: 700;
    font-size: 17px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .warn__text {
    flex: 1;
    min-width: 0;
    font-size: 15px;
    line-height: 1.45;
  }
  .ask__buttons {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
  }
  .btn {
    flex: 1;
    height: 58px;
    border-radius: 15px;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.14);
    color: var(--ink);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 17px;
    font-weight: 600;
  }
  .btn:active { background: rgba(233, 238, 242, 0.2); }
  .btn--confirm {
    font-weight: 700;
    background: rgba(126, 214, 188, 0.16);
    border-color: rgba(126, 214, 188, 0.4);
    color: var(--accent-lms);
  }
  @keyframes busy {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(340%); }
  }
</style>
