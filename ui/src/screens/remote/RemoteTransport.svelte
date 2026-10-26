<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0164: the remote's transport (design/source/21): shuffle, previous,
  play/pause, next and repeat, in the screen layout's sizes or, `big`, the
  larger ones of a player without a screen. What the renderer does not
  declare is left out and the row re-centres (ADR-0037); what it declares
  but cannot do now is dimmed. Repeat cycles off, all, one, as on the panel
  (ADR-0164 D7). Nothing playing: the row at 0.38, inert.
-->
<script>
  import { active, available, capabilities, metadata, repeat, sendTransport, shuffle } from '../../lib/state.js';
  import { playToggle } from '../../lib/playToggle.svelte.js';
  import { FILLED } from './icons.js';

  let { big = false } = $props();

  const NEXT_REPEAT = { off: 'all', all: 'one', one: 'off' };
  //: Nothing playing: the whole row as the design draws it, dimmed and inert.
  const ALL = ['play', 'pause', 'next', 'previous', 'shuffle', 'repeat'];
  const declared = $derived($active ? ($capabilities?.[$active]?.controls ?? []) : ALL);
  //: Nothing playing, the row is dimmed once as a whole, not each button again.
  const can = (command) => !$active || $available.includes(command);
  const toggle = playToggle(() => $metadata?.transport, () => $active);
  const hasTrack = $derived(!!$active);
  const repeatMode = $derived($repeat ?? 'off');

  async function send(command, body) {
    try {
      await sendTransport(command, body);
    } catch (err) {
      console.info('transport:', err.message);
    }
  }
</script>

<div class="transport" class:is-big={big} class:is-idle={!hasTrack} inert={!hasTrack}>
  {#if declared.includes('shuffle')}
    <button class="toggle" class:is-on={$shuffle === true} type="button" aria-label="Shuffle"
            aria-pressed={$shuffle === true} disabled={!can('shuffle')}
            onclick={() => send('shuffle', { on: $shuffle !== true })}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.shuffle} /></svg>
    </button>
  {/if}
  {#if declared.includes('previous')}
    <button class="skip" type="button" aria-label="Previous" disabled={!can('previous')} onclick={() => send('previous')}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.previous} /></svg>
    </button>
  {/if}
  {#if declared.includes('play') && declared.includes('pause')}
    <button class="play" type="button" aria-label={toggle.shows === 'playing' ? 'Pause' : 'Play'} onclick={toggle.toggle}>
      {#if hasTrack && toggle.shows === 'playing'}
        <svg class="play__pause" viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.pause} /></svg>
      {:else}
        <svg class="play__play" viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.play} /></svg>
      {/if}
    </button>
  {/if}
  {#if declared.includes('next')}
    <button class="skip" type="button" aria-label="Next" disabled={!can('next')} onclick={() => send('next')}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d={FILLED.next} /></svg>
    </button>
  {/if}
  {#if declared.includes('repeat')}
    <button class="toggle" class:is-on={repeatMode !== 'off'} type="button" aria-label={`Repeat ${repeatMode}`}
            disabled={!can('repeat')} onclick={() => send('repeat', { mode: NEXT_REPEAT[repeatMode] ?? 'all' })}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d={repeatMode === 'one' ? FILLED.repeatOne : FILLED.repeat} /></svg>
    </button>
  {/if}
</div>

<style>
  /* The design's gaps at its 412 px; narrower, they give way first, so the
     five buttons keep their size on a 360 px phone. */
  .transport {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: max(4px, min(24px, calc((100% - 272px) / 4)));
    --tg: 44px;
    --tg-glyph: 22px;
    --sk: 56px;
    --sk-glyph: 34px;
    --pl: 72px;
    --pl-pause: 36px;
    --pl-play: 38px;
  }
  .transport.is-big {
    gap: max(4px, min(18px, calc((100% - 308px) / 4)));
    --tg: 48px;
    --tg-glyph: 24px;
    --sk: 64px;
    --sk-glyph: 38px;
    --pl: 84px;
    --pl-pause: 40px;
    --pl-play: 42px;
  }
  .transport.is-idle {
    opacity: 0.38;
  }
  button,
  .play {
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
  .toggle {
    width: var(--tg);
    height: var(--tg);
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.12);
    color: rgba(233, 238, 242, 0.66);
  }
  .toggle.is-on {
    background: rgba(126, 214, 188, 0.16);
    border-color: rgba(126, 214, 188, 0.42);
    color: #7ed6bc;
  }
  .toggle svg {
    width: var(--tg-glyph);
    height: var(--tg-glyph);
  }
  .skip {
    width: var(--sk);
    height: var(--sk);
    background: rgba(233, 238, 242, 0.09);
    color: #e9eef2;
  }
  .skip svg {
    width: var(--sk-glyph);
    height: var(--sk-glyph);
  }
  .play {
    width: var(--pl);
    height: var(--pl);
    background: #f2a48f;
    color: #16232c;
    box-shadow: 0 0 22px rgba(242, 164, 143, 0.22), 0 12px 30px rgba(242, 164, 143, 0.35);
  }
  .play__pause {
    width: var(--pl-pause);
    height: var(--pl-pause);
  }
  .play__play {
    width: var(--pl-play);
    height: var(--pl-play);
  }
</style>
