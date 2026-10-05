<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0110 §6: the panel while it updates. One full-screen message that
  takes no input, from the start until the update has finished or gone back.
  The core restarts in the middle of it; App keeps this up while the socket
  reconnects, so no normal screen shows in between. Sized like the setup
  screens: read from 1-2 m, nothing under 24 px.
-->
<script>
  import mark from '../assets/gexis-mark.svg';
  import UpdateSteps from './UpdateSteps.svelte';
  import ReleaseNotes from './ReleaseNotes.svelte';

  //: `outcome` is null while it runs, then `done` or `failed` for the few
  //: seconds App shows it before going on.
  let { update = null, reconnecting = false, outcome = null, oncontinue = null } = $props();

  const restarting = $derived(update?.reboot && update?.steps?.restart === 'active');
</script>

<div
  class="lock"
  role="alertdialog"
  aria-modal="true"
  aria-live="polite"
  aria-label="Updating"
  onpointerdown={(e) => { e.preventDefault(); e.stopPropagation(); }}
>
  <header class="lock__head">
    <img src={mark} alt="" width="40" height="40" />
    <span class="lock__crumb">Software update</span>
  </header>

  <div class="lock__main" class:lock__main--notes={outcome === 'done' && update?.whats_new}>
    {#if outcome === 'done'}
      <h1>Updated to {update?.installed}</h1>
      {#if update?.whats_new}<div class="lock__notes"><ReleaseNotes text={update.whats_new} large /></div>{/if}
      <div class="lock__foot">
        <p class="lead">Everything is paused or disconnected.</p>
        {#if update?.whats_new && oncontinue}
          <!-- With notes the screen waits for this (or two minutes), so they
               can be read (2026-10-05). -->
          <button type="button" class="lock__continue" onclick={oncontinue}>Continue</button>
        {/if}
      </div>
    {:else if outcome === 'failed'}
      <h1>Did not update</h1>
      <p class="lead">Back on {update?.installed}. {update?.message ?? ''}</p>
    {:else if restarting}
      <h1>Restarting the device</h1>
      <p class="lead">It comes back on {update?.release}.</p>
    {:else}
      <h1>Updating to {update?.release ?? '…'}</h1>
      <div class="lock__steps"><UpdateSteps {update} large /></div>
      <p class="lead lead--warn">
        {reconnecting ? 'The player is restarting…' : "Don't switch off."}
      </p>
    {/if}
  </div>
</div>

<style>
  .lock {
    position: fixed;
    inset: 0;
    z-index: 100;
    display: flex;
    flex-direction: column;
    padding: 30px 56px 36px;
    box-sizing: border-box;
    background: var(--bg-base);
    color: var(--ink);
    font-family: var(--font-ui);
    user-select: none;
    touch-action: none;
  }
  .lock__head {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .lock__crumb {
    font-family: var(--font-mono);
    font-size: 15px;
    letter-spacing: var(--track-label);
    text-transform: uppercase;
    color: var(--ink-muted);
  }
  .lock__main {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 34px;
    text-align: center;
  }
  h1 {
    margin: 0;
    font-size: 60px;
    font-weight: 800;
    letter-spacing: -0.01em;
  }
  .lock__steps {
    text-align: left;
    min-width: 520px;
  }
  /* **Long notes scroll** (George, 2026-10-05: 0.9.0's ran off the screen
     and could not be moved). Their own scroll box, so a vertical swipe
     works here while the rest of the lock still refuses touch: a browser
     reads touch-action only up to the nearest scroll box. */
  .lock__notes {
    max-width: 900px;
    flex: 0 1 auto;
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
    touch-action: pan-y;
    text-align: left;
    padding-right: 8px;
  }
  /* **With notes, the notes get the height**: a smaller title on a short
     screen, and the line and Continue on one row below them - on a
     1280x400 bar the notes had 11 px otherwise (measured 2026-10-05). */
  .lock__main--notes {
    justify-content: flex-start;
    gap: min(34px, 3.5vh);
  }
  .lock__main--notes h1 {
    font-size: min(60px, 9vh);
    flex: none;
  }
  .lock__main--notes .lock__notes {
    flex: 1 1 auto;
  }
  .lock__main--notes .lead {
    font-size: min(30px, 5.5vh);
  }
  .lock__foot {
    flex: none;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 14px 28px;
  }
  .lock__continue {
    flex: none;
    padding: 14px 40px;
    border: 0;
    border-radius: var(--r-pill, 999px);
    background: var(--accent-lms);
    color: var(--bg-base);
    font: 700 22px var(--font-ui);
    touch-action: manipulation;
  }
  .lead {
    margin: 0;
    font-size: 30px;
    color: var(--ink-body);
  }
  .lead--warn {
    color: var(--accent-warn);
    font-size: 26px;
  }
</style>
