<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **Undo the group?**, on the panel (ADR-0166; design/source/22, S4-3): it
  asks first, and says the music stays on the leader.
-->
<script>
  import { undoBody, undoGroup } from '../../lib/group.svelte.js';

  let { open, g = null, oncancel, ondone, onflash } = $props();

  async function undo() {
    try {
      await undoGroup();
      ondone?.();
    } catch (error) {
      onflash?.(`The group was not undone: ${error.message}`);
      oncancel?.();
    }
  }
</script>

<div class="scrim" class:is-open={open} role="presentation" onclick={oncancel}></div>
<div class="card" class:is-open={open} role="alertdialog" aria-label="Undo the group?" aria-hidden={!open} inert={!open}
     ondpadback={(event) => { event.preventDefault(); oncancel?.(); }}>
  <div class="title">Undo the group?</div>
  <div class="body">{g ? undoBody(g) : ''}</div>
  <div class="actions">
    <button class="button" type="button" data-dpad-back onclick={oncancel}>Cancel</button>
    <button class="button button--undo" type="button" data-dpad-main onclick={undo}>Undo group</button>
  </div>
</div>

<style>
  .scrim {
    position: absolute;
    inset: 0;
    z-index: 16;
    background: rgba(8, 12, 16, 0.62);
    transition: opacity 200ms ease;
    opacity: 0;
    pointer-events: none;
  }
  .scrim.is-open { opacity: 1; pointer-events: auto; }
  .card {
    position: absolute;
    left: 50%;
    top: 50%;
    z-index: 17;
    width: 560px;
    background: var(--bg-panel);
    border: 1px solid rgba(233, 238, 242, 0.14);
    border-radius: 22px;
    padding: 26px;
    box-sizing: border-box;
    box-shadow: 0 34px 90px rgba(0, 0, 0, 0.6);
    display: flex;
    flex-direction: column;
    gap: 12px;
    transition: transform 200ms cubic-bezier(0.2, 0.8, 0.2, 1), opacity 180ms ease;
    transform: translate(-50%, -50%) scale(0.96);
    opacity: 0;
    pointer-events: none;
  }
  .card.is-open {
    transform: translate(-50%, -50%) scale(1);
    opacity: 1;
    pointer-events: auto;
  }
  .title { font-size: 25px; font-weight: 700; }
  .body { font-size: 17px; line-height: 1.45; color: rgba(233, 238, 242, 0.72); text-wrap: pretty; }
  .actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 10px; }
  .button {
    font: inherit;
    height: 58px;
    padding: 0 22px;
    border-radius: 15px;
    box-sizing: border-box;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.14);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 17px;
    font-weight: 600;
    white-space: nowrap;
    flex-shrink: 0;
    color: var(--ink);
  }
  .button:active { transform: scale(0.95); }
  .button--undo {
    background: var(--group-undo-ground);
    border-color: var(--group-undo-line);
    color: var(--group-undo-ink);
    font-weight: 700;
  }
</style>
