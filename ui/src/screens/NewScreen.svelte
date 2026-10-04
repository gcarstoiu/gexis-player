<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **A different screen is attached** (ADR-0109, amended 2026-10-03; George:
  "Upon boot couldn't we detect that a new display was connected and give the
  user the choice to keep the new resolution?"). Asked once at start, on the
  panel and on a phone, in the look of Settings' sheets:

  - a recognised tested model by name, with *Use it*: the usual restart and
    Keep, which goes back by itself if the new screen's touch does not work;
  - anything else by its size, with *Choose*: the screen list opens;
  - *Not now*: that screen is not asked about again.
-->
<script>
  let { question, onanswer } = $props();

  const known = $derived(!!question?.label);
  const size = $derived(String(question?.size ?? '').replace('x', ' × '));
  const title = $derived(known ? `A ${question.name} is attached` : `A ${size || 'different'} screen is attached`);
  const text = $derived(known
    ? 'The player is set up for another screen. Use this one? It restarts on it, and asks you to keep it.'
    : 'The player is set up for another screen. Choose this one from the list of screens?');
</script>

<div class="scrim" role="presentation">
  <div class="sheet" role="dialog" aria-modal="true" aria-label={title}>
    <div class="sheet__title">{title}</div>
    <div class="sheet__note">{text}</div>
    <div class="sheet__actions">
      <button class="btn" type="button" onclick={() => onanswer('later')}>Not now</button>
      <button class="btn btn--confirm" type="button" onclick={() => onanswer(known ? 'use' : 'choose')}>
        {known ? 'Use it' : 'Choose'}
      </button>
    </div>
  </div>
</div>

<style>
  .scrim {
    position: fixed;
    inset: 0;
    z-index: 60;
    background: rgba(8, 12, 16, 0.62);
  }
  .sheet {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: calc(100% - 44px);
    max-width: 560px;
    background: var(--bg-panel);
    border: 1px solid rgba(233, 238, 242, 0.14);
    border-radius: 22px;
    box-shadow: 0 30px 70px rgba(0, 0, 0, 0.5);
    padding: 26px;
    display: flex;
    flex-direction: column;
    gap: 18px;
    color: var(--ink);
  }
  .sheet__title {
    font-size: 22px;
    font-weight: 600;
    line-height: 1.25;
  }
  .sheet__note {
    font-size: 15px;
    line-height: 1.5;
    color: rgba(233, 238, 242, 0.6);
  }
  .sheet__actions {
    display: flex;
    gap: 12px;
  }
  .btn {
    flex: 1;
    height: 58px;
    border-radius: 15px;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.14);
    color: var(--ink);
    font-family: inherit;
    font-size: 17px;
    font-weight: 600;
  }
  .btn:active {
    background: rgba(233, 238, 242, 0.2);
  }
  .btn--confirm {
    background: rgba(126, 214, 188, 0.16);
    border-color: rgba(126, 214, 188, 0.4);
    color: var(--accent-lms);
  }
</style>
