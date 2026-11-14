<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  design/source/31 (H01, H05-H07, H11-H16): the mini player at the foot of
  the phone's Radio page while a renderer is active - the art, the title and
  the artist, the radio mark while a station plays, and Stop (a station
  stops; play/pause for the others). A tap anywhere else opens Remote.
-->
<script>
  import { active, metadata, sendTransport } from '../../../lib/state.js';
  import { radio } from '../../../lib/radio.js';
  import { playToggle } from '../../../lib/playToggle.svelte.js';
  import RadioMark from '../../../lib/RadioMark.svelte';
  import StationLogo from '../../../lib/StationLogo.svelte';
  import { FILLED } from '../icons.js';

  let { artwork = null, onopen = () => {} } = $props();

  const isRadio = $derived($active === 'radio');
  const toggle = playToggle(() => $metadata?.transport, () => $active);
  const sounding = $derived(isRadio
    ? ['playing', 'connecting', 'reconnecting'].includes($radio?.state)
    : toggle.shows === 'playing');
  const second = $derived($metadata?.artist || ($metadata?.album !== $metadata?.title ? $metadata?.album : '') || '');

  function press(event) {
    event.stopPropagation();
    if (!isRadio) return toggle.toggle();
    sendTransport(sounding ? 'pause' : 'play').catch((err) => console.info('transport:', err.message));
  }
</script>

<div class="mini" role="button" tabindex="-1" aria-label="Now playing" onclick={onopen}
     onkeydown={(e) => { if (e.key === 'Enter') onopen(); }}>
  {#if isRadio && (!artwork || artwork === $radio?.station?.logo)}
    <StationLogo src={artwork} size={46} radius="var(--r-10)" mark={22} />
  {:else if artwork}
    <img class="art" src={artwork} alt="" />
  {:else}
    <span class="art art--none"></span>
  {/if}
  <span class="words">
    <span class="title">{$metadata?.title ?? ''}</span>
    {#if second}<span class="second" class:is-artist={!!$metadata?.artist}>{second}</span>{/if}
  </span>
  {#if isRadio}<RadioMark size={26} />{/if}
  <button class="go" type="button" aria-label={isRadio ? (sounding ? 'Stop' : 'Play') : (sounding ? 'Pause' : 'Play')}
          onclick={press}>
    {#if sounding && isRadio}
      <svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2" /></svg>
    {:else if sounding}
      <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d={FILLED.pause} /></svg>
    {:else}
      <svg class="go__play" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d={FILLED.play} /></svg>
    {/if}
  </button>
</div>

<style>
  .mini {
    flex-shrink: 0;
    height: 62px;
    margin: 0 10px 10px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 8px;
    border-radius: var(--r-18);
    background: var(--c-dark-101a21-86);
    border: 1px solid var(--ink-line);
    cursor: pointer;
    outline: none;
  }
  .art {
    width: 46px;
    height: 46px;
    flex-shrink: 0;
    border-radius: var(--r-10);
    object-fit: cover;
    display: block;
  }
  .art--none {
    background: var(--ink-fill);
  }
  .words {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 1px;
  }
  .title {
    font-size: 15px;
    font-weight: 700;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .second {
    font-size: 13px;
    color: var(--ink-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .second.is-artist {
    color: var(--accent-artist);
  }
  .go {
    width: 46px;
    height: 46px;
    flex-shrink: 0;
    border: 0;
    padding: 0;
    border-radius: 50%;
    background: var(--play-fill);
    color: var(--ink-on-accent);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 18px var(--c-artist-24), 0 10px 24px var(--c-artist-30);
    cursor: pointer;
  }
  .go:active {
    transform: scale(0.95);
  }
  .go svg {
    fill: currentColor;
  }
  .go__play {
    margin-left: 2px;
  }
</style>
