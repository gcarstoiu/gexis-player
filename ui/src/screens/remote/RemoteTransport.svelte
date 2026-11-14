<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0164: the remote's transport (design/source/21): previous, play/pause
  and next - no shuffle or repeat on the phone (D2) - in the screen layout's
  sizes beside the cover or, `big`, the larger ones of a player without a
  screen. What the renderer does not declare is left out and the row
  re-centres (ADR-0037); what it declares but cannot do now is dimmed.
  Previous restarts the track or goes back one as the renderer's own button
  does (Finding 028). Nothing playing: the row at 0.38, inert.

  A station (ADR-0180, design/source/31 H17-H22): Stop, not Pause - a
  station stops, and Play starts it afresh - and the spinner while it
  connects or reconnects. Previous and Next step through the favourites,
  at 0.4 for a station that is not one. The heart sits at the row's right
  beside the cover (`heart="end"`), or at its left without a screen
  (`heart="start"`).
-->
<script>
  import { active, available, capabilities, metadata, sendTransport } from '../../lib/state.js';
  import { playToggle } from '../../lib/playToggle.svelte.js';
  import { addFavourite, radio, removeFavourite } from '../../lib/radio.js';
  import HeartIcon from '../../lib/HeartIcon.svelte';
  import { FILLED } from './icons.js';
  import { RADIO } from './radio/glyphs.js';

  let { big = false, heart = null, onsay = () => {} } = $props();

  //: Nothing playing: the whole row as the design draws it, dimmed and inert.
  const ALL = ['play', 'pause', 'next', 'previous'];
  const declared = $derived($active ? ($capabilities?.[$active]?.controls ?? []) : ALL);
  //: Nothing playing, the row is dimmed once as a whole, not each button again.
  const can = (command) => !$active || $available.includes(command);
  const toggle = playToggle(() => $metadata?.transport, () => $active);
  const hasTrack = $derived(!!$active);

  async function send(command) {
    try {
      await sendTransport(command);
    } catch (err) {
      console.info('transport:', err.message);
    }
  }

  // ── A station ──────────────────────────────────────────────────────────
  const station = $derived($active === 'radio' ? ($radio?.station ?? null) : null);
  const turning = $derived(!!station && ['connecting', 'reconnecting'].includes($radio?.state));
  //: Stop while the station sounds or is on its way; Play when it stopped
  //: or did not answer (Play tries again).
  const sounding = $derived(!!station && (turning || $radio?.state === 'playing'));
  //: The heart turns at once, as the play toggle's icon does, until the
  //: player says so or HEART_MS passes.
  const HEART_MS = 8000;
  let hearted = $state(null);
  let heartTimer;
  $effect(() => {
    if (hearted && (station?.id !== hearted.id || !!station?.favourite === hearted.on)) {
      clearTimeout(heartTimer);
      hearted = null;
    }
  });
  const favourite = $derived(hearted && hearted.id === station?.id ? hearted.on : !!station?.favourite);
  async function toggleHeart() {
    if (!station) return;
    const s = station;
    const on = !favourite;
    hearted = { id: s.id, on };
    clearTimeout(heartTimer);
    heartTimer = setTimeout(() => (hearted = null), HEART_MS);
    try {
      await (on ? addFavourite(s) : removeFavourite(s.id));
    } catch (err) {
      hearted = null;
      onsay(err.message);
    }
  }
</script>

{#snippet heartButton()}
  <button class="heart" type="button" aria-label={favourite ? 'Remove from favourites' : 'Add to favourites'}
          aria-pressed={favourite} onclick={toggleHeart}>
    <HeartIcon filled={favourite} size={big ? 26 : 22} />
  </button>
{/snippet}

<div class="transport" class:is-big={big} class:is-idle={!hasTrack} class:is-radio={!!station && !!heart}
     inert={!hasTrack}>
  {#if station && heart === 'start'}{@render heartButton()}{/if}
  {#if declared.includes('previous')}
    <button class="skip" type="button" aria-label={station ? 'Previous favourite' : 'Previous'} disabled={!can('previous')}
            onclick={() => send('previous')}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.previous} /></svg>
    </button>
  {/if}
  {#if station && declared.includes('play')}
    <button class="play" type="button" aria-label={sounding ? 'Stop' : 'Play'} onclick={() => send(sounding ? 'pause' : 'play')}>
      {#if turning}
        <svg class="play__turn" viewBox="0 0 24 24" aria-hidden="true"><path d={RADIO.spinner} /></svg>
      {:else if sounding}
        <svg class="play__stop" viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2" /></svg>
      {:else}
        <svg class="play__play" viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.play} /></svg>
      {/if}
    </button>
  {:else if declared.includes('play') && declared.includes('pause')}
    <button class="play" type="button" aria-label={toggle.shows === 'playing' ? 'Pause' : 'Play'} onclick={toggle.toggle}>
      {#if hasTrack && toggle.shows === 'playing'}
        <svg class="play__pause" viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.pause} /></svg>
      {:else}
        <svg class="play__play" viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.play} /></svg>
      {/if}
    </button>
  {/if}
  {#if declared.includes('next')}
    <button class="skip" type="button" aria-label={station ? 'Next favourite' : 'Next'} disabled={!can('next')}
            onclick={() => send('next')}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.next} /></svg>
    </button>
  {/if}
  {#if station && heart === 'end'}{@render heartButton()}{/if}
  {#if station && heart === 'start'}<span class="heart-room" aria-hidden="true"></span>{/if}
</div>

<style>
  .transport {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    --sk: 44px;
    --sk-glyph: 26px;
    --pl: 56px;
    --pl-pause: 28px;
    --pl-play: 30px;
  }
  .transport.is-big {
    gap: 24px;
    --sk: 64px;
    --sk-glyph: 38px;
    --pl: 84px;
    --pl-pause: 40px;
    --pl-play: 42px;
  }
  .transport.is-idle {
    opacity: 0.38;
  }
  button {
    border: 0;
    padding: 0;
    margin: 0;
    border-radius: 50%;
    display: grid;
    place-items: center;
    box-sizing: border-box;
    cursor: pointer;
    flex-shrink: 0;
    font: inherit;
  }
  button:active {
    transform: scale(0.95);
  }
  button:disabled {
    opacity: 0.38;
    cursor: default;
  }
  svg {
    fill: currentColor;
    display: block;
  }
  .skip {
    width: var(--sk);
    height: var(--sk);
    background: var(--c-ink-09);
    color: var(--ink);
  }
  .skip svg {
    width: var(--sk-glyph);
    height: var(--sk-glyph);
  }
  .play {
    width: var(--pl);
    height: var(--pl);
    background: var(--accent-artist);
    color: var(--bg-panel);
    box-shadow: 0 0 22px var(--c-artist-22), 0 12px 30px var(--c-artist-35);
  }
  .play__pause {
    width: var(--pl-pause);
    height: var(--pl-pause);
  }
  .play__play {
    width: var(--pl-play);
    height: var(--pl-play);
  }

  /* A station beside the cover (H17): the row packed to the left, the
     heart at its right; without a screen (H20), the heart at its left and
     its room kept at the right, the five spread across the column. */
  .transport.is-radio {
    --sk: 42px;
    --sk-glyph: 21px;
    justify-content: flex-start;
    gap: 8px;
    margin: 0 -4px 0 -2px;
  }
  .transport.is-radio.is-big {
    --sk: 64px;
    --sk-glyph: 38px;
    justify-content: space-between;
    gap: 0;
    margin: 0;
  }
  .transport.is-radio button:disabled {
    opacity: 0.4;
  }
  .play__stop {
    width: 20px;
    height: 20px;
  }
  .is-big .play__stop {
    width: 30px;
    height: 30px;
  }
  .play__turn {
    width: 26px;
    height: 26px;
    fill: none;
    stroke: currentColor;
    stroke-width: 3.2;
    stroke-linecap: round;
    animation: turn 1s linear infinite;
  }
  .is-big .play__turn {
    width: 34px;
    height: 34px;
  }
  @keyframes turn {
    to {
      transform: rotate(360deg);
    }
  }
  .heart {
    width: 44px;
    height: 44px;
    margin-left: auto;
    background: var(--ink-fill);
  }
  .is-big .heart,
  .heart-room {
    width: 52px;
    height: 52px;
    flex-shrink: 0;
    margin-left: 0;
  }
</style>
