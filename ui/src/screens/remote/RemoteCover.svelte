<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0164 C4: the remote's cover (design/source/21), as the panel's - the
  renderer's, or the one the core found for the track (ADR-0081); without
  one, the panel's *artwork pending* glyph (Bluetooth's, as drawn); nothing
  playing, the note. `big` is the layout without a screen. Its size is the
  parent's; an inner ring lies over it. A station (ADR-0180, design/source/31
  §4): its logo on the plate where no cover came - one smaller than 64 px at
  its own size, never enlarged - and with neither, the radio mark on the
  radio's tint.
-->
<script>
  import { FILLED } from './icons.js';
  import { active } from '../../lib/state.js';
  import { radio } from '../../lib/radio.js';
  import RadioMark from '../../lib/RadioMark.svelte';

  let { artwork = null, hasTrack = false, big = false, onfailed = () => {} } = $props();

  const NATIVE_MAX = 64;
  const logo = $derived($active === 'radio' && !!artwork && artwork === $radio?.station?.logo);
  let natural = $state(null);
  $effect(() => {
    void artwork;
    natural = null;
  });
  const tiny = $derived(natural !== null && natural < NATIVE_MAX);
</script>

<div class="cover" class:is-big={big}>
  {#if hasTrack && logo}
    <div class="plate" class:is-tiny={tiny}>
      <img src={artwork} alt="" style:width={tiny ? `${natural}px` : null} style:height={tiny ? `${natural}px` : null}
           onload={(e) => (natural = Math.max(e.currentTarget.naturalWidth, e.currentTarget.naturalHeight) || null)}
           onerror={() => onfailed(artwork)} />
    </div>
  {:else if hasTrack && artwork}
    <img src={artwork} alt="" onerror={() => onfailed(artwork)} />
  {:else if hasTrack && $active === 'radio'}
    <div class="station"><RadioMark size={big ? 120 : 56} stroke={big ? 1.6 : 2} /></div>
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
    background: var(--ink-fill);
    display: grid;
    place-items: center;
    box-shadow: 0 12px 32px var(--c-black-40);
    color: var(--ink-tab-off);
    --ring: 48px;
    --dot: 12px;
    --label: 10px;
    --label-spacing: 0.12em;
    --gap: 10px;
    --note: 44px;
  }
  .cover.is-big {
    border-radius: var(--r-card);
    box-shadow: 0 18px 48px var(--c-black-50);
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
    background: linear-gradient(160deg, var(--c-lms-07), var(--c-artist-06)), var(--bg-well);
  }
  .plate {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--station-logo-plate);
  }
  .plate img {
    object-fit: contain;
  }
  .plate.is-tiny img {
    position: static;
  }
  .station {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--station-fallback-ground);
    box-shadow: inset 0 0 0 1px var(--station-fallback-line);
    border-radius: inherit;
  }
  .pending__ring {
    width: var(--ring);
    height: var(--ring);
    border-radius: 50%;
    border: 2px solid var(--c-lms-40);
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .pending__dot {
    width: var(--dot);
    height: var(--dot);
    border-radius: 50%;
    background: var(--c-lms-45);
  }
  .pending__label {
    font-family: var(--font-mono);
    font-size: var(--label);
    letter-spacing: var(--label-spacing);
    color: var(--ink-quiet);
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
    box-shadow: inset 0 0 0 1px var(--c-white-08);
    pointer-events: none;
  }
</style>
