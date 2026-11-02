<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0166, design/source/22 (*Undo confirm*, phone): *Undo the group?*,
  who plays on their own again and where the music stays, Cancel and Undo
  group (amber). It asks first.
-->
<script>
  import { group, undoBody, undoGroup } from '../../lib/group.svelte.js';

  let { open = false, onclose = () => {}, onsay = () => {} } = $props();
  const g = $derived($group);
  let busy = $state(false);

  async function undo() {
    if (busy) return;
    busy = true;
    try {
      await undoGroup();
      onclose();
    } catch (error) {
      onsay(`Not undone: ${error.message}`);
    } finally {
      busy = false;
    }
  }
</script>

{#if open && g}
  <div class="scrim" role="presentation" onclick={onclose}></div>
  <div class="confirm" role="alertdialog" aria-label="Undo the group?">
    <div class="title">Undo the group?</div>
    <div class="body">{undoBody(g)}</div>
    <div class="buttons">
      <button class="cancel" type="button" onclick={onclose}>Cancel</button>
      <button class="undo" type="button" disabled={busy} onclick={undo}>Undo group</button>
    </div>
  </div>
{/if}

<style>
  .scrim {
    position: absolute;
    inset: 0;
    z-index: 60;
    background: var(--c-dark-04080a-60);
  }
  .confirm {
    position: absolute;
    z-index: 61;
    left: 16px;
    right: 16px;
    top: 50%;
    transform: translateY(-50%);
    background: var(--bg-panel);
    border: 1px solid var(--c-ink-14);
    border-radius: var(--r-20);
    box-shadow: 0 18px 48px var(--c-black-55);
    padding: 22px 18px 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .title {
    font-size: 19px;
    font-weight: 700;
  }
  .body {
    font-size: 15px;
    line-height: 1.45;
    color: var(--ink-muted);
    text-wrap: pretty;
  }
  .buttons {
    display: flex;
    gap: 8px;
    margin-top: 8px;
  }
  button {
    flex: 1;
    height: 48px;
    border-radius: var(--r-14);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-ui);
    font-size: 16px;
    white-space: nowrap;
    cursor: pointer;
  }
  .cancel {
    background: var(--ink-fill);
    border: 1px solid var(--c-ink-14);
    color: var(--ink);
    font-weight: 600;
  }
  .undo {
    background: var(--group-undo-ground);
    border: 1px solid var(--group-undo-line);
    color: var(--group-undo-ink);
    font-weight: 700;
  }
  button:active {
    transform: scale(0.97);
  }
</style>
