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
  import { update, metadata, connection, updateAsked } from '../lib/state.js';
  import { runSetting } from '../lib/settings.js';
  import UpdateSteps from './UpdateSteps.svelte';
  import ReleaseHistory from './ReleaseHistory.svelte';

  //: `check` runs a check first - the tile's *Check for updates* and, since
  //: 2026-10-13, its *Update…* too, so a release the channel has moved past
  //: is never offered; `available` opens on the waiting release as the
  //: updater last wrote it; `progress` reopens an install already running.
  let { start = 'check', onclose } = $props();

  const CHECK_TIMEOUT_MS = 90_000;

  //: **A check asked for while an update runs is not sent** (George,
  //: 2026-10-12, answer 5: "Yes"). The updater holds its status lock for the
  //: whole install and leaves a check unanswered, so the modal waited out
  //: CHECK_TIMEOUT_MS and then said the player had not answered. It shows
  //: the install instead, and says that is what is happening.
  const running = !!$update?.active;
  let phase = $state(start === 'progress' || (start === 'check' && running) ? 'progress'
    : start === 'check' ? 'checking' : 'answer');
  //: True when a check found an update already under way - the progress
  //: view says so, and follows that install to its end as `progress` does.
  let busy = $state(start === 'check' && running);
  //: What the updater's file said when the ask went out. **An answer is a
  //: change from it**, not a time after the phone's clock: `at` is the
  //: player's clock, to the second, and a player even two seconds behind the
  //: phone never answered - the check timed out, the install never ended
  //: (code review, 2026-10-12). A Pi has no clock of its own to keep it right.
  let asked = $state(null);
  let from = $state($update?.installed ?? null);
  let timedOut = $state(false);

  const u = $derived($update ?? {});
  const playing = $derived($metadata?.transport === 'playing');
  const fresh = $derived(!!u.at && !!asked && (u.at !== asked.at || u.state !== asked.state));
  const answered = $derived(fresh && ['current', 'available', 'failed'].includes(u.state));

  onMount(() => {
    if (start !== 'check' || busy) return;
    asked = { at: u.at, state: u.state };
    runSetting('update_check');
    const id = setTimeout(() => (timedOut = true), CHECK_TIMEOUT_MS);
    return () => clearTimeout(id);
  });

  // The check's answer, once the updater has written one newer than the ask.
  $effect(() => {
    if (phase !== 'checking') return;
    // An install that started while the check waited: the updater will not
    // answer the check until it is over, so show the install.
    if (u.active) {
      busy = true;
      phase = 'progress';
    } else if (answered) phase = 'answer';
    else if (timedOut) phase = 'answer';
  });

  // The install's end: done, or failed and back where it was.
  $effect(() => {
    if (phase === 'progress' && !u.active && ['done', 'failed'].includes(u.state) && (fresh || start === 'progress' || busy)) {
      phase = 'end';
    }
  });

  function choose() {
    if (playing) phase = 'confirm';
    else go();
  }

  function go() {
    from = u.installed ?? from;
    asked = { at: u.at, state: u.state };
    phase = 'progress';
    updateAsked.set(Date.now());
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
      {#if timedOut && !answered}
        <div class="ask__title">Could not check for updates</div>
        <div class="task__text">The player did not answer in time. Try again in a minute.</div>
        <div class="ask__buttons"><button type="button" class="btn btn--confirm" onclick={close}>OK</button></div>
      {:else if u.state === 'available'}
        <div class="ask__title">{u.release} is available</div>
        {#if u.whats_new || u.whats_new_all?.length}
          <div class="notes">
            <ReleaseHistory update={u} />
          </div>
        {/if}
        <div class="task__text task__text--quiet">
          This player has {u.installed}. Installing stops playback. The player restarts, and the device too
          if the system needs it.
        </div>
        <div class="ask__buttons">
          <button type="button" class="btn" onclick={close}>Not now</button>
          <button type="button" class="btn btn--confirm" onclick={choose}>Update</button>
        </div>
      {:else if u.state === 'failed'}
        <div class="ask__title">Could not check for updates</div>
        <div class="warn"><span class="warn__mark">!</span><span class="warn__text">{u.message}</span></div>
        <div class="ask__buttons"><button type="button" class="btn btn--confirm" onclick={close}>OK</button></div>
      {:else}
        <div class="ask__title">Up to date</div>
        <div class="task__text">This player has {u.installed}, the newest release.</div>
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
      {#if busy}
        <div class="task__text">An update is being installed. Check for updates again once it has finished.</div>
      {/if}
      <UpdateSteps update={u} />
      <div class="task__text task__text--quiet">
        {#if $connection !== 'open'}The player is restarting. Reconnecting…{:else}The update carries on if you close this.{/if}
      </div>
      <div class="ask__buttons"><button type="button" class="btn" onclick={close}>Hide</button></div>
    {:else}
      {#if u.state === 'done'}
        <!-- ADR-0110, 2026-10-05: every step ticked, not the notes again. -->
        <div class="ask__title">Updated to {u.installed}</div>
        <UpdateSteps update={u} />
        <div class="task__text task__text--quiet">Everything is paused or disconnected.</div>
      {:else}
        <div class="ask__title">Did not update</div>
        <UpdateSteps update={u} />
        <div class="warn"><span class="warn__mark">!</span><span class="warn__text">{u.message}</span></div>
      {/if}
      <div class="ask__buttons"><button type="button" class="btn btn--confirm" onclick={close}>{u.state === 'done' ? 'Done' : 'OK'}</button></div>
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
