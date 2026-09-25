<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Handoff transition, Phase 4 step 4f (criterion 4, ADR-0010). Ported from
  design/source/Now Playing.dc.html. Shown for the real takeover, from the
  published handoff's start until it ends, held long enough to read.
-->
<script>
  import { fade } from 'svelte/transition';
  import spotifyMark from '../assets/icon-spotify.png';
  import bluetoothMark from '../assets/icon-bluetooth.png';
  import lyrionMark from '../assets/icon-lyrion.svg';
  import { sources } from '../lib/state.js';

  let { from, to } = $props();

  const IMAGES = { spotify: spotifyMark, bluetooth: bluetoothMark };
  //: ADR-0086: the name and the colour are the source's own, so a takeover
  //: to a renderer this file has never heard of is still announced by name.
  //: The id is the fallback, which is what it always was for an unknown one.
  const label = (id) => $sources[id]?.name ?? id;
  const accent = $derived($sources[to]?.accent ?? `var(--accent-${to}, var(--accent-lms))`);
</script>

{#snippet mark(source, size, color, opacity)}
  {#if source === 'lms'}
    <span
      class="mark mark--lms"
      style:width={`${size * 1.34}px`}
      style:height={`${size}px`}
      style:background={color}
      style:opacity
      style:--mark={`url(${lyrionMark})`}
    ></span>
  {:else if IMAGES[source]}
    <img
      class="mark"
      src={IMAGES[source]}
      alt=""
      style:height={`${source === 'bluetooth' ? size * 1.12 : size}px`}
      style:opacity
    />
  {/if}
{/snippet}

<div class="handoff" style:--to-accent={accent} transition:fade={{ duration: 260 }}>
  <div class="caption">Handing off</div>

  <div class="pair">
    <div class="side">
      <div class="ring ring--from">{@render mark(from, 44, 'var(--ink)', 0.42)}</div>
      <span class="label label--from">{label(from)}</span>
    </div>

    <div class="flow">
      <div class="line"></div>
      <span class="note note--1">&#9834;</span>
      <span class="note note--2">&#9835;</span>
      <span class="note note--3">&#9834;</span>
    </div>

    <div class="side">
      <div class="ring ring--to">{@render mark(to, 50, 'var(--to-accent)', 1)}</div>
      <span class="label label--to">{label(to)}</span>
    </div>
  </div>
</div>

<style>
  .handoff {
    position: absolute;
    inset: 0;
    z-index: 30;
    background: rgba(13, 21, 27, 0.95);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 54px;
  }

  .caption {
    font-family: var(--font-mono);
    font-size: var(--t-meta);
    letter-spacing: 0.34em;
    text-transform: uppercase;
    color: rgba(233, 238, 242, 0.5);
    animation: rise 320ms ease both;
  }

  .pair {
    display: flex;
    align-items: center;
    gap: 44px;
    animation: rise 380ms ease 60ms both;
  }

  .side {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
    width: 300px;
  }

  .ring {
    width: 132px;
    height: 132px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .ring--from {
    border: 2px solid rgba(233, 238, 242, 0.18);
  }
  .ring--to {
    border: 2px solid var(--to-accent);
    background: color-mix(in srgb, var(--to-accent) 15%, transparent);
    box-shadow: 0 0 46px color-mix(in srgb, var(--to-accent) 15%, transparent);
  }

  .mark {
    flex-shrink: 0;
    display: block;
    width: auto;
  }
  .mark--lms {
    -webkit-mask: var(--mark) center / contain no-repeat;
    mask: var(--mark) center / contain no-repeat;
  }

  .label {
    white-space: nowrap;
  }
  .label--from {
    font-size: 24px;
    font-weight: 600;
    letter-spacing: 0.02em;
    color: rgba(233, 238, 242, 0.45);
  }
  .label--to {
    font-size: 30px;
    font-weight: 700;
    letter-spacing: 0.01em;
    color: var(--to-accent);
  }

  .flow {
    width: 176px;
    height: 132px;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }
  .line {
    position: absolute;
    left: 0;
    right: 0;
    top: 50%;
    height: 2px;
    background: linear-gradient(90deg, rgba(233, 238, 242, 0.12), var(--to-accent));
  }
  .note {
    position: absolute;
    top: 50%;
    left: 50%;
    line-height: 1;
    color: var(--to-accent);
  }
  .note--1 { margin-top: -42px; margin-left: -44px; font-size: 40px; animation: march 1400ms linear infinite; }
  .note--2 { margin-top: -4px; margin-left: -10px; font-size: 32px; animation: march 1400ms linear 320ms infinite; }
  .note--3 { margin-top: -52px; margin-left: 14px; font-size: 28px; animation: march 1400ms linear 700ms infinite; }

  @keyframes rise {
    from { opacity: 0; transform: translateY(14px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes march {
    0% { transform: translateX(-34px); opacity: 0; }
    35% { transform: translateX(-12px); opacity: 1; }
    100% { transform: translateX(34px); opacity: 0; }
  }
</style>
