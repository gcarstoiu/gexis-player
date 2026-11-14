<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  design/source/31 (H05-H07, H11, H16): a sub-page's head on the phone -
  Back (44), the title (20/800) and the crumb in mono 12; Done or nothing at
  the right.
-->
<script>
  import { RADIO } from './glyphs.js';

  let { title, crumb = '', onback, end = null } = $props();
</script>

<div class="head">
  <button class="back" type="button" aria-label="Back" onclick={onback}>
    <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d={RADIO.back} /></svg>
  </button>
  <span class="words">
    <span class="title">{title}</span>
    {#if crumb}<span class="crumb">{crumb}</span>{/if}
  </span>
  {#if end}{@render end()}{/if}
</div>

<style>
  .head {
    flex-shrink: 0;
    height: 50px;
    margin: 0 16px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .back {
    width: 44px;
    height: 44px;
    flex-shrink: 0;
    border: 0;
    padding: 0;
    border-radius: 50%;
    background: var(--ink-fill);
    color: var(--ink);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }
  .back:active {
    background: var(--ink-fill-press);
  }
  .back svg {
    fill: none;
    stroke: currentColor;
    stroke-width: 2.6;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .words {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .title {
    font-size: 20px;
    font-weight: 800;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .crumb {
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.06em;
    color: var(--ink-quiet);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
