<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  What the correction leaves (ADR-0187 D7-D8, George's B and B, 2026-11-23):
  the ringing in the bass for the speaker shown - what is left of a note
  0.2 s later, before and after - and a card per dip the bass keeps, its
  cause and what may help. On the measurement's own screens and, since
  ADR-0189 (B, 2026-11-25), in the room page's step 3.
-->
<script>
  import { bandWord, dipRows, ringBands, ringDb, ringWidth } from '../../lib/room.svelte.js';

  //: `show`: 'ringing' or 'dips'; `speaker`: the chart's speaker shown;
  //: `dips`: the measurement's; `expected`: the after is worked out, not measured.
  let { show = 'ringing', speaker = null, dips = null, expected = false } = $props();

  const rings = $derived(ringBands(speaker));
  const dipCard = $derived(dipRows(dips));
</script>

{#if show === 'dips' && dipCard.length}
  <div class="card dipcard">
    <div class="dipcard__head">
      <span class="dipcard__title">Dips left as they are</span>
      <span class="dipcard__lead">In the bass only cuts: more power does not fill a dip. What causes each, and what may help:</span>
    </div>
    {#each dipCard as d (d.freq)}
      <div class="dip">
        <div class="dip__top"><span class="dip__f">{d.freq}</span><span class="dip__db">{d.depth}</span></div>
        {#if d.tag}<span class="dip__tag dip__tag--{d.tone}">{d.tag}</span>{/if}
        <span class="dip__text">{d.text}</span>
      </div>
    {/each}
  </div>
{:else if show === 'ringing' && rings.length}
  <div class="card ringcard">
    <div class="ringcard__head">
      <span class="ringcard__title">Ringing in the bass</span>
      <span class="ringcard__lead">What is left of a note 0.2 s later. Shorter is cleaner.</span>
    </div>
    {#each rings as r (r.hz)}
      <div class="band">
        <span class="band__hz">{bandWord(r.hz)}</span>
        <span class="band__bars">
          <span class="band__bar band__bar--before" style="width:{ringWidth(r.before)}"></span>
          {#if r.after != null}<span class="band__bar band__bar--after" style="width:{ringWidth(r.after)}"></span>{/if}
        </span>
        <span class="band__db">{ringDb(r.before)}<br />{ringDb(r.after)}</span>
      </div>
    {/each}
    <div class="ringcard__key">
      <span class="key"><span class="key__swatch key__swatch--before"></span>Before</span>
      <span class="key"><span class="key__swatch key__swatch--after"></span>{expected ? 'After, expected' : 'After, measured'}</span>
    </div>
  </div>
{/if}

<style>
  .card {
    flex-shrink: 0;
    border-radius: var(--r-15);
    background: var(--c-white-05);
    border: 1px solid var(--ink-line);
  }
  .dipcard__head,
  .ringcard__head {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .dipcard__head {
    padding: 14px 16px 4px;
  }
  .dipcard__title,
  .ringcard__title {
    font-size: 17px;
    font-weight: 700;
  }
  .dipcard__lead,
  .ringcard__lead {
    font-size: 14px;
    line-height: 1.4;
    color: var(--ink-quiet);
    text-wrap: pretty;
  }
  .dip {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 12px 16px;
  }
  .dip + .dip {
    border-top: 1px solid var(--c-ink-08);
  }
  .dip__top {
    display: flex;
    align-items: baseline;
    gap: 10px;
    font-family: var(--font-mono);
  }
  .dip__f {
    font-size: 16px;
    font-weight: 600;
  }
  .dip__db {
    font-size: 13px;
    color: var(--ink-quiet);
  }
  .dip__tag {
    align-self: flex-start;
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.06em;
    border-radius: var(--r-pill);
    padding: 3px 10px;
  }
  .dip__tag--blue {
    background: var(--rc-dip-cancel-fill);
    color: var(--rc-dip-cancel);
  }
  .dip__tag--amber {
    background: var(--rc-without-fill);
    color: var(--rc-without);
  }
  .dip__tag--grey {
    background: var(--c-ink-08);
    color: var(--c-ink-78);
  }
  .dip__text {
    font-size: 14.5px;
    line-height: 1.45;
    color: var(--c-ink-78);
    text-wrap: pretty;
  }
  .ringcard {
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .band {
    display: grid;
    grid-template-columns: 58px minmax(0, 1fr) 70px;
    gap: 10px;
    align-items: center;
  }
  .band__hz {
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--c-ink-78);
  }
  .band__bars {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .band__bar {
    height: 9px;
    border-radius: var(--r-pill);
  }
  .band__bar--before,
  .key__swatch--before {
    background: var(--rc-before);
  }
  .band__bar--after,
  .key__swatch--after {
    background: var(--rc-after);
  }
  .band__db {
    font-family: var(--font-mono);
    font-size: 12.5px;
    line-height: 1.35;
    text-align: right;
    color: var(--ink-quiet);
    font-variant-numeric: tabular-nums;
  }
  .ringcard__key {
    display: flex;
    gap: 16px;
  }
  .key {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 13px;
    color: var(--c-ink-78);
  }
  .key__swatch {
    width: 18px;
    height: 9px;
    border-radius: var(--r-pill);
  }
</style>
