<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The radio mark** (design/source/31, decided while drawing #2, George
  2026-11-14): a dot between two pairs of arcs, in the radio's accent. Also
  the picture of a station with no logo. §8's Arcs fan read as Wi-Fi at
  this size.
-->
<script>
  let { size = 28, stroke = 2, ink = 'var(--accent-radio)' } = $props();
</script>

<svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke={ink} stroke-width={stroke}
  stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style:color={ink}>
  <circle cx="12" cy="12" r="2.3" fill="currentColor" stroke="none"></circle>
  <path d="M8.1 8.1a5.5 5.5 0 0 0 0 7.8"></path>
  <path d="M15.9 8.1a5.5 5.5 0 0 1 0 7.8"></path>
  <path d="M5.1 5.1a9.8 9.8 0 0 0 0 13.8"></path>
  <path d="M18.9 5.1a9.8 9.8 0 0 1 0 13.8"></path>
</svg>

<style>
  svg { display: block; flex-shrink: 0; }
</style>
