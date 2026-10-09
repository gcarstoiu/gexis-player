<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **A factory reset under way** (ADR-0132). George, 2026-10-09, after holding
  the button on a phone and seeing nothing: "Something needs to be shown to
  the user so he knows that the device is being reset." Over everything, on
  the panel and every phone, with no way out: the player is going. A phone
  keeps it after the connection drops, and says how to reach setup from
  there, because this page cannot follow the player into it.
-->
<script>
  let { surface = 'panel' } = $props();
</script>

<div class="reset" role="alertdialog" aria-modal="true" aria-label="Resetting to factory settings">
  <div class="card">
    <div class="title">Resetting to factory settings</div>
    {#if surface === 'panel'}
      <div class="note">The player is clearing everything and restarting. Setup starts here in a few minutes. Don't switch off.</div>
    {:else}
      <div class="note">The player is clearing everything and restarting. This page stops working now; in a few minutes the player's screen shows setup.</div>
      <div class="note">
        To set it up from this phone: join the Wi-Fi <b>gexis-setup</b> (the password is on the player's screen, or
        <b>gexis-setup</b> on a player without one), then open <b>http://10.42.0.1:8090</b>. With a network cable
        plugged in, open <b>http://raspberrypi.local:8090</b> instead.
      </div>
    {/if}
    <div class="bar"><span></span></div>
  </div>
</div>

<style>
  .reset {
    position: fixed;
    inset: 0;
    z-index: 200;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 22px;
    background: rgba(8, 12, 16, 0.92);
  }
  .card {
    width: 100%;
    max-width: 620px;
    max-height: 100%;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 28px;
    border-radius: 22px;
    background: var(--bg-panel);
    border: 1px solid rgba(224, 167, 88, 0.35);
    box-shadow: 0 30px 70px rgba(0, 0, 0, 0.5);
    color: var(--ink);
  }
  .title {
    font-size: 26px;
    font-weight: 600;
    color: #e0a758;
  }
  .note {
    font-size: 17px;
    line-height: 1.45;
    color: var(--ink-dim, #9fb0bd);
    overflow-wrap: anywhere;
  }
  .note b {
    color: var(--ink);
    font-weight: 600;
  }
  .bar {
    height: 6px;
    border-radius: 3px;
    background: rgba(233, 238, 242, 0.1);
    overflow: hidden;
  }
  .bar span {
    display: block;
    width: 30%;
    height: 100%;
    border-radius: 3px;
    background: rgba(224, 167, 88, 0.7);
    animation: resetWait 1600ms ease-in-out infinite;
  }
  @keyframes resetWait {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(340%); }
  }
  /* The bar: 320 px high - the essentials only, in one block. */
  @media (max-height: 420px) {
    .card { padding: 18px 22px; gap: 10px; }
    .title { font-size: 22px; }
    .note { font-size: 15px; }
  }
</style>
