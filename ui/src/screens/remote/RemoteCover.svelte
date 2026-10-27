<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0164 C4: the remote's cover (design/source/21), as the panel's - the
  renderer's, or the one the core found for the track (ADR-0081); without
  one, the panel's *artwork pending* glyph (Bluetooth's, as drawn); nothing
  playing, the note. `big` is the layout without a screen. Its size is the
  parent's; an inner ring lies over it.
-->
<script>
  import { FILLED } from './icons.js';

  let { artwork = null, hasTrack = false, big = false, onfailed = () => {} } = $props();
</script>

<div class="cover" class:is-big={big}>
  {#if hasTrack && artwork}
    <img src={artwork} alt="" onerror={() => onfailed(artwork)} />
  {:else if hasTrack}
    <div class="pending">
      <span class="pending__ring"><span class="pending__dot"></span></span>
      <span class="pending__label">artwork pending</span>
    </div>
  {:else}
    <svg class="note" viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.note} /></svg>
  {/if}
  <span class="ring" aria-hidden="true"></span>
</div>

<style>
  .cover {
    position: relative;
    width: 100%;
    height: 100%;
    border-radius: var(--remote-cover-radius);
    overflow: hidden;
    background: rgba(233, 238, 242, 0.07);
    display: grid;
    place-items: center;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
    color: rgba(233, 238, 242, 0.5);
    --ring: 48px;
    --dot: 12px;
    --label: 10px;
    --label-spacing: 0.12em;
    --gap: 10px;
    --note: 44px;
  }
  .cover.is-big {
    border-radius: 24px;
    box-shadow: 0 18px 48px rgba(0, 0, 0, 0.5);
    --ring: 110px;
    --dot: 26px;
    --label: 13px;
    --label-spacing: 0.16em;
    --gap: 20px;
    --note: 72px;
  }
  img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
  .pending {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--gap);
    background: linear-gradient(160deg, rgba(126, 214, 188, 0.07), rgba(242, 164, 143, 0.06)), #17242d;
  }
  .pending__ring {
    width: var(--ring);
    height: var(--ring);
    border-radius: 50%;
    border: 2px solid rgba(126, 214, 188, 0.4);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .pending__dot {
    width: var(--dot);
    height: var(--dot);
    border-radius: 50%;
    background: rgba(126, 214, 188, 0.45);
  }
  .pending__label {
    font-family: var(--font-mono);
    font-size: var(--label);
    letter-spacing: var(--label-spacing);
    color: rgba(233, 238, 242, 0.6);
    text-transform: uppercase;
    white-space: nowrap;
  }
  .note {
    width: var(--note);
    height: var(--note);
    fill: currentColor;
  }
  .ring {
    position: absolute;
    inset: 0;
    border-radius: inherit;
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
    pointer-events: none;
  }
</style>
