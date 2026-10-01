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
  import { screen } from '../lib/family.svelte.js';
  import { fitText } from '../lib/fit.js';

  let { from, to } = $props();

  const IMAGES = { spotify: spotifyMark, bluetooth: bluetoothMark };
  //: ADR-0086: the name and the colour are the source's own, so a takeover
  //: to a renderer this file has never heard of is still announced by name.
  //: The id is the fallback, which is what it always was for an unknown one.
  const label = (id) => $sources[id]?.name ?? id;
  const accent = $derived($sources[to]?.accent ?? `var(--accent-${to}, var(--accent-lms))`);

  //: ADR-0109, Bar family (design `Bar Panels` t2, round 2 `Bar States`
  //: t-long): one strip - the old source small at the left, a line that
  //: takes the width, the new one in its ring with the name beside it.
  const bar = $derived(screen.family === 'bar');
  const wide = $derived(screen.width > 1500);
  //: The name is 64 on one line; a name that needs two lines is 52 in a
  //: 340 px box (64 in 520 from 1500 wide). Smaller only when a single word
  //: is wider than the box, so it never leaves it.
  const nameSizes = $derived(
    wide ? [[64, 2], [56, 2], [48, 2], [40, 2], [34, 2]] : [[64, 1], [52, 2], [46, 2], [40, 2], [34, 2]],
  );
  //: Decision 8 of the round-2 review: a renderer with no mark shows its
  //: initial in a ring.
  const initial = (id) => ((label(id) ?? '').trim()[0] ?? '?').toUpperCase();
  const drawable = (id) => id === 'lms' || !!IMAGES[id] || !!$sources[id]?.mark;
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
      style:height={`${size}px`}
      style:opacity
    />
  {:else if $sources[source]?.mark}
    <!-- **ADR-0086, the same gap as `SourceMark` had one layer down.** This
         file already takes the *name* and the *accent* from the manifest, so a
         takeover to a renderer it has never heard of is announced by name -
         and then drew an empty ring, because the glyph was the one thing it
         still looked up in a map of the three it knows. -->
    <img class="mark" src={$sources[source].mark} alt="" style:height={`${size}px`} style:opacity />
  {/if}
{/snippet}

{#if bar}
<div class="handoff handoff--bar" style:--to-accent={accent} out:fade={{ duration: 260 }}>
  <div class="hb__wash"></div>
  <div class="hb">
    <div class="hb__from">
      {#if drawable(from)}
        {@render mark(from, 44, 'var(--ink)', 1)}
      {:else}
        <span class="hb__letter hb__letter--from">{initial(from)}</span>
      {/if}
      <span class="hb__fromname">{label(from)}</span>
    </div>
    <div class="hb__line"></div>
    <div class="hb__to">
      <div class="hb__ring">
        {#if drawable(to)}
          {@render mark(to, 70, 'var(--to-accent)', 1)}
        {:else}
          <span class="hb__letter">{initial(to)}</span>
        {/if}
      </div>
      <div class="hb__text" class:hb__text--wide={wide}>
        <div class="hb__kicker">Handing off to</div>
        <div class="hb__name" use:fitText={{ sizes: nameSizes, key: label(to) }}>{label(to)}</div>
      </div>
    </div>
  </div>
</div>
{:else}
<!-- **Appears at once, fades out** (George, 2026-09-26). The design fades it in
  over 260 ms, and the incoming renderer's artwork changed underneath while it
  was still mostly transparent - a blink. Its contents still rise in. -->
<div class="handoff" style:--to-accent={accent} out:fade={{ duration: 260 }}>
  <div class="caption">Handing off</div>

  <div class="pair">
    <div class="side">
      <div class="ring ring--from">
        {#if drawable(from)}{@render mark(from, 44, 'var(--ink)', 0.42)}{:else}<span class="letter letter--from">{initial(from)}</span>{/if}
      </div>
      <span class="label label--from">{label(from)}</span>
    </div>

    <div class="flow">
      <div class="line"></div>
      <span class="note note--1">&#9834;</span>
      <span class="note note--2">&#9835;</span>
      <span class="note note--3">&#9834;</span>
    </div>

    <div class="side">
      <div class="ring ring--to">
        {#if drawable(to)}{@render mark(to, 50, 'var(--to-accent)', 1)}{:else}<span class="letter">{initial(to)}</span>{/if}
      </div>
      <span class="label label--to">{label(to)}</span>
    </div>
  </div>
</div>
{/if}

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

  /* ADR-0109, Bar family: `Bar Panels` t2 and `Bar States` t-long. */
  .handoff--bar {
    display: block;
  }
  .hb__wash {
    position: absolute;
    top: 0;
    bottom: 0;
    right: 0;
    width: 62%;
    background: linear-gradient(90deg, transparent, color-mix(in srgb, var(--to-accent) 20%, transparent));
  }
  .hb {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    padding: 0 72px;
    gap: 40px;
    animation: rise 380ms ease both;
  }
  .hb__from {
    display: flex;
    align-items: center;
    gap: 18px;
    opacity: 0.55;
    flex-shrink: 0;
    min-width: 0;
    max-width: 280px;
  }
  .hb__fromname {
    font-size: 26px;
    font-weight: 600;
    color: rgba(233, 238, 242, 0.7);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }
  .hb__line {
    flex: 1;
    min-width: 120px;
    height: 2px;
    background: linear-gradient(90deg, rgba(233, 238, 242, 0.12), var(--to-accent));
  }
  .hb__to {
    display: flex;
    align-items: center;
    gap: 28px;
    flex-shrink: 0;
  }
  .hb__ring {
    width: 176px;
    height: 176px;
    border-radius: 50%;
    flex-shrink: 0;
    box-sizing: border-box;
    border: 3px solid var(--to-accent);
    background: color-mix(in srgb, var(--to-accent) 14%, transparent);
    box-shadow: 0 0 60px color-mix(in srgb, var(--to-accent) 25%, transparent);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  /* Standard: a renderer with no mark shows its initial inside the ring it
     already has (decision 8: both families), at the mark's size. */
  .letter {
    font-size: 40px;
    font-weight: 800;
    line-height: 1;
    color: var(--to-accent);
  }
  .letter--from {
    font-size: 34px;
    color: var(--ink);
    opacity: 0.42;
  }
  /* A renderer with no mark: its initial, in the accent (round 2 t-long
     draws a plugin whose accent is ink). */
  .hb__letter {
    font-size: 84px;
    font-weight: 800;
    line-height: 1;
    color: var(--to-accent);
  }
  .hb__letter--from {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    border: 2px solid rgba(233, 238, 242, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    color: var(--ink);
    flex-shrink: 0;
  }
  .hb__text {
    max-width: 340px;
    min-width: 0;
  }
  .hb__text--wide {
    max-width: 520px;
  }
  .hb__kicker {
    font-family: var(--font-mono);
    font-size: 15px;
    letter-spacing: 0.34em;
    text-transform: uppercase;
    color: rgba(233, 238, 242, 0.55);
    white-space: nowrap;
  }
  .hb__name {
    margin-top: 6px;
    font-size: 64px;
    line-height: 1.02;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: var(--to-accent);
    text-wrap: balance;
  }

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
