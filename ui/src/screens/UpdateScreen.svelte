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
  let { update = null, reconnecting = false, outcome = null } = $props();

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

  <div class="lock__main">
    {#if outcome === 'done'}
      <h1>Updated to {update?.installed}</h1>
      {#if update?.whats_new}<div class="lock__notes"><ReleaseNotes text={update.whats_new} large /></div>{/if}
      <p class="lead">Everything is paused or disconnected.</p>
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
  .lock__notes { max-width: 900px; }
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
