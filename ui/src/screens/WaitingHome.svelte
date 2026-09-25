<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The panel's root with LMS off** (ADR-0079). George, 2026-09-25: *"The home
  screen is used only to signal that renderers are waiting for a connection -
  the current bottom bar when no renderer is connected. That bar scales the
  entire screen... The settings tile becomes a settings icon in the upper right
  corner."*

  There is no library to sit under and no tiles to sit beside, so this is the
  waiting marks and one button. The marks themselves are `WaitingServices` in
  its `full` shape - the same component the library root uses as a footer, so
  the design's colours, sizes and ring delays have one home.
-->
<script>
  import WaitingServices from './WaitingServices.svelte';
  import { pressing } from '../lib/press.svelte.js';

  let { availability = {}, onsettings } = $props();

  const press = pressing();
  // Every source switched off is reachable now that the rows work (ADR-0077),
  // and an empty screen with no way off it would be the panel bricking itself.
  // The icon stays whatever happens; this only says why the screen is bare.
  const none = $derived(!['lms', 'spotify', 'bluetooth'].some((id) => availability[id]));
</script>

<div class="waithome">
  <button
    class="corner"
    class:is-pressed={press.is('settings')}
    type="button"
    aria-label="Settings"
    onpointerdown={() => press.down('settings')}
    onpointerup={press.up}
    onpointercancel={press.up}
    onclick={() => press.act(onsettings)}
  >
    <span class="i-sliders"><i></i><b></b><i></i><b></b></span>
  </button>

  {#if none}
    <div class="none">
      <div class="none__head">No sources</div>
      <div class="none__note">Every source is switched off. Settings, top right.</div>
    </div>
  {:else}
    <WaitingServices {availability} full />
  {/if}
</div>

<style>
  .waithome {
    position: absolute;
    inset: 0;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  /* The tile's glyph at the tile's own size, in the corner the tile is not in
     any more. Inset matches the panel's other edge controls. */
  .corner {
    position: absolute;
    top: 26px;
    right: 26px;
    width: 64px;
    height: 64px;
    border-radius: 18px;
    border: 1px solid rgba(233, 238, 242, 0.14);
    background: var(--ink-fill);
    color: var(--ink);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    cursor: pointer;
    transition: transform 120ms ease, background 120ms ease;
  }
  .corner.is-pressed {
    transform: scale(0.94);
    background: rgba(233, 238, 242, 0.16);
  }

  /* Two sliders: a track each with a handle at a different position, which is
     the library tile's `glyph--sliders` at this size. */
  .i-sliders {
    position: relative;
    width: 26px;
    height: 18px;
    display: block;
  }
  .i-sliders i,
  .i-sliders b {
    position: absolute;
    display: block;
  }
  .i-sliders i {
    left: 0;
    width: 26px;
    height: 2px;
    border-radius: 1px;
    background: currentColor;
    opacity: 0.55;
  }
  .i-sliders i:first-child {
    top: 4px;
  }
  .i-sliders i:nth-child(3) {
    top: 12px;
  }
  .i-sliders b {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: currentColor;
  }
  .i-sliders b:nth-child(2) {
    top: 1.5px;
    left: 6px;
  }
  .i-sliders b:nth-child(4) {
    top: 9.5px;
    left: 15px;
  }

  .none {
    text-align: center;
    max-width: 560px;
    padding: 0 40px;
  }
  .none__head {
    font-size: 30px;
    font-weight: 700;
    color: var(--ink);
  }
  .none__note {
    margin-top: 12px;
    font-size: 17px;
    color: var(--ink-quiet);
  }
</style>
