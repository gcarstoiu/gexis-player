<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The waiting screen's way to Radio** (design/source/31, `RadioCornerButton`,
  picks 5a / 9a; P21, P22, B14, B15, B34): beside Settings in the corner, the
  radio mark and *Radio*. It shows whenever the waiting screen does - Lyrion
  off, or its library navigation off - while internet radio is on.
-->
<script>
  import RadioMark from '../../lib/RadioMark.svelte';
  import { pressing } from '../../lib/press.svelte.js';

  let { onopen } = $props();
  const press = pressing();
</script>

<button class="radiobtn" class:is-pressed={press.is('radio')} type="button" aria-label="Radio"
  onpointerdown={() => press.down('radio')} onpointerup={press.up} onpointercancel={press.up}
  onclick={() => press.act(onopen)}>
  <RadioMark size={28} />
  <span>Radio</span>
</button>

<style>
  /* Settings' corner button, wider (WaitingHome.svelte's `.corner`). */
  .radiobtn {
    width: var(--radio-corner-button-width);
    height: 64px;
    box-sizing: border-box;
    border-radius: var(--r-18);
    border: 1px solid var(--c-ink-14);
    background: var(--c-dark-101a21-60);
    color: var(--ink);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 0;
    font: inherit;
    font-size: 20px;
    font-weight: 700;
    cursor: pointer;
    transition: transform 120ms ease, background 120ms ease;
  }
  .radiobtn.is-pressed {
    transform: scale(0.94);
    background: var(--c-ink-16);
  }
</style>
