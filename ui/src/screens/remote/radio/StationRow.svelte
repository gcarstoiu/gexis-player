<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0180, design/source/31 (2a, H01, H05, H09): a station on the phone -
  the favourite's number where the list has one, the logo, the name and its
  meta, the heart. The first tap selects the row and shows Play; only Play
  plays (George, 2026-11-14, as every leaf row). The heart acts at once.
  Playing, the meta becomes the visualiser glyph and *Playing · FLAC 1411*.
-->
<script>
  import StationLogo from '../../../lib/StationLogo.svelte';
  import HeartIcon from '../../../lib/HeartIcon.svelte';
  import { FILLED } from '../icons.js';
  import { RADIO } from './glyphs.js';
  import { rowMeta } from './words.js';

  let {
    station,
    num = null,
    selected = false,
    playing = false,
    favourite = false,
    //: Search's text: its letters in the name are drawn in the accent.
    match = '',
    onselect = () => {},
    onplay = () => {},
    onheart = () => {},
  } = $props();

  const meta = $derived(rowMeta(station));
  const sound = $derived([station.codec, station.bitrate].filter(Boolean).join(' '));

  const parts = $derived.by(() => {
    const name = station.name ?? '';
    const want = match.trim().toLowerCase();
    if (want.length < 2) return [{ text: name, hit: false }];
    const out = [];
    const lower = name.toLowerCase();
    let at = 0;
    for (let i = lower.indexOf(want); i !== -1; i = lower.indexOf(want, at)) {
      if (i > at) out.push({ text: name.slice(at, i), hit: false });
      out.push({ text: name.slice(i, i + want.length), hit: true });
      at = i + want.length;
    }
    if (at < name.length) out.push({ text: name.slice(at), hit: false });
    return out;
  });

  function key(event) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onselect();
    }
  }
</script>

<div class="row" class:is-selected={selected} class:is-revealed={selected} role="button" tabindex="-1"
     aria-label={station.name} onclick={onselect} onkeydown={key}>
  {#if num !== null}<span class="num">{num}</span>{/if}
  <StationLogo src={station.logo} size={44} radius="var(--station-logo-phone-radius)" mark={20} />
  <div class="text">
    <span class="name">{#each parts as p, i (i)}{#if p.hit}<span class="hit">{p.text}</span>{:else}{p.text}{/if}{/each}</span>
    {#if playing}
      <span class="meta meta--playing">
        <svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true"><path d={RADIO.bars} /></svg>
        {sound ? `Playing · ${sound}` : 'Playing'}
      </span>
    {:else}
      <span class="meta">{meta}</span>
    {/if}
  </div>
  <div class="acts">
    {#if selected}
      <button class="play" type="button" aria-label="Play" onclick={(e) => { e.stopPropagation(); onplay(); }}>
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d={FILLED.play} /></svg>
      </button>
    {/if}
    <button class="heart" type="button" aria-label={favourite ? 'Remove from favourites' : 'Add to favourites'}
            aria-pressed={favourite} onclick={(e) => { e.stopPropagation(); onheart(); }}>
      <HeartIcon filled={favourite} size={22} />
    </button>
  </div>
</div>

<style>
  .row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 9px 6px 9px 8px;
    border-radius: var(--r-14);
    cursor: pointer;
    outline: none;
  }
  .row.is-selected {
    background: var(--row-selected);
  }
  .num {
    width: 14px;
    flex-shrink: 0;
    text-align: right;
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--ink-quiet);
  }
  .text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .name {
    font-size: 17px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .is-selected .name,
  .hit {
    color: var(--accent-lms);
  }
  .meta {
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--c-ink-62);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .meta--playing {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--accent-lms);
  }
  .meta--playing svg {
    flex-shrink: 0;
    fill: none;
    stroke: currentColor;
    stroke-width: 2.6;
    stroke-linecap: round;
  }
  .acts {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }
  button {
    border: 0;
    padding: 0;
    margin: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    cursor: pointer;
    font: inherit;
  }
  .play {
    width: 40px;
    height: 40px;
    box-sizing: border-box;
    border-radius: var(--r-md);
    background: var(--row-act-ground);
    border: 1px solid var(--row-act-line);
    color: var(--accent-lms);
  }
  .play svg {
    fill: currentColor;
    margin-left: 2px;
  }
  .heart {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: transparent;
  }
  button:active {
    transform: scale(0.95);
  }
</style>
