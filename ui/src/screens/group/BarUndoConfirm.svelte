<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  *Undo the group?* on the bar (ADR-0166; design/source/22, S4-4): asks
  first; the music stays on the leader. 640 wide, radius 22, padding 26;
  Cancel and Undo group 60 tall.
-->
<script>
  import { undoBody, undoGroup } from '../../lib/group.svelte.js';

  let { open, g, onclose, onerror = () => {} } = $props();

  //: The leader gone, there is no music to keep (the design's `undoBody`).
  const body = $derived(!g ? '' : g.silent ? undoBody(g).replace(/ The music stays on .*$/, '') : undoBody(g));
  async function undo() {
    onclose?.();
    try {
      await undoGroup();
    } catch (error) {
      onerror(error.message);
    }
  }
</script>

{#if open && g}
  <div class="scrim" role="presentation" onclick={onclose}></div>
  <div class="confirm" role="alertdialog" aria-label="Undo the group?" data-dpad-layer
    ondpadback={(event) => { event.preventDefault(); onclose?.(); }}>
    <div class="title">Undo the group?</div>
    <div class="body">{body}</div>
    <div class="buttons">
      <button class="btn" type="button" onclick={onclose}>Cancel</button>
      <button class="btn btn--undo" type="button" data-dpad-main onclick={undo}>Undo group</button>
    </div>
  </div>
{/if}

<style>
  .scrim {
    position: absolute;
    inset: 0;
    z-index: 40;
    background: rgba(8, 12, 16, 0.62);
  }
  .confirm {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    z-index: 41;
    width: 640px;
    background: var(--bg-panel);
    border: 1px solid rgba(233, 238, 242, 0.14);
    border-radius: 22px;
    padding: 26px;
    box-sizing: border-box;
    box-shadow: 0 34px 90px rgba(0, 0, 0, 0.6);
    display: flex;
    flex-direction: column;
    gap: 10px;
    text-transform: none;
    letter-spacing: normal;
    color: var(--ink);
  }
  .title { font-size: 26px; font-weight: 700; }
  .body {
    font-size: 18px;
    line-height: 1.45;
    color: rgba(233, 238, 242, 0.72);
    text-wrap: pretty;
  }
  .buttons {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 10px;
  }
  .btn {
    height: 60px;
    padding: 0 22px;
    border-radius: 15px;
    box-sizing: border-box;
    background: var(--ink-fill);
    border: 1px solid rgba(233, 238, 242, 0.14);
    color: var(--ink);
    display: flex;
    align-items: center;
    justify-content: center;
    font: inherit;
    font-size: 18px;
    font-weight: 600;
    white-space: nowrap;
    flex-shrink: 0;
  }
  .btn:active { transform: scale(0.95); }
  .btn--undo {
    background: var(--group-undo-ground);
    border-color: var(--group-undo-line);
    color: var(--group-undo-ink);
    font-weight: 700;
  }
</style>
